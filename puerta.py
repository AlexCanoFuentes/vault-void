#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La puerta del catálogo: rechaza, o dice en qué liga entra una estrella.

Uso:
  python3 puerta.py estrellas/<nivel>/<nombre> [...]   juzga esas estrellas
  python3 puerta.py --todas                             juzga todas las de estrellas/
  python3 puerta.py --cambiadas REF                     las que cambian respecto a REF (rama o commit),
                                                        y además mira que suban de versión

Opciones:
  --ejecutar     corre la prueba que declara cada estrella (en una copia, fuera del repo). Es lo que
                 hace GitHub Actions. En tu máquina, solo con estrellas que hayas leído.
  --nombres F    más nombres de personas a vigilar, uno por línea (un fichero fuera del repo)

Tres salidas, en este orden:
  1. RECHAZADA: el formato no vale (formato.py), no sale limpia (secretos, correos, teléfonos,
     nombres de personas o rutas de la máquina de alguien), su prueba no pasa (con --ejecutar), o
     cambian sus ficheros y no su versión (con --cambiadas). No entra en ninguna liga.
  2. LIGA PEQUEÑA: KERNEL por debajo de 80, con el número y la dimensión más débil.
  3. LIGA GRANDE: KERNEL 80 o más.

KERNEL son las seis dimensiones de la rúbrica de AICODE (skills/kernel/REFERENCE.md), con sus
pesos, puntuadas con reglas fijas sobre lo que la estrella declara. La tabla está en
estrellas/FORMATO.md. No dice cómo subir la nota: eso lo hace cada uno con el kernel de su vault.

Sale con 1 si alguna estrella queda rechazada. Solo biblioteca estándar.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import formato  # noqa: E402
import fugas  # noqa: E402

UMBRAL = 80
TIEMPO_PRUEBA = 600  # segundos

# Rutas de la máquina de alguien: una estrella que las lleva está conectada a un vault concreto.
RUTAS_DE_MAQUINA = [
    re.compile(r"(?<![\w.~])/(?:home|Users)/[A-Za-z0-9._-]+"),
    re.compile(r"(?i)\b[A-Z]:\\+(?:Users|Documents and Settings)\\+"),
    re.compile(r"(?i)/mnt/[a-z]/Users/"),
    re.compile(r"(?i)\\\\wsl(?:\$|\.localhost)\\"),
]


# ---------------------------------------------------------------- KERNEL

def _una_frase(texto):
    trozos = [t for t in re.split(r"[.!?](?:\s+|$)", texto.strip()) if t.strip()]
    return len(trozos) == 1


def _coste(ficha):
    puntos = {"días": 5, "dinero": 5, "un tercero": 5, "horas": 3, "minutos": 1}
    return max([puntos.get(e.get("coste"), 0) for e in ficha["nacio_de"]] or [0])


