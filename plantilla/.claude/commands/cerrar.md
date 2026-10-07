Cierra la sesión: deja el vault al día y guardado. Se cierra cuando {{nombre}} lo pide, nunca antes.

1. **Reescribe entera la sección «Hoy» del `README.md`.** Una foto de 12 líneas como máximo,
   sacada de los archivos y de lo que digan las herramientas, con el siguiente paso. No acumules
   párrafos con fecha: la historia ya está en git. Cambia también la fecha de «Última
   actualización».
2. **Decisiones y lecciones.** Si se decidió algo de peso o salió una lección (también un
   error tuyo o de {{nombre}}), añade una línea al final de `criterio/decisiones.md`, con su
   porqué. Si no hubo, no se inventa.
3. **Apuntes de criterio.** Repasa la sesión y propón los apuntes que aparecieron, con las
   palabras de {{nombre}} entre comillas y el tipo elegido (ver la cabecera del archivo).
   Propónlos para que los **corrija**, no para que los firme: deja a la vista el punto
   discutible. Si los acepta todos tal cual, probablemente están escritos en tu voz y no en la
   suya. Solo va al final de `criterio/apuntes.md` lo que confirme. Si no propones ninguno,
   di por qué.
4. **INBOX.** Cada línea va a su archivo o se descarta. `INBOX.md` queda vacío.
5. **Si se tocó algo de `herramientas/`:** `python3 herramientas/pruebas.py`. Si falla, no se guarda.
6. **Prepara y revisa, en este orden:**
   ```
   git add -A
   python3 herramientas/revisar.py
   ```
   `revisar` mira también lo que acabas de preparar: si marca una copia de un documento, una
   imagen, un teléfono o una clave, se saca (`git rm --cached <archivo>`) antes de guardar.
7. **Guarda:**
   ```
   git commit -m "vault: <qué cambió, en una línea>"
   ```
8. **Subir lo decide {{nombre}}, no tú.** Si el vault no tiene dónde subirse (`git remote` no dice
   nada), no hay nada que subir: díselo y sigue. Si lo tiene, enséñale lo que se va a subir y
   pregúntale:
   ```
   git fetch --quiet
   git log --oneline origin/main..HEAD
   ```
   - **Si dice que sí:** `git pull --rebase origin main` y `git push origin HEAD:main`. Si el
     `push` a `main` no se deja (en la nube, por ejemplo), pide permiso para subir la rama
     (`git push -u origin HEAD`) y dile que su trabajo está a salvo en esa rama.
   - **Si dice que no:** no se sube nada. En su PC, el commit se queda guardado. **En la nube,
     avísale:** sin subir, el trabajo se pierde cuando caduca la sesión.
   - Si algún paso falla, dilo claro: **el cierre no está hecho.**
9. Dile qué archivos tocaste.
10. **Termina con tres afirmaciones sobre lo que mostró la sesión**, no sobre lo que se hizo.
    Concretas hasta poder estar equivocadas. Al menos una tiene que incomodar (algo que se va
    quedando, un proyecto parado sin decirlo, una pregunta sin contestar). Si {{nombre}} confirma
    una, es un apunte; si la rompe, su corrección es un apunte mejor.
