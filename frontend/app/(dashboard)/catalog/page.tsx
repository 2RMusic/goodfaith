"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { apiFetch } from "@/lib/api";
import { canManageCatalog, isArtistRole, useAuth } from "@/lib/auth";
import {
  buttonPrimaryClassName,
  buttonSecondaryClassName,
  inputClassName,
  labelClassName,
} from "@/lib/catalog-form";
import { formatDate, titleCase } from "@/lib/format";
import { RELEASE_TYPES, type Artist, type Label, type Release } from "@/lib/types";

export default function CatalogPage() {
  const router = useRouter();
  const { token, user } = useAuth();
  const [releases, setReleases] = useState<Release[]>([]);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [labels, setLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    label: "",
    primary_artist: "",
    title: "",
    release_type: "single" as Release["release_type"],
    upc: "",
    release_date: "",
  });

  const canManage = user && canManageCatalog(user.role);
  const isArtist = user && isArtistRole(user.role);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    Promise.all([
      apiFetch<Release[]>("/api/catalog/releases/", {}, token),
      canManage ? apiFetch<Artist[]>("/api/catalog/artists/", {}, token) : Promise.resolve([]),
      canManage ? apiFetch<Label[]>("/api/catalog/labels/", {}, token) : Promise.resolve([]),
    ])
      .then(([releaseData, artistData, labelData]) => {
        setReleases(releaseData);
        setArtists(artistData);
        setLabels(labelData);
        if (labelData.length === 1) {
          setForm((current) => ({ ...current, label: String(labelData[0].id) }));
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load catalog."))
      .finally(() => setLoading(false));
  }, [token, canManage]);

  const rosterArtists = form.label
    ? artists.filter((artist) => artist.label === Number(form.label))
    : artists;

  async function handleCreateRelease(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !canManage || !form.label || !form.primary_artist || !form.title) return;

    setSubmitting(true);
    setError(null);
    try {
      const body: Record<string, string | number> = {
        label: Number(form.label),
        primary_artist: Number(form.primary_artist),
        title: form.title.trim(),
        release_type: form.release_type,
      };
      if (form.upc.trim()) body.upc = form.upc.trim();
      if (form.release_date) body.release_date = form.release_date;

      const created = await apiFetch<Release>(
        "/api/catalog/releases/",
        { method: "POST", body: JSON.stringify(body) },
        token,
      );
      setShowForm(false);
      setForm((current) => ({
        ...current,
        title: "",
        upc: "",
        release_date: "",
        primary_artist: "",
      }));
      router.push(`/catalog/releases/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create release.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title={isArtist ? "My releases" : "Catalog"}
        description={
          isArtist
            ? "Releases you're credited on with the label."
            : "Releases, tracks, and identifiers across your roster."
        }
        action={
          <div className="flex gap-2">
            {canManage ? (
              <button
                type="button"
                onClick={() => setShowForm((v) => !v)}
                className={buttonPrimaryClassName}
              >
                {showForm ? "Cancel" : "Add release"}
              </button>
            ) : null}
            <Link href="/catalog/artists" className={buttonSecondaryClassName}>
              View artists
            </Link>
          </div>
        }
      />

      {error ? (
        <p className="mb-4 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      {canManage && showForm ? (
        <form
          onSubmit={handleCreateRelease}
          className="mb-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-4"
        >
          <h2 className="font-semibold">New release</h2>
          {labels.length > 1 ? (
            <label className={labelClassName}>
              Label
              <select
                required
                value={form.label}
                onChange={(event) =>
                  setForm((c) => ({ ...c, label: event.target.value, primary_artist: "" }))
                }
                className={inputClassName}
              >
                <option value="">Select label…</option>
                {labels.map((label) => (
                  <option key={label.id} value={label.id}>
                    {label.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label className={labelClassName}>
            Primary artist
            <select
              required
              value={form.primary_artist}
              onChange={(event) => setForm((c) => ({ ...c, primary_artist: event.target.value }))}
              className={inputClassName}
            >
              <option value="">Select artist…</option>
              {rosterArtists.map((artist) => (
                <option key={artist.id} value={artist.id}>
                  {artist.name}
                </option>
              ))}
            </select>
          </label>
          {rosterArtists.length === 0 ? (
            <p className="text-sm text-[var(--color-muted)]">
              <Link href="/catalog/artists" className="text-[var(--color-primary-text)] hover:underline">
                Add an artist
              </Link>{" "}
              before creating a release.
            </p>
          ) : null}
          <label className={labelClassName}>
            Title
            <input
              required
              value={form.title}
              onChange={(event) => setForm((c) => ({ ...c, title: event.target.value }))}
              className={inputClassName}
              placeholder="Release title"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className={labelClassName}>
              Type
              <select
                value={form.release_type}
                onChange={(event) =>
                  setForm((c) => ({
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
                value={form.release_date}
                onChange={(event) => setForm((c) => ({ ...c, release_date: event.target.value }))}
                className={inputClassName}
              />
            </label>
          </div>
          <label className={labelClassName}>
            UPC / EAN
            <input
              value={form.upc}
              onChange={(event) => setForm((c) => ({ ...c, upc: event.target.value }))}
              className={inputClassName}
              placeholder="Optional 12–13 digit barcode"
              maxLength={13}
            />
          </label>
          <button
            type="submit"
            disabled={submitting || rosterArtists.length === 0}
            className={buttonPrimaryClassName}
          >
            {submitting ? "Creating…" : "Create release"}
          </button>
        </form>
      ) : null}

      {loading ? (
        <p className="text-sm text-[var(--color-muted)]">Loading releases…</p>
      ) : releases.length === 0 ? (
        <EmptyState
          title="No releases yet"
          description={
            canManage
              ? "Create a release and add tracks with ISRCs for royalty matching."
              : "Releases will appear here once your label adds them."
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-surface)] text-left text-[var(--color-muted)]">
              <tr>
                <th className="px-4 py-3 font-medium">Release</th>
                <th className="px-4 py-3 font-medium">Artist</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">UPC</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium text-right">Tracks</th>
              </tr>
            </thead>
            <tbody>
{releases.map((release) => (
  <tr
    key={release.id}
    className="border-t border-[var(--color-border)] hover:bg-[var(--color-surface)]"
  >
    <td className="px-4 py-3">
      <Link
        href={`/catalog/releases/${release.id}`}
        className="font-medium text-[var(--color-primary-text)] hover:underline"
      >
        {release.title}
      </Link>

      {release.tracks?.length > 0 ? (
        <div className="mt-2 space-y-1">
          {release.tracks.map((track) => (
            <div
              key={track.id}
              className="text-xs text-[var(--color-muted)]"
            >
              {String(track.track_number).padStart(2, "0")}. {track.title}

              {track.artists?.length > 0 ? (
                <>
                  {" — "}
                  {track.artists
                    .map((credit) =>
                      credit.role === "featured"
                        ? `feat. ${credit.artist_name}`
                        : credit.artist_name
                    )
                    .join(" · ")}
                </>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </td>

    <td className="px-4 py-3">
      {release.primary_artist_name}
    </td>

    <td className="px-4 py-3 capitalize">
      {titleCase(release.release_type)}
    </td>

    <td className="px-4 py-3 font-mono text-xs">
      {release.upc ?? "—"}
    </td>

    <td className="px-4 py-3">
      {formatDate(release.release_date)}
    </td>

    <td className="px-4 py-3 text-right tabular-nums">
      {release.track_count}
    </td>
  </tr>
))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
