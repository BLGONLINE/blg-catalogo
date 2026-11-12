self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Modo pasivo para permitir funcionamiento online con Tiendanube
});