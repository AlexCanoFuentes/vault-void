#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Junta la copia de Void con el vault del ordenador, por turnos y sin perder nada de ningún lado (fase 1, parte 1).

Uso:  python3 turno.py <vault del ordenador> <carpeta con la copia de Void>

La copia de Void entra como una rama de lectura (refs/void/main), nunca como main. Si solo escribió Void, el ordenador
avanza; si solo escribió el ordenador, no cambia nada y lo dice; si escribieron los dos, se juntan en un commit de unión
(los ficheros que solo crecen, marcados merge=union en .gitattributes, se unen solos). Si algo choca, se deshace la unión,
todo queda como estaba y dice qué fichero choca. Nunca se reescribe la historia ni se fuerza nada. Solo viaja lo que git
sigue: lo ignorado (.void/, .agente/, credenciales) no se toca.
"""
import subprocess
import sys
from pathlib import Path

REF = "refs/void/main"


def _git(carpeta, *args):
    r = subprocess.run(["git", "-C", str(carpeta)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return r.returncode, r.stdout.decode("utf-8", "replace").strip()


def _r(resultado, mensaje, ficheros=None):
    return {"resultado": resultado, "mensaje": mensaje, "ficheros": ficheros or []}


def juntar(pc, copia):
    pc, copia = Path(pc), Path(copia)
    if _git(pc, "rev-parse", "--git-dir")[0] != 0:
        return _r("sin_copia", "Esta carpeta no es un vault con historia (git).")
    if _git(copia, "rev-parse", "--git-dir")[0] != 0:
        return _r("sin_copia", "La copia de Void no trae su historia: descárgala completa desde Mi espacio.")
    if _git(pc, "status", "--porcelain", "--untracked-files=no")[1]:
        return _r("sin_guardar", "Tu ordenador tiene cambios sin guardar. Guárdalos primero y vuelve a intentarlo: "
                                 "así no se mezcla nada a medias.")
    if _git(pc, "fetch", "--quiet", str(copia), "+HEAD:" + REF)[0] != 0:
        return _r("sin_copia", "No he podido leer la historia de la copia de Void.")
    if _git(pc, "merge-base", "HEAD", REF)[0] != 0:
        return _r("sin_comun", "La copia de Void y tu ordenador no tienen ninguna historia en común: no son el mismo "
                               "vault, o uno se rehízo desde cero. No junto nada; míralo con calma.")
    codigo, cuenta = _git(pc, "rev-list", "--left-right", "--count", "HEAD..." + REF)
    pc_delante, void_delante = (int(x) for x in cuenta.split()) if codigo == 0 else (0, 0)
    if not pc_delante and not void_delante:
        return _r("al_dia", "Al día: tu ordenador y Void tienen lo mismo.")
    if not void_delante:
        return _r("void_detras", "Tu ordenador tiene {} cambio(s) que Void no tiene. Súbelo en tu turno, con tu espacio "
                                 "dormido.".format(pc_delante))
    if not pc_delante:
        if _git(pc, "merge", "--ff-only", "--quiet", REF)[0] != 0:
            return _r("choque", "No he podido traer lo de Void a tu ordenador sin tocar nada tuyo.")
        return _r("avanza", "Tu ordenador ya tiene lo que escribiste en Void ({} cambio(s)).".format(void_delante))
    codigo, _ = _git(pc, "merge", "--no-ff", "--no-edit", "-m",
                     "void: junta lo de Void ({} cambio(s)) con lo del ordenador".format(void_delante), REF)
    if codigo != 0:
        chocan = [f for f in _git(pc, "diff", "--name-only", "--diff-filter=U")[1].splitlines() if f]
        _git(pc, "merge", "--abort")
        return _r("choque", "Tu ordenador y Void cambiaron lo mismo en: {}. No he tocado nada. Elige qué versión se queda "
                            "de cada uno y vuelve a intentarlo.".format(", ".join(chocan) or "algún fichero"), chocan)
    return _r("unido", "Juntado: {} cambio(s) de Void y {} de tu ordenador, en un commit de unión.".format(
        void_delante, pc_delante))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    r = juntar(sys.argv[1], sys.argv[2])
    print(r["mensaje"])
    sys.exit(0 if r["resultado"] in ("al_dia", "avanza", "unido", "void_detras") else 1)
