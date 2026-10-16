#!/usr/bin/env python3
"""Conecta la carpeta real a Void. Sin --confirmar-alojamiento solo muestra el alcance local."""
import argparse
import getpass
import hashlib
import stat
import uuid
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request

MAX_ARCHIVO=128*1024*1024
TAM_PARTE=512*1024
MAX_CLARO=200*1024*1024
USER_AGENT='VoidVault/0.0.11 (+https://vaultvoid.app)'

def dentro_de(ruta, base):
    """Si una ruta está dentro de otra, como en Python 3.9, pero en 3.8: la guía promete 3.8 (16-oct)."""
    try:
        ruta.relative_to(base)
        return True
    except ValueError:
        return False

def archivos(vault):
    """Inventario completo. No lee contenidos, no sigue enlaces externos ni omite ignorados."""
    vault=Path(vault).resolve()
    if (vault/'.git').is_symlink() or not (vault/'.git').is_dir():
        raise ValueError('Hace falta git local completo, sin worktree.')
    if (vault/'.git/objects/info/alternates').exists() or (vault/'.git/worktrees').exists():
        raise ValueError('El historial depende de otra carpeta; no se omite: prepara un vault autónomo.')
    seleccion=[]
    def recorrer(base,ancestros):
        real=base.resolve(strict=True)
        if not dentro_de(real, vault):
            raise ValueError('Hay un enlace fuera del vault; no se omite ni se copia sin revisar su dueño.')
        if real in ancestros:
            raise ValueError('Hay un enlace circular; no se omite: corrígelo antes de copiar.')
        for p in sorted(base.iterdir()):
            r=p.relative_to(vault).as_posix()
            if re.search(r'[\\\x00-\x1f\x7f]',r) or re.match(r'^[A-Za-z]:',r):
                raise ValueError('Hay una ruta incompatible con la copia segura; no se omite ningún dato.')
            if p.is_symlink():
                destino=p.resolve(strict=True)
                if not dentro_de(destino, vault):
                    raise ValueError('Hay un enlace fuera del vault; no se omite ni se copia sin revisar su dueño.')
            else:destino=p
            modo=destino.stat().st_mode
            if stat.S_ISDIR(modo):recorrer(p,ancestros|{real})
            elif stat.S_ISREG(modo):seleccion.append(r)
            else:raise ValueError('Hay un archivo especial; no se omite: prepara una copia recuperable.')
    recorrer(vault,set())
    if '.git/HEAD' not in seleccion:raise ValueError('Hace falta un vault con git local completo.')
    if '.git/index.lock' in seleccion:raise ValueError('Git está escribiendo: espera a que termine antes de copiar.')
    return sorted(seleccion)


def estructura(vault):
    """Directorios originales y enlaces, incluidos los vacíos. Solo metadatos."""
    directorios=[];enlaces={}
    for raiz,dirs,ficheros in os.walk(vault,followlinks=False):
        for nombre in dirs+ficheros:
            p=Path(raiz)/nombre;r=p.relative_to(vault).as_posix()
            if re.search(r'[\\\x00-\x1f\x7f]',r) or re.match(r'^[A-Za-z]:',r):
                raise ValueError('Hay una ruta incompatible con la copia segura; no se omite ningún dato.')
            if p.is_symlink():enlaces[r]=os.readlink(p)
            elif p.is_dir():directorios.append(r)
        dirs[:]=[d for d in dirs if not (Path(raiz)/d).is_symlink()]
    return sorted(directorios),enlaces


def firma(p):
    st=p.stat()
    return st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns


