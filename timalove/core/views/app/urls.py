from django.urls import path

from . import views

app_name = "app"

urlpatterns = [
    path("decouvrir/", views.decouvrir, name="decouvrir"),
    path("decouvrir/swipe/", views.swipe, name="swipe"),
    path("likes/", views.likes, name="likes"),
    path("historique/", views.historique, name="historique"),
    path("historique/<uuid:profile_id>/like/", views.historique_like, name="historique_like"),
    path("historique/<uuid:profile_id>/superlike/", views.historique_superlike, name="historique_superlike"),
    path("rencontres/", views.rencontres, name="rencontres"),
    path("discussions/", views.discussions, name="discussions"),
    path("discussions/<uuid:partner_id>/", views.discussion_detail, name="discussion_detail"),
    path("profil/", views.profil, name="profil"),
    path("profil/parametres/", views.parametres, name="parametres"),
]
