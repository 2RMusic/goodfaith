from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.catalog.models import AssetKind, Label, Track
from apps.core.models import TimeStampedModel


class Distributor(models.TextChoices):
    DISTROKID = "distrokid", "DistroKid"
    TUNECORE = "tunecore", "TuneCore"
    CD_BABY = "cd_baby", "CD Baby"
    SYMPHONIC = "symphonic", "Symphonic"
    ONERPM = "onerpm", "ONErpm"
    ROUTENOTE = "routenote", "RouteNote"
    TOOLOST = "toolost", "TooLost"
    FUGA = "fuga", "FUGA"
    VYDIA = "vydia", "Vydia"
    THE_ORCHARD = "the_orchard", "The Orchard"
    COLONIZE = "colonize", "Colonize Media"
    LUJO = "lujo", "Lujo Network"
    OTHER = "other", "Other"


class StatementStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"


class RoyaltyStatement(TimeStampedModel):
    """Uploaded distributor royalty statement awaiting normalization."""

    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="royalty_statements")
    distributor = models.CharField(max_length=32, choices=Distributor.choices)
    filename = models.CharField(max_length=512)
    file = models.FileField(upload_to="royalty_statements/%Y/%m/")
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=StatementStatus.choices,
        default=StatementStatus.PENDING,
    )
    row_count = models.PositiveIntegerField(blank=True, null=True)
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        blank=True,
        null=True,
    )
    currency = models.CharField(max_length=3, default="USD")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_statements",
    )
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.get_distributor_display()} — {self.filename}"


class RoyaltyLineItem(TimeStampedModel):
    """A single normalized row from a parsed distributor statement."""

    statement = models.ForeignKey(
        RoyaltyStatement, on_delete=models.CASCADE, related_name="line_items"
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="royalty_line_items",
        help_text="Matched by ISRC within the statement's label catalog, when possible.",
    )
    sale_period = models.DateField(
        blank=True, null=True, help_text="Reporting period this row's activity occurred in."
    )
    store = models.CharField(max_length=128, blank=True, help_text="DSP/platform, e.g. Spotify.")
    country = models.CharField(max_length=2, blank=True)
    artist_name = models.CharField(max_length=255, blank=True, help_text="Artist name as reported by the distributor.")
    track_title = models.CharField(max_length=512, blank=True, help_text="Track title as reported by the distributor.")
    isrc = models.CharField(max_length=12, blank=True)
    source_asset_kind = models.CharField(
        max_length=16, choices=AssetKind.choices, default=AssetKind.UNKNOWN,
        help_text="Asset classification captured when this line was imported.",
    )
    upc = models.CharField(max_length=13, blank=True)
    quantity = models.PositiveIntegerField(default=0, help_text="Units/streams for this row.")
    amount = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    raw_data = models.JSONField(
        default=dict, blank=True, help_text="Original row exactly as read from the statement file."
    )

    class Meta:
        ordering = ("-sale_period", "id")

    def __str__(self) -> str:
        return f"{self.isrc or self.track_title} — {self.amount}"


class RoyaltyRunStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready"
    CLOSED = "closed", "Closed"


class RoyaltyRun(TimeStampedModel):
    """A consolidated royalty run combining one or more normalized statements."""

    label = models.ForeignKey(Label, on_delete=models.CASCADE, related_name="royalty_runs")
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=RoyaltyRunStatus.choices,
        default=RoyaltyRunStatus.DRAFT,
    )
    statements = models.ManyToManyField(RoyaltyStatement, related_name="runs", blank=True)
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=Decimal("0"),
    )
    currency = models.CharField(max_length=3, default="USD")
    consolidation_error = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.name


class RoyaltyRunPayout(TimeStampedModel):
    """Per-participant share of consolidated earnings for one track within a run."""

    run = models.ForeignKey(RoyaltyRun, on_delete=models.CASCADE, related_name="payouts")
    track = models.ForeignKey(
        Track,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="run_payouts",
    )
    isrc = models.CharField(max_length=12, blank=True)
    track_title = models.CharField(max_length=512, blank=True)
    participant_name = models.CharField(max_length=255)
    artist = models.ForeignKey(
        "catalog.Artist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="run_payouts",
    )
    role = models.CharField(max_length=16, blank=True)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    track_gross = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    amount = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    unallocated_reason = models.CharField(
        max_length=64,
        blank=True,
        help_text="Set when earnings could not be split (missing or draft split sheet).",
    )

    class Meta:
        ordering = ("-amount", "participant_name")

    def __str__(self) -> str:
        return f"{self.participant_name} — {self.amount}"
