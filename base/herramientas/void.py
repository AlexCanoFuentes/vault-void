#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Void: trae la base común de los vaults, o una estrella del catálogo, y la deja en un commit que
se deshace.

Uso, desde la carpeta del vault:
  python herramientas/void.py estado
  python herramientas/void.py actualizar
  python herramientas/void.py actualizar --conectar     la primera vez (el vault aún no tiene void.json)
  python herramientas/void.py traer <estrella>          trae una estrella del catálogo, o la actualiza
  python herramientas/void.py traer <estrella> --conectar   igual, en un vault que aún no tiene void.json

Opciones:
  --vault CARPETA     el vault sobre el que trabaja. Si no se dice: la carpeta de encima de
                      herramientas/ cuando void.py vive ahí; si no, la carpeta actual.
  --desde RUTA        trae de una carpeta o de un .zip en vez de GitHub (para probar).

Qué garantiza:
  - Comprueba la huella (sha256) de cada fichero contra base/MANIFIESTO.json, o contra
    catalogo.json si es una estrella, ANTES de escribir. Si una no cuadra, no escribe nada.
  - Nunca ejecuta lo que descarga: solo lo escribe, y solo dentro del vault.
  - No pisa lo tuyo: si cambiaste un fichero de la base o de una estrella, deja la versión nueva al
    lado como <fichero>.base-nueva y te lo dice. Una estrella tampoco pisa lo de la base ni lo de
    otra estrella.
  - En los .md de la base con <!-- base:inicio --> y <!-- base:fin -->, solo cambia lo de dentro.
  - Deja UN commit: «void: base <versión>» o «void: estrella <nombre> <versión>».
    Para deshacerlo: git revert HEAD.

