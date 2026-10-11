import importlib.util,subprocess,tempfile,io,tarfile,sqlite3,json,hashlib,contextlib
from pathlib import Path
s=importlib.util.spec_from_file_location('cliente',Path(__file__).resolve().parents[1]/'conectar_vault.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.TemporaryDirectory(prefix='void-completo-') as td:
 v=Path(td)/'vault';v.mkdir()
 def git(*a,cwd=v):return subprocess.check_output(['git',*a],cwd=cwd,stderr=subprocess.DEVNULL)
 git('init','-b','main');(v/'.gitignore').write_text('ignorado/\n.env\n.void/\n.agente/\n');(v/'README.md').write_text('Vault original inventado\n');git('add','.gitignore','README.md');git('-c','user.name=Codex','-c','user.email=codex@lexlabs.local','commit','-m','fixture: historial')
 (v/'.void').mkdir();(v/'.void/llave').write_text('vv_'+'i'*43);(v/'.env').write_text('SECRETO_INVENTADO=privado\n');(v/'ignorado').mkdir();(v/'ignorado/personal.md').write_text('Contenido ignorado indispensable\n');(v/'ignorado/vacio').mkdir();(v/'sin-commit.md').write_text('Dato sin commit\n');(v/'personalizacion').symlink_to('ignorado',target_is_directory=True)
 (v/'.agente').mkdir();db=sqlite3.connect(v/'.agente/conversacion.db');db.execute('PRAGMA journal_mode=WAL');db.execute('CREATE TABLE mensajes(texto)');db.execute("INSERT INTO mensajes VALUES('Conversación inventada')");db.commit()
 antes={str(p.relative_to(v)):hashlib.sha256(p.read_bytes()).hexdigest() for p in v.rglob('*') if p.is_file()};head=git('rev-parse','HEAD').strip()
 salida=io.StringIO()
 with contextlib.redirect_stdout(salida):m.conectar(v)
 assert 'SECRETO_INVENTADO' not in salida.getvalue() and 'No se ha enviado nada' in salida.getvalue()
 rutas=m.archivos(v);assert all(p in rutas for p in ['.env','ignorado/personal.md','sin-commit.md','personalizacion/personal.md','.git/config','.void/llave'])
 paquete=m.empaquetar(v,rutas);ver=m.verificar(paquete);assert ver['archivos']==len(rutas) and ver['enlaces']==1
 salida_archivo=Path('/tmp/void_completo_fixture.tgz');salida_archivo.write_bytes(paquete)
 restaurado=Path(td)/'restaurado';restaurado.mkdir()
 with tarfile.open(fileobj=io.BytesIO(paquete),mode='r:gz') as tar:
  assert all(m.isfile() or m.isdir() for m in tar.getmembers());tar.extractall(restaurado,filter='data')
  meta=json.load(tar.extractfile(next(p for p in tar.getnames() if p.endswith('/manifiesto.json'))))
 assert git('rev-parse','HEAD',cwd=restaurado).strip()==head
 for r,d in meta['archivos'].items():assert hashlib.sha256((restaurado/d['ruta_archivo']).read_bytes()).hexdigest()==d['sha256']
 assert (restaurado/'ignorado/vacio').is_dir()
 with sqlite3.connect(restaurado/'.agente/conversacion.db') as copia:assert copia.execute('SELECT texto FROM mensajes').fetchone()[0]=='Conversación inventada'
 for p,h in antes.items():
  if not p.endswith('-shm'):assert hashlib.sha256((v/p).read_bytes()).hexdigest()==h,p
 assert meta['enlaces']=={'personalizacion':'ignorado'}
 # Restaurar la forma original de enlaces en una copia de prueba, después de comparar contenido.
 import shutil
 shutil.rmtree(restaurado/'personalizacion');(restaurado/'personalizacion').symlink_to(meta['enlaces']['personalizacion'],target_is_directory=True)
 assert (restaurado/'personalizacion/personal.md').read_text()==(v/'ignorado/personal.md').read_text()
 (v/'externo').symlink_to(Path(td)/'fuera');(Path(td)/'fuera').write_text('No pertenece al vault')
 try:m.archivos(v);raise AssertionError('Se aceptó un enlace externo')
 except ValueError:pass
 (v/'externo').unlink();(v/'ciclo').symlink_to('.')
 try:m.archivos(v);raise AssertionError('Se aceptó un enlace circular')
 except ValueError:pass
 db.close()
 print('✓ Copia y restauración completas: ignorados, secretos inventados sin imprimir, historial, nota sin commit, enlaces internos, directorio vacío y conversación SQLite con WAL. Original intacto. Rechaza enlaces externos y ciclos.')