# (dimensión, peso, pregunta, [(qué se mira, puntos, cómo)]). Dimensiones y pesos: REFERENCE.md.
# Cada cómo devuelve los puntos que da (o True/False para todo o nada).
RUBRICA = [
    ("Claridad", 20, "¿Se entiende en una frase qué error resuelve y cuándo muerde?", [
        ("regla en una frase de hasta 200 caracteres", 6,
         lambda f, c: len(f["regla"]) <= 200 and _una_frase(f["regla"])),
        ("resuelve.frase de hasta 200 caracteres", 4, lambda f, c: len(f["resuelve"]["frase"]) <= 200),
        ("cuando", 6, lambda f, c: bool(f.get("cuando"))),
        ("3 o más palabras_clave", 4, lambda f, c: len(f.get("palabras_clave", [])) >= 3),
    ]),
    ("Alcance", 20, "¿Dice qué hace y qué no?", [
        ("no_protege con algo", 10, lambda f, c: len(f.get("no_protege", [])) >= 1),
        ("no_protege con 3 o más", 4, lambda f, c: len(f.get("no_protege", [])) >= 3),
        ("requisitos", 6, lambda f, c: bool(f.get("requisitos"))),
    ]),
    ("Contexto", 15, "¿Otro la instala y la termina sin preguntar?", [
        ("instalar", 6, lambda f, c: bool(f.get("instalar"))),
        ("un README.md entre sus ficheros", 5, lambda f, c: "README.md" in f["ficheros"]),
        ("probado_en", 4, lambda f, c: bool(f.get("probado_en"))),
    ]),
    ("Riesgo", 15, "¿Dice qué ejecuta en tu máquina, si usa la red y cómo se quita?", [
        ("riesgo.ejecuta", 5, lambda f, c: bool(f.get("riesgo", {}).get("ejecuta"))),
        ("riesgo.red", 5, lambda f, c: bool(f.get("riesgo", {}).get("red"))),
        ("riesgo.deshacer", 5, lambda f, c: bool(f.get("riesgo", {}).get("deshacer"))),
    ]),
    ("Validación", 15, "¿Se puede ver la cura funcionando?", [
        ("prueba.comando", 5, lambda f, c: bool(f.get("prueba", {}).get("comando"))),
        ("prueba.rojos de 1 o más", 4, lambda f, c: f.get("prueba", {}).get("rojos", 0) >= 1),
        ("prueba.sabotaje", 3, lambda f, c: bool(f.get("prueba", {}).get("sabotaje"))),
        ("vive_en", 3, lambda f, c: bool(f.get("vive_en"))),
    ]),
    ("Prioridad", 15, "¿Cuánto cuesta el error y quién la usa ya?", [
        ("coste del error", 5, lambda f, c: _coste(f)),
        ("usada en 1 vault o más", 5, lambda f, c: f.get("uso", {}).get("vaults", 0) >= 1),
        ("durante 4 semanas o más", 5, lambda f, c: f.get("uso", {}).get("semanas", 0) >= 4),
    ]),
]


def puntuar(ficha, carpeta=None):
    """{"total": n, "dimensiones": {dim: [puntos, peso]}, "mas_debil": dim}. La ficha ya es válida."""
    dims = {}
    for dim, peso, _, comprobaciones in RUBRICA:
        puntos = 0
        for _, valor, como in comprobaciones:
            r = como(ficha, carpeta)
            puntos += valor if r is True else (0 if r is False else min(int(r), valor))
        dims[dim] = [min(puntos, peso), peso]
    total = sum(p for p, _ in dims.values())
    mas_debil = min(dims, key=lambda d: dims[d][0] / dims[d][1])   # a igualdad, la primera de la tabla
    return {"total": total, "dimensiones": dims, "mas_debil": mas_debil}


def liga(total):
    return "grande" if total >= UMBRAL else "pequeña"


# ---------------------------------------------------------------- limpia

def _textos(carpeta):
    """(ruta, texto) de cada fichero de texto de la estrella, su ficha incluida."""
    for p in sorted(Path(carpeta).rglob("*")):
        rel = p.relative_to(carpeta)
        if not p.is_file() or any(x in formato.IGNORAR_DIRS for x in rel.parts) or \
                p.name.endswith(formato.IGNORAR_SUFIJOS):
            continue
        datos = p.read_bytes()
        if b"\0" in datos[:8000]:
            continue
        yield rel.as_posix(), datos.decode("utf-8", "replace")


def limpia(carpeta, nombres=frozenset()):
    """Lista de problemas: lo que fugas.py encuentra y las rutas de la máquina de alguien."""
    vigilados = fugas.NOMBRES | set(nombres)
    problemas = []
    for ruta, texto in _textos(carpeta):
        for n, tipo, trozo in fugas.revisar_texto(ruta, vigilados):
            problemas.append("el nombre del fichero {} lleva un {} ({})".format(ruta, tipo, trozo))
        for n, tipo, trozo in fugas.revisar_texto(texto, vigilados):
            problemas.append("{}:{}: {} ({})".format(ruta, n, tipo, trozo))
        for n, linea in enumerate(texto.splitlines(), 1):
            for rx in RUTAS_DE_MAQUINA:
                m = rx.search(linea)
                if m:
                    problemas.append("{}:{}: ruta de la máquina de alguien ({})".format(
                        ruta, n, fugas.tapar(m.group(0))))
    return problemas


# ---------------------------------------------------------------- lo que solo se mira en Actions

