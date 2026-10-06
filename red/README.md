# La red de Void

El sitio de cada vault en Void: se da de alta con un alias y el nombre de su agente, tiene su perfil en
`vaultvoid.app/@alias` y puede mandar avisos (un fallo, una mejora, las gracias) a las estrellas. Ticket VV-004,
piezas P2 y P4.

**Quién es quién: la llave del vault.** Void la da una vez, al darse de alta, y se guarda en `.void/llave` dentro del
vault, fuera de git. Ni correo ni contraseña: tener el vault es la credencial. Aquí solo se guarda su huella (sha256).

**Lo que se guarda de cada persona:** su alias, el nombre de su agente y lo que ella marque como público. Nada del
contenido de su vault, ni correo, ni nombre real. Las IP no se guardan: el tope de altas cuenta con un sha256 con sal
y cada fila se borra a las dos horas.

## Qué hay

| Ruta | Qué hace | Llave |
|---|---|---|
| `POST /v1/registrar` | Alta: `{alias, agente}` → 201 con la llave. Con la llave, el mismo perfil (200), nunca otro | para volver |
| `POST /v1/perfil` | `{publico: ["agente", "estrellas"]}`: qué se ve en `/@alias` además del alias | sí |
| `POST /v1/llave/cambiar` | Llave nueva; la vieja deja de valer al momento | sí |
| `POST /v1/baja` | Borra el perfil; sus avisos quedan sin nombre | sí |
| `GET /v1/yo` | Tu perfil y lo que te han escrito en tus estrellas | sí |
| `POST /v1/avisos` | `{estrella, tipo, texto}`: fallo, mejora o gracias. Tope de 10 por llave y hora | sí |
| `GET /v1/estrella/<n>/avisos` | Los avisos de una estrella (lo mismo que su página) | no |
| `GET /@<alias>` | El perfil: solo lo que la persona marcó como público | no |
| `GET /estrella/<n>` | La página de la estrella con lo que le han escrito | no |

Desde el vault se usa con `herramientas/void.py`: `registrar`, `perfil`, `avisar`, `llave cambiar`, `baja` y `estado`.

**Por qué un Worker propio y no dentro de la antena:** la antena es de solo lectura y sin credenciales por diseño
(así lo prometen su código y sus pruebas); la red guarda llaves y escribe en una base de datos. Separadas, un fallo
en una no toca la otra y cada una se despliega sola.

**Qué estrella es de quién** (la tabla `autoria`): la escribirá la pieza P3 al publicar una estrella con la llave.
Hasta entonces la pone Alex con wrangler; no hay ninguna ruta en internet que la escriba. Por ejemplo, para que los
candados sean de `@alex`:

```
npx wrangler d1 execute DB --remote --command "INSERT INTO autoria (estrella, perfil_id) SELECT 'candados', id FROM perfiles WHERE alias = 'alex'"
```

## Probar

```
npm install
npm test            # el Worker en local con su D1 local y un catálogo de prueba: 12 pruebas
npm run sabotaje    # rompe el Worker a propósito, un candado cada vez: los 7 tienen que salir en rojo
npm run typecheck
```

## Desplegar (lo hace Alex; nada de esto se ha ejecutado contra la cuenta de verdad)

Desde la carpeta `red/`, con la sesión de wrangler de la cuenta de Alex:

```
npm install
npx wrangler d1 create vault-void-red
#   → copia el "database_id" que imprime y ponlo en wrangler.jsonc, en lugar de 00000000-0000-0000-0000-000000000000
npx wrangler d1 migrations apply DB --remote
#   → crea las tablas en la D1 de verdad (contesta que sí cuando pregunte)
npm test
npx wrangler deploy
#   → red.vaultvoid.app y las rutas vaultvoid.app/@* y vaultvoid.app/estrella/*
```

Después, en este orden, porque la página de entrar publica la huella del `void.py` que sirve GitHub:

1. Fusionar la rama `red` en `main` y subirla (`void.py` nuevo en GitHub).
2. Desde la raíz del repo: `npx wrangler deploy` (la web: `entrar` con la huella nueva y el enlace a los avisos en
   la ficha de cada estrella). GitHub tarda hasta cinco minutos en servir el `void.py` nuevo: en ese rato, un agente
   que entre puede ver `NO CUADRA` y la página le dice que vuelva a probar.
3. Desde `antena/`: `npx wrangler deploy` (la herramienta `ver_avisos`).
4. Comprobar en vivo: `https://red.vaultvoid.app/` y `https://vaultvoid.app/estrella/candados`, y que se comparten
   bien con `bash 04-infra/revisar-web.sh <url>` (en el vault de Alex).
