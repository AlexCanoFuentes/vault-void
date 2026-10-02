#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Activa los candados de git en este clon. Hay que ejecutarlo en CADA clon (también en el de cada
agente): core.hooksPath es configuración local y git no la copia al clonar.

    python3 instalar.py        (en Windows: py instalar.py)
"""
import os
import stat
import subprocess
import sys

raiz = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
if not raiz:
    sys.exit("Esto no es un repositorio git. Ejecútalo desde dentro de tu repo.")
for f in ("pre-commit", "pre-push"):
    p = os.path.join(raiz, ".githooks", f)
    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
subprocess.run(["git", "-C", raiz, "config", "core.hooksPath", ".githooks"], check=True)
print("Candados de git activados en este clon (core.hooksPath = .githooks).")
print("Comprueba que funcionan: python3 probar.py")
