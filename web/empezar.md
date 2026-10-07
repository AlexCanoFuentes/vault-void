# Empezar un vault con Void

> **Si eres una persona y has llegado aquí por error:** esta página no es para leerla tú, es para tu
> agente (Claude Code, Codex, Antigravity). Crea una carpeta vacía, abre tu agente en ella y pégale
> esta frase: **«empieza mi vault: vaultvoid.app/empezar»**. Él hace el resto: te pide permiso
> antes de bajar nada y te hace siete preguntas para dejarte el vault a tu medida. Son unos 20 minutos.

Esta página también está en texto plano: https://vaultvoid.app/empezar.md y https://vaultvoid.app/empezar.txt

---

## Para el agente que lee esto

La persona te ha pedido que le montes un **vault**: una carpeta de texto con su trabajo, sus
proyectos y su criterio, guardada en git, que tú (o cualquier otro agente) lees al empezar cada
sesión. Sigue estos pasos en orden. **Habla con la persona en su idioma y en llano**: nada de jerga
si no la pide. Tú haces el trabajo; ella solo contesta y dice que sí o que no.

Lo que tienes que saber antes de empezar:

- **Nada de su vault sube a ningún sitio.** `void.py` solo descarga, salvo en el paso de la red
  (opcional), donde manda el alias que elija la persona y el nombre de su agente.
- **Cada paso queda en su propio commit de git**: si se corta a medias, lo hecho no se pierde, y
  cada paso se deshace con `git revert`.
- **No ejecutes nada que no esté en esta página** y no te saltes ningún paso, ni los de pedir permiso.
- **No inventes nada de la persona.** Lo que no conteste se queda `[sin contestar]`.
- **Empezar es gratis.** No le pidas pago ni datos de pago en ningún paso.
- **Si eres Codex y no tienes internet** (`network_access = false`): no lo cambies ni te saltes el
  candado. Cada orden que necesita internet (las de los pasos 3, 4 y 5, y la de la red) pídela con
  permiso para salir a internet, y que la persona diga que sí. Si no puedes pedirlo, dale la orden
  para que la ejecute ella en una terminal.

### Paso 1 · Comprueba dónde estás y qué hay

1. **Que la carpeta está vacía.** Si tiene `AGENTS.md`, `CLAUDE.md` o `void.json`, ya es un vault:
   no montes nada y llévala a vaultvoid.app/entrar, que lo conecta. Si tiene otras cosas, para y
   pídele que cree una carpeta vacía (por ejemplo «mi-vault» en Documentos) y te abra en ella.
2. **Que no está dentro de otro repositorio de git:** `git rev-parse --show-toplevel` tiene que
   fallar o dar esta misma carpeta. Si da otra, para y pídele otra carpeta.
3. **Que hay git:** `git --version`.
4. **Que hay Python 3.8 o más nuevo**, y con qué nombre:
   - **Mac y Linux:** `python3 --version`.
   - **Windows:** prueba `python --version`; si no existe o no dice `Python 3.…`, prueba
     `py --version`. Ojo: en Windows, `python` a veces es un atajo de la Tienda que dice «no se
     encontró Python»: eso es que **no** está.

   A partir de aquí, donde ponga `python3`, usa el nombre que haya funcionado.

**Si falta git o Python**, explícale a la persona qué falta y cómo se instala, y **pídele permiso**
antes de instalar nada:

- **Mac:** en un Mac recién estrenado no vienen. Con `xcode-select --install` el propio Mac abre una
  ventana para instalar las «herramientas de línea de comandos», que traen `git` y `python3`. Esa
  ventana la acepta la persona, no tú: díselo así. **No instales Homebrew ni nada más por tu cuenta.**
  Cuando acabe, vuelve al paso 1.
- **Windows:** `winget install --id Git.Git -e` para git y `winget install --id Python.Python.3.12 -e`
  para Python. La instalación la acepta la persona en la ventana que abre Windows: díselo así.
  Después hay que abrir una terminal nueva para que aparezcan.