Solo biblioteca estándar de Python 3.8 o más nuevo, y git. Funciona igual en Windows.
"""
import hashlib
import io
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REPO = "AlexCanoFuentes/vault-void"
RAMA = "main"
# GitHub documenta github.com/<repo>/archive/refs/heads/<rama>.zip, que redirige aquí:
# https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives
URL_BASE = "https://codeload.github.com/{}/zip/refs/heads/{}".format(REPO, RAMA)

MANIFIESTO = "MANIFIESTO.json"
CATALOGO = "catalogo.json"
NIVELES = ("oficiales", "socio", "comunidad")
LIGAS = ("grande", "pequeña")
VOID_JSON = "void.json"
SUFIJO_NUEVA = ".base-nueva"
MARCA_INICIO = "<!-- base:inicio -->"
MARCA_FIN = "<!-- base:fin -->"

MAX_DESCARGA = 20 * 1024 * 1024   # el zip entero
MAX_FICHERO = 5 * 1024 * 1024     # cada fichero de la base o de una estrella
TIEMPO_RED = 30                   # segundos

MSG_SIN_RED = ("No hay conexión a internet para descargar de Void: si estás en Codex, pide permiso "
               "de red para este comando, o ejecútalo tú en una terminal.")
MSG_SIN_VOID_JSON = ("Esta carpeta no está conectada a Void (no tiene void.json), así que no toco nada. "
                     "Si es tu vault y quieres conectarlo, ejecuta "
                     "«python herramientas/void.py actualizar --conectar».")
MSG_SIN_VOID_JSON_ESTRELLA = ("Esta carpeta no está conectada a Void (no tiene void.json), así que no toco "
                              "nada. Si es tu vault, añade --conectar: «python herramientas/void.py traer "
                              "{} --conectar».")

PROHIBIDOS_WINDOWS = set('<>:"|?*\\')
RESERVADOS_WINDOWS = {"con", "prn", "aux", "nul"} | {"com%d" % i for i in range(1, 10)} | {
    "lpt%d" % i for i in range(1, 10)}


class Fallo(Exception):
    """Un error que se le enseña a la persona tal cual, en una frase."""


# ---------------------------------------------------------------- huellas y marcas

def huella(datos):
    """sha256 del contenido. En texto, \\r\\n cuenta como \\n: el mismo fichero en Windows y en
    Mac tiene la misma huella."""
    if b"\0" not in datos:
        datos = datos.replace(b"\r\n", b"\n")
    return hashlib.sha256(datos).hexdigest()


def partir_marcas(datos):
    """Devuelve (antes, bloque, despues) en bytes, con las líneas de marca dentro de antes y
    despues. None si no hay exactamente una marca de inicio seguida de una de fin."""
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        return None
    lineas = texto.splitlines(True)
    inicios = [i for i, l in enumerate(lineas) if l.strip() == MARCA_INICIO]
    fines = [i for i, l in enumerate(lineas) if l.strip() == MARCA_FIN]
    if len(inicios) != 1 or len(fines) != 1 or fines[0] < inicios[0]:
        return None
    a, b = inicios[0], fines[0]
    return ("".join(lineas[:a + 1]).encode("utf-8"),
            "".join(lineas[a + 1:b]).encode("utf-8"),
            "".join(lineas[b:]).encode("utf-8"))


def usa_crlf(datos):
    return b"\r\n" in datos


def con_finales(datos, crlf):
    """Pone los finales de línea que ya usa el fichero de la persona."""
    if b"\0" in datos:
        return datos
    datos = datos.replace(b"\r\n", b"\n")
    return datos.replace(b"\n", b"\r\n") if crlf else datos


def envolver(local, bloque):
    """Si el tramo de la base está tal cual, una sola vez y sin marcas, le pone las marcas alrededor.
    No cambia ni una letra más. None si no se puede."""
    try:
        texto, buscado = local.decode("utf-8"), bloque.decode("utf-8")
    except UnicodeDecodeError:
        return None
    objetivo = buscado.replace("\r\n", "\n").splitlines()
    lineas = texto.splitlines(True)
    limpias = [l.rstrip("\r\n") for l in lineas]
    n = len(objetivo)
    if not n or not any(l.strip() for l in objetivo):
        return None
    sitios = [i for i in range(len(limpias) - n + 1) if limpias[i:i + n] == objetivo]
    if len(sitios) != 1:
        return None
    i = sitios[0]
    salto = "\r\n" if lineas and lineas[0].endswith("\r\n") else "\n"
    medio = "".join(lineas[i:i + n])
    if not medio.endswith("\n"):
        medio += salto
    return ("".join(lineas[:i]) + MARCA_INICIO + salto + medio + MARCA_FIN + salto
            + "".join(lineas[i + n:])).encode("utf-8")


def es_md_con_marcas(ruta, datos):
    return ruta.lower().endswith(".md") and partir_marcas(datos) is not None


# ---------------------------------------------------------------- rutas

def ruta_segura(ruta):
    """Una ruta del manifiesto solo vale si cae dentro del vault y se puede crear en Windows."""
    if not isinstance(ruta, str) or not ruta or "\\" in ruta or ruta.startswith("/"):
        return False
    partes = PurePosixPath(ruta).parts
    if not partes or PurePosixPath(ruta).as_posix() != ruta:
        return False
    for p in partes:
        if p in ("", ".", "..") or p.lower() == ".git":
            return False
        if any(c in PROHIBIDOS_WINDOWS or ord(c) < 32 for c in p):
            return False
        if p.endswith((" ", ".")) or p.split(".")[0].lower() in RESERVADOS_WINDOWS:
            return False
    if ruta == VOID_JSON or ruta.endswith(SUFIJO_NUEVA):
        return False
    return True


def dentro(vault, destino):
    """True si destino, con los enlaces resueltos, sigue dentro del vault."""
    try:
        destino.resolve().relative_to(vault.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- de dónde sale la base

def validar_manifiesto(datos):
    try:
        m = json.loads(datos.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise Fallo("El manifiesto de la base está roto: no he escrito nada.")
    version = m.get("version") if isinstance(m, dict) else None
    ficheros = m.get("ficheros") if isinstance(m, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r"\d+(\.\d+)*", version):
        raise Fallo("El manifiesto de la base no dice una versión válida: no he escrito nada.")
    if not isinstance(ficheros, dict) or not ficheros:
        raise Fallo("El manifiesto de la base no lista ficheros: no he escrito nada.")
    vistos = set()
    for ruta, h in ficheros.items():
        if not ruta_segura(ruta):
            raise Fallo("El manifiesto de la base trae una ruta que saldría del vault o no vale "
                        "en Windows ({}): no he escrito nada.".format(ruta))
        if not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h):
            raise Fallo("El manifiesto de la base trae una huella rota para {}: no he escrito nada."
                        .format(ruta))
        if ruta.lower() in vistos:
            raise Fallo("El manifiesto de la base repite {} (en Windows serían el mismo fichero): "
                        "no he escrito nada.".format(ruta))
        vistos.add(ruta.lower())
    return version, dict(ficheros)


class Fuente:
    """La base: su manifiesto y una forma de leer cada fichero. No ejecuta nada."""

    def __init__(self, descripcion, leer):
        self.descripcion = descripcion
        self._leer = leer
        crudo = leer(MANIFIESTO)
        if crudo is None:
            raise Fallo("No encuentro base/{} en {}: no he escrito nada.".format(MANIFIESTO, descripcion))
        self.version, self.ficheros = validar_manifiesto(crudo)

    def leer_comprobado(self):
        """Lee todos los ficheros del manifiesto y comprueba su huella. Si uno falla, no
        devuelve ninguno."""
        contenido = {}
        for ruta, esperado in sorted(self.ficheros.items()):
            datos = self._leer(ruta)
            if datos is None:
                raise Fallo("A la base le falta {}, que su manifiesto sí lista: no he escrito nada."
                            .format(ruta))
            if huella(datos) != esperado:
                raise Fallo("La base no cuadra con su manifiesto en {}: puede haberse cambiado por el "
                            "camino, así que no he escrito nada. Vuelve a probar más tarde y, si se "
                            "repite, avisa a quien mantiene la base.".format(ruta))
            contenido[ruta] = datos
        return contenido


def lector_de_carpeta(raiz):
    """Una forma de leer ficheros de una carpeta, por su ruta posix. No sigue enlaces."""
    def leer(ruta):
        p = raiz.joinpath(*PurePosixPath(ruta).parts)
        if not p.is_file() or p.is_symlink():
            return None
        if p.stat().st_size > MAX_FICHERO:
            raise Fallo("{} pesa demasiado para venir de Void: no he escrito nada.".format(ruta))
        return p.read_bytes()
    return leer


def lector_de_zip(datos, descripcion, ancla):
    """Una forma de leer ficheros de un zip como los de GitHub (todo dentro de una carpeta), por su
    ruta posix desde esa carpeta. ancla es un fichero que tiene que estar, una sola vez."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        raise Fallo("Lo descargado no es un zip válido: no he escrito nada. Vuelve a probar más tarde.")
    nombres = zf.namelist()
    candidatos = [n for n in nombres if re.fullmatch(r"[^/]+/" + re.escape(ancla), n)]
    if len(candidatos) != 1:
        raise Fallo("En {} no está {}: no he escrito nada.".format(descripcion, ancla))
    prefijo = candidatos[0][:-len(ancla)]
    entradas = set(nombres)

    def leer(ruta):
        nombre = prefijo + ruta
        if nombre not in entradas:
            return None
        info = zf.getinfo(nombre)
        if info.file_size > MAX_FICHERO:
            raise Fallo("{} pesa demasiado para venir de Void: no he escrito nada.".format(ruta))
        with zf.open(info) as f:
            leido = f.read(MAX_FICHERO + 1)
        if len(leido) > MAX_FICHERO:
            raise Fallo("{} pesa demasiado para venir de Void: no he escrito nada.".format(ruta))
        return leido
    return leer


