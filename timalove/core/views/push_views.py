import json

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


@require_GET
@cache_control(max_age=3600, public=True)
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
importScripts("https://www.gstatic.com/firebasejs/12.17.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/12.17.1/firebase-messaging-compat.js");

firebase.initializeApp({json.dumps(config)});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {{
  const title = payload.notification?.title || "TimaLove";
  const options = {{
    body: payload.notification?.body || "",
    icon: "{icon_url}",
    badge: "{icon_url}",
    data: payload.data || {{}},
  }};
  self.registration.showNotification(title, options);
}});

self.addEventListener("notificationclick", (event) => {{
  event.notification.close();
  const target = event.notification.data?.url || "/";
  event.waitUntil(clients.openWindow(target));
}});
"""
    return HttpResponse(body, content_type="application/javascript; charset=utf-8")
