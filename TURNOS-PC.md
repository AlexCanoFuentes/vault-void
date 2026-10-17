# Traer la última copia de Void al PC · 2026-10-17

Desde una terminal con Python 3.8 o posterior y Git, ejecuta el cliente de este repositorio. Elige una carpeta nueva, privada y fuera de cualquier repositorio para conservar la descarga:

```text
python3 espacio.py bajar --alias NOMBRE --destino /ruta/privada/descarga-nueva
```

Sustituye `NOMBRE` por el nombre de tu espacio, en minúsculas. El cliente pide tu código con entrada oculta. No lo pongas en los argumentos, el historial de órdenes ni un chat. Si no hay entrada oculta, se detiene. El cliente todavía no forma parte de la base común.

Para incorporar sus commits al vault del PC en la misma operación:

```text
python3 espacio.py bajar --alias NOMBRE --destino /ruta/privada/descarga-nueva --juntar /ruta/del/vault
```

Esto usa `turno.py`. Conserva `archivo.tgz` íntegro y una carpeta `copia` para la unión. Si la copia tiene cambios sin commit o marcas del índice que podrían ocultarlos, no se junta. Si hay un conflicto o historias sin antepasado común, tampoco se fuerza la unión. Los archivos ignorados, conversaciones y credenciales de la descarga no se incorporan al vault del PC. No se ejecutan los scripts, hooks ni la configuración Git recibidos; el archivo original los conserva, y la copia de trabajo de Git usa una configuración mínima propia.

## Si solo tienes el kit

Añade `--recuperar-con-kit`. Esta opción usa la recuperación existente de Void: **cambia tu código y cierra sesiones anteriores**. Introduce el kit únicamente cuando lo pida la terminal. El código nuevo queda en `acceso.json`, dentro de la carpeta privada, antes de empezar la descarga. Una primera entrada con código también puede devolver un kit nuevo, que se guarda en ese mismo archivo. Si no se recibió ningún acceso nuevo, el archivo contiene un objeto vacío.

Conserva `acceso.json` en tu lugar privado de accesos. No lo añadas a Git ni lo compartas. Si la descarga falla después de recuperar, ese archivo sigue ahí. Si la respuesta se pierde justo después de que el servidor cambie el código, vuelve a recuperar usando tu kit y un destino nuevo. El cliente no puede hacer atómicos el cambio remoto y la escritura en tu disco.

## Qué se ha comprobado y qué significa

El cliente descarga la **última copia guardada**. No despierta ni duerme el espacio, ni fuerza un guardado. Puede haber trabajo activo todavía sin guardar en la caja. El SHA-256 mostrado identifica los bytes descargados; no es una firma ni un recibo de generación del servidor.

La carpeta de destino tiene permisos 0700 y los archivos privados 0600 en sistemas POSIX. Probado en Linux con Python 3.8 y 3.14; no verificado en Windows ni macOS. La extracción rechaza enlaces, archivos especiales, rutas inseguras, repeticiones, referencias Git de reemplazo e historias dependientes de otras carpetas. Si se rechaza, conserva el archivo para revisar y recuperar por otro camino. Límites: 128 MiB comprimidos y 200 MiB descomprimidos.

Al terminar intenta cerrar la sesión y olvidar el aparato temporal. Si falla la salida, lo avisa y descarta las cookies locales. No guarda sesiones en disco. Una recuperación con kit puede haber cerrado tus otras sesiones aunque la descarga posterior falle.

La unión habla de los commits de esa copia, no de todos los archivos ni del estado actual del espacio. Las copias creadas con exclusiones tienen una historia nueva y no se juntan con el historial completo original del PC.

## Ver si está al día

```text
python3 espacio.py estado --alias NOMBRE --vault /ruta/del/vault
```

Compara el último commit de tu ordenador con el último commit que guardó tu espacio. Dice una de estas cosas: «Al día», «Tu ordenador tiene N commits que tu espacio no tiene» (súbelos), «Tu espacio tiene commits que tu ordenador no tiene» (bájalos con `bajar --juntar`), «Los dos tienen cambios» (baja, junta y sube) o «No se pudo comprobar». Sin dato, nunca dice «al día». Avisa si tienes cambios sin commit, si hay una subida esperando y si la última chocó. Habla de commits: las conversaciones y los archivos ignorados del espacio no cuentan.

## Subir tus commits (17-oct)

```text
python3 espacio.py subir --alias NOMBRE --vault /ruta/del/vault
```

Sube **solo tus commits nuevos**, como un paquete de git, y solo si:

- tu ordenador no tiene cambios sin commit;
- tu ordenador parte del último commit que guardó tu espacio (si no, baja y junta primero);
- tu espacio está **dormido** (duérmelo en Mi espacio).

El paquete espera cifrado con tu candado y **se aplica la próxima vez que despierte tu espacio**, antes de arrancar el ayudante: avanza o junta, como `turno.py`. Si choca, no toca nada, retira la subida y `estado` te dice en qué ficheros; baja, junta en tu ordenador y vuelve a subir. Las conversaciones, las llaves y los archivos ignorados del espacio no se tocan nunca. No uses `conectar_vault.py` para esto: sirve para la conexión inicial.
