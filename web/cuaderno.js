/* Continúa el cuaderno de historia.js. No guarda ni envía datos. */
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const media = matchMedia('(prefers-reduced-motion: reduce)');
  const raiz = document.createElement('div');
  raiz.id = 'cuaderno';
  raiz.hidden = true;
  raiz.setAttribute('aria-hidden', 'true');
  document.body.append(raiz);
  const d = VoidCandado.dibujo();
  d.svg.setAttribute('viewBox', '44 10 190 210');
  d.partes.halo.remove();
  d.partes.correa.remove();
  d.partes.candado.remove();
  raiz.append(d.svg);
  const nodo = (tag, attrs) => {
    const n = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    d.partes.diario.append(n);
    return n;
  };
  // Una hoja sobre el mismo lomo y las mismas tapas de la portada.
  nodo('rect', {x:90, y:40, width:114, height:148, rx:3, fill:'#24211C'});
  const filas = Array.from({length:7}, (_, j) => {
    const y = 58 + j * 18;
    nodo('path', {d:'M100 '+(y+4)+'h94', stroke:'#514A3E', 'stroke-width':.6});
    return nodo('text', {x:100, y, 'font-size':8, 'font-family':'monospace', fill:'#B3AC9F'});
  });
  let revelada = false, imprimiendo = false, animacion = null;
  const finalizar = () => {
    revelada = true;
    imprimiendo = false;
    raiz.hidden = true;
    raiz.style.opacity = '';
    d.svg.style.transform = '';
  };
  window.VoidCuaderno = {
    get revelada() { return revelada; },
    reiniciar() {
      animacion?.cancel();
      revelada = false;
      imprimiendo = false;
      filas.forEach(n => n.textContent = '');
    },
    llenar(respuestas, hasta, colores) {
      filas.forEach((n, j) => {
        const texto = j < hasta && respuestas[j]
          ? respuestas[j].trim().replace(/\s+/g, ' ') : '';
        const letras = Array.from(texto);
        n.textContent = letras.length > 17 ? letras.slice(0, 16).join('') + '…' : texto;
        n.setAttribute('fill', 'rgb(' + colores[j].join(',') + ')');
      });
    },
    colocar(cx, cy, r, dpr, visible) {
      raiz.hidden = !visible || (revelada && !imprimiendo);
      raiz.style.left = cx / dpr + 'px';
      raiz.style.top = cy / dpr + 'px';
      raiz.style.width = Math.min(320, r * 1.45 / dpr) + 'px';
    },
    async imprimir() {
      if (revelada) return;
      if (media.matches || document.hidden || document.body.classList.contains('compacta')) {
        finalizar();
        return;
      }
      imprimiendo = true;
      // Levantar, caer por gravedad, rebotar perdiendo energía, retirar.
      const cuadros = [];
      const g = 2 * 12 / (.18 * .18);
      for (let ms = 0; ms <= 900; ms += 15) {
        let y = 0, opacidad = 1;
        if (ms < 180) {
          const u = ms / 180;
          y = -12 * u * u * (3 - 2 * u);
        } else if (ms < 360) {
          y = -12 + .5 * g * Math.pow((ms - 180) / 1000, 2);
        } else if (ms < 500) {
          const t = (ms - 360) / 1000, v = g * .18 * .2;
          y = t < 2 * v / g ? -v * t + .5 * g * t * t : 0;
        } else {
          const u = (ms - 500) / 400;
          y = -40 * u * u;
          opacidad = 1 - u;
        }
        cuadros.push({offset:ms / 900, transform:'translateY('+y+'px)', opacity:opacidad});
      }
      animacion = d.svg.animate(cuadros, {duration:900, fill:'forwards', easing:'linear'});
      const revelar = () => {
        if (!imprimiendo) return;
        if (Number(animacion.currentTime) >= 360) revelada = true;
        requestAnimationFrame(revelar);
      };
      const omitir = () => animacion?.finish();
      // En el móvil, la barra de direcciones y el teclado cambian la altura y disparan «resize»: eso no la salta.
      // Solo un cambio de ancho (girar el teléfono) la termina de golpe (15-oct).
      const ancho0 = innerWidth, siGira = () => { if (Math.abs(innerWidth - ancho0) > 2) omitir(); };
      addEventListener('resize', siGira);
      media.addEventListener('change', omitir);
      document.addEventListener('visibilitychange', omitir);
      requestAnimationFrame(revelar);
      try { await animacion.finished; } catch {}
      finally {
        finalizar();
        animacion.cancel();
        animacion = null;
        removeEventListener('resize', siGira);
        media.removeEventListener('change', omitir);
        document.removeEventListener('visibilitychange', omitir);
      }
    }
  };
})();
