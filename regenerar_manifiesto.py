#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rehace base/MANIFIESTO.json: la versión de la base y la huella de cada fichero.

Uso:
  python3 regenerar_manifiesto.py                  mantiene la versión que ya tenía
  python3 regenerar_manifiesto.py --version 0.2    con versión nueva
  python3 regenerar_manifiesto.py --plantilla 0.2  con versión nueva de la plantilla
  python3 regenerar_manifiesto.py --comprobar      no escribe; falla si el manifiesto no está al día

Antes de calcular, copia void.py a base/herramientas/void.py: así cada vault lleva el mismo
cliente que este repo.

También escribe la huella de void.py en la página que lee el agente para conectar un vault
(vaultvoid.app/entrar: web/entrar.md y web/entrar.html, que se escriben a mano salvo la huella) y
copia entrar.md a entrar.txt. Con --comprobar, falla si la huella de la página no cuadra con void.py:
el agente compara lo que baja de GitHub con esa huella, y una página desfasada lo pararía.

Y rehace plantilla/MANIFIESTO.json, la huella de cada fichero de la plantilla con la que empieza
un vault nuevo, y pone la huella de ese manifiesto y la de void.py en la página que lo guía
(vaultvoid.app/empezar: web/empezar.md y .html a mano salvo las huellas; empezar.txt es copia
de empezar.md). Antes pasa el escáner de fugas por la plantilla, con los
nombres de .fugas-nombres y las palabras de .fugas-plantilla (las dos fuera de git): si sale
algo, no escribe nada. La plantilla es pública y la copia todo el que empieza un vault.
"""
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import void  # noqa: E402
import fugas  # noqa: E402

BASE = AQUI / "base"
CLIENTE_EN_BASE = ("herramientas", "void.py")
IGNORAR_DIRS = {"__pycache__"}

PLANTILLA = AQUI / "plantilla"
# Palabras de los vaults de los que salió la plantilla (ciudades, oficios, proyectos, herramientas
# de cada uno), como sha256 y fuera de git, igual que .fugas-nombres: escritas aquí, se publicarían.
PALABRAS_PLANTILLA = AQUI / ".fugas-plantilla"

WEB = AQUI / "web"
ENTRAR = ("entrar.md", "entrar.html")   # a mano, salvo la huella, que la pone este script
ENTRAR_TXT = ("entrar.md", "entrar.txt")   # entrar.txt es una copia de entrar.md
RE_HUELLA = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")

EMPEZAR = ("empezar.md", "empezar.html")   # vaultvoid.app/empezar: a mano, salvo las dos huellas
EMPEZAR_TXT = ("empezar.md", "empezar.txt")
# En empezar, la huella de la plantilla es la que va detrás de «--huella»; las demás son la de void.py.
RE_HUELLA_PLANTILLA = re.compile(r"(?<=--huella )[0-9a-f]{64}(?![0-9a-f])")


def huella_cliente(raiz=AQUI):
    """La huella de void.py tal como lo sirve GitHub (con \n; void.huella no cuenta los \r\n)."""
    return void.huella((Path(raiz) / "void.py").read_bytes())


def entrar_con_huella(web, h):
    """{nombre: bytes} de la página de entrar con la huella h puesta. No escribe nada."""
    salida = {}
    for nombre in ENTRAR:
        texto = (Path(web) / nombre).read_text(encoding="utf-8")
        salida[nombre] = RE_HUELLA.sub(h, texto).encode("utf-8")
    salida[ENTRAR_TXT[1]] = salida[ENTRAR_TXT[0]]
    return salida


def huella_plantilla(plantilla=None):
    """La huella de plantilla/MANIFIESTO.json, la que comprueba «void.py empezar --huella»."""
    return void.huella((Path(plantilla or PLANTILLA) / void.MANIFIESTO).read_bytes())


def empezar_con_huellas(web, h_void, h_plantilla):
    """{nombre: bytes} de la página de empezar con las dos huellas puestas. No escribe nada."""
    salida = {}
    for nombre in EMPEZAR:
        texto = (Path(web) / nombre).read_text(encoding="utf-8")
        texto = RE_HUELLA_PLANTILLA.sub("\0", texto)
        texto = RE_HUELLA.sub(h_void, texto).replace("\0", h_plantilla)
        salida[nombre] = texto.encode("utf-8")
    salida[EMPEZAR_TXT[1]] = salida[EMPEZAR_TXT[0]]
    return salida


def problemas_empezar(web, h_void, h_plantilla):
    """Lo que no cuadra entre la página de empezar, void.py y la plantilla. Vacía si está al día."""
    problemas = []
    for nombre in EMPEZAR + EMPEZAR_TXT[1:]:
        p = Path(web) / nombre
        if not p.is_file():
            problemas.append("falta web/{}".format(nombre))
            continue
        texto = p.read_text(encoding="utf-8")
        de_plantilla = RE_HUELLA_PLANTILLA.findall(texto)
        de_void = RE_HUELLA.findall(RE_HUELLA_PLANTILLA.sub("", texto))
        if len(de_void) < 2:
            problemas.append("web/{} no publica la huella de void.py (dos veces: a la vista y en la orden)"
                             .format(nombre))
        elif any(x != h_void for x in de_void):
            problemas.append("la huella de void.py en web/{} no cuadra con void.py".format(nombre))
        if not de_plantilla:
            problemas.append("web/{} no publica la huella de la plantilla (en la orden «empezar --huella»)"
                             .format(nombre))
        elif any(x != h_plantilla for x in de_plantilla):
            problemas.append("la huella de la plantilla en web/{} no cuadra con plantilla/MANIFIESTO.json"
                             .format(nombre))
    md, txt = (Path(web) / n for n in EMPEZAR_TXT)
    if md.is_file() and txt.is_file() and void.huella(md.read_bytes()) != void.huella(txt.read_bytes()):
        problemas.append("web/empezar.txt no es una copia de web/empezar.md")
    return problemas


def problemas_entrar(web, h):
    """Lo que no cuadra entre la página de entrar y void.py. Vacía si está al día."""
    problemas = []
    for nombre in ENTRAR + ENTRAR_TXT[1:]:
        p = Path(web) / nombre
        if not p.is_file():
            problemas.append("falta web/{}".format(nombre))
            continue
        vistas = RE_HUELLA.findall(p.read_text(encoding="utf-8"))
        if len(vistas) < 2:
            problemas.append("web/{} no publica la huella de void.py (dos veces: a la vista y en la orden)"
                             .format(nombre))
        elif any(x != h for x in vistas):
            problemas.append("la huella de void.py en web/{} no cuadra con void.py".format(nombre))
    md, txt = (Path(web) / n for n in ENTRAR_TXT)
    if md.is_file() and txt.is_file() and void.huella(md.read_bytes()) != void.huella(txt.read_bytes()):
        problemas.append("web/entrar.txt no es una copia de web/entrar.md")
    return problemas


def palabras_plantilla(fichero=None):
    """Las huellas de .fugas-plantilla: una por línea. Vacío si no está (en GitHub Actions)."""
    f = Path(fichero or PALABRAS_PLANTILLA)
    if not f.is_file():
        return set()
    return {l.split()[0] for l in f.read_text(encoding="utf-8").splitlines() if l.split()}


def problemas_plantilla(carpeta=None, nombres=None):
    """Lo que no puede salir en la plantilla: secretos, correos, teléfonos y nombres de personas
    (fugas.py), y las palabras de .fugas-plantilla. Vacía si está limpia. Se escanea una copia sin
    git: así mira solo la plantilla, no la historia del repo entero."""
    carpeta = Path(carpeta or PLANTILLA)
    if not carpeta.is_dir():
        return ["falta la carpeta plantilla/"]
    nombres = palabras_plantilla() if nombres is None else set(nombres)
    tmp = Path(tempfile.mkdtemp(prefix="void-plantilla-"))
    try:
        copia = tmp / "plantilla"
        shutil.copytree(str(carpeta), str(copia), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        hallazgos = fugas.escanear(copia, nombres)
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    return ["la plantilla trae {} en {}:{} ({})".format(tipo, donde, n, trozo)
            for donde, n, tipo, trozo in hallazgos]


def ficheros_de(base):
    salida = {}
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        if not p.is_file() or any(parte in IGNORAR_DIRS for parte in rel.parts):
            continue
        ruta = rel.as_posix()
        if ruta == void.MANIFIESTO or ruta.endswith((".pyc", void.SUFIJO_NUEVA)):
            continue
        salida[ruta] = void.huella(p.read_bytes())
    return salida


def contenido(base, version):
    datos = {"version": version, "ficheros": ficheros_de(base)}
    return (json.dumps(datos, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def version_actual(base):
    p = base / void.MANIFIESTO
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("version")


def main(argv):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    comprobar = "--comprobar" in argv
    version = None
    if "--version" in argv:
        i = argv.index("--version")
        if i + 1 >= len(argv):
            print("Falta la versión: --version 0.2", file=sys.stderr)
            return 2
        version = argv[i + 1]
    version = version or version_actual(BASE)
    if not version:
        print("No hay versión: pásala con --version 0.1", file=sys.stderr)
        return 2

    version_plantilla = None
    if "--plantilla" in argv:
        i = argv.index("--plantilla")
        if i + 1 >= len(argv):
            print("Falta la versión de la plantilla: --plantilla 0.2", file=sys.stderr)
            return 2
        version_plantilla = argv[i + 1]
    version_plantilla = version_plantilla or version_actual(PLANTILLA) or "0.1"

    sucia = problemas_plantilla()
    if sucia:
        for pr in sucia:
            print(pr, file=sys.stderr)
        print("La plantilla es pública: sácalo de plantilla/ y vuelve a probar. No he escrito nada.",
              file=sys.stderr)
        return 1

    cliente = BASE.joinpath(*CLIENTE_EN_BASE)
    if comprobar:
        # Se compara con huella: en un clon de Windows, git pone \r\n y no es un cambio.
        problemas = []
        if not cliente.is_file() or void.huella(cliente.read_bytes()) != void.huella((AQUI / "void.py").read_bytes()):
            problemas.append("base/herramientas/void.py no es igual que void.py")
        p = BASE / void.MANIFIESTO
        if not p.is_file() or void.huella(p.read_bytes()) != void.huella(contenido(BASE, version)):
            problemas.append("base/MANIFIESTO.json no está al día con los ficheros de base/")
        p = PLANTILLA / void.MANIFIESTO
        if not p.is_file() or void.huella(p.read_bytes()) != void.huella(contenido(PLANTILLA, version_plantilla)):
            problemas.append("plantilla/MANIFIESTO.json no está al día con los ficheros de plantilla/")
        problemas += problemas_entrar(WEB, huella_cliente())
        if p.is_file():
            problemas += problemas_empezar(WEB, huella_cliente(), huella_plantilla())
        for pr in problemas:
            print(pr + ": corre python3 regenerar_manifiesto.py", file=sys.stderr)
        if not problemas:
            print("Manifiesto al día (base {}, {} ficheros; plantilla {}, {} ficheros).".format(
                version, len(ficheros_de(BASE)), version_plantilla, len(ficheros_de(PLANTILLA))))
        return 1 if problemas else 0

    cliente.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(AQUI / "void.py"), str(cliente))
    (BASE / void.MANIFIESTO).write_bytes(contenido(BASE, version))
    (PLANTILLA / void.MANIFIESTO).write_bytes(contenido(PLANTILLA, version_plantilla))
    h = huella_cliente()
    for nombre, datos in entrar_con_huella(WEB, h).items():
        (WEB / nombre).write_bytes(datos)
    hp = huella_plantilla()
    for nombre, datos in empezar_con_huellas(WEB, h, hp).items():
        (WEB / nombre).write_bytes(datos)
    print("Manifiesto rehecho: base {}, {} ficheros.".format(version, len(ficheros_de(BASE))))
    print("Huella de void.py en web/entrar: {}".format(h))
    print("Manifiesto de la plantilla rehecho: plantilla {}, {} ficheros.".format(
        version_plantilla, len(ficheros_de(PLANTILLA))))
    print("Huellas en web/empezar: void.py {} y plantilla {}".format(h, hp))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
