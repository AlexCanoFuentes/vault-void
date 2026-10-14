# Entrada alojada · 2026-10-11

Publicada por orden de la persona responsable del producto. El recorrido crea un vault alojado con nombre nuevo, enlaza la huella del cuento, conserva las respuestas literalmente dentro del archivo privado y permite conversar y volver con la misma identidad.

## Operación

1. Desplegar `void-nube` con la exportación privada `VoidAlojamiento` y su imagen Docker.
2. Aplicar las migraciones D1 pendientes mediante `wrangler d1 migrations apply DB --remote --config red/wrangler.jsonc`.
3. Desplegar la API con `NUBE` y `TOPE_WEB=3`.
4. Desplegar los assets con `wrangler deploy --config wrangler.toml`.

El piloto usa las tres cajas ya disponibles. No aumenta el máximo de contenedores. El cupo cuenta los espacios alojados creados, también si están dormidos. Para cerrar nuevas altas, poner `TOPE_WEB=0` y desplegar la API; no elimina espacios existentes.

La sesión usa cookie Secure, HttpOnly y SameSite=Strict. Las escrituras exigen origen propio. D1 conserva hashes de sesiones y recuperación; las palabras se guardan en el archivo cifrado del vault. No se envían las respuestas a un repositorio de GitHub. Cifrado en reposo con clave del operador: no equivale a cifrado inaccesible al operador ni a independencia de Cloudflare o del proveedor del modelo.

El código privado se muestra al crear el espacio y se puede descargar. Es necesario para volver desde otro navegador. La interfaz permite guardar borrador y reintentar un fallo sin crear otra huella. Un perfil local ya registrado no se convierte automáticamente en uno alojado.

## Validación

- `npm run typecheck`, desde `red`.
- `npm test`: 19 comprobaciones existentes correctas.
- `VOID_NUBE_REPO=/ruta/void-nube node pruebas/entrada-web.mjs`, desde `red`: siete comprobaciones con Worker, D1 y cifrado reales en Miniflare; el contenedor es un doble explícito.
- Navegador local en 1366×900 y 390×844: primera escritura de huella forzada a fallar, bloqueo y reintento, alta, conversación, vuelta y recuperación con huella idéntica, sin errores ni desbordamiento.
- Caja Docker real: conversación e historial git restaurados tras parar y volver a crear una caja. El modelo gratuito real respondió por `prompt_async` en una comprobación separada.
- Revisión de interfaz independiente: tres correcciones resueltas, disposición final `ship`. No certifica seguridad ni producción.
- Producción: portada, cuento, espacio y JavaScript responden 200; `/v1/web/yo` sin sesión devuelve 401. Comprobación de solo lectura, sin cuentas ni huellas de prueba.

La primera prueba humana en producción corresponde a la persona responsable del producto. Comprensión sin explicación y recorrido real en Cloudflare pendientes de esa prueba.

## Versiones publicadas

- Caja: `5e31d739-3644-4c92-bff5-f5a0d42b5d2d`.
- API: `5742884d-bef9-4ca2-8773-99f7d64cfbf3`.
- Web: `fe1618e8-502b-445e-b212-9eaf7d26b645`.
- D1: migración `0006_entrada_web.sql`, aplicada sin eliminar datos.

## Copia completa preparada · 2026-10-12

El conector incluye los archivos ignorados por Git y los archivos de acceso locales, sin leer ni mostrar sus valores en la vista previa. Tras consentimiento empaqueta todos los archivos, preserva configuración e historial y materializa enlaces internos con metadatos privados para reconstruirlos. Directorios vacíos incluidos. Enlaces externos, ciclos, archivos especiales, escritura concurrente o límites superados detienen la copia; no se recortan datos. SQLite usa respaldo coherente; sus WAL/SHM originales quedan como archivos de recuperación inactivos dentro de la importación. La memoria compartida SQLite puede cambiar por su propio protocolo de lectura, sin modificar filas ni el WAL.

`python3 pruebas/pruebas_copia_completa.py`: restauración de todos los contenidos declarados, historial y enlaces; ignorados, secretos inventados sin imprimir y conversación con WAL. El paquete también pasó el validador real de void-nube. El manifiesto permite verificar conservación antes del envío. Alex ha autorizado la publicación y su copia completa, incluidos los archivos de acceso y entregables descritos. También autoriza ampliar el límite a 128 MiB comprimidos; se mantienen 200 MiB claros y tres cajas. La prueba real se registra después de ejecutarla.

## Transporte completo · 2026-10-12

POST /v1/alojar acepta x-void-subida: iniciar, trozo o terminar, siempre con consentimiento y llave vigente. El inicio declara bytes y SHA-256; las partes de 512 KiB llevan identificador e índice. La caja cifra por parte, rechaza contenido distinto en un reintento y confirma el puntero solo tras comprobar hash, tamaño y archivo seguro. La entrada anterior permanece disponible para clientes pequeños y archivos antiguos. GET /v1/alojar/archivo recupera solo el archivo propio en flujo, sin caché. El cliente compara recibo y manifiesto de todos los archivos. Un vault previo nunca se pisa. La caja usa el mismo almacenamiento en flujo al guardar; conserva archivos sin commit aunque un hook impida el checkpoint, sin desactivar candados.

Validación adicional: 17 comprobaciones de entrada, incluyendo importación y recuperación de una copia inventada mayor de 50 MiB, corte antes de confirmar, reintento, límite, guardado en flujo y rechazo de hash incorrecto. Pruebas Python de copia completa y de verificación de respuesta y descarga. Docker real con conversación e historial restaurados, sin invocar el modelo.
