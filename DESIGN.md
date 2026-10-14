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
  headline-conexion:
    fontFamily: '"Instrument Serif", Georgia, serif'
    fontSize: "clamp(34px,6vw,52px)"
    fontWeight: 400
    lineHeight: 1.1
  body-conexion:
    fontFamily: '"IBM Plex Mono", monospace'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.7
rounded:
  pildora: "999px"
  campo: "10px"
  menu: "14px"
  ficha: "12px"
  hoja: "18px"
  orden: "6px"
  utilidad: "8px"
  boton-espacio: "24px"
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
  campo-conexion:
    backgroundColor: "{colors.panel-solido}"
    textColor: "{colors.tinta}"
    typography: "{typography.body-conexion}"
    rounded: "{rounded.campo}"
    padding: "12px"
    width: "100%"
  boton-primario-espacio:
    backgroundColor: "{colors.ambar}"
    textColor: "{colors.tinta-accion-espacio}"
    rounded: "{rounded.boton-espacio}"
    padding: "11px 18px"
  mando-regresar:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.tinta-2}"
    rounded: "{rounded.campo}"
    padding: "0 10px"
    height: "36px"
---

# Design System: Vault Void

## Overview

**Creative North Star: "El lienzo de huellas"**

Void conserva su mundo visual existente: un fondo de carbón cálido y huellas orgánicas de muchos colores. Instrument Serif da voz a los títulos y IBM Plex Mono ordena la interfaz. El ámbar señala las acciones, mientras el color personal vive principalmente en la huella.

La interfaz permanece sobria para que el lienzo tenga presencia sin competir con las palabras. Los paneles flotantes usan bordes tenues y fondos cálidos; el espacio de conversaciones adapta la misma identidad a una columna de lectura. La huella mantiene su semilla y tono al regresar, en vez de estrenar una identidad visual.

El vacío de portada se puede recorrer en cualquier dirección, sin borde de atlas ni sitios reservados. La superficie de experiencia deja espacio al plano y sus huellas reales; conectar un vault existente o a medida usa una columna operativa legible dentro de la misma identidad. El alcance infinito es espacial, sin rellenar el mundo con vaults inventados. Cada huella tiene sitio y textura propios aunque comparta semilla visual con otra; al vincularse, la huella del cuento conserva su forma y tono y toma el sitio del perfil.

**Key Characteristics:**

- Carbón cálido y texto claro, con jerarquía de tres intensidades.
- Títulos serif ligeros e interfaz monoespaciada.
- Ámbar para actuar y verde en el énfasis del cuento.
- Huellas orgánicas multicolor con identidad persistente.
- Bordes finos y superficies sin sombras.
- Plano navegable sin bordes, con regreso visible y movimiento reducido.

Fuente y fecha: 2026-10-11. Fusión con la captura anterior del cuento y extracción de `web/index.html`, `web/vacio.js`, `web/conectar-vault.html`, `web/conectar-vault.js`, `web/mi-vault.html` y `web/huella.js`, contrastada con `PRODUCT.md` y `.impeccable/direccion.md`. Los valores del frontmatter son normativos para esta captura; el CSS del producto sigue siendo la fuente de ejecución. No se han normalizado las diferencias entre pantallas.

Límites de fidelidad: extracción del código contrastada con capturas existentes en `.impeccable/review/ampliacion/`, sin una nueva auditoría ni revisión de estilos computados. Las capturas usan datos inventados para pruebas locales, no usuarios reales. La revisión previa terminó con veredicto `ship` tras resolver el placeholder de conexión y la selección con movimiento reducido; ese cierre de correcciones no acredita otros servicios. Los ejemplos del sidecar reproducen componentes reales sin anclaje fijo, backend ni animación completa. El mundo se dibuja con canvas nativo; no hay comp aprobada ni imágenes nuevas.

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
- **Headline de conexión**, `headline-conexion`: entrada de la columna para vaults existentes o a medida, con énfasis serif en cursiva.
- **Headline**, `headline-cuento`: voz centrada del cuento, con ancho máximo de 18em y equilibrio de líneas.
- **Marca**, `marca-portada`: nombre del menú. Se reduce con el menú plegado y en móvil.
- **Title**, `titulo-ficha`: alias o título de la ficha flotante.
- **Body**, `body`, `body-cuento`, `body-espacio` y `body-conexion`: ajustes existentes para portada, cuento, conversaciones y conexión.
- **Label:** botones y nombres destacados usan peso 500. En portada, pie y pista usan 11px, contadores y mandos 12px, explicación y ficha 13px, y el cierre de ficha 18px. La marca móvil expandida usa 30px. Son usos concretos, sin escala de etiquetas unificada. Los subtítulos del espacio y conexión usan serif de 28px; conexión los espacia con margen superior de 36px.

**The Dos voces Rule.** Conserva Instrument Serif para los títulos e IBM Plex Mono para controles, campos y lectura de interfaz.

