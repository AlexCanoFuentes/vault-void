// Trabajador de fondo [16-oct]: existe para que el móvil ofrezca «añadir a la pantalla de inicio».
// No guarda nada en caché ni responde a ninguna petición: todo sigue yendo a la red, como sin él.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});

// Avisos en el móvil (23-oct). El aviso llega vacío:
// los mensajes van cifrados y la red no sabe de quién son ni qué dicen, así que aquí no se puede contar más.
self.addEventListener('push', (e) => {
  e.waitUntil(self.registration.showNotification('Mensaje nuevo en Void', {
    body: 'Ábrelo en tu espacio.', tag: 'void-mensaje', renotify: true,
    icon: '/icono-192.png', badge: '/icono-192.png', data: { url: '/mi-vault#comunidad' },
  }));
});
self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = new URL(e.notification.data?.url || '/mi-vault#comunidad', self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((ventanas) => {
    const abierta = ventanas.find((v) => new URL(v.url).pathname === '/mi-vault');
    return abierta ? abierta.navigate(url).then((v) => (v || abierta).focus()) : self.clients.openWindow(url);
  }));
});
