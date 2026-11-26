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
# No hay stack por defecto: cada construcción declara qué usa en cada pieza, frente a qué y por qué. Si para la misma pieza ya
# se eligió otra cosa, separarse exige decir por qué (así «el mejor para cada cosa» no acaba en un stack distinto por repo).
CON_STACK = frozenset(("construccion", "ampliacion", "migracion"))
# Las piezas son una lista cerrada (revisión de Codex, 26-nov: con nombres libres, llamar «Persistencia» a «Datos» saltaba la
# comparación). Lo concreto va en «para»; una pieza que no está aquí es «otra» con su nombre, y se dice.
PIEZAS = ("lenguaje", "datos", "ficheros", "servidor", "interfaz", "acceso", "pruebas", "despliegue",
          "modelo", "entrenamiento", "agentes", "otra")
RAIZ = Path(__file__).resolve().parent.parent


def necesario(cambios):
    """Una corrección deja de ser menor si además cambia datos, permisos o alcance."""
    if not isinstance(cambios, list) or not cambios or any(not isinstance(c, str) or c not in DISPARADORES | SIN_EVALUACION for c in cambios):
        raise ValueError("declara al menos un cambio de la lista; no se adivina por el texto")
    return bool(DISPARADORES.intersection(cambios))


def _pieza(s):
    return " ".join(str(s).lower().split())


def _texto(x):
    return isinstance(x, str) and bool(x.strip())


def _clave(s):
    return "otra:" + _pieza(s.get("nombre", "")) if s["pieza"] == "otra" else s["pieza"]


def revisar_stack(d, anteriores):
    """Comprueba el stack declarado y lo compara con lo elegido antes (y aprobado) para las mismas piezas."""
    stack = d.get("stack")
    if not isinstance(stack, list) or not stack:
        raise ValueError("una construcción declara su stack: lista de piezas con eleccion, alternativas y porque")
    vistas = set()
    for i, s in enumerate(stack):
        if not isinstance(s, dict) or not all(_texto(s.get(k)) for k in ("pieza", "eleccion", "porque")):
            raise ValueError("stack[{}]: pieza, eleccion y porque, con texto".format(i))
        if s["pieza"] not in PIEZAS:
            raise ValueError("stack[{}]: la pieza es una de {} (lo concreto va en «para»)".format(i, ", ".join(PIEZAS)))
        if s["pieza"] == "otra" and not _texto(s.get("nombre")):
            raise ValueError("stack[{}]: una pieza «otra» lleva su nombre".format(i))
        if s["pieza"] == "otra" and _pieza(s["nombre"]) in PIEZAS:
            raise ValueError("stack[{}]: «{}» ya es una pieza: úsala, no «otra»".format(i, s["nombre"]))
        for campo in ("para", "nombre", "distinto_porque"):
            if campo in s and not isinstance(s[campo], str):
                raise ValueError("stack[{}]: {} es texto".format(i, campo))
        alt = s.get("alternativas")
        if not isinstance(alt, list) or not alt or not all(_texto(a) for a in alt):
            raise ValueError("{}: di frente a qué se eligió (alternativas, al menos una)".format(s["pieza"]))
        clave = _clave(s)
        if (clave, _pieza(s["eleccion"])) in vistas:
            raise ValueError("{}: {} repetido en el stack".format(s["pieza"], s["eleccion"]))
        vistas.add((clave, _pieza(s["eleccion"])))
        antes = anteriores.get(clave) or []
        if antes and _pieza(s["eleccion"]) not in {_pieza(a["eleccion"]) for a in antes} and not _texto(s.get("distinto_porque")):
            raise ValueError("{}: hasta hoy se eligió {}; di por qué ahora {} (distinto_porque)".format(
                s["pieza"], ", ".join(sorted({a["eleccion"] for a in antes})), s["eleccion"]))


