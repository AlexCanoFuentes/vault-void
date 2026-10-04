# vault-void

El canal por el que un arreglo hecho una vez llega a todos los vaults.

- `base/`: lo que todos los vaults comparten. `base/MANIFIESTO.json` dice la versión de la base
  y la huella (sha256) de cada fichero.
- `void.py`: el cliente. Cada vault lleva una copia en `herramientas/void.py`.
- `estrellas/` y `catalogo.json`: el catálogo de estrellas (abajo).

## Qué lleva la base (0.2)

Solo lo que los vaults ya compartían **tal cual**, sacado de ellos y no reescrito. Es poco a
propósito: lo que cambia de un vault a otro (el nombre, el idioma, las herramientas de cada uno)
se queda en cada vault.

| Fichero | Qué es | Cómo se actualiza |
|---|---|---|
| `.codex/config.toml` | Los candados de Codex: escribe solo en la carpeta, sin internet, pide permiso | entero |
| `.claude/encerrado.json` | El encierro de Claude en Mac, Linux y WSL | entero |
| `AGENTS.md` | «Antes de nada, entres por donde entres» | solo entre las marcas |
| `CLAUDE.md` | La línea `@AGENTS.md` | solo entre las marcas |
| `herramientas/candados_comunes.py` | Los candados comunes de `revisar.py` (Codex encerrado, Claude lee `AGENTS.md`) | entero |
| `herramientas/pruebas_comunes.py` | Sus pruebas y su sabotaje, sacados de `pruebas.py` | entero |
| `herramientas/void.py` | Este cliente | entero |

Al conectar un vault que ya tiene `AGENTS.md` o `CLAUDE.md`, si el tramo de la base está tal cual,
`void.py` le pone las marcas alrededor y no cambia nada más.

## Uso, desde la carpeta del vault

```
python herramientas/void.py estado
python herramientas/void.py actualizar
```

En Windows, si `python` no existe, con `py`. Solo usa la biblioteca estándar de Python 3.8 o más
nuevo, y `git`.

- **`estado`** dice qué versión de la base tienes, si hay una nueva y qué ficheros de la base has
  cambiado tú.
- **`actualizar`** descarga la base de GitHub, comprueba cada fichero contra su huella antes de
  escribir nada, y deja **un commit** `void: base <versión>`. Para deshacerlo: `git revert HEAD`.
- **No pisa lo tuyo.** Si cambiaste un fichero de la base, no lo toca: deja la versión nueva al
  lado, como `<fichero>.base-nueva`, y te lo dice.
- **En los `.md`**, la base solo es lo que va entre `<!-- base:inicio -->` y `<!-- base:fin -->`.
  Lo de fuera de esas marcas es tuyo y no se toca nunca.
- **Nunca ejecuta lo que descarga.** Solo lo escribe, y solo dentro del vault.

## Conectar un vault por primera vez

En una carpeta vacía o en un vault que aún no tiene `void.json`:

```
python void.py actualizar --conectar --vault <carpeta del vault>
```

## Estrellas: traer una y publicar una

Una **estrella** es una herramienta que alguien hizo en su vault, publicada con **el error que la
hizo nacer**. Vive en `estrellas/<nivel>/<nombre>/` (oficiales > socio > comunidad) y
`catalogo.json` la lista con su liga: la **grande** si pasa KERNEL con 80 o más, la **pequeña** si
no. El formato campo a campo y la rúbrica, en [`estrellas/FORMATO.md`](estrellas/FORMATO.md).

**Traer una**, desde la carpeta del vault (hace falta la base 0.2: antes, `actualizar`):

```
python herramientas/void.py traer candados
```

Comprueba la huella de cada fichero contra el catálogo antes de escribir nada, y la deja en **un
commit** `void: estrella candados 0.2.0`. Para deshacerlo: `git revert HEAD`. No pisa lo tuyo, ni lo
de la base, ni lo de otra estrella: deja la versión nueva al lado, como `<fichero>.base-nueva`. **No
ejecuta nada**: al terminar te dice los pasos para ponerla en marcha. En un vault sin `void.json`,
con `--conectar`. Las de la comunidad, léelas antes de ejecutar nada de ellas.

**Publicar una:**

```
python3 formato.py --huellas estrellas/<nivel>/<nombre>       # la huella de cada fichero
python3 puerta.py estrellas/<nivel>/<nombre> --ejecutar       # rechazada, liga pequeña o liga grande
python3 regenerar_catalogo.py                                 # rehace catalogo.json
```

Y un pull request: GitHub Actions repite las pruebas, `fugas.py` y la puerta, con su prueba
ejecutada. Si cambias una estrella que ya está, sube su versión.

## Sin internet

Codex trabaja sin red. Si `actualizar` dice que no hay conexión, pide permiso de red para ese
comando o ejecútalo tú en una terminal.

## Para quien mantiene la base

```
python3 regenerar_manifiesto.py --version 0.2   # copia void.py a la base y rehace el manifiesto
python3 pruebas.py                              # pruebas
python3 pruebas.py --sabotaje                   # rompe cada candado y comprueba que las pruebas lo cazan
python3 pruebas.py --vaults <copia1> <copia2>   # 0.1 -> 0.2 -> revert sobre copias de vaults reales
python3 fugas.py                                # secretos, correos, teléfonos y nombres: tiene que dar 0
python3 puerta.py --todas                       # todas las estrellas por la puerta
python3 regenerar_catalogo.py --comprobar       # catalogo.json al día con estrellas/
```

## La nebulosa: convertir algo de tu vault en una estrella

Si algo te ha funcionado en tu vault y quieres compartirlo, pásalo por el taller:

```
python taller.py tu-carpeta
```

Busca lo tuyo que no puede salir (nombres, correos, teléfonos, claves, rutas de tu máquina), te deja un
borrador de la ficha si no la tiene, la prueba en un vault vacío, le pasa la puerta y te dice qué le falta
para entrar en el catálogo. No toca nada fuera de esa carpeta.
