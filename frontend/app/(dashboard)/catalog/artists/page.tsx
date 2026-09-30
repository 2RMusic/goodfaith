"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { apiFetch } from "@/lib/api";
import { canManageCatalog, useAuth } from "@/lib/auth";
import {
  buttonPrimaryClassName,
  buttonSecondaryClassName,
  inputClassName,
  labelClassName,
  slugify,
} from "@/lib/catalog-form";
import type { Artist, Label } from "@/lib/types";

export default function ArtistsPage() {
  const { token, user } = useAuth();
  const [artists, setArtists] = useState<Artist[]>([]);
  const [labels, setLabels] = useState<Label[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [invitingId, setInvitingId] = useState<number | null>(null);
  const [form, setForm] = useState({ label: "", name: "", slug: "" });
  const [inviteForm, setInviteForm] = useState({
    username: "",
    password: "",
    email: "",
  });

  const canManage = user && canManageCatalog(user.role);
  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch<Artist[]>("/api/catalog/artists/", {}, token),
      canManage ? apiFetch<Label[]>("/api/catalog/labels/", {}, token) : Promise.resolve([]),
    ])
      .then(([artistData, labelData]) => {
        setArtists(artistData);
        setLabels(labelData);
        if (labelData.length === 1) {
          setForm((current) => ({ ...current, label: String(labelData[0].id) }));
        }
      })
      .finally(() => setLoading(false));
  }, [token, canManage]);

  function resetForm() {
    setForm({
      label: labels.length === 1 ? String(labels[0].id) : "",
      name: "",
      slug: "",
    });
    setEditingId(null);
    setShowForm(false);
  }

  function startEdit(artist: Artist) {
    setEditingId(artist.id);
    setInvitingId(null);
    setForm({
      label: String(artist.label),
      name: artist.name,
      slug: artist.slug,
    });
    setShowForm(true);
    setError(null);
  }

  function startInvite(artist: Artist) {
    setInvitingId(artist.id);
    setShowForm(false);
    setEditingId(null);
    setInviteForm({
      username: slugify(artist.name).replace(/-/g, "") || "artist",
      password: "",
      email: "",
    });
    setError(null);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !canManage || !form.label || !form.name) return;

    setSubmitting(true);
    setError(null);
    const body: Record<string, string | number> = {
      label: Number(form.label),
      name: form.name.trim(),
    };
    if (form.slug.trim()) body.slug = slugify(form.slug.trim());

    try {
      if (editingId) {
        const updated = await apiFetch<Artist>(
          `/api/catalog/artists/${editingId}/`,
          { method: "PATCH", body: JSON.stringify(body) },
          token,
        );
        setArtists((current) => current.map((a) => (a.id === updated.id ? updated : a)));
      } else {
        const created = await apiFetch<Artist>(
          "/api/catalog/artists/",
          { method: "POST", body: JSON.stringify(body) },
          token,
        );
        setArtists((current) => [...current, created].sort((a, b) => a.name.localeCompare(b.name)));
      }
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save artist.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleInvite(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !canManage || !invitingId) return;

    setSubmitting(true);
    setError(null);
    try {
      const updated = await apiFetch<Artist>(
        `/api/catalog/artists/${invitingId}/invite/`,
        {
          method: "POST",
          body: JSON.stringify({
            username: inviteForm.username.trim(),
            password: inviteForm.password,
            email: inviteForm.email.trim(),
          }),
        },
        token,
      );
      setArtists((current) => current.map((a) => (a.id === updated.id ? updated : a)));
      setInvitingId(null);
      setInviteForm({ username: "", password: "", email: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create portal login.");
    } finally {
      setSubmitting(false);
    }
  }

  const invitingArtist = artists.find((a) => a.id === invitingId) ?? null;

  return (
    <>
      <PageHeader
        title="Artists"
        description="Signed roster artists on your label."
        action={
          <div className="flex gap-2">
            {canManage ? (
              <button
                type="button"
                onClick={() => {
                  setInvitingId(null);
                  if (showForm && !editingId) resetForm();
                  else {
                    setEditingId(null);
                    setShowForm((v) => !v);
                  }
                }}
                className={buttonPrimaryClassName}
              >
                {showForm && !editingId ? "Cancel" : "Add artist"}
              </button>
            ) : null}
            <Link href="/catalog" className={buttonSecondaryClassName}>
              View releases
            </Link>
          </div>
        }
      />

      {error ? (
        <p className="mb-4 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      ) : null}

      {canManage && invitingArtist ? (
        <form
          onSubmit={handleInvite}
          className="mb-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-4"
        >
          <h2 className="font-semibold">Invite portal login — {invitingArtist.name}</h2>
          <p className="text-sm text-[var(--color-muted)]">
            Creates an Artist-role account linked to this roster entry. Share the credentials
            securely — they can sign in and see their releases, splits, earnings, and payouts.
          </p>
          <label className={labelClassName}>
            Username
            <input
              required
              value={inviteForm.username}
              onChange={(event) => setInviteForm((c) => ({ ...c, username: event.target.value }))}
              className={inputClassName}
            />
          </label>
          <label className={labelClassName}>
            Temporary password
            <input
              required
              type="password"
              minLength={8}
              value={inviteForm.password}
              onChange={(event) => setInviteForm((c) => ({ ...c, password: event.target.value }))}
              className={inputClassName}
              placeholder="At least 8 characters"
            />
          </label>
          <label className={labelClassName}>
            Email (optional)
            <input
              type="email"
              value={inviteForm.email}
              onChange={(event) => setInviteForm((c) => ({ ...c, email: event.target.value }))}
              className={inputClassName}
            />
          </label>
          <div className="flex gap-2">
            <button type="submit" disabled={submitting} className={buttonPrimaryClassName}>
              {submitting ? "Creating…" : "Create portal login"}
            </button>
            <button
              type="button"
              onClick={() => setInvitingId(null)}
              className={buttonSecondaryClassName}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {canManage && showForm ? (
        <form
          onSubmit={handleSubmit}
          className="mb-8 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-4"
        >
          <h2 className="font-semibold">{editingId ? "Edit artist" : "New artist"}</h2>
          {labels.length > 1 ? (
            <label className={labelClassName}>
              Label
              <select
                required
                value={form.label}
                onChange={(event) => setForm((c) => ({ ...c, label: event.target.value }))}
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
            Name
            <input
              required
              value={form.name}
              onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))}
              className={inputClassName}
              placeholder="Artist display name"
            />
          </label>
          <label className={labelClassName}>
            Slug
            <input
              value={form.slug}
              onChange={(event) => setForm((c) => ({ ...c, slug: event.target.value }))}
              className={inputClassName}
              placeholder={form.name ? slugify(form.name) : "auto-generated if blank"}
            />
          </label>
          <div className="flex gap-2">
            <button type="submit" disabled={submitting} className={buttonPrimaryClassName}>
              {submitting ? "Saving…" : editingId ? "Save changes" : "Create artist"}
            </button>
            <button type="button" onClick={resetForm} className={buttonSecondaryClassName}>
              Cancel
            </button>
          </div>
        </form>
      ) : null}

      {loading ? (
        <p className="text-sm text-[var(--color-muted)]">Loading artists…</p>
      ) : artists.length === 0 ? (
        <EmptyState
          title="No artists yet"
          description={
            canManage
              ? "Add your first artist to start building the catalog."
              : "Add artists to your label to start building the catalog."
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {artists.map((artist) => (
            <article
              key={artist.id}
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
            >
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-semibold">{artist.name}</h2>
                {canManage ? (
                  <button
                    type="button"
                    onClick={() => startEdit(artist)}
                    className="text-xs font-medium text-[var(--color-primary-text)] hover:underline shrink-0"
                  >
                    Edit
                  </button>
                ) : null}
              </div>
              <p className="mt-1 text-xs text-[var(--color-muted)] font-mono">{artist.slug}</p>
              {artist.user ? (
                <p className="mt-3 text-xs text-[var(--color-accent-text)] font-medium">
                  Portal: {artist.username || "linked"}
                </p>
              ) : (
                <div className="mt-3 flex items-center justify-between gap-2">
                  <p className="text-xs text-[var(--color-muted)]">No portal login</p>
                  {canManage ? (
                    <button
                      type="button"
                      onClick={() => startInvite(artist)}
                      className="text-xs font-medium text-[var(--color-primary-text)] hover:underline"
                    >
                      Invite
                    </button>
                  ) : null}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </>
  );
}