def elecciones(raiz):
    """Lo elegido para cada pieza en evaluaciones registradas que permitieron construir (lo rechazado no cuenta)."""
    destino = ruta_local(raiz, "criterio/kernel.jsonl")
    hechas = {}
    if not destino.exists():
        return hechas
    for linea in destino.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        a = json.loads(linea)
        ev = a.get("evaluacion") if isinstance(a, dict) else None
        res = a.get("resultado") if isinstance(a, dict) else None
        if not isinstance(ev, dict) or not isinstance(ev.get("stack"), list) or not (isinstance(res, dict) and res.get("puede_construir") is True):
            continue
        for s in ev["stack"]:
            if isinstance(s, dict) and s.get("pieza") in PIEZAS and _texto(s.get("eleccion")):
                nombre = s["pieza"] + (": " + s["nombre"] if s["pieza"] == "otra" and isinstance(s.get("nombre"), str) else "")
                hechas.setdefault(_clave(s), []).append({"pieza": nombre, "eleccion": s["eleccion"], "para": s.get("para", "") if isinstance(s.get("para"), str) else "",
                    "porque": s.get("porque", ""), "fecha": str(a.get("fecha", "")), "objeto": ev.get("objeto", "")})
    return hechas


def evaluar(d, anteriores=None):
    if not isinstance(d, dict):
        raise ValueError("la evaluación debe ser un objeto JSON")
    for campo in ("objeto", "alcance", "fuentes"):
        if not isinstance(d.get(campo), str) or not d[campo].strip():
            raise ValueError("falta {} y su evidencia".format(campo))
    cambios = d.get("cambios")
    if not isinstance(cambios, list) or not necesario(cambios):
        raise ValueError("esta evaluación debe declarar un disparador de KERNEL")
    if CON_STACK.intersection(cambios) or "stack" in d:   # un stack presente se valida siempre, lo pida el cambio o no
        revisar_stack(d, anteriores or {})
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
    ver = ordenes.add_parser("stack", help="lo elegido hasta hoy para cada pieza (del registro)")
    ver.add_argument("pieza", nargs="?", help="solo las piezas que contengan este texto")
    args = p.parse_args(argv)
    try:
        if args.orden == "necesario":
            print("KERNEL NECESARIO" if necesario(args.cambio) else "KERNEL NO NECESARIO: continúa el trabajo autorizado")
            return 0
        if args.orden == "stack":
            hechas = [x for clave, xs in sorted(elecciones(raiz).items()) for x in xs
                      if not args.pieza or _pieza(args.pieza) in clave]
            for x in hechas:
                print("{} · {}{} · {} ({}): {}".format(x["pieza"], x["eleccion"], " para " + x["para"] if x["para"] else "",
                                                       x["fecha"][:10], x["objeto"], x["porque"]))
            if not hechas:
                print("Nada elegido todavía{}.".format(" para «{}»".format(args.pieza) if args.pieza else ""))
            return 0
        entrada = ruta_local(raiz, args.entrada)
        d = json.loads(entrada.read_text(encoding="utf-8"))
        anteriores = elecciones(raiz)
        r = evaluar(d, anteriores)
        print("KERNEL {}/{} · {}".format(r["total"], r["maximo"], r["estado"]))
        nombre = r["dimension_mas_debil"]
        pesos = {n: peso for n, peso, _ in RUBRICA}
        print("Dimensión más débil: {} {}/{}".format(nombre, d["dimensiones"][nombre]["nota"], pesos[nombre]))
        for n, peso, _ in RUBRICA:
            print("{} {}/{}: {}".format(n, d["dimensiones"][n]["nota"], peso, d["dimensiones"][n]["porque"]))
        for s in d.get("stack") or []:
            cambio = " · distinto de lo elegido antes: {}".format(s["distinto_porque"]) if _texto(s.get("distinto_porque")) else ""
            print("stack · {}: {} (frente a {}){}".format(s["pieza"], s["eleccion"], ", ".join(s["alternativas"]), cambio))
        if args.registrar:
            registrar(raiz, d, r)
            print("Registrado en criterio/kernel.jsonl; no sale del vault.")
        elif CON_STACK.intersection(d["cambios"]) and r["puede_construir"]:
            # Sin registrar, lo elegido no queda para la próxima: una construcción solo vale registrada.
            print("KERNEL: una construcción solo vale registrada (--registrar), para que la próxima vea lo elegido.", file=sys.stderr)
            return 5
        print("Las notas son una valoración. KERNEL no da permiso para publicar, gastar ni dar una entrega por terminada.")
        return 0 if r["puede_construir"] else 3 if r["estado"] in ("CONDICIONAL", "REVISION_DE_RIESGO") else 4
    except (OSError, ValueError, UnicodeError) as e:
        print("KERNEL SE NIEGA: {}".format(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
