/* El candado de tu vault, en movimiento. Cuenta lo que pasa sin palabras técnicas:
 * tu cuaderno se cierra con tu candado, tus dos llaves salen hacia ti y Void no se queda ninguna.
 * SVG + Web Animations, sin librerías. Con «movimiento reducido», el estado final quieto. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const quieto = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SALIDA = 'cubic-bezier(.16,1,.3,1)', MUELLE = 'cubic-bezier(.34,1.56,.64,1)';
  const el = (tag, attrs = {}, padre) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); padre?.append(n); return n; };
  const esperar = (a) => a.finished.catch(() => {});

  const estilo = document.createElement('style');
  estilo.textContent = `
.vc{--vc-tinta:var(--tinta,#ECE7DE);--vc-ambar:var(--acento,#F2A93B);--vc-ambar2:var(--acento-2,#F8CB86);--vc-linea:var(--linea,#38332B);--vc-fondo:var(--fondo,var(--vacio,#12110E));display:block;width:100%;max-width:300px;height:auto;margin:0 auto;overflow:visible}
.vc .trazo{fill:none;stroke-linecap:round;stroke-linejoin:round}
.vc-llaves{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:18px 0}
.vc-llave{border:1px solid var(--linea,#38332B);border-radius:14px;padding:14px;background:color-mix(in srgb,var(--fondo,var(--vacio,#12110E)) 70%,transparent);min-width:0}
.vc-llave h3{margin:0 0 4px;font:500 15px/1.4 var(--mono,monospace);color:var(--tinta,#ECE7DE);display:flex;align-items:center;gap:8px}.vc-hueco-llave{display:inline-flex;width:22px;height:22px}
.vc-llave code{min-height:3em}
.vc-llave p{margin:0 0 10px;font-size:13px;color:var(--secundaria,var(--tinta-2,#B3AC9F))}
.vc-llave code{display:block;font:12px/1.5 var(--mono,monospace);overflow-wrap:anywhere;color:var(--acento-2,#F8CB86);user-select:all;margin-bottom:10px}
.vc-llave button{font-size:13px;padding:9px 14px}
.vc-llaves.una{grid-template-columns:1fr;max-width:340px;margin-inline:auto}
.vc-nota{font-size:14px;color:var(--secundaria,var(--tinta-2,#B3AC9F));max-width:34em}
@media(max-width:560px){.vc-llaves{grid-template-columns:1fr}}`;
  document.head.append(estilo);

  /** El dibujo: un diario (tu vault) con su correa y su candado. Se entiende sin explicarlo: es secreto y es tuyo. */
  function dibujo(etiqueta = 'Tu vault, cerrado con tu candado') {
    const svg = el('svg', { viewBox: '0 0 300 210', class: 'vc', role: 'img', 'aria-label': etiqueta });
    // El destello del clic: luz que se apaga hacia fuera, no un disco.
    const id = 'vc-luz-' + Math.random().toString(36).slice(2, 8);
    const grad = el('radialGradient', { id }, el('defs', {}, svg));
    el('stop', { offset: '0%', 'stop-color': '#F8CB86', 'stop-opacity': .55 }, grad);
    el('stop', { offset: '45%', 'stop-color': '#F2A93B', 'stop-opacity': .18 }, grad);
    el('stop', { offset: '100%', 'stop-color': '#F2A93B', 'stop-opacity': 0 }, grad);
    const halo = el('circle', { cx: 226, cy: 136, r: 62, fill: `url(#${id})`, opacity: 0 }, svg);
    const diario = el('g', {}, svg);
    el('rect', { x: 64, y: 30, width: 150, height: 168, rx: 12, fill: '#1B1915', stroke: 'var(--vc-linea)', 'stroke-width': 2 }, diario);
    el('rect', { x: 64, y: 30, width: 20, height: 168, rx: 8, fill: '#24211C' }, diario);
    el('path', { d: 'M84 30v168', class: 'trazo', stroke: 'var(--vc-linea)', 'stroke-width': 2 }, diario);
    el('rect', { x: 108, y: 58, width: 82, height: 44, rx: 6, class: 'trazo', stroke: 'var(--vc-linea)', 'stroke-width': 1.5 }, diario);
    const etiquetaLineas = [[118, 74, 60], [118, 88, 38]].map(([x, y, w]) => el('path', { d: `M${x} ${y}h${w}`, class: 'trazo', stroke: 'var(--vc-ambar2)', 'stroke-width': 3, pathLength: 1, 'stroke-dasharray': 1, 'stroke-dashoffset': 0 }, diario));
    // La correa: sale del lomo, cruza la tapa y llega al candado.
    const correa = el('rect', { x: 84, y: 118, width: 142, height: 20, rx: 4, fill: '#2E2A23', stroke: 'var(--vc-linea)', 'stroke-width': 1.5 }, svg);
    const candado = el('g', {}, svg);
    const arco = el('path', { d: 'M212 122v-14a14 14 0 0 1 28 0v14', class: 'trazo', stroke: 'var(--vc-ambar)', 'stroke-width': 6 }, candado);
    el('rect', { x: 202, y: 118, width: 48, height: 40, rx: 9, fill: 'var(--vc-ambar)' }, candado);
    el('circle', { cx: 226, cy: 134, r: 5, fill: '#1A1206' }, candado);
    el('path', { d: 'M226 137v9', class: 'trazo', stroke: '#1A1206', 'stroke-width': 3.5 }, candado);
    return { svg, partes: { halo, diario, etiquetaLineas, correa, candado, arco } };
  }

  /** Una llave suelta, en el mismo trazo que el candado (para volar y para las tarjetas). */
  function iconoLlave(tam = 30) {
    const s = el('svg', { viewBox: '0 0 30 30', width: tam, height: tam, 'aria-hidden': 'true' });
    el('circle', { cx: 10, cy: 10, r: 6.5, class: 'trazo', stroke: 'var(--acento-2,#F8CB86)', 'stroke-width': 2.6, fill: 'none' }, s);
    el('path', { d: 'M14.6 14.6L26 26m-4.5-4.5 3-3m-6-0 2.2-2.2', class: 'trazo', stroke: 'var(--acento-2,#F8CB86)', 'stroke-width': 2.6, fill: 'none', 'stroke-linecap': 'round' }, s);
    return s;
  }

  // ---- Movimiento dirigido con Codex (14-oct): peso, física de la caída y entrega exacta. ----
