from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Role

from .models import Artist, Label, LabelMembership, Release, Track, TrackArtist
from .permissions import CanManageCatalog
from .serializers import (
    ArtistSerializer,
    LabelSerializer,
    ReleaseSerializer,
    TrackSerializer,
    TrackArtistSerializer,
)
User = get_user_model()


def _user_label_ids(user) -> list[int]:
    return list(user.label_memberships.values_list("label_id", flat=True))


class ArtistInviteSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=8, write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, default="")

    def validate_username(self, value: str) -> str:
        username = value.strip()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("That username is already taken.")
        return username


class LabelViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LabelSerializer
    permission_classes = [CanManageCatalog]

    def get_queryset(self) -> QuerySet[Label]:
        return Label.objects.filter(id__in=_user_label_ids(self.request.user))


class ArtistViewSet(viewsets.ModelViewSet):
    serializer_class = ArtistSerializer
    permission_classes = [CanManageCatalog]

    def get_queryset(self) -> QuerySet[Artist]:
        qs = Artist.objects.filter(label_id__in=_user_label_ids(self.request.user)).select_related(
            "user"
        )
        user = self.request.user
        if user.role == Role.ARTIST and hasattr(user, "artist_profile"):
            qs = qs.filter(pk=user.artist_profile.pk)
        return qs

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def invite(self, request, pk=None):
        """Create a portal login for this artist and link it to the roster record."""
        artist = self.get_object()
        if artist.user_id:
            raise serializers.ValidationError(
                {"detail": "This artist already has a portal login."}
            )

        body = ArtistInviteSerializer(data=request.data)
        body.is_valid(raise_exception=True)

        user = User.objects.create_user(
            username=body.validated_data["username"],
            password=body.validated_data["password"],
            email=body.validated_data.get("email") or "",
            role=Role.ARTIST,
        )
        LabelMembership.objects.get_or_create(user=user, label=artist.label)
        artist.user = user
        artist.save(update_fields=["user", "updated_at"])

        return Response(ArtistSerializer(artist, context={"request": request}).data, status=201)


class ReleaseViewSet(viewsets.ModelViewSet):
    serializer_class = ReleaseSerializer
    permission_classes = [CanManageCatalog]

    def get_queryset(self) -> QuerySet[Release]:
        qs = Release.objects.filter(label_id__in=_user_label_ids(self.request.user)).prefetch_related(
            "tracks"
        )
        user = self.request.user
        if user.role == Role.ARTIST and hasattr(user, "artist_profile"):
            qs = qs.filter(primary_artist=user.artist_profile)
        return qs


class TrackViewSet(viewsets.ModelViewSet):
    serializer_class = TrackSerializer
    permission_classes = [CanManageCatalog]

    def get_queryset(self) -> QuerySet[Track]:
        qs = Track.objects.filter(release__label_id__in=_user_label_ids(self.request.user))
        user = self.request.user
        if user.role == Role.ARTIST and hasattr(user, "artist_profile"):
            qs = qs.filter(release__primary_artist=user.artist_profile)
        return qs
class TrackArtistViewSet(viewsets.ModelViewSet):
    serializer_class = TrackArtistSerializer
    permission_classes = [CanManageCatalog]

    def get_queryset(self) -> QuerySet[TrackArtist]:
        return (
            TrackArtist.objects
            .filter(track__release__label_id__in=_user_label_ids(self.request.user))
            .select_related("track", "artist")
        )

    def perform_create(self, serializer):
        track = serializer.validated_data["track"]
        artist = serializer.validated_data["artist"]

        if track.release.label_id not in _user_label_ids(self.request.user):
            raise serializers.ValidationError({"track": "Track not accessible."})

        if artist.label_id != track.release.label_id:
            raise serializers.ValidationError(
                {"artist": "Artist must belong to the same label as the track."}
            )

        serializer.save()