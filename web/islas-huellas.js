/* M-09 · la vista por defecto del archipiélago: cada isla es una huella [21-oct, decisión del responsable del producto:
   «1 si (...) 2 a» y «dejamos el dibujo de las islas como opcion visual? si»].
   Usa el mismo motor del lienzo (huella.js, Gray-Scott): cada isla es un territorio y donde dos se tocan se mezclan.
   La forma sale de lo que la isla tiene dentro (tareas hechas frente a pendientes, cuánto contiene, cuándo se tocó por
   última vez). Esto solo lo ve su dueño: fuera, la huella será la fusión de todas, sin bordes (fase 2).
   Misma forma de uso que islas-paisaje.js (pintar, seleccionar, destruir), para que islas.js cambie de vista sin más. */
(()=>{
'use strict';
window.VoidHuellasIslas = function(contenedor, etiquetas, {abrir, fallo}) {
  if (!window.VoidHuella) throw Error('No se pudo cargar la vista de huellas. Puedes usar la lista.');
  const N = 150, lienzo = document.createElement('canvas');
  lienzo.width = lienzo.height = N; lienzo.className = 'islas-huellas'; lienzo.setAttribute('aria-hidden', 'true');
  contenedor.prepend(lienzo); contenedor.classList.add('vista-huellas');
  const ctx = lienzo.getContext('2d');
  if (!ctx) { lienzo.remove(); throw Error('No se pudo dibujar la vista de huellas. Puedes usar la lista.'); }
  const reducido = matchMedia('(prefers-reduced-motion: reduce)');
  let campo = null, raf = 0, pasos = 0, destruido = false, seleccion = null;

  function tono(hex) { // el color que eligió la persona, como tono del motor
    const n = parseInt(String(hex).slice(1), 16), r = (n >> 16 & 255) / 255, g = (n >> 8 & 255) / 255, b = (n & 255) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
    if (!d) return 0;
    const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return Math.round((h * 60 + 360) % 360);
  }
  function cifras(d) { // de dentro de la isla, sin leer textos: solo cuántos y cuándo
    if (d.destino) return {dias: 120, pulso: 30, decisiones: 3, proyectos: 3, calladas: 0, tono: tono(d.color)};
    let hechas = 0, pendientes = 0, otros = 0;
    for (const b of d.bloques || []) {
      if (b.tipo === 'tareas') for (const t of b.items) t.hecho ? hechas++ : pendientes++;
      else if (b.tipo === 'tabla') otros += b.filas.length;
      else if (b.tipo === 'nota') otros += b.texto.trim() ? 1 : 0;
      else otros++;
    }
    const edad = d.actualizado ? (Date.now() - Date.parse(d.actualizado)) / 864e5 : 30;
    return {dias: Math.min(365, 40 + 25 * (hechas + pendientes + otros)), pulso: Math.max(5, 60 - 2 * edad),
            decisiones: hechas + 1, proyectos: pendientes + otros + 1, calladas: 0, tono: tono(d.color)};
  }
  function etiquetar(datos) {
    etiquetas.replaceChildren();
    for (const t of campo.territorios) {
      const d = datos.find(x => x.id === t.alias); if (!d) continue;
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'islas-huella-etiqueta'; b.dataset.id = d.id; b.textContent = d.nombre;
      b.style.left = Math.min(84, Math.max(16, t.x / N * 100)) + '%'; b.style.top = Math.min(94, Math.max(6, t.y / N * 100)) + '%';
      b.setAttribute('aria-pressed', String(d.id === seleccion));
      b.onclick = () => abrir(d.id);
      etiquetas.append(b);
    }
  }
  function bucle() {
    if (destruido) return;
    campo.paso(8); pasos += 8; campo.pintar(ctx, false);
    if (pasos < 2400 && !document.hidden) raf = requestAnimationFrame(bucle);
  }
  function pintar(datos, actual) {
    seleccion = actual; cancelAnimationFrame(raf);
    try {
      campo = VoidHuella.crear(datos.map(d => ({alias: d.id, semilla: d.id, huella: cifras(d)})), N, 0);
    } catch { fallo('No se pudo dibujar la vista de huellas. Puedes seguir en la lista.'); return; }
    pasos = 0; etiquetar(datos);
    if (reducido.matches) { campo.paso(1600); campo.pintar(ctx, false); } else bucle();
  }
  return {
    pintar,
    seleccionar(id) { seleccion = id; for (const b of etiquetas.children) b.setAttribute('aria-pressed', String(b.dataset.id === id)); },
    destruir() { destruido = true; cancelAnimationFrame(raf); lienzo.remove(); contenedor.classList.remove('vista-huellas'); etiquetas.replaceChildren(); }
  };
};
})();
