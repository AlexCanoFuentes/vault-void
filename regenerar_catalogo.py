#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rehace catalogo.json a partir de estrellas/: lo que lee void.py para traer una estrella y lo que
leerá la página de vaultvoid.app para buscarla.

Uso:
  python3 regenerar_catalogo.py              rehace catalogo.json
  python3 regenerar_catalogo.py --comprobar  no escribe; falla si catalogo.json no está al día

Cada estrella pasa antes por la puerta (sin ejecutar su prueba: eso lo hace Actions). Si una queda
rechazada, no se escribe nada. Lo que entra de cada estrella:
  - lo que se ve primero: la regla, los errores que la hicieron nacer, qué resuelve y el criterio;
  - con qué se busca: «cuando», las palabras clave y «buscar», todo junto en minúsculas y sin tildes;
  - liga y nivel, con el KERNEL crudo y la dimensión más débil;
  - con qué se trae: su ruta en el repo y la huella de cada fichero (void.py las comprueba).
"""
import json
import sys
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import formato  # noqa: E402
import puerta  # noqa: E402
import void  # noqa: E402

CATALOGO = "catalogo.json"
SE_COPIA = ("titulo", "version", "nivel", "autor", "regla", "resuelve", "nacio_de", "criterio", "cuando",
            "palabras_clave", "no_protege", "requisitos", "instalar", "probado_en", "riesgo", "prueba",
            "uso")


def para_buscar(ficha):
    """Todo lo que describe el error, junto, en minúsculas y sin tildes."""
    trozos = [ficha["titulo"], ficha["regla"], ficha["resuelve"]["frase"], ficha["resuelve"].get("medido", ""),
              ficha["criterio"]]
    for e in ficha["nacio_de"]:
        trozos += [e["fallo"], e["que_paso"]]
    trozos += ficha.get("cuando", []) + ficha.get("palabras_clave", [])
    texto = unicodedata.normalize("NFKD", " ".join(trozos).lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def generar(raiz, nombres=frozenset()):
    """(catálogo como dict, problemas). Con algún problema, el catálogo no se escribe."""
    raiz = Path(raiz)
    carpetas, problemas = puerta.todas(raiz)
    estrellas = {}
    for c in carpetas:
        v = puerta.juzgar(c, nombres=nombres)
        rel = c.relative_to(raiz).as_posix()
        if v["rechazo"]:
            problemas.append("{}: rechazada por la puerta ({})".format(rel, "; ".join(v["rechazo"])))
            continue
        ficha = formato.leer_ficha(c)
        if ficha["nombre"] in estrellas:
            problemas.append("{}: ya hay una estrella que se llama {} ({})".format(
                rel, ficha["nombre"], estrellas[ficha["nombre"]]["ruta"]))
            continue
        e = {k: ficha[k] for k in SE_COPIA if k in ficha}
        e["liga"] = v["liga"]
        e["kernel"] = v["kernel"]
        e["buscar"] = para_buscar(ficha)
        e["ruta"] = rel
        e["ficheros"] = dict(sorted(ficha["ficheros"].items()))
        e["no_se_instala"] = sorted(ficha.get("no_se_instala", []))
        e["huella_ficha"] = void.huella((c / formato.FICHA).read_bytes())
        estrellas[ficha["nombre"]] = e
    catalogo = {
        "aviso": "Lo genera regenerar_catalogo.py a partir de estrellas/. No se cambia a mano.",
        "formato": formato.FORMATO,
        "estrellas": dict(sorted(estrellas.items())),
    }
    return catalogo, problemas


def contenido(catalogo):
    return (json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main(argv, raiz=AQUI):
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    comprobar = "--comprobar" in argv
    catalogo, problemas = generar(raiz)
    if problemas:
        for p in problemas:
            print(p, file=sys.stderr)
        print("No escribo {}: arregla o retira lo de arriba.".format(CATALOGO), file=sys.stderr)
        return 1
    destino = Path(raiz) / CATALOGO
    nuevo = contenido(catalogo)
    n = len(catalogo["estrellas"])
    if comprobar:
        if not destino.is_file() or void.huella(destino.read_bytes()) != void.huella(nuevo):
            print("{} no está al día con estrellas/: corre python3 regenerar_catalogo.py".format(CATALOGO),
                  file=sys.stderr)
            return 1
        print("Catálogo al día ({} estrella{}).".format(n, "" if n == 1 else "s"))
        return 0
    destino.write_bytes(nuevo)
    print("Catálogo rehecho: {} estrella{}.".format(n, "" if n == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
