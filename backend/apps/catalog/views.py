from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.accounts.permissions import Mandatory2FAEnforced
from apps.royalties.models import Distributor
from apps.royalties.permissions import CanAccessRoyalties

from .models import Artist, Label, LabelMembership, Release, Track, TrackArtist
from .permissions import CanManageCatalog
from .serializers import (
    ArtistSerializer,
    LabelSerializer,
    ReleaseSerializer,
    TrackSerializer,
    TrackArtistSerializer,
    TrackAssetSerializer,
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
            "tracks__identifiers", "tracks__artists"
        )
        user = self.request.user
        if user.role == Role.ARTIST and hasattr(user, "artist_profile"):
            qs = qs.filter(primary_artist=user.artist_profile)
        return qs


class TrackViewSet(viewsets.ModelViewSet):
    serializer_class = TrackSerializer
    permission_classes = [CanManageCatalog]

    def get_queryset(self) -> QuerySet[Track]:
        qs = Track.objects.filter(release__label_id__in=_user_label_ids(self.request.user)).select_related(
            "release"
        ).prefetch_related("identifiers", "artists")
        user = self.request.user
        if user.role == Role.ARTIST:
            if not hasattr(user, "artist_profile"):
                return qs.none()
            qs = qs.filter(release__primary_artist=user.artist_profile)
        return qs

    @action(detail=True, methods=["get"], permission_classes=[CanAccessRoyalties, Mandatory2FAEnforced])
    def royalties(self, request, pk=None):
        track = self.get_object()
        rows = track.royalty_line_items.filter(statement__label_id=track.release.label_id).order_by().values(
            "amount", "isrc", "source_asset_kind", "statement_id", "statement__filename",
            "statement__period_start", "statement__period_end", "statement__distributor", "statement__currency",
        )
        assets, statements = {}, {}
        total = Decimal("0.0000")
        line_count = 0
        currencies = set()
        # Sum persisted Decimals rather than SQLite's floating-point SQL SUM.
        for row in rows.iterator():
            currencies.add(row["statement__currency"])
            key = (row["source_asset_kind"], row["isrc"])
            asset = assets.setdefault(key, {
                "source_asset_kind": key[0], "isrc": key[1], "line_count": 0, "total": Decimal("0.0000"),
            })
            statement = statements.setdefault(row["statement_id"], {
                "id": row["statement_id"], "filename": row["statement__filename"],
                "period_start": row["statement__period_start"], "period_end": row["statement__period_end"],
                "distributor": row["statement__distributor"],
                "distributor_display": dict(Distributor.choices).get(row["statement__distributor"], row["statement__distributor"]),
                "line_count": 0, "total": Decimal("0.0000"),
            })
            for group in (asset, statement):
                group["line_count"] += 1
                group["total"] += row["amount"]
            total += row["amount"]
            line_count += 1
        if len(currencies) > 1:
            raise serializers.ValidationError({"detail": "This track has royalties in multiple currencies; a combined total is not available."})
        for group in (*assets.values(), *statements.values()):
            group["total"] = f"{group['total']:.4f}"
        return Response({
            "track": TrackSerializer(track).data,
            "release_title": track.release.title,
            "primary_artist_name": track.release.primary_artist.name,
            "currency": next(iter(currencies), None),
            "total_royalties": f"{total:.4f}", "line_count": line_count,
            "by_asset": [assets[key] for key in sorted(assets)],
            "by_statement": [statements[key] for key in sorted(statements)],
        })

    @action(detail=True, methods=["get", "post"])
    def assets(self, request, pk=None):
        track = self.get_object()
        if request.method == "GET":
            return Response(TrackAssetSerializer(
                track.identifiers.filter(label_id=track.release.label_id), many=True,
            ).data)
        serializer = TrackAssetSerializer(data=request.data, context={"track": track})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["patch", "delete"], url_path=r"assets/(?P<asset_id>\d+)")
    def asset_detail(self, request, pk=None, asset_id=None):
        track = self.get_object()
        asset = get_object_or_404(track.identifiers, pk=asset_id, label_id=track.release.label_id)
        if request.method == "DELETE":
            asset.delete()
            return Response(status=204)
        serializer = TrackAssetSerializer(asset, data=request.data, partial=True, context={"track": track})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


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
