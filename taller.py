#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La nebulosa: el taller donde algo de tu vault se convierte en una estrella.

Uso, con la carpeta de lo que quieres compartir:
  python taller.py CARPETA                      repasa la carpeta y dice qué le falta
  python taller.py CARPETA --nivel socio --autor TU_USUARIO_DE_GITHUB

Hace, en este orden y sin tocar nada fuera de la carpeta (como mucho, escribe en ella un borrador de
estrella.json si no lo tiene):
  1. Limpieza: busca nombres de personas, correos, teléfonos, claves y rutas de tu máquina. Lo que se
     publica no puede llevar nada tuyo. Si tienes una lista privada de nombres, ponla en .fugas-nombres
     junto a este fichero (ver fugas.py).
  2. La ficha: si no hay estrella.json, escribe un borrador con lo que ya se sabe y te dice qué rellenar.
  3. El vault vacío: la copia a una carpeta nueva, como si fuera un vault recién creado, y ejecuta su
     prueba ahí. Tiene que funcionar sin nada tuyo alrededor.
  4. La puerta: la misma que juzga el catálogo, con su nota de 0 a 100 y lo que más la hunde.
  5. Qué falta: en una lista corta, en palabras normales.

Nace del 5-oct-2026 [Alex: «podemos tener una estrella que sirva para depurar tus estrellas?»]: lo que
se le pidió a mano a la primera estrella de un socio (quitar su voz, su marca y sus cifras, escribir el
error que la hizo nacer, probarla en un vault vacío) lo hace una herramienta. Es una capa de Void, no
una estrella: la necesita cualquiera que cree.

Solo biblioteca estándar. Reutiliza formato.py, fugas.py y puerta.py: un solo criterio, no dos.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import formato  # noqa: E402
import fugas    # noqa: E402
import puerta   # noqa: E402

PENDIENTE = "PENDIENTE: "


def limpieza(carpeta, nombres=frozenset()):
    """[(fichero, línea, qué es, trozo tapado)] de lo que no puede publicarse."""
    hallazgos = []
    todos = fugas.NOMBRES | set(nombres)
    for p in sorted(carpeta.rglob("*")):
        rel = p.relative_to(carpeta)
        if any(parte in formato.IGNORAR_DIRS for parte in rel.parts) or not p.is_file():
            continue
        for n, tipo, trozo in fugas.revisar_texto(rel.as_posix(), todos):
            hallazgos.append(("nombre del fichero " + rel.as_posix(), n, tipo, trozo))
        datos = p.read_bytes()
        if b"\0" in datos[:8000]:
            continue
        for n, tipo, trozo in fugas.revisar_texto(datos.decode("utf-8", "replace"), todos):
            hallazgos.append((rel.as_posix(), n, tipo, trozo))
    return hallazgos


def borrador(carpeta, nivel, autor):
    """La ficha mínima, con lo que se sabe y PENDIENTE donde hace falta la persona."""
    return {
        "formato": formato.FORMATO,
        "nombre": carpeta.name,
        "titulo": PENDIENTE + "un nombre corto, hasta 80 caracteres",
        "version": "0.1.0",
        "nivel": nivel,
        "autor": autor or PENDIENTE + "tu usuario de GitHub",
        "regla": PENDIENTE + "la regla que impone, en imperativo (por ejemplo: «Ninguna cifra sale sin su fuente»)",
        "resuelve": {"frase": PENDIENTE + "qué resuelve, en una frase", "medido": PENDIENTE + "cómo sabes que lo resuelve, con números"},
        "nacio_de": [{"fallo": PENDIENTE + "uno de: " + ", ".join(formato.FALLOS),
                      "que_paso": PENDIENTE + "qué pasó, sin nombres ni cifras tuyas",
                      "coste": PENDIENTE + "uno de: " + ", ".join(formato.COSTES)}],
        "criterio": PENDIENTE + "la decisión de diseño que hace que funcione",
        "ficheros": {},
    }


def en_vault_vacio(carpeta, ficha):
    """Copia la estrella a un vault recién creado y ejecuta su prueba ahí. None si pasa, o el motivo."""
    if "prueba" not in ficha:
        return "no tiene prueba: añade «prueba» con el comando que demuestra que funciona"
    return puerta.ejecutar_prueba(carpeta, ficha)


