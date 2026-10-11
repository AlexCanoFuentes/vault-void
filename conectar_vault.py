#!/usr/bin/env python3
"""Conecta la carpeta real a Void. Sin --confirmar-alojamiento solo muestra el alcance local."""
import argparse
import getpass
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

MAX_ARCHIVO=50*1024*1024
MAX_CLARO=200*1024*1024
EXCLUIR={'node_modules','__pycache__','.venv','venv','.aws','.ssh','.idea'}

def archivos(vault):
    salida=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=vault)
    rutas={p.decode('utf-8') for p in salida.split(b'\0') if p}
    # El historial local y las claves propias de Void también viajan en la copia privada, nunca a un repo.
    for carpeta in ['.git','.void','.agente']:
        base=vault/carpeta
        if base.is_symlink():raise ValueError('Una carpeta privada apunta a otro sitio; prepara un clon completo.')
        if base.is_dir():
            for raiz,dirs,ficheros in os.walk(base,followlinks=False):
                dirs[:]=[d for d in dirs if d not in EXCLUIR and not (Path(raiz)/d).is_symlink()]
                for nombre in ficheros:rutas.add((Path(raiz)/nombre).relative_to(vault).as_posix())
    seleccion=[]
    for ruta in sorted(rutas):
        partes=Path(ruta).parts;nombre=partes[-1];p=vault/ruta
        if any(x in EXCLUIR for x in partes) or nombre=='.env' or nombre.startswith('.env.') or nombre.endswith(('.pem','.key','-wal','-shm')):continue
        if ruta.startswith('.git/hooks/') or ruta in {'.git/config','.git/index.lock','.void/enlace-web.json'}:continue
        if ruta=='.git/objects/info/alternates' or ruta.startswith('.git/worktrees/'):raise ValueError('El historial depende de otra carpeta; usa un clon completo sin worktree.')
        if p.is_symlink():raise ValueError('Hay enlaces simbólicos: prepara una copia con archivos reales antes de alojar.')
        if p.is_file():seleccion.append(ruta)
    if '.git/HEAD' not in seleccion:raise ValueError('Hace falta un vault con git local completo.')
    return seleccion

def empaquetar(vault,rutas):
    if sum((vault/p).stat().st_size for p in rutas)>MAX_CLARO:raise ValueError('La copia supera los 200 MiB descomprimidos del piloto.')
    buf=io.BytesIO()
    with tempfile.TemporaryDirectory(prefix='void-copia-') as temporal:
        with tarfile.open(fileobj=buf,mode='w:gz',format=tarfile.USTAR_FORMAT) as tar:
            for n,ruta in enumerate(rutas):
                p=vault/ruta
                if p.is_symlink() or p.resolve().is_relative_to(vault) is False:raise ValueError('Un archivo ha cambiado de ubicación; vuelve a preparar la copia.')
                if ruta.startswith('.agente/') and p.suffix=='.db':
                    copia=Path(temporal)/str(n)
                    with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as origen,sqlite3.connect(copia) as destino:
                        origen.backup(destino)
                        if destino.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('La conversación no pasó la comprobación de SQLite.')
                    info=tar.gettarinfo(str(copia),arcname=ruta);info.mode=0o600
                    with copia.open('rb') as f:tar.addfile(info,f)
                else:tar.add(p,arcname=ruta,recursive=False)
            config=b'[core]\n\trepositoryformatversion = 0\n\tbare = false\n\tfilemode = true\n'
            if (vault/'.githooks').is_dir():config+=b'\thooksPath = .githooks\n'
            info=tarfile.TarInfo('.git/config');info.size=len(config);info.mode=0o600;tar.addfile(info,io.BytesIO(config))
    datos=buf.getvalue()
    if len(datos)>MAX_ARCHIVO:raise ValueError('La copia supera los 50 MiB comprimidos del piloto.')
    return datos

class SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Void devolvió una redirección: no envío tus datos a otro destino.')

def conectar(vault,confirmado=False,alojado=False):
    vault=Path(vault).resolve()
    if not (vault/'.git').is_dir():raise ValueError('Abre esta herramienta dentro de tu vault con git local.')
    rutas=[] if alojado else archivos(vault)
    print('Se abrirá la caja actual.' if alojado else f'Copia privada: {len(rutas)} archivos y el historial git; conserva el original. No sincroniza cambios posteriores con el PC.')
    print('Excluye archivos .env, .pem y .key, carpetas de dependencias y la configuración del remoto GitHub. Mantiene el historial, las claves propias de Void y sus conversaciones: revisa también lo guardado en commits anteriores. El operador puede acceder al contenido alojado.')
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
    req=urllib.request.Request(endpoint+'/v1/alojar',data=cuerpo,method='POST',headers={'authorization':'Bearer '+credencial,'content-type':'application/json' if alojado else 'application/gzip','x-void-origen':'alojado' if alojado else 'archivo','x-void-consentimiento':'alojar-mi-vault'})
    try:
        with urllib.request.build_opener(SinRedireccion()).open(req,timeout=180) as r:datos=json.loads(r.read(65536))
    except urllib.error.HTTPError as e:
        try:mensaje=json.loads(e.read(65536)).get('error','No se pudo conectar.')
        finally:e.close()
        raise ValueError(mensaje) from None
    except (OSError,TimeoutError,urllib.error.URLError):raise ValueError('No se pudo completar la conexión. El original sigue intacto; reintenta sin crear otro vault.') from None
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
