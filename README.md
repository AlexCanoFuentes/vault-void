# vault-void

El canal por el que un arreglo hecho una vez llega a todos los vaults.

- `base/`: lo que todos los vaults comparten. `base/MANIFIESTO.json` dice la versión de la base
  y la huella (sha256) de cada fichero.
- `void.py`: el cliente. Cada vault lleva una copia en `herramientas/void.py`.
- `estrellas/` y `catalogo.json`: el catálogo de estrellas (abajo).

## Qué lleva la base (0.0.9)

Incluye las reglas comunes, los candados y KERNEL con sus disparadores. Lo que cambia de un
vault a otro (el nombre, el idioma y el criterio propio) se queda en cada vault.

| Fichero | Qué es | Cómo se actualiza |
|---|---|---|
| `.codex/config.toml` | Los candados de Codex: escribe solo en la carpeta, sin internet, pide permiso | entero |
| `.claude/encerrado.json` | El encierro de Claude en Mac, Linux y WSL | entero |
| `AGENTS.md` | «Antes de nada, entres por donde entres» | solo entre las marcas |
| `CLAUDE.md` | La línea `@AGENTS.md` | solo entre las marcas |
| `herramientas/candados_comunes.py` | Los candados comunes de `revisar.py` (Codex encerrado, Claude lee `AGENTS.md`) | entero |
| `herramientas/pruebas_comunes.py` | Sus pruebas y su sabotaje, sacados de `pruebas.py` | entero |
| `herramientas/void.py` | Este cliente | entero |
| `herramientas/kernel.py` | Disparadores, rúbrica y registro de evaluaciones | entero |
| `herramientas/pruebas_kernel.py` | Sus pruebas y sabotajes | entero |
| `herramientas/kernel_ejemplo.json` | Ejemplo sin evidencia: rechazado, para escribir el encargo real | entero |

Al conectar un vault que ya tiene `AGENTS.md` o `CLAUDE.md`, si el tramo de la base está tal cual,
`void.py` le pone las marcas alrededor y no cambia nada más.

## La plantilla de un vault nuevo (0.0.9)

`plantilla/` es con lo que empieza un vault en una carpeta vacía (vaultvoid.app/empezar, abajo).
Es lo que tenían en común los tres primeros vaults, montados a mano el 1-oct, **sin nada de
ninguno**: ni nombres, ni oficios, ni ciudades, ni proyectos. Lo de cada persona lo pone ella al
contestar las siete preguntas.

| Fichero | De dónde sale |
|---|---|
| `README.md` | La forma de los tres: «Hoy» (12 líneas, se reescribe al cerrar), cómo se usa, mapa y qué no entra, con huecos `[sin contestar]` |
| `AGENTS.md`, `CLAUDE.md` | Las reglas que repetían los tres, con `{{nombre}}` donde iba el de cada uno, y el tramo de la base tal cual |
| `INBOX.md`, `criterio/decisiones.md` | Iguales en los tres, salvo una palabra |
| `criterio/apuntes.md` | La cabecera de los tres y las siete preguntas como huecos, con la redacción en que coincidían dos de los tres |
| `proyectos/_plantilla.md` | El molde por proyecto de dos de ellos (alias, fecha, estado) con los campos de objetivo y fecha límite del tercero |
| `.claude/commands/abrir.md`, `cerrar.md` | Los pasos de los tres; preguntar los huecos, de dos de ellos |
| `.claude/settings.json`, `encerrado-windows.json` | Los candados más completos de los tres, tal cual |
| `.gitignore`, `herramientas/revisar.py`, `pruebas.py` | `revisar` y sus pruebas con sabotaje de uno de ellos, con las extensiones de imagen, vídeo y audio de otro; sin el programa propio de nadie |

`plantilla/MANIFIESTO.json` lleva la huella de cada fichero. Lo rehace `regenerar_manifiesto.py`,
que antes pasa `fugas.py` por la plantilla con los nombres de `.fugas-nombres` y las palabras de
`.fugas-plantilla` (ciudades, oficios y proyectos de esos vaults, como sha256 y fuera de git):
si sale algo, no escribe nada.

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

Lo más fácil: abre tu agente (Claude Code, Codex, Antigravity) en la carpeta de tu vault y pégale
**«conéctate a Void: vaultvoid.app/entrar»**. Esa página es para el agente: comprueba que hay git y
Python, te pide permiso, baja `void.py`, comprueba su huella, conecta el vault y te explica cómo
deshacerlo. Su texto está en `web/entrar.md` (y en `web/entrar.html` y `web/entrar.txt`).

A mano, en una carpeta vacía o en un vault que aún no tiene `void.json`:

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

## La red: tu sitio en Void y los avisos (opcional)

Un vault conectado puede darse de alta en la red de Void con un alias y el nombre de su agente. **No sube nada del
vault:** Void guarda el alias, el nombre del agente y lo que tú marques como público.

```
python herramientas/void.py registrar --alias nube --agente Brock    # alta; la llave queda en .void/llave
python herramientas/void.py perfil --publico agente,estrellas         # qué enseña vaultvoid.app/@nube
python herramientas/void.py avisar candados gracias "me salvó el lunes"   # fallo, mejora o gracias
python herramientas/void.py estado                                    # incluye «Te han escrito»
python herramientas/void.py llave cambiar                             # si la llave se te escapa
python herramientas/void.py baja --si                                 # te borra de la red
```

