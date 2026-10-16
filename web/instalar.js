// Acceso directo en el móvil [16-oct]. En Android, el botón aparece cuando el navegador lo ofrece; en el iPhone se explica.
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('/trabajador.js').catch(() => {});
  const instalada = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const caja = $('acceso-directo'); if (!caja) return;
  if (instalada) { caja.hidden = true; return; }
  const iphone = /iPhone|iPad|iPod/.test(navigator.userAgent);
  $('acceso-iphone').hidden = !iphone;
  let oferta = null;
  addEventListener('beforeinstallprompt', e => { e.preventDefault(); oferta = e; $('acceso-boton').hidden = false; });
  $('acceso-boton').onclick = async () => {
    if (!oferta) return;
    oferta.prompt();
    const r = await oferta.userChoice.catch(() => null);
    oferta = null; $('acceso-boton').hidden = true;
    $('acceso-estado').textContent = r?.outcome === 'accepted' ? 'Listo: ya lo tienes en tu pantalla de inicio.' : '';
  };
})();
