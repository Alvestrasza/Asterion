const CACHE_NAME = "asterion-static-v0.4.1";
const STATIC_ASSETS = [
  "/offline.html",
  "/manifest.webmanifest",
  "/assets/spritesheet.webp",
  "/assets/animations/idle.gif",
  "/assets/animations/waving.gif",
  "/assets/animations/jumping.gif",
  "/assets/animations/failed.gif",
  "/assets/animations/waiting.gif",
  "/assets/animations/review.gif",
  "/assets/companions/asterion.png",
  "/assets/companions/rabbit.png",
  "/assets/companions/cat.png",
  "/assets/companions/orc.png",
  "/assets/companions/pony.png",
  "/assets/companions/fairy.png",
  "/assets/companions/dog.png",
  "/assets/companions/elf.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;

  if (event.request.mode === "navigate") {
    event.respondWith(fetch(event.request).catch(() => caches.match("/offline.html")));
    return;
  }

  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/login")) return;

  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/assets/")) {
    event.respondWith(
      caches.match(event.request).then((cached) =>
        cached ??
        fetch(event.request).then((response) => {
          if (response.ok) {
            const copy = response.clone();
            void caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
      )
    );
  }
});
