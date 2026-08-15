from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("site-config/", views.site_config, name="site_config"),
    path("discover/feed/", views.discover_feed, name="discover_feed"),
    path("swipes/", views.swipes, name="swipes"),
    path("likes/incoming/", views.likes_incoming, name="likes_incoming"),
    path("likes/count/", views.likes_count, name="likes_count"),
    path("matches/", views.matches, name="matches"),
    path("matches/<uuid:partner_id>/unmatch/", views.unmatch, name="unmatch"),
    path("messages/", views.messages, name="messages"),
    path("messages/unread-count/", views.unread_messages, name="unread_messages"),
    path("notifications/", views.notifications, name="notifications"),
    path("payments/checkout/", views.payments_checkout, name="payments_checkout"),
    path("payments/confirm/", views.payments_confirm, name="payments_confirm"),
    path("payments/naboo-webhook/", views.naboo_webhook, name="naboo_webhook"),
    path("reports/", views.reports, name="reports"),
    path("blocked-users/", views.blocked_users, name="blocked_users"),
    path("coaching/checkout/", views.coaching_checkout, name="coaching_checkout"),
    path("push/config/", views.push_config, name="push_config"),
    path("push/register/", views.push_register, name="push_register"),
    path("push/unregister/", views.push_unregister, name="push_unregister"),
    path("auth/google/", views.auth_google, name="auth_google"),
    path("auth/apple/", views.auth_apple, name="auth_apple"),
    path("auth/signup/check/", views.signup_check, name="signup_check"),
    path("auth/signup/complete/", views.signup_complete, name="signup_complete"),
    path("auth/signup/location/", views.signup_location, name="signup_location"),
    path("onboarding/step/", views.onboarding_step, name="onboarding_step"),
    path("onboarding/photo/", views.onboarding_photo, name="onboarding_photo"),
    path("profile/update/", views.profile_update, name="profile_update"),
    path("profile/photo/", views.profile_photo, name="profile_photo"),
    path("profile/photo/delete/", views.profile_photo_delete, name="profile_photo_delete"),
    path("profile/photo/primary/", views.profile_photo_primary, name="profile_photo_primary"),
    path("profile/filters/", views.profile_filters, name="profile_filters"),
    path("profile/delete/", views.profile_delete, name="profile_delete"),
]
