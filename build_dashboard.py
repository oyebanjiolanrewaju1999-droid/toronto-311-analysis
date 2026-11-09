"""Build a self-contained HTML dashboard from output/*.csv.

No dependencies. Hand-rolled SVG so the file opens offline and can be
published as-is.
"""

import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
DEST = ROOT / "dashboard.html"

INK = "#0f172a"
MUTED = "#5b6b82"
LINE = "#e2e8f0"
NAVY = "#1d4ed8"
AMBER = "#b45309"
GREEN = "#15803d"
RED = "#b91c1c"


def read(name):
    with (OUT / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def esc(value):
    return html.escape(str(value))


def bars(rows, label_key, value_key, color=NAVY, width=760, height=None, fmt="{:,.0f}"):
    """Horizontal bars."""
    values = [float(r[value_key]) for r in rows]
    top = max(values) or 1
    row_h = 30
    height = height or len(rows) * row_h + 10
    label_w = 250
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    for i, row in enumerate(rows):
        y = i * row_h + 4
        value = float(row[value_key])
        bar_w = (width - label_w - 90) * (value / top)
        out.append(
            f'<text x="0" y="{y + 17}" font-size="13" fill="{INK}">{esc(str(row[label_key])[:34])}</text>'
            f'<rect x="{label_w}" y="{y + 5}" width="{bar_w:.1f}" height="18" rx="4" fill="{color}" opacity="0.9"/>'
            f'<text x="{label_w + bar_w + 8:.1f}" y="{y + 18}" font-size="12" fill="{MUTED}">{fmt.format(value)}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def line_chart(rows, label_key, value_key, color=NAVY, width=760, height=240):
    values = [float(r[value_key]) for r in rows]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    pad_x, pad_y = 46, 26
    plot_w = width - pad_x - 12
    plot_h = height - pad_y - 30
    step = plot_w / max(len(values) - 1, 1)
    points = []
    for i, value in enumerate(values):
        x = pad_x + i * step
        y = pad_y + plot_h - ((value - lo) / span) * plot_h
        points.append((x, y))
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = path + f" L{points[-1][0]:.1f},{pad_y + plot_h} L{points[0][0]:.1f},{pad_y + plot_h} Z"
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    out.append(f'<path d="{area}" fill="{color}" opacity="0.08"/>')
    out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.4"/>')
    for frac in (0, 0.5, 1):
        value = lo + span * frac
        y = pad_y + plot_h - (frac * plot_h)
        out.append(
            f'<line x1="{pad_x}" x2="{width - 12}" y1="{y:.1f}" y2="{y:.1f}" stroke="{LINE}"/>'
            f'<text x="0" y="{y + 4:.1f}" font-size="11" fill="{MUTED}">{value:,.0f}</text>'
        )
    every = max(1, len(rows) // 8)
    for i, row in enumerate(rows):
        if i % every:
            continue
        x = pad_x + i * step
        out.append(
            f'<text x="{x:.1f}" y="{height - 8}" font-size="10.5" fill="{MUTED}" text-anchor="middle">'
            f'{esc(row[label_key][2:])}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def column_chart(rows, label_key, value_key, color=NAVY, width=760, height=220):
    values = [float(r[value_key]) for r in rows]
    top = max(values) or 1
    pad_x, pad_y = 10, 16
    plot_h = height - pad_y - 26
    slot = (width - pad_x * 2) / len(rows)
    bar_w = slot * 0.62
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    for i, row in enumerate(rows):
        value = float(row[value_key])
        h = plot_h * (value / top)
        x = pad_x + i * slot + (slot - bar_w) / 2
        y = pad_y + plot_h - h
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="{color}" opacity="0.88"/>')
        out.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{height - 8}" font-size="10.5" fill="{MUTED}" text-anchor="middle">'
            f'{esc(row[label_key])}</text>'
        )
    out.append("</svg>")
    return "".join(out)


def kpi(value, label, note=""):
    return f'''<div class="kpi"><div class="kpi-value">{value}</div>
    <div class="kpi-label">{label}</div>{f'<div class="kpi-note">{note}</div>' if note else ''}</div>'''


def main():
    monthly = read("q1_monthly_volume.csv")
    types = read("q2_top_types.csv")
    wards = read("q3_volume_by_ward.csv")
    status = read("q4_status_by_division.csv")
    season = read("q5_seasonality.csv")
    hours = read("q6_hour_of_day.csv")
    growth = read("q8_growth_by_division.csv")

    peak = max(monthly, key=lambda r: int(r["requests"]))
    july = next((r for r in season if r["month_number"] == "7"), None)
    jan = next((r for r in season if r["month_number"] == "1"), None)

    status_rows = "".join(
        f'<tr><td>{esc(r["division"])}</td><td class="num">{int(r["requests"]):,}</td>'
        f'<td class="num ok">{r["completed_pct"]}%</td>'
        f'<td class="num warn">{r["cancelled_pct"]}%</td>'
        f'<td class="num">{r["open_pct"]}%</td></tr>'
        for r in status
    )

    growth_rows = "".join(
        f'<tr><td>{esc(r["division"])}</td><td class="num">{int(r["y2023"]):,}</td>'
        f'<td class="num">{int(r["y2025"]):,}</td>'
        f'<td class="num {"ok" if float(r["pct_change"]) >= 0 else "bad"}">{float(r["pct_change"]):+.1f}%</td></tr>'
        for r in growth if r["division"] != "Parks"
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Toronto 311 — 2023 to 2025</title>
<style>
  :root {{ --ink:{INK}; --muted:{MUTED}; --line:{LINE}; --navy:{NAVY}; --bg:#f7f8fa; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
         font:15px/1.5 -apple-system,"Segoe UI",Roboto,Arial,sans-serif; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding:40px 22px 70px; }}
  header {{ margin-bottom:26px; }}
  h1 {{ font-size:32px; letter-spacing:-.02em; margin:0 0 6px; }}
  .sub {{ color:var(--muted); margin:0; }}
  .tag {{ display:inline-block; font-size:12px; letter-spacing:.06em; text-transform:uppercase;
          color:var(--navy); background:#e8effd; border-radius:999px; padding:4px 10px; margin-bottom:14px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:22px 0 30px; }}
  .kpi {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:16px 18px; }}
  .kpi-value {{ font-size:26px; font-weight:750; letter-spacing:-.02em; }}
  .kpi-label {{ font-size:13px; color:var(--muted); margin-top:2px; }}
  .kpi-note {{ font-size:12px; color:#94a3b8; margin-top:6px; }}
  h2 {{ font-size:19px; margin:34px 0 4px; }}
  .hint {{ color:var(--muted); font-size:13px; margin:0 0 14px; }}
  .card {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:20px 22px; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th {{ text-align:left; font-weight:600; color:var(--muted); font-size:12.5px;
        text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid var(--line); padding:8px 6px; }}
  td {{ padding:9px 6px; border-bottom:1px solid #f1f5f9; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  td.ok {{ color:{GREEN}; }} td.warn {{ color:{AMBER}; }} td.bad {{ color:{RED}; }}
  .callout {{ background:#fff7ed; border:1px solid #fed7aa; border-radius:14px; padding:16px 18px; margin-top:16px; }}
  .callout b {{ color:#9a3412; }}
  footer {{ margin-top:44px; color:var(--muted); font-size:12.5px; border-top:1px solid var(--line); padding-top:16px; }}
  @media (max-width:820px) {{
    .kpis {{ grid-template-columns:1fr 1fr; }}
    .grid2 {{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="tag">Portfolio project · SQLite · SQL</div>
    <h1>Toronto 311 service requests</h1>
    <p class="sub">1,351,594 customer-initiated requests · 1 January 2023 – 31 December 2025 ·
      City of Toronto Open Data</p>
  </header>

  <div class="kpis">
    {kpi("1,351,594", "requests analysed")}
    {kpi("+20.8%", "volume growth, 2023 → 2025", "414,282 → 500,269")}
    {kpi("16.9%", "Solid Waste cancels", "76,987 dispatches")}
    {kpi("19.3%", "share of top 8 types", "830 types in total")}
  </div>

  <h2>Volume over time</h2>
  <p class="hint">Monthly requests. Peak {esc(peak["month"])} at {int(peak["requests"]):,} —
    a snowstorm, not a data error: 6,168 requests on 19 Feb 2025 alone, almost all snow clearing.</p>
  <div class="card">{line_chart(monthly, "month", "requests")}</div>

  <div class="grid2" style="margin-top:22px">
    <div>
      <h2>Seasonality</h2>
      <p class="hint">Average requests by calendar month.
        July {float(july["avg_requests_per_month"]):,.0f} vs January {float(jan["avg_requests_per_month"]):,.0f}.</p>
      <div class="card">{column_chart(season, "month_number", "avg_requests_per_month")}</div>
    </div>
    <div>
      <h2>Time of day</h2>
      <p class="hint">Requests created by hour. 9–11 am holds 25.7% of the day.</p>
      <div class="card">{column_chart(hours, "hour", "requests", color="#0e7490")}</div>
    </div>
  </div>

  <h2>Which services absorb the work</h2>
  <p class="hint">Requests by division, three years combined.</p>
  <div class="card">{bars(status, "division", "requests")}</div>

  <h2>Completion and cancellations</h2>
  <p class="hint">Status share per division. Cancellations are the hidden cost.</p>
  <div class="card">
    <table>
      <thead><tr><th>Division</th><th class="num">Requests</th><th class="num">Completed</th>
      <th class="num">Cancelled</th><th class="num">Open</th></tr></thead>
      <tbody>{status_rows}</tbody>
    </table>
  </div>
  <div class="callout"><b>76,987 Solid Waste cancellations.</b> The five most-cancelled
    types are all missed collections — garbage, furniture, recycling, green bin, yard waste.
    Those are dispatches that produced no service.</div>

  <div class="grid2" style="margin-top:26px">
    <div>
      <h2>Busiest wards</h2>
      <p class="hint">Raw counts — no population adjustment in this dataset.</p>
      <div class="card">{bars(wards[:8], "ward", "requests", color="#4338ca")}</div>
    </div>
    <div>
      <h2>Year-over-year change by division</h2>
      <p class="hint">2023 vs 2025, divisions with 1,000+ requests in 2023.
        Parks excluded — renamed in 2025, see caveat.</p>
      <div class="card">
        <table>
          <thead><tr><th>Division</th><th class="num">2023</th><th class="num">2025</th><th class="num">Change</th></tr></thead>
          <tbody>{growth_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="callout"><b>Caveat — do not read the Parks row as a collapse.</b>
    The division was renamed from <code>Parks</code> to <code>Parks and Recreation</code> in 2025;
    its recorded volume fell from 34,203 to 1,437. That is a labelling change, not a real decline.
    Any division trend including Parks is invalid without noting it.</div>

  <h2>Most common request types</h2>
  <p class="hint">The eight largest are only 19.3% of volume — demand is unusually fragmented.</p>
  <div class="card">{bars(types[:10], "request_type", "requests", color="#0f766e")}</div>

  <footer>
    Source: City of Toronto Open Data, "311 Service Requests – Customer Initiated" ·
    Open Government Licence – Toronto · downloaded 9 November 2026.
    Built with Python standard library and SQLite; queries in <code>queries.sql</code>.
  </footer>
</div>
</body>
</html>
"""

    DEST.write_text(page, encoding="utf-8")
    print(f"wrote {DEST}  ({DEST.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
