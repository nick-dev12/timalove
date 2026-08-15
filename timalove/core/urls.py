from django.urls import include, path

from core.views import push_views

urlpatterns = [
    path("firebase-messaging-sw.js", push_views.firebase_messaging_sw, name="firebase_messaging_sw"),
    path("", include("core.views.public.urls")),
    path("", include("core.views.auth.urls")),
    path("", include("core.views.app.urls")),
    path("espace-prive/", include("core.views.admin_panel.urls")),
    path("api/", include("core.views.api.urls")),
]
