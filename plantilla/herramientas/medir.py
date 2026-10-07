#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cómo va tu vault, en cifras, para mandarlo sin que salga nada de lo que hay escrito dentro.

Uso:
  python3 herramientas/medir.py                     el bloque de hoy, para copiar y mandar
  python3 herramientas/medir.py --toca              dice si toca medir: a los 7 días de montar el vault
  python3 herramientas/medir.py --hoy 2026-10-15    como si fuera ese día

Qué cuenta: cuántas veces has guardado y en cuántos días, cuántos proyectos tienen objetivo y
fecha, cuántos apuntes de criterio nuevos hay (y cuántos son Corregí), cuántas de las siete
preguntas siguen sin contestar, cuántas herramientas tuyas hay, si pasan las pruebas y revisar, y
qué versión de Void tienes. Nunca un nombre, un título ni una línea de tus ficheros: solo números,
sí o no y la versión. Lo de cómo te ha ido lo pones tú, con tus palabras.

Cuando la hayas mandado (o si no quieres medir), se apunta en git y no vuelve a salir:
  git commit --allow-empty -m "vault: medida de la primera semana"

Sin dependencias: Python 3.8 o más nuevo. En Windows, `py` en lugar de `python3`.
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import revisar  # noqa: E402  las mismas respuestas y las mismas herramientas que mira revisar

DIAS = 7
MENSAJE = "vault: medida de la primera semana"
TIPOS = ("Principio", "Regla", "Elegí", "Descarté", "Corregí")
APUNTE = re.compile(r"^- \*\*({})\*\* ·".format("|".join(TIPOS)))


def git(raiz, *args):
    try:
        r = subprocess.run(["git", "-C", str(raiz)] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def guardados(raiz):
    """La fecha de cada commit, del primero al último. None si no hay git o no hay commits."""
    salida = git(raiz, "log", "--reverse", "--format=%ad", "--date=short")
    if not salida:
        return None
    return [date.fromisoformat(x) for x in salida.split()]


def ya_medido(raiz):
    salida = git(raiz, "log", "--format=%s") or ""
    return any(l.strip() == MENSAJE for l in salida.splitlines())


def toca(raiz, hoy):
    """(si toca medir, días desde que se montó el vault)."""
    fechas = guardados(raiz)
    if not fechas:
        return False, 0
    dias = (hoy - fechas[0]).days
    return dias >= DIAS and not ya_medido(raiz), dias


def proyectos(raiz):
    """(cuántos proyectos hay, cuántos tienen objetivo y fecha límite). Sin _plantilla.md."""
    carpeta = Path(raiz) / "proyectos"
    total = completos = 0
    for p in sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []:
        if p.name == "_plantilla.md":
            continue
        total += 1
        campos = {}
        for linea in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"- (objetivo|fecha límite):(.*)", linea)
            if m:
                campos[m.group(1)] = m.group(2).strip()
        if all(campos.get(c) and revisar.SIN_CONTESTAR not in campos[c] for c in ("objetivo", "fecha límite")):
            completos += 1
    return total, completos


def es_pregunta(lineas, i):
    """Las siete preguntas del montaje llevan su «*Pregunta:*» debajo: no son apuntes nuevos."""
    return i + 1 < len(lineas) and "*Pregunta:*" in lineas[i + 1]


def apuntes(raiz):
    """(apuntes nuevos, de ellos cuántos Corregí). Las siete preguntas del montaje no cuentan."""
    lineas = revisar.leer_texto(raiz, Path("criterio") / "apuntes.md").splitlines()
    nuevos = corregi = 0
    for i, linea in enumerate(lineas):
        m = APUNTE.match(linea)
        if not m or es_pregunta(lineas, i):
            continue
        nuevos += 1
        corregi += m.group(1) == "Corregí"
    return nuevos, corregi


def herramientas_propias(raiz):
    carpeta = Path(raiz) / "herramientas"
    de_void = revisar.de_void(raiz)
    return sum(1 for p in carpeta.glob("*.py") if p.name not in revisar.DE_LA_PLANTILLA
               and "herramientas/" + p.name not in de_void) if carpeta.is_dir() else 0


