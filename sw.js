self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('blg-cache-v1').then((cache) => {
      return cache.addAll(['/catalogo']);
    })
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => {
      return response || fetch(e.request);
    })
  );
});