def empaquetar(vault,rutas,para_envio=True):
    """Solo tras consentimiento: copia completa, manifiesto y verificación de cada contenido."""
    vault=Path(vault).resolve()
    if rutas!=archivos(vault):raise ValueError('El vault cambió desde la revisión; vuelve a revisar su alcance.')
    firmas={r:firma(vault/r) for r in rutas}
    if sum(f[2] for f in firmas.values())>MAX_CLARO:raise ValueError('La copia completa supera 200 MiB; no se recorta ningún dato.')
    directorios,enlaces=estructura(vault)
    manifiesto={'formato':'void-vault-completo-1','archivos':{},'enlaces':enlaces,'directorios':directorios,'sqlite':{}}
    # WAL/SHM originales se conservan aparte. El SQLite activo incorpora el WAL mediante backup.
    bases=[r for r in rutas if r.startswith('.agente/') and r.endswith('.db')]
    metaruta='.void/importacion-'+uuid.uuid4().hex
    trasladados={r:metaruta+'/sqlite-original/'+r for r in rutas if any(r==db+suf for db in bases for suf in ('-wal','-shm'))}
    copias={};buf=io.BytesIO()
    with tempfile.TemporaryDirectory(prefix='void-copia-') as temporal:
        for n,ruta in enumerate(bases):
            p=vault/ruta;copia=Path(temporal)/str(n)
            with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as origen,sqlite3.connect(copia) as destino:
                origen.backup(destino)
                if destino.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('La conversación no pasó la comprobación de SQLite.')
            copias[ruta]=copia
            manifiesto['sqlite'][ruta]={'respaldo_coherente':True}
        with tarfile.open(fileobj=buf,mode='w:gz',format=tarfile.USTAR_FORMAT,dereference=True) as tar:
            for r in directorios:
                info=tar.gettarinfo(str(vault/r),arcname=r)
                if not info.isdir():raise ValueError('Un directorio cambió durante la copia.')
                tar.addfile(info)
            for ruta in rutas:
                p=vault/ruta
                if not dentro_de(p.resolve(strict=True), vault) or firma(p)!=firmas[ruta]:
                    raise ValueError('Un archivo cambió durante la copia; no se envía una copia incompleta.')
                origen=copias.get(ruta,p);arcname=trasladados.get(ruta,ruta)
                # Materializa enlaces internos para el importador; el manifiesto conserva su forma original.
                info=tar.gettarinfo(str(origen.resolve()),arcname=arcname)
                if not info.isfile():raise ValueError('Un archivo cambió de tipo durante la copia.')
                h=hashlib.sha256()
                class Lectura:
                    def __init__(self,f):self.f=f
                    def read(self,n=-1):
                        datos=self.f.read(n);h.update(datos);return datos
                with origen.open('rb') as f:tar.addfile(info,Lectura(f))
                if firma(p)!=firmas[ruta]:raise ValueError('Un archivo cambió durante la copia; el original se conserva.')
                manifiesto['archivos'][ruta]={'ruta_archivo':arcname,'bytes':info.size,'sha256':h.hexdigest(),'modo':info.mode}
            texto=json.dumps(manifiesto,ensure_ascii=False,sort_keys=True).encode()
            info=tarfile.TarInfo(metaruta+'/manifiesto.json');info.size=len(texto);info.mode=0o600;tar.addfile(info,io.BytesIO(texto))
    if rutas!=archivos(vault) or estructura(vault)!=(directorios,enlaces):
        raise ValueError('El vault cambió durante la copia; vuelve a revisar antes de enviar.')
    if any(firma(vault/r)!=f for r,f in firmas.items()):raise ValueError('El vault cambió durante la copia; no se envía.')
    datos=buf.getvalue()
    if para_envio and len(datos)>MAX_ARCHIVO:raise ValueError(f'La copia completa ocupa {len(datos)/1024/1024:.2f} MiB y supera el límite comprimido del piloto; no se recorta ningún dato.')
    verificar(datos)
    return datos


