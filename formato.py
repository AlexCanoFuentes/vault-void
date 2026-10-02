#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""El formato universal de una estrella: valida su estrella.json y la huella de cada fichero.

Uso:
  python3 formato.py CARPETA [CARPETA...]   valida cada estrella; sale 1 si alguna no vale
  python3 formato.py --huellas CARPETA      rehace la lista «ficheros» de su estrella.json con la
                                            huella (sha256) de cada fichero de la carpeta

Qué es una estrella, campo a campo: estrellas/FORMATO.md. Aquí solo se mira la forma y que los
ficheros sean los que dice, con la huella que dice. Si está limpia (sin datos ni conexiones con el
vault de nadie) y cuánto vale (KERNEL) lo mira puerta.py.

Solo biblioteca estándar. Las rutas y la huella son las mismas que usa void.py para traerla.
"""
import json
import re
import sys
from pathlib import Path, PurePosixPath

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import void  # noqa: E402  ruta_segura y huella: las mismas al validar y al traer

FICHA = "estrella.json"
FORMATO = 1
NIVELES = ("oficiales", "socio", "comunidad")

# Listas cerradas, comunes a todos. Salen del 26-sep (06-ideas/kernel-como-capa.md en el vault de
# Alex). Crecen por pull request a este fichero y a FORMATO.md, nunca en una estrella suelta.
FALLOS = (
    "dato inventado",
    "límite sin comprobar",
    "se coló algo privado",
    "regla que solo vive en un documento",
    "comprobación que no puede fallar",
    "decidir por la persona",
    "dato caducado",
    "construir sin definir lo que se construye",
)
CUANDO = (
    "al empezar",
    "antes de construir",
    "construyendo",
    "al publicar",
    "al vender",
    "al cobrar",
    "con un tercero",
    "al cerrar",
)
COSTES = ("minutos", "horas", "días", "dinero", "un tercero", "sin medir")

RE_NOMBRE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
RE_VERSION = re.compile(r"\d+(?:\.\d+)*")
RE_AUTOR = re.compile(r"[A-Za-z0-9](?:-?[A-Za-z0-9]){0,38}")   # un usuario de GitHub
RE_HUELLA = re.compile(r"[0-9a-f]{64}")
RE_VIVE_EN = re.compile(r"(.+):(\d+)")

# Lo que no es de la estrella aunque esté en su carpeta.
IGNORAR_DIRS = {"__pycache__", ".git"}
IGNORAR_SUFIJOS = (".pyc",)

OBLIGATORIOS = ("formato", "nombre", "titulo", "version", "nivel", "autor", "regla", "resuelve",
                "nacio_de", "criterio", "ficheros")
OPCIONALES = ("cuando", "palabras_clave", "no_protege", "requisitos", "instalar", "probado_en",
              "riesgo", "prueba", "vive_en", "uso", "no_se_instala", "huella_historia")


def ficheros_de(carpeta):
    """{ruta posix: huella} de todo lo que hay en la carpeta de la estrella, menos su ficha."""
    carpeta = Path(carpeta)
    salida = {}
    for p in sorted(carpeta.rglob("*")):
        rel = p.relative_to(carpeta)
        if any(parte in IGNORAR_DIRS for parte in rel.parts) or p.name.endswith(IGNORAR_SUFIJOS):
            continue
        if p.is_symlink():
            salida[rel.as_posix()] = "enlace"
            continue
        if not p.is_file():
            continue
        ruta = rel.as_posix()
        if ruta == FICHA:
            continue
        salida[ruta] = void.huella(p.read_bytes())
    return salida


def leer_ficha(carpeta):
    """El estrella.json como dict. Lanza ValueError con una frase si no se puede leer."""
    p = Path(carpeta) / FICHA
    if not p.is_file():
        raise ValueError("no tiene {}".format(FICHA))
    try:
        datos = json.loads(p.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ValueError("{} no es JSON válido en UTF-8".format(FICHA))
    if not isinstance(datos, dict):
        raise ValueError("{} no es un objeto".format(FICHA))
    return datos


def _texto(v, minimo=1, maximo=2000):
    return isinstance(v, str) and minimo <= len(v.strip()) and len(v) <= maximo


def _lista_textos(v, maximo=2000):
    return isinstance(v, list) and all(_texto(x, 1, maximo) for x in v)


def _entero(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def validar(carpeta, ficha=None):
    """Lista de problemas (frases). Vacía = la estrella tiene la forma y las huellas que dice.

    La carpeta tiene que ser estrellas/<nivel>/<nombre>/ (o cualquier <nivel>/<nombre>/)."""
    carpeta = Path(carpeta)
    problemas = []
    if ficha is None:
        try:
            ficha = leer_ficha(carpeta)
        except ValueError as e:
            return [str(e)]

    for clave in OBLIGATORIOS:
        if clave not in ficha:
            problemas.append("falta «{}»".format(clave))
    for clave in ficha:
        if clave not in OBLIGATORIOS and clave not in OPCIONALES:
            problemas.append("«{}» no es un campo del formato (FORMATO.md los lista todos)".format(clave))
    if problemas:
        return problemas

    if ficha["formato"] != FORMATO:
        problemas.append("«formato» tiene que ser {}".format(FORMATO))
    nombre = ficha["nombre"]
    if not isinstance(nombre, str) or not RE_NOMBRE.fullmatch(nombre) or len(nombre) > 40:
        problemas.append("«nombre» va en minúsculas, cifras y guiones, hasta 40 caracteres")
    elif nombre != carpeta.name:
        problemas.append("«nombre» ({}) no es el de su carpeta ({})".format(nombre, carpeta.name))
    if not _texto(ficha["titulo"], 1, 80):
        problemas.append("«titulo» tiene que ser un texto de hasta 80 caracteres")
    if not isinstance(ficha["version"], str) or not RE_VERSION.fullmatch(ficha["version"]):
        problemas.append("«version» tiene que ser como 0.1.0")
    nivel = ficha["nivel"]
    if nivel not in NIVELES:
        problemas.append("«nivel» tiene que ser uno de: {}".format(", ".join(NIVELES)))
    elif nivel != carpeta.parent.name:
        problemas.append("«nivel» ({}) no es la carpeta donde vive ({})".format(nivel, carpeta.parent.name))
    if not isinstance(ficha["autor"], str) or not RE_AUTOR.fullmatch(ficha["autor"]):
        problemas.append("«autor» tiene que ser un usuario de GitHub")
    if not _texto(ficha["regla"], 1, 500):
        problemas.append("«regla» tiene que ser un texto (la restricción, en imperativo)")
    if not _texto(ficha["criterio"], 1, 1000):
        problemas.append("«criterio» tiene que ser un texto")

    resuelve = ficha["resuelve"]
    if not isinstance(resuelve, dict) or not _texto(resuelve.get("frase"), 1, 500) or \
            set(resuelve) - {"frase", "medido"} or ("medido" in resuelve and not _texto(resuelve["medido"])):
        problemas.append("«resuelve» tiene que ser {\"frase\": ..., \"medido\": ...} (medido es opcional)")

    nacio = ficha["nacio_de"]
    if not isinstance(nacio, list) or not nacio:
        problemas.append("«nacio_de» tiene que decir al menos un error que la hizo nacer")
    else:
        for i, e in enumerate(nacio, 1):
            if not isinstance(e, dict) or set(e) - {"fallo", "que_paso", "coste"}:
                problemas.append("«nacio_de» {}: cada error es {{\"fallo\", \"que_paso\", \"coste\"}}".format(i))
                continue
            if e.get("fallo") not in FALLOS:
                problemas.append("«nacio_de» {}: «fallo» tiene que ser uno de la lista cerrada".format(i))
            if not _texto(e.get("que_paso"), 20, 1000):
                problemas.append("«nacio_de» {}: «que_paso» cuenta el error en al menos 20 caracteres".format(i))
            if "coste" in e and e["coste"] not in COSTES:
                problemas.append("«nacio_de» {}: «coste» tiene que ser uno de: {}".format(i, ", ".join(COSTES)))

    # ---- opcionales: si están, con su forma
    if "cuando" in ficha and (not isinstance(ficha["cuando"], list) or
                              any(c not in CUANDO for c in ficha["cuando"])):
        problemas.append("«cuando» es una lista de la lista cerrada: {}".format(", ".join(CUANDO)))
    for clave in ("palabras_clave", "no_protege", "instalar", "probado_en"):
        if clave in ficha and not _lista_textos(ficha[clave], 500):
            problemas.append("«{}» tiene que ser una lista de textos".format(clave))
    if "requisitos" in ficha and not _texto(ficha["requisitos"], 1, 500):
        problemas.append("«requisitos» tiene que ser un texto")
    if "riesgo" in ficha:
        r = ficha["riesgo"]
        if not isinstance(r, dict) or set(r) - {"ejecuta", "red", "deshacer"} or \
                not all(_texto(v, 1, 1000) for v in r.values()):
            problemas.append("«riesgo» es {\"ejecuta\", \"red\", \"deshacer\"}, cada uno un texto")
    if "uso" in ficha:
        u = ficha["uso"]
        if not isinstance(u, dict) or set(u) - {"vaults", "semanas", "nota"} or \
                not _entero(u.get("vaults")) or not _entero(u.get("semanas", 0)) or \
                ("nota" in u and not _texto(u["nota"])):
            problemas.append("«uso» es {\"vaults\": n, \"semanas\": n, \"nota\": ...}")
    if "huella_historia" in ficha and (not isinstance(ficha["huella_historia"], str) or
                                       not RE_HUELLA.fullmatch(ficha["huella_historia"])):
        problemas.append("«huella_historia» es un sha256 en hexadecimal")

    # ---- los ficheros: los que dice, con la huella que dice
    declarados = ficha["ficheros"]
    if not isinstance(declarados, dict) or not declarados:
        problemas.append("«ficheros» tiene que listar al menos un fichero con su huella")
        return problemas
    for ruta, h in sorted(declarados.items()):
        if not void.ruta_segura(ruta) or ruta == FICHA:
            problemas.append("«ficheros»: {} no es una ruta que se pueda instalar".format(ruta))
        if not isinstance(h, str) or not RE_HUELLA.fullmatch(h):
            problemas.append("«ficheros»: la huella de {} no es un sha256".format(ruta))
    if len({r.lower() for r in declarados}) != len(declarados):
        problemas.append("«ficheros» repite una ruta (en Windows serían el mismo fichero)")
    reales = ficheros_de(carpeta)
    for ruta in sorted(set(reales) - set(declarados)):
        problemas.append("{} está en la carpeta y no en «ficheros»".format(ruta))
    for ruta in sorted(set(declarados) - set(reales)):
        problemas.append("{} está en «ficheros» y no en la carpeta".format(ruta))
    for ruta in sorted(set(declarados) & set(reales)):
        if reales[ruta] == "enlace":
            problemas.append("{} es un enlace: una estrella solo lleva ficheros".format(ruta))
        elif reales[ruta] != declarados[ruta]:
            problemas.append("la huella de {} no cuadra con «ficheros»".format(ruta))

    if "no_se_instala" in ficha:
        n = ficha["no_se_instala"]
        if not isinstance(n, list) or any(x not in declarados for x in n):
            problemas.append("«no_se_instala» lista rutas que estén en «ficheros»")
    if "prueba" in ficha:
        p = ficha["prueba"]
        comando = p.get("comando") if isinstance(p, dict) else None
        if not isinstance(p, dict) or set(p) - {"comando", "comprobaciones", "rojos", "sabotaje"} or \
                not _lista_textos(comando or [None]) or comando[0] != "python" or len(comando) < 2 or \
                comando[1] not in declarados or \
                not all(_entero(p[k]) for k in ("comprobaciones", "rojos") if k in p) or \
                ("sabotaje" in p and not _texto(p["sabotaje"])):
            problemas.append("«prueba» es {\"comando\": [\"python\", \"<fichero de la estrella>\", ...], "
                             "\"comprobaciones\": n, \"rojos\": n, \"sabotaje\": ...}")
    if "vive_en" in ficha:
        m = RE_VIVE_EN.fullmatch(ficha["vive_en"]) if isinstance(ficha["vive_en"], str) else None
        if not m or m.group(1) not in declarados:
            problemas.append("«vive_en» es «fichero:línea», con un fichero de la estrella")
        else:
            p = carpeta.joinpath(*PurePosixPath(m.group(1)).parts)
            lineas = p.read_bytes().decode("utf-8", "replace").splitlines() if p.is_file() else []
            n = int(m.group(2))
            if not 1 <= n <= len(lineas) or not lineas[n - 1].strip():
                problemas.append("«vive_en»: {} no tiene una línea {} con algo escrito".format(m.group(1), n))
    return problemas


def rehacer_huellas(carpeta):
    """Reescribe «ficheros» en estrella.json con lo que hay en la carpeta. Mantiene el resto."""
    carpeta = Path(carpeta)
    ficha = leer_ficha(carpeta)
    ficha["ficheros"] = ficheros_de(carpeta)
    (carpeta / FICHA).write_bytes((json.dumps(ficha, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return ficha["ficheros"]


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
    if args[0] == "--huellas":
        for c in args[1:]:
            try:
                n = len(rehacer_huellas(c))
            except ValueError as e:
                print("{}: {}".format(c, e), file=sys.stderr)
                return 1
            print("{}: huellas rehechas ({} ficheros).".format(c, n))
        return 0
    malas = 0
    for c in args:
        problemas = validar(c)
        if problemas:
            malas += 1
            print("{}: NO VALE".format(c))
            for p in problemas:
                print("  - " + p)
        else:
            print("{}: formato correcto.".format(c))
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
