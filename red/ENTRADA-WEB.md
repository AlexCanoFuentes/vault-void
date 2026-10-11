# Entrada alojada · 2026-10-11

[CONF] Publicada por orden de la persona responsable del producto. El recorrido crea un vault alojado con nombre nuevo, enlaza la huella del cuento, conserva las respuestas literalmente dentro del archivo privado y permite conversar y volver con la misma identidad.

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
