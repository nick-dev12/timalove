from django.urls import path

from . import views

app_name = "admin_panel"

urlpatterns = [
    path("connexion/", views.connexion, name="connexion"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("inscriptions/", views.inscriptions, name="inscriptions"),
    path("activites/", views.activites, name="activites"),
    path("coaching/", views.coaching, name="coaching"),
    path("paiements/", views.paiements, name="paiements"),
    path("avis/", views.avis, name="avis"),
    path("signalements/", views.signalements, name="signalements"),
    path("monitoring/", views.monitoring, name="monitoring"),
    path("parametres/", views.parametres, name="parametres"),
]