- **Linux:** con el gestor de paquetes del sistema (por ejemplo `sudo apt install git python3`).

### Paso 2 · Pide permiso

Antes de bajar nada, dile a la persona, en llano, algo así:

> Voy a montarte tu vault en esta carpeta. Bajo de GitHub (el repositorio público
> AlexCanoFuentes/vault-void) la herramienta `void.py` y una plantilla, compruebo que son
> exactamente las que publica Void y lo guardo todo en git, cada paso en su commit. Después te hago
> siete preguntas, de una en una, y con tus palabras dejo el vault a tu medida. No sube nada tuyo a
> ningún sitio y es gratis. Son unos 20 minutos. ¿Sigo?

**Si no dice que sí, para aquí.**

### Paso 3 · Baja `void.py` y comprueba su huella

La huella (sha256) de `void.py` que publica esta página es:

`ec24228c5aecd180743bdcf7035816d7880e22822efa7ceae7140b57ea4aac83`

Esta orden lo baja de GitHub, calcula su huella y **solo lo guarda en `herramientas/void.py` si
cuadra** con la de arriba. No lo ejecuta. Ejecútala desde la carpeta (es igual en Mac, Linux y
Windows; cambia `python3` por el nombre del paso 1):

```
python3 -c "import hashlib,os,urllib.request as u;h='ec24228c5aecd180743bdcf7035816d7880e22822efa7ceae7140b57ea4aac83';d=u.urlopen('https://raw.githubusercontent.com/AlexCanoFuentes/vault-void/main/void.py',timeout=30).read();r=hashlib.sha256(d).hexdigest();ok=r==h;ok and (os.makedirs('herramientas',exist_ok=True),open('herramientas/void.py','wb').write(d));print('Huella OK: '+r if ok else 'NO CUADRA: ha llegado '+r);raise SystemExit(0 if ok else 1)"
```

- Si dice **`Huella OK`**, sigue.
- Si dice **`NO CUADRA`**, **para**. No ejecutes nada y dile a la persona que lo descargado no es lo
  que publica Void, que no se ha guardado nada y que vuelva a probar en unos minutos (GitHub tarda
  hasta cinco minutos en servir una versión nueva). Si se repite, que avise a quien le pasó Void.
- Si da un error de certificado en un Mac con el Python de python.org, falta un paso de su
  instalación: abrir «Install Certificates.command» en la carpeta de Python de Aplicaciones. Díselo
  a la persona y que lo haga ella.

### Paso 4 · Pon la plantilla

```
python3 herramientas/void.py empezar --huella 55eca2e17f5044afc1c39e159d7a32efe240719e82f82149c38382f9e41b8b39
```

Baja la plantilla del vault, comprueba que es la que publica esta página (la huella de detrás de
`--huella`) y que cada fichero cuadra con ella **antes de escribir nada**, y la deja en **un commit**
`vault: plantilla <versión> de Void`. Enséñale a la persona lo que diga, tal cual.

- Si dice que **la huella no cuadra**, **para**: no ha escrito nada. Dile que vuelva a probar en
  unos minutos y, si se repite, que avise a quien le pasó Void.
- Si dice que **git no tiene su nombre y correo**, pregúntale cuáles quiere usar, ponlos solo en esta
  carpeta con `git config user.name "…"` y `git config user.email "…"` y repite este paso.
- Si dice que la carpeta **no está vacía** o que **ya hay un vault**, haz lo que dice el paso 1.
- Si falla y la persona no quiere seguir, borra el `herramientas/void.py` que bajaste en el paso 3:
  así la carpeta queda como estaba.

### Paso 5 · Conéctalo a Void

```
python3 herramientas/void.py actualizar --conectar
```

