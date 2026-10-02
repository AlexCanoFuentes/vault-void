#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La guardia: un solo hook PreToolUse para Claude Code y para Codex.

Los dos mandan la llamada con la misma forma (tool_name, tool_input) y aceptan la misma respuesta
para denegarla, asi que no hacen falta dos candados que diverjan. Lo que cambia:
  - Bash: los dos mandan tool_input.command.
  - Ficheros: Claude manda Write/Edit con file_path; Codex manda apply_patch con el parche entero
    en tool_input.command (*** Add File / *** Update File / *** Delete File).

Deniega: comandos prohibidos (candados.py), credenciales en comandos, ficheros y parches, y quitar
lineas o sobrescribir los ficheros que solo crecen (candados.json).
FALLA ABIERTA: si la guardia se rompe, deja pasar. Un candado que tumba el trabajo por un fallo
suyo se desactiva en un dia, y entonces no protege nada.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import candados  # noqa: E402

CABEZA = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+)$")
TRUNCA = re.compile(r"(?<![>&0-9])>(?!>)\s*([^\s;&|]+)")


def niega(motivo):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "CANDADO: " + motivo + ". Si de verdad hace falta, lo hace la persona, no el agente.",
    }}, ensure_ascii=False))
    sys.exit(0)


def rel(ruta, base):
    if not ruta:
        return ""
    return os.path.relpath(ruta if os.path.isabs(ruta) else os.path.join(base, ruta), base).replace("\\", "/")


def parche(texto):
    """[(accion, ruta, quitadas, anadidas)] por fichero de un parche de Codex."""
    partes, actual = [], None
    for l in texto.splitlines():
        m = CABEZA.match(l)
        if m:
            actual = [m.group(1), m.group(2).strip(), [], []]
            partes.append(actual)
        elif l.startswith("*** "):
            continue
        elif actual is not None and l.startswith("-"):
            actual[2].append(l[1:])
        elif actual is not None and l.startswith("+"):
            actual[3].append(l[1:])
    return partes


def main():
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        return
    nombre = datos.get("tool_name", "")
    ti = datos.get("tool_input") or {}
    if not isinstance(ti, dict):
        return
    base = candados.raiz()
    cfg = candados.config()

    if nombre == "Bash":
        cmd = ti.get("command", "") or ""
        motivo = candados.busca_prohibido(cmd)
        if motivo:
            niega(motivo)
        s = candados.busca_secreto(cmd)
        if s:
            niega("el comando lleva una credencial (%s)" % s)
        for destino in TRUNCA.findall(cmd):
            if candados.es_solo_crece(rel(destino.strip("'\""), base), cfg):
                niega("'%s' solo crece y '>' lo sobrescribe entero; se anade con '>>'" % destino)
        return

    if nombre == "apply_patch":
        for accion, ruta, quitadas, anadidas in parche(ti.get("command", "") or ""):
            r = rel(ruta, base)
            s = candados.busca_secreto("\n".join(anadidas))
            if s:
                niega("el parche mete una credencial en %s (%s)" % (r, s))
            if candados.es_solo_crece(r, cfg) and (accion == "Delete" or quitadas):
                niega("%s solo crece y este parche le quita lineas" % r)
        return

    if nombre in ("Write", "Edit", "MultiEdit"):
        r = rel(ti.get("file_path", ""), base)
        nuevo = ti.get("content") or ti.get("new_string") or ""
        for e in ti.get("edits") or []:
            nuevo += "\n" + (e.get("new_string") or "")
        s = candados.busca_secreto(nuevo)
        if s:
            niega("esto mete una credencial en %s (%s)" % (r, s))
        if candados.es_solo_crece(r, cfg):
            if nombre == "Write" and os.path.exists(os.path.join(base, r)):
                niega("%s solo crece y escribirlo entero lo reemplaza; se anade al final" % r)
            viejo = ti.get("old_string") or ""
            if viejo and len((ti.get("new_string") or "").splitlines()) < len(viejo.splitlines()):
                niega("%s solo crece y esta edicion le quita lineas" % r)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass  # falla abierta
