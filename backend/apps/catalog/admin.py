from django.contrib import admin

from .models import Artist, Label, LabelMembership, Release, Track, TrackIdentifier


class TrackInline(admin.TabularInline):
    model = Track
    extra = 0


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(LabelMembership)
class LabelMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "created_at")
    list_filter = ("label",)


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("name", "label", "slug", "user")
    list_filter = ("label",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "primary_artist", "label", "release_type", "upc", "release_date")
    list_filter = ("label", "release_type")
    inlines = [TrackInline]


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("title", "release", "track_number", "isrc", "duration_seconds")
    list_filter = ("release__label",)


@admin.register(TrackIdentifier)
class TrackIdentifierAdmin(admin.ModelAdmin):
    list_display = ("value", "identifier_type", "asset_kind", "track", "label")
    list_filter = ("label", "identifier_type", "asset_kind")
    search_fields = ("value", "track__title")
