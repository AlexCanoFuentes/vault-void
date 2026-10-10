#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KERNEL común: decide cuándo evaluar y calcula la rúbrica de construcción.

Las notas y sus razones las propone quien revisa el encargo, no el programa.
El resultado permite construir; no sustituye pruebas, revisión ni permiso humano.
Python 3.8+, sin dependencias. Rúbrica de construcción de AICODE v2.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

RUBRICA = (
    ("clarity", 20, "Objetivo inequívoco en una frase"),
    ("scope", 20, "Inclusiones y exclusiones explícitas"),
    ("context", 15, "Ficheros, dependencias y decisiones previas"),
    ("risk", 15, "Riesgos identificados y mitigados"),
    ("validation", 15, "Aceptación verificable y reproducible"),
    ("priority", 15, "Avanza un objetivo activo o desbloquea su camino"),
)
DISPARADORES = frozenset(("construccion", "ampliacion", "permisos", "datos", "migracion",
                          "salida", "publicacion", "base", "contradiccion"))
SIN_EVALUACION = frozenset(("consulta", "captura", "correccion-menor"))
RAIZ = Path(__file__).resolve().parent.parent


def necesario(cambios):
    """Una corrección deja de ser menor si además cambia datos, permisos o alcance."""
    if not isinstance(cambios, list) or not cambios or any(not isinstance(c, str) or c not in DISPARADORES | SIN_EVALUACION for c in cambios):
        raise ValueError("declara al menos un cambio de la lista; no se adivina por el texto")
    return bool(DISPARADORES.intersection(cambios))


def evaluar(d):
    if not isinstance(d, dict):
        raise ValueError("la evaluación debe ser un objeto JSON")
    for campo in ("objeto", "alcance", "fuentes"):
        if not isinstance(d.get(campo), str) or not d[campo].strip():
            raise ValueError("falta {} y su evidencia".format(campo))
    cambios = d.get("cambios")
    if not isinstance(cambios, list) or not necesario(cambios):
        raise ValueError("esta evaluación debe declarar un disparador de KERNEL")
    dimensiones = d.get("dimensiones")
    if not isinstance(dimensiones, dict) or set(dimensiones) != {n for n, _, _ in RUBRICA}:
        raise ValueError("usa las seis dimensiones de la rúbrica, sin inventar ni quitar ninguna")
    valores = []
    for nombre, peso, _ in RUBRICA:
        dato = dimensiones[nombre]
        if not isinstance(dato, dict) or type(dato.get("nota")) is not int or not 0 <= dato["nota"] <= peso:
            raise ValueError("{}: nota entera entre 0 y {}".format(nombre, peso))
        if not isinstance(dato.get("porque"), str) or not dato["porque"].strip():
            raise ValueError("{}: explica la nota y qué falta".format(nombre))
        valores.append((nombre, dato["nota"], peso))
    total = sum(v for _, v, _ in valores)
    estado = "EXECUTE" if total >= 80 else "CONDICIONAL" if total >= 60 else "RECHAZADO"
    riesgo_bajo = dimensiones["risk"]["nota"] < 9
    if estado == "EXECUTE" and riesgo_bajo:
        estado = "REVISION_DE_RIESGO"
    debil = min(valores, key=lambda x: (x[1] / x[2], x[1]))
    return {"total": total, "maximo": sum(p for _, p, _ in RUBRICA), "estado": estado,
            "dimension_mas_debil": debil[0], "riesgo_bajo": riesgo_bajo,
            "puede_construir": estado == "EXECUTE"}


def ruta_local(raiz, relativa):
    raiz = Path(raiz).resolve()
    p = Path(relativa)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("la ruta debe ser relativa al vault, sin salir de él")
    destino = raiz / p
    try:
        destino.resolve().relative_to(raiz)
    except ValueError:
        raise ValueError("la ruta sale del vault a través de un enlace")
    for paso in (destino,) + tuple(destino.parents):
        if paso == raiz:
            break
        if paso.is_symlink():
            raise ValueError("no se leen ni escriben evaluaciones a través de enlaces")
    return destino


def registrar(raiz, d, resultado):
    destino = ruta_local(raiz, "criterio/kernel.jsonl")
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Lee el registro entero antes de añadir; un registro roto no se sustituye.
    if destino.exists():
        for linea in destino.read_text(encoding="utf-8").splitlines():
            if linea.strip() and not isinstance(json.loads(linea), dict):
                raise ValueError("el registro anterior no es válido; se conserva sin escribir")
    apunte = {"fecha": datetime.now(timezone.utc).isoformat(),
              "tipo": "valoracion-del-encargo", "evaluacion": d, "resultado": resultado}
    with destino.open("a", encoding="utf-8") as f:
        f.write(json.dumps(apunte, ensure_ascii=False, sort_keys=True) + "\n")
    return destino


def main(argv=None, raiz=RAIZ):
    p = argparse.ArgumentParser(description=__doc__)
    ordenes = p.add_subparsers(dest="orden", required=True)
    necesidad = ordenes.add_parser("necesario", help="comprueba los disparadores declarados")
    necesidad.add_argument("--cambio", action="append", required=True,
                           choices=sorted(DISPARADORES | SIN_EVALUACION))
    nota = ordenes.add_parser("evaluar", help="evalúa un encargo escrito en un JSON del vault")
    nota.add_argument("entrada", help="ruta relativa al vault del JSON con alcance, fuentes y seis razones")
    nota.add_argument("--registrar", action="store_true", help="añade el resultado a criterio/kernel.jsonl")
    args = p.parse_args(argv)
    try:
        if args.orden == "necesario":
            print("KERNEL NECESARIO" if necesario(args.cambio) else "KERNEL NO NECESARIO: continúa el trabajo autorizado")
            return 0
        entrada = ruta_local(raiz, args.entrada)
        d = json.loads(entrada.read_text(encoding="utf-8"))
        r = evaluar(d)
        print("KERNEL {}/{} · {}".format(r["total"], r["maximo"], r["estado"]))
        nombre = r["dimension_mas_debil"]
        pesos = {n: peso for n, peso, _ in RUBRICA}
        print("Dimensión más débil: {} {}/{}".format(nombre, d["dimensiones"][nombre]["nota"], pesos[nombre]))
        for n, peso, _ in RUBRICA:
            print("{} {}/{}: {}".format(n, d["dimensiones"][n]["nota"], peso, d["dimensiones"][n]["porque"]))
        if args.registrar:
            registrar(raiz, d, r)
            print("Registrado en criterio/kernel.jsonl; no sale del vault.")
        print("Las notas son una valoración. KERNEL no da permiso para publicar, gastar ni dar una entrega por terminada.")
        return 0 if r["puede_construir"] else 3 if r["estado"] in ("CONDICIONAL", "REVISION_DE_RIESGO") else 4
    except (OSError, ValueError, UnicodeError) as e:
        print("KERNEL SE NIEGA: {}".format(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
