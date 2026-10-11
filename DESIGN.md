---
name: "Vault Void"
description: "Huellas de colores sobre carbón cálido, con una interfaz sobria y legible."
colors:
  vacio: "#12110E"
  panel: "rgba(24,22,18,.92)"
  panel-solido: "#1B1915"
  tinta: "#ECE7DE"
  tinta-2: "#B3AC9F"
  tenue: "#8C8578"
  linea: "#2E2B25"
  linea-cuento: "#2B2822"
  linea-vault: "#38332B"
  ambar: "#F2A93B"
  ambar-2: "#F8CB86"
  verde: "#5BE06A"
  tinta-accion-portada: "#1A1407"
  tinta-accion-espacio: "#1A1206"
typography:
  display:
    fontFamily: '"Instrument Serif", Georgia, serif'
    fontSize: "clamp(34px,5vw,52px)"
    fontWeight: 400
    lineHeight: 1.1
  headline-cuento:
    fontFamily: '"Instrument Serif", Georgia, "Times New Roman", serif'
    fontSize: "clamp(26px,7vw,40px)"
    fontWeight: 400
    lineHeight: 1.12
  marca-portada:
    fontFamily: '"Instrument Serif", Georgia, "Times New Roman", serif'
    fontSize: "38px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "-.01em"
  titulo-ficha:
    fontFamily: '"Instrument Serif", Georgia, "Times New Roman", serif'
    fontSize: "24px"
    fontWeight: 400
    lineHeight: 1.1
  body:
    fontFamily: '"IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  body-cuento:
    fontFamily: '"IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  body-espacio:
    fontFamily: '"IBM Plex Mono", monospace'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.65
rounded:
  pildora: "999px"
  campo: "10px"
  menu: "14px"
  ficha: "12px"
  hoja: "18px"
spacing:
  grupo-8: "8px"
  grupo-10: "10px"
  interior-12: "12px"
  margen-16: "16px"
  interior-18: "18px"
  identidad-24: "24px"
components:
  boton-primario-portada:
    backgroundColor: "{colors.ambar}"
    textColor: "{colors.tinta-accion-portada}"
    rounded: "{rounded.pildora}"
    padding: "9px 18px"
  boton-secundario-portada:
    backgroundColor: "transparent"
    textColor: "{colors.tinta}"
    rounded: "{rounded.pildora}"
    padding: "8px 16px"
  campo-acceso:
    backgroundColor: "{colors.vacio}"
    textColor: "{colors.tinta}"
    typography: "{typography.body-espacio}"
    rounded: "{rounded.campo}"
    padding: "12px"
    width: "100%"
  menu-flotante:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.tinta}"
    typography: "{typography.body}"
    rounded: "{rounded.menu}"
    width: "min(360px,calc(100% - 32px))"
  ficha-huella:
    backgroundColor: "{colors.panel-solido}"
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.ficha}"
    padding: "14px 16px"
    width: "min(300px,calc(100% - 32px))"
---

# Design System: Vault Void

## Overview

**Creative North Star: "El lienzo de huellas"**

[CONF] Void conserva su mundo visual existente: un fondo de carbón cálido y huellas orgánicas de muchos colores. Instrument Serif da voz a los títulos y IBM Plex Mono ordena la interfaz. El ámbar señala las acciones, mientras el color personal vive principalmente en la huella.

[CONF] La interfaz permanece sobria para que el lienzo tenga presencia sin competir con las palabras. Los paneles flotantes usan bordes tenues y fondos cálidos; el espacio de conversaciones adapta la misma identidad a una columna de lectura. La huella mantiene su semilla y tono al regresar, en vez de estrenar una identidad visual.

**Key Characteristics:**

- Carbón cálido y texto claro, con jerarquía de tres intensidades.
- Títulos serif ligeros e interfaz monoespaciada.
- Ámbar para actuar y verde en el énfasis del cuento.
- Huellas orgánicas multicolor con identidad persistente.
- Bordes finos y superficies sin sombras.

Fuente y fecha: 2026-10-11. Extracción de `web/index.html`, `web/tu-huella.html`, `web/mi-vault.html` y `web/huella.js`, contrastada con `PRODUCT.md` y `.impeccable/direccion.md`. Los valores del frontmatter son normativos para esta captura; el CSS del producto sigue siendo la fuente de ejecución. No se han normalizado las diferencias entre pantallas.

