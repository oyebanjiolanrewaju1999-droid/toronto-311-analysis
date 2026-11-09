"""Run every query in queries.sql and write one CSV per question.

Standard library only. Usage:
    python run_queries.py
"""

import csv
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "toronto311.db"
SQL = ROOT / "queries.sql"
OUT = ROOT / "output"

SECTION = re.compile(r"^-- name:\s*(\S+)", re.MULTILINE)


def split_queries(text):
    parts = []
    matches = list(SECTION.finditer(text))
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        # drop the -- Question line and any comment lines before the SELECT
        lines = [line for line in body.splitlines() if not line.strip().startswith("--")]
        statement = "\n".join(lines).strip().rstrip(";")
        if statement:
            parts.append((match.group(1), statement))
    return parts


def main():
    OUT.mkdir(exist_ok=True)
    queries = split_queries(SQL.read_text(encoding="utf-8"))
    if not queries:
        raise SystemExit("No queries found in queries.sql")

    conn = sqlite3.connect(DB)
    for name, sql in queries:
        cursor = conn.execute(sql)
        headers = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        path = OUT / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f"{name:24s} {len(rows):>4} rows -> {path.name}")
    conn.close()


if __name__ == "__main__":
    main()
