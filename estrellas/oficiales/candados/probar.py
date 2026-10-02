#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba todos los candados: cada uno con su ROJO (lo para) y su VERDE (deja pasar lo normal).

Y al final, el sabotaje: repite los rojos contra una guardia vacía. Si alguno sigue saliendo rojo,
la prueba no mide nada (un candado que no puede fallar no es un candado). Uso: python3 probar.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
# Las credenciales de prueba se construyen aquí para que este fichero no lleve ninguna escrita.
TOKEN = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0" * 2
OK = MAL = 0


def ver(nombre, bien, detalle=""):
    global OK, MAL
    OK, MAL = (OK + 1, MAL) if bien else (OK, MAL + 1)
    print(("  ok    " if bien else "  FALLA ") + nombre + ("" if bien else "  -> " + detalle[:200]))


def guardia(payload, cwd, script):
    r = subprocess.run([sys.executable, script], input=json.dumps(payload), capture_output=True,
                       text=True, cwd=cwd, timeout=60)
    return '"deny"' in r.stdout, r.stdout


def bash(c):
    return {"tool_name": "Bash", "tool_input": {"command": c}}


def parche(*l):
    return {"tool_name": "apply_patch", "tool_input": {"command": "\n".join(["*** Begin Patch", *l, "*** End Patch"])}}


ROJOS = [
    ("--no-verify", bash("git commit --no-verify -m x")),
    ("push forzado (al final)", bash("git push origin main --force")),
    ("push forzado (-f)", bash("git push -f origin main")),
    ("push forzado (+refspec)", bash("git push origin +main")),
    ("borrar main en el remoto", bash("git push origin --delete main")),
    ("reset --hard", bash("git reset --hard HEAD~3")),
    ("git clean -fd", bash("git clean -fd")),
    ("rm -rf", bash("rm -rf docs")),
    ("el agente usa el escape", bash("CANDADOS_A_PROPOSITO=1 git push")),
    ("token en un comando", bash("echo " + TOKEN + " > clave.txt")),
    ("'>' sobre un fichero que solo crece", bash("echo hola > docs/bitacora.md")),
    ("Claude: token en un fichero", {"tool_name": "Write", "tool_input": {"file_path": "notas.md", "content": "k=" + TOKEN}}),
    ("Claude: reescribir entero lo que solo crece", {"tool_name": "Write", "tool_input": {"file_path": "docs/bitacora.md", "content": "nuevo"}}),
    ("Claude: quitar líneas de lo que solo crece", {"tool_name": "Edit", "tool_input": {"file_path": "docs/bitacora.md", "old_string": "a\nb", "new_string": "a"}}),
    ("Codex: token en un parche", parche("*** Add File: notas.md", "+k=" + TOKEN)),
    ("Codex: quitar líneas de lo que solo crece", parche("*** Update File: docs/bitacora.md", "@@", "-a", "+b")),
    ("Codex: borrar lo que solo crece", parche("*** Delete File: docs/decisiones/001.md")),
]
VERDES = [
    ("un comando normal", bash("git status")),
    ("un push normal", bash("git push origin HEAD:main")),
    ("rm de un fichero suelto", bash("rm borrador.md")),
    ("añadir con '>>'", bash("echo hola >> docs/bitacora.md")),
    ("Claude: añadir a lo que solo crece", {"tool_name": "Edit", "tool_input": {"file_path": "docs/bitacora.md", "old_string": "a", "new_string": "a\nb"}}),
    ("Codex: añadir a lo que solo crece", parche("*** Update File: docs/bitacora.md", "@@", "+una línea nueva")),
    ("Codex: un fichero nuevo normal", parche("*** Add File: notas.md", "+hola")),
    ("entrada rota: falla abierta", None),
]