def ejecutar_prueba(carpeta, ficha):
    """None si su prueba pasa; si no, el motivo. Corre en una copia de la estrella, fuera del repo."""
    prueba = ficha.get("prueba")
    if not prueba:
        return None
    tmp = Path(tempfile.mkdtemp(prefix="puerta-"))
    try:
        copia = tmp / ficha["nombre"]
        shutil.copytree(str(carpeta), str(copia), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        orden = [sys.executable] + list(prueba["comando"][1:])
        try:
            r = subprocess.run(orden, cwd=str(copia), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=TIEMPO_PRUEBA)
        except subprocess.TimeoutExpired:
            return "su prueba no termina en {} segundos".format(TIEMPO_PRUEBA)
        if r.returncode != 0:
            lineas = [l for l in r.stdout.decode("utf-8", "replace").splitlines() if l.strip()]
            return "su prueba no pasa (sale con {}): {}".format(r.returncode, (lineas or ["?"])[-1][:200])
        return None
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)


def _version(v):
    return tuple(int(x) for x in v.split("."))


def ficha_en(raiz, ref, carpeta):
    """El estrella.json de esa carpeta en REF, o None si no existía."""
    ruta = (Path(carpeta).resolve().relative_to(Path(raiz).resolve()) / formato.FICHA).as_posix()
    r = subprocess.run(["git", "-C", str(raiz), "show", "{}:{}".format(ref, ruta)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout.decode("utf-8"))
    except ValueError:
        return None


def sube_de_version(antes, ahora):
    """None si está bien; si no, el motivo."""
    if not isinstance(antes, dict) or not isinstance(antes.get("version"), str) or \
            not formato.RE_VERSION.fullmatch(antes["version"]):
        return None
    if _version(ahora["version"]) < _version(antes["version"]):
        return "baja de versión ({} -> {})".format(antes["version"], ahora["version"])
    if antes.get("ficheros") != ahora["ficheros"] and ahora["version"] == antes["version"]:
        return "cambian sus ficheros y no su versión ({}): quien ya la tiene no recibiría el cambio".format(
            ahora["version"])
    return None


# ---------------------------------------------------------------- el veredicto

def juzgar(carpeta, ejecutar=False, nombres=frozenset(), raiz=None, contra=None):
    """{"carpeta", "nombre", "version", "rechazo": [motivos], "kernel": {...} o None, "liga", "ejecutada"}"""
    carpeta = Path(carpeta)
    v = {"carpeta": carpeta, "nombre": carpeta.name, "version": None, "rechazo": [], "kernel": None,
         "liga": None, "ejecutada": False}
    try:
        ficha = formato.leer_ficha(carpeta)
    except ValueError as e:
        v["rechazo"].append(str(e))
        return v
    v["version"] = ficha.get("version")
    v["rechazo"] += formato.validar(carpeta, ficha)
    v["rechazo"] += limpia(carpeta, nombres)
    if v["rechazo"]:
        return v
    if contra is not None:
        motivo = sube_de_version(ficha_en(raiz or AQUI, contra, carpeta), ficha)
        if motivo:
            v["rechazo"].append(motivo)
    if ejecutar:
        motivo = ejecutar_prueba(carpeta, ficha)
        v["ejecutada"] = "prueba" in ficha
        if motivo:
            v["rechazo"].append(motivo)
    if v["rechazo"]:
        return v
    v["kernel"] = puntuar(ficha, carpeta)
    v["liga"] = liga(v["kernel"]["total"])
    return v


def contar(veredicto):
    """Lo que se le enseña a la persona, en líneas."""
    v = veredicto
    cabeza = "{} ({} {})".format(Path(v["carpeta"]).as_posix(), v["nombre"], v["version"] or "?")
    if v["rechazo"]:
        return [cabeza, "  RECHAZADA:"] + ["    - " + m for m in v["rechazo"]]
    k = v["kernel"]
    debil = k["dimensiones"][k["mas_debil"]]
    lineas = [cabeza,
              "  LIGA {} · KERNEL {} · más débil: {} ({}/{})".format(
                  v["liga"].upper(), k["total"], k["mas_debil"], debil[0], debil[1]),
              "  " + " · ".join("{} {}/{}".format(d, p, w) for d, (p, w) in k["dimensiones"].items())]
    return lineas


# ---------------------------------------------------------------- qué estrellas

def todas(raiz):
    """(carpetas de estrella, sueltos): estrellas/<nivel>/<nombre>/ y lo que no encaja ahí."""
    base = Path(raiz) / "estrellas"
    carpetas, sueltos = [], []
    if not base.is_dir():
        return carpetas, sueltos
    for nivel in sorted(base.iterdir()):
        if not nivel.is_dir():
            continue
        if nivel.name not in formato.NIVELES:
            sueltos.append("{}: no es un nivel ({})".format(nivel.relative_to(raiz).as_posix(),
                                                            ", ".join(formato.NIVELES)))
            continue
        for c in sorted(nivel.iterdir()):
            if c.is_dir():
                carpetas.append(c)
            else:
                sueltos.append("{}: fichero suelto; cada estrella va en su carpeta".format(
                    c.relative_to(raiz).as_posix()))
    return carpetas, sueltos


def cambiadas(raiz, ref):
    """Carpetas de estrella que cambian respecto a ref (lo commiteado, lo sin commitear y lo nuevo)."""
    salida = set()
    rutas = []
    for orden in (["diff", "--name-only", ref, "--", "estrellas"],
                  ["ls-files", "--others", "--exclude-standard", "--", "estrellas"]):
        r = subprocess.run(["git", "-C", str(raiz)] + orden, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode != 0:
            raise SystemExit("git no puede comparar con {}: {}".format(
                ref, r.stderr.decode("utf-8", "replace").strip()))
        rutas += [l for l in r.stdout.decode("utf-8", "replace").splitlines() if l.strip()]
    for ruta in rutas:
        partes = PurePosixPath(ruta).parts
        if len(partes) >= 4:
            salida.add(Path(raiz, *partes[:3]))
        elif len(partes) == 3:
            salida.add(Path(raiz, *partes[:2]))   # algo suelto en un nivel: que lo vea todas()
    return sorted(salida)


def main(argv):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = list(argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    ejecutar = "--ejecutar" in args
    if ejecutar:
        args.remove("--ejecutar")
    nombres = set()
    if "--nombres" in args:
        i = args.index("--nombres")
        nombres = fugas.nombres_extra(args[i + 1] if i + 1 < len(args) else None)
        del args[i:i + 2]
    raiz, contra, sueltos = AQUI, None, []
    if args and args[0] == "--todas":
        carpetas, sueltos = todas(raiz)
    elif args and args[0] == "--cambiadas":
        if len(args) < 2:
            print("Falta con qué comparar: --cambiadas origin/main", file=sys.stderr)
            return 2
        contra = args[1]
        _, sueltos_todos = todas(raiz)
        tocadas = cambiadas(raiz, contra)
        carpetas = [c for c in tocadas if c.is_dir() and c.parent.parent.name == "estrellas"]
        retiradas = [c for c in tocadas if not c.exists()]
        sueltos = [s for s in sueltos_todos if any(s.startswith(Path(c).relative_to(raiz).as_posix())
                                                    for c in tocadas)]
        for c in retiradas:
            print("{}: retirada del catálogo.".format(c.relative_to(raiz).as_posix()))
        if not carpetas and not sueltos:
            print("Ninguna estrella cambia respecto a {}.".format(contra))
            return 0
    else:
        carpetas = [Path(a) for a in args]
    if not (fugas.NOMBRES or nombres):
        print("OJO: sin lista de nombres (.fugas-nombres): esta pasada no vigila nombres de personas.")
    rechazadas = 0
    for s in sueltos:
        print(s)
        rechazadas += 1
    for c in carpetas:
        v = juzgar(c, ejecutar=ejecutar, nombres=nombres, raiz=raiz, contra=contra)
        for linea in contar(v):
            print(linea)
        if not v["rechazo"] and v["ejecutada"]:
            print("  prueba ejecutada: en verde.")
        rechazadas += 1 if v["rechazo"] else 0
    print()
    print("{} estrella(s) juzgada(s), {} rechazada(s).".format(len(carpetas), rechazadas))
    return 1 if rechazadas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
