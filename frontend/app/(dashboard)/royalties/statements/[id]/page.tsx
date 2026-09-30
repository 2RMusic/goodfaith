"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import { canAccessRoyalties, useAuth } from "@/lib/auth";
import { formatDate, formatMoney } from "@/lib/format";
import type { RoyaltyLineItem, RoyaltyStatement } from "@/lib/types";

type PaginatedLineItems = {
  results: RoyaltyLineItem[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export default function StatementDetailPage() {
  const params = useParams<{ id: string }>();
  const { token, user } = useAuth();

  const [statement, setStatement] = useState<RoyaltyStatement | null>(null);
  const [lineItems, setLineItems] = useState<RoyaltyLineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const hasAccess = user && canAccessRoyalties(user.role);

  const load = useCallback(async () => {
    if (!token || !params.id || !hasAccess) return;

    setLoading(true);
    setError(null);

    try {
      const statementData = await apiFetch<RoyaltyStatement>(
        `/api/royalties/statements/${params.id}/`,
        {},
        token,
      );

      setStatement(statementData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load statement.");
    } finally {
      setLoading(false);
    }
  }, [token, params.id, hasAccess]);

  const loadLineItems = useCallback(async () => {
    if (!token || !params.id || !hasAccess) return;

    setItemsLoading(true);

    try {
      const data = await apiFetch<PaginatedLineItems>(
        `/api/royalties/statements/${params.id}/line_items/?page=${page}&page_size=${pageSize}`,
        {},
        token,
      );

      setLineItems(data.results);
      setTotalItems(data.count);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load line items.");
    } finally {
      setItemsLoading(false);
    }
  }, [token, params.id, hasAccess, page, pageSize]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    loadLineItems();
  }, [loadLineItems]);

  async function handleReprocess() {
    if (!token || !params.id) return;

    setReprocessing(true);

    try {
      const updated = await apiFetch<RoyaltyStatement>(
        `/api/royalties/statements/${params.id}/reprocess/`,
        { method: "POST" },
        token,
      );

      setStatement(updated);
      setLineItems([]);
      setTotalItems(0);
      setPage(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reprocess failed.");
    } finally {
      setReprocessing(false);
    }
  }

  function handlePageSizeChange(value: number) {
    setPageSize(value);
    setPage(1);
  }

  const startItem =
    totalItems === 0 ? 0 : (page - 1) * pageSize + 1;

  const endItem =
    totalItems === 0 ? 0 : Math.min(page * pageSize, totalItems);

  const visiblePages = Array.from(
    { length: Math.min(5, totalPages) },
    (_, index) => {
      let start = Math.max(1, page - 2);

      if (start + 4 > totalPages) {
        start = Math.max(1, totalPages - 4);
      }

      return start + index;
    },
  );

  if (!hasAccess) {
    return (
      <p className="text-sm text-[var(--color-muted)]">
        You do not have access to royalty statements.
      </p>
    );
  }

  if (loading) {
    return (
      <p className="text-sm text-[var(--color-muted)]">
        Loading statement...
      </p>
    );
  }

  if (error || !statement) {
    return (
      <div>
        <p
          className="text-sm text-red-600 dark:text-red-400"
          role="alert"
        >
          {error ?? "Statement not found."}
        </p>

        <Link
          href="/royalties"
          className="inline-block mt-4 text-sm text-[var(--color-primary-text)]"
        >
          ← Back to royalties
        </Link>
      </div>
    );
  }

  return (
    <>
      <Link
        href="/royalties"
        className="text-sm text-[var(--color-muted)] hover:text-[var(--color-ink)]"
      >
        ← Royalties
      </Link>

      <PageHeader
        title={statement.filename}
        description={`${statement.distributor_display} · ${formatDate(
          statement.period_start,
        )} – ${formatDate(statement.period_end)}`}
        action={
          statement.status === "failed" ? (
            <button
              type="button"
              onClick={handleReprocess}
              disabled={reprocessing}
              className="rounded-md border border-[var(--color-border)] px-3 py-2 text-sm font-medium hover:bg-[var(--color-surface-2)] disabled:opacity-60"
            >
              {reprocessing ? "Reprocessing..." : "Reprocess"}
            </button>
          ) : null
        }
      />

      <dl className="grid gap-4 sm:grid-cols-4 mb-8 text-sm">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <dt className="text-[var(--color-muted)]">Status</dt>
          <dd className="mt-1">
            <StatusBadge
              label={statement.status_display}
              status={statement.status}
            />
          </dd>
        </div>

        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <dt className="text-[var(--color-muted)]">Rows parsed</dt>
          <dd className="mt-1 font-semibold tabular-nums">
            {statement.row_count ?? "—"}
          </dd>
        </div>

        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <dt className="text-[var(--color-muted)]">Total</dt>
          <dd className="mt-1 font-semibold tabular-nums">
            {formatMoney(statement.total_amount, statement.currency)}
          </dd>
        </div>

        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <dt className="text-[var(--color-muted)]">Uploaded by</dt>
          <dd className="mt-1">{statement.uploaded_by_username}</dd>
        </div>
      </dl>

      {statement.error_message ? (
        <p className="mb-6 rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-sm text-red-700 dark:text-red-300">
          {statement.error_message}
        </p>
      ) : null}

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Parsed line items</h2>

          {totalItems > 0 ? (
            <p className="mt-1 text-sm text-[var(--color-muted)]">
              Showing {startItem.toLocaleString()}–{endItem.toLocaleString()} of{" "}
              {totalItems.toLocaleString()}
            </p>
          ) : null}
        </div>

        <label className="flex items-center gap-2 text-sm">
          <span className="text-[var(--color-muted)]">Show</span>

          <select
            value={pageSize}
            onChange={(event) =>
              handlePageSizeChange(Number(event.target.value))
            }
            className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2"
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={250}>250</option>
            <option value={500}>500</option>
          </select>

          <span className="text-[var(--color-muted)]">rows</span>
        </label>
      </div>

      {itemsLoading ? (
        <p className="text-sm text-[var(--color-muted)]">
          Loading line items...
        </p>
      ) : lineItems.length === 0 ? (
        <p className="text-sm text-[var(--color-muted)]">
          {statement.status === "pending" ||
          statement.status === "processing"
            ? "Parser is still running — refresh in a moment."
            : "No line items were extracted from this statement."}
        </p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-[var(--color-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-surface)] text-left text-[var(--color-muted)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Track</th>
                  <th className="px-4 py-3 font-medium">ISRC</th>
                  <th className="px-4 py-3 font-medium">Store</th>
                  <th className="px-4 py-3 font-medium">Period</th>
                  <th className="px-4 py-3 font-medium text-right">Qty</th>
                  <th className="px-4 py-3 font-medium text-right">Amount</th>
                </tr>
              </thead>

              <tbody>
                {lineItems.map((item) => (
                  <tr
                    key={item.id}
                    className="border-t border-[var(--color-border)]"
                  >
                    <td className="px-4 py-3">
                      <span className="font-medium">
                        {item.track_title || "—"}
                      </span>

                      {item.artist_name ? (
                        <span className="block text-xs text-[var(--color-muted)]">
                          {item.artist_name}
                        </span>
                      ) : null}
                    </td>

                    <td className="px-4 py-3 font-mono text-xs">
                      {item.isrc || "—"}
                    </td>

                    <td className="px-4 py-3">
                      {item.store || "—"}
                    </td>

                    <td className="px-4 py-3">
                      {formatDate(item.sale_period)}
                    </td>

                    <td className="px-4 py-3 text-right tabular-nums">
                      {item.quantity}
                    </td>

                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatMoney(item.amount, statement.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 ? (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                disabled={page <= 1 || itemsLoading}
                onClick={() => setPage((current) => current - 1)}
                className="rounded-md border border-[var(--color-border)] px-3 py-2 text-sm disabled:opacity-40"
              >
                ← Previous
              </button>

              <div className="flex flex-wrap items-center justify-center gap-1">
                {visiblePages.map((pageNumber) => (
                  <button
                    key={pageNumber}
                    type="button"
                    onClick={() => setPage(pageNumber)}
                    className={`min-w-9 rounded-md border px-3 py-2 text-sm ${
                      pageNumber === page
                        ? "border-[var(--color-ink)] bg-[var(--color-ink)] text-[var(--color-surface)]"
                        : "border-[var(--color-border)]"
                    }`}
                  >
                    {pageNumber}
                  </button>
                ))}

                {totalPages > 5 && page < totalPages - 2 ? (
                  <>
                    <span className="px-1 text-[var(--color-muted)]">…</span>

                    <button
                      type="button"
                      onClick={() => setPage(totalPages)}
                      className="min-w-9 rounded-md border border-[var(--color-border)] px-3 py-2 text-sm"
                    >
                      {totalPages}
                    </button>
                  </>
                ) : null}
              </div>

              <button
                type="button"
                disabled={page >= totalPages || itemsLoading}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-md border border-[var(--color-border)] px-3 py-2 text-sm disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          ) : null}
        </>
      )}
    </>
  );
}