from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['confirmation_code', 'user', 'route', 'tour_date', 'num_people', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'tour_date']
    search_fields = ['confirmation_code', 'user__email', 'route__title', 'contact_name']
    readonly_fields = ['confirmation_code', 'created_at', 'updated_at']

    actions = ['confirm_bookings', 'complete_bookings']

    def confirm_bookings(self, request, queryset):
        queryset.update(status='confirmed')
    confirm_bookings.short_description = 'Подтвердить бронирования'

    def complete_bookings(self, request, queryset):
        queryset.update(status='completed')
    complete_bookings.short_description = 'Отметить как завершённые'