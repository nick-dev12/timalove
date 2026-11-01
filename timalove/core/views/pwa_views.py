"""PWA — manifest, page hors-ligne et logique cache du service worker."""

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from core.deploy_revision import get_deploy_revision

THEME_COLOR = "#ffffff"
BACKGROUND_COLOR = "#ffffff"
OFFLINE_URL = "/hors-ligne/"


def _icon(path: str, size: int, purpose: str = "any") -> dict:
    return {"src": static(path), "sizes": f"{size}x{size}", "type": "image/png", "purpose": purpose}


@require_GET
@cache_control(public=True, max_age=3600)
def manifest(request):
    data = {
        "id": "/",
        "name": "TimaLove — Rencontres sérieuses",
        "short_name": "TimaLove",
        "description": "Rencontres authentiques et bienveillantes, vers le mariage.",
        "lang": "fr",
        "dir": "ltr",
        "start_url": "/explorer/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "display_override": ["standalone", "minimal-ui"],
        "background_color": BACKGROUND_COLOR,
        "theme_color": THEME_COLOR,
        "categories": ["social", "lifestyle"],
        "prefer_related_applications": False,
        "related_applications": [
            {"platform": "webapp", "url": request.build_absolute_uri("/manifest.webmanifest")},
        ],
        "icons": [
            _icon("images/pwa/icon-96.png", 96),
            _icon("images/pwa/icon-192.png", 192),
            _icon("images/pwa/icon-512.png", 512),
            _icon("images/pwa/icon-maskable-192.png", 192, "maskable"),
            _icon("images/pwa/icon-maskable-512.png", 512, "maskable"),
        ],
        "screenshots": [
            {
                "src": static(f"images/pwa/screen-{n}.webp"),
                "sizes": "621x1344",
                "type": "image/webp",
                "form_factor": "narrow",
                "label": label,
            }
            for n, label in (
                ("04", "Un parcours de rencontres choisi pour vous"),
                ("05", "Des messages guidés et bienveillants"),
                ("06", "Un coaching pour avancer sereinement"),
            )
        ],
        "shortcuts": [
            {"name": "Parcours", "url": "/explorer/?source=pwa", "icons": [_icon("images/pwa/icon-96.png", 96)]},
            {"name": "Messages", "url": "/discussions/?source=pwa", "icons": [_icon("images/pwa/icon-96.png", 96)]},
            {"name": "Intérêts", "url": "/likes/?source=pwa", "icons": [_icon("images/pwa/icon-96.png", 96)]},
        ],
    }
    response = JsonResponse(data, json_dumps_params={"ensure_ascii": False})
    response["Content-Type"] = "application/manifest+json; charset=utf-8"
    return response


@require_GET
def offline(request):
    return render(request, "pwa/offline.html", {"title": "Hors ligne"})


def service_worker_cache_section() -> str:
    """Partie PWA du service worker (cache statique + repli hors-ligne)."""
    precache = [
        OFFLINE_URL,
        static("css/timalove.css"),
        static("images/logo.webp"),
        static("images/pwa/icon-192.png"),
        static("images/pwa/apple-touch-icon.png"),
    ]
    version = get_deploy_revision()
    return f"""/* TimaLove — PWA : cache + hors-ligne */
const TL_CACHE_VERSION = {json.dumps(version)};
const TL_STATIC_CACHE = "timalove-static-" + TL_CACHE_VERSION;
const TL_PAGES_CACHE = "timalove-offline-" + TL_CACHE_VERSION;
const TL_OFFLINE_URL = {json.dumps(OFFLINE_URL)};
const TL_PRECACHE = {json.dumps(precache)};
const TL_STATIC_MAX = 120;

self.addEventListener("install", (event) => {{
  event.waitUntil((async () => {{
    const pages = await caches.open(TL_PAGES_CACHE);
    await pages.add(new Request(TL_OFFLINE_URL, {{ cache: "reload" }}));
    const assets = await caches.open(TL_STATIC_CACHE);
    await Promise.all(
      TL_PRECACHE.filter((u) => u !== TL_OFFLINE_URL).map((u) => assets.add(u).catch(() => null))
    );
    await self.skipWaiting();
  }})());
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil((async () => {{
    const keep = new Set([TL_STATIC_CACHE, TL_PAGES_CACHE]);
    const keys = await caches.keys();
    await Promise.all(
      keys.filter((k) => k.startsWith("timalove-") && !keep.has(k)).map((k) => caches.delete(k))
    );
    if (self.registration.navigationPreload) {{
      await self.registration.navigationPreload.enable().catch(() => null);
    }}
    await self.clients.claim();
  }})());
}});

async function tlTrimCache(name, max) {{
  const cache = await caches.open(name);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}}

async function tlNavigate(event) {{
  try {{
    const preloaded = await event.preloadResponse;
    if (preloaded) return preloaded;
    return await fetch(event.request);
  }} catch (_err) {{
    const cache = await caches.open(TL_PAGES_CACHE);
    return (await cache.match(TL_OFFLINE_URL)) || Response.error();
  }}
}}

async function tlStatic(event) {{
  const cache = await caches.open(TL_STATIC_CACHE);
  const cached = await cache.match(event.request);
  const network = fetch(event.request)
    .then((res) => {{
      if (res && res.ok && (res.type === "basic" || res.type === "cors")) {{
        cache.put(event.request, res.clone()).then(() => tlTrimCache(TL_STATIC_CACHE, TL_STATIC_MAX));
      }}
      return res;
    }})
    .catch(() => null);
  if (cached) {{
    event.waitUntil(network);
    return cached;
  }}
  return (await network) || Response.error();
}}

self.addEventListener("fetch", (event) => {{
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (req.mode === "navigate") {{
    // Pages HTML jamais mises en cache (données privées) : réseau, sinon page hors-ligne.
    event.respondWith(tlNavigate(event));
    return;
  }}

  const sameOrigin = url.origin === self.location.origin;
  const isStatic = sameOrigin && url.pathname.startsWith("/static/");
  const isFont = url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com";
  if (isStatic || isFont) {{
    event.respondWith(tlStatic(event));
  }}
}});

self.addEventListener("message", (event) => {{
  if (event.data && event.data.type === "timalove:skip-waiting") self.skipWaiting();
}});
"""
