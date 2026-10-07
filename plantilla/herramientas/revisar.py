#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Busca en el vault lo que no tiene que entrar.

Uso:
  python3 herramientas/revisar.py            revisa todo el vault
  python3 herramientas/revisar.py <archivo>  revisa solo el texto de ese archivo

Qué mira:
  1. Claves de API, contraseñas o tokens escritos, y claves privadas.
  2. Correos, teléfonos y números con forma de DNI: los de otras personas no van aquí tal cual.
  3. Que git no guarde copias de documentos, correos, fotos ni vídeos (se consultan, no se copian),
     y que el .gitignore los siga bloqueando, también en mayúsculas (CONTRATO.PDF).
  4. Que el agente, Claude o Codex, siga encerrado en esta carpeta, pregunte antes de subir
     nada y lea las reglas del vault:
     .claude/settings.json (también la app de escritorio de Claude en Windows, que no admite
     otra configuración y por eso lleva los mismos candados que la de Windows),
     .claude/encerrado.json (Mac, Linux, WSL2), .claude/encerrado-windows.json (Claude en la
     terminal de Windows), .codex/config.toml, y AGENTS.md importado desde CLAUDE.md.
  5. Que el README y los proyectos no digan de ti lo que no dijiste: si una línea cita una de tus
     siete respuestas (criterio/apuntes.md) y está sin contestar, dice [sin contestar]; si está
     contestada, lleva tus palabras entre «» y están tal cual en tu respuesta.

Qué NO puede ver: un nombre de persona no tiene forma reconocible. Eso se cuida al escribir.

Si marca una línea que está bien (tu propio correo, por ejemplo), añade al final de esa línea
el comentario  <!-- revisar:ok -->  y deja de marcarla.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXTENSIONES = {".md", ".txt", ".csv", ".json"}
PERMISO = "revisar:ok"
LIMITE_BYTES = 1024 * 1024

COPIAS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    ".pages", ".numbers", ".key", ".eml", ".msg", ".mbox",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".psd", ".raw",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v",
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".zip", ".rar", ".7z",
}
MUESTRAS = [
    "contrato.pdf", "CONTRATO.PDF", "presupuesto.docx", "cuentas.xlsx", "charla.pptx",
    "correo.eml", "Mensaje.MSG", "foto.jpg", "IMG_1234.HEIC", "captura.png",
    "video.mp4", "audio.opus", "nota.m4a", "drive.zip",
    "capas.psd", "CLIP.MP4", "escena.webm",
]

CLAVE_API = re.compile(
    r"\b(sk[-_][A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,})")
CLAVE_PRIVADA = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
ESCRITA = re.compile(
    r"(?i)\b(password|passwd|contraseña|contrasena|token|secret|api[ _-]?key|clave)\s*[:=]\s*\S{6,}")
