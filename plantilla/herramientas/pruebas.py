#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de las herramientas del vault.

Uso:
  python3 herramientas/pruebas.py             corre las pruebas
  python3 herramientas/pruebas.py --sabotaje  rompe el programa a propósito, una cosa cada vez,
                                              y comprueba que las pruebas lo cazan

Por qué existe el sabotaje: una prueba que nunca viste fallar no demuestra nada.
Puede estar pasando porque el programa está bien o porque la prueba no mira.

Cada herramienta nueva que añadas a herramientas/ trae aquí sus pruebas y, en SABOTAJES, al
menos una forma de romperla que las pruebas tienen que cazar.
"""
import importlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import revisar  # noqa: E402
import medir  # noqa: E402


# KERNEL viene en la base y se comprueba con la suite normal del vault.
import pruebas_kernel


def load_tests(loader, tests, pattern):
    tests.addTests(loader.loadTestsFromTestCase(pruebas_kernel.Kernel))
    return tests


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# ---------------------------------------------------------------- el montaje

class Montaje(Base):
    def test_el_montaje_no_dejo_huecos(self):
        """Al montar, el agente pone tu nombre y la fecha donde la plantilla dice {{nombre}} y
        {{fecha}}. Si queda alguno, el agente no sabe de quién es el vault."""
        quedan = []
        for p in sorted(RAIZ.rglob("*.md")):
            rel = p.relative_to(RAIZ)
            if ".git" in rel.parts or rel.as_posix() == "proyectos/_plantilla.md":
                continue
            if "{{" in p.read_text(encoding="utf-8"):
                quedan.append(rel.as_posix())
        self.assertEqual(quedan, [], "quedan huecos del montaje ({{nombre}} o {{fecha}}) en estos archivos")

    def test_las_siete_preguntas_siguen_ahi(self):
        """Contestadas o no, las siete preguntas no se borran: lo que no se contestó queda [sin contestar]."""
        texto = (RAIZ / "criterio" / "apuntes.md").read_text(encoding="utf-8")
        self.assertEqual(texto.count("*Pregunta:*"), 7)

    def test_el_vault_no_dice_de_ti_lo_que_no_dijiste(self):
        self.assertEqual(revisar.inventado(RAIZ), [])


class Sabotaje(Base):
    def test_restaurar_deja_como_estaba_cualquier_herramienta(self):
        """Un programa nuevo de herramientas/ también vuelve a estar como estaba tras su sabotaje."""
        (self.dir / "herramienta_de_prueba.py").write_text("MARGEN = 7\n", encoding="utf-8")
        sys.path.insert(0, str(self.dir))
        try:
            modulo = importlib.import_module("herramienta_de_prueba")
            modulo.MARGEN = -1
            restaurar(self.dir)
            self.assertEqual(modulo.MARGEN, 7)
        finally:
            sys.path.remove(str(self.dir))
            sys.modules.pop("herramienta_de_prueba", None)


class NoInventa(Base):
    """El agente rellena el README y el primer proyecto con tus siete respuestas. Lo que no
    contestaste queda [sin contestar] y lo que cita va entre «», tal cual lo dijiste."""

    def montar(self, contestadas, readme, proyecto=None):
        """Unos apuntes de prueba con las respuestas que se digan y las demás sin contestar. No
        se usan los de este vault: en cuanto contestas, ya no tienen los huecos."""
        (self.dir / "criterio").mkdir()
        texto = "# Apuntes de criterio\n\n## Las siete preguntas\n"
        for i in range(1, 8):
            texto += ("\n- **[sin contestar]** · tema {}\n  *Pregunta:* ¿pregunta {}?\n  *Tu respuesta:* {}\n"
                      "  *Qué hizo el vault con esto:* nada todavía.\n").format(
                i, i, contestadas.get(i, "(la escribes aquí, o el agente te la pregunta y la copia tal cual)"))
        (self.dir / "criterio" / "apuntes.md").write_text(texto, encoding="utf-8")
        (self.dir / "README.md").write_text(readme, encoding="utf-8")
        if proyecto is not None:
            (self.dir / "proyectos").mkdir()
            (self.dir / "proyectos" / "taller.md").write_text(proyecto, encoding="utf-8")
        return revisar.inventado(self.dir)

    def test_lee_las_siete_respuestas(self):
        self.montar({1: "Soy Ana y hago cerámica\n  en un taller pequeño.", 5: "Vender en dos ferias."}, "")
        self.assertEqual(revisar.respuestas(self.dir),
                         ["Soy Ana y hago cerámica en un taller pequeño.", None, None, None, "Vender en dos ferias.",
                          None, None])

    def test_lo_contestado_citado_tal_cual_pasa(self):
        self.assertEqual(self.montar(
            {1: "Soy Ana y hago cerámica en un taller pequeño, sobre todo tazas.", 2: "Con IA, nada."},
            "- **Quién soy:** «hago cerámica en un taller pequeño» (respuesta 1).\n"
            "- **Con qué trabajo:** «Con IA, nada» (respuestas 2 y 3).\n"
            "- **Lo que pesa:** [sin contestar] (respuesta 4).\n",
            "- qué es: «Soy Ana y … sobre todo tazas» (respuesta 1)\n- objetivo: [sin contestar] (respuesta 5)\n"), [])

    def test_caza_lo_que_no_se_contesto(self):
        problemas = self.montar({1: "Soy Ana."}, "- **Lo que pesa:** no llega a todo (respuesta 4).\n")
        self.assertEqual(len(problemas), 1)
        self.assertIn("README.md:1", problemas[0])
        self.assertIn("sin contestar", problemas[0])

    def test_caza_lo_inventado_en_un_proyecto(self):
        problemas = self.montar({1: "Soy Ana."}, "", "- objetivo: «vender 200 tazas» (respuesta 5)\n")
        self.assertEqual(len(problemas), 1)
        self.assertIn("proyectos/taller.md:1", problemas[0])

    def test_caza_una_cita_que_no_es_literal(self):
        problemas = self.montar({1: "Soy Ana y hago cerámica."}, "- **Quién soy:** «Ana, ceramista» (respuesta 1).\n")
        self.assertEqual(len(problemas), 1)
        self.assertIn("no está tal cual", problemas[0])

    def test_caza_una_respuesta_contada_sin_sus_palabras(self):
        problemas = self.montar({1: "Soy Ana y hago cerámica."}, "- **Quién soy:** ceramista de éxito (respuesta 1).\n")
        self.assertEqual(len(problemas), 1)
        self.assertIn("sin tus palabras", problemas[0])

    def test_lo_inventado_hace_fallar_revisar(self):
        self.montar({}, "- **Hacia dónde voy:** «abrir una tienda» (respuesta 5).\n")
        lineas, codigo = revisar.revisar_todo(self.dir)
        self.assertEqual(codigo, 1)
        self.assertTrue(any("no dijiste" in x for x in lineas), lineas)


# ---------------------------------------------------------------- medir

@unittest.skipUnless(revisar.hay_git(), "sin git en este equipo")
class Medir(Base):
    """A los 7 días el vault propone medir cómo va, una vez, y el bloque solo lleva cifras."""

    SECRETO = "Zacarías"

    def guardar(self, dia, mensaje):
        entorno = dict(__import__("os").environ, GIT_AUTHOR_DATE=dia + "T12:00:00", GIT_COMMITTER_DATE=dia + "T12:00:00")
        subprocess.run(["git", "-C", str(self.dir), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.dir), "-c", "user.name=Prueba", "-c", "user.email=prueba@" "ejemplo.invalid",
                        "commit", "-q", "--allow-empty", "-m", mensaje], check=True, env=entorno)

    def vault(self):
        """Un vault con algo de cada cosa y el mismo nombre escondido en todas partes."""
        revisar.git(self.dir, "init", "-q")
        (self.dir / "criterio").mkdir()
        (self.dir / "proyectos").mkdir()
        (self.dir / "herramientas").mkdir()
        preguntas = "".join("\n- **{}** · tema {}\n  *Pregunta:* ¿{}?\n  *Tu respuesta:* {}\n".format(
            "Principio" if i != 3 else "[sin contestar]", i, i,
            "habla de " + self.SECRETO if i != 3 else "(la escribes aquí, o el agente te la pregunta y la copia tal cual)")
            for i in range(1, 8))
        (self.dir / "criterio" / "apuntes.md").write_text(
            "# Apuntes\n" + preguntas + "\n- **Regla** · con " + self.SECRETO + "\n  «sí»\n"
            "\n- **Corregí** · la regla de " + self.SECRETO + "\n  «no»\n", encoding="utf-8")
        (self.dir / "proyectos" / "_plantilla.md").write_text("- objetivo:\n- fecha límite:\n", encoding="utf-8")
        (self.dir / "proyectos" / "zacarias.md").write_text(
            "# " + self.SECRETO + "\n- objetivo: vender\n- fecha límite: 31/10\n", encoding="utf-8")
        (self.dir / "proyectos" / "otro.md").write_text("- objetivo: [sin contestar]\n- fecha límite:\n",
                                                        encoding="utf-8")
        (self.dir / "herramientas" / "zacarias.py").write_text("print(1)\n", encoding="utf-8")
        (self.dir / "void.json").write_text('{"base": "0.4", "ficheros": {}}', encoding="utf-8")
        self.guardar("2026-10-01", "vault: plantilla de " + self.SECRETO)
        self.guardar("2026-10-01", "vault: tus siete respuestas")
        self.guardar("2026-10-03", "vault: " + self.SECRETO)

    def datos(self, hoy="2026-10-08"):
        return medir.datos(self.dir, medir.date.fromisoformat(hoy), comprobar_vault=lambda raiz: (True, False))

    def test_cuenta_lo_que_hay(self):
        self.vault()
        self.assertEqual(self.datos(), {
            "dias": 7, "guardados": 3, "dias_con_algo": 2, "proyectos": 2, "con_objetivo_y_fecha": 1,
            "apuntes_nuevos": 2, "corregi": 1, "sin_contestar": 1, "herramientas": 1, "pruebas": True,
            "revisar": False, "void": "0.4", "red": False})

    def test_el_bloque_no_saca_nada_de_dentro(self):
        self.vault()
        texto = medir.bloque(self.datos()) + medir.PARA_EL_AGENTE
        for trozo in (self.SECRETO, "zacarias", "Zacar", "vender", "31/10", "habla de"):
            self.assertNotIn(trozo.lower(), texto.lower())
        self.assertIn("[tu respuesta]", texto)

    def test_toca_a_los_siete_dias_y_una_vez(self):
        self.vault()
        self.assertEqual(medir.toca(self.dir, medir.date(2026, 10, 7)), (False, 6))
        self.assertEqual(medir.toca(self.dir, medir.date(2026, 10, 8)), (True, 7))
        self.guardar("2026-10-08", "vault: medida de la primera semana")   # lo que dice abrir.md, tal cual
        self.assertEqual(medir.toca(self.dir, medir.date(2026, 10, 20)), (False, 19))

    def test_sin_commits_no_toca(self):
        revisar.git(self.dir, "init", "-q")
        self.assertEqual(medir.toca(self.dir, medir.date(2026, 10, 8)), (False, 0))


# ---------------------------------------------------------------- tus herramientas

class Herramientas(Base):
    """Una herramienta nueva entra con sus pruebas, su sabotaje y sin dependencias."""

    def poner(self, herramienta, pruebas, void_json=None):
        (self.dir / "herramientas").mkdir()
        (self.dir / "herramientas" / "encargos.py").write_text(herramienta, encoding="utf-8")
        (self.dir / "herramientas" / "pruebas.py").write_text(pruebas, encoding="utf-8")
        if void_json is not None:
            (self.dir / "void.json").write_text(void_json, encoding="utf-8")
        return revisar.herramientas_sin_pruebas(self.dir)

    def test_las_de_este_vault_cumplen(self):
        self.assertEqual(revisar.herramientas_sin_pruebas(RAIZ), [])

    def test_con_pruebas_y_sabotaje_pasa(self):
        self.assertEqual(self.poner("import re\nimport revisar\n",
                                    "import encargos\nSABOTAJES = [\n    ('x', lambda: setattr(encargos, 'y', 1)),\n]\n"), [])

    def test_caza_una_herramienta_sin_pruebas(self):
        problemas = self.poner("import re\n", "import revisar\nSABOTAJES = []\n")
        self.assertEqual(len(problemas), 1)
        self.assertIn("encargos.py no tiene pruebas", problemas[0])

    def test_caza_una_herramienta_sin_sabotaje(self):
        # El señuelo: otro «SABOTAJES = [» que nombra la herramienta, dentro de un texto de una prueba.
        problemas = self.poner("import re\n", "import encargos\nX = 'SABOTAJES = [encargos]'\n\nSABOTAJES = [\n]\n")
        self.assertEqual(len(problemas), 1)
        self.assertIn("no tiene sabotaje", problemas[0])

    def test_caza_una_dependencia(self):
        problemas = self.poner("import re\nimport pandas as pd\nfrom requests import get\n",
                               "import encargos\nSABOTAJES = [('x', lambda: encargos)]\n")
        self.assertEqual(len(problemas), 2, problemas)
        self.assertTrue(all("no viene con Python" in x for x in problemas), problemas)

    def test_lo_que_trae_void_no_es_tuyo(self):
        """La base y las estrellas traen sus programas con sus propias pruebas: no se cuentan aquí."""
        self.assertEqual(self.poner("import re\n", "SABOTAJES = []\n",
                                    '{"ficheros": {}, "estrellas": {"x": {"ficheros": {"herramientas/encargos.py": "0"}}}}'),
                         [])


# ---------------------------------------------------------------- revisar

class Revisar(Base):
    def hay(self, linea):
        return [q for q, _ in revisar.revisar_linea(linea)]

    def test_caza_correos(self):
        # Correos y teléfonos armados por partes: escritos enteros, el escáner de fugas de Void
        # cazaría este archivo.
        self.assertEqual(self.hay("escribir a ana.perez@" "correo.es"), ["correo"])

    def test_caza_telefonos_y_dni(self):
        for linea in ("llamar al +" "34 6" "12 345 678", "fijo 9" "22 123 456", "móvil 6" "12345678",
                      "DNI 12345678Z"):
            self.assertTrue(self.hay(linea), linea)

    def test_caza_claves_y_contrasenas(self):
        # Armadas por partes para que este archivo no contenga nada con forma de clave.
        self.assertIn("clave de API", self.hay("clave " + "sk-" + "A1b2" * 6))
        self.assertIn("contraseña, token o clave escrita", self.hay("contraseña" + ": " + "hunter22"))

    def test_no_marca_fechas_tablas_ni_importes(self):
        for linea in ("| Pagar el seguro | | 30/9/2026 | | 2026-09-20 |", "reunión a las 10:30",
                      "presupuesto 12.000.000 €", "cuesta 15000000 euros", "7/10/2026"):
            self.assertEqual(self.hay(linea), [], linea)

    def test_no_marca_numeros_dentro_de_un_enlace(self):
        self.assertEqual(self.hay("<https://support.claude.com/en/articles/10166901-use-google>"), [])
        self.assertTrue(self.hay("https://ejemplo.es y llama al 6" "12345678"))

    def test_se_puede_dar_por_buena_una_linea(self):
        self.assertEqual(self.hay("mi correo: yo@" "correo.es <!-- revisar:ok -->"), [])

    @unittest.skipUnless(revisar.hay_git(), "sin git en este equipo")
    def test_el_gitignore_bloquea_documentos_correos_y_fotos(self):
        self.assertEqual(revisar.copias_sin_bloquear(RAIZ), [])

    @unittest.skipUnless(revisar.hay_git(), "sin git en este equipo")
    def test_el_gitignore_deja_pasar_el_texto(self):
        """El candado del candado: un .gitignore que lo bloquea todo también «pasaría»."""
        with tempfile.TemporaryDirectory() as tmp:
            revisar.git(tmp, "init", "-q")
            shutil.copy(RAIZ / ".gitignore", Path(tmp) / ".gitignore")
            fuera = revisar.git(tmp, "check-ignore", "--stdin",
                                entrada="proyectos/x.md\ncriterio/apuntes.md\nherramientas/revisar.py\n").stdout
        self.assertEqual(fuera.strip(), "")

    @unittest.skipUnless(revisar.hay_git(), "sin git en este equipo")
    def test_caza_una_copia_guardada_en_git(self):
        revisar.git(self.dir, "init", "-q")
        (self.dir / "CONTRATO.PDF").write_bytes(b"%PDF")
        (self.dir / "notas.md").write_text("hola\n", encoding="utf-8")
        revisar.git(self.dir, "add", "-f", "CONTRATO.PDF", "notas.md")
        self.assertEqual([n for n, _ in revisar.copias_en_git(self.dir)], ["CONTRATO.PDF"])

    def test_claude_sigue_encerrado_en_las_dos_configuraciones(self):
        self.assertEqual(revisar.candados_abiertos(RAIZ), [])

    def test_caza_un_encierro_quitado(self):
        (self.dir / ".claude").mkdir()
        (self.dir / ".claude" / "encerrado.json").write_text(
            '{"permissions": {"blockReadsOutsideWorkingDirectories": true}, '
            '"sandbox": {"enabled": true, "failIfUnavailable": false, "allowUnsandboxedCommands": false}}',
            encoding="utf-8")
        abiertos = revisar.candados_abiertos(self.dir)
        self.assertTrue(any("arrancar sin encierro" in a for a in abiertos))
        self.assertTrue(any("git push" in a for a in abiertos))

    def test_la_de_windows_arranca_sin_encierro_del_sistema(self):
        win = revisar.leer_ajustes(RAIZ, "encerrado-windows.json")
        self.assertTrue(win)
        self.assertFalse(win.get("sandbox", {}).get("failIfUnavailable"))

    def test_caza_windows_sin_permiso_por_comando(self):
        (self.dir / ".claude").mkdir()
        (self.dir / ".claude" / "encerrado-windows.json").write_text(
            '{"permissions": {"blockReadsOutsideWorkingDirectories": true, "ask": ["Bash"], '
            '"deny": ["Bash(curl *)"]}, "sandbox": {"failIfUnavailable": true}}', encoding="utf-8")
        abiertos = revisar.candados_windows(self.dir)
        self.assertTrue(any("antes de cada comando (PowerShell)" in a for a in abiertos))
        self.assertTrue(any("Invoke-WebRequest" in a for a in abiertos))
        self.assertTrue(any("no arrancaría" in a for a in abiertos))

    def test_la_app_de_escritorio_en_windows_pide_permiso_por_comando(self):
        """La app de escritorio de Claude solo lee settings.json: tiene que llevar los candados de Windows."""
        self.assertEqual(revisar.candados_windows(RAIZ, "settings.json"), [])
        perm = revisar.leer_ajustes(RAIZ, "settings.json")["permissions"]
        self.assertIn("PowerShell", perm["ask"])
        self.assertEqual(perm["disableBypassPermissionsMode"], "disable")

    def test_caza_settings_sin_los_candados_de_windows(self):
        (self.dir / ".claude").mkdir()
        (self.dir / ".claude" / "settings.json").write_text(
            '{"permissions": {"blockReadsOutsideWorkingDirectories": true, '
            '"ask": ["Bash(git push *)", "PowerShell(git push *)"]}}', encoding="utf-8")
        abiertos = revisar.candados_abiertos(self.dir)
        self.assertTrue(any(a.startswith("settings.json ya no pide permiso antes de cada comando (PowerShell)")
                            for a in abiertos))
        self.assertTrue(any(a.startswith("settings.json deja entrar en un modo que aprueba solo") for a in abiertos))

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

    @unittest.skipUnless(revisar.hay_git(), "sin git en este equipo")
    def test_el_vault_esta_limpio(self):
        lineas, codigo = revisar.revisar_todo(RAIZ)
        self.assertEqual(codigo, 0, "\n".join(lineas))


# ---------------------------------------------------------------- el sabotaje

def _sin_powershell(original):
    def leer(raiz, nombre):
        d = original(raiz, nombre)
        if nombre == "encerrado-windows.json":
            p = d.get("permissions", {})
            p["ask"] = [a for a in p.get("ask", []) if a != "PowerShell"]
        return d
    return leer


def _sin_pdf(original):
    def leer(raiz):
        return "\n".join(l for l in original(raiz).splitlines() if "[pP][dD][fF]" not in l)
    return leer


def _sin_fail(original):
    def leer(raiz, nombre):
        d = original(raiz, nombre)
        d.get("sandbox", {}).pop("failIfUnavailable", None)
        return d
    return leer


def _escritorio_sin_permiso(original):
    def leer(raiz, nombre):
        d = original(raiz, nombre)
        if nombre == "settings.json":
            p = d.get("permissions", {})
            p["ask"] = [a for a in p.get("ask", []) if a not in ("Bash", "PowerShell")]
            p.pop("disableBypassPermissionsMode", None)
        return d
    return leer


def _codex_abierto(raiz):
    return {"": {"sandbox_mode": "danger-full-access", "approval_policy": "never"},
            "sandbox_workspace_write": {"network_access": True}}


def _claude_sin_import(original):
    def leer(raiz, nombre):
        texto = original(raiz, nombre)
        return texto.replace("@AGENTS.md", "") if nombre == "CLAUDE.md" else texto
    return leer


SABOTAJES = [
    ("el .gitignore deja pasar los PDF",
     lambda: setattr(revisar, "leer_gitignore", _sin_pdf(revisar.leer_gitignore))),
    ("revisar deja de buscar correos",
     lambda: setattr(revisar, "PATRONES", [p for p in revisar.PATRONES if p[0] != "correo"])),
    ("revisar deja de buscar teléfonos y DNI",
     lambda: setattr(revisar, "NUMERO_LARGO", __import__("re").compile(r"(?!x)x"))),
    ("en Windows, PowerShell deja de pedir permiso antes de cada comando",
     lambda: setattr(revisar, "leer_ajustes", _sin_powershell(revisar.leer_ajustes))),
    ("el encierro deja arrancar a Claude sin encierro (failIfUnavailable desaparece)",
     lambda: setattr(revisar, "leer_ajustes", _sin_fail(revisar.leer_ajustes))),
    ("en la app de escritorio de Windows, Claude deja de pedir permiso por comando y se puede saltar los permisos",
     lambda: setattr(revisar, "leer_ajustes", _escritorio_sin_permiso(revisar.leer_ajustes))),
    ("Codex pasa a acceso total, sin pedir permiso y con internet",
     lambda: setattr(revisar, "leer_codex", _codex_abierto)),
    ("CLAUDE.md deja de importar AGENTS.md (Claude sin las reglas del vault)",
     lambda: setattr(revisar, "leer_texto", _claude_sin_import(revisar.leer_texto))),
    ("el vault da por contestadas las preguntas que no contestaste",
     lambda: setattr(revisar, "HUECO_RESPUESTA", "(ninguna respuesta se ve como hueco)")),
    ("una herramienta que depende de algo que no viene con Python pasa",
     lambda: setattr(revisar, "viene_con_python", lambda nombre: True)),
    ("una herramienta tuya se toma por una de Void y no se le piden pruebas",
     lambda: setattr(revisar, "de_void", lambda raiz: {"herramientas/encargos.py"})),
    ("medir propone medir antes de los 7 días",
     lambda: setattr(medir, "DIAS", 0)),
    ("medir vuelve a proponer medir aunque ya se midió",
     lambda: setattr(medir, "MENSAJE", "vault: otra cosa")),
    ("medir cuenta las siete preguntas como apuntes nuevos",
     lambda: setattr(medir, "es_pregunta", lambda lineas, i: False)),
    ("una cita que no es tal cual pasa por buena",
     lambda: setattr(revisar, "cita_literal", lambda cita, texto: True)),
]


def correr(verbosidad=0):
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    flujo = io.StringIO()
    res = unittest.TextTestRunner(stream=flujo, verbosity=verbosidad).run(suite)
    return res, flujo.getvalue()


def restaurar(carpeta=AQUI):
    """Deja como estaban todos los programas de herramientas/ tras un sabotaje, también los que
    añadas tú (si no, el sabotaje de uno rompería todas las pruebas que vienen detrás)."""
    for modulo in list(sys.modules.values()):
        fichero = getattr(modulo, "__file__", None)
        if fichero and modulo.__name__ != "__main__" and Path(fichero).resolve().parent == Path(carpeta).resolve():
            importlib.reload(modulo)


def sabotaje():
    print("Sabotaje: rompo el programa a propósito, una cosa cada vez, y miro si las pruebas lo cazan.")
    print("Una prueba que nunca viste fallar no demuestra nada.\n")
    res, _ = correr()
    if not res.wasSuccessful():
        # Si algo ya falla sin romper nada, cualquier sabotaje parecería «cazado» por esa prueba.
        print("Las pruebas ya fallan sin sabotaje: arréglalas primero (python3 herramientas/pruebas.py).")
        return 1
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
