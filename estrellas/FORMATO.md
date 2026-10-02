# El formato de una estrella

Una **estrella** es una herramienta, plantilla o invento que alguien hizo en su vault y comparte en
Void. No se publica por lo que hace, sino por **el error que la hizo nacer**: la línea que solo sabe
escribir quien se estrelló. Sin esa línea no entra.

Cada estrella es una carpeta `estrellas/<nivel>/<nombre>/` con sus ficheros y un `estrella.json`.

- **Niveles** (quién la hizo): `oficiales` > `socio` > `comunidad`. El nivel es la carpeta.
- **Ligas** (cuánto vale): la **grande**, si pasa KERNEL con 80 o más; la **pequeña**, si no. Lo
  decide `puerta.py`, no quien publica.

## Lo que NO lleva una estrella

**Ni datos del usuario ni conexiones con su vault.** Ni nombres de personas, ni correos, ni
teléfonos, ni claves, ni rutas de su máquina (`/home/...`, `C:\Users\...`), ni nada que lea su vault.
Tiene que funcionar en un vault recién creado. La historia del error se cuenta como **tipo de fallo
y regla**, sin quién, sin cliente y sin cifras suyas. Si quieres probar que la historia existe sin
enseñarla, pon su sha256 en `huella_historia` y guárdala en tu vault.

## `estrella.json`, campo a campo

Ningún campo más que estos: uno desconocido es un rechazo (así no se cuela nada por un campo nuevo).

### Obligatorios (sin ellos, la puerta la rechaza)

| Campo | Qué es |
|---|---|
| `formato` | `1` |
| `nombre` | igual que su carpeta: minúsculas, cifras y guiones |
| `titulo` | hasta 80 caracteres |
| `version` | como `0.1.0`. Si cambian los ficheros, cambia la versión |
| `nivel` | `oficiales`, `socio` o `comunidad`; igual que la carpeta de encima |
| `autor` | su usuario de GitHub |
| `regla` | **la restricción, en imperativo.** Lo primero que se ve en el catálogo |
| `resuelve` | `{"frase": "qué resuelve, en una frase", "medido": "cómo se sabe, con números"}` |
| `nacio_de` | **la lista de errores que la hicieron nacer.** Cada uno: `{"fallo": <lista cerrada>, "que_paso": "qué pasó, sin nombres", "coste": <lista cerrada>}` |
| `criterio` | el criterio importante: la decisión de diseño que la hace funcionar |
| `ficheros` | `{"ruta": "sha256"}` de **todos** los ficheros de la carpeta menos `estrella.json`. Ni uno de más ni uno de menos |

### Opcionales (no la rechazan; los mira KERNEL)

| Campo | Qué es |
|---|---|
| `cuando` | el momento de trabajo en que muerde el error (lista cerrada). Es por donde la encuentra el buscador |
| `palabras_clave` | cómo lo diría alguien a quien le pasa |
| `no_protege` | lo que NO hace. Una estrella honesta lo dice |
| `requisitos` | qué necesita para funcionar |
| `instalar` | los pasos, uno por línea, después de traerla |
| `probado_en` | dónde se ha visto funcionar |
| `riesgo` | `{"ejecuta": "qué corre en tu máquina y cuándo", "red": "si usa internet y para qué", "deshacer": "cómo se quita"}` |
| `prueba` | `{"comando": ["python", "<fichero>", ...], "comprobaciones": n, "rojos": n, "sabotaje": "cómo se ha visto fallar sin la cura"}` |
| `vive_en` | `"fichero:línea"`: dónde vive la regla en el código. Tiene que existir |
| `uso` | `{"vaults": n, "semanas": n, "nota": "..."}`: quién la usa ya, medido |
| `no_se_instala` | ficheros que viajan con la estrella pero no se copian al vault (un README, por ejemplo) |
| `huella_historia` | sha256 de la historia completa, que se queda en tu vault |

### Las listas cerradas

Son comunes a todo el ecosistema. Crecen por pull request a este fichero y a `formato.py`.

- **`fallo`**: dato inventado · límite sin comprobar · se coló algo privado · regla que solo vive en
  un documento · comprobación que no puede fallar · decidir por la persona · dato caducado ·
  construir sin definir lo que se construye.
- **`cuando`**: al empezar · antes de construir · construyendo · al publicar · al vender · al cobrar ·
  con un tercero · al cerrar.
- **`coste`**: minutos · horas · días · dinero · un tercero · sin medir.

## La puerta (`puerta.py`)

Primero, lo que es **rechazo** (no entra en ninguna liga):

1. El formato no vale (`formato.py`): falta un obligatorio, sobra un campo, un fichero no cuadra con
   su huella, o hay uno que no está en la lista.
2. No sale limpia: `fugas.py` encuentra un secreto, un correo, un teléfono o un nombre de persona, o
   aparece una ruta de la máquina de alguien.
3. En GitHub Actions, además: su `prueba` no pasa, o cambian los ficheros y no la versión.

Después, **KERNEL**: las seis dimensiones de la rúbrica de AICODE (`skills/kernel/REFERENCE.md`),
con sus pesos, leídas de lo que la estrella declara. Umbral **80**, sin redondear.

| Dimensión | Peso | La pregunta, para una estrella | Cómo se puntúa |
|---|---|---|---|
| Claridad | 20 | ¿Se entiende en una frase qué error resuelve y cuándo muerde? | `regla` en una frase de hasta 200 caracteres (6) · `resuelve.frase` de hasta 200 (4) · `cuando` (6) · 3 o más `palabras_clave` (4) |
| Alcance | 20 | ¿Dice qué hace y qué no? | `no_protege` con algo (10) · con 3 o más (4) · `requisitos` (6) |
| Contexto | 15 | ¿Otro la instala y la termina sin preguntar? | `instalar` (6) · un `README.md` entre sus ficheros (5) · `probado_en` (4) |
| Riesgo | 15 | ¿Dice qué ejecuta en tu máquina, si usa la red y cómo se quita? | `riesgo.ejecuta` (5) · `riesgo.red` (5) · `riesgo.deshacer` (5) |
| Validación | 15 | ¿Se puede ver la cura funcionando? | `prueba.comando` (5) · `prueba.rojos` de 1 o más (4) · `prueba.sabotaje` (3) · `vive_en` (3) |
| Prioridad | 15 | ¿Cuánto cuesta el error y quién la usa ya? | `coste` del error: días, dinero o un tercero (5), horas (3), minutos (1), sin medir (0) · usada en 1 vault o más (5) · durante 4 semanas o más (5) |

- **80 o más → liga grande. Menos de 80 → liga pequeña**, con el número y la dimensión más débil.
  La puerta no dice cómo subir: eso lo hace cada uno con el kernel de su vault.
- **Lo que esta puerta NO comprueba:** que lo declarado sea verdad. Puntúa lo que la estrella dice
  de sí misma; lo único que verifica de verdad son las huellas, la limpieza, que `vive_en` exista y,
  en Actions, que la `prueba` pase. Por eso las estrellas de la comunidad se leen antes de ejecutar.

## Publicar una estrella

```
python3 formato.py --huellas estrellas/<nivel>/<nombre>    # apunta la huella de cada fichero
python3 puerta.py estrellas/<nivel>/<nombre>               # rechazo, liga pequeña o liga grande
python3 regenerar_catalogo.py                              # rehace catalogo.json
```

Y un pull request. Actions vuelve a pasar la puerta, con la prueba ejecutada.
