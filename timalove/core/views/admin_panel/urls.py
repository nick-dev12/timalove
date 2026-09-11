from django.urls import path
from django.views.generic.base import RedirectView

from . import views

app_name = "admin_panel"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="admin_panel:dashboard", permanent=False)),
    path("connexion/", views.connexion, name="connexion"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/data/kpis/", views.dashboard_data_kpis, name="dashboard_data_kpis"),
    path("dashboard/data/charts/", views.dashboard_data_charts, name="dashboard_data_charts"),
    path("membres/", views.membres, name="membres"),
    path("membres/<uuid:profile_id>/", views.membre_detail, name="membre_detail"),
    path("signalements/", views.signalements, name="signalements"),
    path("signalements/<uuid:report_id>/", views.signalement_detail, name="signalement_detail"),
    path("paiements/", views.paiements, name="paiements"),
    path("paiements/data/summary/", views.paiements_data_summary, name="paiements_data_summary"),
    path("monetisation/", views.monetisation, name="monetisation"),
    path("communications/", views.communications, name="communications"),
    path("communications/cities/", views.communications_cities, name="communications_cities"),
    path("configuration/", views.configuration, name="configuration"),
    path("monitoring/", views.monitoring, name="monitoring"),
    path("equipe/", views.roles_audit, name="roles_audit"),
    path("2fa/configuration/", views.admin_2fa_setup, name="admin_2fa_setup"),
    path("2fa/verification/", views.admin_2fa_verify, name="admin_2fa_verify"),
]