const vcLimitar = (v) => Math.max(0, Math.min(1, v));
const vcSalida = (v) => 1 - Math.pow(1 - vcLimitar(v), 3);
const vcSuave = (v) => {
  const t = vcLimitar(v);
  return t * t * (3 - 2 * t);
};

function vcAcabado() {
  if (estilo.dataset.acabado) return;
  estilo.dataset.acabado = '1';

  estilo.textContent += `
.vc-llave{
  display:flex;
  flex-direction:column;
  transition:border-color 180ms;
}
.vc-llave button{
  align-self:flex-start;
  margin-top:auto;
  min-height:44px;
}
.vc-hueco-llave{flex:0 0 22px}
.vc-hueco-llave svg{
  transform-box:fill-box;
  transform-origin:center;
  transition:transform 180ms;
}
.vc-pantalla button{
  transition:transform 100ms,border-color 160ms,background-color 160ms;
}
.vc-pantalla button:active:not(:disabled){
  transform:translateY(1px);
}
.vc-pantalla :focus-visible{
  outline:2px solid var(--acento-2,#F8CB86);
  outline-offset:4px;
}
.vc-pantalla button:disabled{cursor:default}
@media(hover:hover) and (pointer:fine){
  .vc-pantalla[data-lista] .vc-llave:hover{
    border-color:#766044;
  }
  .vc-pantalla[data-lista] .vc-llave:hover .vc-hueco-llave svg{
    transform:translateY(-1px) rotate(-7deg);
  }
}
@media(prefers-reduced-motion:reduce){
  .vc-pantalla button,
  .vc-llave,
  .vc-hueco-llave svg{
    transition:none!important;
  }
  .vc-pantalla button:active,
  .vc-pantalla .vc-llave:hover .vc-hueco-llave svg{
    transform:none!important;
  }
}`;
}

