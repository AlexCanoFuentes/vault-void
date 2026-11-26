#!/usr/bin/env python3
"""Pruebas y sabotajes del KERNEL común. No usa datos ni cuentas reales."""
import contextlib
import copy
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kernel


def encargo(notas=None):
    notas = notas or dict(clarity=18, scope=18, context=13, risk=12, validation=13, priority=8)
    return dict(objeto="Prueba de una herramienta", alcance="Solo el prototipo local",
                fuentes="proyectos/prueba.md", cambios=["construccion"],
                stack=[dict(pieza="datos", eleccion="SQLite", alternativas=["ficheros JSON"], porque="Consultas y escrituras seguras")],
                dimensiones={n:dict(nota=v, porque="Valoración de prueba con límites explícitos")
                             for n,v in notas.items()})


class Kernel(unittest.TestCase):
    def test_disparadores_y_excepciones(self):
        for c in ("construccion", "ampliacion", "permisos", "datos", "migracion", "salida", "publicacion", "base", "contradiccion"):
            self.assertTrue(kernel.necesario([c]), c)
        for c in ("consulta", "captura", "correccion-menor"):
            self.assertFalse(kernel.necesario([c]), c)
        self.assertTrue(kernel.necesario(["correccion-menor", "permisos"]))

    def test_evento_desconocido_no_se_toma_por_inocuo(self):
        for c in ([], ["otro"], [{}], [[]], "datos", None):
            with self.assertRaises(ValueError): kernel.necesario(c)

    def test_notas_y_dimension_debil(self):
        r=kernel.evaluar(encargo())
        self.assertEqual(r['total'],82)
        self.assertEqual(r['dimension_mas_debil'],'priority')
        self.assertTrue(r['puede_construir'])

    def test_umbral_duro(self):
        for total, estado in ((59,'RECHAZADO'),(60,'CONDICIONAL'),(79,'CONDICIONAL'),(80,'EXECUTE')):
            d=encargo(dict(clarity=20, scope=20, context=total-55, risk=10, validation=5, priority=0))
            if total>70:
                d=encargo(dict(clarity=20,scope=20,context=15,risk=10,validation=total-65,priority=0))
            self.assertEqual(kernel.evaluar(d)['estado'],estado)

    def test_riesgo_bajo_para_aunque_el_total_pase(self):
        d=encargo(dict(clarity=20,scope=20,context=15,risk=8,validation=15,priority=15))
        r=kernel.evaluar(d)
        self.assertEqual(r['estado'],'REVISION_DE_RIESGO')
        self.assertFalse(r['puede_construir'])

    def test_no_acepta_notas_fuera_de_rango_booleanas_ni_decimales(self):
        for n in (-1,21,True,19.9):
            d=encargo();d['dimensiones']['clarity']['nota']=n
            with self.assertRaises(ValueError):kernel.evaluar(d)

    def test_no_acepta_dimension_inventada_ni_falta_de_razon(self):
        d=encargo();d['dimensiones']['otra']=dict(nota=1,porque='x')
        with self.assertRaises(ValueError):kernel.evaluar(d)
        d=encargo();d['dimensiones']['scope']['porque']='  '
        with self.assertRaises(ValueError):kernel.evaluar(d)

    def test_entrada_incompleta_no_pasa(self):
        for campo in ('objeto','alcance','fuentes','cambios','dimensiones'):
            d=encargo();del d[campo]
            with self.assertRaises(ValueError):kernel.evaluar(d)

    def test_registro_anade_y_no_sustituye(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=encargo();r=kernel.evaluar(d)
            p=kernel.registrar(tmp,d,r);antes=p.read_bytes()
            kernel.registrar(tmp,d,r)
            self.assertTrue(p.read_bytes().startswith(antes))
            self.assertEqual(len(p.read_text().splitlines()),2)
            dato=json.loads(p.read_text().splitlines()[0])
            self.assertIn('fecha',dato)
            self.assertEqual(dato['evaluacion']['alcance'],d['alcance'])

    def test_registro_roto_se_conserva(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'criterio/kernel.jsonl';p.parent.mkdir();p.write_text('roto\n')
            with self.assertRaises(ValueError):kernel.registrar(tmp,encargo(),kernel.evaluar(encargo()))
            self.assertEqual(p.read_text(),'roto\n')

    def test_construir_pide_stack_con_alternativas_y_porque(self):
        for roto in (None, [], [{}], [dict(pieza="datos", eleccion="SQLite", porque="x")],
                     [dict(pieza="datos", eleccion="SQLite", alternativas=[], porque="x")],
                     [dict(pieza="datos", eleccion="SQLite", alternativas=["JSON"], porque=" ")],
                     [dict(pieza="datos", eleccion="A", alternativas=["B"], porque="x"), dict(pieza="datos", eleccion=" a ", alternativas=["D"], porque="y")]):
            d=encargo();d['stack']=roto
            if roto is None: del d['stack']
            with self.assertRaises(ValueError): kernel.evaluar(d)
        d=encargo();del d['stack'];d['cambios']=['permisos']
        self.assertTrue(kernel.evaluar(d)['puede_construir'])   # sin construir, no se pide stack

    def test_las_piezas_son_una_lista_cerrada(self):
        d=encargo();d['stack'][0]['pieza']='Persistencia'      # el truco de cambiar el nombre
        with self.assertRaises(ValueError): kernel.evaluar(d)
        d=encargo();d['stack'][0]['pieza']='otra'
        with self.assertRaises(ValueError): kernel.evaluar(d)  # «otra» sin nombre
        d['stack'][0]['nombre']=' Datos '                       # el truco de «otra» con el nombre de una pieza
        with self.assertRaises(ValueError): kernel.evaluar(d)
        d['stack'][0]['nombre']='Colas'
        self.assertTrue(kernel.evaluar(d)['puede_construir'])
        d=encargo();d['stack'][0]['para']={'componente':'cache'}  # «para» que no es texto rompía la consulta
        with self.assertRaises(ValueError): kernel.evaluar(d)

    def test_un_stack_presente_se_valida_aunque_el_cambio_no_lo_pida(self):
        d=encargo();d['cambios']=['permisos'];d['stack']=[{}]
        with self.assertRaises(ValueError): kernel.evaluar(d)
        antes={'datos':[dict(pieza='datos',eleccion='Postgres',porque='p',fecha='2026-11-01',objeto='otra',para='')]}
        d=encargo();d['cambios']=['permisos']
        with self.assertRaises(ValueError): kernel.evaluar(d, antes)   # tampoco se cuela otra elección por «permisos»

    def test_separarse_de_lo_elegido_antes_exige_decir_por_que(self):
        antes={'datos':[dict(pieza='datos',eleccion='Postgres',porque='p',fecha='2026-11-01T00:00:00',objeto='otra',para='')]}
        with self.assertRaises(ValueError): kernel.evaluar(encargo(), antes)
        d=encargo();d['stack'][0]['distinto_porque']='Una sola máquina, sin servidor'
        self.assertTrue(kernel.evaluar(d, antes)['puede_construir'])
        d=encargo();d['stack'][0]['eleccion']=' postgres '
        self.assertTrue(kernel.evaluar(d, antes)['puede_construir'])   # lo mismo que antes no pide nada

    def test_el_registro_recuerda_solo_lo_aprobado_y_lo_aplica(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);d=encargo();kernel.registrar(raiz,d,kernel.evaluar(d))
            rechazada=encargo(dict(clarity=5,scope=5,context=5,risk=5,validation=5,priority=5));rechazada['stack'][0]['eleccion']='Mongo'
            kernel.registrar(raiz,rechazada,kernel.evaluar(rechazada))
            with (raiz/'criterio/kernel.jsonl').open('a') as f: f.write(json.dumps(dict(fecha='x',evaluacion=dict(objeto='vieja')))+'\n')
            self.assertEqual([x['eleccion'] for x in kernel.elecciones(raiz)['datos']],['SQLite'])   # Mongo, rechazada, no cuenta
            otro=encargo();otro['stack'][0]['eleccion']='Postgres';(raiz/'e.json').write_text(json.dumps(otro))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(kernel.main(['evaluar','e.json','--registrar'],raiz),2)
            salida=io.StringIO()
            with contextlib.redirect_stdout(salida): self.assertEqual(kernel.main(['stack','dat'],raiz),0)
            self.assertIn('datos · SQLite',salida.getvalue())

    def test_una_construccion_solo_vale_registrada(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);(raiz/'e.json').write_text(json.dumps(encargo()))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(kernel.main(['evaluar','e.json'],raiz),5)
                self.assertEqual(kernel.main(['evaluar','e.json','--registrar'],raiz),0)

    def test_no_escribe_fuera_ni_a_traves_de_enlace(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp)/'vault';raiz.mkdir();fuera=Path(tmp)/'fuera';fuera.mkdir()
            (raiz/'criterio').symlink_to(fuera,target_is_directory=True)
            with self.assertRaises(ValueError):kernel.registrar(raiz,encargo(),kernel.evaluar(encargo()))
            self.assertEqual(list(fuera.iterdir()),[])
            with self.assertRaises(ValueError):kernel.ruta_local(raiz,'../fuera/a.json')

    def test_cli_devuelve_no_cero_si_no_permite_construir(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);p=raiz/'encargo.json'
            d=encargo();d['dimensiones']['clarity']['nota']=15 # 79
            p.write_text(json.dumps(d))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(kernel.main(['evaluar','encargo.json','--registrar'],raiz),3)
            self.assertTrue((raiz/'criterio/kernel.jsonl').is_file())


def correr():
    return unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromTestCase(Kernel))


def sabotaje():
    if not correr().wasSuccessful():
        print('Las pruebas ya fallan sin sabotaje.');return 1
    original=kernel.necesario
    original_eval=kernel.evaluar
    def sin_riesgo(d, anteriores=None):
        r=original_eval(d, anteriores)
        if r['total']>=80:r.update(estado='EXECUTE',puede_construir=True)
        return r
    def redondea(d, anteriores=None):
        dato=copy.deepcopy(d)
        if sum(v['nota'] for v in dato['dimensiones'].values())==79:
            dato['dimensiones']['priority']['nota']+=1
        return original_eval(dato, anteriores)
    original_stack=kernel.revisar_stack
    original_piezas=kernel.PIEZAS;original_elecciones=kernel.elecciones
    class _Todo(tuple):
        def __contains__(self, x): return True
        def __iter__(self): return iter(original_piezas)
    def _con_rechazadas(raiz):
        destino=kernel.ruta_local(raiz,'criterio/kernel.jsonl');hechas={}
        if not destino.exists(): return hechas
        for linea in destino.read_text(encoding='utf-8').splitlines():
            a=json.loads(linea);ev=a.get('evaluacion') or {}
            for s in ev.get('stack') or []:
                if isinstance(s,dict) and s.get('eleccion'): hechas.setdefault(kernel._clave(s),[]).append(dict(s,fecha='',objeto=''))
        return hechas
    def solo_la_lista(d, anteriores):
        original_stack(d, {})
    ataques=[('no activa KERNEL',lambda:setattr(kernel,'necesario',lambda cambios:False)),
             ('no pide el stack',lambda:setattr(kernel,'revisar_stack',lambda d,anteriores:None)),
             ('acepta piezas con cualquier nombre',lambda:setattr(kernel,'PIEZAS',_Todo())),
             ('cuenta también lo rechazado',lambda:setattr(kernel,'elecciones',_con_rechazadas)),
             ('no compara con lo elegido antes',lambda:setattr(kernel,'revisar_stack',solo_la_lista)),
             ('ignora riesgo bajo',lambda:setattr(kernel,'evaluar',sin_riesgo)),
             ('redondea 79 a 80',lambda:setattr(kernel,'evaluar',redondea))]
    for nombre,romper in ataques:
        romper()
        try:r=correr()
        finally:kernel.necesario=original;kernel.evaluar=original_eval;kernel.revisar_stack=original_stack;kernel.PIEZAS=original_piezas;kernel.elecciones=original_elecciones
        if r.wasSuccessful():print('NO CAZADO: '+nombre);return 1
        print('CAZADO: '+nombre)
    if not correr().wasSuccessful():return 1
    print('OK: las pruebas cazan los {} sabotajes.'.format(len(ataques)));return 0


if __name__=='__main__':
    if sys.argv[1:]==['--sabotaje']:sys.exit(sabotaje())
    r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Kernel))
    sys.exit(0 if r.wasSuccessful() else 1)
