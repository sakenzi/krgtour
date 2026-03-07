from django.contrib import admin
from .models import Route, Category, RoutePoint, RouteImage, Review, Favorite


class RoutePointInline(admin.TabularInline):
    model = RoutePoint
    extra = 1
    fields = ['name', 'lat', 'lng', 'point_type', 'order']


class RouteImageInline(admin.TabularInline):
    model = RouteImage
    extra = 1


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'distance_km', 'status', 'avg_rating', 'booking_count']
    list_filter = ['status', 'difficulty', 'category', 'is_featured']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [RoutePointInline, RouteImageInline]
    readonly_fields = ['avg_rating', 'review_count', 'view_count', 'booking_count']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['route', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = 'Одобрить выбранные отзывы'