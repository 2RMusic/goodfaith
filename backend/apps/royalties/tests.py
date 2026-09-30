from decimal import Decimal
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.accounts.test_utils import satisfy_mandatory_2fa
from apps.catalog.models import Artist, AssetKind, Label, LabelMembership, Release, Track, TrackIdentifier
from apps.splits.models import SplitEntry, SplitRole, SplitSheet, SplitSheetStatus

from .models import Distributor, RoyaltyLineItem, RoyaltyRun, RoyaltyRunStatus, RoyaltyStatement, StatementStatus

User = get_user_model()


class CommercialIdentifierTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.label = Label.objects.create(name="Good Faith", slug="identifiers")
        artist = Artist.objects.create(label=self.label, name="Artist", slug="artist")
        release = Release.objects.create(label=self.label, primary_artist=artist, title="Single")
        self.track = Track.objects.create(release=release, title="Voy A Desaparecer", isrc="USCGH2458227")
        self.identifier = TrackIdentifier.objects.create(
            label=self.label, track=self.track, value="QZNFJ2406014", asset_kind=AssetKind.MUSIC_VIDEO,
        )

    def process(self, label=None, codes=("USCGH2458227", "QZNFJ2406014")):
        from .tasks import process_statement

        content = "ISRC,Track Title,USD Revenue\n" + "".join(
            f"{code},Voy A Desaparecer,10.00\n" for code in codes
        )
        statement = RoyaltyStatement.objects.create(
            label=label or self.label, distributor=Distributor.COLONIZE, filename="colonize.csv",
            file=SimpleUploadedFile("colonize.csv", content.encode()),
        )
        process_statement(statement.pk)
        statement.refresh_from_db()
        self.assertEqual(statement.status, StatementStatus.PROCESSED)
        return statement

    def test_primary_and_video_preserve_isrc_and_classification(self):
        statement = self.process()
        lines = {line.isrc: line for line in statement.line_items.all()}
        self.assertEqual(set(lines), {"USCGH2458227", "QZNFJ2406014"})
        for line in lines.values():
            self.assertEqual(line.track_id, self.track.pk)
            self.assertEqual(line.raw_data["ISRC"], line.isrc)
        self.assertEqual(lines["USCGH2458227"].source_asset_kind, AssetKind.AUDIO)
        self.assertEqual(lines["QZNFJ2406014"].source_asset_kind, AssetKind.MUSIC_VIDEO)
        from .serializers import RoyaltyLineItemSerializer
        self.assertEqual(
            RoyaltyLineItemSerializer(lines["QZNFJ2406014"]).data["source_asset_kind"], "music_video",
        )

    def test_primary_works_without_additional_identifiers(self):
        self.identifier.delete()
        line = self.process(codes=(self.track.isrc,)).line_items.get()
        self.assertEqual(line.track_id, self.track.pk)
        self.assertEqual(line.source_asset_kind, AssetKind.AUDIO)

    def test_unknown_isrc_and_missing_isrc_do_not_match_title(self):
        for line in self.process(codes=("QZNFJ2405938", "")).line_items.all():
            self.assertIsNone(line.track_id)
            self.assertEqual(line.source_asset_kind, AssetKind.UNKNOWN)

    def test_null_or_empty_alternate_kind_defaults_to_unknown(self):
        # Simulate malformed values returned by the lookup without weakening
        # the model's NOT NULL constraint or writing invalid catalog data.
        for kind in (None, ""):
            with self.subTest(kind=kind):
                self.identifier.asset_kind = kind
                with patch("apps.royalties.tasks.TrackIdentifier.objects.filter") as lookup:
                    lookup.return_value.select_related.return_value = [self.identifier]
                    statement = self.process(codes=(self.track.isrc, self.identifier.value, "QZNFJ2405938"))
                lines = {line.isrc: line for line in statement.line_items.all()}
                self.assertEqual(lines[self.track.isrc].source_asset_kind, AssetKind.AUDIO)
                self.assertEqual(lines[self.identifier.value].track_id, self.track.pk)
                self.assertEqual(lines[self.identifier.value].source_asset_kind, AssetKind.UNKNOWN)
                self.assertIsNone(lines["QZNFJ2405938"].track_id)
                self.assertEqual(lines["QZNFJ2405938"].source_asset_kind, AssetKind.UNKNOWN)
                self.assertTrue(all(line.source_asset_kind for line in lines.values()))

    def test_both_matching_paths_are_scoped_to_label(self):
        other = Label.objects.create(name="Other", slug="other")
        for line in self.process(label=other).line_items.all():
            self.assertIsNone(line.track_id)
            self.assertEqual(line.source_asset_kind, AssetKind.UNKNOWN)
        artist = Artist.objects.create(label=other, name="Other", slug="other")
        release = Release.objects.create(label=other, primary_artist=artist, title="Other")
        track = Track.objects.create(release=release, title="Other")
        TrackIdentifier.objects.create(label=other, track=track, value=self.identifier.value, asset_kind=AssetKind.OTHER)
        line = self.process(label=other, codes=(self.identifier.value,)).line_items.get()
        self.assertEqual(line.track_id, track.pk)
        self.assertEqual(line.source_asset_kind, AssetKind.OTHER)

    def test_primary_match_takes_precedence(self):
        other_track = Track.objects.create(release=self.track.release, title="Other", track_number=2)
        TrackIdentifier.objects.create(
            label=self.label, track=other_track, value=self.track.isrc, asset_kind=AssetKind.OTHER,
        )
        line = self.process(codes=(self.track.isrc,)).line_items.get()
        self.assertEqual(line.track_id, self.track.pk)
        self.assertEqual(line.source_asset_kind, AssetKind.AUDIO)

    def test_stale_identifier_cannot_cross_labels(self):
        other = Label.objects.create(name="Other", slug="other")
        TrackIdentifier.objects.filter(pk=self.identifier.pk).update(label=other)
        line = self.process(label=other, codes=(self.identifier.value,)).line_items.get()
        self.assertIsNone(line.track_id)
        self.assertEqual(line.source_asset_kind, AssetKind.UNKNOWN)

    def test_reprocess_matches_new_identifier_without_duplicate_lines(self):
        from .tasks import process_statement

        self.identifier.delete()
        statement = self.process()
        self.assertIsNone(statement.line_items.get(isrc="QZNFJ2406014").track_id)
        TrackIdentifier.objects.create(
            label=self.label, track=self.track, value="QZNFJ2406014", asset_kind=AssetKind.MUSIC_VIDEO,
        )
        for _ in range(2):
            process_statement(statement.pk)
            statement.refresh_from_db()
            self.assertEqual(statement.row_count, 2)
            self.assertEqual(statement.line_items.count(), 2)
            self.assertEqual(statement.total_amount, Decimal("20"))
            self.assertEqual(set(statement.line_items.values_list("track_id", flat=True)), {self.track.pk})
            video = statement.line_items.get(isrc="QZNFJ2406014")
            self.assertEqual(video.source_asset_kind, AssetKind.MUSIC_VIDEO)

    def test_classification_is_snapshot_and_supports_all_kinds(self):
        for kind in AssetKind.values:
            self.identifier.asset_kind = kind
            self.identifier.save()
            line = self.process(codes=(self.identifier.value,)).line_items.get()
            self.assertEqual(line.source_asset_kind, kind)
            self.identifier.asset_kind = AssetKind.UNKNOWN
            self.identifier.save()
            line.refresh_from_db()
            self.assertEqual(line.source_asset_kind, kind)

    def test_high_precision_ledger_total_reconciles_after_import_and_reprocess(self):
        from .tasks import process_statement

        # Include half-way values, negative adjustments, and sub-ledger amounts.
        amounts = ["0.00005", "0.00015", "0.000826", "0.00108864756", "-0.00005", "0.000049999"] * 250
        expected = [Decimal(value) for value in ("0.0001", "0.0002", "0.0008", "0.0011", "-0.0001", "0.0000")] * 250
        codes = [self.track.isrc, self.identifier.value]
        content = "ISRC,Track Title,USD Revenue\n" + "".join(
            f"{codes[index % 2]},Voy A Desaparecer,{amount}\n"
            for index, amount in enumerate(amounts)
        )
        statement = RoyaltyStatement.objects.create(
            label=self.label, distributor=Distributor.COLONIZE, filename="precision.csv",
            file=SimpleUploadedFile("precision.csv", content.encode()),
        )
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                process_statement(statement.pk)
                statement.refresh_from_db()
                lines = list(statement.line_items.order_by("id"))
                self.assertEqual(statement.status, StatementStatus.PROCESSED)
                self.assertEqual(statement.row_count, 1500)
                self.assertEqual(len(lines), len(expected))
                for line, amount in zip(lines, expected):
                    self.assertEqual(line.amount, amount)
                self.assertEqual(statement.total_amount, Decimal("0.5250"))
                self.assertEqual(statement.total_amount, sum((line.amount for line in lines), Decimal("0")))
                self.assertEqual([line.raw_data["USD Revenue"] for line in lines], amounts)
                self.assertEqual({line.track_id for line in lines}, {self.track.pk})
                self.assertEqual({line.source_asset_kind for line in lines}, {AssetKind.AUDIO, AssetKind.MUSIC_VIDEO})

    def test_audio_and_video_share_one_track_split(self):
        from .consolidation import consolidate_run

        sheet = SplitSheet.objects.create(track=self.track, status=SplitSheetStatus.FINALIZED)
        for name, percentage in (("Artist", "70"), ("Producer", "30")):
            SplitEntry.objects.create(split_sheet=sheet, participant_name=name, percentage=Decimal(percentage))
        statement = self.process()
        run = RoyaltyRun.objects.create(label=self.label, name="Audio + video")
        run.statements.add(statement)
        consolidate_run(run)
        self.assertEqual(run.payouts.count(), 2)
        self.assertEqual(set(run.payouts.values_list("track_id", flat=True)), {self.track.pk})
        self.assertEqual(set(run.payouts.values_list("track_gross", flat=True)), {Decimal("20")})
        self.assertEqual(dict(run.payouts.values_list("participant_name", "amount")), {
            "Artist": Decimal("14"), "Producer": Decimal("6"),
        })
        self.assertEqual(run.total_amount, Decimal("20"))


