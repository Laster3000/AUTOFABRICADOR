"use strict";
const CACHE="af-r76-asset-cache-v2";
const ASSETS=["/","/index.html","/app.css","/app.js","/game2d.js","/game3d.js",
 "/logic-2d-r75.js","/logic-3d-r75.js","/logic-api-r76.js","/manifest.webmanifest","/icon-192.png","/icon-512.png"];
self.addEventListener("install",event=>{
 event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener("activate",event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key))))
    .then(()=>self.clients.claim()));
});
self.addEventListener("fetch",event=>{
 const request=event.request;
 const u=new URL(request.url);
 if(u.origin!==self.location.origin || u.pathname.startsWith("/api/"))return;
 if(request.method!=="GET")return;
 if(!ASSETS.includes(u.pathname))return;
 event.respondWith(caches.match(u.pathname).then(cached=>cached||fetch(request)));
});
