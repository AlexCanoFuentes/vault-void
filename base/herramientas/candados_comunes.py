#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Los candados que comparten todos los vaults: Codex encerrado y Claude leyendo AGENTS.md.

Viene de la base de Void: las cuatro funciones están sacadas tal cual de herramientas/revisar.py
de los vaults. No se cambia aquí; se cambia en la base y llega con «void.py actualizar».

Uso:
  python3 herramientas/candados_comunes.py    dice si algún candado común se ha aflojado
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def leer_codex(raiz):
    """.codex/config.toml como {sección: {clave: valor}}; {} si no existe."""
    try:
        texto = (Path(raiz) / ".codex" / "config.toml").read_text(encoding="utf-8")
    except OSError:
        return {}
    d, sec = {"": {}}, ""
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        if linea.startswith("[") and linea.endswith("]"):
            sec = linea.strip("[]").strip()
            d.setdefault(sec, {})
            continue
        if "=" not in linea:
            continue
        clave, valor = (x.strip() for x in linea.split("=", 1))
        valor = {"true": True, "false": False}.get(valor, valor.strip("\"'"))
        donde = sec
        if not sec and "." in clave:
            donde, clave = clave.split(".", 1)
            d.setdefault(donde, {})
        d[donde][clave] = valor
    return d


def candados_codex(raiz):
    c = leer_codex(raiz)
    if not c:
        return [".codex/config.toml no está: Codex trabajaría con lo que tenga puesto en su equipo"]
    faltan, arriba = [], c.get("", {})
    if arriba.get("sandbox_mode") != "workspace-write":
        faltan.append("config.toml de Codex ya no le deja escribir solo dentro de la carpeta (sandbox_mode)")
    if arriba.get("approval_policy") != "on-request":
        faltan.append("config.toml de Codex ya no le hace pedir permiso para salir de la carpeta (approval_policy)")
    if c.get("sandbox_workspace_write", {}).get("network_access") is not False:
        faltan.append("config.toml de Codex ya no le cierra internet (network_access)")
    if "default_permissions" in arriba or "permissions" in c:
        faltan.append("config.toml de Codex usa un perfil de permisos que pasa por encima de todo lo anterior")
    return faltan


def leer_texto(raiz, nombre):
    try:
        return (Path(raiz) / nombre).read_text(encoding="utf-8")
    except OSError:
        return ""


def reglas_compartidas(raiz):
    """Las reglas viven en AGENTS.md (lo lee Codex) y CLAUDE.md las importa (lo lee Claude)."""
    faltan = []
    if not leer_texto(raiz, "AGENTS.md").strip():
        faltan.append("AGENTS.md no está o está vacío: el agente trabajaría sin las reglas del vault")
    if not any(l.strip() == "@AGENTS.md" for l in leer_texto(raiz, "CLAUDE.md").splitlines()):
        faltan.append("CLAUDE.md ya no importa AGENTS.md (la línea @AGENTS.md): Claude trabajaría sin las reglas del vault")
    return faltan


def main(argv):
    raiz = Path(argv[0]) if argv else RAIZ
    abiertos = candados_codex(raiz) + reglas_compartidas(raiz)
    for a in abiertos:
        print("ABIERTO: " + a)
    if not abiertos:
        print("OK: Codex sigue encerrado y Claude lee las reglas de AGENTS.md.")
    return 1 if abiertos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