function vcPreparar(d) {
  if (d.preparado) return;
  d.preparado = true;
  vcAcabado();

  const p = d.partes;
  p.halo.remove();

  d.omitir = false;
  d.relojes = new Set();
  d.saltar = () => {
    d.omitir = true;
    for (const finalizar of [...d.relojes]) finalizar();
  };

  // Canto de papel, detrás de la cubierta existente.
  const paginas = el('g');
  el('rect', {
    x: 70, y: 35, width: 149, height: 160, rx: 10,
    fill: '#373128'
  }, paginas);
  el('path', {
    d: 'M215 48v132M217 54v120',
    fill: 'none', stroke: '#615544', 'stroke-width': 1
  }, paginas);
  p.diario.insertBefore(paginas, p.diario.firstChild);

  el('path', {
    d: 'M79 31H201',
    fill: 'none', stroke: '#ECE7DE',
    'stroke-width': 1, opacity: .12
  }, p.diario);

  // Una pata larga permanece dentro del cuerpo al abrir.
  p.arco.setAttribute(
    'd', 'M212 132v-24a14 14 0 0 1 28 0v14'
  );

  el('path', {
    d: 'M212 120h28',
    fill: 'none', stroke: '#F8CB86',
    'stroke-width': 1.5, 'stroke-linecap': 'round',
    opacity: .7
  }, p.candado);

  const suelo = el('ellipse', {
    cx: 155, cy: 202, rx: 76, ry: 5,
    fill: '#000', opacity: .28
  }, d.svg);
  suelo.style.filter = 'blur(2px)';

  // Todos reciben juntos la pequeña sacudida del contacto.
  const escena = el('g', {}, d.svg);
  escena.append(p.diario, p.correa);

  const sombra = el('rect', {
    x: 203, y: 119, width: 48, height: 40, rx: 9,
    fill: '#000', opacity: .22
  }, escena);
  escena.append(p.candado);

  Object.assign(p, { escena, suelo, sombra });

  for (const [nodo, origen] of [
    [escena, '150px 114px'],
    [suelo, '155px 202px'],
    [p.correa, '84px 128px'],
    [p.candado, '226px 108px'],
    [sombra, '226px 138px']
  ]) {
    nodo.style.transformBox = 'view-box';
    nodo.style.transformOrigin = origen;
  }
}

// Un reloj común: sin animaciones con fill que sigan reteniendo estilos.
function vcReloj(d, duracion, pintar) {
  return new Promise((resolve, reject) => {
    const inicio = performance.now();
    let raf = 0;
    let terminado = false;

    function limpiar() {
      terminado = true;
      cancelAnimationFrame(raf);
      d.relojes.delete(finalizar);
      document.removeEventListener('visibilitychange', visibilidad);
    }

    function aplicar(t) {
      try {
        pintar(t);
        return true;
      } catch (error) {
        limpiar();
        reject(error);
        return false;
      }
    }

    function finalizar() {
      if (terminado) return;
      limpiar();
      if (aplicar(duracion)) resolve();
    }

    function visibilidad() {
      if (document.hidden) d.saltar();
    }

    function paso(ahora) {
      if (terminado) return;
      if (
        d.omitir || quieto() || document.hidden ||
        !d.svg.isConnected || ahora - inicio >= duracion
      ) {
        finalizar();
        return;
      }

      if (aplicar(ahora - inicio)) {
        raf = requestAnimationFrame(paso);
      }
    }

    d.relojes.add(finalizar);
    document.addEventListener('visibilitychange', visibilidad);

    // Prepara el fotograma inicial antes de que el navegador pinte.
    paso(inicio);
  });
}

function vcCaida(segundos) {
  const altura = 42;
  const tiempoCaida = .260;
  const gravedad = 2 * altura / (tiempoCaida * tiempoCaida);
  const restitucion = .28;

  if (segundos <= 0) return -altura;
  if (segundos < tiempoCaida) {
    return -altura + .5 * gravedad * segundos * segundos;
  }

  let t = segundos - tiempoCaida;
  let velocidad = gravedad * tiempoCaida * restitucion;

  for (let i = 0; i < 2; i++) {
    const duracion = 2 * velocidad / gravedad;
    if (t < duracion) {
      return -velocidad * t + .5 * gravedad * t * t;
    }
    t -= duracion;
    velocidad *= restitucion;
  }

  return 0;
}