def verificar(datos):
    """Verifica todos los archivos declarados sin imprimir sus contenidos."""
    with tarfile.open(fileobj=io.BytesIO(datos),mode='r:gz') as tar:
        miembros=tar.getmembers();nombres=[m.name for m in miembros]
        if len(set(nombres))!=len(nombres):raise ValueError('La copia tiene rutas repetidas.')
        metas=[m for m in miembros if re.fullmatch(r'\.void/importacion-[0-9a-f]{32}/manifiesto\.json',m.name)]
        if not metas:raise ValueError('Falta el manifiesto de conservación.')
        meta=json.load(tar.extractfile(metas[-1]));declaradas=set()
        for dato in meta['archivos'].values():
            m=tar.getmember(dato['ruta_archivo']);h=hashlib.sha256();n=0
            if not m.isfile():raise ValueError('Un contenido de la copia no es un archivo real.')
            with tar.extractfile(m) as f:
                while True:
                    b=f.read(1024*1024)
                    if not b:break
                    h.update(b);n+=len(b)
            if n!=dato['bytes'] or h.hexdigest()!=dato['sha256']:raise ValueError('La copia no conserva un contenido declarado.')
            declaradas.add(m.name)
        nuevas={m.name for m in miembros if m.isfile()}-declaradas-{metas[-1].name}
        if nuevas:raise ValueError('Hay contenidos sin declarar en el manifiesto.')
        return {'archivos':len(meta['archivos']),'enlaces':len(meta['enlaces']),'verificado':True}


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Void devolvió una redirección: no envío tus datos a otro destino.')

def enviar(endpoint,credencial,cuerpo,extra=None):
    h={'authorization':'Bearer '+credencial,'user-agent':USER_AGENT,'content-type':'application/gzip','x-void-origen':'archivo','x-void-consentimiento':'alojar-mi-vault'}
    h.update(extra or {})
    req=urllib.request.Request(endpoint+'/v1/alojar',data=cuerpo,method='POST',headers=h)
    try:
        with urllib.request.build_opener(SinRedireccion()).open(req,timeout=180) as r:return json.loads(r.read(65536))
    except urllib.error.HTTPError as e:
        try:
            try:mensaje=json.loads(e.read(65536)).get('error','No se pudo conectar.')
            except (ValueError,AttributeError):mensaje=f'Void rechazó la conexión (HTTP {e.code}); el original sigue intacto.'
        finally:e.close()
        raise ValueError(mensaje) from None
    except (OSError,TimeoutError,urllib.error.URLError):raise ValueError('No se pudo completar la conexión. El original sigue intacto; reintenta sin crear otro vault.') from None

def subir(endpoint,credencial,cuerpo):
    if len(cuerpo)>MAX_ARCHIVO:raise ValueError('La copia supera 128 MiB comprimidos; no se recorta ningún dato.')
    inicio=enviar(endpoint,credencial,json.dumps({'bytes':len(cuerpo),'sha256':hashlib.sha256(cuerpo).hexdigest()}).encode(),{'x-void-subida':'iniciar','content-type':'application/json'})
    if inicio.get('conservado'):return inicio
    identificador=inicio.get('subida','');recibidos=inicio.get('recibidos')
    total=(len(cuerpo)+TAM_PARTE-1)//TAM_PARTE
    if not re.fullmatch(r'[0-9a-f]{32}',identificador) or inicio.get('tamano_parte')!=TAM_PARTE or not isinstance(recibidos,int) or not 0<=recibidos<=total:
        raise ValueError('La preparación de subida no es válida; el original se conserva.')
    for i in range(recibidos,total):
        enviar(endpoint,credencial,cuerpo[i*TAM_PARTE:(i+1)*TAM_PARTE],{'x-void-subida':'trozo','x-void-subida-id':identificador,'x-void-indice':str(i)})
        if (i+1)%20==0 or i+1==total:print(f'Subida privada: {i+1}/{total} partes; pendiente de comprobar y activar.',flush=True)
    return enviar(endpoint,credencial,b'',{'x-void-subida':'terminar','x-void-subida-id':identificador})

