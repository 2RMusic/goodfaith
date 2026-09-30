from decimal import Decimal, ROUND_HALF_UP

from celery import shared_task
from django.db import transaction

from apps.catalog.models import AssetKind, Track, TrackIdentifier

from apps.audit.models import AuditAction
from apps.audit.services import log_audit_event
from apps.notifications.services import notify_statement_failed, notify_statement_processed

from .models import RoyaltyLineItem, RoyaltyRun, RoyaltyRunStatus, RoyaltyStatement, StatementStatus
from .parsers.aliases import aliases_for
from .parsers.base import StatementParseError, load_dataframe, normalize_rows


@shared_task
def process_statement(statement_id: int) -> None:
    try:
        statement = RoyaltyStatement.objects.get(pk=statement_id)
    except RoyaltyStatement.DoesNotExist:
        return

    statement.status = StatementStatus.PROCESSING
    statement.error_message = ""
    statement.save(update_fields=["status", "error_message", "updated_at"])

    try:
        with statement.file.open("rb") as fileobj:
            df = load_dataframe(fileobj, statement.filename)
        rows, skipped = normalize_rows(df, aliases_for(statement.distributor))
    except StatementParseError as exc:
        statement.status = StatementStatus.FAILED
        statement.error_message = str(exc)
        statement.save(update_fields=["status", "error_message", "updated_at"])
        log_audit_event(
            label_id=statement.label_id,
            action=AuditAction.STATEMENT_FAILED,
            resource_type="royalty_statement",
            resource_id=statement.pk,
            summary=f"Parse failed for {statement.filename}",
            metadata={"error": str(exc)},
        )
        notify_statement_failed(statement)
        return
    except Exception as exc:  # noqa: BLE001 — surface any parse failure on the statement
        statement.status = StatementStatus.FAILED
        statement.error_message = f"Unexpected error while parsing: {exc}"
        statement.save(update_fields=["status", "error_message", "updated_at"])
        log_audit_event(
            label_id=statement.label_id,
            action=AuditAction.STATEMENT_FAILED,
            resource_type="royalty_statement",
            resource_id=statement.pk,
            summary=f"Parse failed for {statement.filename}",
            metadata={"error": str(exc)},
        )
        notify_statement_failed(statement)
        return

    isrcs = {row.isrc for row in rows if row.isrc}
    track_by_isrc = {
        track.isrc: track
        for track in Track.objects.filter(
            isrc__in=isrcs, release__label_id=statement.label_id
        )
    }
    kind_by_isrc = {isrc: AssetKind.AUDIO for isrc in track_by_isrc}
    # Additional identifiers never override a principal ISRC. Check both label
    # paths so a stale identifier cannot cross tenants after a catalog move.
    identifiers = TrackIdentifier.objects.filter(
        label_id=statement.label_id,
        track__release__label_id=statement.label_id,
        identifier_type=TrackIdentifier.IdentifierType.ISRC,
        value__in=isrcs - track_by_isrc.keys(),
    ).select_related("track")
    for identifier in identifiers:
        track_by_isrc[identifier.value] = identifier.track
        kind_by_isrc[identifier.value] = identifier.asset_kind

    line_items = [
        RoyaltyLineItem(
            statement=statement,
            track=track_by_isrc.get(row.isrc),
            sale_period=row.sale_period,
            store=row.store,
            country=row.country,
            artist_name=row.artist_name,
            track_title=row.track_title,
            isrc=row.isrc,
            source_asset_kind=kind_by_isrc.get(row.isrc) or AssetKind.UNKNOWN,
            upc=row.upc,
            quantity=row.quantity,
            amount=row.amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            raw_data=row.raw,
        )
        for row in rows
    ]

    with transaction.atomic():
        RoyaltyLineItem.objects.filter(statement=statement).delete()
        RoyaltyLineItem.objects.bulk_create(line_items, batch_size=1000)
        # Sum persisted Decimals, avoiding SQLite's floating-point SUM.
        total_amount = sum(
            statement.line_items.order_by().values_list("amount", flat=True).iterator(),
            Decimal("0.0000"),
        )
        statement.row_count = len(line_items)
        statement.total_amount = total_amount
        statement.status = StatementStatus.PROCESSED
        if skipped:
            statement.error_message = f"Skipped {skipped} row(s) with no readable amount."
        statement.save(
            update_fields=["row_count", "total_amount", "status", "error_message", "updated_at"]
        )
        log_audit_event(
            label_id=statement.label_id,
            action=AuditAction.STATEMENT_PROCESSED,
            resource_type="royalty_statement",
            resource_id=statement.pk,
            summary=f"Processed {statement.filename} — {total_amount} {statement.currency}",
            metadata={
                "row_count": len(line_items),
                "total_amount": str(total_amount),
                "currency": statement.currency,
                "skipped_rows": skipped,
            },
        )
    notify_statement_processed(statement)


@shared_task
def consolidate_run_task(run_id: int) -> None:
    from .consolidation import ConsolidationError, consolidate_run

    try:
        run = RoyaltyRun.objects.prefetch_related("statements").get(pk=run_id)
    except RoyaltyRun.DoesNotExist:
        return

    try:
        consolidate_run(run)
    except ConsolidationError as exc:
        run.consolidation_error = str(exc)
        run.status = RoyaltyRunStatus.DRAFT
        run.save(update_fields=["consolidation_error", "status", "updated_at"])