async function cerrar(d) {
  vcPreparar(d);

  const {
    escena, suelo, sombra, etiquetaLineas,
    correa, candado, arco
  } = d.partes;

  await vcReloj(d, 1260, (t) => {
    const entrada = vcSalida(t / 360);
    const despuesDelGolpe = Math.max(0, (t - 900) / 1000);

    const sacudida = t >= 900
      ? 1.2 * Math.exp(-18 * despuesDelGolpe) *
        Math.sin(42 * despuesDelGolpe)
      : 0;

    escena.style.opacity = entrada;
    escena.style.transform =
      `translateY(${14 * (1 - entrada) + sacudida}px) ` +
      `rotate(${-2 * (1 - entrada)}deg)`;

    suelo.style.opacity = .28 * entrada;
    suelo.style.transform = `scaleX(${1.12 - .12 * entrada})`;

    etiquetaLineas.forEach((linea, i) => {
      linea.style.strokeDashoffset =
        1 - vcSalida((t - 100 - i * 60) / 360);
    });

    const u = vcLimitar((t - 260) / 380);
    const extension = u < .82
      ? 1.018 * vcSalida(u / .82)
      : 1 + .018 * (1 - vcSuave((u - .82) / .18));

    correa.style.transform = `scaleX(${extension})`;

    const cayendo = t >= 640;
    const y = vcCaida((t - 640) / 1000);
    const altura = vcLimitar(-y / 42);

    const giro = t < 900
      ? -7 * (1 - vcLimitar((t - 640) / 260))
      : 2.3 * Math.exp(-10 * despuesDelGolpe) *
        Math.sin(30 * despuesDelGolpe);

    candado.style.opacity = cayendo ? 1 : 0;
    candado.style.transform = `translateY(${y}px) rotate(${giro}deg)`;

    // El arco termina de entrar después del contacto.
    const cierre = vcSuave((t - 900) / 80);
    arco.style.transform = `translateY(${-9 * (1 - cierre)}px)`;

    sombra.style.opacity = cayendo ? .26 - .20 * altura : 0;
    sombra.style.filter = `blur(${1 + 2 * altura}px)`;
    sombra.style.transform =
      `translate(2px,${3 + 7 * altura}px) scale(${1 + .12 * altura})`;

    if (t === 1260) {
      escena.style.transform = 'none';
      candado.style.transform = 'none';
      arco.style.transform = 'none';
    }
  });
}

async function abrir(d) {
  vcPreparar(d);
  d.saltar();
  d.omitir = false;

  await vcReloj(d, 520, (t) => {
    // Cede un píxel antes de liberarse.
    const y = t < 70
      ? vcSuave(t / 70)
      : 1 - 10 * vcSalida((t - 70) / 230);

    const u = vcLimitar((t - 70) / 450);
    const giro = -3 * Math.sin(Math.PI * u) * (1 - u);

    d.partes.arco.style.transform = `translateY(${y}px)`;
    d.partes.candado.style.transform = `rotate(${giro}deg)`;

    if (t === 520) {
      d.partes.candado.style.transform = 'none';
    }
  });

  d.svg.setAttribute('aria-label', 'Tu vault, con el candado abierto');
}

async function volar(d, destino, retraso = 0, lado = -1) {
  vcPreparar(d);
  await vcReloj(d, retraso, () => {});

  const fin = destino.getBoundingClientRect();
  const matriz = d.partes.candado.getScreenCTM();

  if (
    d.omitir || quieto() || !d.svg.isConnected || !matriz ||
    fin.width === 0 || fin.top < 0 || fin.bottom > innerHeight
  ) {
    destino.style.opacity = 1;
    return;
  }

  // Coordenadas reales del SVG, incluso si está escalado.
  const punto = d.svg.createSVGPoint();
  punto.x = 226;
  punto.y = 134;
  const origen = punto.matrixTransform(matriz);

  const a = { x: origen.x, y: origen.y + 3 };
  const b = { x: origen.x + lado * 64, y: origen.y - 72 };
  const z = {
    x: fin.left + fin.width / 2,
    y: fin.top + fin.height / 2
  };
  const c = { x: z.x - lado * 36, y: z.y - 48 };

  const llave = iconoLlave(30);
  Object.assign(llave.style, {
    position: 'fixed',
    left: '0',
    top: '0',
    zIndex: '50',
    pointerEvents: 'none',
    transformOrigin: '15px 15px',
    filter: 'drop-shadow(0 2px 1px rgba(0,0,0,.4))'
  });
  document.body.append(llave);

  const escalaFinal = fin.width / 30;

  try {
    await vcReloj(d, 600, (t) => {
      let x, y, escala, giro;

      if (t < 70) {
        // Anticipación pequeña, dentro de la salida del ojo.
        const u = vcSuave(t / 70);
        x = origen.x;
        y = origen.y + 3 * u;
        escala = .4 + .15 * u;
        giro = lado * -12 * u;
        llave.style.opacity = u;
      } else {
        const u = vcSuave((t - 70) / 530);
        const v = 1 - u;

        x = v ** 3 * a.x + 3 * v * v * u * b.x +
            3 * v * u * u * c.x + u ** 3 * z.x;
        y = v ** 3 * a.y + 3 * v * v * u * b.y +
            3 * v * u * u * c.y + u ** 3 * z.y;

        escala = .55 + (escalaFinal - .55) * u +
          .25 * Math.sin(Math.PI * u);
        giro = lado * (-12 * (1 - u) + 28 * Math.sin(Math.PI * u));
        llave.style.opacity = 1;
      }

      llave.style.transform =
        `translate3d(${x - 15}px,${y - 15}px,0) ` +
        `rotate(${giro}deg) scale(${escala})`;
    });
  } finally {
    // Misma posición, orientación y tamaño: no hay salto.
    destino.style.opacity = 1;
    llave.remove();
  }
}

