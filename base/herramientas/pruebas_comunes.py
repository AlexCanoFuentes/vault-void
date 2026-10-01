#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de los candados comunes (herramientas/candados_comunes.py).

Viene de la base de Void: las pruebas, el sabotaje y sus ayudas están sacados tal cual de
herramientas/pruebas.py de los vaults. No se cambia aquí; se cambia en la base.

Uso:
  python3 herramientas/pruebas_comunes.py             corre las pruebas
  python3 herramientas/pruebas_comunes.py --sabotaje  afloja cada candado y mira si las pruebas lo cazan
"""
import importlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import candados_comunes as revisar  # noqa: E402  (con el nombre que usan las pruebas de los vaults)


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class Candados(Base):
    def test_codex_escribe_solo_en_la_carpeta_sin_internet_y_pregunta(self):
        self.assertEqual(revisar.candados_codex(RAIZ), [])
        c = revisar.leer_codex(RAIZ)
        self.assertEqual(c[""]["sandbox_mode"], "workspace-write")
        self.assertIs(c["sandbox_workspace_write"]["network_access"], False)

    def test_caza_codex_con_acceso_total_e_internet(self):
        (self.dir / ".codex").mkdir()
        (self.dir / ".codex" / "config.toml").write_text(
            'sandbox_mode = "danger-full-access"  # todo\napproval_policy = "never"\n'
            'sandbox_workspace_write.network_access = true\n', encoding="utf-8")
        abiertos = revisar.candados_codex(self.dir)
        self.assertTrue(any("sandbox_mode" in a for a in abiertos))
        self.assertTrue(any("approval_policy" in a for a in abiertos))
        self.assertTrue(any("network_access" in a for a in abiertos))

    def test_sin_config_de_codex_se_avisa(self):
        self.assertTrue(any("no está" in a for a in revisar.candados_codex(self.dir)))

    def test_claude_y_codex_leen_las_mismas_reglas(self):
        self.assertEqual(revisar.reglas_compartidas(RAIZ), [])

    def test_caza_claude_sin_las_reglas_de_agents(self):
        (self.dir / "AGENTS.md").write_text("# reglas\n", encoding="utf-8")
        (self.dir / "CLAUDE.md").write_text("Lee `@AGENTS.md` antes de nada.\n", encoding="utf-8")
        abiertos = revisar.reglas_compartidas(self.dir)
        self.assertEqual(len(abiertos), 1)
        self.assertIn("@AGENTS.md", abiertos[0])
        (self.dir / "AGENTS.md").write_text("  \n", encoding="utf-8")
        self.assertEqual(len(revisar.reglas_compartidas(self.dir)), 2)


def _codex_abierto(raiz):
    return {"": {"sandbox_mode": "danger-full-access", "approval_policy": "never"},
            "sandbox_workspace_write": {"network_access": True}}


def _claude_sin_import(original):
    def leer(raiz, nombre):
        texto = original(raiz, nombre)
        return texto.replace("@AGENTS.md", "") if nombre == "CLAUDE.md" else texto
    return leer


SABOTAJES = [
    ("Codex pasa a acceso total, sin pedir permiso y con internet",
     lambda: setattr(revisar, "leer_codex", _codex_abierto)),
    ("CLAUDE.md deja de importar AGENTS.md (Claude sin las reglas del vault)",
     lambda: setattr(revisar, "leer_texto", _claude_sin_import(revisar.leer_texto))),
]


def correr(verbosidad=0):
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    flujo = io.StringIO()
    res = unittest.TextTestRunner(stream=flujo, verbosity=verbosidad).run(suite)
    return res, flujo.getvalue()


def restaurar():
    importlib.reload(revisar)


def sabotaje():
    print("Sabotaje: rompo el programa a propósito, una cosa cada vez, y miro si las pruebas lo cazan.")
    print("Una prueba que nunca viste fallar no demuestra nada.\n")
    sin_cazar = 0
    for i, (que, romper) in enumerate(SABOTAJES, 1):
        romper()
        try:
            res, _ = correr()
        finally:
            restaurar()
        caidas = [t.id().split(".")[-1] for t, _ in res.failures + res.errors]
        print(f"  {i}. {que}")
        if caidas:
            print(f"     CAZADO por {len(caidas)} prueba(s): {', '.join(caidas)}")
        else:
            sin_cazar += 1
            print("     NO CAZADO: ninguna prueba se dio cuenta. Ese candado no cierra.")
    res, _ = correr()
    print()
    if sin_cazar:
        print(f"{sin_cazar} sabotaje(s) sin cazar: hace falta una prueba que los mire.")
        return 1
    if not res.wasSuccessful():
        print("Los sabotajes se cazan, pero el programa sin romper ya falla: corre las pruebas normales.")
        return 1
    print(f"Los {len(SABOTAJES)} sabotajes cazados, y sin sabotaje las {res.testsRun - len(res.skipped)} pruebas pasan.")
    return 0


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    if argv == ["--sabotaje"]:
        return sabotaje()
    res, texto = correr(verbosidad=1)
    saltadas = len(res.skipped)
    if res.wasSuccessful():
        motivos = sorted({motivo for _, motivo in res.skipped})
        extra = f" ({saltadas} saltadas: {'; '.join(motivos)})" if saltadas else ""
        print(f"OK: pasan las {res.testsRun - saltadas} pruebas{extra}.")
        return 0
    print(texto)
    print(f"FALLAN {len(res.failures) + len(res.errors)} de {res.testsRun} pruebas. No guardes hasta arreglarlo.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
