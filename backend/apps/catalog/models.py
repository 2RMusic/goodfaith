from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Label(TimeStampedModel):
    """A record label tenant — the top-level catalog boundary."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class LabelMembership(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="label_memberships",
    )
    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="memberships")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "label"], name="unique_user_label_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.label}"


class Artist(TimeStampedModel):
    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="artists")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="artist_profile",
        help_text="Portal login for this artist (Artist role).",
    )

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=["label", "slug"], name="unique_artist_slug_per_label"),
        ]

    def __str__(self) -> str:
        return self.name


class ReleaseType(models.TextChoices):
    ALBUM = "album", "Album"
    EP = "ep", "EP"
    SINGLE = "single", "Single"
    COMPILATION = "compilation", "Compilation"


class Release(TimeStampedModel):
    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="releases")
    primary_artist = models.ForeignKey(
        Artist,
        on_delete=models.PROTECT,
        related_name="releases",
    )
    title = models.CharField(max_length=512)
    release_type = models.CharField(
        max_length=16,
        choices=ReleaseType.choices,
        default=ReleaseType.ALBUM,
    )
    upc = models.CharField(
        max_length=13,
        blank=True,
        null=True,
        unique=True,
        help_text="UPC/EAN barcode for the release.",
    )
    release_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ("-release_date", "title")

    def __str__(self) -> str:
        return self.title


class Track(TimeStampedModel):
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name="tracks")
    title = models.CharField(max_length=512)
    isrc = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        unique=True,
        help_text="International Standard Recording Code.",
    )
    iswc = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="International Standard Musical Work Code (T-xxx.xxx.xxx-x).",
    )
    track_number = models.PositiveSmallIntegerField(default=1)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ("track_number",)
        constraints = [
            models.UniqueConstraint(
                fields=["release", "track_number"],
                name="unique_track_number_per_release",
            ),
        ]

    def __str__(self) -> str:
        return self.title
class TrackArtistRole(models.TextChoices):
    PRIMARY = "primary", "Primary Artist"
    FEATURED = "featured", "Featured Artist"


class TrackArtist(TimeStampedModel):
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name="artists",
    )
    artist = models.ForeignKey(
        Artist,
        on_delete=models.PROTECT,
        related_name="track_credits",
    )
    role = models.CharField(
        max_length=16,
        choices=TrackArtistRole.choices,
        default=TrackArtistRole.PRIMARY,
    )
    billing_order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ("billing_order",)
        constraints = [
            models.UniqueConstraint(
                fields=["track", "artist"],
                name="unique_artist_per_track",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.track.title} — {self.artist.name} ({self.get_role_display()})"