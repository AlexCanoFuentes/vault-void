# M-09, entrega parcial para revisión de Claude, 21-oct-2026

Fase 1 incompleta. Se entrega el puente y las rutas. La web no se ha tocado:
faltó una copia verificable de three.js y su licencia MIT. La descarga del
paquete 0.128.0 falló con `Could not resolve host: registry.npmjs.org`; tampoco
había una copia local. Se ha parado en ese punto según la instrucción de Alex.
No se ha publicado ni desplegado nada.

KERNEL: **95/100, EXECUTE**, evaluación y resultado junto a este informe.
Las fuentes del ticket y ambos `mi-vault.*` se leyeron enteros.

## Commits locales

Los `.git` originales están montados en solo lectura. El intento de `git add`
y commit falló con `Unable to create .../.git/index.lock: Read-only file system`.
Los cambios están también en los árboles originales, sin preparar en su índice.
Los commits existen en copias locales, con la firma pedida y sin saltar hooks:

- `/tmp/m09-void-nube`: `7fcae35`, puente y pruebas; `e8200cc`, Worker y pruebas.
- `/tmp/m09-vault-void`: el commit que contiene este informe, la entrada con
  cookie, sus pruebas y KERNEL.

Se dejan paquetes Git incrementales en `medidas/m09-void-nube.bundle` del repo
void-nube y `medidas/m09-vault-void.bundle` de vault-void. No se añaden los
paquetes al propio historial. Se pueden comprobar con `git bundle verify` desde
el repo de origen o su copia. No se han cambiado las ramas de los repos originales.

## Qué hay construido

`void-nube/imagen/islas.py`: listar, guardar y borrar, esquema cerrado en cada
nivel, cinco tipos de bloque, forma, estilo y plantilla de listas cerradas;
40 islas, 64 KiB de JSON UTF-8 por isla; identificador sin rutas, apertura sin
seguir enlaces, revisión SHA-256 para evitar sobreescrituras, diario y commit
por cambio. La operación de archivos rechaza root. El supervisor usa `runuser`
con usuario agente, entorno limpio y `python3 -I`.

Se comparte un cerrojo fuera del vault con el checkpoint y el archivo de la
caja. Al dormir, se cierra la entrada y se espera al cambio en curso. Un rechazo
de Git repone archivo y diario; los cambios ajenos del índice se conservan.
Contrato y límites: `void-nube/imagen/ISLAS.md`.

La entrada `/v1/web/islas/` usa la cookie del dueño y la protección de origen
existentes. El alias, la prueba y la llave del aparato salen de la sesión.
El Worker usa el puerto 4099 directamente, con un pase nuevo por despertar,
solo con contenedor healthy y corriendo y candado abierto. Ninguna operación
llama a `despierta` ni a `containerFetch`. Una lectura no renueva el reloj.

## Pruebas ejecutadas

| Orden | Salida resumida |
| --- | --- |
| `python3 pruebas/islas.py`, en void-nube | `Ran 15 tests ... OK`; 25 casos adversarios rechazados, incluidos campo desconocido, rutas, bloque ajeno y más de 64 KiB. |
| `node pruebas/islas-web.mjs`, en void-nube | Sesión ajena, sueño, candado, campos, acciones y tamaño rechazados; puerto fijo y fallos comprobados. |
| `node red/pruebas/islas.mjs`, en vault-void | Cookie, CSRF, identidad de sesión, límites, métodos y JSON sin normalizar: correcto. |
| Nueve archivos existentes de pruebas de void-nube | `pass 9`, `fail 0`: actividad, uso, candado, candado-caja, pc-pendiente, permisos, portero-caja, passkey-caja y passkey-puerta. |
| `npm run typecheck`, en red | Correcto, sin errores. |
| Compilar `worker/src/index.js` con esbuild | Correcto, grafo completo del Worker. |
| `bash -n imagen/caja.sh`, `git diff --check` | Correctos. |
| `python3 pruebas.py`, en vault-void | `Ran 203 tests ... FAILED (errors=26)`: 177 correctas; los 26 errores son `PermissionError: Operation not permitted` al abrir sockets de prueba. |
| `npm test`, en red | No arranca: `listen EPERM 127.0.0.1:8789`. |
| `node red/pruebas/entrada-web.mjs` | No arranca: `listen EPERM 127.0.0.1`. |
| `node pruebas/mensajeria.mjs`, en void-nube | No arranca: `listen EPERM 127.0.0.1`. |

La prueba nueva de archivos usa repositorios inventados y demuestra crear,
cambiar, borrar, una línea y un commit por cambio, reabrir desde otro proceso,
rechazar root, límite de 40, concurrencia, espera al supervisor, enlaces,
fallo de hook, conservación del índice ajeno y arranque sin commit previo.
Reabrir otro proceso no sustituye una prueba de dormir y restaurar la caja.
Los logs de ejecución están en `/tmp/m09-*.log`.

## Lo que falta antes de cerrar la fase 1

1. Obtener three.js r128 y su licencia MIT, copiar ambos al repo y servirlos
   desde el mismo origen. Construir el archipiélago y la vista en lista, las
   cuatro islas fijas, las tres plantillas y la edición con este contrato.
   Mantener todas las secciones actuales y sus accesos ante sueño o fallo.
2. Repetir las suites completas en un entorno que permita sockets locales.
3. Ejecutar Docker con datos inventados: crear, cambiar, borrar, SIGTERM,
   archivo, segunda caja y restauración. `docker info` dio permiso denegado
   sobre `/var/run/docker.sock`. No se construyó ni desplegó imagen alguna.
4. Navegador de 320 a 1440 px, recorrido completo y medición en el Pixel 8a.
   No se ha certificado el diseño ni los fps: la interfaz sigue pendiente.
5. Revisión de Claude, especialmente el ciclo de parada, los hooks y la
   recuperación ante caída brusca entre archivo, diario y commit. El cerrojo
   coordina al supervisor y este puente; un agente que haga Git manualmente
   sin tomarlo todavía puede competir con ellos.

Fases posteriores: publicación real como estrella, islas que ejecuten código
y cualquier nueva fusión con el PC siguen fuera. Un despliegue solo podrá
hacerse tras la revisión y la orden expresa de Alex en ese momento.