def fuente_de_carpeta(carpeta):
    raiz = carpeta / "base" if (carpeta / "base" / MANIFIESTO).is_file() else carpeta
    return Fuente(str(raiz), lector_de_carpeta(raiz))


def fuente_de_zip(datos, descripcion):
    leer = lector_de_zip(datos, descripcion, "base/" + MANIFIESTO)
    return Fuente(descripcion, lambda ruta: leer("base/" + ruta))


def descargar(url=URL_BASE):
    return fuente_de_zip(bajar(url), "GitHub ({})".format(REPO))


def bajar(url=URL_BASE):
    """El zip del repo de Void, en bytes."""
    try:
        with urllib.request.urlopen(url, timeout=TIEMPO_RED) as r:
            datos = r.read(MAX_DESCARGA + 1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise Fallo("No encuentro Void en GitHub ({}): puede que la dirección haya cambiado; "
                        "avisa a quien te pasó el vault.".format(url))
        raise Fallo("GitHub ha contestado con un error ({}): vuelve a probar en un rato.".format(e.code))
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLError):
            raise Fallo("No he podido comprobar que la conexión es con GitHub de verdad, así que no "
                        "sigo: revisa la fecha y la hora del ordenador y vuelve a probar.")
        raise Fallo(MSG_SIN_RED)
    except (socket.timeout, TimeoutError, ConnectionError, OSError):
        raise Fallo(MSG_SIN_RED)
    if len(datos) > MAX_DESCARGA:
        raise Fallo("Lo descargado pesa más de lo que puede pesar Void: no he escrito nada.")
    return datos


def abrir_fuente(desde):
    if desde is None:
        return descargar()
    p = Path(desde)
    if p.is_dir():
        return fuente_de_carpeta(p)
    if p.is_file():
        return fuente_de_zip(p.read_bytes(), str(p))
    raise Fallo("No existe {}: dime una carpeta o un .zip con la base.".format(desde))


# ---------------------------------------------------------------- de dónde salen las estrellas

RE_NOMBRE_ESTRELLA = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def validar_estrella(nombre, e):
    """Comprueba la entrada del catálogo de una estrella antes de leer ningún fichero suyo."""
    malo = "La entrada de {} en el catálogo está rota ({}): no he escrito nada."
    if not isinstance(e, dict):
        raise Fallo(malo.format(nombre, "no es un objeto"))
    if not isinstance(e.get("version"), str) or not re.fullmatch(r"\d+(\.\d+)*", e["version"]):
        raise Fallo(malo.format(nombre, "versión"))
    if e.get("nivel") not in NIVELES or e.get("liga") not in LIGAS:
        raise Fallo(malo.format(nombre, "nivel o liga"))
    if e.get("ruta") != "estrellas/{}/{}".format(e["nivel"], nombre):
        raise Fallo(malo.format(nombre, "ruta"))
    ficheros = e.get("ficheros")
    if not isinstance(ficheros, dict) or not ficheros:
        raise Fallo(malo.format(nombre, "no lista ficheros"))
    vistos = set()
    for ruta, h in ficheros.items():
        if not ruta_segura(ruta):
            raise Fallo("La estrella {} trae una ruta que saldría del vault o no vale en Windows ({}): "
                        "no he escrito nada.".format(nombre, ruta))
        if not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h):
            raise Fallo(malo.format(nombre, "huella de " + ruta))
        if ruta.lower() in vistos:
            raise Fallo(malo.format(nombre, "repite " + ruta))
        vistos.add(ruta.lower())
    no_se_instala = e.get("no_se_instala", [])
    if not isinstance(no_se_instala, list) or any(r not in ficheros for r in no_se_instala):
        raise Fallo(malo.format(nombre, "no_se_instala"))
    instalar = e.get("instalar", [])
    if not isinstance(instalar, list) or not all(isinstance(x, str) for x in instalar):
        raise Fallo(malo.format(nombre, "instalar"))
    return e


