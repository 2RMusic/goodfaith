from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.accounts.test_utils import satisfy_mandatory_2fa
from apps.royalties.models import RoyaltyLineItem, RoyaltyStatement
from .models import Artist, Label, LabelMembership, Release, Track


class TrackRoyaltiesTests(TestCase):
    def setUp(self):
        self.label = Label.objects.create(name="Label", slug="label")
        self.user = get_user_model().objects.create_user(username="finance", role=Role.FINANCE)
        satisfy_mandatory_2fa(self.user)
        LabelMembership.objects.create(label=self.label, user=self.user)
        artist = Artist.objects.create(label=self.label, name="Luis Vega", slug="luis-vega")
        release = Release.objects.create(label=self.label, primary_artist=artist, title="Single")
        self.track = Track.objects.create(release=release, title="Voy A Desaparecer", isrc="USCGH2458227")
        self.january = RoyaltyStatement.objects.create(label=self.label, filename="January.xlsx", distributor="colonize", period_start="2025-01-01", period_end="2025-01-31", status="processed")
        self.february = RoyaltyStatement.objects.create(label=self.label, filename="February.xlsx", distributor="colonize", status="processed")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/catalog/tracks/{self.track.pk}/royalties/"

    def add_line(self, amount, statement=None, **kwargs):
        return RoyaltyLineItem.objects.create(
            statement=statement or self.january,
            **{"track": self.track, "isrc": self.track.isrc, "source_asset_kind": "audio", **kwargs},
            amount=Decimal(amount),
        )

    def test_gross_and_both_breakdowns_reconcile_without_runs(self):
        self.add_line("2.0000")
        self.add_line("49.9665", isrc="QZNFJ2406014", source_asset_kind="music_video")
        self.add_line("4.1677", self.february)
        self.add_line("30.1897", self.february, isrc="QZNFJ2406014", source_asset_kind="music_video")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["total_royalties"], "86.3239")
        self.assertEqual(data["line_count"], 4)
        self.assertEqual(data["primary_artist_name"], "Luis Vega")
        self.assertEqual(data["release_title"], "Single")
        self.assertEqual(data["track"]["id"], self.track.pk)
        self.assertEqual(data["currency"], "USD")
        self.assertEqual({row["isrc"]: (row["source_asset_kind"], row["total"], row["line_count"]) for row in data["by_asset"]}, {
            "USCGH2458227": ("audio", "6.1677", 2), "QZNFJ2406014": ("music_video", "80.1562", 2),
        })
        self.assertEqual({row["id"]: row["total"] for row in data["by_statement"]}, {
            self.january.pk: "51.9665", self.february.pk: "34.3574",
        })
        for field in ("by_asset", "by_statement"):
            self.assertEqual(sum(Decimal(row["total"]) for row in data[field]), Decimal(data["total_royalties"]))
            self.assertEqual(sum(row["line_count"] for row in data[field]), data["line_count"])
        self.assertEqual(data["by_statement"][0]["filename"], "January.xlsx")
        self.assertEqual(str(data["by_statement"][0]["period_start"]), "2025-01-01")

    def test_only_exact_track_and_label_lines_are_included(self):
        self.add_line("1.0001")
        other = Track.objects.create(release=self.track.release, title=self.track.title, track_number=2)
        self.add_line("10", track=other)
        self.add_line("20", track=None)
        label = Label.objects.create(name="Other", slug="other")
        statement = RoyaltyStatement.objects.create(label=label, filename="Other", distributor="other")
        self.add_line("30", statement)
        data = self.client.get(self.url).data
        self.assertEqual(data["total_royalties"], "1.0001")
        self.assertEqual(data["line_count"], 1)

    def test_empty_track_has_exact_zero(self):
        data = self.client.get(self.url).data
        self.assertEqual(data["total_royalties"], "0.0000")
        self.assertEqual(data["line_count"], 0)
        self.assertEqual(data["by_asset"], [])
        self.assertEqual(data["by_statement"], [])

    def test_unknown_and_negative_adjustments_preserve_precision(self):
        self.add_line("0.0002", source_asset_kind="unknown", isrc="")
        self.add_line("-0.0001", source_asset_kind="unknown", isrc="")
        data = self.client.get(self.url).data
        self.assertEqual(data["total_royalties"], "0.0001")
        self.assertEqual(data["by_asset"], [{"source_asset_kind": "unknown", "isrc": "", "line_count": 2, "total": "0.0001"}])

    def test_different_currencies_are_not_summed(self):
        self.february.currency = "EUR"
        self.february.save()
        self.add_line("1")
        self.add_line("2", self.february)
        self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_other_label_and_missing_track_are_not_accessible(self):
        LabelMembership.objects.filter(user=self.user).delete()
        other_label = Label.objects.create(name="Other", slug="other")
        LabelMembership.objects.create(user=self.user, label=other_label)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.get("/api/catalog/tracks/99999/royalties/").status_code, 404)

    def test_existing_financial_permissions_and_2fa_apply(self):
        for role in (Role.ARTIST, Role.AR):
            self.user.role = role
            self.user.save()
            self.assertEqual(self.client.get(self.url).status_code, 403)
        self.user.role = Role.FINANCE
        self.user.is_2fa_enabled = False
        self.user.save()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 403)