def comprobar(raiz):
    """(pasan las pruebas, revisar sale limpio)."""
    salida = []
    for programa in ("pruebas.py", "revisar.py"):
        r = subprocess.run([sys.executable, str(Path(raiz) / "herramientas" / programa)], cwd=str(raiz),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        salida.append(r.returncode == 0)
    return tuple(salida)


def version_void(raiz):
    try:
        datos = json.loads(revisar.leer_texto(raiz, "void.json") or "null")
    except ValueError:
        return None
    v = datos.get("base") if isinstance(datos, dict) else None
    return v if isinstance(v, str) and re.fullmatch(r"\d+(\.\d+)*", v) else None


def datos(raiz, hoy, comprobar_vault=comprobar):
    """Todo lo que lleva el bloque. Solo números, sí o no y la versión de Void."""
    fechas = guardados(raiz) or []
    pruebas, limpio = comprobar_vault(raiz)
    total, completos = proyectos(raiz)
    nuevos, corregi = apuntes(raiz)
    return {
        "dias": (hoy - fechas[0]).days if fechas else 0,
        "guardados": len(fechas),
        "dias_con_algo": len(set(fechas)),
        "proyectos": total,
        "con_objetivo_y_fecha": completos,
        "apuntes_nuevos": nuevos,
        "corregi": corregi,
        "sin_contestar": sum(1 for r in revisar.respuestas(raiz) if r is None),
        "herramientas": herramientas_propias(raiz),
        "pruebas": pruebas,
        "revisar": limpio,
        "void": version_void(raiz),
        "red": (Path(raiz) / ".void" / "llave").is_file(),
    }


def dias(n, distintos=False):
    return "{} día{}".format(n, (" distinto" if distintos else "")) if n == 1 else \
        "{} días{}".format(n, (" distintos" if distintos else ""))


def bloque(d):
    si_no = {True: "sí", False: "no"}
    return "\n".join([
        "Mi vault, a los {} de montarlo:".format(dias(d["dias"])),
        "- Guardados: {}, en {}.".format(d["guardados"], dias(d["dias_con_algo"], distintos=True)),
        "- Proyectos: {} (con objetivo y fecha: {}).".format(d["proyectos"], d["con_objetivo_y_fecha"]),
        "- Apuntes de criterio nuevos: {} (de tipo Corregí: {}).".format(d["apuntes_nuevos"], d["corregi"]),
        "- Preguntas del montaje sin contestar: {} de 7.".format(d["sin_contestar"]),
        "- Herramientas mías: {}.".format(d["herramientas"]),
        "- Pasan las pruebas: {}. Revisar sale limpio: {}.".format(si_no[d["pruebas"]], si_no[d["revisar"]]),
        "- Void: {}. En la red: {}.".format("base " + d["void"] if d["void"] else "sin conectar", si_no[d["red"]]),
        "- Con qué lo uso: [el agente que uses y si has conectado algo, como el correo o Drive]",
        "- Qué me ha ahorrado o resuelto: [tu respuesta]",
        "- Qué me ha estorbado, qué no entendí o dónde me atasqué: [tu respuesta]",
    ])


PARA_EL_AGENTE = """
Para el agente: rellena «Con qué lo uso» y pregúntale las dos últimas de una en una, esperando cada
respuesta. Ponlas tal cual; si sale una persona, cámbiala por su papel. Antes de dárselo, comprueba
que el bloque no lleva ningún nombre, correo, teléfono ni texto copiado de sus ficheros. Lo manda
ella, a quien le pasó Void, por donde quiera. Después: git commit --allow-empty -m "{}"
""".format(MENSAJE)


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    hoy = date.today()
    if "--hoy" in argv:
        i = argv.index("--hoy")
        try:
            hoy = date.fromisoformat(argv[i + 1])
        except (IndexError, ValueError):
            print("Así: --hoy 2026-10-15", file=sys.stderr)
            return 2
    if "--toca" in argv:
        si, dias = toca(RAIZ, hoy)
        if si:
            print("Toca medir: hace {} días que montaste el vault. Si quieres, «python3 herramientas/medir.py» "
                  "saca el bloque para mandarlo (solo cifras y tus respuestas).".format(dias))
        elif ya_medido(RAIZ):
            print("Ya mediste la primera semana.")
        else:
            print("Todavía no toca medir: el vault lleva {} días y se mide a los {}.".format(dias, DIAS))
        return 0
    print(bloque(datos(RAIZ, hoy)))
    print(PARA_EL_AGENTE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
