Abre el vault de {{nombre}} antes de trabajar. Lee, pregunta lo que falte, ejecuta y resume; no propongas nada hasta el paso 6.

1. **¿Está al día?**
   ```
   git fetch --quiet
   git status -sb | head -1
   git branch -r --no-merged origin/main
   ```
   - Si esta copia va detrás de `origin/main`, trae lo nuevo (`git pull --ff-only`) antes de leer nada.
   - Si aparece alguna rama, **dilo lo primero** y enseña qué toca
     (`git diff --stat origin/main...<rama>`): es trabajo de una sesión anterior que no llegó a
     `main`. Si nadie la mira, se pierde en silencio.
   - Si `git fetch` falla (sin remoto, sin red), dilo y sigue.
2. **Lee** `README.md`, `INBOX.md`, `criterio/apuntes.md`, `criterio/decisiones.md` y lo que haya
   en `proyectos/`. Mide cuánto pesan juntos (`wc -c`). Si pasan de 100 KB, dilo: toca archivar lo
   viejo por año, porque cada apertura lee todo esto.
3. **Si en `criterio/apuntes.md` queda algún `[sin contestar]`**, pregúntale a {{nombre}} si quiere
   contestarlo ahora. Una pregunta cada vez, tal como está escrita. Acepta respuestas largas o
   pegadas de un audio transcrito, y cópialas **literales**, sin corregirlas, donde dice «Tu
   respuesta». Cambia `[sin contestar]` por el tipo que le propongas (Principio, Regla…) y, en
   «Qué hizo el vault con esto», escribe qué cambiarías del vault por esa respuesta: **propónlo,
   no lo apliques** hasta que diga que sí. Si prefiere contestar otro día, sigue sin insistir.
4. **Ejecuta y enseña lo que dicen. No los describas: córrelos.**
   - `python3 herramientas/revisar.py`: si hay algo que no debe estar en el vault.
   - Cada herramienta que {{nombre}} haya añadido a `herramientas/` y contesta una pregunta suya.
5. Si `INBOX.md` tiene líneas, propón a dónde va cada una.
6. Resume en unas 5 líneas dónde está {{nombre}} según el repo, no según tu memoria. Solo entonces, propón.

Durante la sesión rigen las reglas de `AGENTS.md`: si algo choca con un apunte de
`criterio/apuntes.md`, se dice con la fecha y sus palabras, y decide {{nombre}}.
