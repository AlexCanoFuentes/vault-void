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
import importlib.util
import io
import json
import os
import re
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
import regenerar_catalogo as REF_C  # noqa: E402

VOID_PY = AQUI / "void.py"   # el fichero bajo prueba (el sabotaje lo cambia por uno roto)
V = REF                      # el módulo bajo prueba
F = REF_F                    # formato.py bajo prueba
P = REF_P                    # puerta.py bajo prueba
C = REF_C                    # regenerar_catalogo.py bajo prueba

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
            "urllib", "zipfile", "pathlib"}
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


# ---------------------------------------------------------------- sabotaje

SABOTAJES = [
    ("hash cambiado en el manifiesto: no comprueba la huella",
     [("if huella(datos) != esperado:", "if False:")],
     ["Actualizar.test_hash_cambiado_en_el_manifiesto", "Actualizar.test_fichero_cambiado_por_el_camino"]),
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
     [('codigo, _ = git(vault, "commit", "-q", "-m", mensaje, "--", *rutas, comprobar=False)', "codigo = 0")],
     ["Actualizar.test_01_a_02_un_commit_y_revert_byte_a_byte", "Traer.test_traer_un_commit_y_revert_byte_a_byte"]),
    ("finales de git: escribe \\n donde git sacaría \\r\\n",
     [("        crlf = usa_crlf(previo) if previo is not None else finales.get(ruta)\n",
       "        crlf = usa_crlf(previo) if previo is not None else None\n")],
     ["Actualizar.test_windows_con_autocrlf_revert_byte_a_byte"]),
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
    global V, VOID_PY, F, P, C
    if fichero == "void.py":
        V, VOID_PY = modulo, Path(modulo.__file__)
    elif fichero == "formato.py":
        F = modulo
    elif fichero == "puerta.py":
        P = modulo
    elif fichero == "regenerar_catalogo.py":
        C = modulo
    else:
        raise ValueError(fichero)


def buenos():
    return {"void.py": REF, "formato.py": REF_F, "puerta.py": REF_P, "regenerar_catalogo.py": REF_C}


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