class Catalogo:
    """El catálogo de Void y una forma de leer los ficheros de cada estrella. No ejecuta nada."""

    def __init__(self, descripcion, leer):
        self.descripcion = descripcion
        self._leer = leer
        crudo = leer(CATALOGO)
        if crudo is None:
            raise Fallo("No encuentro {} en {}: no he escrito nada.".format(CATALOGO, descripcion))
        try:
            datos = json.loads(crudo.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise Fallo("El catálogo está roto: no he escrito nada.")
        estrellas = datos.get("estrellas") if isinstance(datos, dict) else None
        if not isinstance(estrellas, dict):
            raise Fallo("El catálogo no lista estrellas: no he escrito nada.")
        self.estrellas = estrellas

    def estrella(self, nombre):
        if not RE_NOMBRE_ESTRELLA.fullmatch(nombre or "") or nombre not in self.estrellas:
            hay = ", ".join(sorted(self.estrellas)) or "ninguna"
            raise Fallo("No hay ninguna estrella que se llame «{}» en el catálogo. Las que hay: {}."
                        .format(nombre, hay))
        return validar_estrella(nombre, self.estrellas[nombre])

    def leer_estrella(self, nombre, e):
        """{ruta: bytes} de lo que se instala, con cada huella comprobada contra el catálogo. Si una
        no cuadra, no devuelve ninguna."""
        contenido = {}
        for ruta, esperada in sorted(e["ficheros"].items()):
            if ruta in e.get("no_se_instala", []):
                continue
            datos = self._leer(e["ruta"] + "/" + ruta)
            if datos is None:
                raise Fallo("A la estrella {} le falta {}, que el catálogo sí lista: no he escrito nada."
                            .format(nombre, ruta))
            if huella(datos) != esperada:
                raise Fallo("La estrella {} no cuadra con el catálogo en {}: puede haberse cambiado por el "
                            "camino, así que no he escrito nada. Vuelve a probar más tarde y, si se repite, "
                            "avisa a quien mantiene Void.".format(nombre, ruta))
            contenido[ruta] = datos
        return contenido


def abrir_catalogo(desde):
    if desde is None:
        return Catalogo("GitHub ({})".format(REPO), lector_de_zip(bajar(), "GitHub ({})".format(REPO), CATALOGO))
    p = Path(desde)
    if p.is_dir():
        return Catalogo(str(p), lector_de_carpeta(p))
    if p.is_file():
        return Catalogo(str(p), lector_de_zip(p.read_bytes(), str(p), CATALOGO))
    raise Fallo("No existe {}: dime una carpeta o un .zip con el catálogo.".format(desde))


# ---------------------------------------------------------------- git

def git(vault, *args, comprobar=True):
    try:
        r = subprocess.run(["git", "-C", str(vault)] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise Fallo("Falta git en este ordenador: instálalo (en Windows, «winget install --id Git.Git -e») "
                    "y vuelve a probar.")
    salida = r.stdout.decode("utf-8", "replace")
    if comprobar and r.returncode != 0:
        raise Fallo(r.stderr.decode("utf-8", "replace").strip() or "git falló")
    return r.returncode, salida


def raiz_git(vault):
    codigo, salida = git(vault, "rev-parse", "--show-toplevel", comprobar=False)
    return Path(salida.strip()) if codigo == 0 and salida.strip() else None


def comprobar_repo(vault, conectar):
    """Devuelve True si hay que crear el repositorio (solo al conectar una carpeta sin git)."""
    if (vault / "base" / MANIFIESTO).is_file() and (vault / "void.py").is_file():
        raise Fallo("{} es el propio repositorio de Void, no un vault: no toco nada.".format(vault))
    if not vault.is_dir():
        if not conectar:
            raise Fallo("No existe la carpeta {}.".format(vault))
        return True
    raiz = raiz_git(vault)
    if raiz is not None and raiz.resolve() == vault.resolve():
        return False
    if raiz is not None:
        raise Fallo("{} está dentro de otro repositorio ({}): el vault tiene que ser su propia "
                    "carpeta de git, así que no toco nada.".format(vault, raiz))
    if not conectar:
        raise Fallo("{} no es un repositorio de git, así que no toco nada.".format(vault))
    return True


def finales_de_git(vault, rutas):
    """Para ficheros que aún no existen: True si git los sacaría con \r\n (Windows con
    core.autocrlf, o eol=crlf), False si con \n, None si git no los toca (binarios)."""
    if not rutas:
        return {}
    _, auto = git(vault, "config", "--get", "core.autocrlf", comprobar=False)
    por_defecto = auto.strip().lower() == "true"
    _, salida = git(vault, "check-attr", "-z", "eol", "text", "--", *rutas, comprobar=False)
    campos = salida.split("\0")
    attrs = {}
    for i in range(0, len(campos) - 2, 3):
        attrs.setdefault(campos[i], {})[campos[i + 1]] = campos[i + 2]
    salida = {}
    for r in rutas:
        a = attrs.get(r, {})
        if a.get("eol") == "crlf":
            salida[r] = True
        elif a.get("eol") == "lf":
            salida[r] = False
        elif a.get("text") == "unset":
            salida[r] = None
        else:
            salida[r] = por_defecto
    return salida


def sin_guardar(vault, rutas):
    """Rutas con cambios que aún no están en un commit."""
    if not rutas:
        return []
    _, salida = git(vault, "status", "--porcelain", "-z", "--untracked-files=all", "--", *rutas)
    return [t[3:] for t in salida.split("\0") if len(t) > 3]


# ---------------------------------------------------------------- el vault

def leer_void_json(vault):
    p = vault / VOID_JSON
    if not p.is_file():
        return None
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(v, dict) and isinstance(v.get("ficheros", {}), dict)
        estrellas = v.get("estrellas", {})
        assert isinstance(estrellas, dict)
        assert all(isinstance(e, dict) and isinstance(e.get("ficheros", {}), dict) for e in estrellas.values())
        return v
    except (ValueError, AssertionError, UnicodeDecodeError):
        raise Fallo("void.json está roto, así que no toco nada: recupéralo con "
                    "«git checkout -- void.json».")


def escribir_void_json(version, instalados, descripcion, estrellas=None):
    """version None: el vault no tiene la base (solo estrellas)."""
    datos = {"aviso": "Lo escribe herramientas/void.py. No se cambia a mano."}
    if version is not None:
        datos["base"] = version
        datos["fuente"] = descripcion
    datos["ficheros"] = dict(sorted(instalados.items()))
    if estrellas:
        datos["estrellas"] = {n: estrellas[n] for n in sorted(estrellas)}
    return (json.dumps(datos, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def plan(vault, actual, version, nuevos, marcas_md=True):
    """Decide qué pasa con cada fichero. No escribe nada.

    Devuelve (escrituras, borrados, instalados, avisos, resumen):
      escrituras: {ruta: bytes} a escribir
      borrados:   [ruta] a borrar
      instalados: {ruta: huella} para void.json
      avisos:     frases para la persona
    """
    instalados_antes = dict((actual or {}).get("ficheros", {}))
    escrituras, borrados, avisos = {}, [], []
    instalados = {}
    resumen = {"nuevos": [], "cambiados": [], "marcados": [], "iguales": [], "tuyos": [], "quitados": []}

    for ruta, base in sorted(nuevos.items()):
        destino = vault.joinpath(*PurePosixPath(ruta).parts)
        if not dentro(vault, destino) or destino.is_symlink():
            raise Fallo("{} apunta fuera del vault (es un enlace), así que no toco nada.".format(ruta))
        marcas = marcas_md and es_md_con_marcas(ruta, base)
        propio = partir_marcas(base)[1] if marcas else base
        h_nueva = huella(propio)
        h_instalada = instalados_antes.get(ruta)
        local = destino.read_bytes() if destino.is_file() else None

        if local is None:
            if h_instalada is None:
                escrituras[ruta] = base
                instalados[ruta] = h_nueva
                resumen["nuevos"].append(ruta)
            else:
                escrituras[ruta + SUFIJO_NUEVA] = base
                if h_instalada:
                    instalados[ruta] = h_instalada
                resumen["tuyos"].append(ruta)
                avisos.append("No he puesto {0} porque lo borraste tú; la versión nueva está en "
                              "{0}{1}.".format(ruta, SUFIJO_NUEVA))
            continue

        crlf = usa_crlf(local)
        if marcas:
            partes = partir_marcas(local)
            envuelto = envolver(local, propio) if partes is None else None
            if envuelto is not None:
                escrituras[ruta] = envuelto
                instalados[ruta] = h_nueva
                resumen["marcados"].append(ruta)
                avisos.append("En {} he puesto las marcas {} y {} alrededor del tramo que ya era igual "
                              "que la base; no he cambiado nada más.".format(ruta, MARCA_INICIO, MARCA_FIN))
                continue
            if partes is None:
                escrituras[ruta + SUFIJO_NUEVA] = con_finales(base, crlf)
                if h_instalada:
                    instalados[ruta] = h_instalada
                resumen["tuyos"].append(ruta)
                avisos.append("No he tocado {0} porque no tiene las marcas {1} y {2}; la versión nueva "
                              "está en {0}{3}.".format(ruta, MARCA_INICIO, MARCA_FIN, SUFIJO_NUEVA))
                continue
            antes, bloque, despues = partes
            h_local = huella(bloque)
            resultado = antes + con_finales(propio, crlf) + despues
        else:
            h_local = huella(local)
            resultado = con_finales(base, crlf)

        if h_local == h_nueva:
            instalados[ruta] = h_nueva
            resumen["iguales"].append(ruta)
        elif h_instalada is not None and h_local == h_instalada:
            escrituras[ruta] = resultado
            instalados[ruta] = h_nueva
            resumen["cambiados"].append(ruta)
        else:
            escrituras[ruta + SUFIJO_NUEVA] = resultado
            if h_instalada:
                instalados[ruta] = h_instalada
            resumen["tuyos"].append(ruta)
            donde = "lo de dentro de las marcas de " if marcas else ""
            avisos.append("No he tocado {0} porque cambiaste {1}{0}; la versión nueva está en {0}{2}: "
                          "compáralas y quédate con lo que quieras.".format(ruta, donde, SUFIJO_NUEVA))

    for ruta, h_instalada in sorted(instalados_antes.items()):
        if ruta in nuevos or not ruta_segura(ruta):
            continue
        destino = vault.joinpath(*PurePosixPath(ruta).parts)
        if not destino.is_file() or not dentro(vault, destino):
            continue
        local = destino.read_bytes()
        if not ruta.lower().endswith(".md") and huella(local) == h_instalada:
            borrados.append(ruta)
            resumen["quitados"].append(ruta)
        else:
            avisos.append("{} ya no es parte de la base; lo dejo como está y deja de actualizarse."
                          .format(ruta))

    return escrituras, borrados, instalados, avisos, resumen


def aplicar(vault, escrituras, borrados, void_json, mensaje):
    """Escribe, borra y hace el commit. Si algo falla antes del commit, lo deja todo como estaba."""
    escrituras = dict(escrituras)
    escrituras[VOID_JSON] = void_json
    nuevos = [r for r in escrituras if not vault.joinpath(*PurePosixPath(r).parts).is_file()]
    finales = finales_de_git(vault, nuevos)
    cambian = {}
    for ruta, datos in escrituras.items():
        destino = vault.joinpath(*PurePosixPath(ruta).parts)
        previo = destino.read_bytes() if destino.is_file() else None
        # Los finales de línea, como los dejaría git: así git revert HEAD lo deja byte a byte.
        crlf = usa_crlf(previo) if previo is not None else finales.get(ruta)
        if crlf is not None:
            datos = con_finales(datos, crlf)
        if previo != datos:
            cambian[ruta] = datos
    rutas = sorted(set(cambian) | set(borrados))
    if not rutas:
        return False

    vigiladas = [r for r in rutas if not r.endswith(SUFIJO_NUEVA)]
    sucias = sin_guardar(vault, [r for r in vigiladas
                                 if vault.joinpath(*PurePosixPath(r).parts).exists()])
    if sucias:
        raise Fallo("Tienes cambios sin guardar en {}: guárdalos en un commit (o deshazlos) y vuelve "
                    "a probar. No he tocado nada.".format(", ".join(sorted(sucias))))

    copia = {}
    try:
        for ruta in rutas:
            destino = vault.joinpath(*PurePosixPath(ruta).parts)
            if not dentro(vault, destino.parent if not destino.exists() else destino):
                raise Fallo("{} saldría del vault, así que no lo escribo.".format(ruta))
            copia[ruta] = destino.read_bytes() if destino.is_file() else None
            if ruta in borrados:
                destino.unlink()
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            if not dentro(vault, destino.parent):
                raise Fallo("{} saldría del vault, así que no lo escribo.".format(ruta))
            fd, tmp = tempfile.mkstemp(dir=str(destino.parent), prefix=".void-")
            with os.fdopen(fd, "wb") as f:
                f.write(cambian[ruta])
            os.replace(tmp, str(destino))
        git(vault, "add", "-A", "--", *rutas)
        codigo, _ = git(vault, "commit", "-q", "-m", mensaje, "--", *rutas, comprobar=False)
        if codigo != 0:
            raise Fallo("git no ha podido guardar el commit (¿tiene tu nombre y correo? "
                        "«git config user.name» y «git config user.email»). He dejado todo como estaba.")
    except BaseException:
        for ruta, previo in copia.items():
            destino = vault.joinpath(*PurePosixPath(ruta).parts)
            if previo is None:
                if destino.exists():
                    destino.unlink()
            else:
                destino.write_bytes(previo)
        codigo, _ = git(vault, "reset", "-q", "--", *rutas, comprobar=False)
        if codigo != 0:  # repositorio recién creado, sin ningún commit todavía
            git(vault, "rm", "-q", "--cached", "--ignore-unmatch", "--", *rutas, comprobar=False)
        raise
    return True


def pendientes(vault):
    salida = []
    for raiz, dirs, ficheros in os.walk(str(vault)):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in ficheros:
            if f.endswith(SUFIJO_NUEVA):
                salida.append(Path(raiz, f).relative_to(vault).as_posix())
    return sorted(salida)


# ---------------------------------------------------------------- órdenes

def estado_ficheros(vault, ficheros):
    for ruta, h in sorted(ficheros.items()):
        destino = vault.joinpath(*PurePosixPath(ruta).parts)
        if not ruta_segura(ruta) or not destino.is_file():
            como = "falta"
        else:
            local = destino.read_bytes()
            partes = partir_marcas(local) if ruta.lower().endswith(".md") else None
            huellas = {huella(local)} | ({huella(partes[1])} if partes else set())
            como = "como se instaló" if h in huellas else "cambiado por ti"
        print("  {:<17} {}".format(como, ruta))


def contar_ficheros(resumen):
    partes = []
    for clave, uno, varios in (("nuevos", "nuevo", "nuevos"), ("cambiados", "cambiado", "cambiados"),
                               ("marcados", "con marcas puestas", "con marcas puestas"),
                               ("iguales", "sin cambios", "sin cambios"),
                               ("tuyos", "sin tocar porque es tuyo", "sin tocar porque son tuyos"),
                               ("quitados", "quitado", "quitados")):
        n = len(resumen[clave])
        if n:
            partes.append("{} {}".format(n, uno if n == 1 else varios))
    return "Ficheros: " + ", ".join(partes) + "."


def orden_estado(vault, desde):
    actual = leer_void_json(vault)
    if actual is None:
        raise Fallo(MSG_SIN_VOID_JSON)
    print("Vault: {}".format(vault))
    if "base" in actual:
        print("Base instalada: {}".format(actual.get("base", "?")))
        try:
            fuente = abrir_fuente(desde)
            if fuente.version == actual.get("base"):
                print("Base disponible: {} (es la que tienes).".format(fuente.version))
            else:
                print("Base disponible: {}. Para traerla: python herramientas/void.py actualizar"
                      .format(fuente.version))
        except Fallo as e:
            print("No he podido mirar si hay base nueva. {}".format(e))
        print("Ficheros de la base:")
        estado_ficheros(vault, actual.get("ficheros", {}))
    else:
        print("Base: no la tienes (este vault solo tiene estrellas).")
    for nombre, e in sorted(actual.get("estrellas", {}).items()):
        print("Estrella {} {} ({}, liga {}):".format(nombre, e.get("version", "?"), e.get("nivel", "?"),
                                                     e.get("liga", "?")))
        estado_ficheros(vault, e.get("ficheros", {}))
    nuevas = pendientes(vault)
    if nuevas:
        print("Por revisar (versión nueva que no puse para no pisar lo tuyo):")
        for r in nuevas:
            print("  " + r)
    return 0


def orden_actualizar(vault, desde, conectar):
    actual = leer_void_json(vault)
    if actual is None and not conectar:
        raise Fallo(MSG_SIN_VOID_JSON)
    if actual is not None and conectar:
        conectar = False
    crear_repo = comprobar_repo(vault, conectar)

    fuente = abrir_fuente(desde)
    nuevos = fuente.leer_comprobado()
    if crear_repo:
        vault.mkdir(parents=True, exist_ok=True)
        git(vault, "init", "-q")
    escrituras, borrados, instalados, avisos, resumen = plan(vault, actual, fuente.version, nuevos)
    antes = (actual or {}).get("base")
    # Con --desde no se apunta la ruta: es de la máquina de quien prueba y acabaría en el commit.
    void_json = escribir_void_json(fuente.version, instalados, "copia local (--desde)"
                                   if desde else "github.com/{} ({})".format(REPO, RAMA),
                                   estrellas=(actual or {}).get("estrellas"))
    mensaje = "void: base {}".format(fuente.version)
    hecho = aplicar(vault, escrituras, borrados, void_json, mensaje)

    if not hecho:
        print("Ya tienes la base {}. No hay nada que actualizar.".format(fuente.version))
    else:
        if antes is None:
            print("Vault conectado a Void con la base {}, en un commit («{}»).".format(fuente.version, mensaje))
        elif antes == fuente.version:
            print("Base {} al día, en un commit («{}»).".format(fuente.version, mensaje))
        else:
            print("Base actualizada de {} a {}, en un commit («{}»).".format(antes, fuente.version, mensaje))
        print(contar_ficheros(resumen))
        print("Para deshacerlo: git revert HEAD")
    for a in avisos:
        print("OJO: " + a)
    return 0


def orden_traer(vault, nombre, desde, conectar_estrella):
    """Trae una estrella del catálogo (o la actualiza) en un commit propio que se deshace."""
    actual = leer_void_json(vault)
    if not conectar_estrella and actual is None:
        raise Fallo(MSG_SIN_VOID_JSON_ESTRELLA.format(nombre))
    crear_repo = comprobar_repo(vault, actual is None)

    catalogo = abrir_catalogo(desde)
    e = catalogo.estrella(nombre)
    nuevos = catalogo.leer_estrella(nombre, e)   # todas las huellas, antes de escribir nada
    if crear_repo:
        vault.mkdir(parents=True, exist_ok=True)
        git(vault, "init", "-q")

    estrellas = dict((actual or {}).get("estrellas", {}))
    previa = estrellas.get(nombre, {})
    # Lo que ya es de la base o de otra estrella no es de esta: no lo pisa ni lo hace suyo.
    ajenos = {r: "la base" for r in (actual or {}).get("ficheros", {})}
    for otra, datos in estrellas.items():
        if otra != nombre:
            ajenos.update({r: "la estrella " + otra for r in datos.get("ficheros", {})})
    propios = {r: d for r, d in nuevos.items() if r not in ajenos}
    antes = {"ficheros": {r: h for r, h in previa.get("ficheros", {}).items() if r not in ajenos}}
    escrituras, borrados, instalados, avisos, resumen = plan(vault, antes, e["version"], propios,
                                                              marcas_md=False)
    for ruta in sorted(set(nuevos) - set(propios)):
        destino = vault.joinpath(*PurePosixPath(ruta).parts)
        if not dentro(vault, destino) or destino.is_symlink():
            raise Fallo("{} apunta fuera del vault (es un enlace), así que no toco nada.".format(ruta))
        local = destino.read_bytes() if destino.is_file() else None
        if local is not None and huella(local) == huella(nuevos[ruta]):
            resumen["iguales"].append(ruta)
            continue
        escrituras[ruta + SUFIJO_NUEVA] = con_finales(nuevos[ruta], usa_crlf(local or b""))
        resumen["tuyos"].append(ruta)
        avisos.append("No he tocado {0} porque es de {1}; la versión de la estrella está en {0}{2}."
                      .format(ruta, ajenos[ruta], SUFIJO_NUEVA))

    estrellas[nombre] = {"version": e["version"], "nivel": e["nivel"], "liga": e["liga"],
                         "ficheros": dict(sorted(instalados.items()))}
    if actual is not None and "base" in actual:
        void_json = escribir_void_json(actual["base"], actual.get("ficheros", {}), actual.get("fuente"),
                                       estrellas=estrellas)
    else:
        void_json = escribir_void_json(None, (actual or {}).get("ficheros", {}), None, estrellas=estrellas)
    mensaje = "void: estrella {} {}".format(nombre, e["version"])
    hecho = aplicar(vault, escrituras, borrados, void_json, mensaje)

    version_antes = previa.get("version")
    if not hecho:
        print("Ya tienes la estrella {} {}. No hay nada que traer.".format(nombre, e["version"]))
    else:
        if version_antes is None:
            print("Estrella {} {} traída, en un commit («{}»).".format(nombre, e["version"], mensaje))
        elif version_antes == e["version"]:
            print("Estrella {} {} al día, en un commit («{}»).".format(nombre, e["version"], mensaje))
        else:
            print("Estrella {} actualizada de {} a {}, en un commit («{}»).".format(
                nombre, version_antes, e["version"], mensaje))
        print(contar_ficheros(resumen))
        print("Para deshacerlo: git revert HEAD")
    for a in avisos:
        print("OJO: " + a)
    if e["liga"] != "grande":
        print("OJO: está en la liga pequeña (KERNEL {}): no ha pasado la puerta grande del catálogo."
              .format((e.get("kernel") or {}).get("total", "?")))
    if e["nivel"] == "comunidad":
        print("OJO: es de la comunidad. Léela antes de ejecutar nada de ella.")
    if hecho and e.get("instalar"):
        print("Para ponerla en marcha (void no ejecuta nada):")
        for paso in e["instalar"]:
            print("  - " + paso)
    return 0


def carpeta_vault(arg):
    if arg:
        return Path(arg).absolute()
    aqui = Path(__file__).resolve().parent
    if aqui.name == "herramientas":
        return aqui.parent
    return Path.cwd()


AYUDA = __doc__


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    args = list(argv)
    if not args or args[0] in ("-h", "--help", "ayuda"):
        print(AYUDA)
        return 0 if args else 2
    orden, resto = args[0], args[1:]
    vault_arg = desde = estrella = None
    conectar = False
    i = 0
    while i < len(resto):
        a = resto[i]
        if a in ("--vault", "--desde") and i + 1 < len(resto):
            if a == "--vault":
                vault_arg = resto[i + 1]
            else:
                desde = resto[i + 1]
            i += 2
        elif a == "--conectar" and orden in ("actualizar", "traer"):
            conectar = True
            i += 1
        elif orden == "traer" and estrella is None and not a.startswith("-"):
            estrella = a
            i += 1
        else:
            print("No entiendo «{}». Mira «python herramientas/void.py --help».".format(a), file=sys.stderr)
            return 2
    vault = carpeta_vault(vault_arg)
    try:
        if orden == "estado":
            return orden_estado(vault, desde)
        if orden == "actualizar":
            return orden_actualizar(vault, desde, conectar)
        if orden == "traer":
            if not estrella:
                print("Dime qué estrella: «python herramientas/void.py traer <estrella>».", file=sys.stderr)
                return 2
            return orden_traer(vault, estrella, desde, conectar)
    except Fallo as e:
        print(str(e), file=sys.stderr)
        return 1
    print("Las órdenes son «estado», «actualizar» y «traer».", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