Límites de fidelidad: documento obtenido del código, sin una nueva revisión de estilos computados ni de capturas por esta agente. Los ejemplos del sidecar reproducen cinco componentes reales, sin el anclaje fijo de pantalla ni las conexiones de datos. No representan la animación completa del lienzo. No hay una imagen de diseño aprobada.

## Colors

La paleta de interfaz combina cálidos casi negros, tintas de papel y ámbar; la huella aporta la variedad cromática.

### Primary

- **Ámbar de acción**, `ambar`: fondo de la acción principal, foco y selección. `ambar-2` aclara el enlace y el hover de la acción principal de portada.
- **Tinta de acción**, `tinta-accion-portada` y `tinta-accion-espacio`: texto oscuro sobre ámbar. Son dos valores existentes, no una escala nueva.

### Secondary

- **Verde del cuento**, `verde`: énfasis en cursiva de los titulares del recorrido de creación.

### Neutral

- **Carbón cálido**, `vacio`: fondo de pantalla y de los campos del espacio.
- **Panel cálido**, `panel`: menú translúcido de portada. El cuento usa su propia transparencia sobre el panel sólido, declarada en su CSS.
- **Panel sólido**, `panel-solido`: ficha de huella y superficies del espacio.
- **Tinta clara**, `tinta`: lectura principal.
- **Tinta secundaria**, `tinta-2`: explicación y texto auxiliar.
- **Tinta tenue**, `tenue`: pistas y metadatos, sin sustituir etiquetas necesarias.
- **Líneas cálidas**, `linea`, `linea-cuento` y `linea-vault`: separación de portada, cuento y espacio, respectivamente. Se conserva la variación observada.

**The Color de la huella Rule.** La variedad cromática pertenece a la huella; no convierte toda la interfaz en una colección de acentos.

La paleta personal no es una lista fija de tokens. `huella.js` genera cuatro tonos a partir del tono persistido y la semilla: desplazamiento de matiz de 55 grados en uno de los dos sentidos, saturación alternada (0,72 y 0,70) y luminosidad alternada (0,60 y 0,62). El color se mezcla sobre el fondo según la química y el pulso. El cuento también tiene siete tintas de pregunta antes de consolidar la huella. No se documentan rampas sintéticas como si estuvieran implementadas.

## Typography

**Display Font:** Instrument Serif, con Georgia y los fallbacks declarados por pantalla.

**Body Font:** IBM Plex Mono, con los fallbacks monoespaciados del frontmatter.

**Character:** títulos ligeros, a menudo con una palabra en cursiva, junto a una interfaz monoespaciada de lectura tranquila. La portada delinea la palabra «Void» con un trazo de tinta; el cuento colorea el énfasis en verde.

### Hierarchy

- **Display**, `display`: título principal del espacio. En móvil, el título de identidad tiene una regla específica de menor tamaño.
- **Headline**, `headline-cuento`: voz centrada del cuento, con ancho máximo de 18em y equilibrio de líneas.
- **Marca**, `marca-portada`: nombre del menú. Se reduce con el menú plegado y en móvil.
- **Title**, `titulo-ficha`: alias o título de la ficha flotante.
- **Body**, `body`, `body-cuento` y `body-espacio`: tres ajustes existentes para portada, cuento y conversaciones.
- **Label:** botones y nombres destacados usan peso 500; los metadatos de portada usan tamaños de 11px a 13px. No hay una escala de etiquetas unificada.

**The Dos voces Rule.** Conserva Instrument Serif para los títulos e IBM Plex Mono para controles, campos y lectura de interfaz.

## Layout

La portada ocupa la pantalla con un canvas fijo. El menú se ancla abajo a la izquierda con margen de 16px y contempla las áreas seguras. Su interior se desplaza cuando no cabe. Los mandos viven arriba a la derecha y la ficha se posiciona junto a la huella seleccionada, limitada por los bordes de la pantalla.

A 700px o menos, el menú usa márgenes de 12px y altura máxima del 62% de la pantalla; su inicialización se pliega por debajo de 700px. La explicación y las acciones principales permanecen visibles. El encuadre del lienzo reserva espacio para el menú, a su derecha en escritorio y por encima en móvil.

El cuento coloca la voz arriba y los controles abajo. El campo ocupa hasta 560px y la huella se centra en el espacio que queda entre ambos. La hoja de respuestas usa hasta 560px y un máximo de 62vh. Los pasos de alta y código permiten desplazamiento en la zona inferior hasta 70dvh.

El espacio usa un contenedor de 1040px, con acceso de hasta 520px y padding horizontal adaptable. La identidad dispone de huella y texto en dos columnas. A 560px o menos, la huella pasa de 120px a 72px y la separación de identidad de 24px a 14px. Los mensajes limitan su altura a 52dvh, o 46dvh en móvil; las conversaciones se desplazan horizontalmente.

Los grupos usan separaciones cortas de 8px y 10px. El aire de paneles, campos e identidad corresponde a los pasos observados del frontmatter; no existe una escala global en CSS que obligue a todos los contextos a usar el mismo padding.

## Elevation & Depth

No hay sombras CSS en las pantallas estudiadas. La profundidad nace del lienzo de fondo, los paneles cálidos translúcidos o sólidos, los bordes finos y el orden de superposición. No hay desenfoque de fondo. La gravedad es un modo opcional del lienzo y está apagada por defecto.

El encuadre de portada viaja durante 650ms con desaceleración cúbica; voz y pista cambian de opacidad durante 0,8s. Las preferencias de movimiento reducido eliminan las transiciones CSS y varias animaciones del recorrido. Estas duraciones describen comportamientos concretos, no una escala universal.

**The Profundidad sin sombra Rule.** Conserva la separación por tono, borde y superposición que ya usa Void.

## Shapes

Las acciones de portada y cuento tienen silueta de píldora. Los botones del espacio usan un radio de 24px. Los campos del espacio y los mandos tienen esquinas suaves, mientras menú, ficha y hoja conservan radios distintos según su tamaño. El textarea del cuento tiene radio de 26px.

Las huellas tienen territorio circular y contornos orgánicos producidos por reacción y difusión. Los sitios todavía vacíos aparecen como círculos de línea discontinua. Los pequeños puntos de color identifican huellas o respuestas; no son una nueva familia de insignias.

## Components

### Botón primario de portada

Acción visible y directa. Usa ámbar, tinta oscura, peso 500 y forma de píldora. Al pasar el puntero cambia a ámbar claro. El foco visible usa contorno de ámbar (2px) con separación de 2px. El cuento y el espacio tienen sus propios paddings y estados deshabilitados en su CSS; no se sustituyen por esta variante.

### Botón secundario de portada

Acción de contorno. Conserva fondo transparente, tinta clara y borde fino. Hover y estado expandido cambian el borde a ámbar; el foco comparte el tratamiento global de portada.

### Campo de acceso

Campo completo con etiqueta visible, fondo de carbón y borde del espacio. Usa el radio y padding del frontmatter. El foco tiene contorno de ámbar (2px) separado 3px. Los campos de contraseña mantienen su semántica; la búsqueda y el textarea del cuento son variantes específicas con otro tratamiento.

### Menú flotante

Puerta al lienzo en un panel cálido de contorno fino. La marca serif, la explicación monoespaciada y las acciones ocupan la cabecera. Las secciones usan `details` con indicador de apertura y separación por líneas; el botón de plegado reduce el menú conservando explicación y acciones. En el sidecar se muestra una muestra estática del contenido y una sección nativa desplegable.

### Ficha de huella

Ficha compacta y sólida cerca de la huella elegida. Presenta un título serif y texto secundario; cuando tiene cifras, las alinea en dos columnas con números tabulares. Se cierra con un botón de esquina y puede enlazar al sitio correspondiente. La muestra del sidecar usa el estado real «Una huella que empieza» y no simula cifras ni identidad de terceros.

## Do's and Don'ts

### Do:

- **Do** conservar el carbón cálido, el ámbar de acción y la jerarquía de tintas de las pantallas existentes.
- **Do** mantener la semilla y el tono personal de la huella al regresar.
- **Do** dar etiquetas visibles a los campos y conservar el foco de teclado.
- **Do** reservar espacio legible para palabras y controles alrededor del lienzo.
- **Do** respetar las variaciones de radios, bordes y tipografía documentadas por pantalla.

### Don't:

- **Don't** sustituir el mundo existente por una identidad nueva.
- **Don't** añadir estrellas de fondo, nebulosas ni halos a la portada.
- **Don't** convertir la paleta multicolor de huellas en acentos decorativos de toda la interfaz.
- **Don't** añadir sombras o desenfoque como si pertenecieran al sistema observado.
- **Don't** presentar los ejemplos estáticos como una reproducción completa del lienzo o de su persistencia.