## Layout

La portada ocupa la pantalla con un canvas fijo. El menú se ancla abajo a la izquierda con margen de 16px y contempla las áreas seguras. Su interior se desplaza cuando no cabe. Los mandos viven arriba a la derecha y la ficha se posiciona junto a la huella seleccionada, limitada por los bordes de la pantalla.

El plano carece de marco o casillas. Las posiciones siguen una espiral estable según la posición recibida: ángulo de 2,399963229728653 radianes por posición y radio de 330 por su raíz cuadrada. La API asigna el doble del identificador del perfil, o el doble del identificador del cuento más uno si todavía no tiene perfil; pares e impares separan ambos espacios. La semilla define la forma, no identifica el sitio ni la textura. Semilla, tono y datos se conservan; las coordenadas permanecen estables mientras se conserve el identificador. Al vincularse, una huella del cuento toma el sitio del perfil. La separación contempla la textura completa de 220px y su respiración máxima (1,024). La portada consume todas las páginas de huellas y solo dibuja las cercanas al encuadre. La caché de texturas usa la posición única y tiene un máximo de 12 entradas; al alejarse, o mientras falta textura, una huella se representa como punto de su propio color. Esta reducción de detalle no reserva huecos ni crea vaults.

A 700px o menos, el menú usa márgenes de 12px y altura máxima del 62% de la pantalla; su inicialización se pliega por debajo de 700px. La explicación y las tres acciones principales permanecen visibles: crear, volver y conectar. El encuadre del lienzo reserva espacio para el menú, a su derecha en escritorio y por encima en móvil.

El cuento coloca la voz arriba y los controles abajo. El campo ocupa hasta 560px y la huella se centra en el espacio que queda entre ambos. La hoja de respuestas usa hasta 560px y un máximo de 62vh. Los pasos de alta y código permiten desplazamiento en la zona inferior hasta 70dvh.

El espacio usa un contenedor de 1040px, con acceso de hasta 520px y padding horizontal adaptable. La identidad dispone de huella y texto en dos columnas. A 560px o menos, la huella pasa de 120px a 72px y la separación de identidad de 24px a 14px. Los mensajes limitan su altura a 52dvh, o 46dvh en móvil; las conversaciones se desplazan horizontalmente.

La conexión usa una sola columna de hasta 640px, margen superior de 48px y padding horizontal de 24px, con 64px al pie. A 560px o menos, el margen superior baja a 28px y el padding horizontal a 18px. La cabecera conserva la marca y el borde del espacio; la cabecera de mi-vault también ofrece «Conectar mi vault». El formulario continúa en el flujo vertical y no compite con un lienzo de fondo.

Los grupos usan separaciones cortas de 8px y 10px. El aire de paneles, campos e identidad corresponde a los pasos observados del frontmatter; no existe una escala global en CSS que obligue a todos los contextos a usar el mismo padding.

## Elevation & Depth

No hay sombras CSS en las pantallas estudiadas. La profundidad nace del lienzo de fondo, los paneles cálidos translúcidos o sólidos, los bordes finos y el orden de superposición. No hay desenfoque de fondo. La gravedad es un modo opcional del lienzo y está apagada por defecto.

El encuadre de portada viaja durante 650ms con desaceleración cúbica; voz y pista cambian de opacidad durante 0,8s. Las texturas visibles respiran con una variación de escala de ±2,4%, sin mover sus coordenadas. Con movimiento reducido, la cámara salta de inmediato al encuadre o a la huella elegida, la ficha se abre sin esperar el vuelo y se elimina la respiración. También se eliminan las transiciones CSS y varias animaciones del cuento. Estas duraciones describen comportamientos concretos, no una escala universal.

**The Profundidad sin sombra Rule.** Conserva la separación por tono, borde y superposición que ya usa Void.

## Shapes

Las acciones de portada y cuento tienen silueta de píldora. Los botones del espacio y conexión usan el radio `boton-espacio`; los campos y los mandos usan `campo`. Menú, ficha y hoja conservan radios distintos según su tamaño. La orden copiable de portada usa `orden`, y plegado, listas y campo de alias usan `utilidad`. El textarea del cuento tiene radio de 26px. Estos valores describen las variantes reales y no imponen una escala nueva.

Las huellas tienen territorio circular y contornos orgánicos producidos por reacción y difusión. El plano de portada no dibuja círculos libres ni límites del mundo. Los pequeños puntos de color identifican huellas, respuestas o huellas vistas de lejos; no son una nueva familia de insignias.

## Components

### Botón primario de portada

Acción visible y directa. Usa ámbar, tinta oscura, peso 500 y forma de píldora. Al pasar el puntero cambia a ámbar claro. El foco visible usa contorno de ámbar (2px) con separación de 2px. El cuento y el espacio tienen sus propios paddings y estados deshabilitados en su CSS; no se sustituyen por esta variante.

