#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rehace base/MANIFIESTO.json: la versión de la base y la huella de cada fichero.

Uso:
  python3 regenerar_manifiesto.py                  mantiene la versión que ya tenía
  python3 regenerar_manifiesto.py --version 0.2    con versión nueva
  python3 regenerar_manifiesto.py --comprobar      no escribe; falla si el manifiesto no está al día

Antes de calcular, copia void.py a base/herramientas/void.py: así cada vault lleva el mismo
cliente que este repo.

También escribe la huella de void.py en la página que lee el agente para conectar un vault
(vaultvoid.app/entrar: web/entrar.md y web/entrar.html, que se escriben a mano salvo la huella) y
copia entrar.md a entrar.txt. Con --comprobar, falla si la huella de la página no cuadra con void.py:
el agente compara lo que baja de GitHub con esa huella, y una página desfasada lo pararía.
"""
import json
import re
import shutil
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import void  # noqa: E402

BASE = AQUI / "base"
CLIENTE_EN_BASE = ("herramientas", "void.py")
IGNORAR_DIRS = {"__pycache__"}

WEB = AQUI / "web"
ENTRAR = ("entrar.md", "entrar.html")   # a mano, salvo la huella, que la pone este script
ENTRAR_TXT = ("entrar.md", "entrar.txt")   # entrar.txt es una copia de entrar.md
RE_HUELLA = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")


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

    cliente = BASE.joinpath(*CLIENTE_EN_BASE)
    if comprobar:
        # Se compara con huella: en un clon de Windows, git pone \r\n y no es un cambio.
        problemas = []
        if not cliente.is_file() or void.huella(cliente.read_bytes()) != void.huella((AQUI / "void.py").read_bytes()):
            problemas.append("base/herramientas/void.py no es igual que void.py")
        p = BASE / void.MANIFIESTO
        if not p.is_file() or void.huella(p.read_bytes()) != void.huella(contenido(BASE, version)):
            problemas.append("base/MANIFIESTO.json no está al día con los ficheros de base/")
        problemas += problemas_entrar(WEB, huella_cliente())
        for pr in problemas:
            print(pr + ": corre python3 regenerar_manifiesto.py", file=sys.stderr)
        if not problemas:
            print("Manifiesto al día (base {}, {} ficheros).".format(version, len(ficheros_de(BASE))))
        return 1 if problemas else 0

    cliente.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(AQUI / "void.py"), str(cliente))
    (BASE / void.MANIFIESTO).write_bytes(contenido(BASE, version))
    h = huella_cliente()
    for nombre, datos in entrar_con_huella(WEB, h).items():
        (WEB / nombre).write_bytes(datos)
    print("Manifiesto rehecho: base {}, {} ficheros.".format(version, len(ficheros_de(BASE))))
    print("Huella de void.py en web/entrar: {}".format(h))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
