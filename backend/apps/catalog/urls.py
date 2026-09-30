from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("labels", views.LabelViewSet, basename="label")
router.register("artists", views.ArtistViewSet, basename="artist")
router.register("releases", views.ReleaseViewSet, basename="release")
router.register("tracks", views.TrackViewSet, basename="track")
router.register("track-artists", views.TrackArtistViewSet, basename="track-artist")

urlpatterns = [
    path("", include(router.urls)),
]
