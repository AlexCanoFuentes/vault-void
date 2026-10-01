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

VOID_PY = AQUI / "void.py"   # el fichero bajo prueba (el sabotaje lo cambia por uno roto)
V = REF                      # el módulo bajo prueba

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
        self.assertIn("No encuentro la base en GitHub", err)


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

    def test_cada_dato_plantado_sale_en_rojo(self):
        for tipo, linea in PLANTADOS:
            (self.repo / "nota.md").write_text(linea + "\n", encoding="utf-8")
            tipos = {t for _, _, t, _ in self.fugas.escanear(self.repo)}
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
        tipos = {t for d, _, t, _ in self.fugas.escanear(self.repo) if d == "mensajes y autores de commit"}
        self.assertEqual(tipos, {"correo", "nombre"}, "no mira el autor y el mensaje de cada commit")

    def test_nombre_de_fichero(self):
        (self.repo / ("notas-" + _rev("ogeid") + ".md")).write_text("x\n", encoding="utf-8")
        donde = {d for d, _, _, _ in self.fugas.escanear(self.repo)}
        self.assertIn("nombre de fichero", donde)


# ---------------------------------------------------------------- sabotaje

SABOTAJES = [
    ("hash cambiado en el manifiesto: no comprueba la huella",
     [("if huella(datos) != esperado:", "if False:")],
     ["Actualizar.test_hash_cambiado_en_el_manifiesto", "Actualizar.test_fichero_cambiado_por_el_camino"]),
    ("fichero modificado por el usuario: pisa lo suyo",
     [("elif h_instalada is not None and h_local == h_instalada:", "elif True:")],
     ["Actualizar.test_fichero_modificado_por_el_usuario",
      "Actualizar.test_marcas_lo_de_dentro_cambiado_por_el_usuario"]),
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
     ["Actualizar.test_01_a_02_un_commit_y_revert_byte_a_byte"]),
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


def sabotaje():
    global V, VOID_PY
    original = VOID_PY.read_text(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="void-sabotaje-"))
    fallos = 0
    try:
        for nombre, cambios, pruebas in SABOTAJES:
            texto = original
            for buscar, poner in cambios:
                if buscar not in texto:
                    print("EL SABOTAJE NO SE PUDO APLICAR ({}): no encuentro {!r}".format(nombre, buscar[:60]))
                    fallos += 1
                    break
                texto = texto.replace(buscar, poner)
            else:
                roto = tmp / "void.py"
                roto.write_text(texto, encoding="utf-8")
                V, VOID_PY = cargar(roto), roto
                r = correr_pruebas(pruebas)
                rojas = r.failures + r.errors
                if not rojas:
                    print("NO LO CAZA: " + nombre)
                    fallos += 1
                else:
                    print("ROJO, como debe | " + nombre)
                    for prueba, traza in rojas:
                        print("    {} -> {}".format(prueba.id().split(".", 1)[1], razon(traza)))
    finally:
        V, VOID_PY = REF, AQUI / "void.py"
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
