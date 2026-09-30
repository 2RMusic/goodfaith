"""
Per-distributor column-header aliases used to map a raw statement's columns
onto the normalized schema in `apps.royalties.parsers.base.CANONICAL_FIELDS`.

Header names below are based on each distributor's publicly documented / commonly
reported export columns as of this writing. Distributors change their export
formats without notice — when a real statement fails to map (see
`StatementParseError`), extend the relevant alias list here rather than
special-casing the parser logic.
"""

from apps.royalties.models import Distributor

# canonical field -> ordered list of header names to try (case-insensitive, whitespace-trimmed)
GENERIC_ALIASES: dict[str, list[str]] = {
    "sale_period": ["Sale Period", "Sale Month", "Period", "Reporting Period", "Reporting Date", "Month", "Sales Date"],
    "store": ["Store", "DSP", "Platform", "Service", "Outlet", "Sales Store"],
    "country": ["Country", "Country Of Sale", "Country of Sale", "Territory"],
    "artist_name": ["Artist", "Artist Name"],
    "track_title": ["Track Title", "Title", "Song Title", "Track Name"],
    "isrc": ["ISRC"],
    "upc": ["UPC", "UPC/EAN", "Album UPC"],
    "quantity": ["Quantity", "Units", "Units Sold", "Qty Sold", "Streams"],
    "amount": [
        "USD Revenue",
        "Earnings (USD)",
        "Earnings",
        "Net Earnings",
        "Net Revenue",
        "Total Earnings",
        "Total Earnings ($)",
        "Total",
        "Revenue",
        "Royalty",
        "Net Payable",
        "Payable Amount",
    ],
    "currency": ["Currency"],
}

