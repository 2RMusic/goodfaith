from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Role

from .models import Artist, AssetKind, Label, LabelMembership, Release, ReleaseType, Track, TrackIdentifier
from django.core.exceptions import ValidationError

User = get_user_model()


class TrackIdentifierTests(TestCase):
    def setUp(self):
        self.label = Label.objects.create(name="Identifiers", slug="identifiers")
        artist = Artist.objects.create(label=self.label, name="Artist", slug="artist")
        release = Release.objects.create(label=self.label, primary_artist=artist, title="Single")
        self.track = Track.objects.create(release=release, title="Voy A Desaparecer", isrc="USCGH2458227")

    def test_normalizes_additional_isrc_without_changing_primary(self):
        identifier = TrackIdentifier.objects.create(
            label=self.label, track=self.track, value=" qznfj2406014 ", asset_kind=AssetKind.MUSIC_VIDEO,
        )
        self.assertEqual(identifier.value, "QZNFJ2406014")
        self.track.refresh_from_db()
        self.assertEqual(self.track.isrc, "USCGH2458227")

    def test_rejects_duplicate_within_label(self):
        TrackIdentifier.objects.create(label=self.label, track=self.track, value="QZNFJ2406014")
        with self.assertRaises(ValidationError):
            TrackIdentifier.objects.create(label=self.label, track=self.track, value="QZNFJ2406014")

    def test_rejects_inconsistent_label(self):
        other = Label.objects.create(name="Other", slug="other")
        with self.assertRaises(ValidationError):
            TrackIdentifier.objects.create(label=other, track=self.track, value="QZNFJ2406014")

    def test_validates_type_kind_and_isrc(self):
        for changes in ({"identifier_type": "upc"}, {"asset_kind": "invalid"}, {"value": "invalid"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                fields = dict(label=self.label, track=self.track, value="QZNFJ2406014")
                fields.update(changes)
                TrackIdentifier.objects.create(**fields)


class TrackAssetAPITests(TestCase):
    def setUp(self):
        self.label = Label.objects.create(name="Assets", slug="assets")
        self.other_label = Label.objects.create(name="Other", slug="other-assets")
        self.manager = User.objects.create_user(username="asset-manager", role=Role.MANAGER)
        LabelMembership.objects.create(user=self.manager, label=self.label)
        self.artist = Artist.objects.create(label=self.label, name="Artist", slug="artist")
        self.release = Release.objects.create(label=self.label, primary_artist=self.artist, title="Single")
        self.track = Track.objects.create(release=self.release, title="Voy A Desaparecer", isrc="USCGH2458227")
        self.second = Track.objects.create(release=self.release, title="Second", track_number=2)
        other_artist = Artist.objects.create(label=self.other_label, name="Other", slug="other")
        other_release = Release.objects.create(label=self.other_label, primary_artist=other_artist, title="Other")
        self.other_track = Track.objects.create(release=other_release, title="Other")
        self.url = f"/api/catalog/tracks/{self.track.pk}/assets/"
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def create_asset(self, **overrides):
        body = {"isrc": "QZNFJ2406014", "asset_kind": "music_video", **overrides}
        return self.client.post(self.url, body, format="json")

    def test_create_normalizes_and_keeps_one_track(self):
        count = Track.objects.count()
        response = self.create_asset(isrc=" qznfj2406014 ", label=self.other_label.pk, track=self.other_track.pk)
        self.assertEqual(response.status_code, 201)
        asset = TrackIdentifier.objects.get(pk=response.data["id"])
        self.assertEqual((asset.track_id, asset.label_id), (self.track.pk, self.label.pk))
        self.assertEqual(asset.value, "QZNFJ2406014")
        self.assertEqual(asset.asset_kind, AssetKind.MUSIC_VIDEO)
        self.assertEqual(asset.identifier_type, "isrc")
        self.assertEqual(Track.objects.count(), count)
        self.assertEqual(self.client.get(self.url).data, [response.data])
        release = self.client.get(f"/api/catalog/releases/{self.release.pk}/").data
        self.assertEqual(release["tracks"][0]["assets"], [response.data])

    def test_required_and_invalid_fields(self):
        for body in ({"asset_kind": "audio"}, {"isrc": ""}, {"isrc": "invalid", "asset_kind": "audio"},
                     {"isrc": "QZNFJ2406014", "asset_kind": "invalid"}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post(self.url, body, format="json").status_code, 400)
        self.assertFalse(TrackIdentifier.objects.exists())

    def test_duplicates_rejected_across_tracks_in_label(self):
        self.assertEqual(self.create_asset().status_code, 201)
        self.assertEqual(self.create_asset(isrc="qznfj2406014").status_code, 400)
        response = self.client.post(f"/api/catalog/tracks/{self.second.pk}/assets/", {
            "isrc": "QZNFJ2406014", "asset_kind": "audio",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.create_asset(isrc=self.track.isrc).status_code, 400)

    def test_same_isrc_allowed_in_different_label(self):
        TrackIdentifier.objects.create(label=self.other_label, track=self.other_track, value="QZNFJ2406014")
        self.assertEqual(self.create_asset().status_code, 201)

    def test_edit_type_and_isrc_without_reassigning_track(self):
        asset_id = self.create_asset().data["id"]
        response = self.client.patch(f"{self.url}{asset_id}/", {
            "isrc": " qznfj2406015 ", "asset_kind": "other",
            "track": self.other_track.pk, "label": self.other_label.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200)
        asset = TrackIdentifier.objects.get(pk=asset_id)
        self.assertEqual((asset.value, asset.asset_kind), ("QZNFJ2406015", "other"))
        self.assertEqual((asset.track_id, asset.label_id), (self.track.pk, self.label.pk))
        self.assertEqual(self.client.patch(f"{self.url}{asset_id}/", {"asset_kind": "audio"}, format="json").status_code, 200)

    def test_edit_rejects_duplicate_and_invalid_isrc(self):
        asset_id = self.create_asset().data["id"]
        TrackIdentifier.objects.create(label=self.label, track=self.second, value="QZNFJ2406015")
        for value in ("QZNFJ2406015", self.track.isrc, "", "invalid"):
            with self.subTest(value=value):
                response = self.client.patch(f"{self.url}{asset_id}/", {"isrc": value}, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertEqual(TrackIdentifier.objects.get(pk=asset_id).value, "QZNFJ2406014")

    def test_delete_only_additional_asset(self):
        asset_id = self.create_asset().data["id"]
        self.assertEqual(self.client.delete(f"{self.url}{asset_id}/").status_code, 204)
        self.assertFalse(TrackIdentifier.objects.filter(pk=asset_id).exists())
        self.track.refresh_from_db()
        self.assertEqual(self.track.isrc, "USCGH2458227")
        self.assertEqual(self.client.get(self.url).data, [])

    def test_label_and_track_isolation_for_all_operations(self):
        asset = TrackIdentifier.objects.create(label=self.other_label, track=self.other_track, value="QZNFJ2406014")
        other_url = f"/api/catalog/tracks/{self.other_track.pk}/assets/"
        self.assertEqual(self.client.get(other_url).status_code, 404)
        self.assertEqual(self.client.post(other_url, {"isrc": "QZNFJ2406015", "asset_kind": "audio"}, format="json").status_code, 404)
        for url in (f"{other_url}{asset.pk}/", f"{self.url}{asset.pk}/"):
            self.assertEqual(self.client.patch(url, {"asset_kind": "audio"}, format="json").status_code, 404)
            self.assertEqual(self.client.delete(url).status_code, 404)
        own = self.create_asset().data["id"]
        wrong_track_url = f"/api/catalog/tracks/{self.second.pk}/assets/{own}/"
        self.assertEqual(self.client.delete(wrong_track_url).status_code, 404)
        self.assertTrue(TrackIdentifier.objects.filter(pk=own).exists())

    def test_artist_read_only_and_own_track_scope(self):
        asset_id = self.create_asset().data["id"]
        user = User.objects.create_user(username="asset-artist", role=Role.ARTIST)
        LabelMembership.objects.create(user=user, label=self.label)
        self.artist.user = user
        self.artist.save()
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.create_asset().status_code, 403)
        self.assertEqual(self.client.patch(f"{self.url}{asset_id}/", {"asset_kind": "other"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"{self.url}{asset_id}/").status_code, 403)
        other_artist = Artist.objects.create(label=self.label, name="Different", slug="different")
        other_release = Release.objects.create(label=self.label, primary_artist=other_artist, title="Different")
        track = Track.objects.create(release=other_release, title="Different")
        self.assertEqual(self.client.get(f"/api/catalog/tracks/{track.pk}/assets/").status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 403)


class CatalogModelTests(TestCase):
    def test_release_track_relationship(self):
        label = Label.objects.create(name="Test Label", slug="test-label")
        artist = Artist.objects.create(label=label, name="Test Artist", slug="test-artist")
        release = Release.objects.create(
            label=label,
            primary_artist=artist,
            title="Test Release",
            release_type=ReleaseType.SINGLE,
            upc="123456789012",
        )
        track = Track.objects.create(
            release=release,
            title="Test Track",
            isrc="USRC17607839",
            track_number=1,
            duration_seconds=210,
        )

        self.assertEqual(release.tracks.get(), track)
        self.assertEqual(track.release, release)


class CatalogAPITests(TestCase):
    def setUp(self):
        self.label = Label.objects.create(name="Good Faith Demo", slug="good-faith-demo")
        self.manager = User.objects.create_user(
            username="manager",
            password="testpass123",
            role=Role.MANAGER,
        )
        LabelMembership.objects.create(user=self.manager, label=self.label)
        self.artist_user = User.objects.create_user(
            username="artist",
            password="testpass123",
            role=Role.ARTIST,
        )
        LabelMembership.objects.create(user=self.artist_user, label=self.label)
        self.artist = Artist.objects.create(
            label=self.label,
            name="Demo Artist",
            slug="demo-artist",
            user=self.artist_user,
        )
        self.client = APIClient()

    def test_manager_can_create_artist(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            "/api/catalog/artists/",
            {"label": self.label.pk, "name": "New Artist", "slug": "new-artist"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Artist.objects.filter(slug="new-artist").count(), 1)

    def test_artist_cannot_create_artist(self):
        self.client.force_authenticate(user=self.artist_user)
        response = self.client.post(
            "/api/catalog/artists/",
            {"label": self.label.pk, "name": "Blocked", "slug": "blocked"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_artist_sees_only_own_releases(self):
        other_artist = Artist.objects.create(
            label=self.label,
            name="Other Artist",
            slug="other-artist",
        )
        Release.objects.create(
            label=self.label,
            primary_artist=self.artist,
            title="Mine",
            release_type=ReleaseType.SINGLE,
        )
        Release.objects.create(
            label=self.label,
            primary_artist=other_artist,
            title="Theirs",
            release_type=ReleaseType.SINGLE,
        )

        self.client.force_authenticate(user=self.artist_user)
        response = self.client.get("/api/catalog/releases/")
        self.assertEqual(response.status_code, 200)
        titles = {item["title"] for item in response.data}
        self.assertEqual(titles, {"Mine"})

    def test_unauthenticated_cannot_access_catalog(self):
        response = self.client.get("/api/catalog/artists/")
        self.assertEqual(response.status_code, 403)

    def test_cannot_create_artist_for_other_label(self):
        other_label = Label.objects.create(name="Other Label", slug="other-label")
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            "/api/catalog/artists/",
            {"label": other_label.pk, "name": "Sneaky", "slug": "sneaky"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_auto_slug_on_artist_create(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            "/api/catalog/artists/",
            {"label": self.label.pk, "name": "Auto Slug Artist"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["slug"], "auto-slug-artist")

    def test_manager_can_create_release_and_track(self):
        self.client.force_authenticate(user=self.manager)
        release_response = self.client.post(
            "/api/catalog/releases/",
            {
                "label": self.label.pk,
                "primary_artist": self.artist.pk,
                "title": "New Single",
                "release_type": ReleaseType.SINGLE,
                "upc": "987654321098",
            },
            format="json",
        )
        self.assertEqual(release_response.status_code, 201)
        release_id = release_response.data["id"]

        track_response = self.client.post(
            "/api/catalog/tracks/",
            {
                "release": release_id,
                "title": "Track One",
                "isrc": "USRC17607841",
            },
            format="json",
        )
        self.assertEqual(track_response.status_code, 201)
        self.assertEqual(track_response.data["track_number"], 1)

    def test_manager_can_invite_artist_portal_login(self):
        unlinked = Artist.objects.create(
            label=self.label,
            name="Invite Me",
            slug="invite-me",
        )
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            f"/api/catalog/artists/{unlinked.pk}/invite/",
            {
                "username": "inviteartist",
                "password": "securepass1",
                "email": "invite@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        unlinked.refresh_from_db()
        self.assertIsNotNone(unlinked.user_id)
        self.assertEqual(unlinked.user.username, "inviteartist")
        self.assertEqual(unlinked.user.role, Role.ARTIST)
        self.assertTrue(
            LabelMembership.objects.filter(user=unlinked.user, label=self.label).exists()
        )
        self.assertEqual(response.data["username"], "inviteartist")

    def test_invite_rejected_when_already_linked(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post(
            f"/api/catalog/artists/{self.artist.pk}/invite/",
            {"username": "another", "password": "securepass1"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
