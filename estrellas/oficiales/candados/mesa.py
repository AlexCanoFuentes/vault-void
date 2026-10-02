#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La mesa: encargos entre agentes, por git, bajo las órdenes de la persona.

  python3 mesa.py                                    -> lo abierto
  python3 mesa.py recoge codex                       -> lo que espera a codex
  python3 mesa.py encarga codex "<qué>" --de claude --orden "<palabras de la persona>"
  python3 mesa.py hecho M-03 "<resultado o dónde está>"

Un encargo sin orden de la persona es una PROPUESTA: el agente que lo recibe no lo ejecuta, se lo
enseña a la persona. Así «bajo mis órdenes» vive en el código y no en la buena voluntad del agente.
"""
import os
import re
import sys
from datetime import date

MESA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mesa.md")
CABECERA = ("# La mesa · encargos entre agentes\n\n"
            "> La lleva `mesa.py`; no se edita a mano. Un encargo sin orden es una propuesta y no se ejecuta.\n\n")
LINEA = re.compile(r"^- \[(M-\d+)\] (\S+) → (\S+) · (.*) · orden: (.*) · estado: (\S+) · (\S+)(?: · (.*))?$")


def leer():
    if not os.path.exists(MESA):
        return []
    return [l.rstrip("\n") for l in open(MESA, encoding="utf-8") if l.startswith("- [M-")]


def escribir(lineas):
    with open(MESA, "w", encoding="utf-8") as f:
        f.write(CABECERA + "\n".join(lineas) + ("\n" if lineas else ""))


def pinta(lineas, para=None):
    vivos = 0
    for l in lineas:
        m = LINEA.match(l)
        if not m or m.group(6) == "hecho" or (para and m.group(3) != para):
            continue
        vivos += 1
        marca = "PROPUESTA: no se ejecuta, enséñasela a la persona" if m.group(6) == "propuesta" else "orden: " + m.group(5)
        print("  %s  %s → %s  %s\n        %s" % (m.group(1), m.group(2), m.group(3), m.group(4), marca))
    if not vivos:
        print("  la mesa está vacía%s." % (" para " + para if para else ""))


def main():
    a, lineas = sys.argv[1:], leer()
    if not a:
        return pinta(lineas)
    if a[0] == "recoge" and len(a) == 2:
        return pinta(lineas, a[1].lower())
    if a[0] == "encarga" and len(a) >= 3:
        para, que = a[1].lower(), a[2]
        de = a[a.index("--de") + 1].lower() if "--de" in a else os.environ.get("AGENTE", "?")
        orden = a[a.index("--orden") + 1].strip() if "--orden" in a else ""
        if "·" in que or "·" in orden:
            sys.exit("sin «·» dentro del encargo ni de la orden: es el separador de la línea.")
        n = max([int(LINEA.match(l).group(1)[2:]) for l in lineas if LINEA.match(l)] or [0]) + 1
        estado = "abierto" if orden else "propuesta"
        lineas.append("- [M-%02d] %s → %s · %s · orden: %s · estado: %s · %s"
                      % (n, de, para, que, orden or "(ninguna)", estado, date.today().isoformat()))
        escribir(lineas)
        return print("en la mesa: M-%02d para %s (%s)" % (n, para, estado))
    if a[0] == "hecho" and len(a) == 3:
        for i, l in enumerate(lineas):
            m = LINEA.match(l)
            if m and m.group(1) == a[1].upper():
                lineas[i] = re.sub(r" · estado: \S+ · (\S+)(?: · .*)?$",
                                   " · estado: hecho · %s · %s" % (date.today().isoformat(), a[2]), l)
                escribir(lineas)
                return print("hecho: %s" % m.group(1))
        sys.exit("no hay %s en la mesa." % a[1])
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
