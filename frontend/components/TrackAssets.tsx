import { useState } from "react";

import { apiFetch } from "@/lib/api";
import {
  buttonPrimaryClassName,
  buttonSecondaryClassName,
  inputClassName,
  labelClassName,
} from "@/lib/catalog-form";
import type { Track, TrackAsset } from "@/lib/types";

const ASSET_LABELS: Record<TrackAsset["asset_kind"], string> = {
  audio: "Audio",
  music_video: "Music Video",
  other: "Other",
  unknown: "Unknown",
};

export function TrackAssets({ track, token, canManage, onAssetsChange }: {
  track: Track;
  token: string | null;
  canManage: boolean;
  onAssetsChange: (assets: TrackAsset[]) => void;
}) {
  const [form, setForm] = useState<{ id?: number; isrc: string; asset_kind: TrackAsset["asset_kind"] } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const assets = track.assets ?? [];
  const endpoint = `/api/catalog/tracks/${track.id}/assets/`;

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!form || !token || !canManage || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const saved = await apiFetch<TrackAsset>(
        form.id ? `${endpoint}${form.id}/` : endpoint,
        {
          method: form.id ? "PATCH" : "POST",
          body: JSON.stringify({ isrc: form.isrc.trim().toUpperCase(), asset_kind: form.asset_kind }),
        },
        token,
      );
      onAssetsChange(form.id ? assets.map((asset) => asset.id === saved.id ? saved : asset) : [...assets, saved]);
      setForm(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save asset.");
    } finally {
      setSubmitting(false);
    }
  }

  async function remove(asset: TrackAsset) {
    if (!token || !canManage || submitting) return;
    if (!window.confirm(`Delete ${ASSET_LABELS[asset.asset_kind]} asset ${asset.isrc} from "${track.title}"?`)) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch(`${endpoint}${asset.id}/`, { method: "DELETE" }, token);
      onAssetsChange(assets.filter((item) => item.id !== asset.id));
      if (form?.id === asset.id) setForm(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete asset.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section aria-label={`Assets for ${track.title}`} className="mt-3 min-w-64 max-w-xl space-y-2">
      <p className="text-xs font-medium text-[var(--color-muted)]">Assets</p>
      {track.isrc ? (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span>Audio · <span className="font-mono">{track.isrc}</span></span>
          <span className="text-[var(--color-muted)]">Primary</span>
        </div>
      ) : <p className="text-xs text-[var(--color-muted)]">No primary audio ISRC.</p>}
      {assets.map((asset) => (
        <div key={asset.id} className="flex flex-wrap items-center gap-3 text-xs">
          <span>{ASSET_LABELS[asset.asset_kind]} · <span className="font-mono">{asset.isrc}</span></span>
          {canManage ? (
            <>
              <button type="button" disabled={submitting} aria-label={`Edit asset ${asset.isrc}`}
                onClick={() => { setForm({ ...asset }); setError(null); }}
                className="text-[var(--color-primary-text)] hover:underline disabled:opacity-50">Edit</button>
              <button type="button" disabled={submitting} aria-label={`Delete asset ${asset.isrc}`}
                onClick={() => remove(asset)}
                className="text-red-600 dark:text-red-400 hover:underline disabled:opacity-50">Delete</button>
            </>
          ) : null}
        </div>
      ))}
      {error ? <p role="alert" className="text-xs text-red-600 dark:text-red-400">{error}</p> : null}
      {canManage && !form ? (
        <button type="button" disabled={submitting}
          onClick={() => { setForm({ isrc: "", asset_kind: "music_video" }); setError(null); }}
          className="text-xs font-medium text-[var(--color-primary-text)] hover:underline disabled:opacity-50">
          + Add asset
        </button>
      ) : null}
      {canManage && form ? (
        <form onSubmit={save} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4 space-y-3">
          <h3 className="text-sm font-medium">{form.id ? "Edit asset" : "Add asset"}</h3>
          <label className={labelClassName}>
            Asset type
            <select value={form.asset_kind} disabled={submitting} className={inputClassName}
              onChange={(event) => setForm({ ...form, asset_kind: event.target.value as TrackAsset["asset_kind"] })}>
              <option value="audio">Audio</option>
              <option value="music_video">Music Video</option>
              <option value="other">Other</option>
              {form.asset_kind === "unknown" ? <option value="unknown">Unknown</option> : null}
            </select>
          </label>
          <label className={labelClassName}>
            ISRC
            <input required value={form.isrc} disabled={submitting} className={inputClassName}
              onChange={(event) => setForm({ ...form, isrc: event.target.value.trim().toUpperCase() })}
              maxLength={12} pattern="[A-Z]{2}[A-Z0-9]{3}[0-9]{7}" placeholder="QZNFJ2406014"
              title="Enter a 12-character ISRC without spaces or hyphens." />
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={submitting} className={buttonPrimaryClassName}>
              {submitting ? "Saving…" : "Save asset"}
            </button>
            <button type="button" disabled={submitting} className={buttonSecondaryClassName}
              onClick={() => { setForm(null); setError(null); }}>Cancel</button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
