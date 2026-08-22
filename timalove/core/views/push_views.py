import json

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@require_GET
@never_cache
def firebase_messaging_sw(request):
    """Service worker FCM — doit être servi à la racine du site."""
    config = {
        "apiKey": settings.FIREBASE_WEB_API_KEY,
        "authDomain": settings.FIREBASE_AUTH_DOMAIN,
        "projectId": settings.FIREBASE_PROJECT_ID,
        "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": settings.FIREBASE_MESSAGING_SENDER_ID,
        "appId": settings.FIREBASE_APP_ID,
        "measurementId": settings.FIREBASE_MEASUREMENT_ID,
    }
    icon_url = f"{settings.SITE_URL.rstrip('/')}/static/images/logo.webp"
    body = f"""/* TimaLove — Firebase Cloud Messaging service worker */
importScripts("https://www.gstatic.com/firebasejs/12.18.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/12.18.0/firebase-messaging-compat.js");

firebase.initializeApp({json.dumps(config)});

const messaging = firebase.messaging();

function showPush(payload) {{
  const data = payload.data || {{}};
  const title = (payload.notification && payload.notification.title) || data.title || "TimaLove";
  const body = (payload.notification && payload.notification.body) || data.message || "";
  const tag = "timalove-" + (data.type || "notif") + "-" + (data.notification_id || Date.now());
  return self.registration.showNotification(title, {{
    body: body,
    icon: "{icon_url}",
    badge: "{icon_url}",
    tag: tag,
    renotify: true,
    data: Object.assign({{ url: data.url || "/" }}, data),
  }});
}}

messaging.onBackgroundMessage((payload) => {{
  return showPush(payload || {{}});
}});

self.addEventListener("notificationclick", (event) => {{
  event.notification.close();
  const target = event.notification.data?.url || "/";
  event.waitUntil((async () => {{
    const all = await clients.matchAll({{ type: "window", includeUncontrolled: true }});
    for (const client of all) {{
      if (client.url && client.url.startsWith(self.location.origin)) {{
        client.focus();
        client.postMessage({{ type: "timalove:open", url: target }});
        return;
      }}
    }}
    await clients.openWindow(target);
  }})());
}});
"""
    return HttpResponse(body, content_type="application/javascript; charset=utf-8")
