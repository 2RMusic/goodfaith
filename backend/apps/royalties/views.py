from django.db.models import QuerySet
from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.catalog.views import _user_label_ids

from apps.audit.models import AuditAction
from apps.audit.services import log_audit_event

from .models import RoyaltyRun, RoyaltyRunPayout, RoyaltyStatement, StatementStatus
from .consolidation import ConsolidationError, consolidate_run
from .permissions import CanAccessRoyalties
from apps.accounts.permissions import Mandatory2FAEnforced
from .pdf_export import royalty_run_pdf, royalty_run_pdf_filename
from .serializers import (
    ArtistEarningsSerializer,
    RoyaltyLineItemSerializer,
    RoyaltyRunCreateSerializer,
    RoyaltyRunPayoutSerializer,
    RoyaltyRunSerializer,
    RoyaltyStatementSerializer,
    RoyaltyStatementUploadSerializer,
)
from .tasks import process_statement


def _log_run_consolidated(run: RoyaltyRun, *, actor) -> None:
    log_audit_event(
        label_id=run.label_id,
        action=AuditAction.RUN_CONSOLIDATED,
        resource_type="royalty_run",
        resource_id=run.pk,
        summary=f"Consolidated run “{run.name}” — {run.total_amount} {run.currency}",
        actor=actor,
        metadata={
            "total_amount": str(run.total_amount),
            "currency": run.currency,
            "payout_count": run.payouts.count(),
            "status": run.status,
        },
    )


class RoyaltyStatementViewSet(viewsets.ModelViewSet):
    permission_classes = [CanAccessRoyalties, Mandatory2FAEnforced]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self) -> QuerySet[RoyaltyStatement]:
        return RoyaltyStatement.objects.filter(
            label_id__in=_user_label_ids(self.request.user)
        ).select_related("uploaded_by", "label")

    def get_serializer_class(self):
        if self.action == "create":
            return RoyaltyStatementUploadSerializer
        return RoyaltyStatementSerializer

    def perform_create(self, serializer):
        uploaded = self.request.FILES.get("file")
        filename = uploaded.name if uploaded else "statement"
        statement = serializer.save(
            uploaded_by=self.request.user,
            filename=filename,
            status=StatementStatus.PENDING,
        )
        log_audit_event(
            label_id=statement.label_id,
            action=AuditAction.STATEMENT_UPLOADED,
            resource_type="royalty_statement",
            resource_id=statement.pk,
            summary=f"Uploaded {statement.get_distributor_display()} statement {filename}",
            actor=self.request.user,
            metadata={
                "distributor": statement.distributor,
                "filename": filename,
            },
        )
        process_statement.delay(statement.pk)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output = RoyaltyStatementSerializer(serializer.instance)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=201, headers=headers)

    @action(detail=True, methods=["get"])
    def line_items(self, request, pk=None):
        statement = self.get_object()

        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1

        try:
            page_size = int(request.query_params.get("page_size", 50))
        except (TypeError, ValueError):
            page_size = 50

        allowed_page_sizes = (50, 100, 250, 500)
        if page_size not in allowed_page_sizes:
            page_size = 50

        items = statement.line_items.all().order_by("id")
        total = items.count()

        total_pages = max(1, (total + page_size - 1) // page_size)

        if page > total_pages:
            page = total_pages

        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        return Response(
            {
                "results": RoyaltyLineItemSerializer(
                    page_items,
                    many=True,
                ).data,
                "count": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }
        )

    @action(detail=True, methods=["post"])
    def reprocess(self, request, pk=None):
        statement = self.get_object()
        statement.status = StatementStatus.PENDING
        statement.save(update_fields=["status", "updated_at"])

        log_audit_event(
            label_id=statement.label_id,
            action=AuditAction.STATEMENT_REPROCESSED,
            resource_type="royalty_statement",
            resource_id=statement.pk,
            summary=f"Reprocess requested for {statement.filename}",
            actor=request.user,
        )

        process_statement.delay(statement.pk)
        return Response(RoyaltyStatementSerializer(statement).data)


class RoyaltyRunViewSet(viewsets.ModelViewSet):
    permission_classes = [CanAccessRoyalties, Mandatory2FAEnforced]

    def get_queryset(self) -> QuerySet[RoyaltyRun]:
        return RoyaltyRun.objects.filter(
            label_id__in=_user_label_ids(self.request.user)
        ).prefetch_related("statements", "payouts").select_related("payout_batch")

    def get_serializer_class(self):
        if self.action == "create":
            return RoyaltyRunCreateSerializer
        return RoyaltyRunSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = serializer.save()

        try:
            consolidate_run(run)
        except ConsolidationError as exc:
            run.delete()
            raise serializers.ValidationError({"detail": str(exc)}) from exc

        log_audit_event(
            label_id=run.label_id,
            action=AuditAction.RUN_CREATED,
            resource_type="royalty_run",
            resource_id=run.pk,
            summary=f"Created royalty run “{run.name}”",
            actor=request.user,
            metadata={
                "statement_ids": list(
                    run.statements.values_list("id", flat=True)
                )
            },
        )

        _log_run_consolidated(run, actor=request.user)

        output = RoyaltyRunSerializer(run)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=201, headers=headers)

    @action(detail=True, methods=["get"])
    def payouts(self, request, pk=None):
        run = self.get_object()
        payouts = run.payouts.select_related("track", "artist")
        return Response(
            RoyaltyRunPayoutSerializer(payouts, many=True).data
        )

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        run = self.get_object()
        content = royalty_run_pdf(run)

        response = HttpResponse(
            content,
            content_type="application/pdf",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{royalty_run_pdf_filename(run)}"'
        )
        return response

    @action(detail=True, methods=["post"])
    def consolidate(self, request, pk=None):
        run = self.get_object()

        try:
            consolidate_run(run)
        except ConsolidationError as exc:
            run.consolidation_error = str(exc)
            run.save(
                update_fields=[
                    "consolidation_error",
                    "updated_at",
                ]
            )

            log_audit_event(
                label_id=run.label_id,
                action=AuditAction.RUN_CONSOLIDATION_FAILED,
                resource_type="royalty_run",
                resource_id=run.pk,
                summary=f"Consolidation failed for “{run.name}”",
                actor=request.user,
                metadata={"error": str(exc)},
            )

            return Response(
                {"detail": str(exc)},
                status=400,
            )

        run.consolidation_error = ""
        run.save(
            update_fields=[
                "consolidation_error",
                "updated_at",
            ]
        )

        _log_run_consolidated(run, actor=request.user)

        return Response(
            RoyaltyRunSerializer(run).data
        )


class MyEarningsView(ListAPIView):
    """Artist-scoped royalty run payout lines — earnings breakdown without label-wide data."""

    serializer_class = ArtistEarningsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[RoyaltyRunPayout]:
        user = self.request.user

        if user.role != Role.ARTIST or not hasattr(
            user,
            "artist_profile",
        ):
            return RoyaltyRunPayout.objects.none()

        label_ids = _user_label_ids(user)

        return (
            RoyaltyRunPayout.objects.filter(
                artist=user.artist_profile,
                run__label_id__in=label_ids,
            )
            .select_related("run", "track")
            .order_by(
                "-run__created_at",
                "-amount",
            )
        )