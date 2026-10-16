// Trabajador de fondo mínimo [16-oct]: existe para que el móvil ofrezca «añadir a la pantalla de inicio».
// No guarda nada en caché ni responde a ninguna petición: todo sigue yendo a la red, como sin él.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
