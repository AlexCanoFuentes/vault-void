// Un solo aviso para la portada, el final del cuento y el espacio privado.
(() => {
  'use strict';
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/trabajador.js').catch(() => {});
  const modo = matchMedia('(display-mode: standalone)');
  let instalada = modo.matches || navigator.standalone === true;
  const ua = navigator.userAgent;
  const ios = /iPhone|iPad|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  // Safari permite añadir a inicio manualmente. No ofrecemos pasos en navegadores integrados.
  const safari = ios && /Version\/.*Safari\//.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS|GSA|FBAN|FBAV|Instagram/.test(ua);
  let oferta = null, esperando = false, numero = 0;
  const avisos = new Set();

  function actualizar() {
    for (const aviso of avisos) {
      if (!aviso.caja.isConnected) { avisos.delete(aviso); continue; }
      aviso.caja.hidden = instalada || (!oferta && !safari);
      aviso.boton.disabled = esperando;
      if (instalada) {
        aviso.ayuda.hidden = true;
        aviso.boton.setAttribute('aria-expanded', 'false');
      }
    }
  }

  function montar(caja) {
    if (!caja || caja.dataset.instalarListo) return;
    caja.dataset.instalarListo = 'true';
    const id = 'instalar-iphone-' + (++numero);
    caja.innerHTML = `<button type="button" class="secundario">Instalar Void</button><p id="${id}" hidden>En Safari, pulsa Compartir, elige «Añadir a pantalla de inicio» y confirma con «Añadir». Si no ves la opción, busca en «Editar acciones».</p>`;
    const boton = caja.querySelector('button'), ayuda = caja.querySelector('p');
    if (safari) {
      boton.setAttribute('aria-controls', id);
      boton.setAttribute('aria-expanded', 'false');
    }
    avisos.add({caja, boton, ayuda});
    boton.onclick = async () => {
      if (instalada || esperando) return;
      if (!oferta) {
        if (safari) {
          ayuda.hidden = !ayuda.hidden;
          boton.setAttribute('aria-expanded', String(!ayuda.hidden));
        }
        return;
      }
      const aviso = oferta;
      oferta = null; esperando = true;
      boton.disabled = true;
      try {
        await aviso.prompt();
        await aviso.userChoice;
      } catch {
        // Si el navegador retira su oferta, esperamos a que vuelva a ofrecerla.
      } finally {
        esperando = false;
        actualizar();
      }
    };
    actualizar();
  }

  addEventListener('beforeinstallprompt', e => {
    e.preventDefault();
    if (instalada) return;
    oferta = e;
    actualizar();
  });
  // Punto preparado para medir en el dispositivo. No envía ni guarda datos.
  addEventListener('appinstalled', () => {
    instalada = true; oferta = null;
    actualizar();
  });
  modo.addEventListener('change', e => {
    instalada = e.matches || navigator.standalone === true;
    actualizar();
  });
  window.VoidInstalar = {montar};
  document.querySelectorAll('[data-instalar]').forEach(montar);
})();
