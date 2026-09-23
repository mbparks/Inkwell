/* INKWELL: same-origin offline shell only. No telemetry or drawing uploads. */
'use strict';
const PREFIX = 'inkwell@' + self.registration.scope + ':';
const CACHE = PREFIX + '1.0.0';
const ROOT = self.registration.scope;
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon.svg'].map(p => new URL(p, ROOT).href);
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== location.origin || !url.href.startsWith(ROOT)) return;
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).then(response => {
      if (response.ok) { const copy = response.clone(); event.waitUntil(caches.open(CACHE).then(c => c.put(request, copy))); }
      return response;
    }).catch(async () => (await caches.match(request)) || (await caches.match(new URL('./index.html', ROOT).href))));
    return;
  }
  if (ASSETS.includes(url.href)) event.respondWith(caches.match(request).then(hit => hit || fetch(request)));
});
