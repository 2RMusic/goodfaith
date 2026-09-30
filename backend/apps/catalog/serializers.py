import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from rest_framework import serializers

from .models import Artist, AssetKind, Label, Release, Track, TrackArtist, TrackIdentifier


def _user_label_ids(context: dict) -> set[int]:
    user = context["request"].user
    return set(user.label_memberships.values_list("label_id", flat=True))


def _unique_artist_slug(label: Label, base: str, *, exclude_pk: int | None = None) -> str:
    slug = base or "artist"
    counter = 1
    qs = Artist.objects.filter(label=label, slug=slug)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    while qs.exists():
        slug = f"{base}-{counter}"
        counter += 1
        qs = Artist.objects.filter(label=label, slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)

    return slug


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ("id", "name", "slug", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ArtistSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True, default="")
    username = serializers.SerializerMethodField()

    class Meta:
        model = Artist
        fields = (
            "id",
            "label",
            "name",
            "slug",
            "user",
            "username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")

    def get_username(self, obj: Artist) -> str:
        return obj.user.username if obj.user_id else ""

    def validate_label(self, label: Label) -> Label:
        if label.id not in _user_label_ids(self.context):
            raise serializers.ValidationError("Label not accessible.")
        return label

    def create(self, validated_data: dict) -> Artist:
        slug = (validated_data.get("slug") or "").strip()

        if not slug:
            label = validated_data["label"]
            name = validated_data["name"]
            validated_data["slug"] = _unique_artist_slug(
                label,
                slugify(name) or "artist",
            )

        return super().create(validated_data)

    def update(self, instance: Artist, validated_data: dict) -> Artist:
        slug = validated_data.get("slug", instance.slug)

        if not str(slug).strip():
            label = validated_data.get("label", instance.label)
            name = validated_data.get("name", instance.name)
            validated_data["slug"] = _unique_artist_slug(
                label,
                slugify(name) or "artist",
                exclude_pk=instance.pk,
            )

        return super().update(instance, validated_data)


class TrackArtistSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source="artist.name", read_only=True)

    class Meta:
        model = TrackArtist
        fields = (
            "id",
            "track",
            "artist",
            "artist_name",
            "role",
            "billing_order",
        )
        read_only_fields = ("id", "artist_name")


class TrackAssetSerializer(serializers.ModelSerializer):
    isrc = serializers.CharField(source="value", max_length=12)
    asset_kind = serializers.ChoiceField(choices=AssetKind.choices)

    class Meta:
        model = TrackIdentifier
        fields = ("id", "isrc", "asset_kind")
        read_only_fields = ("id",)

    def validate_isrc(self, value):
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", value):
            raise serializers.ValidationError("Enter a valid 12-character ISRC.")
        return value

    def validate(self, attrs):
        track = self.context["track"]
        value = attrs.get("value", getattr(self.instance, "value", ""))
        duplicates = TrackIdentifier.objects.filter(
            label_id=track.release.label_id, identifier_type="isrc", value=value,
        )
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists() or Track.objects.filter(
            release__label_id=track.release.label_id, isrc__iexact=value,
        ).exists():
            raise serializers.ValidationError({"isrc": "This ISRC already belongs to an asset in this label."})
        return attrs

    def save(self, **kwargs):
        track = self.context["track"]
        try:
            with transaction.atomic():
                return super().save(track=track, label=track.release.label, identifier_type="isrc")
        except DjangoValidationError as exc:
            errors = getattr(exc, "message_dict", {"detail": exc.messages})
            if "value" in errors:
                errors["isrc"] = errors.pop("value")
            raise serializers.ValidationError(errors) from exc
        except IntegrityError as exc:
            raise serializers.ValidationError({"isrc": "This ISRC already belongs to an asset in this label."}) from exc


class TrackSerializer(serializers.ModelSerializer):
    artists = TrackArtistSerializer(many=True, read_only=True)
    assets = TrackAssetSerializer(source="identifiers", many=True, read_only=True)

    class Meta:
        model = Track
        fields = (
            "id",
            "release",
            "title",
            "isrc",
            "iswc",
            "track_number",
            "duration_seconds",
            "artists",
            "assets",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_release(self, release: Release) -> Release:
        if release.label_id not in _user_label_ids(self.context):
            raise serializers.ValidationError("Release not accessible.")
        return release

    def validate(self, attrs: dict) -> dict:
        release = attrs.get("release") or getattr(self.instance, "release", None)

        if self.instance is None and release and "track_number" not in attrs:
            next_number = release.tracks.count() + 1
            attrs["track_number"] = next_number

        return attrs


class ReleaseSerializer(serializers.ModelSerializer):
    tracks = TrackSerializer(many=True, read_only=True)
    primary_artist_name = serializers.CharField(
        source="primary_artist.name",
        read_only=True,
    )
    track_count = serializers.SerializerMethodField()

    class Meta:
        model = Release
        fields = (
            "id",
            "label",
            "primary_artist",
            "primary_artist_name",
            "title",
            "release_type",
            "upc",
            "release_date",
            "tracks",
            "track_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_track_count(self, obj: Release) -> int:
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "tracks" in obj._prefetched_objects_cache
        ):
            return len(obj.tracks.all())

        return obj.tracks.count()

    def validate_label(self, label: Label) -> Label:
        if label.id not in _user_label_ids(self.context):
            raise serializers.ValidationError("Label not accessible.")

        return label

    def validate(self, attrs: dict) -> dict:
        label = attrs.get("label") or getattr(self.instance, "label", None)
        artist = attrs.get("primary_artist") or getattr(
            self.instance,
            "primary_artist",
            None,
        )

        if label and artist and artist.label_id != label.id:
            raise serializers.ValidationError(
                {
                    "primary_artist": (
                        "Artist must belong to the same label as the release."
                    )
                }
            )

        return attrs
