/* Avisos en el móvil (23-oct).
   Un botón en Comunidad apunta este navegador para el espacio abierto, o lo borra. El aviso llega vacío. */
(() => {
  'use strict';
  const boton = document.getElementById('avisos-movil'), nota = document.getElementById('avisos-movil-nota');
  if (!boton) return;
  let apuntado = false, clave = null;
  const decir = (t) => { nota.textContent = t; nota.hidden = !t; };
  const bytes = (b64) => { const s = atob(b64.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - b64.length % 4) % 4)); return Uint8Array.from(s, (c) => c.charCodeAt(0)); };
  const soporta = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  const iphone = () => /iP(hone|ad|od)/.test(navigator.userAgent) && !matchMedia('(display-mode: standalone)').matches;
  async function suscripcion() { const r = await navigator.serviceWorker.ready; return r.pushManager.getSubscription(); }
  function pintar() {
    boton.textContent = apuntado ? 'Dejar de avisarme en este móvil' : 'Avisarme en este móvil';
    boton.setAttribute('aria-pressed', String(apuntado));
  }
  async function mirar() {
    boton.hidden = false;
    if (!soporta()) {
      boton.hidden = true;
      decir(iphone() ? 'En iPhone, añade Void a tu pantalla de inicio (Compartir → Añadir a pantalla de inicio) y ábrelo desde ahí para recibir avisos.' : 'Este navegador no puede recibir avisos.');
      return;
    }
    const s = await suscripcion();
    const d = await window.VoidEspacio.api('avisos' + (s ? '?endpoint=' + encodeURIComponent(s.endpoint) : ''));
    clave = d.clave; apuntado = !!d.apuntado;
    if (!clave) { boton.hidden = true; decir(''); return; }
    decir(apuntado ? 'Este móvil suena cuando te llega un mensaje. El aviso no dice de quién ni qué: los mensajes van cifrados.' : '');
    pintar();
  }
  boton.addEventListener('click', async () => {
    boton.disabled = true;
    try {
      if (apuntado) {
        const s = await suscripcion();
        if (s) await window.VoidEspacio.api('avisos', { accion: 'baja', endpoint: s.endpoint });
        apuntado = false; decir('Este móvil ya no suena con tus mensajes.');
      } else {
        if (await Notification.requestPermission() !== 'granted') { decir('El navegador no ha dado permiso para avisarte. Puedes cambiarlo en los ajustes del sitio.'); return; }
        const r = await navigator.serviceWorker.ready;
        const s = (await r.pushManager.getSubscription()) || await r.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: bytes(clave) });
        await window.VoidEspacio.api('avisos', { accion: 'alta', endpoint: s.endpoint });
        apuntado = true; decir('Listo: este móvil sonará cuando te llegue un mensaje.');
      }
      pintar();
    } catch (e) { decir(e?.message || 'No se ha podido cambiar el aviso.'); }
    finally { boton.disabled = false; }
  });
  window.addEventListener('void-abrir', () => { mirar().catch(() => { boton.hidden = true; }); });
})();
