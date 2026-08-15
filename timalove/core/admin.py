from django.contrib import admin

from core import models

admin.site.site_header = "TimaLove Admin"
admin.site.site_title = "TimaLove"


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "gender", "city", "registration_status", "role")
    list_filter = ("registration_status", "role", "gender", "subscription_tier")
    search_fields = ("first_name", "last_name", "email", "phone", "city")


for model in (
    models.ProfileGalleryPhoto,
    models.Swipe,
    models.Match,
    models.Message,
    models.ConversationHide,
    models.BlockedUser,
    models.Notification,
    models.Transaction,
    models.Subscription,
    models.CoachingRequest,
    models.Report,
    models.BannedIdentity,
    models.Testimonial,
    models.SiteSetting,
    models.PushDevice,
):
    admin.site.register(model)
