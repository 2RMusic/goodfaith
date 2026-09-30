from rest_framework import serializers

from apps.catalog.models import Label

from .models import RoyaltyLineItem, RoyaltyRun, RoyaltyRunPayout, RoyaltyStatement, StatementStatus


class RoyaltyStatementSerializer(serializers.ModelSerializer):
    distributor_display = serializers.CharField(source="get_distributor_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = RoyaltyStatement
        fields = (
            "id",
            "label",
            "distributor",
            "distributor_display",
            "filename",
            "period_start",
            "period_end",
            "status",
            "status_display",
            "row_count",
            "total_amount",
            "currency",
            "uploaded_by",
            "uploaded_by_username",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "filename",
            "status",
            "row_count",
            "total_amount",
            "uploaded_by",
            "error_message",
            "created_at",
            "updated_at",
        )


class RoyaltyStatementUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoyaltyStatement
        fields = ("label", "distributor", "file", "period_start", "period_end", "currency")


class RoyaltyLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoyaltyLineItem
        fields = (
            "id",
            "statement",
            "track",
            "sale_period",
            "store",
            "country",
            "artist_name",
            "track_title",
            "isrc",
            "source_asset_kind",
            "upc",
            "quantity",
            "amount",
        )
        read_only_fields = fields


class RoyaltyRunPayoutSerializer(serializers.ModelSerializer):
    role_display = serializers.SerializerMethodField()

    class Meta:
        model = RoyaltyRunPayout
        fields = (
            "id",
            "run",
            "track",
            "isrc",
            "track_title",
            "participant_name",
            "artist",
            "role",
            "role_display",
            "share_percentage",
            "track_gross",
            "amount",
            "unallocated_reason",
        )
        read_only_fields = fields

    def get_role_display(self, obj: RoyaltyRunPayout) -> str:
        if not obj.role:
            return ""
        try:
            from apps.splits.models import SplitRole

            return SplitRole(obj.role).label
        except ValueError:
            return obj.role.replace("_", " ").title()


class ArtistEarningsSerializer(serializers.ModelSerializer):
    run_name = serializers.CharField(source="run.name", read_only=True)
    run_status = serializers.CharField(source="run.status", read_only=True)
    currency = serializers.CharField(source="run.currency", read_only=True)
    run_created_at = serializers.DateTimeField(source="run.created_at", read_only=True)
    role_display = serializers.SerializerMethodField()

    class Meta:
        model = RoyaltyRunPayout
        fields = (
            "id",
            "run",
            "run_name",
            "run_status",
            "run_created_at",
            "currency",
            "track",
            "isrc",
            "track_title",
            "participant_name",
            "role",
            "role_display",
            "share_percentage",
            "track_gross",
            "amount",
        )
        read_only_fields = fields

    def get_role_display(self, obj: RoyaltyRunPayout) -> str:
        if not obj.role:
            return ""
        try:
            from apps.splits.models import SplitRole

            return SplitRole(obj.role).label
        except ValueError:
            return obj.role.replace("_", " ").title()


class RoyaltyRunSerializer(serializers.ModelSerializer):
    statement_count = serializers.IntegerField(source="statements.count", read_only=True)
    payout_count = serializers.IntegerField(source="payouts.count", read_only=True)
    payout_batch_id = serializers.SerializerMethodField()

    class Meta:
        model = RoyaltyRun
        fields = (
            "id",
            "label",
            "name",
            "status",
            "statements",
            "statement_count",
            "payout_count",
            "payout_batch_id",
            "total_amount",
            "currency",
            "consolidation_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "total_amount",
            "consolidation_error",
            "created_at",
            "updated_at",
        )

    def get_payout_batch_id(self, obj: RoyaltyRun) -> int | None:
        try:
            return obj.payout_batch.id
        except RoyaltyRun.payout_batch.RelatedObjectDoesNotExist:
            return None


class RoyaltyRunCreateSerializer(serializers.ModelSerializer):
    statements = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=RoyaltyStatement.objects.all(),
    )

    class Meta:
        model = RoyaltyRun
        fields = ("label", "name", "currency", "statements")

    def validate(self, attrs):
        label: Label = attrs["label"]
        statements = attrs["statements"]
        if not statements:
            raise serializers.ValidationError({"statements": "Select at least one processed statement."})

        currency = attrs.get("currency", "USD")
        for statement in statements:
            if statement.label_id != label.id:
                raise serializers.ValidationError(
                    {"statements": f"“{statement.filename}” belongs to a different label."}
                )
            if statement.status != StatementStatus.PROCESSED:
                raise serializers.ValidationError(
                    {"statements": f"“{statement.filename}” is not processed yet."}
                )
            if statement.currency != currency:
                raise serializers.ValidationError(
                    {"statements": f"“{statement.filename}” uses {statement.currency}; run uses {currency}."}
                )
        return attrs

    def create(self, validated_data):
        statements = validated_data.pop("statements")
        run = RoyaltyRun.objects.create(**validated_data)
        run.statements.set(statements)
        return run
