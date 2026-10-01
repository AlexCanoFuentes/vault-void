#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Escáner de fugas: este repo es público, así que cualquier fuga se publica.

Uso:
  python3 fugas.py [CARPETA]              tiene que decir «0 fugas»
  python3 fugas.py [CARPETA] --nombres F  añade nombres a vigilar (uno por línea, en un fichero
                                          que NO esté en el repo)

Mira, en cada fichero de la carpeta (los de git y los nuevos que git no ignora), en cada versión de
cada fichero que haya pasado por la historia, en los mensajes de commit y en los nombres y correos
de autor:
  - secretos: claves privadas, tokens de GitHub, OpenAI, Anthropic, AWS, Google, Slack, JWT,
    y «clave = "..."» con valor;
  - correos (menos los de ejemplo y los «noreply»);
  - teléfonos de España, Colombia y Argentina, y cualquiera con prefijo internacional;
  - nombres de las personas de los vaults.

Los nombres no están escritos aquí: estarían publicados en el propio escáner. Se guarda su sha256 y
se compara con el de cada palabra. Es una tapa, no un candado: un nombre corto se adivina probando.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

def _cargar_nombres():
    """Las huellas de los nombres viven en `.fugas-nombres`, junto a este fichero y fuera de git:
    publicarlas, aunque sea como sha256, es publicar una lista que se adivina probando.
    Una huella por línea; «mayuscula» detrás si el nombre también es palabra común."""
    todos, solo_mayus = set(), set()
    f = Path(__file__).with_name(".fugas-nombres")
    if f.exists():
        for linea in f.read_text(encoding="utf-8").splitlines():
            partes = linea.split()
            if partes:
                todos.add(partes[0])
                if "mayuscula" in partes[1:]:
                    solo_mayus.add(partes[0])
    return todos, solo_mayus


NOMBRES, SOLO_CON_MAYUSCULA = _cargar_nombres()

SECRETOS = [
    ("clave privada", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("token de GitHub", r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})"),
    ("clave de Anthropic", r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    ("clave de OpenAI", r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    ("clave de AWS", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("clave de Google", r"\bAIza[0-9A-Za-z_-]{35}"),
    ("token de Slack", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("clave con valor", r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|contrase[ñn]a|clave)\b"
                        r"\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']"),
]
CORREO = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
CORREOS_PERMITIDOS = re.compile(
    r"(?i)(@example\.(?:com|org|net)$|@users\.noreply\.github\.com$|^noreply@anthropic\.com$)")
TELEFONOS = [
    ("teléfono internacional", r"(?<![\w+])\+\d{1,3}[ .-]?\(?\d{1,4}\)?(?:[ .-]?\d{2,4}){2,4}(?![\w])"),
    ("teléfono de España", r"(?<![\w.+-])[6789]\d{2}(?:[ .-]?\d{3}){2}(?![\w.-]?\d)(?!\w)"),
    ("teléfono de España", r"(?<![\w.+-])[6789]\d{2}(?: \d{2}){3}(?!\w)"),
    ("teléfono de Colombia", r"(?<![\w.+-])3\d{2}[ .-]?\d{3}[ .-]?\d{4}(?!\w)"),
    ("teléfono de Argentina", r"(?<![\w.+-])(?:11|15)[ .-]?\d{4}[ .-]?\d{4}(?!\w)"),
]
PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")

COMPILADOS = ([(n, re.compile(p)) for n, p in SECRETOS] + [(n, re.compile(p)) for n, p in TELEFONOS])
RE_CORREO = re.compile(CORREO)


def h(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def tapar(s):
    s = s.strip()
    return s[:3] + "…" if len(s) > 3 else "…"


def nombres_extra(fichero):
    if not fichero:
        return set()
    return {h(l.strip().lower()) for l in Path(fichero).read_text(encoding="utf-8").splitlines() if l.strip()}


def revisar_texto(texto, nombres):
    """Devuelve [(línea, tipo, trozo tapado)]."""
    salida = []
    for n, linea in enumerate(texto.splitlines(), 1):
        for tipo, rx in COMPILADOS:
            for m in rx.finditer(linea):
                salida.append((n, tipo, tapar(m.group(0))))
        for m in RE_CORREO.finditer(linea):
            if not CORREOS_PERMITIDOS.search(m.group(0)):
                salida.append((n, "correo", tapar(m.group(0))))
        for m in PALABRA.finditer(linea):
            p = m.group(0)
            hp = h(p.lower())
            if hp in nombres and (hp not in SOLO_CON_MAYUSCULA or p[0].isupper()):
                salida.append((n, "nombre", tapar(p)))
    return salida


def git(raiz, *args):
    r = subprocess.run(["git", "-C", str(raiz)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.returncode, r.stdout


def escanear(raiz, nombres=None):
    """Devuelve [(dónde, línea, tipo, trozo tapado)]."""
    raiz = Path(raiz)
    nombres = NOMBRES | (nombres or set())
    hallazgos = []

    def mirar(donde, datos):
        if b"\0" in datos[:8000]:
            return
        for n, tipo, trozo in revisar_texto(datos.decode("utf-8", "replace"), nombres):
            hallazgos.append((donde, n, tipo, trozo))

    codigo, salida = git(raiz, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if codigo != 0:
        rutas = [p.relative_to(raiz).as_posix() for p in raiz.rglob("*")
                 if p.is_file() and ".git" not in p.relative_to(raiz).parts]
    else:
        rutas = [r for r in salida.decode("utf-8", "replace").split("\0") if r]
    for ruta in sorted(set(rutas)):
        p = raiz / ruta
        mirar("nombre de fichero", ruta.encode("utf-8"))
        if p.is_file():
            mirar(ruta, p.read_bytes())

    if codigo == 0:
        _, objetos = git(raiz, "rev-list", "--objects", "--all")
        vistos = set()
        for linea in objetos.decode("utf-8", "replace").splitlines():
            partes = linea.split(" ", 1)
            if len(partes) != 2 or partes[0] in vistos:
                continue
            vistos.add(partes[0])
            c, tipo = git(raiz, "cat-file", "-t", partes[0])
            if tipo.strip() == b"blob":
                _, datos = git(raiz, "cat-file", "blob", partes[0])
                mirar("historia: " + partes[1], datos)
        _, log = git(raiz, "log", "--all", "--format=%H%n%an <%ae>%n%cn <%ce>%n%B%n----")
        mirar("mensajes y autores de commit", log)

    return sorted(set(hallazgos))


def main(argv):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    extra = None
    args = list(argv)
    if "--nombres" in args:
        i = args.index("--nombres")
        extra = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    raiz = Path(args[0]) if args else Path(__file__).resolve().parent
    hallazgos = escanear(raiz, nombres_extra(extra))
    for donde, n, tipo, trozo in hallazgos:
        print("{}:{}: {}: {}".format(donde, n, tipo, trozo))
    print("{} fugas.".format(len(hallazgos)))
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
