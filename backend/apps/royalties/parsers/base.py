"""
Format-agnostic loading and column normalization for distributor royalty
statements. Distributor-specific knowledge lives entirely in `aliases.py` —
this module only knows how to read a table and map/coerce columns once told
which header names to look for.
"""

import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import IO, Any

import pandas as pd

CANONICAL_FIELDS = (
    "sale_period",
    "store",
    "country",
    "artist_name",
    "track_title",
    "isrc",
    "upc",
    "quantity",
    "amount",
    "currency",
)

# A row is only usable if we found an amount column, plus at least one of
# these identity columns to know what the money is for.
IDENTITY_FIELDS = ("isrc", "track_title")


class StatementParseError(Exception):
    """Raised when a statement's columns can't be mapped onto the normalized schema."""


@dataclass
class ParsedRow:
    sale_period: date | None = None
    store: str = ""
    country: str = ""
    artist_name: str = ""
    track_title: str = ""
    isrc: str = ""
    upc: str = ""
    quantity: int = 0
    amount: Decimal = Decimal("0")
    currency: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


def load_dataframe(fileobj: IO[bytes], filename: str) -> pd.DataFrame:
    """Read a statement file into a DataFrame regardless of CSV/TSV/XLSX format."""
    lower = filename.lower()

    if lower.endswith((".xlsx", ".xls")):
        # Read without assuming where the real header is.
        preview = pd.read_excel(fileobj, header=None, dtype=str)

        # Look through the first rows for a likely royalty-statement header.
        # We require an identity field (ISRC or track title) plus a revenue field.
        header_row = None

        for idx in range(min(20, len(preview))):
            values = {
                str(value).strip().lower()
                for value in preview.iloc[idx].tolist()
                if pd.notna(value)
            }

            has_identity = (
                "isrc" in values
                or "track title" in values
                or "track_title" in values
            )

            has_amount = any(
                value in values
                for value in (
                    "usd revenue",
                    "net revenue",
                    "revenue",
                    "earnings",
                    "amount",
                )
            )

            if has_identity and has_amount:
                header_row = idx
                break

        if header_row is not None:
            df = preview.iloc[header_row + 1:].copy()
            df.columns = preview.iloc[header_row].tolist()
            return df.reset_index(drop=True)

        # Fallback for ordinary Excel files whose header is already on row 1.
        fileobj.seek(0)
        return pd.read_excel(fileobj, dtype=str)

    # The python engine's delimiter sniffer needs text, not bytes.
    raw = fileobj.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    # sep=None + python engine auto-sniffs the delimiter (comma, tab, semicolon, ...)
    return pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str)


def build_column_map(columns: list[str], aliases: dict[str, list[str]]) -> dict[str, str]:
    """Map canonical field -> actual column name, matching case/whitespace-insensitively."""
    lookup = {str(col).strip().lower(): col for col in columns}
    column_map: dict[str, str] = {}
    for canonical_field, names in aliases.items():
        for name in names:
            actual = lookup.get(name.strip().lower())
            if actual is not None:
                column_map[canonical_field] = actual
                break
    return column_map


def _clean_str(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _parse_amount(value: Any) -> Decimal | None:
    text = _clean_str(value).replace(",", "").replace("$", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _parse_quantity(value: Any) -> int:
    text = _clean_str(value).replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _parse_period(value: Any) -> date | None:
    text = _clean_str(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def normalize_rows(df: pd.DataFrame, aliases: dict[str, list[str]]) -> tuple[list[ParsedRow], int]:
    """
    Map a raw DataFrame onto normalized rows using the given alias map.

    Returns (rows, skipped_count). Raises StatementParseError if the header
    can't be mapped at all (no amount column, or no identity column).
    """
    column_map = build_column_map(list(df.columns), aliases)

    if "amount" not in column_map:
        raise StatementParseError(
            "Couldn't find a revenue/earnings column in this statement. "
            f"Columns present: {', '.join(str(c) for c in df.columns)}"
        )
    if not any(f in column_map for f in IDENTITY_FIELDS):
        raise StatementParseError(
            "Couldn't find an ISRC or track title column in this statement. "
            f"Columns present: {', '.join(str(c) for c in df.columns)}"
        )

    rows: list[ParsedRow] = []
    skipped = 0

    for _, series in df.iterrows():
        amount = _parse_amount(series.get(column_map["amount"]))
        if amount is None:
            skipped += 1
            continue

        raw = {str(k): (None if pd.isna(v) else v) for k, v in series.items()}

        rows.append(
            ParsedRow(
                sale_period=_parse_period(series.get(column_map.get("sale_period"))),
                store=_clean_str(series.get(column_map.get("store"))),
                country=_clean_str(series.get(column_map.get("country")))[:2].upper(),
                artist_name=_clean_str(series.get(column_map.get("artist_name"))),
                track_title=_clean_str(series.get(column_map.get("track_title"))),
                isrc=_clean_str(series.get(column_map.get("isrc"))).upper(),
                upc=_clean_str(series.get(column_map.get("upc"))),
                quantity=_parse_quantity(series.get(column_map.get("quantity"))),
                amount=amount,
                currency=_clean_str(series.get(column_map.get("currency"))).upper(),
                raw=raw,
            )
        )

    return rows, skipped
