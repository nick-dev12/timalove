from django.urls import path

from . import views

app_name = "auth"

urlpatterns = [
    path("connexion/", views.connexion, name="connexion"),
    path("inscription/", views.inscription, name="inscription"),
    path("completer-profil/", views.completer_profil, name="completer_profil"),
    path("mot-de-passe-oublie/", views.mot_de_passe_oublie, name="mot_de_passe_oublie"),
    path("deconnexion/", views.deconnexion, name="deconnexion"),
]