class RoyaltyAPITests(TestCase):
    def setUp(self):
        self.label = Label.objects.create(name="Demo Label", slug="demo-label")
        self.finance = User.objects.create_user(
            username="finance",
            password="testpass123",
            role=Role.FINANCE,
        )
        LabelMembership.objects.create(user=self.finance, label=self.label)
        satisfy_mandatory_2fa(self.finance)
        self.artist = User.objects.create_user(
            username="artist",
            password="testpass123",
            role=Role.ARTIST,
        )
        LabelMembership.objects.create(user=self.artist, label=self.label)
        self.client = APIClient()

    def test_finance_can_upload_and_parse_distrokid_statement(self):
        self.client.force_authenticate(user=self.finance)
        catalog_artist = Artist.objects.create(label=self.label, name="Test Artist", slug="test-artist")
        release = Release.objects.create(label=self.label, primary_artist=catalog_artist, title="Test EP")
        Track.objects.create(release=release, title="Track One", isrc="USRC17607839", track_number=1)

        upload = SimpleUploadedFile(
            "distrokid-q1.csv",
            (
                b"Sale Month,Store,Title,Artist,ISRC,Quantity,Earnings (USD)\n"
                b"2026-01,Spotify,Track One,Test Artist,USRC17607839,100,1.23\n"
                b"2026-01,Apple Music,Unmatched Track,Test Artist,USRC00000000,10,0.45\n"
            ),
            content_type="text/csv",
        )
        response = self.client.post(
            "/api/royalties/statements/",
            {
                "label": self.label.pk,
                "distributor": Distributor.DISTROKID,
                "file": upload,
                "currency": "USD",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

        statement = RoyaltyStatement.objects.get()
        self.assertEqual(statement.filename, "distrokid-q1.csv")
        self.assertEqual(statement.uploaded_by, self.finance)
        # CELERY_TASK_ALWAYS_EAGER runs the parse inline during the request.
        self.assertEqual(statement.status, StatementStatus.PROCESSED)
        self.assertEqual(statement.row_count, 2)
        self.assertEqual(statement.total_amount, Decimal("1.68"))

        matched = RoyaltyLineItem.objects.get(isrc="USRC17607839")
        self.assertEqual(matched.track.title, "Track One")
        self.assertEqual(matched.amount, Decimal("1.23"))

        unmatched = RoyaltyLineItem.objects.get(isrc="USRC00000000")
        self.assertIsNone(unmatched.track)

    def test_upload_with_unmappable_columns_fails_gracefully(self):
        self.client.force_authenticate(user=self.finance)
        upload = SimpleUploadedFile(
            "mystery-statement.csv",
            b"foo,bar\n1,2\n",
            content_type="text/csv",
        )
        response = self.client.post(
            "/api/royalties/statements/",
            {
                "label": self.label.pk,
                "distributor": Distributor.OTHER,
                "file": upload,
                "currency": "USD",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        statement = RoyaltyStatement.objects.get()
        self.assertEqual(statement.status, StatementStatus.FAILED)
        self.assertIn("revenue/earnings column", statement.error_message)

    def test_artist_cannot_list_statements(self):
        self.client.force_authenticate(user=self.artist)
        response = self.client.get("/api/royalties/statements/")
        self.assertEqual(response.status_code, 403)


class RoyaltyRunConsolidationTests(TestCase):
    def setUp(self):
        self.label = Label.objects.create(name="Run Label", slug="run-label")
        self.finance = User.objects.create_user(
            username="runfinance",
            password="testpass123",
            role=Role.FINANCE,
        )
        LabelMembership.objects.create(user=self.finance, label=self.label)
        satisfy_mandatory_2fa(self.finance)
        self.client = APIClient()
        self.client.force_authenticate(user=self.finance)

        artist = Artist.objects.create(label=self.label, name="Run Artist", slug="run-artist")
        release = Release.objects.create(label=self.label, primary_artist=artist, title="Run EP")
        self.track = Track.objects.create(
            release=release,
            title="Run Track",
            isrc="USRC17607839",
            track_number=1,
        )
        sheet = SplitSheet.objects.create(track=self.track, status=SplitSheetStatus.FINALIZED)
        SplitEntry.objects.create(
            split_sheet=sheet,
            participant_name="Run Artist",
            artist=artist,
            role=SplitRole.ARTIST,
            percentage=Decimal("70.00"),
        )
        SplitEntry.objects.create(
            split_sheet=sheet,
            participant_name="Producer",
            role=SplitRole.PRODUCER,
            percentage=Decimal("30.00"),
        )

        self.statement = RoyaltyStatement.objects.create(
            label=self.label,
            distributor=Distributor.DISTROKID,
            filename="run-q1.csv",
            file=SimpleUploadedFile("run-q1.csv", b"header\n"),
            status=StatementStatus.PROCESSED,
            row_count=1,
            total_amount=Decimal("10.0000"),
            currency="USD",
            uploaded_by=self.finance,
        )
        RoyaltyLineItem.objects.create(
            statement=self.statement,
            track=self.track,
            isrc="USRC17607839",
            track_title="Run Track",
            amount=Decimal("10.0000"),
        )

    def test_create_run_applies_finalized_splits(self):
        response = self.client.post(
            "/api/royalties/runs/",
            {
                "label": self.label.pk,
                "name": "Q1 2026",
                "currency": "USD",
                "statements": [self.statement.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], RoyaltyRunStatus.READY)
        self.assertEqual(Decimal(response.data["total_amount"]), Decimal("10.0000"))
        self.assertEqual(response.data["payout_count"], 2)

        payouts = self.client.get(f"/api/royalties/runs/{response.data['id']}/payouts/")
        self.assertEqual(payouts.status_code, 200)
        amounts = {row["participant_name"]: Decimal(row["amount"]) for row in payouts.data}
        self.assertEqual(amounts["Run Artist"], Decimal("7.0000"))
        self.assertEqual(amounts["Producer"], Decimal("3.0000"))

    def test_run_rejects_unprocessed_statement(self):
        pending = RoyaltyStatement.objects.create(
            label=self.label,
            distributor=Distributor.TUNECORE,
            filename="pending.csv",
            file=SimpleUploadedFile("pending.csv", b"header\n"),
            status=StatementStatus.PENDING,
            currency="USD",
            uploaded_by=self.finance,
        )
        response = self.client.post(
            "/api/royalties/runs/",
            {
                "label": self.label.pk,
                "name": "Bad Run",
                "currency": "USD",
                "statements": [pending.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(RoyaltyRun.objects.exists())


class MyEarningsAPITests(TestCase):
    def setUp(self):
        self.label = Label.objects.create(name="Earn Label", slug="earn-label")
        self.finance = User.objects.create_user(
            username="earnfinance",
            password="testpass123",
            role=Role.FINANCE,
        )
        satisfy_mandatory_2fa(self.finance)
        LabelMembership.objects.create(user=self.finance, label=self.label)

        self.artist_user = User.objects.create_user(
            username="earnartist",
            password="testpass123",
            role=Role.ARTIST,
        )
        LabelMembership.objects.create(user=self.artist_user, label=self.label)
        self.artist = Artist.objects.create(
            label=self.label,
            name="Earn Artist",
            slug="earn-artist",
            user=self.artist_user,
        )

        release = Release.objects.create(label=self.label, primary_artist=self.artist, title="Earn EP")
        track = Track.objects.create(release=release, title="Earn Track", isrc="USRC17607841", track_number=1)
        sheet = SplitSheet.objects.create(track=track, status=SplitSheetStatus.FINALIZED)
        SplitEntry.objects.create(
            split_sheet=sheet,
            participant_name="Earn Artist",
            artist=self.artist,
            role=SplitRole.ARTIST,
            percentage=Decimal("100.00"),
        )

        statement = RoyaltyStatement.objects.create(
            label=self.label,
            distributor=Distributor.DISTROKID,
            filename="earn.csv",
            file=SimpleUploadedFile("earn.csv", b"x"),
            status=StatementStatus.PROCESSED,
            currency="USD",
            uploaded_by=self.finance,
        )
        RoyaltyLineItem.objects.create(
            statement=statement,
            track=track,
            isrc="USRC17607841",
            amount=Decimal("25.0000"),
        )
        run = RoyaltyRun.objects.create(label=self.label, name="Q1 Earn", currency="USD")
        run.statements.set([statement])
        from .consolidation import consolidate_run

        consolidate_run(run)

        self.client = APIClient()

    def test_artist_sees_own_earnings_only(self):
        self.client.force_authenticate(user=self.artist_user)
        response = self.client.get("/api/royalties/my-earnings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Decimal(response.data[0]["amount"]), Decimal("25.0000"))
        self.assertEqual(response.data[0]["run_name"], "Q1 Earn")

    def test_manager_gets_empty_earnings_list(self):
        self.client.force_authenticate(user=self.finance)
        response = self.client.get("/api/royalties/my-earnings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
