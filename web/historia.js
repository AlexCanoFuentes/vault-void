/* historia.js: presentación local; no crea ni publica ninguna huella. */
(() => {
  'use strict';

  const C = v => Math.max(0, Math.min(1, v));
  const suave = v => {
    const u = C(v);
    return u * u * (3 - 2 * u);
  };
  const salida = v => 1 - Math.pow(1 - C(v), 3);
  const viajar = v => {
    const u = C(v);
    return u * u * u * (10 + u * (-15 + 6 * u));
  };
  const mezclar = (a, b, t) => a + (b - a) * t;
  const RECUERDO = 'void-historia-v1';
  const NS = 'http://www.w3.org/2000/svg';

  function caida(s) {
    const g = 2 * 42 / (.26 * .26);
    if (s <= 0) return -42;
    if (s < .26) return -42 + .5 * g * s * s;

    let t = s - .26;
    let v = g * .26 * .28;

    for (let i = 0; i < 2; i++) {
      const duracion = 2 * v / g;
      if (t < duracion) return -v * t + .5 * g * t * t;
      t -= duracion;
      v *= .28;
    }
    return 0;
  }

  function guardar() {
    try {
      localStorage.setItem(RECUERDO, '1');
    } catch {}
  }

  function visto() {
    try {
      return localStorage.getItem(RECUERDO) === '1';
    } catch {
      return false;
    }
  }

  function svg(tag, attrs, padre) {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    padre.append(n);
    return n;
  }

  function iniciar(api) {
    let activa = false, preparada = false, fuente = null, impresion;
    let tiempo = 0, anterior = 0, pausa = false, estatica = false;
    let dialogo, capa, ctx, dibujo, partes, sombra, escena;
    let lineas, texto, ejemplo, crear, pausar, salir, origen;
    let dpr = 1, abortar;

    const reducida = matchMedia('(prefers-reduced-motion: reduce)');

    function colocarBoton() {
      const b = document.querySelector('#menu .primario')
        .getBoundingClientRect();

      Object.assign(crear.style, {
        left: b.left + 'px',
        top: b.top + 'px',
        width: b.width + 'px',
        height: b.height + 'px'
      });
    }

    function terminar(foco = true) {
      if (!activa) return;

      activa = false;
      guardar();
      abortar.abort();

      document.body.classList.remove('vh-activa');
      document.body.style.removeProperty('--vh-menu');
      dialogo.close();
      dialogo.remove();

      if (foco) {
        document.querySelector('#menu .primario')
          ?.focus({ preventScroll: true });
      }
      api.repintar();
    }

    function montar() {
      if (
        !window.VoidCandado ||
        typeof HTMLDialogElement === 'undefined'
      ) return;

      const estilo = document.createElement('style');
      estilo.textContent = `
.vh{
  position:fixed;inset:0;margin:0;padding:0;
  width:100%;height:100%;max-width:none;max-height:none;
  border:0;background:transparent;color:var(--tinta);overflow:auto
}
.vh::backdrop{
  background:rgb(18 17 14 / var(--vh-velo,.62))
}
.vh canvas{
  position:fixed;inset:0;pointer-events:none
}
.vh-stage{
  position:fixed;left:50%;top:37%;
  width:min(340px,78vw);aspect-ratio:300/210;
  transform:translate(-50%,-50%);
  pointer-events:none;perspective:700px
}
.vh-stage .vc{
  max-width:none;width:100%;height:100%;
  transform-origin:50% 55%
}
.vh-copy{
  position:fixed;top:59%;left:50%;
  transform:translateX(-50%);
  width:min(440px,calc(100% - 40px));
  text-align:center;pointer-events:none
}
.vh-copy p{
  margin:0;
  font:400 clamp(23px,4vw,32px)/1.18 var(--serif)
}
.vh-copy small{
  display:block;min-height:2em;margin-top:10px;
  color:var(--tinta-2);font:11px/1.4 var(--mono)
}
.vh-transport{
  position:fixed;right:16px;
  top:max(12px,env(safe-area-inset-top));
  display:flex;gap:8px
}
.vh button{
  min-height:44px;padding:8px 12px;
  border:1px solid var(--linea);border-radius:10px;
  background:var(--panel-solido);cursor:pointer
}
.vh-cta{position:fixed;white-space:nowrap}
.vh-resumen{
  position:absolute;width:1px;height:1px;
  overflow:hidden;clip-path:inset(50%)
}
body.vh-activa .menu,
body.vh-activa .mandos,
body.vh-activa .pista{
  opacity:var(--vh-menu,0)
}
.vh.estatica{
  background:rgb(18 17 14 / .9);padding:80px 24px 24px
}
.vh.estatica .vh-stage,
.vh.estatica .vh-copy,
.vh.estatica canvas{display:none}
.vh.estatica .vh-resumen{
  position:static;width:auto;height:auto;
  overflow:visible;clip-path:none;
  max-width:32em;margin:0 auto 24px;
  font:16px/1.6 var(--mono)
}
.vh.estatica .vh-cta{
  position:static;display:flex;
  width:max-content!important;height:auto!important;margin:auto
}
@media(max-height:600px){
  .vh-stage{top:32%;width:min(230px,52vw)}
  .vh-copy{top:53%}
  .vh-copy p{font-size:23px}
}`;
      document.head.append(estilo);

      dialogo = document.createElement('dialog');
      dialogo.className = 'vh';
      dialogo.setAttribute('aria-label', 'Así funciona Void');
      dialogo.setAttribute('aria-describedby', 'vh-resumen');
      dialogo.innerHTML = `
<canvas aria-hidden="true"></canvas>
<div class="vh-stage" aria-hidden="true"></div>
<div class="vh-copy" aria-hidden="true">
  <p></p><small></small>
</div>
<div class="vh-resumen" id="vh-resumen">
  <p>Tu cuaderno: guarda aquí tus ideas.</p>
  <p>Tu ayudante de IA lee lo que guardas para seguir contigo.</p>
  <p>Tus palabras se guardan bajo llave. Mientras trabajáis,
     el ayudante y Void pueden leerlas.</p>
  <p>En el lienzo se ve una huella hecha de cifras.
     Tus palabras no se muestran aquí.</p>
</div>
<div class="vh-transport">
  <button type="button" data-pausa>Pausar</button>
  <button type="button" data-salir>Ver lienzo</button>
</div>
<a class="primario vh-cta" href="/tu-huella">Crear el mío</a>`;

      document.body.append(dialogo);

      capa = dialogo.querySelector('canvas');
      ctx = capa.getContext('2d');
      if (!ctx) {
        dialogo.remove();
        return;
      }

      escena = dialogo.querySelector('.vh-stage');
      texto = dialogo.querySelector('.vh-copy p');
      ejemplo = dialogo.querySelector('.vh-copy small');
      crear = dialogo.querySelector('.vh-cta');
      pausar = dialogo.querySelector('[data-pausa]');
      salir = dialogo.querySelector('[data-salir]');

      dibujo = VoidCandado.dibujo();
      partes = dibujo.partes;
      partes.halo.remove();
      escena.append(dibujo.svg);
      dibujo.svg.setAttribute('aria-hidden', 'true');

      sombra = svg('ellipse', {
        cx: 155, cy: 202, rx: 78, ry: 4,
        fill: '#000', opacity: .3
      }, dibujo.svg);
      dibujo.svg.insertBefore(sombra, dibujo.svg.firstChild);

      lineas = [148, 163, 178].map((y, i) => svg('path', {
        d: 'M108 ' + y + 'h' + (i === 2 ? 55 : 76),
        fill: 'none',
        stroke: '#766C5A',
        'stroke-width': 2,
        'stroke-linecap': 'round',
        pathLength: 1,
        'stroke-dasharray': 1
      }, partes.diario));

      partes.arco.setAttribute(
        'd', 'M212 132v-24a14 14 0 0 1 28 0v14'
      );

      estatica = reducida.matches || innerHeight < 480;
      dialogo.classList.toggle('estatica', estatica);
      pausar.hidden = estatica;

      activa = true;
      abortar = new AbortController();
      const op = { signal: abortar.signal };

      pausar.addEventListener('click', () => {
        pausa = !pausa;
        pausar.textContent = pausa ? 'Continuar' : 'Pausar';
        anterior = 0;
      }, op);

      salir.addEventListener('click', () => terminar(), op);
      crear.addEventListener('click', guardar, op);

      dialogo.addEventListener('cancel', e => {
        e.preventDefault();
        terminar();
      }, op);

      document.addEventListener('visibilitychange', () => {
        anterior = 0;
      }, op);

      addEventListener('resize', () => terminar(), op);
      reducida.addEventListener('change', () => terminar(), op);

      dialogo.showModal();
      colocarBoton();

      const r = escena.getBoundingClientRect();
      origen = {
        x: r.left + r.width * .52,
        y: r.top + r.height * .55,
        lado: Math.min(156, r.width * .5)
      };

      dpr = Math.min(devicePixelRatio || 1, 2);
      capa.width = Math.round(innerWidth * dpr);
      capa.height = Math.round(innerHeight * dpr);
      capa.style.width = innerWidth + 'px';
      capa.style.height = innerHeight + 'px';

      document.body.classList.add('vh-activa');
      if (!estatica) pintar();
      salir.focus({ preventScroll: true });
    }

    function pintar() {
      colocarBoton();

      const t = tiempo;
      const entrada = salida(t / 480);
      const prensa = 3 * Math.sin(Math.PI * C((t - 6100) / 650));
      const retirar = suave((t - 6750) / 520);

      dibujo.svg.style.opacity =
        entrada * (1 - suave((t - 6990) / 280));
      dibujo.svg.style.transform =
        'translateY(' +
        (-14 * (1 - entrada) + prensa - 10 * retirar) + 'px) ' +
        'rotateY(' + (78 * retirar) + 'deg)';

      sombra.setAttribute('opacity', .3 * entrada);

      partes.etiquetaLineas.forEach((n, i) => {
        n.style.strokeDashoffset =
          1 - salida((t - 400 - i * 100) / 400);
      });

      lineas.forEach((n, i) => {
        n.style.strokeDashoffset =
          1 - salida((t - 650 - i * 120) / 350);
        const lee = suave((t - 1700 - i * 220) / 280);
        n.setAttribute('stroke', lee > .5 ? '#F8CB86' : '#766C5A');
      });

      const extension = C((t - 3900) / 400);
      const ancho = extension < .82
        ? 1.018 * salida(extension / .82)
        : 1 + .018 * (1 - suave((extension - .82) / .18));

      partes.correa.setAttribute(
        'transform',
        'translate(84 0) scale(' + ancho + ' 1) translate(-84 0)'
      );

      partes.candado.style.opacity = t >= 4400 ? 1 : 0;

      const s = (t - 4400) / 1000;
      const golpe = Math.max(0, s - .26);
      const giro = s < .26
        ? -7 * (1 - C(s / .26))
        : 2 * Math.exp(-14 * golpe) * Math.sin(34 * golpe);

      partes.candado.setAttribute(
        'transform',
        'translate(0 ' + caida(s) + ') rotate(' + giro + ' 226 108)'
      );
      partes.arco.setAttribute(
        'transform',
        'translate(0 ' + (-9 * (1 - suave((t - 4660) / 80))) + ')'
      );

      const frase = t < 1700
        ? 'Tu cuaderno. Guarda aquí tus ideas.'
        : t < 3900
          ? 'Tu ayudante lee lo que guardas.'
          : t < 6100
            ? 'Tus palabras, bajo llave.'
            : 'Aquí se ve su huella. Tus palabras no.';

      if (texto.textContent !== frase) texto.textContent = frase;

      if (t >= 6500 && impresion === undefined) {
        impresion = fuente;
        api.repintar();
      }

      ejemplo.textContent = t >= 6100
        ? (impresion || fuente
          ? 'Huella de ejemplo. La tuya vendrá después.'
          : 'Tu cuaderno podrá dejar su huella aquí.')
        : '';

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.clearRect(0, 0, innerWidth, innerHeight);

      if (impresion && t >= 6500) {
        const f = impresion;
        const destino = api.destino(f);
        const u = viajar((t - 7350) / 1800);

        const w0 = origen.lado * f.canvas.width /
          Math.max(f.canvas.width, f.canvas.height);
        const h0 = w0 * f.canvas.height / f.canvas.width;

        const w = mezclar(w0, destino.w, u);
        const h = mezclar(h0, destino.h, u);
        const x = mezclar(origen.x, destino.x + destino.w / 2, u);
        const y = mezclar(origen.y, destino.y + destino.h / 2, u)
          - 48 * Math.sin(Math.PI * u);

        ctx.save();
        ctx.beginPath();

        const revela = suave((t - 6500) / 550);
        ctx.rect(x - w / 2, y + h / 2 - h * revela, w, h * revela);
        ctx.clip();
        ctx.drawImage(f.canvas, x - w / 2, y - h / 2, w, h);

        ctx.restore();
      } else if (t >= 6500) {
        // Sin datos: conservar el cuaderno, sin inventar huellas públicas.
        dibujo.svg.style.opacity = 1;
        dibujo.svg.style.transform = 'none';
      }

      const entregar = suave((t - 8900) / 400);
      dialogo.style.setProperty('--vh-velo', String(.62 * (1 - entregar)));
      document.body.style.setProperty('--vh-menu', String(entregar));
      crear.style.opacity = String(1 - entregar);
    }

    if (!visto()) {
      try {
        montar();
      } catch {
        if (activa) terminar(false);
        else dialogo?.remove();
      }
    }

    return {
      get activa() {
        return activa;
      },
      get oculta() {
        return activa && !!impresion && tiempo >= 6500;
      },
      paso(now) {
        if (document.hidden) {
          anterior = 0;
          return;
        }

        // También prepara el primer plano en las visitas posteriores.
        if (!preparada) {
          try {
            const f = api.preparar();
            if (f !== null) {
              preparada = true;
              fuente = f || null;
              if (fuente) api.enfocar(fuente, true);
            }
          } catch {
            preparada = true;
          }
        }

        if (!activa || estatica) return;

        const dt = anterior ? Math.min(64, now - anterior) : 0;
        anterior = now;
        if (!pausa) tiempo += dt;

        try {
          pintar();
          if (tiempo >= 9300) terminar();
        } catch {
          terminar();
        }
      }
    };
  }

  window.VoidHistoria = { iniciar };
})();
