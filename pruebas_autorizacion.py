import importlib.util
from pathlib import Path
import unittest
raiz = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("void", raiz / "void.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
class Autorizacion(unittest.TestCase):
    def mensaje(self, **cambios):
        d = dict(v=1, tipo="PETICION", asunto="Prueba", cuerpo="Revisar este documento", devuelve="Un informe", responde_a=None, autoriza="Prueba · persona")
        d.update(cambios)
        return d
    def test_rechaza_sin_autorizacion(self):
        d = self.mensaje(); del d["autoriza"]
        self.assertIsNotNone(v.problema_mensaje(d))
    def test_rechaza_autorizacion_de_agente(self):
        self.assertIsNotNone(v.problema_mensaje(self.mensaje(autoriza="Prueba · agente")))
    def test_acepta_declaracion_de_persona(self):
        self.assertIsNone(v.problema_mensaje(self.mensaje()))
    def test_todos_los_tipos_declaran_que_devuelven(self):
        self.assertIsNotNone(v.problema_mensaje(self.mensaje(tipo="AVISO", devuelve=None)))
    def test_nombre_vacio_no_autoriza(self):
        self.assertIsNotNone(v.problema_mensaje(self.mensaje(autoriza=" · persona")))
    def test_respuesta_identifica_original(self):
        self.assertIsNotNone(v.problema_mensaje(self.mensaje(tipo="RESPUESTA")))
        self.assertIsNone(v.problema_mensaje(self.mensaje(tipo="RESPUESTA", responde_a=1)))
    def test_numero_original_no_admite_booleanos_ni_cadenas(self):
        for n in (True, False, "1", -1, 0):
            with self.subTest(numero=n):
                self.assertIsNotNone(v.problema_mensaje(self.mensaje(responde_a=n)))
    def test_secretos_en_cualquier_campo(self):
        falsos = ["sk-" + "A"*16, "github_pat_" + "A"*20, "xoxb-" + "A"*12,
                  "sbp_" + "A"*20, "ghp_" + "A"*20, "AKIA" + "A"*16,
                  "eyJ" + "A"*12 + "." + "A"*12 + "." + "A"*12,
                  "ES00" + "0"*20, 'token="' + "A"*20 + '"']
        for secreto in falsos:
            for campo in ("asunto", "cuerpo", "devuelve", "autoriza"):
                dato = secreto + " · persona" if campo == "autoriza" else secreto
                with self.subTest(campo=campo, patron=falsos.index(secreto)):
                    self.assertIsNotNone(v.problema_mensaje(self.mensaje(**{campo:dato})))
    def test_archivo_antiguo_conserva_lectura_sin_inventar_autorizacion(self):
        d = self.mensaje(tipo="AVISO", devuelve=None); del d["autoriza"]
        self.assertIsNone(v.problema_mensaje(d, antiguo=True))
        self.assertIsNotNone(v.problema_mensaje(d))
if __name__ == "__main__": unittest.main()
