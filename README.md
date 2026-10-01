# vault-void

El canal por el que un arreglo hecho una vez llega a todos los vaults.

- `base/`: lo que todos los vaults comparten. `base/MANIFIESTO.json` dice la versión de la base
  y la huella (sha256) de cada fichero.
- `void.py`: el cliente. Cada vault lleva una copia en `herramientas/void.py`.

## Qué lleva la base (0.1)

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
```
