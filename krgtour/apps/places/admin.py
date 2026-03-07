from django.contrib import admin
from .models import Place, PlaceCategory, PlaceImage, PlaceReview, PlaceFavorite


class PlaceImageInline(admin.TabularInline):
    model = PlaceImage
    extra = 1


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'lat', 'lng', 'avg_rating', 'is_active', 'is_featured']
    list_filter = ['category', 'is_active', 'is_featured']
    search_fields = ['name', 'description']
    inlines = [PlaceImageInline]
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PlaceCategory)
class PlaceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PlaceReview)
class PlaceReviewAdmin(admin.ModelAdmin):
    list_display = ['place', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved']