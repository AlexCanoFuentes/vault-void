#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pruebas de void.py.

Uso:
  python3 pruebas.py                        corre las pruebas
  python3 pruebas.py --sabotaje             rompe void.py a propósito, un candado cada vez, y
                                            comprueba que las pruebas lo cazan (en rojo y por qué)
  python3 pruebas.py --vaults DIR [DIR...]  sobre una COPIA de cada vault: conecta la base 0.1,
                                            actualiza a 0.2 (un commit), git revert HEAD lo deja
                                            byte a byte como estaba, y sus propias pruebas en verde

Por qué existe el sabotaje: una prueba que nunca viste fallar no demuestra nada.
Las carpetas de --vaults nunca se tocan: se copian a una carpeta temporal.
"""
import ast
import datetime
import html
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import void as REF  # noqa: E402  la versión buena, para montar los datos de las pruebas
import regenerar_manifiesto  # noqa: E402
import formato as REF_F  # noqa: E402
import puerta as REF_P  # noqa: E402
import taller as REF_T  # noqa: E402  la nebulosa: el taller de estrellas
import regenerar_catalogo as REF_C  # noqa: E402

VOID_PY = AQUI / "void.py"   # el fichero bajo prueba (el sabotaje lo cambia por uno roto)
V = REF                      # el módulo bajo prueba
F = REF_F                    # formato.py bajo prueba
P = REF_P                    # puerta.py bajo prueba
C = REF_C                    # regenerar_catalogo.py bajo prueba
T = REF_T                    # taller.py bajo prueba
M = regenerar_manifiesto     # regenerar_manifiesto.py bajo prueba (la huella de vaultvoid.app/entrar)

TMP_GLOBAL = None


def preparar_git(aislado=True):
    """Git aislado de la configuración de quien prueba, con una identidad de prueba.

    Con las copias de vaults reales no se aísla: en Windows, git convierte los finales de línea
    (core.autocrlf) y la prueba tiene que ver el vault como lo ve su dueño."""
    global TMP_GLOBAL
    TMP_GLOBAL = tempfile.mkdtemp(prefix="void-git-")
    if aislado:
        vacio = Path(TMP_GLOBAL, "gitconfig")
        vacio.write_text("", encoding="utf-8")
        os.environ["GIT_CONFIG_GLOBAL"] = str(vacio)
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
    for k in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        os.environ[k] = "Prueba"
    for k in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        os.environ[k] = "prueba@example.com"
    for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        os.environ.pop(k, None)


def borrar(carpeta):
    """shutil.rmtree que también puede con los ficheros de solo lectura de .git en Windows."""
    def quitar_solo_lectura(funcion, ruta, _):
        try:
            os.chmod(ruta, 0o700)
            funcion(ruta)
        except OSError:
            pass
    if carpeta and os.path.exists(str(carpeta)):
        if sys.version_info >= (3, 12):
            shutil.rmtree(str(carpeta), onexc=quitar_solo_lectura)
        else:
            shutil.rmtree(str(carpeta), onerror=quitar_solo_lectura)


def cargar(ruta):
    spec = importlib.util.spec_from_file_location("void_bajo_prueba", str(ruta))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------- ayudas

def git(carpeta, *args):
    r = subprocess.run(["git", "-C", str(carpeta)] + list(args), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def hacer_base(carpeta, version, ficheros, manifiesto=None):
    """Una base de prueba: carpeta/base/<ficheros> y su manifiesto."""
    base = Path(carpeta) / "base"
    if base.exists():
        shutil.rmtree(str(base))
    for ruta, datos in ficheros.items():
        p = base.joinpath(*ruta.split("/"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(datos)
    m = manifiesto or {"version": version,
                       "ficheros": {r: REF.huella(d) for r, d in ficheros.items()}}
    (base / REF.MANIFIESTO).write_text(json.dumps(m), encoding="utf-8")
    return Path(carpeta)


def hacer_vault(carpeta, ficheros=None):
    v = Path(carpeta)
    v.mkdir(parents=True, exist_ok=True)
    git(v, "init", "-q")
    for ruta, datos in (ficheros or {"README.md": b"# Mi vault\n"}).items():
        p = v.joinpath(*ruta.split("/"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(datos)
    git(v, "add", "-A")
    git(v, "commit", "-q", "-m", "inicio")
    return v


def foto(carpeta):
    """Todo el vault, fichero a fichero y en bytes, sin .git."""
    salida = {}
    for raiz, dirs, ficheros in os.walk(str(carpeta)):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in ficheros:
            p = Path(raiz, f)
            salida[p.relative_to(carpeta).as_posix()] = p.read_bytes()
    return salida


def commits(carpeta):
    codigo, salida = git(carpeta, "log", "--format=%s")
    return salida.splitlines() if codigo == 0 else []


def limpio(carpeta):
    return git(carpeta, "status", "--porcelain")[1].strip() == ""


def correr(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        codigo = V.main([str(a) for a in args])
    return codigo, out.getvalue(), err.getvalue()


AGENTS_01 = ("# Reglas\n<!-- base:inicio -->\n- regla común 1\n<!-- base:fin -->\n").encode("utf-8")
AGENTS_02 = ("# Reglas\n<!-- base:inicio -->\n- regla común 1\n- regla común 2\n<!-- base:fin -->\n"
             ).encode("utf-8")
UNO_01 = b"linea uno\nlinea dos\n"
UNO_02 = b"linea uno\nlinea dos\nlinea tres\n"
BASE_01 = {"AGENTS.md": AGENTS_01, "uno.txt": UNO_01, "herramientas/dos.py": b"X = 1\n"}
BASE_02 = {"AGENTS.md": AGENTS_02, "uno.txt": UNO_02, "herramientas/dos.py": b"X = 2\n"}


class Caso(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="void-prueba-"))
        self.b01 = hacer_base(self.tmp / "b01", "0.1", BASE_01)
        self.b02 = hacer_base(self.tmp / "b02", "0.2", BASE_02)

    def tearDown(self):
        borrar(str(self.tmp))

    def conectado(self, ficheros=None):
        v = hacer_vault(self.tmp / "vault", ficheros)
        codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, "no pudo conectar el vault de prueba: " + err)
        if commits(v)[0] != "void: base 0.1" or not limpio(v):
            self.fail("conectar no dejó el commit «void: base 0.1» con todo dentro")
        return v

    def commit_usuario(self, v, ruta, datos):
        v.joinpath(*ruta.split("/")).write_bytes(datos)
        git(v, "add", "-A")
        git(v, "commit", "-q", "-m", "cambio mío")


# ---------------------------------------------------------------- conectar y void.json

class SinVoidJson(Caso):
    def test_actualizar_sin_void_json_no_toca_nada(self):
        v = hacer_vault(self.tmp / "vault", {"README.md": b"hola\n", "uno.txt": b"mio\n"})
        antes, log = foto(v), commits(v)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b01)
        if foto(v) != antes or commits(v) != log:
            self.fail("escribió en un vault sin void.json (sin que nadie dijera --conectar)")
        self.assertEqual(codigo, 1, "no falló al no haber void.json")
        self.assertIn("no está conectada a Void", err, "el error no dice que falta void.json")

    def test_estado_sin_void_json(self):
        v = hacer_vault(self.tmp / "vault")
        codigo, out, err = correr("estado", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 1)
        self.assertIn("no está conectada a Void", err)

    def test_conectar_carpeta_vacia(self):
        v = self.tmp / "nuevo"
        codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        self.assertEqual(commits(v), ["void: base 0.1"], "conectar no dejó un solo commit")
        for ruta, datos in BASE_01.items():
            self.assertEqual(v.joinpath(*ruta.split("/")).read_bytes(), datos)
        self.assertEqual(json.loads((v / "void.json").read_text(encoding="utf-8"))["base"], "0.1")
        self.assertTrue(limpio(v), "quedaron cambios fuera del commit")

    def test_conectar_se_lleva_lo_recien_bajado_y_revert_lo_quita(self):
        """vaultvoid.app/entrar: el agente baja void.py a herramientas/ y conecta con él. Ese fichero
        es igual que el de la base pero git aún no lo sigue: tiene que entrar en el commit de conectar,
        o queda suelto y git revert HEAD no deja el vault como estaba antes de bajarlo."""
        v = hacer_vault(self.tmp / "vault")
        antes = foto(v)
        (v / "herramientas").mkdir()
        (v / "herramientas" / "dos.py").write_bytes(BASE_01["herramientas/dos.py"])
        codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        if not limpio(v):
            self.fail("lo recién bajado, igual que la base, quedó fuera del commit de conectar")
        git(v, "revert", "--no-edit", "HEAD")
        if foto(v) != antes:
            self.fail("git revert HEAD no deja el vault como estaba antes de bajar void.py")

    def test_conectar_no_pisa_lo_que_ya_hay(self):
        v = hacer_vault(self.tmp / "vault", {"AGENTS.md": b"# Mis reglas\n", "uno.txt": b"mio\n"})
        codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        self.assertEqual((v / "AGENTS.md").read_bytes(), b"# Mis reglas\n",
                         "pisó un AGENTS.md que no tenía marcas")
        self.assertEqual((v / "uno.txt").read_bytes(), b"mio\n", "pisó un fichero del usuario al conectar")
        self.assertEqual((v / "uno.txt.base-nueva").read_bytes(), UNO_01)
        self.assertIn("uno.txt.base-nueva", out)
        self.assertIn("AGENTS.md.base-nueva", out)

    def test_conectar_con_carpeta_ignorada(self):
        """El vault de Alex, 8-oct: su .gitignore ignora .codex/ entera salvo config.toml. void.py dejó al
        lado la versión de la base como .base-nueva, git la rechazó por ignorada y la conexión se
        deshizo entera. Lo que escribe void.py entra en su commit aunque la carpeta esté ignorada."""
        v = hacer_vault(self.tmp / "vault", {".gitignore": b"herramientas/*\n!herramientas/dos.py\n",
                                             "herramientas/dos.py": b"X = 9\n"})
        codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, "no conectó un vault que ignora una carpeta de la base: " + err)
        self.assertEqual((v / "herramientas" / "dos.py").read_bytes(), b"X = 9\n", "pisó lo del usuario")
        self.assertEqual((v / "herramientas" / "dos.py.base-nueva").read_bytes(), BASE_01["herramientas/dos.py"])
        self.assertTrue(limpio(v), "quedaron cambios fuera del commit")
        codigo, lista = git(v, "ls-files", "herramientas/dos.py.base-nueva")
        self.assertIn("dos.py.base-nueva", lista, "la .base-nueva no entró en el commit")

    def test_conectar_pone_marcas_al_tramo_que_ya_es_igual(self):
        propio = b"# Mis reglas\n\nMi intro.\n- regla com\xc3\xban 1\nMi final.\n"
        v = hacer_vault(self.tmp / "vault", {"AGENTS.md": propio})
        codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        esperado = (b"# Mis reglas\n\nMi intro.\n<!-- base:inicio -->\n- regla com\xc3\xban 1\n"
                    b"<!-- base:fin -->\nMi final.\n")
        if (v / "AGENTS.md").read_bytes() != esperado:
            self.fail("al poner las marcas cambió algo más que las dos líneas de marca")
        self.assertFalse((v / "AGENTS.md.base-nueva").exists())
        self.assertIn("he puesto las marcas", out)

    def test_tramo_repetido_no_se_marca(self):
        propio = b"- regla com\xc3\xban 1\n\n- regla com\xc3\xban 1\n"
        v = hacer_vault(self.tmp / "vault", {"AGENTS.md": propio})
        correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual((v / "AGENTS.md").read_bytes(), propio, "marcó un tramo que aparece dos veces")
        self.assertTrue((v / "AGENTS.md.base-nueva").exists())

    def test_no_actua_sobre_el_repo_de_void(self):
        codigo, out, err = correr("actualizar", "--conectar", "--vault", AQUI, "--desde", self.b01)
        self.assertEqual(codigo, 1, "se dejó usar sobre el propio repositorio de Void")

    def test_dentro_de_otro_repo(self):
        padre = hacer_vault(self.tmp / "padre")
        (padre / "sub").mkdir()
        codigo, out, err = correr("actualizar", "--conectar", "--vault", padre / "sub", "--desde", self.b01)
        self.assertEqual(codigo, 1)
        self.assertIn("otro repositorio", err)


# ---------------------------------------------------------------- actualizar

class Actualizar(Caso):
    def test_01_a_02_un_commit_y_revert_byte_a_byte(self):
        v = self.conectado()
        antes, log = foto(v), commits(v)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        self.assertEqual(commits(v), ["void: base 0.2"] + log, "no dejó exactamente un commit «void: base 0.2»")
        self.assertTrue(limpio(v), "quedaron cambios fuera del commit")
        for ruta, datos in BASE_02.items():
            self.assertEqual(v.joinpath(*ruta.split("/")).read_bytes(), datos, ruta + " no se actualizó")
        git(v, "revert", "--no-edit", "HEAD")
        if foto(v) != antes:
            self.fail("git revert HEAD no deja el vault byte a byte como estaba")

    def test_hash_cambiado_en_el_manifiesto(self):
        v = self.conectado()
        m = json.loads((self.b02 / "base" / "MANIFIESTO.json").read_text(encoding="utf-8"))
        m["ficheros"]["uno.txt"] = "0" * 64
        hacer_base(self.b02, "0.2", BASE_02, manifiesto=m)
        antes, log = foto(v), commits(v)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        if foto(v) != antes or commits(v) != log:
            self.fail("escribió aunque la huella de uno.txt no cuadraba con el manifiesto")
        self.assertEqual(codigo, 1)
        self.assertIn("no cuadra con su manifiesto en uno.txt", err)

    def test_fichero_cambiado_por_el_camino(self):
        v = self.conectado()
        (self.b02 / "base" / "herramientas" / "dos.py").write_bytes(b"import os; os.system('x')\n")
        antes = foto(v)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        if foto(v) != antes:
            self.fail("escribió aunque herramientas/dos.py no cuadraba con el manifiesto")
        self.assertIn("no cuadra", err)

    def test_fichero_modificado_por_el_usuario(self):
        v = self.conectado()
        self.commit_usuario(v, "uno.txt", b"lo he cambiado yo\n")
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        if (v / "uno.txt").read_bytes() != b"lo he cambiado yo\n":
            self.fail("pisó uno.txt, que el usuario había cambiado")
        self.assertEqual((v / "uno.txt.base-nueva").read_bytes(), UNO_02,
                         "no dejó la versión nueva al lado como uno.txt.base-nueva")
        self.assertIn("uno.txt.base-nueva", out, "no lo dijo en voz alta")
        self.assertEqual((v / "herramientas" / "dos.py").read_bytes(), b"X = 2\n",
                         "no actualizó lo que el usuario no había tocado")
        instalado = json.loads((v / "void.json").read_text(encoding="utf-8"))["ficheros"]["uno.txt"]
        self.assertEqual(instalado, REF.huella(UNO_01), "void.json dice instalada una versión que no se puso")

    def test_marcas_lo_de_fuera_es_tuyo(self):
        v = self.conectado()
        propio = ("Mis cosas arriba\n" + AGENTS_01.decode("utf-8") + "\nMis cosas abajo\n").encode("utf-8")
        self.commit_usuario(v, "AGENTS.md", propio)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        esperado = ("Mis cosas arriba\n" + AGENTS_02.decode("utf-8") + "\nMis cosas abajo\n").encode("utf-8")
        if (v / "AGENTS.md").read_bytes() != esperado:
            self.fail("no respetó lo de fuera de las marcas en AGENTS.md, o no cambió lo de dentro")
        self.assertFalse((v / "AGENTS.md.base-nueva").exists())

    def test_marcas_lo_de_dentro_cambiado_por_el_usuario(self):
        v = self.conectado()
        self.commit_usuario(v, "AGENTS.md", AGENTS_01.replace(b"regla com", b"MI regla com"))
        antes = (v / "AGENTS.md").read_bytes()
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        if (v / "AGENTS.md").read_bytes() != antes:
            self.fail("pisó lo de dentro de las marcas, que el usuario había cambiado")
        self.assertTrue((v / "AGENTS.md.base-nueva").exists())
        self.assertIn("AGENTS.md.base-nueva", out)

    def test_marcas_quitadas(self):
        v = self.conectado()
        self.commit_usuario(v, "AGENTS.md", b"# Sin marcas\n")
        correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual((v / "AGENTS.md").read_bytes(), b"# Sin marcas\n")
        self.assertEqual((v / "AGENTS.md.base-nueva").read_bytes(), AGENTS_02)

    def test_finales_de_linea_de_windows(self):
        v = self.conectado()
        self.commit_usuario(v, "uno.txt", UNO_01.replace(b"\n", b"\r\n"))
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        if (v / "uno.txt").read_bytes() != UNO_02.replace(b"\n", b"\r\n"):
            self.fail("tomó un fichero con finales de Windows por un cambio del usuario, "
                      "o no respetó sus finales de línea")

    def test_windows_con_autocrlf_revert_byte_a_byte(self):
        """Git para Windows trae core.autocrlf=true: saca los ficheros con \\r\\n."""
        v = hacer_vault(self.tmp / "vault")
        git(v, "config", "core.autocrlf", "true")
        codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        vj = (v / "void.json").read_bytes()
        if vj.count(b"\n") != vj.count(b"\r\n"):
            self.fail("con core.autocrlf escribió void.json con \\n; git lo sacaría con \\r\\n y el revert no cuadraría")
        antes = foto(v)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        self.assertTrue(limpio(v), "quedaron cambios fuera del commit")
        git(v, "revert", "--no-edit", "HEAD")
        if foto(v) != antes:
            self.fail("con core.autocrlf, git revert HEAD no deja el vault byte a byte (finales de línea)")
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b01)
        self.assertIn("No hay nada que actualizar", out, "con \\r\\n en disco cree que hay cambios: " + err)

    def test_cambios_sin_guardar(self):
        v = self.conectado()
        (v / "AGENTS.md").write_bytes(b"Arriba sin guardar\n" + AGENTS_01)
        antes, log = foto(v), commits(v)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        if foto(v) != antes or commits(v) != log:
            self.fail("actualizó un fichero con cambios sin guardar (el commit se los llevaría)")
        self.assertEqual(codigo, 1)
        self.assertIn("sin guardar", err)

    def test_ruta_que_sale_del_vault(self):
        v = self.conectado()
        malo = dict(BASE_02)
        malo["../fuera.txt"] = b"fuera\n"
        base = self.tmp / "mala"
        (base / "base").mkdir(parents=True)
        (base / "fuera.txt").write_bytes(b"fuera\n")
        hacer_base(base, "0.2", {k: d for k, d in malo.items() if not k.startswith("..")},
                   manifiesto={"version": "0.2", "ficheros": {k: REF.huella(d) for k, d in malo.items()}})
        (base / "fuera.txt").write_bytes(b"fuera\n")
        antes = foto(self.tmp)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", base)
        if foto(self.tmp) != antes:
            self.fail("escribió fuera del vault por una ruta con ..")
        self.assertEqual(codigo, 1)
        if "saldría del vault" not in err:
            self.fail("no rechazó la ruta con .. por sí mismo (lo paró otra cosa: {})".format(err.strip()[:120]))

    @unittest.skipIf(os.name == "nt", "los enlaces simbólicos piden permisos especiales en Windows")
    def test_enlace_que_sale_del_vault(self):
        v = self.conectado()
        fuera = self.tmp / "fuera"
        shutil.copytree(str(v / "herramientas"), str(fuera))
        shutil.rmtree(str(v / "herramientas"))
        os.symlink(str(fuera), str(v / "herramientas"))
        git(v, "add", "-A")
        git(v, "commit", "-q", "-m", "enlace")
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        if (fuera / "dos.py").read_bytes() != b"X = 1\n":
            self.fail("escribió fuera del vault siguiendo un enlace")
        self.assertEqual(codigo, 1)
        if "fuera del vault" not in err:
            self.fail("no rechazó el enlace por sí mismo (lo paró otra cosa: {})".format(err.strip()[:120]))

    def test_nunca_ejecuta_lo_que_descarga(self):
        v = self.conectado()
        marca = self.tmp / "EJECUTADO"
        trampa = "open({!r}, 'w').write('si')\n".format(str(marca)).encode("utf-8")
        ficheros = dict(BASE_02)
        ficheros["herramientas/trampa.py"] = trampa
        ficheros["sitecustomize.py"] = trampa
        hacer_base(self.b02, "0.2", ficheros)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        self.assertEqual((v / "herramientas" / "trampa.py").read_bytes(), trampa)
        if marca.exists():
            self.fail("ejecutó código descargado")

    def test_si_el_commit_falla_lo_deja_todo_como_estaba(self):
        v = self.conectado()
        antes, log = foto(v), commits(v)
        quitar = {k: os.environ.pop(k) for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
                                                 "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")}
        git(v, "config", "user.useConfigOnly", "true")
        try:
            codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        finally:
            os.environ.update(quitar)
        if foto(v) != antes or commits(v) != log or not limpio(v):
            self.fail("el commit falló y dejó ficheros a medias")
        self.assertEqual(codigo, 1)
        self.assertIn("He dejado todo como estaba", err)

    def test_nada_que_hacer(self):
        v = self.conectado()
        log = commits(v)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0)
        self.assertIn("No hay nada que actualizar", out)
        self.assertEqual(commits(v), log, "hizo un commit sin cambios")

    def test_fichero_que_sale_de_la_base(self):
        v = self.conectado()
        sin_dos = {k: d for k, d in BASE_02.items() if k != "herramientas/dos.py"}
        hacer_base(self.b02, "0.2", sin_dos)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        self.assertFalse((v / "herramientas" / "dos.py").exists(), "no quitó un fichero que salió de la base")

    def test_fichero_que_sale_de_la_base_pero_es_tuyo(self):
        v = self.conectado()
        self.commit_usuario(v, "herramientas/dos.py", b"X = 'mio'\n")
        hacer_base(self.b02, "0.2", {k: d for k, d in BASE_02.items() if k != "herramientas/dos.py"})
        correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual((v / "herramientas" / "dos.py").read_bytes(), b"X = 'mio'\n",
                         "borró un fichero que el usuario había cambiado")

    def test_estado(self):
        v = self.conectado()
        self.commit_usuario(v, "uno.txt", b"mio\n")
        codigo, out, err = correr("estado", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        self.assertIn("Base instalada: 0.1", out)
        self.assertIn("Base disponible: 0.2", out)
        self.assertRegex(out, r"cambiado por ti\s+uno\.txt")
        self.assertRegex(out, r"como se instaló\s+AGENTS\.md")


# ---------------------------------------------------------------- GitHub y la red

def zip_como_github(ficheros, version):
    datos = io.BytesIO()
    with zipfile.ZipFile(datos, "w") as z:
        z.writestr("vault-void-main/", b"")
        z.writestr("vault-void-main/void.py", b"")
        for ruta, d in ficheros.items():
            z.writestr("vault-void-main/base/" + ruta, d)
        z.writestr("vault-void-main/base/MANIFIESTO.json", json.dumps(
            {"version": version, "ficheros": {r: REF.huella(d) for r, d in ficheros.items()}}))
    return datos.getvalue()


class Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Red(Caso):
    def test_descarga_de_github(self):
        v = self.conectado()
        z = zip_como_github(BASE_02, "0.2")
        with mock.patch.object(V.urllib.request, "urlopen", return_value=Respuesta(z)) as abrir:
            codigo, out, err = correr("actualizar", "--vault", v)
        self.assertEqual(codigo, 0, err)
        self.assertEqual(abrir.call_args[0][0],
                         "https://codeload.github.com/AlexCanoFuentes/vault-void/zip/refs/heads/main")
        self.assertEqual(commits(v)[0], "void: base 0.2")
        self.assertIn("github.com/AlexCanoFuentes/vault-void", (v / "void.json").read_text(encoding="utf-8"))

    def test_zip_local(self):
        v = self.conectado()
        z = self.tmp / "base.zip"
        z.write_bytes(zip_como_github(BASE_02, "0.2"))
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", z)
        self.assertEqual(codigo, 0, err)
        self.assertEqual((v / "uno.txt").read_bytes(), UNO_02)

    def test_sin_red(self):
        v = self.conectado()
        antes = foto(v)
        fallo = urllib.error.URLError(ConnectionRefusedError("sin red"))
        with mock.patch.object(V.urllib.request, "urlopen", side_effect=fallo):
            codigo, out, err = correr("actualizar", "--vault", v)
        self.assertEqual(foto(v), antes)
        self.assertEqual(codigo, 1, "sin red no terminó con error")
        if "permiso de red" not in err or "ejecútalo tú" not in err:
            self.fail("sin red no dice qué hacer (pedir permiso de red o ejecutarlo la persona)")
        self.assertEqual(err.strip().count("\n"), 0, "el error sin red no es una sola frase")

    def test_sin_red_de_verdad(self):
        """Un proceso aparte, con la red cortada por un proxy que no existe."""
        v = self.conectado()
        antes = foto(v)
        entorno = dict(os.environ)
        for k in ("HTTPS_PROXY", "https_proxy"):
            entorno[k] = "http://127.0.0.1:9"
        entorno.pop("NO_PROXY", None)
        entorno.pop("no_proxy", None)
        r = subprocess.run([sys.executable, str(VOID_PY), "actualizar", "--vault", str(v)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=entorno, timeout=120)
        err = r.stderr.decode("utf-8", "replace")
        self.assertEqual(foto(v), antes)
        self.assertEqual(r.returncode, 1, "sin red no terminó con error: " + err[-300:])
        if "permiso de red" not in err or "Traceback" in err:
            self.fail("sin red no da el error de una frase: " + err.strip().splitlines()[-1][:200])

    def test_404(self):
        v = self.conectado()
        fallo = urllib.error.HTTPError("u", 404, "no", {}, None)
        with mock.patch.object(V.urllib.request, "urlopen", side_effect=fallo):
            codigo, out, err = correr("actualizar", "--vault", v)
        self.assertEqual(codigo, 1)
        self.assertIn("No encuentro Void en GitHub", err)


# ---------------------------------------------------------------- el repo

class Repo(unittest.TestCase):
    def test_un_vault_nuevo_se_monta_con_la_base_y_pasa_sus_pruebas(self):
        tmp = Path(tempfile.mkdtemp(prefix="void-montar-"))
        try:
            v = tmp / "vault-nuevo"
            codigo, out, err = correr("actualizar", "--conectar", "--vault", v, "--desde", AQUI)
            self.assertEqual(codigo, 0, err)
            self.assertEqual(commits(v), ["void: base " + REF.validar_manifiesto(
                (AQUI / "base" / "MANIFIESTO.json").read_bytes())[0]])
            r = subprocess.run([sys.executable, str(v / "herramientas" / "pruebas_comunes.py")],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(v))
            self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace")[-500:])
        finally:
            borrar(str(tmp))

    def test_la_base_no_trae_nada_de_nadie(self):
        """La base no puede llevar nombres, datos ni criterio de una persona: lo mira el escáner."""
        import fugas
        self.assertEqual(fugas.escanear(AQUI / "base"), [])

    def test_manifiesto_al_dia(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            codigo = regenerar_manifiesto.main(["--comprobar"])
        self.assertEqual(codigo, 0, out.getvalue())

    def test_manifiesto_valido_y_rutas_seguras(self):
        datos = (AQUI / "base" / "MANIFIESTO.json").read_bytes()
        version, ficheros = REF.validar_manifiesto(datos)
        self.assertTrue(ficheros)

    def test_solo_biblioteca_estandar(self):
        estandar = getattr(sys, "stdlib_module_names", None) or {
            "hashlib", "io", "json", "os", "re", "socket", "ssl", "subprocess", "sys", "tempfile",
            "time", "urllib", "zipfile", "pathlib"}
        arbol = ast.parse(VOID_PY.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            nombres = []
            if isinstance(nodo, ast.Import):
                nombres = [a.name for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module or ""]
            for n in nombres:
                self.assertIn(n.split(".")[0], estandar, n + " no es de la biblioteca estándar")

    def test_sin_bash_ni_shell(self):
        texto = VOID_PY.read_text(encoding="utf-8")
        for prohibido in ("shell=True", "os.system", "bash", "exec(", "eval(", "import_module",
                          "spec_from_file_location", "runpy"):
            self.assertNotIn(prohibido, texto, "void.py usa " + prohibido)

    def test_rutas_seguras(self):
        for mala in ("../x", "/etc/x", "a/../../x", ".git/config", "C:/x", "a\\b", "con.txt",
                     "void.json", "x.base-nueva", "a/./b", "", "a//b", "nul", "x "):
            self.assertFalse(REF.ruta_segura(mala), mala)
        for buena in ("AGENTS.md", ".codex/config.toml", "herramientas/void.py", ".gitignore"):
            self.assertTrue(REF.ruta_segura(buena), buena)


# ---------------------------------------------------------------- vaultvoid.app/entrar

WEB = AQUI / "web"


def ordenes_md(texto):
    return re.findall(r"^```\n(.*?)\n```$", texto, re.S | re.M)


def ordenes_html(texto):
    return [html.unescape(o) for o in re.findall(r"<pre><code>(.*?)</code></pre>", texto, re.S)]


class Entrar(unittest.TestCase):
    """La página que lee el agente para conectar un vault: la huella que publica tiene que ser la de
    void.py, y la orden que la comprueba tiene que guardar solo lo que cuadra."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="void-entrar-"))

    def tearDown(self):
        borrar(str(self.tmp))

    def copia_web(self):
        web = self.tmp / "web"
        web.mkdir()
        for n in ("entrar.md", "entrar.html", "entrar.txt"):
            shutil.copyfile(str(WEB / n), str(web / n))
        return web

    def test_la_pagina_publica_la_huella_de_void_py(self):
        h = REF.huella(VOID_PY.read_bytes())
        self.assertEqual(M.problemas_entrar(WEB, h), [], "corre python3 regenerar_manifiesto.py")

    def test_huella_que_no_cuadra_sale_en_rojo(self):
        h = REF.huella(VOID_PY.read_bytes())
        otra = ("0" if h[0] != "0" else "1") + h[1:]
        for nombre in ("entrar.md", "entrar.html", "entrar.txt"):
            web = self.copia_web()
            p = web / nombre
            p.write_text(p.read_text(encoding="utf-8").replace(h, otra, 1), encoding="utf-8")
            problemas = M.problemas_entrar(web, h)
            if not any("no cuadra" in x and nombre in x for x in problemas):
                self.fail("la huella de {} no cuadra con void.py y no salta (vio {})".format(nombre, problemas))
            borrar(str(web))

    def test_void_py_cambia_y_la_pagina_no(self):
        web = self.copia_web()
        h = REF.huella(VOID_PY.read_bytes() + b"# un cambio\n")
        if not any("no cuadra" in x for x in M.problemas_entrar(web, h)):
            self.fail("void.py cambió y la página sigue publicando la huella vieja sin que salte")

    def test_la_huella_es_la_del_void_py_que_sirve_github(self):
        """GitHub sirve el fichero tal como está en git: sin \r\n, su sha256 es el de la página."""
        r = subprocess.run(["git", "-C", str(AQUI), "show", "HEAD:void.py"], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        if r.returncode != 0:
            self.skipTest("sin git en este sistema")
        self.assertNotIn(b"\r", r.stdout, "void.py en git lleva \\r: su sha256 no sería la huella publicada")

    def test_md_html_y_txt_dicen_lo_mismo(self):
        md = (WEB / "entrar.md").read_text(encoding="utf-8")
        ht = (WEB / "entrar.html").read_text(encoding="utf-8")
        self.assertEqual((WEB / "entrar.txt").read_bytes(), (WEB / "entrar.md").read_bytes())
        self.assertTrue(ordenes_md(md), "entrar.md no tiene órdenes")
        self.assertEqual(ordenes_md(md), ordenes_html(ht), "las órdenes de entrar.md y entrar.html no son las mismas")
        for frase in ("conéctate a Void: vaultvoid.app/entrar", "git revert HEAD", "network_access = false",
                      "xcode-select --install", "py --version", "Homebrew",
                      "herramientas/void.py registrar --alias", "Si no dice que sí, termina aquí",
                      "No enseñes la llave"):
            self.assertIn(frase, md)
            self.assertIn(frase, html.unescape(ht))

    def test_hay_camino_a_mano_si_el_agente_no_puede(self):
        """Informe de un socio, 9-oct: el modo automático de Claude Code rechazó bajar y comprobar, y la
        entrada se quedó parada. La página tiene que decirle al agente que no insista y darle a la persona
        las órdenes para pegarlas ella, con la misma orden de bajar que el paso 3 (que comprueba la huella)."""
        md = (WEB / "entrar.md").read_text(encoding="utf-8")
        ht = html.unescape(re.sub(r"<[^>]+>", "", (WEB / "entrar.html").read_text(encoding="utf-8")))
        for texto in (md, ht):
            for frase in ("Camino a mano", "auto mode classifier", "no la repitas ni busques otra forma",
                          "para echarle un vistazo", "qué cambian los candados",
                          "`python3` por `py`" if texto is md else "python3 por py"):
                self.assertIn(frase, texto)
        ordenes = ordenes_md(md)
        self.assertEqual(ordenes.count(ordenes[0]), 2, "el camino a mano no usa la misma orden de bajar que el paso 3")
        for o in ("git --version\npython3 --version", "python3 herramientas/void.py actualizar --conectar",
                  "python3 herramientas/void.py estado"):
            self.assertIn(o, ordenes)

    def test_el_html_se_lee_sin_javascript(self):
        ht = (WEB / "entrar.html").read_text(encoding="utf-8").lower()
        self.assertNotIn("<script", ht, "entrar.html depende de JavaScript: un agente no lo ejecuta")

    def bajar(self, servido):
        """Ejecuta la orden del paso 3 tal cual, pero bajando de un fichero local en vez de GitHub."""
        orden = ordenes_md((WEB / "entrar.md").read_text(encoding="utf-8"))[0]
        codigo = re.fullmatch(r'python3 -c "(.*)"', orden).group(1)
        url = "https://raw.githubusercontent.com/AlexCanoFuentes/vault-void/main/void.py"
        self.assertIn(url, codigo)
        fuente = self.tmp / "servido.py"
        fuente.write_bytes(servido)
        vault = self.tmp / "vault"
        vault.mkdir()
        r = subprocess.run([sys.executable, "-c", codigo.replace(url, fuente.as_uri())], cwd=str(vault),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return r.returncode, r.stdout.decode("utf-8", "replace"), vault / "herramientas" / "void.py"

    def test_la_orden_de_bajar_guarda_si_cuadra(self):
        codigo, salida, destino = self.bajar(VOID_PY.read_bytes())
        self.assertEqual(codigo, 0, salida)
        self.assertIn("Huella OK", salida)
        self.assertEqual(destino.read_bytes(), VOID_PY.read_bytes())

    def test_la_orden_de_bajar_no_guarda_si_no_cuadra(self):
        codigo, salida, destino = self.bajar(VOID_PY.read_bytes() + b"import os\n")
        self.assertEqual(codigo, 1, "la orden no falló con un void.py cambiado por el camino")
        self.assertIn("NO CUADRA", salida)
        self.assertFalse(destino.exists(), "guardó un void.py cuya huella no cuadraba")


# ---------------------------------------------------------------- la plantilla de un vault nuevo

PLANTILLA = AQUI / "plantilla"


def ficheros_planos(carpeta):
    return sorted(p.relative_to(carpeta).as_posix() for p in Path(carpeta).rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.name != REF.MANIFIESTO)


class Plantilla(unittest.TestCase):
    """La plantilla con la que empieza un vault (vaultvoid.app/empezar): es pública, así que no
    puede llevar nada de las personas de cuyos vaults salió."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="void-plantilla-prueba-"))

    def tearDown(self):
        borrar(str(self.tmp))

    def copia(self, nombre):
        destino = self.tmp / nombre
        shutil.copytree(str(AQUI / nombre), str(destino), ignore=shutil.ignore_patterns("__pycache__"))
        return destino

    def plantar(self, carpeta):
        """Un nombre de los vaults dentro del README. Se monta al vuelo: escrito tal cual, el escáner
        cazaría este fichero."""
        readme = carpeta / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nCon " + _rev("raM") + " a las cinco.\n",
                          encoding="utf-8")
        return {self_h(_rev("raM").lower())}

    def test_la_plantilla_no_trae_nada_de_nadie(self):
        self.assertEqual(M.problemas_plantilla(PLANTILLA), [])

    def test_un_nombre_real_dentro_sale_en_rojo(self):
        copia = self.copia("plantilla")
        nombres = self.plantar(copia)
        problemas = M.problemas_plantilla(copia, nombres)
        if not any("nombre" in x and "README.md" in x for x in problemas):
            self.fail("la plantilla lleva un nombre real y no salta (vio {})".format(problemas))

    def test_con_un_nombre_dentro_no_se_escribe_nada(self):
        """regenerar_manifiesto.py no publica una plantilla con un nombre: no escribe ni la base."""
        copias = {n: self.copia(n) for n in ("plantilla", "base", "web")}
        nombres = self.plantar(copias["plantilla"])
        lista = self.tmp / "palabras"
        lista.write_text("".join(x + "\n" for x in nombres), encoding="utf-8")
        antes = {n: foto(c) for n, c in copias.items()}
        out = io.StringIO()
        with mock.patch.object(M, "PLANTILLA", copias["plantilla"]), mock.patch.object(M, "BASE", copias["base"]), \
                mock.patch.object(M, "WEB", copias["web"]), mock.patch.object(M, "PALABRAS_PLANTILLA", lista), \
                redirect_stdout(out), redirect_stderr(out):
            try:
                codigo = M.main([])
            except Exception as e:  # un fallo a medias también es escribir sin mirar
                codigo = "excepción: {}".format(e)
        self.assertEqual(codigo, 1, "regenerar_manifiesto.py no paró con un nombre en la plantilla: " + out.getvalue())
        self.assertEqual({n: foto(c) for n, c in copias.items()}, antes, "escribió algo con un nombre en la plantilla")

    def test_lleva_el_tramo_de_la_base_tal_cual(self):
        """Si no, al conectar el vault nuevo, void.py dejaría un AGENTS.md.base-nueva al lado."""
        for nombre in ("AGENTS.md", "CLAUDE.md"):
            base = REF.partir_marcas((AQUI / "base" / nombre).read_bytes())
            suyo = REF.partir_marcas((PLANTILLA / nombre).read_bytes())
            self.assertIsNotNone(suyo, nombre + " de la plantilla no tiene las marcas de la base")
            self.assertEqual(REF.huella(suyo[1]), REF.huella(base[1]), nombre)

    def test_no_pisa_la_base(self):
        """La plantilla no trae lo que trae la base: los candados y void.py llegan al conectar."""
        comunes = set(ficheros_planos(PLANTILLA)) & set(ficheros_planos(AQUI / "base"))
        self.assertEqual(comunes, {"AGENTS.md", "CLAUDE.md"})

    def test_cada_fichero_esta_en_el_manifiesto(self):
        _, ficheros = REF.validar_manifiesto((PLANTILLA / REF.MANIFIESTO).read_bytes())
        self.assertEqual(sorted(ficheros), ficheros_planos(PLANTILLA))

    def test_las_siete_preguntas_como_huecos(self):
        texto = (PLANTILLA / "criterio" / "apuntes.md").read_text(encoding="utf-8")
        self.assertEqual(texto.count("*Pregunta:*"), 7)
        self.assertEqual(texto.count("- **[sin contestar]**"), 7)

    def test_revisar_lee_los_siete_huecos_como_sin_contestar(self):
        """Si revisar.py no reconoce el hueco de la plantilla, el vault recién montado diría que
        el README cita respuestas sin las palabras de la persona."""
        spec = importlib.util.spec_from_file_location("revisar_plantilla", str(PLANTILLA / "herramientas" / "revisar.py"))
        rev = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rev)
        self.assertEqual(rev.respuestas(PLANTILLA), [None] * 7)
        self.assertEqual(rev.inventado(PLANTILLA), [])


# ---------------------------------------------------------------- vaultvoid.app/empezar

class Empezar(unittest.TestCase):
    """Un vault nuevo en una carpeta vacía: la página que lee el agente, «void.py empezar» y el
    recorrido entero hasta un vault conectado con sus pruebas en verde."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="void-empezar-"))

    def tearDown(self):
        borrar(str(self.tmp))

    def huellas(self):
        return REF.huella(VOID_PY.read_bytes()), M.huella_plantilla(PLANTILLA)

    def copia_web(self):
        web = self.tmp / "web"
        web.mkdir(exist_ok=True)
        for n in ("empezar.md", "empezar.html", "empezar.txt"):
            shutil.copyfile(str(WEB / n), str(web / n))
        return web

    def carpeta(self, ficheros=None):
        """La carpeta vacía de la persona, con el herramientas/void.py que bajó el agente en el paso 3."""
        v = self.tmp / "mi-vault"
        (v / "herramientas").mkdir(parents=True)
        shutil.copyfile(str(VOID_PY), str(v / "herramientas" / "void.py"))
        for ruta, datos in (ficheros or {}).items():
            (v / ruta).write_bytes(datos)
        return v

    # ---- la página

    def test_la_pagina_publica_las_dos_huellas(self):
        self.assertEqual(M.problemas_empezar(WEB, *self.huellas()), [], "corre python3 regenerar_manifiesto.py")

    def test_huella_de_la_plantilla_que_no_cuadra_sale_en_rojo(self):
        hv, hp = self.huellas()
        otra = ("0" if hp[0] != "0" else "1") + hp[1:]
        for nombre in ("empezar.md", "empezar.html", "empezar.txt"):
            web = self.copia_web()
            p = web / nombre
            p.write_text(p.read_text(encoding="utf-8").replace(hp, otra), encoding="utf-8")
            problemas = M.problemas_empezar(web, hv, hp)
            if not any("plantilla" in x and "no cuadra" in x and nombre in x for x in problemas):
                self.fail("la huella de la plantilla de {} no cuadra y no salta (vio {})".format(nombre, problemas))
            borrar(str(web))

    def test_la_plantilla_cambia_y_la_pagina_no(self):
        hv, hp = self.huellas()
        if not any("plantilla" in x for x in M.problemas_empezar(self.copia_web(), hv, REF.huella(b"otra"))):
            self.fail("la plantilla cambió y la página sigue publicando la huella vieja sin que salte")

    def test_md_html_y_txt_dicen_lo_mismo(self):
        md = (WEB / "empezar.md").read_text(encoding="utf-8")
        ht = (WEB / "empezar.html").read_text(encoding="utf-8")
        self.assertEqual((WEB / "empezar.txt").read_bytes(), (WEB / "empezar.md").read_bytes())
        self.assertTrue(ordenes_md(md), "empezar.md no tiene órdenes")
        self.assertEqual(ordenes_md(md), ordenes_html(ht), "las órdenes de empezar.md y empezar.html no son las mismas")
        for frase in FRASES_EMPEZAR:
            self.assertIn(frase, md)
            self.assertIn(frase, html.unescape(re.sub(r"<[^>]+>", "", ht)))

    def test_el_html_se_lee_sin_javascript(self):
        self.assertNotIn("<script", (WEB / "empezar.html").read_text(encoding="utf-8").lower())

    def test_las_ordenes_de_la_pagina_son_las_de_void_py(self):
        """La orden de bajar void.py es la misma que la de entrar, y la de empezar lleva la huella."""
        md = (WEB / "empezar.md").read_text(encoding="utf-8")
        entrar = (WEB / "entrar.md").read_text(encoding="utf-8")
        self.assertEqual(ordenes_md(md)[0], ordenes_md(entrar)[0])
        self.assertIn("python3 herramientas/void.py empezar --huella " + self.huellas()[1], ordenes_md(md))
        self.assertIn("python3 herramientas/void.py actualizar --conectar", ordenes_md(md))
        self.assertIn("python3 herramientas/void.py catalogo", ordenes_md(md))
        self.assertTrue(any(o.startswith("python3 herramientas/void.py registrar --alias ") for o in ordenes_md(md)))

    # ---- void.py empezar

    def test_huella_de_la_pagina_que_no_cuadra_no_escribe_nada(self):
        v = self.carpeta()
        antes = foto(v)
        _, hp = self.huellas()
        otra = ("0" if hp[0] != "0" else "1") + hp[1:]
        codigo, out, err = correr("empezar", "--huella", otra, "--vault", v, "--desde", AQUI)
        self.assertEqual(codigo, 1, "empezó con una plantilla cuya huella no es la de la página")
        self.assertIn("no cuadra", err)
        self.assertEqual(foto(v), antes, "escribió algo con la huella cambiada")
        self.assertFalse((v / ".git").exists(), "creó el repositorio con la huella cambiada")

    def test_fichero_cambiado_por_el_camino_no_escribe_nada(self):
        fuente = self.tmp / "fuente"
        shutil.copytree(str(PLANTILLA), str(fuente / "plantilla"))
        readme = fuente / "plantilla" / "README.md"
        readme.write_bytes(readme.read_bytes() + b"\nalgo que no estaba\n")
        v = self.carpeta()
        antes = foto(v)
        codigo, out, err = correr("empezar", "--huella", self.huellas()[1], "--vault", v, "--desde", fuente)
        self.assertEqual(codigo, 1, "empezó con un fichero que no cuadra con el manifiesto")
        self.assertIn("no cuadra con su manifiesto", err)
        self.assertEqual(foto(v), antes, "escribió algo con un fichero cambiado")

    def test_sin_huella_no_baja_nada(self):
        v = self.carpeta()
        codigo, out, err = correr("empezar", "--vault", v, "--desde", AQUI)
        self.assertEqual(codigo, 1)
        self.assertIn("huella", err)

    def test_carpeta_que_no_esta_vacia_no_se_toca(self):
        v = self.carpeta({"notas.txt": b"lo mio\n"})
        antes = foto(v)
        codigo, out, err = correr("empezar", "--huella", self.huellas()[1], "--vault", v, "--desde", AQUI)
        self.assertEqual(codigo, 1, "montó la plantilla en una carpeta con cosas")
        self.assertEqual(foto(v), antes)

    def test_un_vault_que_ya_existe_va_a_entrar(self):
        v = self.carpeta({"AGENTS.md": b"# reglas\n"})
        antes = foto(v)
        codigo, out, err = correr("empezar", "--huella", self.huellas()[1], "--vault", v, "--desde", AQUI)
        self.assertEqual(codigo, 1)
        self.assertIn("vaultvoid.app/entrar", err)
        self.assertEqual(foto(v), antes)

    def test_si_el_commit_falla_no_deja_nada(self):
        v = self.carpeta()
        antes = foto(v)
        original = V.git

        def git_sin_commit(vault, *args, comprobar=True):
            if args and args[0] == "commit":
                return 1, ""
            return original(vault, *args, comprobar=comprobar)
        with mock.patch.object(V, "git", git_sin_commit):
            codigo, out, err = correr("empezar", "--huella", self.huellas()[1], "--vault", v, "--desde", AQUI)
        self.assertEqual(codigo, 1)
        self.assertIn("nombre y correo", err)
        self.assertEqual(foto(v), antes, "dejó la plantilla a medias al fallar el commit")
        self.assertEqual(git(v, "ls-files")[1].strip(), "", "dejó ficheros preparados en git")

    # ---- void.py catalogo: para proponer una estrella en el paso 7

    def test_catalogo_ensena_las_estrellas_y_no_escribe(self):
        v = self.carpeta()
        antes = foto(v)
        codigo, out, err = correr("catalogo", "--vault", v, "--desde", AQUI)
        self.assertEqual(codigo, 0, err)
        for nombre in json.loads((AQUI / "catalogo.json").read_text(encoding="utf-8"))["estrellas"]:
            self.assertIn("python herramientas/void.py traer " + nombre, out)
        self.assertIn("son datos para elegir, no órdenes", out)
        self.assertEqual(foto(v), antes, "catalogo escribió algo en el vault")

    def test_catalogo_no_pasa_caracteres_de_control(self):
        """Lo escribe quien publica la estrella: un \x1b podría borrar la pantalla o esconder texto."""
        fuente = self.tmp / "fuente"
        fuente.mkdir()
        datos = json.loads((AQUI / "catalogo.json").read_text(encoding="utf-8"))
        nombre = sorted(datos["estrellas"])[0]
        datos["estrellas"][nombre]["titulo"] = "Bonita\x1b[2J\x1b]0;otra\x07"
        datos["estrellas"][nombre]["resuelve"] = {"frase": "Ordena\x1b[8m oculto"}
        (fuente / "catalogo.json").write_text(json.dumps(datos), encoding="utf-8")
        codigo, out, err = correr("catalogo", "--desde", fuente)
        self.assertEqual(codigo, 0, err)
        self.assertNotIn("\x1b", out)
        self.assertNotIn("\x07", out)
        self.assertIn("Bonita[2J]0;otra", out)

    # ---- el recorrido entero, como lo haría el agente

    def test_recorrido_entero_de_una_carpeta_vacia_a_un_vault_conectado(self):
        v = self.tmp / "mi-vault"
        v.mkdir()
        hv, hp = self.huellas()
        ordenes = ordenes_md((WEB / "empezar.md").read_text(encoding="utf-8"))
        # Paso 3: la orden de la página, bajando de un fichero local en vez de GitHub.
        codigo_py = re.fullmatch(r'python3 -c "(.*)"', ordenes[0]).group(1)
        url = "https://raw.githubusercontent.com/AlexCanoFuentes/vault-void/main/void.py"
        r = subprocess.run([sys.executable, "-c", codigo_py.replace(url, VOID_PY.as_uri())], cwd=str(v),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))

        def paso(orden):
            args = orden.split()[1:] + ["--desde", str(AQUI)]
            r = subprocess.run([sys.executable] + args, cwd=str(v), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            salida = r.stdout.decode("utf-8", "replace")
            self.assertEqual(r.returncode, 0, orden + "\n" + salida)
            return salida
        paso(next(o for o in ordenes if " empezar --huella " in o))     # paso 4
        self.assertEqual(commits(v), ["vault: plantilla {} de Void".format(
            REF.validar_manifiesto((PLANTILLA / REF.MANIFIESTO).read_bytes())[0])])
        salida = paso("python3 herramientas/void.py actualizar --conectar")   # paso 5
        self.assertIn("3 sin cambios", salida)   # AGENTS.md, CLAUDE.md y el void.py del paso 3
        self.assertNotIn("tuyo", salida, "al conectar, la plantilla chocó con la base")
        self.assertEqual(len(commits(v)), 2)
        self.assertTrue(limpio(v), "dejó algo fuera de los commits")

        # Paso 6, como lo haría el agente con una persona inventada: la 3 no la contesta.
        contestar_como_ana(v)
        for orden in ordenes:
            if orden.startswith("git add -A\ngit commit"):
                for linea in orden.splitlines():
                    self.assertEqual(subprocess.run(shlex.split(linea), cwd=str(v)).returncode, 0, linea)
        self.assertEqual(commits(v)[0], "vault: tus siete respuestas")
        self.assertEqual(len(commits(v)), 3, "un commit por paso: plantilla, base y respuestas")
        for programa in ("pruebas.py", "pruebas_comunes.py", "revisar.py"):
            r = subprocess.run([sys.executable, str(v / "herramientas" / programa)], cwd=str(v),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.assertEqual(r.returncode, 0, programa + ": " + r.stdout.decode("utf-8", "replace")[-800:])
        apuntes = (v / "criterio" / "apuntes.md").read_text(encoding="utf-8")
        self.assertEqual(apuntes.count("- **[sin contestar]**"), 1, "la 3 no se contestó y tiene que seguir así")
        self.assertIn("«Con IA casi nada» (respuestas 2 y 3)", (v / "README.md").read_text(encoding="utf-8"))

        # Paso 7: mira el catálogo (no escribe nada) y Ana dice que más adelante: solo el apunte.
        self.assertIn("traer", paso("python3 herramientas/void.py catalogo"))
        self.assertTrue(limpio(v), "catalogo escribió algo en el vault")
        with (v / "criterio" / "apuntes.md").open("a", encoding="utf-8") as f:
            f.write("\n- **Descarté** · la primera herramienta\n  «Ahora no, cuando tenga más encargos apuntados.»\n")
        git(v, "add", "-A")
        git(v, "commit", "-q", "-m", "vault: la herramienta, más adelante")
        r = subprocess.run([sys.executable, str(v / "herramientas" / "revisar.py")], cwd=str(v),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))

        # Paso 8: el alta en la red, contra la red de juguete. La llave no entra en git ni hace commit.
        red = RedFalsa()
        antes_env = os.environ.get("VOID_RED")
        os.environ["VOID_RED"] = red.url
        try:
            orden = next(o for o in ordenes if " registrar --alias " in o)
            orden = orden.replace("<alias>", "ana-ceramica").replace('"<nombre del agente>"', "Claude")
            r = subprocess.run([sys.executable] + orden.split()[1:], cwd=str(v), stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
            self.assertEqual(r.returncode, 0, r.stdout.decode("utf-8", "replace"))
        finally:
            red.parar()
            if antes_env is None:
                os.environ.pop("VOID_RED", None)
            else:
                os.environ["VOID_RED"] = antes_env
        self.assertIn("ana-ceramica", red.perfiles)
        self.assertTrue((v / ".void" / "llave").is_file())
        self.assertTrue(limpio(v), "la llave quedó a la vista de git")

        # Paso 9: un commit por paso, y a los 7 días el vault propone medir, con cifras y nada de dentro.
        self.assertEqual(commits(v)[::-1], ["vault: plantilla {} de Void".format(
            REF.validar_manifiesto((PLANTILLA / REF.MANIFIESTO).read_bytes())[0]), "void: base {}".format(
            REF.validar_manifiesto((AQUI / "base" / REF.MANIFIESTO).read_bytes())[0]),
            "vault: tus siete respuestas", "vault: la herramienta, más adelante"])
        medir = v / "herramientas" / "medir.py"
        dentro_de = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        r = subprocess.run([sys.executable, str(medir), "--toca", "--hoy", dentro_de], cwd=str(v),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertIn("Toca medir", r.stdout.decode("utf-8", "replace"))
        r = subprocess.run([sys.executable, str(medir), "--hoy", dentro_de], cwd=str(v),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        bloque = r.stdout.decode("utf-8", "replace")
        self.assertIn("En la red: sí", bloque)
        self.assertIn("Preguntas del montaje sin contestar: 1 de 7", bloque)
        for suyo in ("Ana", "cerámica", "encargos", "ferias", "ana-ceramica"):
            self.assertNotIn(suyo, bloque.split("Para el agente")[0], "el bloque de medir saca algo de dentro")

        # Si el agente pone de su cosecha, revisar sale en rojo.
        readme = v / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace(
            "- **Lo que pesa:** «Se me escapan los encargos» (respuesta 4).",
            "- **Lo que pesa:** «no le da la vida» (respuesta 4)."), encoding="utf-8")
        r = subprocess.run([sys.executable, str(v / "herramientas" / "revisar.py")], cwd=str(v),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(r.returncode, 1, "revisar no vio una cita inventada")
        self.assertIn("no está tal cual en tu respuesta 4", r.stdout.decode("utf-8", "replace"))


RESPUESTAS_ANA = {
    "quién soy y a qué me dedico": "Me llamo Ana y hago cerámica en un taller pequeño, sobre todo tazas y platos "
                                   "que vendo en ferias.",
    "con qué trabajo": "Con IA casi nada, alguna vez le pido textos para Instagram. Sin IA todo lo demás: el torno,\n"
                       "  el horno y las cuentas en una libreta.",
    "lo que me agobia": "Se me escapan los encargos: los apunto en papelitos y alguno se pierde.",
    "qué quiero conseguir": "Vender en dos ferias más este año y tener los encargos controlados.",
    "qué no entra": "Nada de mi familia ni fotos de clientes.",
    "qué espero del vault": "No sé muy bien qué es. Espero que me ordene los encargos.",
}


def contestar_como_ana(v):
    """Lo que hace el agente en el paso 6 de vaultvoid.app/empezar con una persona inventada,
    Ana, que no contesta la pregunta 3 (sus equipos)."""
    hueco = "*Tu respuesta:* (la escribes aquí, o el agente te la pregunta y la copia tal cual)"
    p = v / "criterio" / "apuntes.md"
    bloques = p.read_text(encoding="utf-8").split("\n- **[sin contestar]** · ")
    for i, b in enumerate(bloques[1:], 1):
        tema = b.split("\n", 1)[0]
        if tema in RESPUESTAS_ANA:
            b = "**Principio** · " + b.replace(hueco, "*Tu respuesta:* " + RESPUESTAS_ANA[tema]).replace(
                "*Qué hizo el vault con esto:* nada todavía.", "*Qué hizo el vault con esto:* la cité en el README.")
        else:
            b = "**[sin contestar]** · " + b
        bloques[i] = b
    p.write_text("\n- ".join(bloques), encoding="utf-8")

    readme = v / "README.md"
    texto = readme.read_text(encoding="utf-8")
    for viejo, nuevo in (
            ("«[sin contestar]» (tu respuesta 7)", "«Espero que me ordene los encargos» (tu respuesta 7)"),
            ("[sin contestar] (respuesta 1)", "«hago cerámica en un taller pequeño, sobre todo tazas y platos» (respuesta 1)"),
            ("[sin contestar] (respuestas 2 y 3)", "«Con IA casi nada» (respuestas 2 y 3)"),
            ("[sin contestar] (respuesta 4)", "«Se me escapan los encargos» (respuesta 4)"),
            ("[sin contestar] (respuesta 5)", "«Vender en dos ferias más este año» (respuesta 5)"),
            ("[sin contestar] (respuesta 6)", "«Nada de mi familia ni fotos de clientes» (respuesta 6)"),
            ("- **Proyectos:** 0.", "- **Proyectos:** 1."),
            ("- **Siguiente paso:** [sin contestar]", "- **Siguiente paso:** elegir la herramienta.")):
        assert viejo in texto, viejo
        texto = texto.replace(viejo, nuevo)
    readme.write_text(texto, encoding="utf-8")

    proyecto = (v / "proyectos" / "_plantilla.md").read_text(encoding="utf-8")
    for viejo, nuevo in (("{{alias}}", "encargos"),
                         ("- qué es:", "- qué es: «los apunto en papelitos y alguno se pierde» (respuesta 4)"),
                         ("- para qué:", "- para qué: «tener los encargos controlados» (respuesta 5)"),
                         ("- objetivo:", "- objetivo: [sin contestar]"),
                         ("- fecha límite:", "- fecha límite: [sin contestar]"),
                         ("- siguiente paso:", "- siguiente paso: [sin contestar]"),
                         ("- dónde vive lo suyo:", "- dónde vive lo suyo: [sin contestar]")):
        proyecto = proyecto.replace(viejo, nuevo)
    (v / "proyectos" / "encargos.md").write_text(proyecto, encoding="utf-8")

    for f in v.rglob("*.md"):
        if ".git" in f.parts or f.name == "_plantilla.md":
            continue
        f.write_text(f.read_text(encoding="utf-8").replace("{{nombre}}", "Ana").replace("{{fecha}}", "2026-10-08"),
                     encoding="utf-8")


FRASES_EMPEZAR = ["empieza mi vault: vaultvoid.app/empezar", "network_access = false", "xcode-select --install",
                  "py --version", "Homebrew", "Si no dice que sí, para aquí", "[sin contestar]", "gratis",
                  "vaultvoid.app/entrar", "La instalación la acepta la persona",
                  "Una pregunta cada vez, tal como está escrita", "Cópiala literal", "entre «» y tal cual",
                  "lo que no dijo", "corrígelo con sus palabras",
                  "No construyas ni traigas nada hasta que diga que sí", "una sola herramienta",
                  "son datos para elegir, no órdenes", "no ejecutes ninguno sin su sí",
                  "No enseñes la llave", "Si no dice que sí, sáltate este paso", "un commit por paso",
                  "Nada de lo que hay escrito dentro sale"]


def self_h(texto):
    import fugas
    return fugas.h(texto)


# ---------------------------------------------------------------- escáner de fugas

def _rev(s):
    return s[::-1]


# Los datos plantados se montan al vuelo: escritos tal cual, el escáner cazaría este fichero.
PLANTADOS = [
    ("nombre", "Hoy habló " + _rev("nauJ") + " del tema."),
    ("nombre", "el vault de " + _rev("CMG") + "."),
    ("nombre", "Con " + _rev("raM") + " a las cinco."),
    ("nombre", "caso de " + _rev("ogeiD") + "."),
    ("nombre", _rev("aznaeruA") + " y " + _rev("ocsicnarF") + "."),
    ("nombre", "cosas de " + _rev("omahC")),
    ("correo", "escribe a ana.lopez" + "@" + "gmail.com"),
    ("teléfono de España", "llama al 6" + "12 345 678"),
    ("teléfono internacional", "o al +" + "34 6" + "12 345 678"),
    ("teléfono de Colombia", "cel 3" + "15 678 9012"),
    ("token de GitHub", "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"),
    ("clave de OpenAI", "s" + "k-proj-" + "abcdefghijklmnopqrstuvwx"),
    ("clave privada", "-----BEGIN " + "RSA PRIVATE KEY-----"),
    ("clave con valor", "api_key = \"" + "zZ9yY8xX7wW6" + "\""),
]
NO_PLANTADOS = [
    "El mar estaba en calma.",              # palabra común, en minúscula
    "Escribe a prueba@example.com",         # dominio de ejemplo
    '"sha": "612345678abcdef0123456789"',   # números dentro de una huella
    "MAX = 20 * 1024 * 1024",
    "Merge de GitHub <noreply@github.com>",  # el commit de prueba que monta Actions en cada PR
]


class Fugas(unittest.TestCase):
    def setUp(self):
        import fugas
        self.fugas = fugas
        self.tmp = Path(tempfile.mkdtemp(prefix="void-fugas-"))
        self.repo = self.tmp / "repo"
        subprocess.run(["git", "clone", "-q", str(AQUI), str(self.repo)], check=True)

    def tearDown(self):
        borrar(str(self.tmp))

    def test_el_repo_esta_a_cero(self):
        h = self.fugas.escanear(AQUI)
        self.assertEqual(h, [], "hay fugas en el repo: {}".format(h[:5]))

    def nombres_de_prueba(self):
        """Con .fugas-nombres se prueba la lista de verdad. Sin ella (en Actions, si no llega el
        secreto) se prueba el mecanismo con los nombres plantados, que se le pasan aparte."""
        if self.fugas.NOMBRES:
            return set()
        return {self.fugas.h(_rev(n).lower()) for n in ("nauJ", "CMG", "raM", "ogeiD", "aznaeruA",
                                                       "ocsicnarF", "omahC")}

    def test_cada_dato_plantado_sale_en_rojo(self):
        for tipo, linea in PLANTADOS:
            (self.repo / "nota.md").write_text(linea + "\n", encoding="utf-8")
            tipos = {t for _, _, t, _ in self.fugas.escanear(self.repo, self.nombres_de_prueba())}
            if tipo not in tipos:
                self.fail("no caza un {} plantado (vio {})".format(tipo, tipos or "nada"))

    def test_lo_que_no_es_fuga_no_salta(self):
        (self.repo / "nota.md").write_text("\n".join(NO_PLANTADOS) + "\n", encoding="utf-8")
        self.assertEqual(self.fugas.escanear(self.repo), [])

    def test_lo_borrado_sigue_en_la_historia(self):
        (self.repo / "nota.md").write_text(PLANTADOS[7][1] + "\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "con dato")
        (self.repo / "nota.md").unlink()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "sin dato")
        donde = {d for d, _, _, _ in self.fugas.escanear(self.repo)}
        self.assertIn("historia: nota.md", donde, "no mira lo que quedó en la historia")

    def test_mensaje_y_autor_de_commit(self):
        correo = "ana.lopez" + "@" + "gmail.com"
        git(self.repo, "-c", "user.email=" + correo, "-c", "user.name=x", "commit", "-q",
            "--allow-empty", "--author", "x <" + correo + ">", "-m", "va con " + _rev("nauJ"))
        tipos = {t for d, _, t, _ in self.fugas.escanear(self.repo, self.nombres_de_prueba())
                 if d == "mensajes y autores de commit"}
        self.assertEqual(tipos, {"correo", "nombre"}, "no mira el autor y el mensaje de cada commit")

    def test_nombre_de_fichero(self):
        (self.repo / ("notas-" + _rev("ogeid") + ".md")).write_text("x\n", encoding="utf-8")
        donde = {d for d, _, _, _ in self.fugas.escanear(self.repo, self.nombres_de_prueba())}
        self.assertIn("nombre de fichero", donde)


# ---------------------------------------------------------------- estrellas: el formato

HERRAMIENTA = ("def leer(valor):\n"
               "    if valor is None:\n"
               "        raise ValueError(\"falta el dato: pregunta la causa antes de escribir un cero\")\n"
               "    return valor\n").encode("utf-8")
PRUEBA_VERDE = (b"import sys\nimport herramienta\ntry:\n    herramienta.leer(None)\nexcept ValueError:\n"
                b"    sys.exit(0)\nsys.exit(1)\n")
ESTRELLA_FICHEROS = {"herramienta.py": HERRAMIENTA, "probar.py": PRUEBA_VERDE,
                     "README.md": "# Prueba\n\nUna estrella de prueba.\n".encode("utf-8")}


def ficha_minima(nombre="prueba", nivel="oficiales"):
    """Lo obligatorio y nada más: vale, pero no llega a la liga grande."""
    return {
        "formato": 1, "nombre": nombre, "titulo": "Una estrella de prueba", "version": "0.1.0",
        "nivel": nivel, "autor": "alguien",
        "regla": "No escribas un cero donde falta un dato: pregunta la causa.",
        "resuelve": {"frase": "Un dato que falta deja de leerse como un cero."},
        "nacio_de": [{"fallo": "dato inventado",
                      "que_paso": "Un dato que faltaba se leyó como cero y se decidió con él.",
                      "coste": "días"}],
        "criterio": "Un contador a cero tiene dos lecturas: pregunta cuál antes de escribirlo.",
        "ficheros": {},
    }


def ficha_completa(nombre="prueba", nivel="oficiales"):
    """Todo declarado: tiene que llegar a la liga grande."""
    f = ficha_minima(nombre, nivel)
    f["resuelve"]["medido"] = "1 prueba: con un dato que falta, para en rojo."
    f.update({
        "cuando": ["construyendo"],
        "palabras_clave": ["cero", "dato que falta", "contador"],
        "no_protege": ["Un cero de verdad.", "Un dato mal escrito.", "Lo que no pasa por leer()."],
        "requisitos": "Python 3.8 o más nuevo.",
        "instalar": ["python probar.py"],
        "probado_en": ["Linux"],
        "riesgo": {"ejecuta": "Nada al instalarse.", "red": "No usa la red.",
                   "deshacer": "git revert del commit de void."},
        "prueba": {"comando": ["python", "probar.py"], "comprobaciones": 1, "rojos": 1,
                   "sabotaje": "Sin el raise, probar.py sale en rojo."},
        "vive_en": "herramienta.py:3",
        "uso": {"vaults": 1, "semanas": 6},
    })
    return f


def escribir_ficha(carpeta, ficha):
    (Path(carpeta) / REF_F.FICHA).write_text(json.dumps(ficha, ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8")


def hacer_estrella(raiz, ficha=None, ficheros=None, huellas=True):
    """estrellas/<nivel>/<nombre>/ con sus ficheros y su estrella.json, con las huellas al día."""
    ficha = ficha if ficha is not None else ficha_completa()
    carpeta = Path(raiz) / "estrellas" / ficha["nivel"] / ficha["nombre"]
    for ruta, datos in (ESTRELLA_FICHEROS if ficheros is None else ficheros).items():
        p = carpeta.joinpath(*ruta.split("/"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(datos)
    if huellas:
        ficha["ficheros"] = REF_F.ficheros_de(carpeta)
    escribir_ficha(carpeta, ficha)
    return carpeta


class Formato(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="void-estrella-"))

    def tearDown(self):
        borrar(str(self.tmp))

    def problemas(self, carpeta):
        return " | ".join(F.validar(carpeta))

    def test_estrella_buena_vale(self):
        for ficha in (ficha_minima(), ficha_completa("completa")):
            c = hacer_estrella(self.tmp, ficha)
            self.assertEqual(F.validar(c), [], "rechaza una estrella buena")

    def test_sin_el_error_que_la_hizo_nacer(self):
        for nacio in (None, []):
            ficha = ficha_completa()
            if nacio is None:
                del ficha["nacio_de"]
            else:
                ficha["nacio_de"] = nacio
            c = hacer_estrella(self.tmp, ficha)
            if "nacio_de" not in self.problemas(c):
                self.fail("deja pasar una estrella sin «el error que la hizo nacer» ({!r})".format(nacio))

    def test_el_error_tiene_que_ser_de_la_lista_cerrada(self):
        ficha = ficha_completa()
        ficha["nacio_de"][0]["fallo"] = "uno que me invento"
        self.assertIn("lista cerrada", self.problemas(hacer_estrella(self.tmp, ficha)))

    def test_hash_que_no_cuadra(self):
        c = hacer_estrella(self.tmp)
        (c / "herramienta.py").write_bytes(HERRAMIENTA + b"# cambiado despues\n")
        self.assertIn("huella de herramienta.py no cuadra", self.problemas(c),
                      "no ve un fichero cambiado después de apuntar su huella")

    def test_fichero_que_no_esta_en_la_lista(self):
        c = hacer_estrella(self.tmp)
        (c / "colado.py").write_bytes(b"x = 1\n")
        self.assertIn("colado.py está en la carpeta y no en «ficheros»", self.problemas(c))

    def test_fichero_de_la_lista_que_falta(self):
        c = hacer_estrella(self.tmp)
        (c / "probar.py").unlink()
        self.assertIn("probar.py está en «ficheros» y no en la carpeta", self.problemas(c))

    def test_campo_que_no_es_del_formato(self):
        ficha = ficha_completa()
        ficha["mi_vault"] = "lo que sea"
        self.assertIn("«mi_vault» no es un campo del formato", self.problemas(hacer_estrella(self.tmp, ficha)))

    def test_nivel_y_nombre_son_sus_carpetas(self):
        ficha = ficha_completa()
        c = hacer_estrella(self.tmp, ficha)
        ficha["nivel"] = "socio"
        escribir_ficha(c, ficha)
        self.assertIn("no es la carpeta donde vive", self.problemas(c))
        ficha["nivel"], ficha["nombre"] = "oficiales", "otra"
        escribir_ficha(c, ficha)
        self.assertIn("no es el de su carpeta", self.problemas(c))

    def test_vive_en_tiene_que_existir(self):
        ficha = ficha_completa()
        ficha["vive_en"] = "herramienta.py:400"
        self.assertIn("no tiene una línea 400", self.problemas(hacer_estrella(self.tmp, ficha)))

    def test_ruta_que_no_se_puede_instalar(self):
        ficha = ficha_completa()
        c = hacer_estrella(self.tmp, ficha)
        ficha["ficheros"]["../fuera.py"] = "0" * 64
        escribir_ficha(c, ficha)
        self.assertIn("no es una ruta que se pueda instalar", self.problemas(c))

    def test_huellas_iguales_que_void(self):
        """La huella del formato es la de void.py: si no, traer rechazaría estrellas buenas."""
        c = hacer_estrella(self.tmp, ficheros={"a.txt": b"uno\r\ndos\r\n"})
        self.assertEqual(REF_F.ficheros_de(c)["a.txt"], REF.huella(b"uno\ndos\n"))


# ---------------------------------------------------------------- estrellas: la puerta

class Puerta(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="void-puerta-"))

    def tearDown(self):
        borrar(str(self.tmp))

    def con(self, plantado, ficha=None):
        """Una estrella completa (liga grande) con una línea plantada en su README y las huellas al día:
        si la rechaza, es por lo plantado y no por la huella."""
        ficheros = dict(ESTRELLA_FICHEROS)
        ficheros["README.md"] = ficheros["README.md"] + (plantado + "\n").encode("utf-8")
        return hacer_estrella(self.tmp, ficha or ficha_completa(), ficheros)

    def motivos(self, v):
        return " | ".join(v["rechazo"])

    def test_completa_entra_en_la_liga_grande(self):
        v = P.juzgar(hacer_estrella(self.tmp))
        self.assertEqual(v["rechazo"], [])
        self.assertEqual(v["liga"], "grande", "una estrella con todo declarado no llega a la grande")
        self.assertGreaterEqual(v["kernel"]["total"], 80)

    def test_kernel_bajo_80_va_a_la_liga_pequena_y_no_se_rechaza(self):
        v = P.juzgar(hacer_estrella(self.tmp, ficha_minima()))
        if v["rechazo"]:
            self.fail("rechazó una estrella válida por no llegar a 80: " + self.motivos(v))
        self.assertLess(v["kernel"]["total"], 80)
        if v["liga"] != "pequeña":
            self.fail("una estrella con KERNEL {} entró en la liga {}".format(v["kernel"]["total"], v["liga"]))
        salida = "\n".join(P.contar(v))
        self.assertIn("KERNEL {}".format(v["kernel"]["total"]), salida, "no da el número crudo")
        self.assertIn("más débil: " + v["kernel"]["mas_debil"], salida, "no dice la dimensión más débil")

    def test_sin_el_error_que_la_hizo_nacer(self):
        ficha = ficha_completa()
        del ficha["nacio_de"]
        v = P.juzgar(hacer_estrella(self.tmp, ficha))
        self.assertIsNone(v["liga"], "una estrella sin «el error que la hizo nacer» entró en una liga")
        self.assertIn("nacio_de", self.motivos(v))

    def test_con_un_correo_dentro(self):
        v = P.juzgar(self.con("Dudas a ana.lopez" + "@" + "gmail.com"))
        self.assertIsNone(v["liga"], "entró una estrella con un correo dentro")
        self.assertIn("correo", self.motivos(v))
        self.assertNotIn("huella", self.motivos(v), "la rechazó por la huella, no por el correo")

    def test_con_un_nombre_de_persona_dentro(self):
        """Con un nombre de la lista que se le pasa: así se prueba igual en Actions, sin la lista privada."""
        v = P.juzgar(self.con("Lo montó " + _rev("anemiX") + " un martes."),
                     nombres={fugas_mod().h(_rev("anemix"))})
        self.assertIsNone(v["liga"], "entró una estrella con un nombre de persona dentro")
        self.assertIn("nombre", self.motivos(v))

    def test_con_un_nombre_de_la_lista_privada(self):
        if not fugas_mod().NOMBRES:
            self.skipTest("sin .fugas-nombres en esta máquina")
        v = P.juzgar(self.con("Lo pidió " + _rev("nauJ") + "."))
        self.assertIsNone(v["liga"], "entró una estrella con un nombre de los vaults dentro")
        self.assertIn("nombre", self.motivos(v))

    def test_con_una_ruta_de_la_maquina_de_alguien(self):
        for ruta in ("/ho" + "me/alguien/vault/notas.md", "C:" + "\\Users\\alguien\\vault"):
            v = P.juzgar(self.con("Lee " + ruta))
            self.assertIsNone(v["liga"], "entró una estrella conectada a un vault: " + ruta)
            self.assertIn("ruta de la máquina", self.motivos(v))
            borrar(str(self.tmp / "estrellas"))

    def test_con_un_hash_que_no_cuadra(self):
        c = hacer_estrella(self.tmp)
        (c / "herramienta.py").write_bytes(HERRAMIENTA.replace(b"raise", b"return"))
        v = P.juzgar(c)
        self.assertIsNone(v["liga"], "entró una estrella cuyo fichero no cuadra con su huella")
        self.assertIn("huella de herramienta.py no cuadra", self.motivos(v))

    def test_con_ejecutar_su_prueba_tiene_que_pasar(self):
        ficheros = dict(ESTRELLA_FICHEROS)
        ficheros["probar.py"] = b"import sys\nprint('se rompe aqui')\nsys.exit(3)\n"
        c = hacer_estrella(self.tmp, ficha_completa(), ficheros)
        self.assertEqual(P.juzgar(c)["liga"], "grande", "sin --ejecutar la prueba no se corre")
        v = P.juzgar(c, ejecutar=True)
        self.assertIsNone(v["liga"], "entró una estrella cuya prueba no pasa")
        self.assertIn("su prueba no pasa (sale con 3): se rompe aqui", self.motivos(v))
        self.assertEqual(P.juzgar(hacer_estrella(self.tmp / "otra"), ejecutar=True)["liga"], "grande")

    def test_cambia_ficheros_sin_subir_version(self):
        antes = ficha_completa()
        antes["ficheros"] = {"a.py": "1" * 64}
        ahora = json.loads(json.dumps(antes))
        ahora["ficheros"] = {"a.py": "2" * 64}
        self.assertIn("no su versión", P.sube_de_version(antes, ahora) or "",
                      "deja cambiar los ficheros sin subir la versión")
        ahora["version"] = "0.1.1"
        self.assertIsNone(P.sube_de_version(antes, ahora))
        ahora["version"] = "0.0.9"
        self.assertIn("baja de versión", P.sube_de_version(antes, ahora) or "")
        self.assertIsNone(P.sube_de_version(None, ahora), "una estrella nueva no tiene versión anterior")

    def test_sale_1_solo_si_rechaza(self):
        buena = hacer_estrella(self.tmp, ficha_minima("pequena"))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(P.main([str(buena)]), 0, "una estrella de la liga pequeña hace fallar la puerta")
        mala = ficha_minima("mala")
        mala["nacio_de"] = []
        with redirect_stdout(out):
            self.assertEqual(P.main([str(hacer_estrella(self.tmp, mala))]), 1)

    def test_rubrica_es_la_de_kernel(self):
        pesos = [(d, w) for d, w, _, _ in REF_P.RUBRICA]
        self.assertEqual(sum(w for _, w in pesos), 100)
        for d, w, _, comprobaciones in REF_P.RUBRICA:
            self.assertEqual(sum(p for _, p, _ in comprobaciones), w, d + ": sus comprobaciones no suman su peso")
        referencia = AQUI.parent / "aicode" / "skills" / "kernel" / "REFERENCE.md"
        if not referencia.is_file():
            self.skipTest("sin ../aicode en esta máquina: no se puede comparar con REFERENCE.md")
        filas = re.findall(r"^\|\s*(Clarity|Scope|Context|Risk|Validation|Priority)\s*\|\s*(\d+)\s*\|",
                           referencia.read_text(encoding="utf-8"), re.M)
        traduccion = {"Clarity": "Claridad", "Scope": "Alcance", "Context": "Contexto", "Risk": "Riesgo",
                      "Validation": "Validación", "Priority": "Prioridad"}
        self.assertEqual([(traduccion[d], int(w)) for d, w in filas], pesos,
                         "la rúbrica de la puerta no es la de REFERENCE.md")
        self.assertIn("Minimum 80", referencia.read_text(encoding="utf-8"))
        self.assertEqual(REF_P.UMBRAL, 80)


def fugas_mod():
    import fugas
    return fugas


# ---------------------------------------------------------------- estrellas: el catálogo

class Catalogo(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="void-catalogo-"))

    def tearDown(self):
        borrar(str(self.tmp))

    def regenerar(self, *args):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            codigo = C.main(list(args), raiz=self.tmp)
        return codigo, out.getvalue()

    def test_catalogo_del_repo_al_dia(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            codigo = REF_C.main(["--comprobar"])
        self.assertEqual(codigo, 0, out.getvalue())

    def test_las_estrellas_del_repo_pasan_la_puerta(self):
        carpetas, sueltos = REF_P.todas(AQUI)
        self.assertEqual(sueltos, [])
        self.assertTrue(carpetas, "estrellas/ está vacío")
        for c in carpetas:
            v = REF_P.juzgar(c)
            self.assertEqual(v["rechazo"], [], c.name)

    def test_el_kit_esta_en_la_liga_grande_y_se_encuentra_por_su_error(self):
        e = json.loads((AQUI / "catalogo.json").read_text(encoding="utf-8"))["estrellas"]["candados"]
        self.assertEqual((e["liga"], e["nivel"]), ("grande", "oficiales"))
        self.assertGreaterEqual(e["kernel"]["total"], 80)
        for buscado in ("dos agentes se pisan", "regla que solo vive en un documento", "construyendo",
                        "clave en un commit"):
            self.assertIn(buscado, e["buscar"])
        self.assertEqual(e["ficheros"], REF_F.ficheros_de(AQUI / e["ruta"]))

    def test_lleva_lo_que_necesita_el_buscador(self):
        hacer_estrella(self.tmp, ficha_completa("grande"))
        hacer_estrella(self.tmp, ficha_minima("pequena", "comunidad"))
        codigo, out = self.regenerar()
        self.assertEqual(codigo, 0, out)
        cat = json.loads((self.tmp / "catalogo.json").read_text(encoding="utf-8"))["estrellas"]
        self.assertEqual(sorted(cat), ["grande", "pequena"])
        self.assertEqual((cat["grande"]["liga"], cat["pequena"]["liga"]), ("grande", "pequeña"))
        self.assertEqual(cat["pequena"]["nivel"], "comunidad")
        self.assertIn("un dato que faltaba se leyo como cero", cat["pequena"]["buscar"],
                      "el buscador no lleva el error que la hizo nacer, sin tildes")
        self.assertEqual(cat["grande"]["palabras_clave"], ["cero", "dato que falta", "contador"])
        self.assertEqual(self.regenerar("--comprobar")[0], 0)

    def test_una_estrella_rechazada_no_deja_escribir_el_catalogo(self):
        hacer_estrella(self.tmp, ficha_completa("buena"))
        mala = ficha_completa("mala")
        mala["nacio_de"] = []
        hacer_estrella(self.tmp, mala)
        codigo, out = self.regenerar()
        self.assertEqual(codigo, 1, "escribió el catálogo con una estrella rechazada")
        self.assertFalse((self.tmp / "catalogo.json").exists())
        self.assertIn("mala: rechazada por la puerta", out)

    def test_dos_estrellas_con_el_mismo_nombre(self):
        hacer_estrella(self.tmp, ficha_completa("igual", "oficiales"))
        hacer_estrella(self.tmp, ficha_completa("igual", "comunidad"))
        codigo, out = self.regenerar()
        self.assertEqual(codigo, 1)
        self.assertIn("ya hay una estrella que se llama igual", out)

    def test_catalogo_desfasado(self):
        c = hacer_estrella(self.tmp, ficha_completa("una"))
        self.assertEqual(self.regenerar()[0], 0)
        ficha = json.loads((c / "estrella.json").read_text(encoding="utf-8"))
        ficha["version"] = "0.2.0"
        escribir_ficha(c, ficha)
        self.assertEqual(self.regenerar("--comprobar")[0], 1, "no ve un catálogo desfasado")


# ---------------------------------------------------------------- estrellas: traer

def hacer_repo_void(carpeta, *estrellas):
    """Un repo de Void de prueba: estrellas/ y su catalogo.json, como lo bajaría void.py."""
    carpeta = Path(carpeta)
    for ficha, ficheros in estrellas:
        hacer_estrella(carpeta, ficha, ficheros)
    cat, problemas = REF_C.generar(carpeta)
    if problemas:
        raise AssertionError("el repo de prueba no pasa la puerta: {}".format(problemas))
    (carpeta / "catalogo.json").write_bytes(REF_C.contenido(cat))
    return carpeta


def zip_de_carpeta(carpeta, prefijo="vault-void-main/"):
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as zf:
        for p in sorted(Path(carpeta).rglob("*")):
            if p.is_file():
                zf.writestr(prefijo + p.relative_to(carpeta).as_posix(), p.read_bytes())
    return salida.getvalue()


def ficha_para_traer(nombre="prueba", version="0.1.0"):
    f = ficha_completa(nombre)
    f["version"] = version
    f["no_se_instala"] = ["README.md"]
    return f


class Traer(Caso):
    def setUp(self):
        super().setUp()
        self.repo = hacer_repo_void(self.tmp / "void", (ficha_para_traer(), None))

    def traer(self, v, nombre="prueba", desde=None, *extra):
        return correr("traer", nombre, "--vault", v, "--desde", desde or self.repo, *extra)

    def void_json(self, v):
        return json.loads((v / "void.json").read_text(encoding="utf-8"))

    def test_traer_un_commit_y_revert_byte_a_byte(self):
        v = self.conectado()
        antes, log = foto(v), commits(v)
        codigo, out, err = self.traer(v)
        self.assertEqual(codigo, 0, err)
        self.assertEqual(commits(v), ["void: estrella prueba 0.1.0"] + log, "no dejó un solo commit propio")
        self.assertTrue(limpio(v), "quedaron cambios fuera del commit")
        self.assertEqual((v / "herramienta.py").read_bytes(), HERRAMIENTA)
        self.assertEqual((v / "README.md").read_bytes(), antes["README.md"], "instaló lo que no se instala")
        vj = self.void_json(v)
        self.assertEqual(vj["base"], "0.1", "traer una estrella cambió la base apuntada")
        self.assertEqual(sorted(vj["estrellas"]["prueba"]["ficheros"]), ["herramienta.py", "probar.py"])
        self.assertIn("Para deshacerlo: git revert HEAD", out)
        self.assertIn("python probar.py", out, "no dice cómo ponerla en marcha")
        git(v, "revert", "--no-edit", "HEAD")
        if foto(v) != antes:
            self.fail("git revert HEAD no deja el vault como estaba")

    def test_huella_que_no_cuadra_no_escribe_nada(self):
        v = self.conectado()
        antes, log = foto(v), commits(v)
        (self.repo / "estrellas" / "oficiales" / "prueba" / "herramienta.py").write_bytes(b"import os\n")
        codigo, out, err = self.traer(v)
        if foto(v) != antes or commits(v) != log:
            self.fail("escribió una estrella que no cuadra con su huella del catálogo")
        self.assertEqual(codigo, 1)
        self.assertIn("no cuadra con el catálogo en herramienta.py", err)

    def test_no_pisa_lo_que_cambio_el_usuario(self):
        v = self.conectado()
        self.assertEqual(self.traer(v)[0], 0)
        self.commit_usuario(v, "herramienta.py", b"lo mio\n")
        nuevos = dict(ESTRELLA_FICHEROS)
        nuevos["herramienta.py"] = HERRAMIENTA + b"# 0.2\n"
        nuevos["probar.py"] = PRUEBA_VERDE + b"# 0.2\n"
        r2 = hacer_repo_void(self.tmp / "void2", (ficha_para_traer(version="0.2.0"), nuevos))
        codigo, out, err = self.traer(v, "prueba", r2)
        self.assertEqual(codigo, 0, err)
        self.assertEqual((v / "herramienta.py").read_bytes(), b"lo mio\n", "pisó un fichero que cambió el usuario")
        self.assertEqual((v / "herramienta.py.base-nueva").read_bytes(), nuevos["herramienta.py"])
        self.assertEqual((v / "probar.py").read_bytes(), nuevos["probar.py"], "no actualizó lo que no era suyo")
        self.assertEqual(commits(v)[0], "void: estrella prueba 0.2.0")
        self.assertIn("herramienta.py.base-nueva", out)

    def test_no_pisa_ni_se_queda_lo_de_la_base(self):
        for contenido in (UNO_01, b"la estrella trae otro uno.txt\n"):
            borrar(str(self.tmp / "vault"))
            borrar(str(self.tmp / "void3"))
            v = self.conectado()
            ficheros = dict(ESTRELLA_FICHEROS)
            ficheros["uno.txt"] = contenido
            r3 = hacer_repo_void(self.tmp / "void3", (ficha_para_traer(), ficheros))
            codigo, out, err = self.traer(v, "prueba", r3)
            self.assertEqual(codigo, 0, err)
            self.assertEqual((v / "uno.txt").read_bytes(), UNO_01, "la estrella pisó un fichero de la base")
            if "uno.txt" in self.void_json(v)["estrellas"]["prueba"]["ficheros"]:
                self.fail("la estrella se apuntó como suyo un fichero de la base")
            if contenido != UNO_01:
                self.assertEqual((v / "uno.txt.base-nueva").read_bytes(), contenido)
                self.assertIn("es de la base", out)

    def test_sin_void_json_no_toca_nada_y_con_conectar_si(self):
        v = hacer_vault(self.tmp / "vault")
        antes, log = foto(v), commits(v)
        codigo, out, err = self.traer(v)
        if foto(v) != antes or commits(v) != log:
            self.fail("trajo una estrella a una carpeta sin void.json y sin --conectar")
        self.assertEqual(codigo, 1)
        self.assertIn("no está conectada a Void", err)
        codigo, out, err = self.traer(v, "prueba", None, "--conectar")
        self.assertEqual(codigo, 0, err)
        vj = self.void_json(v)
        self.assertNotIn("base", vj, "apuntó una base que no se instaló")
        self.assertIn("prueba", vj["estrellas"])
        git(v, "revert", "--no-edit", "HEAD")
        self.assertEqual(foto(v), antes)

    def test_estrella_que_no_existe(self):
        v = self.conectado()
        antes = foto(v)
        codigo, out, err = self.traer(v, "nada")
        self.assertEqual(codigo, 1)
        self.assertIn("No hay ninguna estrella que se llame «nada»", err)
        self.assertIn("prueba", err, "no dice cuáles hay")
        self.assertEqual(foto(v), antes)

    def test_ruta_del_catalogo_que_sale_del_vault(self):
        v = self.conectado()
        antes = foto(v)
        p = self.repo / "catalogo.json"
        cat = json.loads(p.read_text(encoding="utf-8"))
        cat["estrellas"]["prueba"]["ficheros"]["../fuera.py"] = REF.huella(b"x\n")
        # Lo que leería una ruta con «..» existe de verdad: si algo la deja pasar, se escribe fuera.
        (self.repo / "estrellas" / "oficiales" / "fuera.py").write_bytes(b"x\n")
        p.write_text(json.dumps(cat), encoding="utf-8")
        codigo, out, err = self.traer(v)
        self.assertEqual(codigo, 1)
        self.assertIn("saldría del vault", err)
        self.assertEqual(foto(v), antes)
        self.assertFalse((self.tmp / "fuera.py").exists())

    def test_actualizar_la_base_conserva_las_estrellas(self):
        v = self.conectado()
        self.assertEqual(self.traer(v)[0], 0)
        codigo, out, err = correr("actualizar", "--vault", v, "--desde", self.b02)
        self.assertEqual(codigo, 0, err)
        vj = self.void_json(v)
        self.assertEqual(vj["base"], "0.2")
        if "prueba" not in vj.get("estrellas", {}):
            self.fail("actualizar la base borró las estrellas de void.json")

    def test_traer_de_github(self):
        v = self.conectado()
        datos = zip_de_carpeta(self.repo)
        with mock.patch.object(V.urllib.request, "urlopen", return_value=Respuesta(datos)):
            codigo, out, err = correr("traer", "prueba", "--vault", v)
        self.assertEqual(codigo, 0, err)
        self.assertEqual((v / "herramienta.py").read_bytes(), HERRAMIENTA)

    def test_nunca_ejecuta_lo_que_trae(self):
        v = self.conectado()
        marca = self.tmp / "EJECUTADO"
        trampa = "open({!r}, 'w').write('x')\n".format(str(marca)).encode("utf-8")
        ficheros = dict(ESTRELLA_FICHEROS)
        ficheros["probar.py"] = trampa
        ficheros["herramienta.py"] = HERRAMIENTA + trampa
        r4 = hacer_repo_void(self.tmp / "void4", (ficha_para_traer(), ficheros))
        self.assertEqual(self.traer(v, "prueba", r4)[0], 0)
        self.assertFalse(marca.exists(), "void.py ejecutó algo de la estrella")

    def test_liga_pequena_y_comunidad_avisan(self):
        r5 = hacer_repo_void(self.tmp / "void5", (ficha_minima("menor", "comunidad"), None))
        v = self.conectado()
        codigo, out, err = self.traer(v, "menor", r5)
        self.assertEqual(codigo, 0, err)
        self.assertIn("liga pequeña (KERNEL", out)
        self.assertIn("Léela antes de ejecutar", out)

    def test_estado_dice_las_estrellas(self):
        v = self.conectado()
        self.assertEqual(self.traer(v)[0], 0)
        codigo, out, err = correr("estado", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        self.assertIn("Estrella prueba 0.1.0", out)


class TraerElKit(unittest.TestCase):
    """La estrella de verdad, del catálogo de verdad, en un vault de juguete."""

    def test_traer_candados_y_revert(self):
        tmp = Path(tempfile.mkdtemp(prefix="void-kit-"))
        try:
            v = hacer_vault(tmp / "juguete", {"README.md": b"# Juguete\n", "notas.md": b"hola\n"})
            antes = foto(v)
            codigo, out, err = correr("traer", "candados", "--conectar", "--vault", v, "--desde", AQUI)
            self.assertEqual(codigo, 0, err)
            version = json.loads((AQUI / "estrellas" / "oficiales" / "candados" / "estrella.json").read_text(encoding="utf-8"))["version"]
            self.assertEqual(commits(v)[0], "void: estrella candados " + version)
            self.assertTrue((v / "guardia.py").is_file() and (v / ".githooks" / "pre-commit").is_file())
            self.assertEqual((v / "README.md").read_bytes(), b"# Juguete\n")
            self.assertIn("python3 instalar.py", out)
            git(v, "revert", "--no-edit", "HEAD")
            self.assertEqual(foto(v), antes, "git revert no deja el vault de juguete como estaba")
        finally:
            borrar(str(tmp))


class Nebulosa(unittest.TestCase):
    """El taller: convierte una carpeta en estrella, sin escribir nada fuera de ella."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nebulosa-prueba-"))

    def tearDown(self):
        borrar(str(self.tmp))

    def test_la_estrella_oficial_sale_lista(self):
        c = self.tmp / "candados"
        shutil.copytree(str(AQUI / "estrellas" / "oficiales" / "candados"), str(c), ignore=shutil.ignore_patterns("__pycache__"))
        r = T.repasar(c, nivel="oficiales")
        self.assertTrue(r["lista"], r)

    def test_dice_la_carpeta_del_nivel_de_la_ficha(self):
        """8-oct: la estrella de un socio salía «lista» con «cópiala a estrellas/comunidad/», porque el
        mensaje usaba el --nivel de la orden y no el nivel que dice la ficha."""
        c = self.tmp / "candados"
        shutil.copytree(str(AQUI / "estrellas" / "oficiales" / "candados"), str(c), ignore=shutil.ignore_patterns("__pycache__"))
        codigo, out = None, io.StringIO()
        with redirect_stdout(out):
            codigo = T.main([str(c)])
        self.assertEqual(codigo, 0, out.getvalue())
        self.assertIn("estrellas/oficiales/candados/", out.getvalue(),
                      "el taller manda la estrella a otra carpeta que la de su nivel")

    def test_un_correo_no_sale(self):
        c = self.tmp / "con-correo"
        c.mkdir()
        (c / "motor.py").write_text('print("ok")\n# escribe a alguien' + '@' + 'dominio-real.com\n', encoding="utf-8")
        r = T.repasar(c, autor="AlexCanoFuentes")
        self.assertFalse(r["lista"])
        self.assertIn("quitar lo que la limpieza ha encontrado", r["falta"])

    def test_sin_ficha_deja_un_borrador_y_no_esta_lista(self):
        c = self.tmp / "sin-ficha"
        c.mkdir()
        (c / "motor.py").write_text('print("ok")\n', encoding="utf-8")
        r = T.repasar(c)
        self.assertTrue((c / "estrella.json").is_file())
        self.assertFalse(r["lista"])
        self.assertIn("rellenar lo que pone PENDIENTE en estrella.json", r["falta"])

    def test_no_escribe_fuera_de_la_carpeta(self):
        c = self.tmp / "aislada"
        c.mkdir()
        (c / "motor.py").write_text('print("ok")\n', encoding="utf-8")
        antes = sorted(p.relative_to(self.tmp).as_posix() for p in self.tmp.rglob("*"))
        T.repasar(c)
        despues = sorted(p.relative_to(self.tmp).as_posix() for p in self.tmp.rglob("*"))
        self.assertEqual(sorted(set(despues) - set(antes)), ["aislada/estrella.json"])


# ---------------------------------------------------------------- la red: registrar, perfil, avisar

class Cifrado(unittest.TestCase):
    """VV-008, M0: el cifrado de los mensajes, escrito en Python puro desde los RFC. Cada pieza contra los vectores
    oficiales de su RFC, y el conjunto contra los de RFC 9180, apéndice A.2 (modos Base y Auth)."""
    h = staticmethod(bytes.fromhex)

    def test_x25519_rfc7748(self):
        h = self.h
        self.assertEqual(V._x25519(h("a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4"),
                                      h("e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c")),
                         h("c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552"))
        self.assertEqual(V._x25519(h("4b66e9d4d1b4673c5ad22691957d6af5c11b6421e0ea01d42ca4169e7918ba0d"),
                                      h("e5210f12786811d3f4b7959d0538ae2c31dbe7106fc03c3efc4cd549c715a493")),
                         h("95cbde9476e8907d7aade45cb4b873f88b595a68799fa152e6f8f7647aac7957"))
        a = h("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
        b = h("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb")
        self.assertEqual(V._x25519_publica(a), h("8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a"))
        self.assertEqual(V._x25519(a, V._x25519_publica(b)), h("4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742"))

    def test_hkdf_rfc5869(self):
        h = self.h
        prk = V._hkdf_extract(h("000102030405060708090a0b0c"), h("0b" * 22))
        self.assertEqual(prk, h("077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"))
        self.assertEqual(V._hkdf_expand(prk, h("f0f1f2f3f4f5f6f7f8f9"), 42),
                         h("3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"))

    def test_chacha20_poly1305_rfc8439(self):
        h = self.h
        pt = (b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, "
              b"sunscreen would be it.")
        k, n, aad = bytes(range(0x80, 0xa0)), h("070000004041424344454647"), h("50515253c0c1c2c3c4c5c6c7")
        sobre = V._aead_cerrar(k, n, aad, pt)
        self.assertEqual(sobre[-16:], h("1ae10b594f09e26a7e902ecbd0600691"))
        self.assertTrue(sobre.startswith(h("d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fe")))
        self.assertEqual(V._aead_abrir(k, n, aad, sobre), pt)

    def test_hpke_rfc9180_base_y_auth(self):
        h = self.h
        info, aad = h("4f6465206f6e2061204772656369616e2055726e"), h("436f756e742d30")
        pt = h("4265617574792069732074727574682c20747275746820626561757479")
        enc, sobre = V.hpke_cerrar(h("4310ee97d88cc1f088a5576c77ab0cf5c3ac797f3d95139c6c84b5429c59662a"), pt, info, aad,
                                      _efimera=h("f4ec9b33b792c372c1d2c2063507b684ef925b8c75a42dbcbf57d63ccd381600"))
        self.assertEqual(enc, h("1afa08d3dec047a643885163f1180476fa7ddb54c6a8029ea33f95796bf2ac4a"))
        self.assertEqual(sobre, h("1c5250d8034ec2b784ba2cfd69dbdb8af406cfe3ff938e131f0def8c8b60b4db21993c62ce81883d2dd1b51a28"))
        skr, pks = h("3ca22a6d1cda1bb9480949ec5329d3bf0b080ca4c45879c95eddb55c70b80b82"), h("f0f4f9e96c54aeed3f323de8534fffd7e0577e4ce269896716bcb95643c8712b")
        enc, sobre = V.hpke_cerrar(h("1a478716d63cb2e16786ee93004486dc151e988b34b475043d3e0175bdb01c44"), pt, info, aad,
                                      priv_remitente=h("2def0cb58ffcf83d1062dd085c8aceca7f4c0c3fd05912d847b61f3e54121f05"),
                                      _efimera=h("c94619e1af28971c8fa7957192b7e62a71ca2dcdde0a7cc4a8a9e741d600ab13"))
        self.assertEqual(sobre, h("ab1a13c9d4f01a87ec3440dbd756e2677bd2ecf9df0ce7ed73869b98e00c09be111cb9fdf077347aeb88e61bdf"))
        self.assertEqual(V.hpke_abrir(skr, enc, sobre, info, aad, pub_remitente=pks), pt)
        # sabotajes: firma de otra clave y un byte cambiado
        with self.assertRaises(ValueError):
            V.hpke_abrir(skr, enc, sobre, info, aad, pub_remitente=h("4310ee97d88cc1f088a5576c77ab0cf5c3ac797f3d95139c6c84b5429c59662a"))
        malo = bytearray(sobre); malo[3] ^= 1
        with self.assertRaises(ValueError):
            V.hpke_abrir(skr, enc, bytes(malo), info, aad, pub_remitente=pks)

    def test_igual_que_la_referencia_si_esta(self):
        try:
            from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
            from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        except ImportError:
            self.skipTest("sin la biblioteca cryptography: la comparación es solo de las pruebas, nunca de void.py")
        for _ in range(10):
            a, b = os.urandom(32), os.urandom(32)
            ref = X25519PrivateKey.from_private_bytes(a).exchange(X25519PublicKey.from_public_bytes(V._x25519_publica(b)))
            self.assertEqual(V._x25519(a, V._x25519_publica(b)), ref)
            k, n, pt, ad = os.urandom(32), os.urandom(12), os.urandom(os.urandom(1)[0]), os.urandom(7)
            self.assertEqual(V._aead_cerrar(k, n, ad, pt), ChaCha20Poly1305(k).encrypt(n, pt, ad))


class RedFalsa:
    """Una red de Void de juguete, en este proceso, que contesta como el Worker de red/ (sus reglas de
    verdad las prueban red/pruebas/todo.mjs contra el Worker). Aquí se prueba el cliente."""

    def __init__(self):
        import http.server
        import threading
        self.perfiles = {}      # alias -> {"llave", "agente", "publico"}
        self.avisos = []        # {"estrella", "tipo", "texto", "de", "creado"}
        self.autoria = {}       # estrella -> alias
        self.vistas = []        # (método, ruta, llave o None)
        self.huellas = {}       # alias -> huella tal cual llegó
        red = self

        class Manejador(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def responder(self, codigo, datos):
                cuerpo = json.dumps(datos).encode("utf-8")
                self.send_response(codigo)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)

            def quien(self):
                cab = self.headers.get("authorization") or ""
                llave = cab[7:] if cab.startswith("Bearer ") else None
                red.vistas.append((self.command, self.path, llave))
                for alias, p in red.perfiles.items():
                    if llave and p["llave"] == llave:
                        return alias, llave
                return None, llave

            def do_GET(self):
                alias, llave = self.quien()
                if self.path == "/v1/yo":
                    if not alias:
                        return self.responder(401, {"error": "sin llave"})
                    suyas = [e for e, a in red.autoria.items() if a == alias]
                    return self.responder(200, {"alias": alias, "estrellas": suyas,
                                                "avisos": [a for a in red.avisos if a["estrella"] in suyas]})
                self.responder(404, {"error": "no"})

            def do_POST(self):
                alias, llave = self.quien()
                largo = int(self.headers.get("content-length") or 0)
                b = json.loads(self.rfile.read(largo).decode("utf-8") or "{}")
                if self.path == "/v1/registrar":
                    if llave:
                        if not alias:
                            return self.responder(401, {"error": "llave falsa"})
                        if alias != b["alias"]:
                            return self.responder(409, {"error": "Este vault ya está en la red como @" + alias})
                        return self.responder(200, {"alias": alias, "nuevo": False})
                    if b["alias"] in red.perfiles:
                        return self.responder(409, {"error": "El alias @{} ya es de otro vault.".format(b["alias"])})
                    nueva = "vv_" + hashlib_sha(b["alias"] + str(len(red.perfiles)))[:43]
                    red.perfiles[b["alias"]] = {"llave": nueva, "agente": b["agente"], "publico": []}
                    return self.responder(201, {"alias": b["alias"], "nuevo": True, "llave": nueva})
                if not alias:
                    return self.responder(401, {"error": "sin llave"})
                if self.path == "/v1/perfil":
                    red.perfiles[alias]["publico"] = b["publico"]
                    return self.responder(200, {"alias": alias, "publico": b["publico"]})
                if self.path == "/v1/avisos":
                    if sum(1 for a in red.avisos if a["de"] == alias) >= 10:
                        return self.responder(429, {"error": "Ya has mandado 10 avisos en la última hora, que es el tope (10)."})
                    red.avisos.append({"estrella": b["estrella"], "tipo": b["tipo"], "texto": b["texto"], "de": alias,
                                       "creado": 1790000000000})
                    return self.responder(201, {"estrella": b["estrella"], "pagina": "https://vaultvoid.app/estrella/" + b["estrella"]})
                if self.path == "/v1/llave/cambiar":
                    nueva = "vv_" + hashlib_sha("otra" + llave)[:43]
                    red.perfiles[alias]["llave"] = nueva
                    return self.responder(200, {"alias": alias, "llave": nueva})
                if self.path == "/v1/huella":
                    red.huellas[alias] = b["huella"]
                    return self.responder(200, {"alias": alias, "huella": b["huella"]})
                if self.path == "/v1/huella/retirar":
                    red.huellas.pop(alias, None)
                    return self.responder(200, {"alias": alias, "retirada": True})
                if self.path == "/v1/baja":
                    del red.perfiles[alias]
                    return self.responder(200, {"alias": alias, "baja": True})
                self.responder(404, {"error": "no"})

        self.servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.url = "http://127.0.0.1:{}".format(self.servidor.server_address[1])
        self.hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.hilo.start()

    def parar(self):
        self.servidor.shutdown()
        self.servidor.server_close()


def hashlib_sha(texto):
    import hashlib
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class RedDeVoid(Caso):
    """void.py registrar / perfil / avisar / llave / baja / estado contra una red de juguete."""

    def setUp(self):
        super().setUp()
        self.red = RedFalsa()
        self.antes_env = os.environ.get("VOID_RED")
        os.environ["VOID_RED"] = self.red.url

    def tearDown(self):
        self.red.parar()
        if self.antes_env is None:
            os.environ.pop("VOID_RED", None)
        else:
            os.environ["VOID_RED"] = self.antes_env
        super().tearDown()

    def alta(self, v, alias="nube"):
        codigo, out, err = correr("registrar", "--alias", alias, "--agente", "Brock", "--vault", v)
        self.assertEqual(codigo, 0, err)
        return out

    def test_huella_solo_cifras_y_solo_si_se_pide(self):
        """VV-007: la huella sale del vault como cifras. Sin --publicar no se manda nada; con él, solo números y
        ningún texto del vault, aunque el vault esté lleno de nombres."""
        v = self.conectado({"README.md": b"# Mi vault\n", "criterio/apuntes.md": "- **Elegí** · negocio · Lucía Pérez\n- **[sin contestar]** · algo\n".encode("utf-8"),
                            "proyectos/taller.md": "# Taller de Lucía\n".encode("utf-8"), "proyectos/_plantilla.md": b"# plantilla\n"})
        self.alta(v)
        codigo, out, err = correr("huella", "--vault", v)
        self.assertEqual(codigo, 0, err)
        self.assertIn("1 decisiones", out); self.assertIn("1 proyectos", out); self.assertIn("1 preguntas sin contestar", out)
        self.assertEqual(self.red.huellas, {}, "sin --publicar ha mandado la huella")
        codigo, out, err = correr("huella", "--publicar", "--tono", "200", "--vault", v)
        self.assertEqual(codigo, 0, err)
        h = self.red.huellas["nube"]
        self.assertEqual(sorted(h), sorted(["version", "dias", "pulso", "decisiones", "proyectos", "calladas", "tono"]))
        self.assertTrue(all(isinstance(x, int) for x in h.values()), "la huella lleva algo que no es un número")
        self.assertNotIn("Lucía", json.dumps(h), "la huella lleva texto del vault")
        codigo, out, err = correr("huella", "--retirar", "--vault", v)
        self.assertEqual(codigo, 0, err)
        self.assertNotIn("nube", self.red.huellas)
        self.assertEqual(correr("huella", "--publicar", "--tono", "999", "--vault", v)[0], 1, "un tono fuera de la rueda no se para")

    def test_registrar_guarda_la_llave_y_la_deja_fuera_de_git(self):
        v = self.conectado()
        out = self.alta(v)
        llave = (v / ".void" / "llave").read_text(encoding="utf-8").strip()
        self.assertEqual(llave, self.red.perfiles["nube"]["llave"])
        self.assertIn("@nube", out)
        self.assertEqual(commits(v)[0], "void: la llave de la red, fuera de git (.void/ en .gitignore)")
        self.assertIn(".void/", (v / ".gitignore").read_text(encoding="utf-8"))
        self.assertTrue(limpio(v), "registrar deja cambios fuera del commit")
        # Lo que haría cualquiera después: git add -A y un commit. La llave no puede entrar.
        git(v, "add", "-A")
        git(v, "commit", "-q", "-m", "todo")
        _, seguidos = git(v, "ls-files")
        self.assertNotIn(".void", seguidos, "la llave ha entrado en git con un git add -A")
        _, historia = git(v, "log", "--all", "-p")
        self.assertNotIn(llave, historia, "la llave está en la historia de git")

    def test_la_llave_no_entra_aunque_el_gitignore_la_vuelva_a_meter(self):
        """Un .gitignore que ignora lo de dentro de .void pero vuelve a meter la llave con «!»."""
        v = self.conectado({"README.md": b"# Mi vault\n", ".gitignore": b".void/*\n!.void/llave\n"})
        self.alta(v)
        llave = (v / ".void" / "llave").read_text(encoding="utf-8").strip()
        git(v, "add", "-A")
        git(v, "commit", "-q", "-m", "todo")
        _, seguidos = git(v, "ls-files")
        self.assertNotIn(".void", seguidos, "la llave ha entrado en git por la regla con «!»")
        _, historia = git(v, "log", "--all", "-p")
        self.assertNotIn(llave, historia)

    def test_la_llave_no_entra_si_git_ya_sigue_la_carpeta(self):
        v = self.conectado()
        (v / ".void").mkdir()
        (v / ".void" / "nota.txt").write_text("hola\n", encoding="utf-8")
        git(v, "add", "-f", ".void/nota.txt")
        git(v, "commit", "-q", "-m", "una nota en .void")
        codigo, out, err = correr("registrar", "--alias", "nube", "--agente", "Brock", "--vault", v)
        self.assertEqual(codigo, 1)
        self.assertIn("git rm -r --cached .void", err)
        self.assertFalse((v / ".void" / "llave").exists())

    def test_registrar_dos_veces_no_crea_otro_perfil(self):
        v = self.conectado()
        self.alta(v)
        llave = (v / ".void" / "llave").read_text(encoding="utf-8").strip()
        log = commits(v)
        codigo, out, err = correr("registrar", "--alias", "nube", "--agente", "Brock", "--vault", v)
        self.assertEqual(codigo, 0, err)
        self.assertIn("no he creado otro perfil", out)
        self.assertEqual(self.red.vistas[-1][2], llave, "la segunda vez no mandó la llave del vault")
        self.assertEqual(list(self.red.perfiles), ["nube"])
        self.assertEqual(commits(v), log, "la segunda vez dejó otro commit")
        self.assertEqual((v / ".void" / "llave").read_text(encoding="utf-8").strip(), llave, "cambió la llave")

    def test_llave_falsa_da_un_error_de_una_frase(self):
        v = self.conectado()
        self.alta(v)
        (v / ".void" / "llave").write_text("vv_" + "A" * 43 + "\n", encoding="utf-8")
        codigo, out, err = correr("avisar", "candados", "gracias", "me salvó el lunes", "--vault", v)
        self.assertEqual(codigo, 1)
        self.assertIn("ya no vale", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(self.red.avisos, [])

    def test_avisar_llega_al_estado_del_creador(self):
        creador = self.conectado()
        self.alta(creador, "nube")
        self.red.autoria["candados"] = "nube"
        otro = hacer_vault(self.tmp / "otro")
        correr("actualizar", "--conectar", "--vault", otro, "--desde", self.b01)
        self.alta(otro, "cosmo")
        codigo, out, err = correr("avisar", "candados", "gracias", "Me salvó el lunes", "--vault", otro)
        self.assertEqual(codigo, 0, err)
        self.assertIn("vaultvoid.app/estrella/candados", out)
        codigo, out, err = correr("estado", "--vault", creador, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        self.assertIn("Te han escrito:", out)
        self.assertIn("gracias · candados · de @cosmo", out)
        self.assertIn("Me salvó el lunes", out)

    def test_avisar_mal_escrito_no_sale(self):
        v = self.conectado()
        self.alta(v)
        for args in (("candados", "queja", "hola hola"), ("Candados", "fallo", "hola hola"), ("candados", "fallo", "x")):
            codigo, out, err = correr("avisar", *args, "--vault", v)
            self.assertEqual(codigo, 1, args)
        self.assertEqual(self.red.avisos, [])

    def test_limite_de_avisos(self):
        v = self.conectado()
        self.alta(v)
        for i in range(10):
            self.assertEqual(correr("avisar", "candados", "mejora", "idea {}".format(i), "--vault", v)[0], 0)
        codigo, out, err = correr("avisar", "candados", "mejora", "una más", "--vault", v)
        self.assertEqual(codigo, 1)
        self.assertIn("tope", err)

    def test_perfil_publico(self):
        v = self.conectado()
        self.alta(v)
        self.assertEqual(correr("perfil", "--publico", "agente,estrellas", "--vault", v)[0], 0)
        self.assertEqual(self.red.perfiles["nube"]["publico"], ["agente", "estrellas"])
        self.assertEqual(correr("perfil", "--publico", "nada", "--vault", v)[0], 0)
        self.assertEqual(self.red.perfiles["nube"]["publico"], [])
        codigo, out, err = correr("perfil", "--publico", "correo", "--vault", v)
        self.assertEqual(codigo, 1)
        self.assertEqual(self.red.perfiles["nube"]["publico"], [])

    def test_cambiar_la_llave_y_baja(self):
        v = self.conectado()
        self.alta(v)
        vieja = (v / ".void" / "llave").read_text(encoding="utf-8").strip()
        self.assertEqual(correr("llave", "cambiar", "--vault", v)[0], 0)
        nueva = (v / ".void" / "llave").read_text(encoding="utf-8").strip()
        self.assertNotEqual(vieja, nueva)
        self.assertEqual(self.red.perfiles["nube"]["llave"], nueva)
        self.assertEqual(correr("baja", "--vault", v)[0], 1, "la baja sin --si no pidió confirmación")
        self.assertIn("nube", self.red.perfiles)
        self.assertEqual(correr("baja", "--si", "--vault", v)[0], 0)
        self.assertEqual(self.red.perfiles, {})
        self.assertFalse((v / ".void" / "llave").exists())

    def test_estado_sin_red_sigue_funcionando(self):
        v = self.conectado()
        self.alta(v)
        self.red.parar()
        os.environ["VOID_RED"] = "http://127.0.0.1:9"
        codigo, out, err = correr("estado", "--vault", v, "--desde", self.b01)
        self.assertEqual(codigo, 0, err)
        self.assertIn("No he podido mirar la red de Void", out)
        self.red = RedFalsa()

    def test_la_llave_no_viaja_en_claro(self):
        v = self.conectado()
        os.environ["VOID_RED"] = "http://ejemplo.invalid"
        codigo, out, err = correr("registrar", "--alias", "nube", "--agente", "Brock", "--vault", v)
        self.assertEqual(codigo, 1)
        self.assertIn("no mando la llave ahí", err)

    def test_sin_conectar_no_registra(self):
        v = hacer_vault(self.tmp / "suelto")
        codigo, out, err = correr("registrar", "--alias", "nube", "--agente", "Brock", "--vault", v)
        self.assertEqual(codigo, 1)
        self.assertIn("no está conectada a Void", err)
        self.assertEqual(self.red.perfiles, {})


# ---------------------------------------------------------------- sabotaje

SABOTAJES = [
    ("taller: no mira la limpieza",
     [("    h = limpieza(carpeta, nombres)\n", "    h = []\n")],
     ["Nebulosa.test_un_correo_no_sale"], "taller.py"),
    ("hash cambiado en el manifiesto: no comprueba la huella",
     [("if huella(datos) != esperado:", "if False:")],
     ["Actualizar.test_hash_cambiado_en_el_manifiesto", "Actualizar.test_fichero_cambiado_por_el_camino",
      "Empezar.test_fichero_cambiado_por_el_camino_no_escribe_nada"]),
    ("fichero modificado por el usuario: pisa lo suyo",
     [("elif h_instalada is not None and h_local == h_instalada:", "elif True:")],
     ["Actualizar.test_fichero_modificado_por_el_usuario",
      "Actualizar.test_marcas_lo_de_dentro_cambiado_por_el_usuario", "Traer.test_no_pisa_lo_que_cambio_el_usuario"]),
    ("sin red: no da el error de una frase",
     [("raise Fallo(MSG_SIN_RED)", "raise")],
     ["Red.test_sin_red", "Red.test_sin_red_de_verdad"]),
    ("vault sin void.json: actualiza igual",
     [("if actual is None and not conectar:", "if False:")],
     ["SinVoidJson.test_actualizar_sin_void_json_no_toca_nada"]),
    ("rutas: deja salir del vault",
     [("        if not ruta_segura(ruta):\n            raise Fallo(\"El manifiesto",
       "        if False:\n            raise Fallo(\"El manifiesto"),
      ("if not dentro(vault, destino) or destino.is_symlink():", "if False:"),
      ("            if not dentro(vault, destino.parent if not destino.exists() else destino):",
       "            if False:"),
      ("            if not dentro(vault, destino.parent):", "            if False:")],
     ["Actualizar.test_ruta_que_sale_del_vault"] + ([] if os.name == "nt" else
                                                    ["Actualizar.test_enlace_que_sale_del_vault"])),
    ("marcas: sustituye el fichero entero",
     [("resultado = antes + con_finales(propio, crlf) + despues", "resultado = con_finales(base, crlf)")],
     ["Actualizar.test_marcas_lo_de_fuera_es_tuyo"]),
    ("commit: escribe pero no guarda",
     [('codigo, _ = git(vault, "commit", "-q", "-m", mensaje, "--", *(rutas + sueltos), comprobar=False)',
       "codigo = 0")],
     ["Actualizar.test_01_a_02_un_commit_y_revert_byte_a_byte", "Traer.test_traer_un_commit_y_revert_byte_a_byte"]),
    ("finales de git: escribe \\n donde git sacaría \\r\\n",
     [("        crlf = usa_crlf(previo) if previo is not None else finales.get(ruta)\n",
       "        crlf = usa_crlf(previo) if previo is not None else None\n")],
     ["Actualizar.test_windows_con_autocrlf_revert_byte_a_byte"]),
    ("entrar: la página publica una huella que no es la de void.py",
     [("        elif any(x != h for x in vistas):", "        elif False:")],
     ["Entrar.test_huella_que_no_cuadra_sale_en_rojo", "Entrar.test_void_py_cambia_y_la_pagina_no"],
     "regenerar_manifiesto.py"),
    ("plantilla: no le pasa fugas.py",
     [("        hallazgos = fugas.escanear(copia, nombres)\n", "        hallazgos = []\n")],
     ["Plantilla.test_un_nombre_real_dentro_sale_en_rojo", "Plantilla.test_con_un_nombre_dentro_no_se_escribe_nada"],
     "regenerar_manifiesto.py"),
    ("plantilla: escribe el manifiesto aunque lleve un nombre",
     [("    if sucia:\n        for pr in sucia:", "    if False:\n        for pr in sucia:")],
     ["Plantilla.test_con_un_nombre_dentro_no_se_escribe_nada"], "regenerar_manifiesto.py"),
    ("empezar: no comprueba la huella que publica la página",
     [("    if fuente.huella_manifiesto != esperada:", "    if False:")],
     ["Empezar.test_huella_de_la_pagina_que_no_cuadra_no_escribe_nada"]),
    ("empezar: monta en una carpeta que no está vacía",
     [("    if hay:\n        raise Fallo(\"Esta carpeta no está vacía", "    if False:\n        raise Fallo(\"Esta carpeta no está vacía")],
     ["Empezar.test_carpeta_que_no_esta_vacia_no_se_toca"]),
    ("empezar: si el commit falla deja la plantilla a medias",
     [("    except BaseException:\n        git(vault, \"rm\"", "    except ZeroDivisionError:\n        git(vault, \"rm\"")],
     ["Empezar.test_si_el_commit_falla_no_deja_nada"]),
    ("empezar: la página publica una huella de la plantilla que no es la suya",
     [("        elif any(x != h_plantilla for x in de_plantilla):", "        elif False:")],
     ["Empezar.test_huella_de_la_plantilla_que_no_cuadra_sale_en_rojo", "Empezar.test_la_plantilla_cambia_y_la_pagina_no"],
     "regenerar_manifiesto.py"),
    ("catalogo: enseña tal cual lo que escribe quien publica la estrella",
     [("    return \" \".join(limpio_de_control(valor, tope).split())", "    return \" \".join(str(valor).split())")],
     ["Empezar.test_catalogo_no_pasa_caracteres_de_control"]),
    ("conectar: deja fuera del commit el void.py recién bajado",
     [('    sueltos = sorted(set(sin_seguir(vault, [r for r in iguales if ruta_segura(r)])) - set(rutas))\n',
       "    sueltos = []\n")],
     ["SinVoidJson.test_conectar_se_lleva_lo_recien_bajado_y_revert_lo_quita"]),
    ("cambios sin guardar: se los lleva en el commit",
     [("    if sucias:\n", "    if False:\n")],
     ["Actualizar.test_cambios_sin_guardar"]),
    ("si el commit falla: deja ficheros a medias",
     [("    except BaseException:\n        for ruta, previo", "    except ZeroDivisionError:\n        for ruta, previo")],
     ["Actualizar.test_si_el_commit_falla_lo_deja_todo_como_estaba"]),
    ("finales de línea: \\r\\n cuenta como cambio del usuario",
     [('    if b"\\0" not in datos:\n        datos = datos.replace(b"\\r\\n", b"\\n")\n    return hashlib',
       "    return hashlib")],
     ["Actualizar.test_finales_de_linea_de_windows"]),
    ("formato: no exige el error que la hizo nacer",
     [('        problemas.append("«nacio_de» tiene que decir al menos un error que la hizo nacer")',
       "        pass"),
      ('        if clave not in ficha:\n            problemas.append("falta «{}»".format(clave))',
       '        if clave not in ficha and clave != "nacio_de":\n'
       '            problemas.append("falta «{}»".format(clave))'),
      ('    nacio = ficha["nacio_de"]', '    nacio = ficha.get("nacio_de", [])')],
     ["Formato.test_sin_el_error_que_la_hizo_nacer"], "formato.py"),
    ("formato: no compara las huellas",
     [("        elif reales[ruta] != declarados[ruta]:", "        elif False:")],
     ["Formato.test_hash_que_no_cuadra"], "formato.py"),
    ("formato: no mira si sobran ficheros",
     [("    for ruta in sorted(set(reales) - set(declarados)):", "    for ruta in []:")],
     ["Formato.test_fichero_que_no_esta_en_la_lista"], "formato.py"),
    ("formato: acepta campos que no son del formato",
     [("        if clave not in OBLIGATORIOS and clave not in OPCIONALES:", "        if False:")],
     ["Formato.test_campo_que_no_es_del_formato"], "formato.py"),
    ("puerta: no pasa fugas.py sobre la estrella",
     [('    v["rechazo"] += limpia(carpeta, nombres)\n', "")],
     ["Puerta.test_con_un_correo_dentro", "Puerta.test_con_un_nombre_de_persona_dentro",
      "Puerta.test_con_una_ruta_de_la_maquina_de_alguien"], "puerta.py"),
    ("puerta: no valida el formato",
     [('    v["rechazo"] += formato.validar(carpeta, ficha)\n', "")],
     ["Puerta.test_con_un_hash_que_no_cuadra"], "puerta.py"),
    ("puerta: deja entrar en la grande por debajo de 80",
     [('    return "grande" if total >= UMBRAL else "pequeña"', '    return "grande"')],
     ["Puerta.test_kernel_bajo_80_va_a_la_liga_pequena_y_no_se_rechaza"], "puerta.py"),
    ("puerta: rechaza lo que no llega a 80 en vez de ofrecerle la pequeña",
     [('    v["liga"] = liga(v["kernel"]["total"])\n',
       '    v["liga"] = liga(v["kernel"]["total"])\n'
       '    if v["liga"] != "grande":\n        v["rechazo"].append("no llega a 80")\n')],
     ["Puerta.test_kernel_bajo_80_va_a_la_liga_pequena_y_no_se_rechaza"], "puerta.py"),
    ("puerta: no corre la prueba aunque se lo pidan",
     [("        motivo = ejecutar_prueba(carpeta, ficha)\n", "        motivo = None\n")],
     ["Puerta.test_con_ejecutar_su_prueba_tiene_que_pasar"], "puerta.py"),
    ("puerta: deja cambiar los ficheros sin subir la versión",
     [('    if antes.get("ficheros") != ahora["ficheros"] and ahora["version"] == antes["version"]:',
       "    if False:")],
     ["Puerta.test_cambia_ficheros_sin_subir_version"], "puerta.py"),
    ("catálogo: mete las estrellas rechazadas",
     [('        if v["rechazo"]:\n            problemas.append', '        if False:\n            problemas.append')],
     ["Catalogo.test_una_estrella_rechazada_no_deja_escribir_el_catalogo"], "regenerar_catalogo.py"),
    ("catálogo: no comprueba si está al día",
     [("        if not destino.is_file() or void.huella(destino.read_bytes()) != void.huella(nuevo):",
       "        if not destino.is_file():")],
     ["Catalogo.test_catalogo_desfasado"], "regenerar_catalogo.py"),
    ("traer: no comprueba la huella contra el catálogo",
     [("            if huella(datos) != esperada:", "            if False:")],
     ["Traer.test_huella_que_no_cuadra_no_escribe_nada"]),
    ("traer: hace suyos los ficheros de la base",
     [("    propios = {r: d for r, d in nuevos.items() if r not in ajenos}", "    propios = dict(nuevos)")],
     ["Traer.test_no_pisa_ni_se_queda_lo_de_la_base"]),
    ("traer: trae a una carpeta sin void.json",
     [("    if not conectar_estrella and actual is None:", "    if False:")],
     ["Traer.test_sin_void_json_no_toca_nada_y_con_conectar_si"]),
    ("traer: actualizar la base pierde las estrellas",
     [('                                   estrellas=(actual or {}).get("estrellas"))',
       "                                   estrellas=None)")],
     ["Traer.test_actualizar_la_base_conserva_las_estrellas"]),
    ("traer: no valida las rutas del catálogo",
     [("        if not ruta_segura(ruta):\n            raise Fallo(\"La estrella",
       "        if False:\n            raise Fallo(\"La estrella"),
      ("        if not dentro(vault, destino) or destino.is_symlink():", "        if False:"),
      ("            if not dentro(vault, destino.parent if not destino.exists() else destino):",
       "            if False:"),
      ("            if not dentro(vault, destino.parent):", "            if False:")],
     ["Traer.test_ruta_del_catalogo_que_sale_del_vault"]),
    ("red: guarda la llave sin sacarla antes de git",
     [("    llave_fuera_de_git(vault)\n", ""),
      ('    if not llave_ignorada(vault):\n        raise Fallo("git vería', '    if False:\n        raise Fallo("git vería')],
     ["RedDeVoid.test_registrar_guarda_la_llave_y_la_deja_fuera_de_git",
      "RedDeVoid.test_la_llave_no_entra_aunque_el_gitignore_la_vuelva_a_meter"]),
    ("red: guarda la llave aunque git ya siga la carpeta .void",
     [("    if seguidos.strip():\n        raise Fallo(\"git ya sigue", "    if False:\n        raise Fallo(\"git ya sigue"),
      ("    if codigo != 0 or seguidos.strip():\n        return False", "    if codigo != 0:\n        return False")],
     ["RedDeVoid.test_la_llave_no_entra_si_git_ya_sigue_la_carpeta"]),
    ("red: registrar otra vez no manda la llave (y pediría otro perfil)",
     [('    llave = leer_llave(vault)\n    codigo, r = pedir_red("POST", "/v1/registrar"',
       '    llave = None\n    codigo, r = pedir_red("POST", "/v1/registrar"')],
     ["RedDeVoid.test_registrar_dos_veces_no_crea_otro_perfil"]),
    ("red: una llave que no vale no se explica",
     [("    if codigo == 401:\n        raise Fallo(MSG_LLAVE_NO_VALE if llave else MSG_SIN_LLAVE)\n", "")],
     ["RedDeVoid.test_llave_falsa_da_un_error_de_una_frase"]),
    ("red: estado no dice lo que te han escrito",
     [("    estado_red(vault)\n    return 0", "    return 0")],
     ["RedDeVoid.test_avisar_llega_al_estado_del_creador"]),
    ("red: manda la llave a una dirección sin https",
     [('    if otra.startswith("https://") or re.fullmatch(', '    if True or re.fullmatch(')],
     ["RedDeVoid.test_la_llave_no_viaja_en_claro"]),
    ("red: estado se cae si la red no contesta",
     [('    except Fallo as e:\n        print("No he podido mirar la red', '    except ZeroDivisionError as e:\n        print("No he podido mirar la red')],
     ["RedDeVoid.test_estado_sin_red_sigue_funcionando"]),
]


def correr_pruebas(nombres):
    cargador = unittest.TestLoader()
    suite = unittest.TestSuite()
    for n in nombres:
        suite.addTests(cargador.loadTestsFromName(n, sys.modules[__name__]))
    resultado = unittest.TestResult()
    suite.run(resultado)
    return resultado


def razon(traza):
    lineas = [l for l in traza.strip().splitlines() if l.strip()]
    ultima = lineas[-1] if lineas else "?"
    return ultima.replace("AssertionError: ", "")[:220]


def poner_bajo_prueba(fichero, modulo):
    """Cambia el módulo que usan las pruebas: el bueno o uno saboteado."""
    global V, VOID_PY, F, P, C, T, M
    if fichero == "void.py":
        V, VOID_PY = modulo, Path(modulo.__file__)
    elif fichero == "formato.py":
        F = modulo
    elif fichero == "puerta.py":
        P = modulo
    elif fichero == "regenerar_catalogo.py":
        C = modulo
    elif fichero == "taller.py":
        T = modulo
    elif fichero == "regenerar_manifiesto.py":
        M = modulo
    else:
        raise ValueError(fichero)


def buenos():
    return {"void.py": REF, "formato.py": REF_F, "puerta.py": REF_P, "regenerar_catalogo.py": REF_C, "taller.py": REF_T,
            "regenerar_manifiesto.py": regenerar_manifiesto}


def sabotaje():
    tmp = Path(tempfile.mkdtemp(prefix="void-sabotaje-"))
    fallos = 0
    try:
        for s in SABOTAJES:
            nombre, cambios, pruebas = s[:3]
            fichero = s[3] if len(s) > 3 else "void.py"
            original = (AQUI / fichero).read_text(encoding="utf-8")
            texto = original
            for buscar, poner in cambios:
                if buscar not in texto:
                    print("EL SABOTAJE NO SE PUDO APLICAR ({}): no encuentro {!r}".format(nombre, buscar[:60]))
                    fallos += 1
                    break
                texto = texto.replace(buscar, poner)
            else:
                roto = tmp / fichero
                roto.write_text(texto, encoding="utf-8")
                poner_bajo_prueba(fichero, cargar(roto))
                try:
                    r = correr_pruebas(pruebas)
                finally:
                    poner_bajo_prueba(fichero, buenos()[fichero])
                rojas = r.failures + r.errors
                if not rojas:
                    print("NO LO CAZA: " + nombre)
                    fallos += 1
                else:
                    print("ROJO, como debe | " + nombre)
                    for prueba, traza in rojas:
                        print("    {} -> {}".format(prueba.id().split(".", 1)[1], razon(traza)))
    finally:
        for fichero, modulo in buenos().items():
            poner_bajo_prueba(fichero, modulo)
        borrar(str(tmp))
    print()
    if fallos:
        print("MAL: {} sabotajes no se cazan.".format(fallos))
        return 1
    print("OK: las pruebas cazan los {} sabotajes.".format(len(SABOTAJES)))
    return 0


# ---------------------------------------------------------------- copias de vaults reales

def base_de_prueba(destino, version, cambiar):
    """Copia la base del repo con otra versión; con cambiar=True, toca un fichero de cada tipo."""
    base = Path(destino) / "base"
    shutil.copytree(str(AQUI / "base"), str(base))
    if cambiar:
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.name == REF.MANIFIESTO:
                continue
            datos = p.read_bytes()
            linea = "prueba de la base " + version
            if p.suffix == ".md" and REF.partir_marcas(datos):
                antes, bloque, despues = REF.partir_marcas(datos)
                p.write_bytes(antes + bloque + ("- " + linea + "\n").encode("utf-8") + despues)
            elif p.suffix in (".py", ".toml") or p.name == ".gitignore":
                p.write_bytes(datos + ("# " + linea + "\n").encode("utf-8"))
    (base / REF.MANIFIESTO).write_bytes(regenerar_manifiesto.contenido(base, version))
    return Path(destino)


def pruebas_del_vault(v, nombre="pruebas.py"):
    p = v / "herramientas" / nombre
    if not p.is_file():
        return nombre != "pruebas.py", "no tiene herramientas/" + nombre
    r = subprocess.run([sys.executable, str(p)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       cwd=str(v), timeout=600)
    ultima = (r.stdout.decode("utf-8", "replace").strip().splitlines() or ["?"])[-1]
    return r.returncode == 0, ultima


def vaults(carpetas):
    tmp = Path(tempfile.mkdtemp(prefix="void-vaults-"))
    b01 = base_de_prueba(tmp / "b01", "0.1", False)
    b02 = base_de_prueba(tmp / "b02", "0.2", True)
    mal = 0
    try:
        for i, origen in enumerate(carpetas):
            origen = Path(origen).resolve()
            v = tmp / "vault{}".format(i)
            shutil.copytree(str(origen), str(v), symlinks=True)
            print("== copia de {}".format(origen.name))
            pasos = []

            def paso(ok, texto):
                pasos.append(ok)
                print("  {} {}".format("ok " if ok else "MAL", texto))

            if (v / "void.json").exists():
                paso(False, "ya tenía void.json: la prueba espera un vault sin conectar")
                mal += 1
                continue
            ok, ultima = pruebas_del_vault(v)
            paso(ok, "sus pruebas ANTES de conectar nada: " + ultima)
            r = subprocess.run([sys.executable, str(AQUI / "void.py"), "actualizar", "--conectar",
                                "--vault", str(v), "--desde", str(b01)], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
            salida = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
            paso(r.returncode == 0 and commits(v)[0] == "void: base 0.1", "conecta la base 0.1 en un commit")
            for l in salida.strip().splitlines():
                print("      | " + l)
            ok, ultima = pruebas_del_vault(v)
            paso(ok, "sus pruebas con la 0.1: " + ultima)
            ok, ultima = pruebas_del_vault(v, "pruebas_comunes.py")
            paso(ok, "las pruebas comunes de la base: " + ultima)

            antes, log = foto(v), commits(v)
            r = subprocess.run([sys.executable, str(v / "herramientas" / "void.py"), "actualizar",
                                "--desde", str(b02)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=str(v))
            salida = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
            paso(r.returncode == 0 and commits(v) == ["void: base 0.2"] + log,
                 "su herramientas/void.py actualiza a la 0.2 en UN commit «void: base 0.2»")
            for l in salida.strip().splitlines():
                print("      | " + l)
            paso(limpio(v), "no deja nada fuera del commit")
            ok, ultima = pruebas_del_vault(v)
            paso(ok, "sus pruebas con la 0.2: " + ultima)

            codigo, _ = git(v, "revert", "--no-edit", "HEAD")
            paso(codigo == 0 and foto(v) == antes, "git revert HEAD lo deja byte a byte como estaba")
            ok, ultima = pruebas_del_vault(v)
            paso(ok, "sus pruebas tras el revert: " + ultima)
            if not all(pasos):
                mal += 1
    finally:
        borrar(str(tmp))
    print()
    if mal:
        print("MAL: {} de {} vaults no pasan.".format(mal, len(carpetas)))
        return 1
    print("OK: los {} vaults pasan 0.1 -> 0.2 -> revert con sus pruebas en verde.".format(len(carpetas)))
    return 0


def main(argv):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    preparar_git(aislado="--vaults" not in argv)
    try:
        if "--sabotaje" in argv:
            return sabotaje()
        if "--vaults" in argv:
            carpetas = argv[argv.index("--vaults") + 1:]
            if not carpetas:
                print("Dime al menos una carpeta: --vaults DIR [DIR...]", file=sys.stderr)
                return 2
            return vaults(carpetas)
        suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        r = unittest.TextTestRunner(verbosity=1, stream=sys.stdout).run(suite)
        n = r.testsRun - len(r.skipped)
        if r.wasSuccessful():
            print("OK: pasan las {} pruebas{}.".format(
                n, " ({} saltadas en este sistema)".format(len(r.skipped)) if r.skipped else ""))
            return 0
        print("MAL: fallan {} de {} pruebas.".format(len(r.failures) + len(r.errors), n))
        return 1
    finally:
        borrar(TMP_GLOBAL)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
