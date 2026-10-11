"""El cliente solo anuncia éxito tras recuperar la misma copia; red sustituida explícitamente."""
import contextlib,hashlib,importlib.util,io,json,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def modulo(nombre,ruta):
    s=importlib.util.spec_from_file_location(nombre,ruta);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=modulo('cliente',root/'conectar_vault.py');fixtures=modulo('fixtures',root/'pruebas/pruebas_conectar_vault.py')
with tempfile.TemporaryDirectory(prefix='void-recuperar-') as d:
    with contextlib.redirect_stdout(io.StringIO()):f=fixtures.fabricar(Path(d))[0]
    v=Path(d)/f['alias'];paquete=Path(f['archivo']).read_bytes();original=m.empaquetar
    m.empaquetar=lambda *a,**k:paquete
    class Red:
        def __init__(self,modo):self.modo=modo;self.partes=[]
        def open(self,req,timeout=180):
            assert req.get_header('Authorization')=='Bearer '+f['llave']
            accion=req.get_header('X-void-subida')
            if req.full_url.endswith('/archivo'):
                return io.BytesIO(paquete if self.modo!='alterado' else paquete+b'cambio')
            if accion=='iniciar':
                b=json.loads(req.data);assert b['bytes']==len(paquete) and b['sha256']==hashlib.sha256(paquete).hexdigest()
                r={'subida':'a'*32,'recibidos':0,'tamano_parte':m.TAM_PARTE}
            elif accion=='trozo':self.partes.append(req.data);r={'recibidos':len(self.partes)}
            else:
                assert b''.join(self.partes)==paquete
                r={'importado':True,'archivo_sha256':hashlib.sha256(paquete).hexdigest() if self.modo!='otra-copia' else '0'*64,'enlace':'ve_'+'t'*43}
            return io.BytesIO(json.dumps(r).encode())
    for modo in ['correcto','alterado','otra-copia']:
        red=Red(modo);m.urllib.request.build_opener=lambda *a:red;salida=io.StringIO()
        with contextlib.redirect_stdout(salida):
            if modo=='correcto':assert m.conectar(v,confirmado=True)['importado']
            else:
                try:m.conectar(v,confirmado=True);raise AssertionError('Se declaró éxito con otra copia')
                except ValueError:pass
        assert f['llave'] not in salida.getvalue() and 'DATO_INVENTADO' not in salida.getvalue()
        if modo!='correcto':assert 've_' not in salida.getvalue() and 'recuperada y verificada' not in salida.getvalue()
    assert (v/'nota-sin-commit.md').is_file()
print('✓ El cliente comprueba subida y recuperación; rechaza copia alterada o caja diferente sin anunciar éxito ni imprimir secretos inventados.')