def repo_de_prueba(t):
    w = os.path.join(t, "w")
    shutil.copytree(AQUI, w, ignore=shutil.ignore_patterns(".git", "__pycache__", "mesa.md"))
    os.makedirs(os.path.join(w, "docs", "decisiones"), exist_ok=True)
    with open(os.path.join(w, "docs", "bitacora.md"), "w", encoding="utf-8") as f:
        f.write("# bitácora\n- a\n- b\n")
    with open(os.path.join(w, "docs", "decisiones", "001.md"), "w", encoding="utf-8") as f:
        f.write("# decisión 1\n")
    env = dict(os.environ, GIT_AUTHOR_NAME="p", GIT_AUTHOR_EMAIL="p@example.com",
               GIT_COMMITTER_NAME="p", GIT_COMMITTER_EMAIL="p@example.com")
    for c in (["git", "init", "-q", "-b", "main"], ["git", "add", "-A"], ["git", "commit", "-qm", "base"]):
        subprocess.run(c, cwd=w, env=env, capture_output=True)
    subprocess.run([sys.executable, "instalar.py"], cwd=w, capture_output=True)
    return w, env


def rojo_git(r):
    """Un rojo de git cuenta solo si lo para EL CANDADO, no un fallo cualquiera de git."""
    return r.returncode != 0 and "CANDADO" in r.stderr


def main():
    t = tempfile.mkdtemp(prefix="candados-")
    try:
        w, env = repo_de_prueba(t)
        script = os.path.join(w, "guardia.py")
        print("guardia (Claude Code y Codex):")
        for n, p in ROJOS:
            nego, out = guardia(p, w, script)
            ver("ROJO: " + n, nego, out)
        for n, p in VERDES:
            if p is None:
                r = subprocess.run([sys.executable, script], input="no es json", capture_output=True, text=True, cwd=w)
                ver(n, '"deny"' not in r.stdout and r.returncode == 0, r.stderr)
                continue
            nego, out = guardia(p, w, script)
            ver(n, not nego, out)

        print("git (valen para cualquier agente y para la persona):")
        def git(*a, extra=None):
            return subprocess.run(["git", *a], cwd=w, env=dict(env, **(extra or {})), capture_output=True, text=True)
        with open(os.path.join(w, "notas.md"), "w") as f:
            f.write("k=" + TOKEN + "\n")
        git("add", "notas.md")
        ver("ROJO: commit con un token", rojo_git(git("commit", "-qm", "x")))
        git("reset", "-q", "notas.md"); os.remove(os.path.join(w, "notas.md"))
        with open(os.path.join(w, "docs", "bitacora.md"), "w") as f:
            f.write("# bitácora\n- a\n")
        git("add", "-A")
        ver("ROJO: commit que quita una línea de lo que solo crece", rojo_git(git("commit", "-qm", "x")))
        ver("y la persona puede, a propósito", git("commit", "-qm", "x", extra={"CANDADOS_A_PROPOSITO": "1"}).returncode == 0)
        with open(os.path.join(w, "docs", "bitacora.md"), "a") as f:
            f.write("- c\n")
        git("add", "-A")
        ver("un commit que añade pasa", git("commit", "-qm", "añade").returncode == 0)
        origen = os.path.join(t, "origen.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origen], capture_output=True)
        git("remote", "add", "origin", origen)
        ver("un push normal pasa", git("push", "-q", "origin", "main").returncode == 0)
        git("reset", "-q", "--hard", "HEAD~1")
        with open(os.path.join(w, "otra.md"), "w") as f:
            f.write("historia reescrita\n")
        git("add", "-A"); git("commit", "-qm", "reescrita")
        ver("ROJO: push --force que pisa main", rojo_git(git("push", "-q", "--force", "origin", "main")))
        ver("ROJO: borrar main en el remoto", rojo_git(git("push", "-q", "origin", "--delete", "main")))

        print("sabotaje (con la guardia vacía, ningún rojo puede seguir rojo):")
        vacia = os.path.join(t, "vacia.py")
        with open(vacia, "w") as f:
            f.write("import sys\nsys.stdin.read()\n")
        siguen = [n for n, p in ROJOS if guardia(p, w, vacia)[0]]
        ver("los %d rojos dejan de cazar sin la guardia" % len(ROJOS), not siguen, ", ".join(siguen))
    finally:
        shutil.rmtree(t, ignore_errors=True)
    print("\n%d en verde, %d en rojo." % (OK, MAL))
    sys.exit(1 if MAL else 0)


if __name__ == "__main__":
    main()
