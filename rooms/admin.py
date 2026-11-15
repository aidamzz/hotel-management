from django.contrib import admin

from .models import Booking, Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "label", "beds", "view")
    search_fields = ("label",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "user_identifier", "check_in", "check_out")
    list_select_related = ("room",)
