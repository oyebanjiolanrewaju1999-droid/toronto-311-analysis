"""Load Toronto 311 CSVs into SQLite.

Standard library only (csv, sqlite3) so the whole project reproduces with
`python build_db.py` and nothing to install.

Source: City of Toronto Open Data, "311 Service Requests - Customer Initiated"
https://open.toronto.ca/dataset/311-service-requests-customer-initiated/
Licence: Open Government Licence - Toronto
"""

import csv
import io
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED = ROOT / "data" / "extracted"
DB = ROOT / "toronto311.db"

INSERT_COLUMNS = [
    "creation_date",
    "year",
    "month",
    "hour",
    "status",
    "postal_prefix",
    "street_1",
    "street_2",
    "ward",
    "ward_code",
    "request_type",
    "division",
    "section",
]

SCHEMA = """
DROP TABLE IF EXISTS requests;
CREATE TABLE requests (
    id            INTEGER PRIMARY KEY,
    creation_date TEXT NOT NULL,
    year          INTEGER NOT NULL,
    month         TEXT NOT NULL,
    hour          INTEGER,
    status        TEXT,
    postal_prefix TEXT,
    street_1      TEXT,
    street_2      TEXT,
    ward          TEXT,
    ward_code     TEXT,
    request_type  TEXT,
    division      TEXT,
    section       TEXT
);
"""

SOURCE_COLUMNS = {
    "Creation Date",
    "Status",
    "First 3 Chars of Postal Code",
    "Intersection Street 1",
    "Intersection Street 2",
    "Ward",
    "Service Request Type",
    "Division",
    "Section",
}

WARD_RE = re.compile(r"^(.*?)\s*\((\d{2})\)\s*$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})")

INSERT_SQL = (
    f"INSERT INTO requests ({','.join(INSERT_COLUMNS)}) "
    f"VALUES ({','.join('?' * len(INSERT_COLUMNS))})"
)


def read_text(path):
    """Some yearly files are cp1252 despite the .csv extension."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252"


def clean(value):
    if value is None:
        return None
    text = value.strip().strip("\ufeff")
    if not text or text.upper() in {"NULL", "N/A", "NA", "UNKNOWN"}:
        return None
    return text


def split_ward(raw):
    """'Etobicoke-Lakeshore (03)' -> ('Etobicoke-Lakeshore', '03')"""
    if not raw:
        return None, None
    match = WARD_RE.match(raw)
    if match:
        return clean(match.group(1)), match.group(2)
    return raw, None


def parse_date(raw):
    """Return (iso_timestamp, year, month, hour) or None."""
    match = DATE_RE.match(raw or "")
    if not match:
        return None
    year, month, day, hour = match.group(1), match.group(2), match.group(3), int(match.group(4))
    return f"{year}-{month}-{day}T{hour:02d}:00:00", int(year), f"{year}-{month}", hour


def row_values(row):
    """Map one source row to the insert tuple, or None if the date is unusable."""
    parsed = parse_date(clean(row.get("Creation Date")))
    if parsed is None:
        return None
    iso, year, month, hour = parsed
    ward_name, ward_code = split_ward(clean(row.get("Ward")))
    postal = clean(row.get("First 3 Chars of Postal Code"))
    return (
        iso,
        year,
        month,
        hour,
        clean(row.get("Status")),
        postal.upper() if postal else None,
        clean(row.get("Intersection Street 1")),
        clean(row.get("Intersection Street 2")),
        ward_name,
        ward_code,
        clean(row.get("Service Request Type")),
        clean(row.get("Division")),
        clean(row.get("Section")),
    )


def load_file(conn, path, counters):
    text, encoding = read_text(path)
    reader = csv.DictReader(io.StringIO(text))

    missing = SOURCE_COLUMNS - {k.strip() for k in (reader.fieldnames or [])}
    if missing:
        sys.exit(f"{path.name} is missing columns: {sorted(missing)}")

    batch = []
    for row in reader:
        counters["read"] += 1
        values = row_values(row)
        if values is None:
            counters["bad_date"] += 1
            continue
        batch.append(values)
        if len(batch) >= 50000:
            conn.executemany(INSERT_SQL, batch)
            batch.clear()
    if batch:
        conn.executemany(INSERT_SQL, batch)

    conn.commit()
    loaded = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    print(f"loaded {path.parent.name} [{encoding}]: {loaded:,} rows so far")


def main():
    files = sorted(EXTRACTED.glob("*/SR*.csv"))
    if not files:
        sys.exit(f"No CSVs found under {EXTRACTED}")

    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA journal_mode = WAL")

    counters = {"read": 0, "bad_date": 0}
    for path in files:
        load_file(conn, path, counters)

    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_year ON requests(year);
        CREATE INDEX IF NOT EXISTS idx_type ON requests(request_type);
        CREATE INDEX IF NOT EXISTS idx_ward ON requests(ward_code);
        CREATE INDEX IF NOT EXISTS idx_month ON requests(month);
        """
    )
    conn.commit()

    rows = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    print(f"\nrows read:       {counters['read']:,}")
    print(f"rows loaded:     {rows:,}")
    print(f"skipped (dates): {counters['bad_date']:,}")
    print(f"database:        {DB}")
    conn.close()


if __name__ == "__main__":
    main()
