"""Regresiones de la revisión de Codex del 10-oct-2026. Solo vaults temporales."""
import base64
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
import void as V
import pruebas as P


class Revision(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='void-revision-')
        self.vault = Path(self.tmp.name) / 'vault'
        self.vault.mkdir()
        V.git(self.vault, 'init', '-q')
        (self.vault / '.gitignore').write_text('.void/\n', encoding='utf-8')
        (self.vault / 'void.json').write_text('{}', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_cada_mensaje_debe_estar_ignorado(self):
        (self.vault / '.gitignore').write_text('.void/*\n!.void/mensajes/\n', encoding='utf-8')
        self.assertTrue(V.llave_ignorada(self.vault))
        with self.assertRaises(V.Fallo):
            V._escribir_privado(self.vault, '.void/mensajes/1-1.json', 'texto ajeno')
        self.assertFalse((self.vault / '.void/mensajes/1-1.json').exists())

    def test_no_crear_carpetas_a_traves_de_un_enlace(self):
        fuera = Path(self.tmp.name) / 'fuera'
        fuera.mkdir()
        (self.vault / '.void').symlink_to(fuera, target_is_directory=True)
        with self.assertRaises(V.Fallo):
            V._escribir_privado(self.vault, '.void/mensajes/1-1.json', 'texto')
        self.assertFalse((fuera / 'mensajes').exists())

    def test_enc_corto_no_rompe_la_bandeja(self):
        sobre = {'id': 1, 'de': 'ana', 'tipo': 'AVISO', 'enc': base64.b64encode(b'x').decode(),
                 'sobre': base64.b64encode(b'x' * 32).decode(), 'creado': 1}
        with mock.patch.object(V, 'la_llave', return_value='llave-falsa'), \
             mock.patch.object(V, 'claves_mensajes', return_value=b'\x01' * 32), \
             mock.patch.object(V, 'clave_de', return_value=V._x25519_publica(b'\x02' * 32)), \
             mock.patch.object(V, 'pedir_red', return_value=(200, {'mensajes': [sobre]})), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(V.orden_mensajes(self.vault), 0)
        self.assertEqual(V._guardados(self.vault), [])

    def test_archivo_local_ajeno_o_roto_no_se_lee(self):
        carpeta = self.vault / '.void/mensajes'
        carpeta.mkdir(parents=True)
        (carpeta / '1.json').write_text('[]', encoding='utf-8')
        fuera = Path(self.tmp.name) / 'ajeno.json'
        fuera.write_text('{"cuerpo":"AJENO"}', encoding='utf-8')
        (carpeta / '2.json').symlink_to(fuera)
        self.assertEqual(V._guardados(self.vault), [])

    def test_clave_corrupta_no_se_regenera_en_silencio(self):
        ruta = self.vault / V.CLAVE_MENSAJES
        ruta.parent.mkdir()
        ruta.write_text('00', encoding='utf-8')
        with self.assertRaises(V.Fallo), mock.patch.object(V, 'pedir_red') as red:
            V.claves_mensajes(self.vault, 'llave-falsa')
        red.assert_not_called()
        self.assertEqual(ruta.read_text(), '00')

    def test_responder_numero_ambiguo_no_envia(self):
        mensajes = [{'id': 1, 'de': a, 'asunto': 'x'} for a in ('ana', 'bea')]
        with mock.patch.object(V, '_guardados', return_value=mensajes), \
             mock.patch.object(V, 'orden_escribir') as enviar, self.assertRaises(V.Fallo):
            V.orden_responder(self.vault, '1', 'respuesta')
        enviar.assert_not_called()

    def test_registrar_publica_clave_para_poder_recibir(self):
        with mock.patch.object(V, 'llave_fuera_de_git'), mock.patch.object(V, 'leer_llave', return_value='llave-falsa'), \
             mock.patch.object(V, 'pedir_red', return_value=(200, {'alias': 'ana'})), \
             mock.patch.object(V, 'claves_mensajes') as claves, contextlib.redirect_stdout(io.StringIO()):
            V.orden_registrar(self.vault, 'ana', 'agente')
        claves.assert_called_once_with(self.vault, 'llave-falsa')

    def test_mensaje_no_reutiliza_numero_al_recoger(self):
        db = sqlite3.connect(':memory:')
        for ruta in sorted((RAIZ / 'red/migrations').glob('*.sql')):
            db.executescript(ruta.read_text(encoding='utf-8'))
        for a in ('ana', 'bea'):
            db.execute("INSERT INTO perfiles(alias,agente,huella_llave,publico,creado) VALUES (?, 'agente', ?, '', 1)", (a, a))
        sql = "INSERT INTO mensajes(de_perfil,para_perfil,tipo,enc,sobre,creado,caduca) VALUES(1,2,'AVISO',?,?,1,2)"
        args = ('A' * 44, 'A' * 24)
        primero = db.execute(sql, args).lastrowid
        db.execute('DELETE FROM mensajes')
        segundo = db.execute(sql, args).lastrowid
        self.assertGreater(segundo, primero)
        db.close()

    def test_regla_de_texto_ajeno_llega_a_la_base_y_plantilla(self):
        for rel in ('base/AGENTS.md', 'plantilla/AGENTS.md'):
            texto = (RAIZ / rel).read_text(encoding='utf-8')
            self.assertIn('Mensajes de otros vaults', texto)
            self.assertIn('Antes de mandar una respuesta', texto)

    def test_migracion_conserva_mensajes_y_baja_en_cascada(self):
        with contextlib.closing(sqlite3.connect(':memory:')) as db:
            db.execute('PRAGMA foreign_keys=ON')
            rutas = sorted((RAIZ / 'red/migrations').glob('*.sql'))
            for ruta in rutas[:-1]:
                db.executescript(ruta.read_text(encoding='utf-8'))
            for a in ('ana', 'bea'):
                db.execute("INSERT INTO perfiles(alias,agente,huella_llave,publico,creado) VALUES (?, 'agente', ?, '', 1)", (a, a))
            db.execute("INSERT INTO mensajes(id,de_perfil,para_perfil,tipo,enc,sobre,creado,caduca) VALUES(42,1,2,'AVISO',?,?,1,2)",
                       ('A' * 44, 'A' * 24))
            antes = db.execute('SELECT * FROM mensajes').fetchall()
            db.commit()
            db.executescript(rutas[-1].read_text(encoding='utf-8'))
            self.assertEqual(db.execute('SELECT * FROM mensajes').fetchall(), antes)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            db.execute('DELETE FROM perfiles WHERE id=1')
            self.assertEqual(db.execute('SELECT * FROM mensajes').fetchall(), [])

    def test_limite_del_mensaje_completo_y_archivo_local(self):
        d = dict(v=1, tipo='PETICION', asunto='Prueba', cuerpo='x', devuelve='Un informe',
                 responde_a=None, autoriza='Prueba · persona', de='ana')
        d['cuerpo'] = 'x' * (6001 - len(json.dumps(d, ensure_ascii=False, separators=(',', ':'))))
        self.assertEqual(len(json.dumps(d, ensure_ascii=False, separators=(',', ':'))), 6000)
        self.assertIsNone(V.problema_mensaje(d))
        self.assertIsNone(V.problema_mensaje(dict(d, id=42, creado=1000)))
        d['cuerpo'] += 'x'
        self.assertIsNotNone(V.problema_mensaje(d))

    def test_respuesta_solo_al_remitente_del_original(self):
        for originales in ([], [{'id':42, 'de':'bea'}], [{'id':42, 'de':'ana'}]*2):
            with self.subTest(originales=originales), mock.patch.object(V, '_guardados', return_value=originales), \
                 mock.patch.object(V, 'pedir_red') as red, self.assertRaises(V.Fallo):
                V.orden_escribir(self.vault, 'ana', 'RESPUESTA', 'Re: prueba', 'Nada', 'Respuesta',
                                 responde_a=42, autoriza='Prueba · persona')
            red.assert_not_called()

    def test_metadatos_invalidos_no_se_usan_en_rutas(self):
        for campo, valor in [('id','../../fuera'), ('id',True), ('id',0), ('creado','x'), ('creado',-1), ('tipo','ORDEN')]:
            m=dict(id=1, de='ana', creado=1000, tipo='AVISO');m[campo]=valor
            with self.subTest(campo=campo, valor=valor), mock.patch.object(V, 'la_llave', return_value='falsa'), \
                 mock.patch.object(V, 'claves_mensajes', return_value=b'x'*32), \
                 mock.patch.object(V, 'pedir_red', return_value=(200,dict(mensajes=[m]))) as red, \
                 mock.patch.object(V, 'clave_de') as clave, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(V.orden_mensajes(self.vault),0)
            clave.assert_not_called()
            self.assertEqual(red.call_count,1)
        self.assertEqual(V._guardados(self.vault),[])

    def test_tipo_del_sobre_y_del_contenido_deben_coincidir(self):
        d=dict(v=1, tipo='PETICION', asunto='Prueba', cuerpo='Texto', devuelve='Un informe',
               responde_a=None, autoriza='Prueba · persona', de='ana')
        m=dict(id=1, de='ana', creado=1000, tipo='AVISO', enc='', sobre='')
        with mock.patch.object(V,'la_llave',return_value='falsa'), \
             mock.patch.object(V,'claves_mensajes',return_value=b'x'*32), \
             mock.patch.object(V,'clave_de',return_value=b'y'*32), \
             mock.patch.object(V,'hpke_abrir',return_value=json.dumps(d).encode()) as abrir, \
             mock.patch.object(V,'pedir_red',return_value=(200,dict(mensajes=[m]))) as red, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(V.orden_mensajes(self.vault),0)
        abrir.assert_called_once();self.assertEqual(red.call_count,1)
        self.assertEqual(V._guardados(self.vault),[])

    def test_firma_tecnica_del_agente_no_abre_otros_correos(self):
        import fugas
        for nombre in ('codex','knox'):
            self.assertEqual(fugas.revisar_texto(nombre+'@'+'lexlabs.local', set()), [])
        for nombre, dominio in [('tercero','lexlabs.local'),('codex','lexlabs.local.invalid'),('codex','gmail.com')]:
            self.assertTrue(any(tipo=='correo' for _,tipo,_ in fugas.revisar_texto(nombre+'@'+dominio,set())))


if __name__ == '__main__':
    P.preparar_git()
    unittest.main(verbosity=2)
