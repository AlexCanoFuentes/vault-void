# Conectar vaults existentes y a medida · 2026-10-12

El plano humano abre el vault real de su dueño conservando su alias, huella, archivos, plantilla e historial. No crea otro perfil ni vuelve a pedir las respuestas del cuento. Los vaults a medida siguen este mismo camino; el cobro queda fuera de esta entrega.

El cliente `conectar_vault.py` primero describe la copia local sin enviar nada. Solo con `--confirmar-alojamiento` usa automáticamente la llave propia del vault para preparar el vínculo. Sin exclusiones conserva el original completo y su historial: también archivos ignorados, `.env`, `.pem`, `.key`, personalizaciones, dependencias y configuración del remoto, tras consentimiento explícito. No muestra sus valores. Los enlaces internos se materializan y sus destinos quedan en el manifiesto privado; un enlace externo, circular o un archivo especial detiene la copia. Los commits previos se conservan y deben revisarse también. Las conversaciones SQLite bajo `.agente` se copian con su API de backup. La copia privada conserva las claves propias de Void. No hay sincronización posterior entre el ordenador y Void.

Una caja previa se vincula con `--ya-alojado` y la contraseña que introduce su dueño con entrada oculta. No se resiembra ni se cambia su archivo. Un reintento de conexión conserva el alojamiento previo. La capacidad del piloto sigue siendo tres alojamientos.

La API comprueba la llave vigente y el consentimiento, y devuelve un código aleatorio `ve_` de un uso que caduca en diez minutos. Solo su hash llega a D1. La web exige origen propio, consume el código de forma atómica y crea un nuevo código privado `vr_` y sesión HttpOnly. Ese paso revoca los accesos web anteriores, conservando la prueba de propiedad de la caja, la llave del vault y su huella. Rotar la llave invalida códigos temporales pendientes.

El vacío elimina los huecos reservados y el marco finito. La API pagina todas las huellas públicas; cada una ocupa coordenadas estables. El lienzo permite desplazamiento en cualquier dirección, zoom, selección y vuelta a las huellas. Prepara únicamente las texturas visibles, con caché de doce, y usa niveles de detalle para las lejanas. La respiración suave se detiene con movimiento reducido. No añade perfiles ficticios.

Verificación local: diecinueve pruebas generales de red, quince comprobaciones de entrada y conexión con Miniflare y contenedor sustituido explícitamente, validación TypeScript y dos copias Python distintas. Las pruebas cubren consumo concurrente, caducidad, rotación de llave, consentimiento, CSRF, archivo peligroso, caja ajena, paginación de más de una página y posiciones únicas con semillas repetidas. El navegador local comprobó móvil y escritorio, recuperación, conversación, huella idéntica al volver y desplazamiento sin bordes. Una caja Docker real conservó plantilla a medida, archivos, historial git y conversación al parar, archivar y restaurar; esa prueba se ejecutó con `--sin-modelo` y no prueba una respuesta nueva de un proveedor de IA.

Cada dueño autoriza el alojamiento de sus propios archivos. La infraestructura y el modelo siguen usando proveedores externos; el operador puede acceder a los archivos durante el trabajo. No representa soberanía completa ni cifrado inaccesible al operador. La comprobación humana en producción corresponde al responsable del producto; no se crean cuentas de prueba allí.

Corrección del solapamiento, 11-oct: perfiles antiguos pueden compartir semilla visual; sus sitios y texturas tienen que ser independientes. La posición se deriva del identificador de perfil (par) o cuento sin perfil (impar), y esa posición identifica la textura en caché. La semilla, tono y datos se conservan. Al vincularse, una huella del cuento toma el sitio del perfil. El paso radial 330 deja separación para la textura de 220px y su respiración máxima. `node pruebas/vacio.mjs` comprueba mil sitios consecutivos, texturas independientes de tres entradas de semilla compartida, selección y estabilidad al reordenar la lista.

2026-10-12: límite autorizado de 128 MiB comprimidos y 200 MiB claros, sobre las mismas tres cajas. El conector manda partes de 512 KiB, cifradas independientemente. El servidor comprueba tamaño, hash completo y USTAR antes de activar la copia; un corte o un hash erróneo conserva la versión vigente. Los archivos previos siguen siendo legibles. GET /v1/alojar/archivo exige la llave vigente y recupera solo el espacio de ese perfil, en flujo y sin caché. El cliente compara el recibo, descarga la copia y comprueba cada contenido antes de anunciar éxito. La caja guarda también en flujo; un candado que impide el checkpoint no impide conservar los archivos sin commit ni se salta el hook. Se conserva una copia anterior además de la vigente; no se promete un historial ilimitado de archivos ignorados. Pruebas adicionales: archivo inventado de 51 MiB, corte, reintento idéntico y distinto, propietario ajeno, límite de 128 MiB, guardado y hash erróneo; cliente rechaza otra copia o descarga alterada.


## Dejar carpetas o archivos en el ordenador · 2026-10-17

Antes de alojar, revisa localmente qué se enviará:

```text
python3 herramientas/conectar_vault.py --vault . --excluir CRM --excluir "documentos/privado.pdf"
```

Si el dueño acepta ese alcance, repite la misma orden añadiendo `--confirmar-alojamiento`. `--excluir` admite rutas literales relativas, archivos o carpetas completas; no usa comodines. Los ignorados por Git siguen incluidos salvo exclusión explícita. Al excluir una base `.db`, `.sqlite` o `.sqlite3` también se excluyen sus auxiliares `-wal`, `-shm` y `-journal`.

Con exclusiones no viaja ningún repositorio `.git` original, ni su configuración, hooks, objetos o historia. La copia comienza con un commit vacío nuevo y los archivos seleccionados en su carpeta de trabajo. El historial completo permanece intacto en el ordenador. Esta copia no comparte antepasados con el original y no se debe unir mediante `turno.py`.

Un enlace simbólico o duro seleccionado detiene este modo; hay que excluirlo también. Excluir una ruta no detecta sus copias independientes, ZIP, bundles o fragmentos en conversaciones: revisa y excluye esas rutas aparte. Los directorios vacíos seleccionados se conservan. El cliente rechaza cambios durante la preparación y verifica la descarga como en la copia completa.

La exclusión de `.void/llave` o de su carpeta detiene la conexión: el protocolo necesita esa credencial para identificarse. El empaquetador local puede omitirla, pero no se promete una conexión sin enviarla como credencial. `--ya-alojado` no admite exclusiones, y una selección nueva nunca purga los datos de una caja existente. Las opciones deben repetirse al confirmar o reintentar.