DISTRIBUTOR_ALIASES: dict[str, dict[str, list[str]]] = {
    Distributor.DISTROKID: {
        "sale_period": ["Sale Month", "Reporting Date", "Period"],
        "store": ["Store", "Service"],
        "country": ["Country of Sale", "Country"],
        "artist_name": ["Artist", "Artist Name"],
        "track_title": ["Title", "Track Title", "Song Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC", "UPC/EAN"],
        "quantity": ["Quantity", "Units", "Streams"],
        "amount": ["Earnings (USD)", "Earnings", "Total Earned"],
        "currency": ["Currency"],
    },
    Distributor.TUNECORE: {
        "sale_period": ["Sale Period", "Period", "Sales Date"],
        "store": ["Store", "Sales Store"],
        "country": ["Country Of Sale", "Country"],
        "artist_name": ["Artist", "Artist Name"],
        "track_title": ["Song Title", "Title", "Track Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC/EAN", "UPC"],
        "quantity": ["Quantity", "Units Sold", "Units"],
        "amount": ["Total", "Earnings", "Net Payable", "Total Earnings"],
        "currency": ["Currency"],
    },
    Distributor.CD_BABY: {
        "sale_period": ["Sale Month", "Sales Month", "Period"],
        "store": ["Store", "Retailer"],
        "country": ["Country", "Territory"],
        "artist_name": ["Artist Name", "Artist"],
        "track_title": ["Track Title", "Title", "Song Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC", "Album UPC"],
        "quantity": ["Quantity", "Units", "Qty Sold"],
        "amount": ["Earnings", "Net Earnings", "Total Earnings ($)"],
        "currency": ["Currency"],
    },
    Distributor.SYMPHONIC: {
        "sale_period": ["Period", "Sale Period", "Month"],
        "store": ["DSP", "Store", "Platform"],
        "country": ["Territory", "Country"],
        "artist_name": ["Artist", "Artist Name"],
        "track_title": ["Title", "Track Name"],
        "isrc": ["ISRC"],
        "upc": ["UPC"],
        "quantity": ["Units", "Quantity", "Streams"],
        "amount": ["Net Revenue", "Revenue", "Earnings"],
        "currency": ["Currency"],
    },
    Distributor.ONERPM: {
        "sale_period": ["Sale Period", "Period", "Reporting Period"],
        "store": ["Store", "Platform"],
        "country": ["Country", "Territory"],
        "artist_name": ["Artist", "Artist Name"],
        "track_title": ["Track", "Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC"],
        "quantity": ["Quantity", "Units"],
        "amount": ["Royalty", "Earnings", "Net Payable"],
        "currency": ["Currency"],
    },
    Distributor.ROUTENOTE: {
        "sale_period": ["Sale Period", "Period", "Month"],
        "store": ["Store", "Outlet"],
        "country": ["Country", "Territory"],
        "artist_name": ["Artist", "Artist Name"],
        "track_title": ["Track Title", "Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC"],
        "quantity": ["Quantity", "Units"],
        "amount": ["Net Earnings", "Earnings", "Payable Amount"],
        "currency": ["Currency"],
    },
    # TooLost — indie distributor; column names from common label export samples.
    Distributor.TOOLOST: {
        "sale_period": ["Reporting Period", "Period", "Sale Month", "Month"],
        "store": ["Store", "Platform", "DSP"],
        "country": ["Country", "Territory"],
        "artist_name": ["Artist Name", "Artist"],
        "track_title": ["Track Title", "Title", "Song"],
        "isrc": ["ISRC", "ISRC Code"],
        "upc": ["UPC", "Album UPC"],
        "quantity": ["Quantity", "Units", "Streams"],
        "amount": ["Net Revenue", "Revenue", "Earnings", "Amount"],
        "currency": ["Currency"],
    },
    # FUGA — B2B aggregator; aligns with FUGA royalty report exports.
    Distributor.FUGA: {
        "sale_period": ["Reporting Month", "Sale Period", "Period", "Month"],
        "store": ["Digital Service Provider", "DSP", "Store", "Platform"],
        "country": ["Territory", "Country"],
        "artist_name": ["Track Artist", "Artist", "Artist Name"],
        "track_title": ["Track Title", "Title", "Track Name"],
        "isrc": ["ISRC", "ISRC Code"],
        "upc": ["UPC", "UPC Code", "Album UPC"],
        "quantity": ["Units", "Quantity", "Streams"],
        "amount": ["Net Amount", "Net Revenue", "Revenue", "Payable"],
        "currency": ["Currency"],
    },
    # The Orchard — Sony enterprise aggregator export headers.
    Distributor.THE_ORCHARD: {
        "sale_period": ["Period", "Sale Period", "Reporting Period", "Month"],
        "store": ["Store", "Digital Store", "DSP", "Retailer"],
        "country": ["Territory", "Country", "Country of Sale"],
        "artist_name": ["Artist", "Track Artist", "Artist Name"],
        "track_title": ["Track Title", "Title", "Song Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC", "Product UPC"],
        "quantity": ["Units", "Quantity", "Stream Count"],
        "amount": ["Label Share Net Receipts", "Net Receipts", "Amount", "Royalty Amount"],
        "currency": ["Currency", "Currency Code"],
    },
    # Vydia — video/multi-platform; amount columns vary by export type.
    Distributor.VYDIA: {
        "sale_period": ["Period", "Reporting Period", "Month"],
        "store": ["Platform", "Store", "Service"],
        "country": ["Country", "Territory"],
        "artist_name": ["Artist", "Artist Name", "Channel"],
        "track_title": ["Title", "Video Title", "Track Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC"],
        "quantity": ["Views", "Quantity", "Units"],
        "amount": ["Net Earnings", "Earnings", "Revenue", "Amount"],
        "currency": ["Currency"],
    },
    # Colonize Media — royalty statement export.
    Distributor.COLONIZE: {
        "sale_period": ["Sales Date", "Received On"],
        "store": ["Store"],
        "country": ["Region"],
        "artist_name": ["Track Artist", "Artist Name"],
        "track_title": ["Track Title"],
        "isrc": ["ISRC"],
        "upc": ["UPC"],
        "quantity": ["Units"],
        "amount": ["USD Revenue"],
        "currency": ["Currency"],
    },
}


def aliases_for(distributor: str) -> dict[str, list[str]]:
    """Distributor-specific aliases, with generic aliases appended as a fallback
    for any canonical field the distributor map doesn't cover."""
    specific = DISTRIBUTOR_ALIASES.get(distributor, {})
    merged: dict[str, list[str]] = {}
    for field, generic_names in GENERIC_ALIASES.items():
        names = list(specific.get(field, []))
        for name in generic_names:
            if name not in names:
                names.append(name)
        merged[field] = names
    return merged
