/* M-09 · la vista por defecto del archipiélago: cada isla es una huella [21-oct, decisión del responsable del producto:
   «1 si (...) 2 a» y «dejamos el dibujo de las islas como opcion visual? si»].
   Usa el mismo motor del lienzo (huella.js, Gray-Scott): cada isla es un territorio y donde dos se tocan se mezclan.
   La forma sale de lo que la isla tiene dentro (tareas hechas frente a pendientes, cuánto contiene, cuándo se tocó por
   última vez). Esto solo lo ve su dueño: fuera, la huella será la fusión de todas, sin bordes (fase 2).
   Misma forma de uso que islas-paisaje.js (pintar, seleccionar, destruir), para que islas.js cambie de vista sin más. */
(()=>{
'use strict';
window.VoidHuellasIslas = function(contenedor, etiquetas, {abrir, mover, fallo}) {
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
  // Sitio fijo de las islas de siempre: no se arrastran (no son del vault) y así no tapan las propias.
  const FIJAS = {fija_hablar: {x: .18, y: .2}, fija_comunidad: {x: .82, y: .2}, fija_modelos: {x: .18, y: .82}, fija_cuidar: {x: .82, y: .82}};
  const sitioDe = d => d.destino ? FIJAS[d.id] || {x: .5, y: .5} : d.posicion;
  // [21-oct] Arrastrar las huellas propias, suponiendo que alguien lo hará mal a propósito: se queda dentro del
  // recuadro, no se suelta encima de otra (se aparta), un toque corto no es arrastre, soltar fuera o cancelar
  // devuelve la huella a su sitio, y las flechas guardan una sola vez cuando dejas de pulsar.
  let datosActuales = [], tecla = null;
  const libre = (id, x, y) => {
    for (let vuelta = 0; vuelta < 12; vuelta++) {
      const choque = datosActuales.find(o => o.id !== id && Math.hypot((sitioDe(o).x - x), (sitioDe(o).y - y)) < .12);
      if (!choque) break;
      const s = sitioDe(choque), a = Math.atan2(y - s.y, x - s.x) || vuelta;
      x = s.x + Math.cos(a) * .13; y = s.y + Math.sin(a) * .13;
    }
    return {x: Math.round(Math.min(.92, Math.max(.08, x)) * 1000) / 1000, y: Math.round(Math.min(.92, Math.max(.08, y)) * 1000) / 1000};
  };
  function colocar(b, x, y) { b.style.left = Math.min(84, Math.max(16, x * 100)) + '%'; b.style.top = Math.min(94, Math.max(6, y * 100)) + '%'; }
  function arrastrable(b, d) {
    let inicio = null, arrastrando = false;
    b.addEventListener('pointerdown', e => { if (e.button !== 0 || etiquetas.inert) return; inicio = {x: e.clientX, y: e.clientY, id: e.pointerId}; arrastrando = false; });
    b.addEventListener('pointermove', e => {
      if (!inicio || e.pointerId !== inicio.id) return;
      if (!arrastrando && Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) < 10) return; // un toque no es arrastre
      if (!arrastrando) { arrastrando = true; b.setPointerCapture(e.pointerId); b.classList.add('arrastrando'); }
      const r = contenedor.getBoundingClientRect();
      colocar(b, (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
    });
    const soltar = (e, vale) => {
      if (!inicio) return;
      const era = arrastrando; inicio = null; arrastrando = false; b.classList.remove('arrastrando');
      if (!era) return;
      const r = contenedor.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      const dentro = vale && x > -.05 && x < 1.05 && y > -.05 && y < 1.05;
      if (!dentro) { colocar(b, sitioDe(d).x, sitioDe(d).y); return; } // soltar fuera o cancelar: vuelve a su sitio
      const nuevo = libre(d.id, x, y); colocar(b, nuevo.x, nuevo.y); mover(d.id, nuevo);
      b.dataset.recienMovida = '1'; setTimeout(() => delete b.dataset.recienMovida, 300);
    };
    b.addEventListener('pointerup', e => soltar(e, true));
    b.addEventListener('pointercancel', e => soltar(e, false));
    b.addEventListener('keydown', e => {
      const paso = {ArrowLeft: [-.03, 0], ArrowRight: [.03, 0], ArrowUp: [0, -.03], ArrowDown: [0, .03]}[e.key];
      if (!paso || etiquetas.inert) return;
      e.preventDefault();
      const s = b._sitio || sitioDe(d), nuevo = libre(d.id, s.x + paso[0], s.y + paso[1]);
      b._sitio = nuevo; colocar(b, nuevo.x, nuevo.y);
      clearTimeout(tecla); tecla = setTimeout(() => { delete b._sitio; mover(d.id, nuevo); }, 450); // una sola vez al soltar
    });
  }
  function etiquetar(datos) {
    datosActuales = datos; etiquetas.replaceChildren();
    for (const t of campo.territorios) {
      const d = datos.find(x => x.id === t.alias); if (!d) continue;
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'islas-huella-etiqueta'; b.dataset.id = d.id; b.textContent = d.nombre;
      colocar(b, t.x / N, t.y / N);
      b.setAttribute('aria-pressed', String(d.id === seleccion));
      if (d.destino) b.dataset.fija = '1';
      else { b.setAttribute('aria-description', 'Arrastra o usa las flechas para moverla.'); if (mover) arrastrable(b, d); }
      b.onclick = () => { if (!b.dataset.recienMovida) abrir(d.id); };
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
      campo = VoidHuella.crear(datos.map(d => ({alias: d.id, semilla: d.id, pos: sitioDe(d), huella: cifras(d)})), N, 0);
    } catch { fallo('No se pudo dibujar la vista de huellas. Puedes seguir en la lista.'); return; }
    pasos = 0; etiquetar(datos);
    if (reducido.matches) { campo.paso(1600); campo.pintar(ctx, false); } else bucle();
  }
  return {
    pintar,
    seleccionar(id) { seleccion = id; for (const b of etiquetas.children) b.setAttribute('aria-pressed', String(b.dataset.id === id)); },
    destruir() { destruido = true; cancelAnimationFrame(raf); clearTimeout(tecla); lienzo.remove(); contenedor.classList.remove('vista-huellas'); etiquetas.replaceChildren(); }
  };
};
})();
