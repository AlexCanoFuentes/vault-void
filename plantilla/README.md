# Vault de {{nombre}}

> «[sin contestar]» (tu respuesta 7). Tu trabajo, tus proyectos y tu criterio, en archivos de
> texto que son tuyos. Funciona con git y un editor; un agente (Claude, Codex o Antigravity) es
> opcional. **Ni una clave ni una copia de un documento dentro.**
> **Última actualización:** {{fecha}} · montaje con tus respuestas.

## Hoy

> Esta sección es una foto: se reescribe entera en cada cierre, 12 líneas como máximo.
> Lo que dijiste tú lleva el número de tu respuesta; lo que se supone, dice «(supuesto)».

- **Quién soy y a qué me dedico:** [sin contestar] (respuesta 1).
- **Con qué trabajo:** [sin contestar] (respuestas 2 y 3).
- **Lo que pesa:** [sin contestar] (respuesta 4).
- **Hacia dónde voy:** [sin contestar] (respuesta 5).
- **Qué no hago y qué no entra aquí:** [sin contestar] (respuesta 6).
- **Proyectos:** 0.
- **Siguiente paso:** [sin contestar]

## Cómo se usa

**Con un agente** (Claude, Codex o Antigravity): «abrir» al empezar (lee todo y te resume dónde
estás) · «cerrar» al terminar (deja esta foto al día, propone lo que vale guardar y lo guarda en
git). En Claude son `/abrir` y `/cerrar`. Cerrar lo decides tú.

**Sin IA:** lo mismo a mano. Al terminar, si cambió algo, reescribe «Hoy» y guarda:

```
python3 herramientas/revisar.py
git add -A && git commit -m "vault: <qué cambió>"
```

**En cualquier momento:** algo suelto que no quieres perder va a `INBOX.md`, una línea con fecha.

En Windows, donde dice `python3` escribe `py`. Todo lo de `herramientas/` es Python sin
dependencias: no hay nada más que instalar.

## Mapa

| Dónde | Qué hay |
|---|---|
| `AGENTS.md` | Las reglas que sigue el agente en este repo, sea Claude, Codex u otro |
| `CLAUDE.md` | Importa `AGENTS.md` y añade lo que solo vale para Claude |
| `INBOX.md` | Lo suelto, una línea con fecha. Se vacía al cerrar |
| `proyectos/` | Un archivo por proyecto. `_plantilla.md` es el molde |
| `criterio/apuntes.md` | Tus palabras cuando decides algo. Empieza con tus siete respuestas |
| `criterio/decisiones.md` | Decisiones y lecciones, cada una con su porqué |
| `herramientas/` | `revisar.py` (lo que no debe entrar), `pruebas.py`, `medir.py` (cómo va, en cifras) y `void.py` (las mejoras de Void) |
| `mirar/` | No existe hasta que la creas: ahí copias algo para que el agente lo mire. No entra en git; bórralo al terminar |
| `.claude/` | Los pasos de abrir y cerrar (en Claude, `/abrir` y `/cerrar`) y los permisos de Claude |
| `.codex/` | Los permisos de Codex: solo esta carpeta, sin internet y preguntando |

**Qué no entra:** claves ni contraseñas, copias de correos o documentos, imágenes, vídeos ni
audio (de eso, solo la ruta o el enlace), ni teléfonos o correos de otras personas escritos tal
cual. Lo comprueba `python3 herramientas/revisar.py`. Lo demás lo decides tú en tu respuesta 6.

**El historial es el de git.** No hay bitácora aparte: `git log` dice qué pasó y cuándo.