CORREO = re.compile(r"(?<![\w.+-])(?!git@)[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# Enlaces, fechas y horas se quitan antes de buscar números largos: el número de un artículo
# dentro de una URL o 2026-09-30 no son un teléfono.
ENLACE = re.compile(r"https?://\S+")
FECHA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b|\b\d{1,2}/\d{1,2}(/\d{2,4})?\b")
NUMERO_LARGO = re.compile(r"(?<![\w,])\+?\d[\d .()-]{6,}\d[A-Za-z]?(?![\w,])")
DINERO = re.compile(r"(?i)^\s*(€|eur|euros|usd|\$)|(€|eur|euros|\$)\s*$")

PATRONES = [
    ("clave de API", CLAVE_API),
    ("clave privada", CLAVE_PRIVADA),
    ("contraseña, token o clave escrita", ESCRITA),
    ("correo", CORREO),
]


def tapar(s):
    """Nunca se reimprime entero lo que se encontró: sería copiarlo a otro sitio."""
    s = s.strip()
    return s[:3] + "…" if len(s) > 3 else "…"


# ------------------------------------------------------------------ texto

def revisar_linea(linea):
    """Devuelve [(qué, trozo)] de una línea."""
    if PERMISO in linea:
        return []
    out = [(nombre, m.group(0)) for nombre, patron in PATRONES for m in patron.finditer(linea)]
    limpia = FECHA.sub(" ", ENLACE.sub(" ", linea))
    for m in NUMERO_LARGO.finditer(limpia):
        digitos = re.sub(r"\D", "", m.group(0))
        if not 8 <= len(digitos) <= 15:
            continue
        antes, despues = limpia[max(0, m.start() - 3):m.start()], limpia[m.end():m.end() + 8]
        if DINERO.search(antes) or DINERO.search(despues):
            continue  # un importe grande no es un documento
        out.append(("número con forma de teléfono o DNI", m.group(0)))
    return out


def revisar_archivo(ruta):
    """Devuelve [(ruta, n_linea, qué, trozo)]."""
    try:
        texto = Path(ruta).read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        return []
    return [(Path(ruta), n, que, trozo)
            for n, linea in enumerate(texto.splitlines(), 1)
            for que, trozo in revisar_linea(linea)]


def archivos_de_texto(raiz):
    for p in sorted(Path(raiz).rglob("*")):
        if ".git" in p.parts or not p.is_file() or p.suffix.lower() not in EXTENSIONES:
            continue
        yield p


# ------------------------------------------------------------------ git

def hay_git():
    return shutil.which("git") is not None


def git(raiz, *args, entrada=None):
    return subprocess.run(["git", "-C", str(raiz)] + list(args), input=entrada,
                          capture_output=True, text=True, encoding="utf-8")


def es_repo(raiz):
    return hay_git() and git(raiz, "rev-parse", "--is-inside-work-tree").stdout.strip() == "true"


def copias_en_git(raiz):
    """Lo que git guarda (o tiene preparado) y no debería: copias de documentos, correos,
    fotos o vídeos, o archivos de más de 1 MB. Devuelve [(ruta, motivo)]."""
    if not es_repo(raiz):
        return []
    out = []
    for nombre in git(raiz, "ls-files", "-z").stdout.split("\0"):
        if not nombre:
            continue
        p = Path(raiz) / nombre
        if Path(nombre).suffix.lower() in COPIAS:
            out.append((nombre, "copia de un documento, correo, foto o vídeo"))
        elif p.is_file() and p.stat().st_size > LIMITE_BYTES:
            out.append((nombre, f"pesa {p.stat().st_size // 1024} KB"))
    return out


def leer_gitignore(raiz):
    p = Path(raiz) / ".gitignore"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def copias_sin_bloquear(raiz):
    """Prueba el .gitignore de verdad, con git, en una carpeta aparte. Devuelve los nombres
    de MUESTRAS que entrarían al repo, o None si no hay git para comprobarlo."""
    if not hay_git():
        return None
    with tempfile.TemporaryDirectory() as tmp:
        if git(tmp, "init", "-q").returncode != 0:
            return None
        Path(tmp, ".gitignore").write_text(leer_gitignore(raiz), encoding="utf-8")
        # Separado por NUL (-z): en Windows, el texto que se pasa a git llega con \r al final de
        # cada linea y git no reconoce la ruta. Con NUL no hay finales de linea que traducir.
        salida = git(tmp, "check-ignore", "--stdin", "-z", entrada="\0".join(MUESTRAS) + "\0").stdout
    bloqueados = set(x for x in salida.split("\0") if x)
    return [m for m in MUESTRAS if m not in bloqueados]


# ------------------------------------------------------------------ los candados de Claude

RED_PROHIBIDA = ["curl *", "wget *", "ssh *", "scp *"]
POWERSHELL_RED = ["Invoke-WebRequest *", "Invoke-RestMethod *"]


def leer_ajustes(raiz, nombre):
    """El JSON de .claude/<nombre>, o {} si no existe o está roto."""
    try:
        return json.loads((Path(raiz) / ".claude" / nombre).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def candados_abiertos(raiz):
    """Lo que falta para que Claude siga encerrado y pregunte antes de subir. [] si está todo."""
    faltan = []
    enc = leer_ajustes(raiz, "encerrado.json")
    sb = enc.get("sandbox", {})
    if not enc.get("permissions", {}).get("blockReadsOutsideWorkingDirectories"):
        faltan.append("encerrado.json ya no impide leer fuera de la carpeta")
    if not (sb.get("enabled") and sb.get("failIfUnavailable") and sb.get("allowUnsandboxedCommands") is False):
        faltan.append("encerrado.json ya no encierra los comandos (o deja arrancar sin encierro)")
    perm = leer_ajustes(raiz, "settings.json").get("permissions", {})
    if not perm.get("blockReadsOutsideWorkingDirectories"):
        faltan.append("settings.json ya no impide leer fuera de la carpeta")
    for t in ("Bash", "PowerShell"):
        if f"{t}(git push *)" not in perm.get("ask", []):
            faltan.append(f"settings.json ya no pide permiso antes de cada git push ({t})")
    return (faltan + candados_windows(raiz) + candados_windows(raiz, "settings.json")
            + candados_codex(raiz) + reglas_compartidas(raiz))


def candados_windows(raiz, nombre="encerrado-windows.json"):
    """En Windows no hay encierro del sistema: quedan los permisos, y tienen que estar todos.
    Se miran en encerrado-windows.json (Claude en la terminal, arrancado con --settings) y en
    settings.json (la app de escritorio de Claude, que solo lee esa)."""
    faltan = []
    win = leer_ajustes(raiz, nombre)
    perm = win.get("permissions", {})
    if not perm.get("blockReadsOutsideWorkingDirectories"):
        faltan.append(f"{nombre} ya no impide leer fuera de la carpeta")
    ask = perm.get("ask", [])
    for t in ("Bash", "PowerShell"):
        if t not in ask:
            faltan.append(f"{nombre} ya no pide permiso antes de cada comando ({t})")
    for t in ("WebFetch", "WebSearch"):
        if t not in ask:
            faltan.append(f"{nombre} ya no pide permiso antes de entrar en internet ({t})")
    reglas = [f"Bash({c})" for c in RED_PROHIBIDA] + [f"PowerShell({c})" for c in RED_PROHIBIDA + POWERSHELL_RED]
    sueltos = [r for r in reglas if r not in perm.get("deny", [])]
    if sueltos:
        faltan.append(f"{nombre} ya no bloquea: " + ", ".join(sueltos))
    if perm.get("disableBypassPermissionsMode") != "disable" or perm.get("disableAutoMode") != "disable":
        faltan.append(f"{nombre} deja entrar en un modo que aprueba solo")
    if win.get("sandbox", {}).get("failIfUnavailable"):
        faltan.append(f"{nombre} exige un encierro que en Windows no existe: Claude no arrancaría")
    return faltan


# Codex: lo que manda es .codex/config.toml. Python 3.8 no trae lector de TOML, así que se lee
# solo lo que usa este vault: «clave = valor» y secciones [así]. Sin él, Codex trabajaría con lo
# que tenga puesto en su equipo, que puede ser acceso total.

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


# ------------------------------------------------------------------ lo que dice el vault de ti

SIN_CONTESTAR = "[sin contestar]"
HUECO_RESPUESTA = "(la escribes aquí, o el agente te la pregunta y la copia tal cual)"
CITA_RESPUESTA = re.compile(r"\((?:tu |tus )?respuestas? (\d+(?:(?:, | y )\d+)*)\)")
ENTRE_COMILLAS = re.compile(r"«([^«»]*)»")
ELIPSIS = re.compile(r"\s*(?:…|\.\.\.)\s*")


def junto(texto):
    return " ".join(texto.split())


def respuestas(raiz):
    """Tus siete respuestas de criterio/apuntes.md, en orden: el texto tal cual, o None si
    sigue sin contestar."""
    salida, actual = [], None
    for linea in leer_texto(raiz, Path("criterio") / "apuntes.md").splitlines():
        if "*Tu respuesta:*" in linea:
            actual = [linea.split("*Tu respuesta:*", 1)[1]]
            salida.append(actual)
        elif actual is not None and ("*Qué hizo el vault con esto:*" in linea or linea.startswith(("- **", "#"))):
            actual = None
        elif actual is not None:
            actual.append(linea)
    textos = [junto(" ".join(trozos)) for trozos in salida[:7]]
    return [None if t in ("", HUECO_RESPUESTA, SIN_CONTESTAR) else t for t in textos]


def cita_literal(cita, texto):
    """Lo que va entre «» está tal cual en tu respuesta (un «…» salta lo que se omite)."""
    trozos = [junto(t) for t in ELIPSIS.split(cita) if junto(t)]
    desde = 0
    for t in trozos:
        donde = texto.find(t, desde)
        if donde < 0:
            return False
        desde = donde + len(t)
    return bool(trozos)


def inventado(raiz):
    """Lo que el README o un proyecto dicen de ti citando una de tus respuestas sin que lo dijeras:
    una respuesta sin contestar que no dice [sin contestar], o una cita entre «» que no está
    literal en la respuesta que cita. El agente no deduce ni rellena: copia tus palabras."""
    tuyas = respuestas(raiz)
    problemas = []
    carpeta = Path(raiz) / "proyectos"
    proyectos = sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []
    for p in [Path(raiz) / "README.md"] + [x for x in proyectos if x.name != "_plantilla.md"]:
        nombre = p.relative_to(raiz).as_posix()
        for n, linea in enumerate(leer_texto(raiz, nombre).splitlines(), 1):
            citas = CITA_RESPUESTA.findall(linea)
            if not citas:
                continue
            numeros = [int(x) for c in citas for x in re.findall(r"\d+", c)]
            dichas = [tuyas[i - 1] for i in numeros if 1 <= i <= len(tuyas) and tuyas[i - 1]]
            comillas = [c for c in ENTRE_COMILLAS.findall(linea) if junto(c) != SIN_CONTESTAR]
            if not dichas:
                if SIN_CONTESTAR not in linea or comillas:
                    problemas.append(f"{nombre}:{n} · dice algo de tu respuesta {', '.join(map(str, numeros))}, "
                                     f"que está sin contestar: tiene que decir {SIN_CONTESTAR}")
                continue
            if not comillas:
                problemas.append(f"{nombre}:{n} · cita tu respuesta {', '.join(map(str, numeros))} sin tus "
                                 "palabras: van entre «» tal cual las dijiste")
            for c in comillas:
                if not any(cita_literal(c, d) for d in dichas):
                    problemas.append(f"{nombre}:{n} · «{c[:60]}» no está tal cual en tu respuesta "
                                     f"{', '.join(map(str, numeros))}")
    return problemas


# ------------------------------------------------------------------ entrada

def linea_hallazgo(h, raiz=RAIZ):
    ruta, n, que, trozo = h
    try:
        ruta = ruta.resolve().relative_to(Path(raiz).resolve())
    except ValueError:
        pass
    return f"{ruta}:{n} · {que} · «{tapar(trozo)}»"


def revisar_todo(raiz=RAIZ):
    """Devuelve (líneas para imprimir, código de salida)."""
    o, problemas = [], 0
    textos = list(archivos_de_texto(raiz))
    hallazgos = [h for p in textos for h in revisar_archivo(p)]
    if hallazgos:
        problemas += len(hallazgos)
        o.append(f"Cosas que no tienen que estar escritas aquí ({len(hallazgos)}):")
        o += ["  " + linea_hallazgo(h, raiz) for h in hallazgos]
        o.append("  Sácalas (una clave, además, cámbiala). Si una está bien, añade  <!-- revisar:ok -->  al final.")
    copias = copias_en_git(raiz)
    if copias:
        problemas += len(copias)
        o.append(f"Git guarda copias que no van aquí ({len(copias)}):")
        o += [f"  {n} · {motivo}" for n, motivo in copias]
        o.append("  Sácalas de git sin borrarlas de tu equipo:  git rm --cached <archivo>")
    sueltos = copias_sin_bloquear(raiz)
    if sueltos is None:
        o.append("Sin git en este equipo no puedo comprobar el .gitignore.")
    elif sueltos:
        problemas += len(sueltos)
        o.append(f"El .gitignore ya no bloquea: {', '.join(sueltos)}. Recupéralo:  git checkout -- .gitignore")
    abiertos = candados_abiertos(raiz)
    if abiertos:
        problemas += len(abiertos)
        o.append("El agente (Claude o Codex) ya no está encerrado, ya no pregunta antes de subir o se ha quedado sin reglas:")
        o += [f"  {a}" for a in abiertos]
        o.append("  Recupéralos:  git checkout -- .claude/ .codex/ AGENTS.md CLAUDE.md")
    puesto = inventado(raiz)
    if puesto:
        problemas += len(puesto)
        o.append("El vault dice de ti cosas que no dijiste en tus siete respuestas (criterio/apuntes.md):")
        o += [f"  {x}" for x in puesto]
        o.append("  Copia tus palabras tal cual entre «», o deja la línea en [sin contestar].")
    if not problemas:
        o.insert(0, f"revisar: {len(textos)} archivos de texto, sin claves, correos ni teléfonos escritos, "
                    "sin copias de documentos en git, Claude y Codex siguen encerrados y nada dice de ti lo que no dijiste.")
        o.insert(1, "  (Los nombres de personas no los puedo ver: eso se cuida al escribir.)")
    return o, (1 if problemas else 0)


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    if argv:
        hallazgos = [h for a in argv for h in revisar_archivo(Path(a))]
        for h in hallazgos:
            print(linea_hallazgo(h))
        if not hallazgos:
            print(f"revisar: {len(argv)} archivos, sin claves, correos ni teléfonos escritos.")
        return 1 if hallazgos else 0
    lineas, codigo = revisar_todo()
    print("\n".join(lineas))
    return codigo


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
