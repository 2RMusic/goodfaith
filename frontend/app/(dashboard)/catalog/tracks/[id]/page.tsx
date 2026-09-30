"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import type { Track } from "@/lib/types";

type TrackRoyalties = {
  track: Track;
  release_title: string;
  primary_artist_name: string;
  currency: string | null;
  total_royalties: string;
  line_count: number;
  by_asset: { source_asset_kind: string; isrc: string; line_count: number; total: string }[];
  by_statement: {
    id: number; filename: string; period_start: string | null; period_end: string | null;
    distributor_display: string; line_count: number; total: string;
  }[];
};

const KIND_LABELS: Record<string, string> = {
  audio: "Audio", music_video: "Music Video", other: "Other", unknown: "Unknown",
};

export default function TrackDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const [result, setResult] = useState<{ id: string; data?: TrackRoyalties; error?: string } | null>(null);

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiFetch<TrackRoyalties>(`/api/catalog/tracks/${id}/royalties/`, {}, token)
      .then((data) => { if (active) setResult({ id, data }); })
      .catch((err) => { if (active) setResult({ id, error: err instanceof Error ? err.message : "Unable to load track." }); });
    return () => { active = false; };
  }, [id, token]);

  if (!result || result.id !== id) return <p className="text-sm text-[var(--color-muted)]">Loading track…</p>;
  if (!result.data) return (
    <div>
      <p role="alert" className="text-sm text-red-600 dark:text-red-400">{result.error}</p>
      <Link href="/catalog" className="mt-4 inline-block text-sm text-[var(--color-primary-text)]">← Catalog</Link>
    </div>
  );

  const data = result.data;
  const artists = data.track.artists.map((artist) => artist.role === "featured" ? `feat. ${artist.artist_name}` : artist.artist_name).join(" · ");
  // Keep the API's exact four decimals; do not convert money to JS Number.
  const money = (amount: string) => `${amount}${data.currency ? ` ${data.currency}` : ""}`;
  const cell = "px-4 py-3";
  const numberCell = `${cell} text-right tabular-nums whitespace-nowrap`;

  return (
    <>
      <Link href={`/catalog/releases/${data.track.release}`} className="text-sm text-[var(--color-muted)] hover:text-[var(--color-ink)]">
        ← {data.release_title}
      </Link>
      <PageHeader title={data.track.title} description={`${artists || data.primary_artist_name} · ${data.release_title}`} />
      <section className="mb-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <h2 className="text-sm font-medium text-[var(--color-muted)]">Gross Royalties</h2>
        <p className="mt-2 text-3xl font-semibold tabular-nums">{money(data.total_royalties)}</p>
        <p className="mt-2 text-sm text-[var(--color-muted)]">{data.line_count.toLocaleString("en-US")} line items · Imported earnings before splits</p>
      </section>
      {data.line_count === 0 ? <p className="text-sm text-[var(--color-muted)]">No imported royalties for this track yet.</p> : (
        <>
          <h2 className="mb-3 text-lg font-semibold">Assets</h2>
          <div className="mb-8 overflow-x-auto rounded-xl border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-surface)] text-left text-[var(--color-muted)]">
                <tr><th className={cell}>Asset type</th><th className={cell}>ISRC</th><th className={numberCell}>Gross royalties</th><th className={numberCell}>Line items</th></tr>
              </thead>
              <tbody>{data.by_asset.map((asset) => (
                <tr key={`${asset.source_asset_kind}:${asset.isrc}`} className="border-t border-[var(--color-border)]">
                  <td className={cell}>{KIND_LABELS[asset.source_asset_kind] ?? "Unknown"}</td>
                  <td className={`${cell} font-mono text-xs`}>{asset.isrc || "—"}</td>
                  <td className={numberCell}>{money(asset.total)}</td><td className={numberCell}>{asset.line_count.toLocaleString("en-US")}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          <h2 className="mb-3 text-lg font-semibold">Statements</h2>
          <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-surface)] text-left text-[var(--color-muted)]">
                <tr><th className={cell}>Statement</th><th className={cell}>Period</th><th className={numberCell}>Track royalties</th><th className={numberCell}>Line items</th></tr>
              </thead>
              <tbody>{data.by_statement.map((statement) => (
                <tr key={statement.id} className="border-t border-[var(--color-border)]">
                  <td className={cell}>
                    <Link href={`/royalties/statements/${statement.id}`} className="font-medium text-[var(--color-primary-text)] hover:underline">#{statement.id} · {statement.filename}</Link>
                    <p className="mt-1 text-xs text-[var(--color-muted)]">{statement.distributor_display}</p>
                  </td>
                  <td className={cell}>{formatDate(statement.period_start)} – {formatDate(statement.period_end)}</td>
                  <td className={numberCell}>{money(statement.total)}</td><td className={numberCell}>{statement.line_count.toLocaleString("en-US")}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