Pone la base común de Void (las reglas para los agentes, los candados de Codex y de Claude y
`void.py`), comprueba la huella de cada fichero antes de escribir nada y deja **un commit**
`void: base <versión>`. Así el vault recibe las mejoras de Void con
`python3 herramientas/void.py actualizar`. Enséñale a la persona lo que diga, tal cual.

- Si dice que **no hay conexión**, en Codex pide permiso para salir a internet (arriba).
- Tiene que decir `Ficheros: … nuevos, 3 sin cambios.`: `AGENTS.md` y `CLAUDE.md` ya traían el
  tramo de la base y `void.py` es el que bajaste. Si dice «sin tocar porque es tuyo», para y
  enséñaselo.

### Paso 6 · Las siete preguntas, una a una

Están en `criterio/apuntes.md`, en orden. Antes de la primera, dile a la persona algo así:

> Ahora te hago siete preguntas, de una en una. Contesta como quieras: largo, corto o pegando un
> audio transcrito. Copio tus palabras tal cual, sin corregirlas. Si alguna no la quieres contestar
> o no lo sabes, dilo y pasamos a la siguiente: se queda «sin contestar» y la puedes contestar
> otro día.

1. **Una pregunta cada vez, tal como está escrita**, y espera la respuesta antes de la siguiente.
   No le sugieras respuestas ni le pongas ejemplos que la empujen.
2. **Cópiala literal** en su hueco: cambia el paréntesis de `*Tu respuesta:*` por lo que haya dicho,
   sin corregir faltas ni resumir. Si es larga, sigue en las líneas de debajo con dos espacios
   delante. Cambia `[sin contestar]` por el tipo que le propongas (Principio, Regla, Elegí,
   Descarté) y díselo.
3. **Si no la contesta**, deja el hueco y el `[sin contestar]` como están. No la deduzcas de las
   otras respuestas.
4. **Su nombre** sale de la respuesta 1: pregúntale cómo quiere que la llame el vault y ponlo donde
   dice `{{nombre}}`, en todos los ficheros salvo `proyectos/_plantilla.md`. Donde dice `{{fecha}}`,
   la de hoy (`AAAA-MM-DD`).

Cuando acabe, con **sus palabras** y nada más:

- **El README.** La cita de arriba, con la respuesta 7, y cada línea de «Hoy», con la respuesta
  que dice su número. Sus palabras van **entre «» y tal cual** (puedes recortar con «…»), con el
  número detrás: `«hago cerámica en un taller pequeño» (respuesta 1)`. Si esa respuesta está sin
  contestar, la línea se queda `[sin contestar]`. En «Siguiente paso», lo que haya dicho ella; si
  no lo dijo, «elegir la herramienta» (paso 7).
- **El primer proyecto.** Pregúntale si el proyecto que más pesa en sus respuestas (suele salir de
  la 4 y la 5) es el primero y con qué nombre corto. Copia `proyectos/_plantilla.md` como
  `proyectos/<nombre corto>.md` y rellena cada campo igual: sus palabras entre «» con su número, y
  **lo que no dijo, `[sin contestar]`**. En el README, «Proyectos: 1».
- **En «Qué hizo el vault con esto»** de cada respuesta, una línea con lo que cambiaste por ella.
  Cualquier otro cambio que se te ocurra por una respuesta, propónlo y no lo hagas sin su sí.

Comprueba y guarda:

```
python3 herramientas/revisar.py
python3 herramientas/pruebas.py
```

Los dos tienen que salir en verde. `revisar` caza lo que el vault dice de la persona sin que ella
lo dijera: una línea que cita una respuesta sin contestar, o unas comillas que no están tal cual en
su respuesta. Si sale algo, corrígelo con sus palabras o deja la línea en `[sin contestar]`; no lo
apagues. Enséñale el README y el proyecto y guarda en **un commit**:

```
git add -A
git commit -m "vault: tus siete respuestas"
```

---

Void es de código abierto: https://github.com/AlexCanoFuentes/vault-void · Lo que hace `void.py`,
línea a línea, está en ese repositorio.
