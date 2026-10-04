#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Candados para agentes: lo que comparten la guardia (Claude Code y Codex) y los candados de git.

Un solo sitio para las reglas, para que las tres capas no diverjan. Solo biblioteca estandar.
La configuracion de cada repo vive en candados.json (ver README).
"""
import json
import os
import re
import subprocess

# Credenciales con forma conocida. No es un escaner completo: es la red que caza lo de siempre.
SECRETOS = [
    (r"\bsk-ant-[A-Za-z0-9_-]{20,}", "clave de Anthropic"),
    (r"\bsk-[A-Za-z0-9_-]{20,}", "clave estilo OpenAI (sk-...)"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}", "token de GitHub"),
    (r"\bgithub_pat_[A-Za-z0-9_]{30,}", "token de GitHub (github_pat_...)"),
    (r"\bsbp_[A-Za-z0-9]{30,}", "token de Supabase (sbp_...)"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "token de Slack"),
    (r"\bAKIA[0-9A-Z]{16}\b", "clave de acceso de AWS"),
    (r"\bAIza[0-9A-Za-z_-]{35}\b", "clave de Google"),
    (r"\b[rs]k_live_[0-9A-Za-z]{20,}", "clave de Stripe en vivo"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "clave privada"),
    (r"(?i)\b(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"][^'\"\s]{16,}['\"]", "asignacion de credencial"),
]
SECRETOS = [(re.compile(p), q) for p, q in SECRETOS]

# Lo que un agente no hace nunca sin que la persona lo ejecute ella misma.
ESCAPE = "CANDADOS_A_PROPOSITO=1"
# Opciones globales de git entre `git` y la orden: -C dir, -c clave=valor, --git-dir=...
G = r"(\s+(-[cC]\s*\S+|--?[A-Za-z][\w-]*(=\S+)?))*"
PROHIBIDOS = [
    (r"(^|[\s;&|(])--no-verify\b", "--no-verify se salta los candados de git"),
    (re.escape(ESCAPE), "el escape de los candados es para la persona, no para el agente"),
    # Las opciones globales (`git -C dir`, `git -c clave=valor`) van entre `git` y la orden: sin
    # contarlas, `git -C . push -f` pasaba. Y `-c core.hooksPath=` apaga los hooks de git para esa
    # orden: era una linea entre el agente y un push forzado. Lo cazo una revision de Codex (3-oct).
    (r"\bgit\b[^;&|\n]*\s-c\s*['\"]?core\.hookspath", "cambiar core.hooksPath apaga los candados de git"),
    (r"GIT_CONFIG_(KEY_\d+|PARAMETERS)\b[^;&|\n]*hookspath", "cambiar core.hooksPath por el entorno apaga los candados de git"),
    (r"\bgit" + G + r"\s+config\b([^;&|\n]*\s--(unset|unset-all|remove-section)\b[^;&|\n]*core\.hookspath"
     r"|[^;&|\n]*core\.hookspath\s+(?!\.githooks\s*($|[;&|]))[^\s-])", "solo vale `git config core.hooksPath .githooks`"),
    (r"\bchmod\b[^;&|\n]*\.githooks", "git ignora un hook que no es ejecutable"),
    (r"\bgit" + G + r"\s+commit\b[^;&|\n]*\s-[a-zA-Z]*n[a-zA-Z]*\b", "`git commit -n` es --no-verify"),
    (r"\bgit" + G + r"\s+push\b[^;&|]*(\s--force\b|\s--force-with-lease\b|\s-f\b|\s-[a-zA-Z]*f[a-zA-Z]*\b|\s\+\S|\s--mirror\b)", "push forzado: borraria trabajo de otro"),
    (r"\bgit" + G + r"\s+push\b[^;&|]*(\s(--delete|-d)\s+\S*\s*(main|master)\b|\s:(refs/heads/)?(main|master)\b)", "borrar la rama principal en el remoto"),
    (r"\bgit" + G + r"\s+reset\s+[^;&|]*--hard\b", "reset --hard borra trabajo sin dejar rastro"),
    (r"\bgit" + G + r"\s+clean\b[^;&|]*\s-[a-zA-Z]*f", "git clean borra ficheros que pueden ser de otro"),
    (r"\bgh\s+api\b[^;&|\n]*git/refs[^;&|\n]*force", "forzar una rama por la API de GitHub no pasa por ningun hook"),
    (r"(^|[\s;&|(])rm\s+(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\b", "borrado recursivo"),
]
PROHIBIDOS = [(re.compile(p, re.I if "hookspath" in p else 0), q) for p, q in PROHIBIDOS]


def raiz():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.stdout.strip() or os.getcwd()


def config():
    """candados.json: {"solo_crecen": ["docs/bitacora.md", "logs/"], "remoto": "github.com/usuario/repo"}"""
    try:
        with open(os.path.join(raiz(), "candados.json"), encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    return {"solo_crecen": c.get("solo_crecen", []), "remoto": c.get("remoto", "")}


def es_solo_crece(ruta, cfg=None):
    """True si la ruta (relativa a la raiz) es un fichero o cae en una carpeta que solo crece."""
    cfg = cfg or config()
    ruta = ruta.replace("\\", "/").lstrip("./")
    for p in cfg["solo_crecen"]:
        p = p.replace("\\", "/").lstrip("./")
        if ruta == p or (p.endswith("/") and ruta.startswith(p)):
            return True
    return False


def busca_secreto(texto):
    for patron, nombre in SECRETOS:
        if patron.search(texto or ""):
            return nombre
    return None


def busca_prohibido(comando):
    for patron, motivo in PROHIBIDOS:
        if patron.search(comando or ""):
            return motivo
    return None