def conectar(vault,confirmado=False,alojado=False):
    vault=Path(vault).resolve()
    if not (vault/'.git').is_dir():raise ValueError('Abre esta herramienta dentro de tu vault con git local.')
    rutas=[] if alojado else archivos(vault)
    print('Se abrirá la caja actual.' if alojado else f'Copia privada completa: {len(rutas)} archivos, incluidos ignorados, personalizaciones, archivos de acceso y el historial git. Conserva el original. No sincroniza cambios posteriores con el PC.')
    print('No se excluyen datos por estar ignorados por Git. Los secretos locales también viajarán en la copia privada completa, sin imprimirse. El operador puede acceder al contenido alojado. Cada dueño debe autorizar sus datos y revisar los documentos de terceros incluidos.')
    if not alojado:
        print(f'Tamaño de contenidos: {sum((vault/r).stat().st_size for r in rutas)} bytes. Enlaces internos conservados en el manifiesto: {len(estructura(vault)[1])}.')
    if not confirmado:
        print('No se ha enviado nada. Revisa el alcance y repite con --confirmar-alojamiento si lo autorizas.')
        return None
    p=vault/'.void/llave'
    if p.is_symlink() or not p.is_file():raise ValueError('Este vault debe estar registrado en Void. La llave se queda privada.')
    credencial=p.read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'vv_[A-Za-z0-9_-]{43}',credencial):raise ValueError('La llave propia de Void no tiene el formato esperado.')
    endpoint=os.environ.get('VOID_RED','https://red.vaultvoid.app').rstrip('/')
    if endpoint!='https://red.vaultvoid.app' and not re.fullmatch(r'http://(?:localhost|127\.0\.0\.1)(?::\d+)?',endpoint):raise ValueError('Solo se conecta a Void o a una prueba local.')
    cuerpo=json.dumps({'pass':getpass.getpass('Contraseña de la caja ya alojada (no se imprime): ')}).encode() if alojado else empaquetar(vault,rutas)
    datos=enviar(endpoint,credencial,cuerpo,{'content-type':'application/json','x-void-origen':'alojado'}) if alojado else subir(endpoint,credencial,cuerpo)
    if not alojado:
        esperado=hashlib.sha256(cuerpo).hexdigest()
        if datos.get('archivo_sha256')!=esperado:
            raise ValueError('El espacio conserva otra copia: no se ha incorporado este original completo. No se sobrescribe; hay que revisar la caja previa.')
        descarga=urllib.request.Request(endpoint+'/v1/alojar/archivo',headers={'authorization':'Bearer '+credencial,'user-agent':USER_AGENT})
        try:
            with urllib.request.build_opener(SinRedireccion()).open(descarga,timeout=180) as r:recuperado=r.read(MAX_ARCHIVO+1)
        except (OSError,TimeoutError,urllib.error.URLError):
            raise ValueError('La copia fue enviada, pero falta verificar su recuperación. El original se conserva; reintenta sin crear otro vault.') from None
        if len(recuperado)>MAX_ARCHIVO or hashlib.sha256(recuperado).hexdigest()!=esperado:
            raise ValueError('La copia recuperada no coincide con la enviada. No se declara terminada la migración; el original se conserva.')
        comprobacion=verificar(recuperado)
        print(f"Copia alojada recuperada y verificada: {comprobacion['archivos']} archivos y {comprobacion['enlaces']} enlaces internos; identidad conservada.")
    if not re.fullmatch(r've_[A-Za-z0-9_-]{43}',datos.get('enlace','')):raise ValueError('La respuesta de conexión no es válida.')
    print('Abre https://vaultvoid.app/conectar-vault y pega este código temporal. Caduca en diez minutos; no lo compartas:')
    print(datos['enlace'])
    print('En la página guardarás un código privado nuevo para volver. El alias y la huella publicados no cambian.')
    return datos

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vault',default='.');p.add_argument('--confirmar-alojamiento',action='store_true');p.add_argument('--ya-alojado',action='store_true');a=p.parse_args()
    try:conectar(a.vault,a.confirmar_alojamiento,a.ya_alojado)
    except (ValueError,OSError,subprocess.CalledProcessError) as e:print('No se conectó: '+str(e));return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
