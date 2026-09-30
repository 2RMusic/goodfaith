from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ProSociety(models.TextChoices):
    ASCAP = "ascap", "ASCAP"
    BMI = "bmi", "BMI"
    SESAC = "sesac", "SESAC"
    SOCAN = "socan", "SOCAN"
    OTHER = "other", "Other"
    NONE = "", "Not set"


class RegistrationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    READY = "ready", "Ready to register"
    SUBMITTED = "submitted", "Submitted"
    REGISTERED = "registered", "Registered"


class ContributorRole(models.TextChoices):
    WRITER = "writer", "Writer"
    COMPOSER = "composer", "Composer"
    WRITER_COMPOSER = "writer_composer", "Writer/Composer"
    PUBLISHER = "publisher", "Publisher"
    ADMIN = "admin", "Admin publisher"


class MusicalWork(TimeStampedModel):
    """
    A composition / musical work for publishing administration (Module 8).
    Distinct from Track (sound recording) — linked via ISWC and optional track M2M.
    """

    label = models.ForeignKey(
        "catalog.Label",
        on_delete=models.CASCADE,
        related_name="musical_works",
    )
    title = models.CharField(max_length=512)
    iswc = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="International Standard Musical Work Code (T-xxx.xxx.xxx-x).",
    )
    registration_status = models.CharField(
        max_length=16,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.DRAFT,
    )
    target_pro = models.CharField(
        max_length=16,
        choices=ProSociety.choices,
        blank=True,
        default="",
        help_text="Primary PRO/society for registration intent.",
    )
    notes = models.TextField(blank=True)
    tracks = models.ManyToManyField(
        "catalog.Track",
        blank=True,
        related_name="musical_works",
        help_text="Sound recordings that embody this work.",
    )

    class Meta:
        ordering = ("title",)
        constraints = [
            models.UniqueConstraint(
                fields=["label", "iswc"],
                condition=models.Q(iswc__isnull=False) & ~models.Q(iswc=""),
                name="unique_iswc_per_label_when_set",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class WorkShare(TimeStampedModel):
    """Writer/publisher share on a musical work — must total 100% when ready/registered."""

    work = models.ForeignKey(MusicalWork, on_delete=models.CASCADE, related_name="shares")
    contributor_name = models.CharField(max_length=255)
    artist = models.ForeignKey(
        "catalog.Artist",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_shares",
    )
    role = models.CharField(
        max_length=16,
        choices=ContributorRole.choices,
        default=ContributorRole.WRITER,
    )
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    ipi_cae = models.CharField(
        max_length=11,
        blank=True,
        help_text="CAE/IPI name number when known.",
    )
    pro_affiliation = models.CharField(
        max_length=16,
        choices=ProSociety.choices,
        blank=True,
        default="",
    )

    class Meta:
        ordering = ("-percentage", "contributor_name")

    def __str__(self) -> str:
        return f"{self.contributor_name} — {self.percentage}%"


class RegistrationEvent(TimeStampedModel):
    """Manual PRO registration history for a musical work (no society API yet)."""

    work = models.ForeignKey(
        MusicalWork,
        on_delete=models.CASCADE,
        related_name="registration_events",
    )
    status = models.CharField(
        max_length=16,
        choices=RegistrationStatus.choices,
    )
    pro_society = models.CharField(
        max_length=16,
        choices=ProSociety.choices,
        blank=True,
        default="",
    )
    reference = models.CharField(
        max_length=128,
        blank=True,
        help_text="Society confirmation / work ID when available.",
    )
    notes = models.TextField(blank=True)
    occurred_on = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registration_events_created",
    )

    class Meta:
        ordering = ("-occurred_on", "-created_at")

    def __str__(self) -> str:
        return f"{self.work} → {self.get_status_display()}"