def repasar(carpeta, nivel="comunidad", autor=None, nombres=frozenset(), escribir=True):
    """Lo que se le enseña a la persona: {"pasos": [(nombre, ok, detalle)], "falta": [...], "lista": bool}."""
    carpeta = Path(carpeta).resolve()
    pasos, falta = [], []
    if not carpeta.is_dir():
        return {"pasos": [("La carpeta", False, "no existe: {}".format(carpeta))], "falta": ["una carpeta que exista"], "lista": False}

    # 1 · limpieza
    h = limpieza(carpeta, nombres)
    if h:
        pasos.append(("1 · Limpieza", False, "{} cosa(s) tuya(s) que no pueden salir:".format(len(h))))
        for donde, n, tipo, trozo in h[:12]:
            pasos.append(("", False, "    {}:{} · {} · {}".format(donde, n, tipo, trozo)))
        falta.append("quitar lo que la limpieza ha encontrado")
    else:
        pasos.append(("1 · Limpieza", True, "no lleva nombres, correos, teléfonos, claves ni rutas de tu máquina"))

    # 2 · la ficha
    fichero = carpeta / formato.FICHA
    if not fichero.exists():
        if nivel not in formato.NIVELES:
            nivel = "comunidad"
        if escribir:
            fichero.write_text(json.dumps(borrador(carpeta, nivel, autor), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            formato.rehacer_huellas(carpeta)
        pasos.append(("2 · La ficha", False, "no tenía estrella.json: te he dejado un borrador. Rellena lo que pone PENDIENTE"))
        falta.append("rellenar lo que pone PENDIENTE en estrella.json")
    try:
        ficha = formato.leer_ficha(carpeta)
    except ValueError as e:
        pasos.append(("2 · La ficha", False, "no se puede leer: {}".format(e)))
        return {"pasos": pasos, "falta": falta + ["que estrella.json sea JSON válido"], "lista": False}
    pendientes = [k for k, v in ficha.items() if PENDIENTE in json.dumps(v, ensure_ascii=False)]
    if pendientes:
        pasos.append(("2 · La ficha", False, "sin rellenar: " + ", ".join(pendientes)))
        if "rellenar lo que pone PENDIENTE en estrella.json" not in falta:
            falta.append("rellenar lo que pone PENDIENTE en estrella.json")

    # La forma y la puerta se miran sobre una copia con la estructura del catálogo (estrellas/<nivel>/<nombre>),
    # así se juzga igual que se juzgará al publicar, sin mover tu carpeta.
    tmp = Path(tempfile.mkdtemp(prefix="nebulosa-"))
    try:
        nv = ficha.get("nivel") if ficha.get("nivel") in formato.NIVELES else "comunidad"
        copia = tmp / "estrellas" / nv / carpeta.name
        shutil.copytree(str(carpeta), str(copia), ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
        errores = [e for e in formato.validar(copia, ficha) if not pendientes or PENDIENTE not in e]
        if not pendientes:
            if errores:
                pasos.append(("2 · La ficha", False, "tiene la forma mal:"))
                pasos += [("", False, "    " + e) for e in errores[:10]]
                falta.append("arreglar la forma de la ficha (ver estrellas/FORMATO.md)")
            else:
                pasos.append(("2 · La ficha", True, "completa y con la forma buena"))

        # 3 · el vault vacío
        motivo = en_vault_vacio(copia, ficha)
        if motivo:
            pasos.append(("3 · Vault vacío", False, motivo))
            falta.append("que su prueba pase en un vault recién creado")
        else:
            pasos.append(("3 · Vault vacío", True, "su prueba pasa en un vault recién creado, sin nada tuyo alrededor"))

        # 4 · la puerta
        if pendientes or errores:
            pasos.append(("4 · La puerta", False, "se pasa cuando la ficha esté completa"))
        else:
            v = puerta.juzgar(copia, nombres=frozenset(nombres))
            if v["rechazo"]:
                pasos.append(("4 · La puerta", False, "la rechaza:"))
                pasos += [("", False, "    " + m) for m in v["rechazo"][:10]]
                falta.append("lo que dice la puerta")
            else:
                k = v["kernel"]
                d = k["mas_debil"]
                pts, maximo = k["dimensiones"][d]
                liga = "grande" if v["liga"] == "grande" else "pequeña"
                pasos.append(("4 · La puerta", v["liga"] == "grande",
                              "{} de 100 · iría a la liga {} · lo que más la hunde: {} ({} de {})".format(k["total"], liga, d, pts, maximo)))
                if v["liga"] != "grande":
                    falta.append("subir {} para llegar a 80 y entrar en la liga grande".format(d))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    return {"pasos": pasos, "falta": falta, "lista": not falta}


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
    def opcion(nombre, defecto=None):
        if nombre in args:
            i = args.index(nombre)
            valor = args[i + 1] if i + 1 < len(args) else defecto
            del args[i:i + 2]
            return valor
        return defecto
    nivel = opcion("--nivel", "comunidad")
    autor = opcion("--autor")
    r = repasar(args[0], nivel=nivel, autor=autor)
    print("La nebulosa · {}\n".format(Path(args[0]).name))
    for paso, ok, detalle in r["pasos"]:
        marca = "" if not paso else ("  ok   " if ok else "  falta")
        print("{} {}  {}".format(marca, paso, detalle) if paso else detalle)
    print()
    if r["lista"]:
        print("Lista para publicar. Cópiala a estrellas/{}/{}/ en tu copia de Void y abre un pull request.".format(nivel, Path(args[0]).name))
        return 0
    print("Le falta:")
    for f in r["falta"]:
        print("  · " + f)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
