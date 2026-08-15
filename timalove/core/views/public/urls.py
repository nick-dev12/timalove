from django.urls import path

from . import views

app_name = "public"

urlpatterns = [
    path("", views.home, name="home"),
    path("accueil/", views.accueil, name="accueil"),
    path("commencer/", views.commencer, name="commencer"),
    path("explorer/", views.explorer, name="explorer"),
    path("explorer/recherche/", views.explorer_search, name="explorer_search"),
    path("messages/", views.messages, name="messages"),
    path("messages/apercu/<str:partner_key>/", views.messages_preview, name="messages_preview"),
    path("historique/", views.historique, name="historique"),
    path("historique/plus/", views.historique_plus, name="historique_plus"),
    path("historique/recherche/", views.historique_search, name="historique_search"),
    path("explorer/stories/", views.explorer_stories, name="explorer_stories"),
    path("explorer/profil/<uuid:profile_id>/", views.explorer_profil, name="explorer_profil"),
    path("presentation/", views.presentation, name="presentation"),
    path("qui-suis-je/", views.qui_suis_je, name="qui_suis_je"),
    path("coaching/", views.coaching, name="coaching"),
    path("temoignages/", views.temoignages, name="temoignages"),
    path("contact/", views.contact, name="contact"),
    path("cgv/", views.cgv, name="cgv"),
    path("mentions-legales/", views.mentions, name="mentions"),
    path("politique-de-confidentialite/", views.confidentialite, name="confidentialite"),
    path("maintenance/", views.maintenance, name="maintenance"),
]