async function descifrar(nodo, texto, d) {
  texto = String(texto);
  nodo.style.opacity = 1;

  if (d.omitir || quieto() || !d.svg.isConnected) {
    if (nodo.textContent !== texto) nodo.textContent = texto;
    return;
  }

  const fragmento = document.createDocumentFragment();
  const letras = Array.from(texto, (caracter) => {
    const letra = document.createElement('span');
    letra.textContent = caracter;
    letra.style.opacity = '.35';
    fragmento.append(letra);
    return letra;
  });
  nodo.replaceChildren(fragmento);

  const tarjeta = nodo.closest('.vc-llave');
  const icono = tarjeta?.querySelector('.vc-hueco-llave svg');

  if (tarjeta) tarjeta.style.borderColor = '#F8CB86';

  try {
    await vcReloj(d, 320, (t) => {
      const u = t / 320;
      const frente = u * (letras.length + 5);

      letras.forEach((letra, i) => {
        const tinta = vcSuave((frente - i) / 5);
        letra.style.opacity = .35 + .65 * tinta;
      });

      if (icono) {
        const resto = Math.exp(-8 * u) * Math.sin(12 * u);
        icono.style.transform =
          `translateY(${resto}px) rotate(${2 * resto}deg)`;
      }
    });
  } finally {
    for (const letra of letras) letra.style.removeProperty('opacity');
    tarjeta?.style.removeProperty('border-color');
    icono?.style.removeProperty('transform');
  }
}

  const descargar = (nombre, texto) => { const u = URL.createObjectURL(new Blob([texto], { type: 'text/plain;charset=utf-8' })); const a = document.createElement('a'); a.href = u; a.download = nombre; a.click(); setTimeout(() => URL.revokeObjectURL(u), 1000); };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  /** La pantalla de tus llaves: el candado se cierra, tus llaves vuelan a ti y se enseñan UNA vez. */