- **La llave es tu credencial** (no hay correo ni contraseña) y **nunca entra en git**: antes de guardarla,
  `registrar` comprueba que git la ignora y, si no, añade `.void/` a tu `.gitignore` en un commit propio. Si aun así
  git la vería, no la guarda. Void solo guarda su huella.
- **Registrar dos veces no crea otro perfil:** con la llave en `.void/llave`, Void reconoce el vault. Sin ella, el
  alias ya está cogido.
- **Los avisos son públicos:** salen en `vaultvoid.app/estrella/<nombre>` con tu alias. Como mucho 10 por hora.
- El servidor está en [`red/`](red/README.md) (Cloudflare Workers + D1), con sus pruebas y cómo se despliega.

## Mensajes privados entre vaults [2026-10-10]

Los mensajes proponen, no ordenan. Antes de enviarlos, la persona debe revisar el texto entero y
autorizarlo. `autoriza` declara quién lo aprobó; no sustituye esa aprobación. Cada mensaje indica
qué espera de vuelta y no supera 6.000 caracteres completos. El cliente filtra credenciales
comunes; la persona sigue revisando qué contenido puede salir.

```
python herramientas/void.py escribir @otro --tipo PETICION --asunto "Revisión" --texto "¿Revisas la propuesta?" --devuelve "Un sí o un no" --autoriza "Nombre · persona"
python herramientas/void.py mensajes
python herramientas/void.py responder 42 --texto "Sí" --autoriza "Nombre · persona"
python herramientas/void.py bloquear @otro
```

HPKE Auth cifra y autentica el contenido; las claves conocidas se conservan y un cambio de clave
exige confirmación por otro canal. El servidor ve metadatos y ciphertext. El vínculo de una
respuesta al remitente del original se comprueba en el cliente, no en el servidor, que no ve ese
campo cifrado. Los archivos privados permanecen en `.void/`, fuera de git.

Datos, conservación y retirada: https://vaultvoid.app/privacidad. No hay una revisión externa de
seguridad ni una prueba de comportamiento con un asistente real ejecutada para esta entrega.

## Sin internet

Codex trabaja sin red. Si `actualizar` dice que no hay conexión, pide permiso de red para ese
comando o ejecútalo tú en una terminal.

## Para quien mantiene la base

```
python3 regenerar_manifiesto.py --version 0.0.9 --plantilla 0.0.9   # copia void.py a la base, rehace el manifiesto y pone
                                                # la huella de void.py en web/entrar.*
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

## Versiones e hitos [2026-10-10]

La revisión actual es **0.0.9, desarrollo**. `VERSION` identifica Void; los manifiestos de base y
plantilla y los paquetes de la red y antena llevan esta revisión. Las versiones de las estrellas
son independientes. No se incrementa la versión por cada arreglo.

- **0.0.x:** construcción y pruebas de desarrollo, sin prometer beta.
- **0.1.0:** beta con vaults reales conectados y un hito relevante confirmado por Alex. Un post de
  LinkedIn es una posibilidad, no publicación autorizada ni requisito suficiente por sí solo.
- **1.0.0:** horizonte de Void completo y lanzamiento en Play Store. No está cerca ni tiene fecha.
  Si la evidencia aconseja adelantar el hito, se propone a Alex y él decide.

Las numeraciones anteriores de dos componentes (`0.8`, `0.9`) no se reescriben en el historial.
El cliente compara igualdad de versiones y huellas, no orden numérico: puede actualizar esas
instalaciones a `0.0.9` conservando las modificaciones locales.

## KERNEL es parte de la base [2026-10-10]

Antes de construir, ampliar, cambiar permisos o datos, migrar, añadir salidas, preparar una
publicación, cambiar la base o resolver una contradicción del plan, evalúa el encargo. Una
consulta, captura o corrección menor sin esos cambios no exige evaluación. Las reglas completas
están en el tramo común de `AGENTS.md`.

```
python3 herramientas/kernel.py necesario --cambio construccion
python3 herramientas/kernel.py evaluar proyectos/encargo.kernel.json --registrar
python3 herramientas/pruebas_kernel.py
python3 herramientas/pruebas_kernel.py --sabotaje
```

Para escribir el JSON, copia `herramientas/kernel_ejemplo.json` a la ruta de tu encargo y
reemplaza el ejemplo por su objetivo, alcance, fuentes y las seis notas con sus razones. El
ejemplo obtiene cero y no permite construir. El programa calcula el resultado, registra en
`criterio/kernel.jsonl` y devuelve un código distinto de cero si falta revisión. Una nota
suficiente permite construir; las pruebas y la revisión determinan si la entrega está lista.
KERNEL no da permiso para enviar, publicar ni gastar.

## Licencia

Apache-2.0 (`LICENSE`, aviso en `NOTICE`): puedes usar, cambiar y redistribuir Void, también en tu trabajo, conservando el aviso.
El servicio de la nube (tu vault vivo) no forma parte de este repositorio.
