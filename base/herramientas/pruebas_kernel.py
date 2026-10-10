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
    def sin_riesgo(d):
        r=original_eval(d)
        if r['total']>=80:r.update(estado='EXECUTE',puede_construir=True)
        return r
    def redondea(d):
        dato=copy.deepcopy(d)
        if sum(v['nota'] for v in dato['dimensiones'].values())==79:
            dato['dimensiones']['priority']['nota']+=1
        return original_eval(dato)
    ataques=[('no activa KERNEL',lambda:setattr(kernel,'necesario',lambda cambios:False)),
             ('ignora riesgo bajo',lambda:setattr(kernel,'evaluar',sin_riesgo)),
             ('redondea 79 a 80',lambda:setattr(kernel,'evaluar',redondea))]
    for nombre,romper in ataques:
        romper()
        try:r=correr()
        finally:kernel.necesario=original;kernel.evaluar=original_eval
        if r.wasSuccessful():print('NO CAZADO: '+nombre);return 1
        print('CAZADO: '+nombre)
    if not correr().wasSuccessful():return 1
    print('OK: las pruebas cazan los {} sabotajes.'.format(len(ataques)));return 0


if __name__=='__main__':
    if sys.argv[1:]==['--sabotaje']:sys.exit(sabotaje())
    r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Kernel))
    sys.exit(0 if r.wasSuccessful() else 1)