### Botón secundario de portada

Acción de contorno. Conserva fondo transparente, tinta clara y borde fino. Hover y estado expandido cambian el borde a ámbar; el foco comparte el tratamiento global de portada.

### Campo de acceso

Campo completo con etiqueta visible, fondo de carbón y borde del espacio. Usa el radio y padding del frontmatter. El foco tiene contorno de ámbar (2px) separado 3px. Los campos de contraseña mantienen su semántica; la búsqueda y el textarea del cuento son variantes específicas con otro tratamiento.

### Menú flotante

Puerta al lienzo en un panel cálido de contorno fino. La marca serif, la explicación monoespaciada y las acciones de crear, volver y conectar ocupan la cabecera. Las secciones usan `details` con indicador de apertura y separación por líneas; el botón de plegado reduce el menú conservando explicación y las tres acciones. En el sidecar se muestra una muestra estática del contenido y una sección nativa desplegable.

### Formulario de conexión

Entrada directa para vaults existentes o hechos a medida. Título serif, cuerpo monoespaciado y campos de fondo sólido con etiquetas visibles. El placeholder usa `tinta-2` con opacidad 1; el foco conserva el contorno ámbar (2px) separado 3px. El botón principal comparte la variante operativa del espacio, con borde ámbar; los botones deshabilitados usan opacidad 0,5 y cursor de espera.

El texto distingue copia local, acceso del asistente y operador, identidad pública y consentimiento explícito. El campo recibe un código temporal de diez minutos y un uso, nunca la llave privada del vault. Tras conectar, un segundo estado presenta el código privado recuperable en textarea de solo lectura, permite guardarlo en archivo y habilita abrir el vault cuando se confirma que se guardó. Los estados y errores tienen texto visible con `role="status"`. No se presenta sincronización posterior ni un precio o cobro.

### Mando de regreso

Botón compacto de la barra superior, con el mismo fondo, borde y tipografía que los mandos de zoom. Aparece como «Volver a las huellas» cuando hay huellas y ninguna queda cerca del encuadre; vuelve a encuadrarlas. Hover aclara la tinta y el borde, y el foco usa el tratamiento global de portada. El teclado permite desplazarse con flechas, variar zoom con +/− y encuadrar con 0; Escape cierra la ficha. Con movimiento reducido, regresar y seleccionar en la lista de huellas actualizan la cámara de inmediato.

### Ficha de huella

Ficha compacta y sólida cerca de la huella elegida. Presenta un título serif y texto secundario; cuando tiene cifras, las alinea en dos columnas con números tabulares. Se cierra con un botón de esquina y puede enlazar al sitio correspondiente. La muestra del sidecar usa el estado real «Una huella que empieza» y no simula cifras ni identidad de terceros.

## Do's and Don'ts

### Do:

- **Do** conservar el carbón cálido, el ámbar de acción y la jerarquía de tintas de las pantallas existentes.
- **Do** mantener la semilla y el tono personal de la huella al regresar.
- **Do** dar etiquetas visibles a los campos y conservar el foco de teclado.
- **Do** reservar espacio legible para palabras y controles alrededor del lienzo.
- **Do** respetar las variaciones de radios, bordes y tipografía documentadas por pantalla.
- **Do** conservar el plano sin bordes, la caché acotada y la representación por detalle de huellas reales.
- **Do** mantener visibles crear, volver y conectar, y ofrecer regreso al alejarse.
- **Do** respetar movimiento reducido con cámara inmediata y sin respiración.

### Don't:

- **Don't** sustituir el mundo existente por una identidad nueva.
- **Don't** añadir estrellas de fondo, nebulosas ni halos a la portada.
- **Don't** convertir la paleta multicolor de huellas en acentos decorativos de toda la interfaz.
- **Don't** añadir sombras o desenfoque como si pertenecieran al sistema observado.
- **Don't** presentar los ejemplos estáticos como una reproducción completa del lienzo o de su persistencia.
- **Don't** rellenar el vacío con huellas ficticias ni círculos de sitios reservados.

## Mi espacio y cuentas propias · 2026-10-12

Navegación horizontal con subrayado ámbar: Conversar, Herramientas, Mis modelos y Mi acceso y mis datos. Herramientas en filas planas de dos columnas, una en móvil. Modelos y formulario de cuentas hasta 580px, select nativo, etiquetas visibles y consentimiento junto a su acción. Claves en campos de contraseña, nunca en mensajes ni almacenamiento del navegador. La exportación explica qué copia descarga.

CSS de espacio posterior al estilo base: campos y lectura móvil a 16px, foco visible, salto al contenido y desplazamiento de navegación sin desbordar la página. Microtransición de opacidad de 180ms al cambiar de zona mediante Web Animations, anulada con movimiento reducido. Markdown de conversación construido con nodos DOM seguros; no ejecuta HTML recibido. Mantiene carbón, ámbar, serif y huella personal.
