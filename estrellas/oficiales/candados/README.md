# Candados para agentes

**Claude Code y Codex en el mismo repositorio, sin pisarse y con los mismos candados.**

Si trabajas con más de un agente de IA sobre el mismo código, tarde o temprano uno hace un `push --force` sobre el trabajo del
otro, mete una clave en un commit o reescribe un fichero que solo debía crecer. Esto lo para, y trae una prueba que demuestra
que cada candado salta de verdad.

## Tres capas, porque cada una deja pasar algo

| Capa | Dónde | Qué para | Qué deja pasar |
|---|---|---|---|
| **La guardia** | `guardia.py`, un hook antes de cada acción del agente | Comandos destructivos, claves en comandos, ficheros y parches, reescribir lo que solo crece | Solo actúa sobre el agente: la persona en su terminal no pasa por ella |
| **Reglas de Codex** | `.codex/rules/candados.rules` | Los mismos comandos, antes de ejecutarse | Comparan el principio exacto del comando: `git push origin main --force` se les escapa (por eso existe la guardia) |
| **Candados de git** | `.githooks/pre-commit` y `pre-push` | Claves en un commit, líneas quitadas a lo que solo crece, `main` forzada o borrada | `--no-verify` (por eso la guardia se lo prohíbe al agente) |

**La guardia es una sola para los dos agentes:** Claude Code y Codex mandan cada acción con la misma forma y aceptan la
misma respuesta para denegarla. Lo único distinto es cómo describen un cambio en un fichero (Claude: `Write`/`Edit` con la
ruta; Codex: `apply_patch` con el parche entero), y la guardia entiende los dos.

## Instalar, en tres pasos

1. **Copia** en la raíz de tu repo: `guardia.py`, `candados.py`, `candados.json`, `instalar.py`, `probar.py`, `mesa.py`,
   `AGENTS.md`, `CLAUDE.md`, `.gitattributes` y las carpetas `.githooks/`, `.claude/` y `.codex/`. Si ya tienes `CLAUDE.md`
   o `.claude/settings.json`, añade lo de aquí a lo tuyo en vez de pisarlo.
2. **Di qué solo crece**, en `candados.json` (un diario, un registro de decisiones…), y ponlos también en `.gitattributes`.
   Si quieres que nadie empuje a otro sitio, pon tu remoto en `"remoto"`.
3. **Actívalo y pruébalo:** `python3 instalar.py` y `python3 probar.py` (en Windows, `py`). Tiene que salir todo en verde.

En **Codex**: marca el proyecto como de confianza y aprueba la guardia en `/hooks` la primera vez (Codex no ejecuta hooks
de un proyecto sin revisarlos). En **Claude Code**: la guardia entra sola con `.claude/settings.json`.

**Cada agente en su propio clon**, y `python3 instalar.py` en cada uno: git no copia los candados al clonar.

## La prueba

`probar.py` monta un repositorio de usar y tirar y comprueba cada candado en rojo (lo para) y en verde (deja pasar lo
normal), con las dos formas, la de Claude y la de Codex. Al final repite todos los rojos contra una guardia vacía: si alguno
siguiera en rojo, la prueba no estaría midiendo nada. **Un candado que no puede fallar no es un candado.**

## La mesa: que los agentes se pasen trabajo

`mesa.py` es un buzón en el propio repositorio: un agente deja un encargo para otro, el otro lo recoge al empezar, y queda en
el historial de git quién pidió qué. **Un encargo sin orden de la persona es una propuesta:** el otro agente no lo ejecuta,
se lo enseña. Así «bajo mis órdenes» vive en el código y no en la buena voluntad del agente.

## Lo que esto NO protege

- **A la persona de sí misma:** desde tu terminal puedes usar `--no-verify` o `CANDADOS_A_PROPOSITO=1`. Es a propósito.
- **El servidor:** si tu proveedor de git deja proteger la rama principal (no forzar, no borrar), hazlo. Es la única capa que
  no se salta desde un cliente.
- **Todas las claves del mundo:** la guardia caza las formas conocidas (GitHub, OpenAI, Anthropic, AWS, Google, Stripe,
  Slack, Supabase, JWT, claves privadas). No es un escáner completo.
- **Lo que el agente lee:** el sandbox de Codex limita lo que escribe, no lo que lee. No dejes un `.env` en el clon del agente.

## Requisitos

Python 3.8 o más nuevo y git. Sin dependencias. Probado en Linux (WSL). En Windows nativo todavía no: los hooks llaman a
`python3`, y si tu Windows solo tiene `py`, hay que cambiarlo en `.claude/settings.json`, `.codex/hooks.json` y la
primera línea de `.githooks/`.

---

Hecho en el laboratorio de [LexLabs](https://alexcanofuentes.com/#lexlabs). Es la primera estrella de [Vault Void](https://vaultvoid.app).
