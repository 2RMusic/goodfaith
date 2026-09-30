"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { TrackAssets } from "@/components/TrackAssets";
import { apiFetch } from "@/lib/api";
import { canManageCatalog, useAuth } from "@/lib/auth";
import {
  buttonPrimaryClassName,
  buttonSecondaryClassName,
  inputClassName,
  labelClassName,
} from "@/lib/catalog-form";
import { formatDate, formatDuration, titleCase } from "@/lib/format";
import { RELEASE_TYPES, type Artist, type Release, type Track } from "@/lib/types";

const EMPTY_TRACK = {
  title: "",
  isrc: "",
  iswc: "",
  track_number: "",
  duration_seconds: "",
};

export default function ReleaseDetailPage() {
  const params = useParams<{ id: string }>();
  const { token, user } = useAuth();
  const [release, setRelease] = useState<Release | null>(null);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEditRelease, setShowEditRelease] = useState(false);
  const [showAddTrack, setShowAddTrack] = useState(false);
  const [editingTrackId, setEditingTrackId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [releaseForm, setReleaseForm] = useState({
    primary_artist: "",
    title: "",
    release_type: "single" as Release["release_type"],
    upc: "",
    release_date: "",
  });
  const [trackForm, setTrackForm] = useState(EMPTY_TRACK);
  const [durationInput, setDurationInput] = useState("");
const [primaryArtistId, setPrimaryArtistId] = useState("");
const [featuredArtistIds, setFeaturedArtistIds] = useState<number[]>([]);
  const canManage = user && canManageCatalog(user.role);

  const load = useCallback(async () => {
    if (!token || !params.id) return;
    setLoading(true);
    setError(null);
    try {
      const releaseData = await apiFetch<Release>(
        `/api/catalog/releases/${params.id}/`,
        {},
        token,
      );
      setRelease(releaseData);
      setReleaseForm({
        primary_artist: String(releaseData.primary_artist),
        title: releaseData.title,
        release_type: releaseData.release_type,
        upc: releaseData.upc ?? "",
        release_date: releaseData.release_date ?? "",
      });
      if (canManage) {
        const artistData = await apiFetch<Artist[]>("/api/catalog/artists/", {}, token);
        setArtists(artistData.filter((artist) => artist.label === releaseData.label));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Release not found.");
    } finally {
      setLoading(false);
    }
  }, [token, params.id, canManage]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleUpdateRelease(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !release || !canManage) return;

    setSubmitting(true);
    setError(null);
    try {
      const body: Record<string, string | number | null> = {
        label: release.label,
        primary_artist: Number(releaseForm.primary_artist),
        title: releaseForm.title.trim(),
        release_type: releaseForm.release_type,
        upc: releaseForm.upc.trim() || null,
        release_date: releaseForm.release_date || null,
      };
      const updated = await apiFetch<Release>(
        `/api/catalog/releases/${release.id}/`,
        { method: "PATCH", body: JSON.stringify(body) },
        token,
      );
      setRelease(updated);
      setShowEditRelease(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update release.");
    } finally {
      setSubmitting(false);
    }
  }

  function startEditTrack(track: Track) {
    setEditingTrackId(track.id);
    setTrackForm({
      title: track.title,
      isrc: track.isrc ?? "",
      iswc: track.iswc ?? "",
      track_number: String(track.track_number),
      duration_seconds: track.duration_seconds ? String(track.duration_seconds) : "",
    });
if (track.duration_seconds) {
  const minutes = Math.floor(track.duration_seconds / 60);
  const seconds = track.duration_seconds % 60;
  setDurationInput(`${minutes}:${String(seconds).padStart(2, "0")}`);
} else {
  setDurationInput("");
}
const primaryCredit = track.artists?.find(
  (credit) => credit.role === "primary"
);

setPrimaryArtistId(
  primaryCredit ? String(primaryCredit.artist) : String(release?.primary_artist ?? "")
);

setFeaturedArtistIds(
  track.artists
    ?.filter((credit) => credit.role === "featured")
    .map((credit) => credit.artist) ?? []
);
    setShowAddTrack(false);
  }

  function resetTrackForm() {
    setTrackForm(EMPTY_TRACK);
    setDurationInput("");
    setEditingTrackId(null);
    setShowAddTrack(false);
  }

  async function handleSaveTrack(event: React.FormEvent) {
    event.preventDefault();

    if (
      !token ||
      !release ||
      !canManage ||
      !trackForm.title.trim() ||
      !primaryArtistId
    ) {
      return;
    }

    setSubmitting(true);
    setError(null);

    const body: Record<string, string | number | null> = {
      release: release.id,
      title: trackForm.title.trim(),
      isrc: trackForm.isrc.trim() || null,
      iswc: trackForm.iswc.trim() || null,
      track_number: trackForm.track_number
        ? Number(trackForm.track_number)
        : release.tracks.length + 1,
    };

    if (durationInput.trim()) {
      const match = durationInput.trim().match(/^(\d+):([0-5]\d)$/);

      if (!match) {
        setError("Duration must use MM:SS format, for example 3:30.");
        setSubmitting(false);
        return;
      }

      body.duration_seconds = Number(match[1]) * 60 + Number(match[2]);
    } else {
      body.duration_seconds = null;
    }

    try {
      let savedTrack: Track;

      if (editingTrackId) {
        savedTrack = await apiFetch<Track>(
          `/api/catalog/tracks/${editingTrackId}/`,
          {
            method: "PATCH",
            body: JSON.stringify(body),
          },
          token,
        );
      } else {
        savedTrack = await apiFetch<Track>(
          "/api/catalog/tracks/",
          {
            method: "POST",
            body: JSON.stringify(body),
          },
          token,
        );
      }

      const desiredCredits = [
        {
          artist: Number(primaryArtistId),
          role: "primary",
          billing_order: 1,
        },
        ...featuredArtistIds.map((artistId, index) => ({
          artist: artistId,
          role: "featured",
          billing_order: index + 2,
        })),
      ];

      const existingCredits = editingTrackId
        ? release.tracks.find((track) => track.id === editingTrackId)?.artists ?? []
        : [];

      for (const credit of existingCredits) {
        const shouldKeep = desiredCredits.some(
          (desired) =>
            desired.artist === credit.artist &&
            desired.role === credit.role,
        );

        if (!shouldKeep) {
          await apiFetch(
            `/api/catalog/track-artists/${credit.id}/`,
            { method: "DELETE" },
            token,
          );
        }
      }

      for (const desired of desiredCredits) {
        const existing = existingCredits.find(
          (credit) => credit.artist === desired.artist,
        );

        if (existing) {
          await apiFetch(
            `/api/catalog/track-artists/${existing.id}/`,
            {
              method: "PATCH",
              body: JSON.stringify({
                track: savedTrack.id,
                artist: desired.artist,
                role: desired.role,
                billing_order: desired.billing_order,
              }),
            },
            token,
          );
        } else {
          await apiFetch(
            "/api/catalog/track-artists/",
            {
              method: "POST",
              body: JSON.stringify({
                track: savedTrack.id,
                artist: desired.artist,
                role: desired.role,
                billing_order: desired.billing_order,
              }),
            },
            token,
          );
        }
      }

      resetTrackForm();
      setPrimaryArtistId("");
      setFeaturedArtistIds([]);
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save track.",
      );
    } finally {
      setSubmitting(false);
    }
  }
async function handleDeleteRelease() {
  if (!token || !release || !canManage) return;

  const confirmed = window.confirm(
    `Delete release "${release.title}"?\n\nThis will also delete all tracks inside this release. This action cannot be undone.`
  );

  if (!confirmed) return;

  setSubmitting(true);
  setError(null);

  try {
    await apiFetch(
      `/api/catalog/releases/${release.id}/`,
      { method: "DELETE" },
      token,
    );

    window.location.href = "/catalog";
  } catch (err) {
    setError(
      err instanceof Error ? err.message : "Failed to delete release."
    );
    setSubmitting(false);
  }
}

  async function handleDeleteTrack(track: Track) {
    if (!token || !canManage) return;
    if (!window.confirm(`Delete track "${track.title}"?`)) return;

    setError(null);
    try {
      await apiFetch(`/api/catalog/tracks/${track.id}/`, { method: "DELETE" }, token);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete track.");
    }
  }

  if (loading) {
    return <p className="text-sm text-[var(--color-muted)]">Loading release…</p>;
  }

  if (error && !release) {
    return (
      <div>
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
        <Link href="/catalog" className="inline-block mt-4 text-sm text-[var(--color-primary-text)]">
          ← Back to catalog
        </Link>
      </div>
    );
  }

  if (!release) return null;

  return (
    <>
      <Link
        href="/catalog"
        className="text-sm text-[var(--color-muted)] hover:text-[var(--color-ink)]"
      >
        ← Catalog
      </Link>

      <PageHeader
        title={release.title}
        description={`${release.primary_artist_name} · ${titleCase(release.release_type)} · ${formatDate(release.release_date)}`}
action={
  canManage ? (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={() => setShowEditRelease((v) => !v)}
        className={buttonSecondaryClassName}
      >
        {showEditRelease ? "Cancel edit" : "Edit release"}
      </button>

      <button
        type="button"
        onClick={handleDeleteRelease}
        disabled={submitting}
        className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
      >
        Delete release
      </button>
    </div>
  ) : undefined
}
      />

      {error ? (
        <p className="mb-4 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      {canManage && showEditRelease ? (
        <form
          onSubmit={handleUpdateRelease}
          className="mb-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-4"
        >
          <h2 className="font-semibold">Edit release</h2>
          <label className={labelClassName}>
            Primary artist
            <select
              required
              value={releaseForm.primary_artist}
              onChange={(event) =>
                setReleaseForm((c) => ({ ...c, primary_artist: event.target.value }))
              }
              className={inputClassName}
            >
              {artists.map((artist) => (
                <option key={artist.id} value={artist.id}>
                  {artist.name}
                </option>
              ))}
            </select>
          </label>
          <label className={labelClassName}>
            Title
            <input
              required
              value={releaseForm.title}
              onChange={(event) => setReleaseForm((c) => ({ ...c, title: event.target.value }))}
              className={inputClassName}
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className={labelClassName}>
              Type
              <select
                value={releaseForm.release_type}
                onChange={(event) =>
                  setReleaseForm((c) => ({
                    ...c,
                    release_type: event.target.value as Release["release_type"],
                  }))
                }
                className={inputClassName}
              >
                {RELEASE_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </label>
            <label className={labelClassName}>
              Release date
              <input
                type="date"
                value={releaseForm.release_date}
                onChange={(event) =>
                  setReleaseForm((c) => ({ ...c, release_date: event.target.value }))
                }
                className={inputClassName}
              />
            </label>
          </div>
          <label className={labelClassName}>
            UPC / EAN
            <input
              value={releaseForm.upc}
              onChange={(event) => setReleaseForm((c) => ({ ...c, upc: event.target.value }))}
              className={inputClassName}
              maxLength={13}
            />
          </label>
          <button type="submit" disabled={submitting} className={buttonPrimaryClassName}>
            {submitting ? "Saving…" : "Save release"}
          </button>
        </form>
      ) : (
        <dl className="grid gap-4 sm:grid-cols-3 mb-8 text-sm">
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <dt className="text-[var(--color-muted)]">UPC / EAN</dt>
            <dd className="mt-1 font-mono">{release.upc ?? "—"}</dd>
          </div>
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <dt className="text-[var(--color-muted)]">Tracks</dt>
            <dd className="mt-1 font-semibold tabular-nums">{release.track_count}</dd>
          </div>
          <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <dt className="text-[var(--color-muted)]">Release type</dt>
            <dd className="mt-1 capitalize">{titleCase(release.release_type)}</dd>
          </div>
        </dl>
      )}

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Track listing</h2>
        {canManage ? (
          <button
            type="button"
            onClick={() => {
              resetTrackForm();
              setShowAddTrack(true);
            }}
            className={buttonPrimaryClassName}
          >
            Add track
          </button>
        ) : null}
      </div>

      {canManage && (showAddTrack || editingTrackId) ? (
        <form
          onSubmit={handleSaveTrack}
          className="mb-6 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-4"
        >
          <h3 className="font-medium">{editingTrackId ? "Edit track" : "New track"}</h3>
<label className={labelClassName}>
  Primary artist
  <select
    required
    value={primaryArtistId}
    onChange={(event) => setPrimaryArtistId(event.target.value)}
    className={inputClassName}
  >
    <option value="">Select artist</option>
    {artists.map((artist) => (
      <option key={artist.id} value={artist.id}>
        {artist.name}
      </option>
    ))}
  </select>
</label>
<label className={labelClassName}>
  Featured artist
  <select
    value=""
    onChange={(event) => {
      const artistId = Number(event.target.value);

      if (artistId && !featuredArtistIds.includes(artistId)) {
        setFeaturedArtistIds((current) => [...current, artistId]);
      }
    }}
    className={inputClassName}
  >
    <option value="">Add featured artist...</option>
    {artists
      .filter(
        (artist) =>
          String(artist.id) !== primaryArtistId &&
          !featuredArtistIds.includes(artist.id)
      )
      .map((artist) => (
        <option key={artist.id} value={artist.id}>
          {artist.name}
        </option>
      ))}
  </select>

  {featuredArtistIds.map((artistId) => {
    const artist = artists.find((item) => item.id === artistId);

    return (
      <div
        key={artistId}
        className="mt-2 flex items-center justify-between rounded-lg border border-[var(--color-border)] px-3 py-2"
      >
        <span>{artist?.name ?? `Artist #${artistId}`}</span>
        <button
          type="button"
          onClick={() =>
            setFeaturedArtistIds((current) =>
              current.filter((id) => id !== artistId)
            )
          }
          className="text-xs text-red-600 hover:underline"
        >
          Remove
        </button>
      </div>
    );
  })}
</label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className={labelClassName}>
              Title
              <input
                required
                value={trackForm.title}
                onChange={(event) => setTrackForm((c) => ({ ...c, title: event.target.value }))}
                className={inputClassName}
              />
            </label>
            <label className={labelClassName}>
              ISRC
              <input
                value={trackForm.isrc}
                onChange={(event) => setTrackForm((c) => ({ ...c, isrc: event.target.value }))}
                className={inputClassName}
                placeholder="USRC17607839"
                maxLength={12}
              />
            </label>
            <label className={labelClassName}>
              ISWC
              <input
                value={trackForm.iswc}
                onChange={(event) => setTrackForm((c) => ({ ...c, iswc: event.target.value }))}
                className={inputClassName}
                placeholder="T-123.456.789-0"
                maxLength={15}
              />
            </label>
            <label className={labelClassName}>
              Track #
              <input
                type="number"
                min={1}
                value={trackForm.track_number}
                onChange={(event) =>
                  setTrackForm((c) => ({ ...c, track_number: event.target.value }))
                }
                className={inputClassName}
                placeholder={String(release.tracks.length + 1)}
              />
            </label>
            <label className={labelClassName}>
  Duration (MM:SS)
  <input
    type="text"
    value={durationInput}
    onChange={(event) => setDurationInput(event.target.value)}
    className={inputClassName}
    placeholder="3:30"
    inputMode="numeric"
  />
</label>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={submitting} className={buttonPrimaryClassName}>
              {submitting ? "Saving…" : editingTrackId ? "Save track" : "Add track"}
            </button>
            <button type="button" onClick={resetTrackForm} className={buttonSecondaryClassName}>
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {release.tracks.length === 0 ? (
        <p className="text-sm text-[var(--color-muted)]">
          No tracks yet. Add tracks with ISRCs so royalty statements can match earnings.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-surface)] text-left text-[var(--color-muted)]">
              <tr>
                <th className="px-4 py-3 font-medium w-12">#</th>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">ISWC</th>
                <th className="px-4 py-3 font-medium text-right">Duration</th>
                {canManage ? <th className="px-4 py-3 font-medium text-right">Actions</th> : null}
              </tr>
            </thead>
            <tbody>
              {release.tracks.map((track) => (
                <tr key={track.id} className="border-t border-[var(--color-border)]">
                  <td className="px-4 py-3 tabular-nums text-[var(--color-muted)]">
                    {track.track_number}
                  </td>
                  <td className="px-4 py-3">
  <div className="font-medium">{track.title}</div>
  {track.artists?.length > 0 ? (
    <div className="mt-1 text-xs text-[var(--color-muted)]">
      {track.artists
        .map((credit) =>
          credit.role === "featured"
            ? `feat. ${credit.artist_name}`
            : credit.artist_name
        )
        .join(" · ")}
    </div>
  ) : null}
                  <TrackAssets
                    track={track}
                    token={token}
                    canManage={Boolean(canManage)}
                    onAssetsChange={(assets) => setRelease((current) => current ? {
                      ...current,
                      tracks: current.tracks.map((item) => item.id === track.id ? { ...item, assets } : item),
                    } : current)}
                  />
</td>
                  <td className="px-4 py-3 font-mono text-xs">{track.iswc ?? "—"}</td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {formatDuration(track.duration_seconds)}
                  </td>
                  {canManage ? (
                    <td className="px-4 py-3 text-right space-x-3">
                      <button
                        type="button"
                        onClick={() => startEditTrack(track)}
                        className="text-xs font-medium text-[var(--color-primary-text)] hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteTrack(track)}
                        className="text-xs font-medium text-red-600 dark:text-red-400 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