function pantallaLlaves(
  contenedor,
  { alias, codigo, kit, titulo, alListo }
) {
  const d = dibujo();
  vcPreparar(d);

  const tarjetas = [];
  if (codigo) tarjetas.push([
    'Tu código',
    'La llave de todos los días. Con ella entras desde cualquier sitio.',
    String(codigo),
    'mi-codigo-void.txt'
  ]);
  if (kit) tarjetas.push([
    'Tu kit de recuperación',
    'La llave de repuesto. Guárdala lejos del código: si pierdes uno, el otro te abre.',
    String(kit),
    'mi-kit-void.txt'
  ]);

  // titulo conserva el contrato HTML del módulo original.
  contenedor.innerHTML = `
    <div class="vc-pantalla" style="width:min(560px,100%);margin:0 auto">
      <div class="vc-hueco"></div>
      <h2 style="text-align:center;margin:8px 0 6px">
        ${titulo || 'Tu espacio tiene candado. <em>Las llaves son tuyas.</em>'}
      </h2>
      <p class="vc-nota" style="margin:0 auto;text-align:center">
        Nosotros no tenemos ninguna. Si un día dejamos de existir,
        tu vault sigue siendo tuyo. ${tarjetas.length > 1 ? 'Te las enseñamos' : 'Te la enseñamos'} <b>solo esta vez</b>.
      </p>
      <div class="vc-llaves${tarjetas.length > 1 ? '' : ' una'}">
        ${tarjetas.map(([nombre, descripcion, valor], i) => `
          <div class="vc-llave">
            <h3>
              <span class="vc-hueco-llave"></span>${esc(nombre)}
            </h3>
            <p>${esc(descripcion)}</p>
            <code style="opacity:${quieto() ? 1 : .35}">${esc(valor)}</code>
            <button type="button" data-i="${i}">
              Guardar en un archivo
            </button>
          </div>
        `).join('')}
      </div>
      <label class="consentimiento">
        <input type="checkbox" class="vc-guardado">
        ${tarjetas.length > 1
          ? 'He guardado mis dos llaves, cada una en un sitio distinto.'
          : 'He guardado mi llave en un lugar privado.'}
      </label>
      <div class="fila" style="margin-top:14px">
        <button type="button" class="principal vc-listo" disabled>
          Abrir mi espacio
        </button>
      </div>
      <p class="estado vc-estado" role="status"></p>
    </div>`;

  const raiz = contenedor.querySelector('.vc-pantalla');
  raiz.querySelector('.vc-hueco').append(d.svg);

  const huecos = [...raiz.querySelectorAll('.vc-llave')];
  const listo = raiz.querySelector('.vc-listo');
  const guardado = raiz.querySelector('.vc-guardado');
  const estado = raiz.querySelector('.vc-estado');
  let entrando = false;

  for (const tarjeta of huecos) {
    const icono = iconoLlave(22);
    icono.style.opacity = quieto() ? 1 : 0;
    tarjeta.querySelector('.vc-hueco-llave').append(icono);
  }

  for (const boton of raiz.querySelectorAll('[data-i]')) {
    boton.onclick = () => {
      d.saltar();
      const [nombre, , valor, archivo] = tarjetas[Number(boton.dataset.i)];
      descargar(
        archivo,
        `Void · @${alias}\nhttps://vaultvoid.app/mi-vault\n${nombre}: ${valor}\n`
      );
      // El navegador inicia la descarga; no sabemos si ya la guardaron.
      boton.textContent = 'Descarga iniciada ✓';
    };
  }

  guardado.onchange = () => {
    listo.disabled = entrando || !guardado.checked;
  };

  listo.onclick = async () => {
    if (entrando || !guardado.checked) return;
    d.saltar();
    entrando = true;
    listo.disabled = true;
    estado.textContent = 'Abriendo tu espacio…';

    try {
      await alListo();
    } catch (error) {
      entrando = false;
      estado.textContent = error?.message || 'No se pudo abrir. Prueba otra vez.';
      listo.disabled = !guardado.checked;
    }
  };

  // Si la persona empieza a usar la pantalla, terminamos la presentación.
  const eventos = new AbortController();
  const opciones = { signal: eventos.signal };
  const saltar = () => d.saltar();

  raiz.addEventListener('pointerdown', saltar, opciones);
  raiz.addEventListener('focusin', saltar, opciones);
  window.addEventListener('resize', saltar, opciones);
  window.addEventListener('scroll', saltar, {
    ...opciones, capture: true, passive: true
  });

  (async () => {
    try {
      await cerrar(d);

      await Promise.all(huecos.map(async (tarjeta, i) => {
        const icono = tarjeta.querySelector('.vc-hueco-llave svg');
        await volar(d, icono, i * 120, i === 0 ? -1 : 1);
        await descifrar(
          tarjeta.querySelector('code'),
          tarjetas[i][2],
          d
        );
      }));
    } catch {
      // Una presentación fallida nunca debe ocultar las llaves.
      d.saltar();
    } finally {
      eventos.abort();
      raiz.dataset.lista = '';

      huecos.forEach((tarjeta, i) => {
        const code = tarjeta.querySelector('code');
        if (code.textContent !== tarjetas[i][2]) {
          code.textContent = tarjetas[i][2];
        }
        code.style.opacity = 1;
        tarjeta.style.removeProperty('border-color');

        const icono = tarjeta.querySelector('.vc-hueco-llave svg');
        icono.style.opacity = 1;
        icono.style.removeProperty('transform');
      });
    }
  })();

  return d;
}

  window.VoidCandado = { dibujo, cerrar, abrir, pantallaLlaves };
})();
