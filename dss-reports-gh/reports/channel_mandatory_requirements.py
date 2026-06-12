#!/usr/bin/env python3
"""
Enhanced DSS Channel Mandatory Requirements Report
====================================================
Reads the existing CSV data and regenerates the HTML report with:
  - Dark mode toggle with localStorage persistence
  - Analytics tab with SVG bar/donut charts and heatmap
  - Sortable table columns (click headers)
  - Export CSV / Print buttons
  - Collapsible channel/role blocks in matrix tab
  - Channel quick-navigation sidebar
  - Search term highlighting in detail tab
  - Mandatory % progress bars in summary
  - Back-to-top floating button
  - Animated tab transitions
  - Enhanced responsive/print styles
  - Keyboard shortcuts
"""

import html
import json
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas required.  pip install pandas")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_FILE = DATA_DIR / "channel_mandatoryrequirements_finalprod.csv"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "output" / "channel_mandatoryrequirements_finalprod.html"

def esc(val):
    return html.escape(str(val).strip()) if val is not None else ""


def build_enhanced_html(df: pd.DataFrame) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---- KPIs ----
    total_rows = len(df)
    channels = sorted(df["channel_name"].dropna().unique())
    roles = sorted(df["party_role_nm"].dropna().unique())
    contract_types = sorted(df["contract_type_cd"].dropna().unique())
    req_codes = sorted(df["req_code_name"].dropna().unique())
    mandatory_count = int((df["mandatory_ind"] == "Y").sum())
    optional_count = total_rows - mandatory_count
    mand_pct = round(mandatory_count / total_rows * 100, 1) if total_rows else 0

    # ---- Channel summary ----
    channel_summary = (
        df.groupby("channel_name")
        .agg(
            contract_types=("contract_type_cd", "nunique"),
            req_codes=("req_code_id", "nunique"),
            mandatory=("mandatory_ind", lambda x: (x == "Y").sum()),
            optional=("mandatory_ind", lambda x: (x != "Y").sum()),
            roles=("party_role_nm", "nunique"),
            total_mappings=("mandatory_ind", "count"),
        )
        .reset_index()
        .sort_values("channel_name")
    )

    # JSON data for charts
    chart_data = []
    for _, r in channel_summary.iterrows():
        chart_data.append({
            "channel": r["channel_name"],
            "mandatory": int(r["mandatory"]),
            "optional": int(r["optional"]),
            "total": int(r["total_mappings"]),
            "contractTypes": int(r["contract_types"]),
            "roles": int(r["roles"]),
        })

    # Role × Channel heatmap data
    heatmap_data = (
        df.groupby(["channel_name", "party_role_nm"])
        .size()
        .reset_index(name="count")
    )
    heatmap_json = []
    for _, r in heatmap_data.iterrows():
        heatmap_json.append({
            "channel": r["channel_name"],
            "role": r["party_role_nm"],
            "count": int(r["count"]),
        })

    # Required code breakdown
    code_breakdown = (
        df.groupby("req_code_name")
        .agg(
            mandatory=("mandatory_ind", lambda x: (x == "Y").sum()),
            optional=("mandatory_ind", lambda x: (x != "Y").sum()),
            total=("mandatory_ind", "count"),
        )
        .reset_index()
        .sort_values("total", ascending=False)
    )
    code_chart_data = []
    for _, r in code_breakdown.iterrows():
        code_chart_data.append({
            "code": r["req_code_name"],
            "mandatory": int(r["mandatory"]),
            "optional": int(r["optional"]),
            "total": int(r["total"]),
        })

    # ---- Summary rows with progress bars ----
    ch_summary_rows = []
    for _, r in channel_summary.iterrows():
        m = int(r["mandatory"])
        t = int(r["total_mappings"])
        pct = round(m / t * 100, 1) if t else 0
        ch_summary_rows.append(f"""
        <tr>
            <td><strong>{esc(r['channel_name'])}</strong></td>
            <td class="num">{int(r['contract_types'])}</td>
            <td class="num">{int(r['req_codes'])}</td>
            <td class="num">{int(r['roles'])}</td>
            <td class="num m-yes-bg">{m}</td>
            <td class="num m-no-bg">{int(r['optional'])}</td>
            <td class="num">{t}</td>
            <td>
                <div class="progress-bar-track">
                    <div class="progress-bar-fill" style="width:{pct}%"></div>
                    <span class="progress-bar-text">{pct}%</span>
                </div>
            </td>
        </tr>""")

    # ---- Matrix: channel/role pivot tables ----
    channel_blocks = []
    for ch in channels:
        ch_df = df[df["channel_name"] == ch].copy()
        ch_roles = sorted(ch_df["party_role_nm"].unique())
        ch_mand = int((ch_df["mandatory_ind"] == "Y").sum())
        ch_total = len(ch_df)
        role_blocks = []
        for role in ch_roles:
            role_df = ch_df[ch_df["party_role_nm"] == role].copy()
            role_count = len(role_df)
            role_mand = int((role_df["mandatory_ind"] == "Y").sum())
            pivot = role_df.pivot_table(
                index=["contract_type_id", "contract_type_cd", "contract_type_nm", "level_value", "level_name"],
                columns="req_code_name",
                values="mandatory_ind",
                aggfunc="first",
            ).reset_index()
            pivot = pivot.sort_values(["level_value", "contract_type_cd"])
            code_cols = sorted([c for c in pivot.columns if c not in
                         ("contract_type_id", "contract_type_cd", "contract_type_nm", "level_value", "level_name")])

            rows_html = []
            for _, row in pivot.iterrows():
                cells = [
                    f'<td class="ct-id">{esc(row["contract_type_id"])}</td>',
                    f'<td class="ct-cd"><strong>{esc(row["contract_type_cd"])}</strong></td>',
                    f'<td class="ct-nm">{esc(row["contract_type_nm"])}</td>',
                    f'<td class="lvl">{esc(row["level_value"])}</td>',
                    f'<td class="lvl">{esc(row["level_name"])}</td>',
                ]
                for cc in code_cols:
                    val = row.get(cc, "")
                    if val == "Y":
                        cells.append('<td class="m-yes">Y</td>')
                    elif val == "N":
                        cells.append('<td class="m-no">N</td>')
                    else:
                        cells.append('<td class="m-na">&mdash;</td>')
                rows_html.append("<tr>" + "".join(cells) + "</tr>")

            header_cells = (
                '<th>Type ID</th><th>Code</th><th>Contract Type</th><th>Level</th><th>Level Name</th>'
                + "".join(f"<th>{esc(c)}</th>" for c in code_cols)
            )

            role_blocks.append(f"""
            <div class="role-block collapsible-section">
                <h4 class="role-title collapsible-toggle" onclick="toggleCollapse(this)">
                    <span class="collapse-icon">&#9660;</span> {esc(role)}
                    <span class="badge badge-blue">{role_count}</span>
                    <span class="badge badge-green">{role_mand}Y</span>
                </h4>
                <div class="collapsible-body">
                    <table class="data-table pivot-table sortable-table">
                        <thead><tr>{header_cells}</tr></thead>
                        <tbody>{"".join(rows_html)}</tbody>
                    </table>
                </div>
            </div>""")

        ch_safe_id = esc(ch).replace(" ", "_").replace("-","_")
        channel_blocks.append(f"""
        <div class="channel-block" id="ch-{ch_safe_id}" data-channel-name="{esc(ch)}">
            <h3 class="channel-title collapsible-toggle" onclick="toggleCollapse(this)">
                <span class="collapse-icon">&#9660;</span> {esc(ch)}
                <span class="badge badge-dark">{ch_total} mappings</span>
                <span class="badge badge-green">{ch_mand} mandatory</span>
            </h3>
            <div class="collapsible-body">
                {"".join(role_blocks)}
            </div>
        </div>""")

    # ---- Flat detail rows ----
    flat_rows = []
    for _, r in df.iterrows():
        mclass = "m-yes" if r["mandatory_ind"] == "Y" else "m-no"
        flat_rows.append(f"""
        <tr class="flat-row" data-channel="{esc(r['channel_name'])}"
            data-role="{esc(r['party_role_nm'])}" data-mandatory="{esc(r['mandatory_ind'])}">
            <td>{esc(r['channel_name'])}</td>
            <td>{esc(r['party_role_nm'])}</td>
            <td>{esc(r['contract_type_cd'])}</td>
            <td>{esc(r['contract_type_nm'])}</td>
            <td>{esc(r['contract_type_id'])}</td>
            <td>{esc(r['level_value'])}</td>
            <td>{esc(r['level_name'])}</td>
            <td>{esc(r['req_code_id'])}</td>
            <td>{esc(r['req_code_name'])}</td>
            <td class="{mclass}"><strong>{esc(r['mandatory_ind'])}</strong></td>
        </tr>""")

    # ---- Legend ----
    code_legend = df[["req_code_id", "req_code_name"]].drop_duplicates().sort_values("req_code_id")
    legend_rows = "".join(
        f"<tr><td>{esc(r['req_code_id'])}</td><td>{esc(r['req_code_name'])}</td></tr>"
        for _, r in code_legend.iterrows()
    )

    # ---- Channel nav links ----
    ch_nav_links = []
    for ch in channels:
        ch_safe_id = esc(ch).replace(" ", "_").replace("-","_")
        short = ch.split(" - ")[0] if " - " in ch else ch[:6]
        ch_nav_links.append(
            f'<a class="ch-nav-link" href="#ch-{ch_safe_id}" onclick="scrollToChannel(\'{ch_safe_id}\')">{esc(short)}</a>'
        )

    # ---- Filter channel/role options ----
    ch_options = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in channels)
    role_options = "".join(f'<option value="{esc(r)}">{esc(r)}</option>' for r in roles)

    # ========================================================================
    # FULL HTML TEMPLATE
    # ========================================================================
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DSS Channel Mandatory Requirements — Production</title>
<style>
/* ============================================================ */
/* CSS CUSTOM PROPERTIES                                        */
/* ============================================================ */
:root {{
    --manulife-green: #00a758;
    --manulife-dark: #003b2e;
    --blue: #1976d2;
    --red: #d32f2f;
    --orange: #f57c00;
    --purple: #7b1fa2;
    --bg: #f5f7fa;
    --card-bg: #ffffff;
    --border: #e0e0e0;
    --text: #333333;
    --text-muted: #757575;
    --hover-bg: #f8fafb;
    --shadow: 0 2px 8px rgba(0,0,0,.08);
    --shadow-lg: 0 4px 16px rgba(0,0,0,.12);
    --anim-speed: .25s;
    --radius: 10px;
}}

/* ---- Dark Mode ---- */
[data-theme="dark"] {{
    --bg: #1a1a2e;
    --card-bg: #16213e;
    --border: #2a2a4a;
    --text: #e0e0e0;
    --text-muted: #9e9e9e;
    --hover-bg: #1e2a4a;
    --shadow: 0 2px 8px rgba(0,0,0,.3);
    --shadow-lg: 0 4px 16px rgba(0,0,0,.4);
}}
[data-theme="dark"] .header {{ background: linear-gradient(135deg, #0d1b2a, #1b4332); }}
[data-theme="dark"] th {{ background: #1e2a4a; }}
[data-theme="dark"] .m-yes-bg {{ background: rgba(0,167,88,.15); }}
[data-theme="dark"] .m-no-bg {{ background: rgba(245,124,0,.12); }}
[data-theme="dark"] tr:hover {{ background: #1e2a4a; }}
[data-theme="dark"] .progress-bar-track {{ background: #2a2a4a; }}
[data-theme="dark"] .legend-card {{ background: #1e2a4a; }}
[data-theme="dark"] .channel-title {{ color: #66bb6a; }}
[data-theme="dark"] .role-title {{ color: #64b5f6; }}
[data-theme="dark"] .filter-bar {{ background: #16213e; }}
[data-theme="dark"] .kpi-card {{ background: #16213e; }}
[data-theme="dark"] .chart-card {{ background: #16213e; }}
[data-theme="dark"] .ch-nav {{ background: #16213e; border-color: #2a2a4a; }}
[data-theme="dark"] .ch-nav-link {{ color: #9e9e9e; }}
[data-theme="dark"] .ch-nav-link:hover {{ background: #1e2a4a; color: #66bb6a; }}
[data-theme="dark"] .tab-bar {{ background: #16213e; }}
[data-theme="dark"] .section {{ background: #16213e; }}
[data-theme="dark"] td {{ border-bottom-color: #2a2a4a; }}
[data-theme="dark"] .heatmap-cell {{ color: #e0e0e0; }}

/* ============================================================ */
/* BASE STYLES                                                  */
/* ============================================================ */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5;
    transition: background var(--anim-speed), color var(--anim-speed);
}}

/* ---- Header ---- */
.header {{
    background: linear-gradient(135deg, var(--manulife-dark), var(--manulife-green));
    color: white; padding: 24px 32px;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 12px;
}}
.header-left h1 {{ font-size: 24px; margin-bottom: 4px; }}
.header-left .subtitle {{ opacity: 0.85; font-size: 14px; }}
.header-actions {{ display: flex; gap: 8px; align-items: center; }}
.header-btn {{
    padding: 7px 14px; border: 1px solid rgba(255,255,255,.35); border-radius: 6px;
    background: rgba(255,255,255,.12); color: white; cursor: pointer; font-size: 13px;
    transition: all .2s; display: flex; align-items: center; gap: 6px;
}}
.header-btn:hover {{ background: rgba(255,255,255,.25); }}
.header-btn svg {{ width: 16px; height: 16px; fill: currentColor; }}

/* ---- KPI Cards ---- */
.kpi-row {{ display: flex; gap: 16px; padding: 20px 32px; flex-wrap: wrap; }}
.kpi-card {{
    background: var(--card-bg); border-radius: var(--radius); padding: 20px 24px;
    flex: 1; min-width: 130px; box-shadow: var(--shadow); text-align: center;
    transition: transform .2s, box-shadow .2s, background var(--anim-speed);
    position: relative; overflow: hidden;
}}
.kpi-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-lg); }}
.kpi-card::after {{
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
}}
.kpi-card:nth-child(1)::after {{ background: var(--blue); }}
.kpi-card:nth-child(2)::after {{ background: var(--manulife-green); }}
.kpi-card:nth-child(3)::after {{ background: var(--blue); }}
.kpi-card:nth-child(4)::after {{ background: var(--orange); }}
.kpi-card:nth-child(5)::after {{ background: var(--manulife-green); }}
.kpi-card:nth-child(6)::after {{ background: var(--manulife-green); }}
.kpi-card:nth-child(7)::after {{ background: var(--red); }}
.kpi-card:nth-child(8)::after {{ background: var(--purple); }}
.kpi-val {{ font-size: 32px; font-weight: 700; }}
.kpi-label {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: .5px; }}
.kpi-green {{ color: var(--manulife-green); }}
.kpi-blue {{ color: var(--blue); }}
.kpi-red {{ color: var(--red); }}
.kpi-orange {{ color: var(--orange); }}
.kpi-purple {{ color: var(--purple); }}

/* ---- Tabs ---- */
.tab-bar {{
    display: flex; gap: 0; border-bottom: 2px solid var(--border);
    padding: 0 32px; background: var(--card-bg); flex-wrap: wrap;
    transition: background var(--anim-speed);
}}
.tab-btn {{
    padding: 12px 24px; cursor: pointer; border: none; background: none;
    font-size: 14px; font-weight: 600; color: var(--text-muted);
    border-bottom: 3px solid transparent; transition: all .2s;
    position: relative;
}}
.tab-btn:hover {{ color: var(--manulife-green); }}
.tab-btn.active {{ color: var(--manulife-green); border-bottom-color: var(--manulife-green); }}
.tab-content {{
    display: none; padding: 20px 32px;
    animation: fadeIn .3s ease;
}}
.tab-content.active {{ display: block; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}

/* ---- Filters ---- */
.filter-bar {{
    display: flex; gap: 12px; padding: 16px 32px; background: var(--card-bg);
    border-bottom: 1px solid var(--border); flex-wrap: wrap; align-items: center;
    transition: background var(--anim-speed);
}}
.filter-bar label {{ font-size: 13px; font-weight: 600; margin-right: 4px; }}
.filter-bar select, .filter-bar input {{
    padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px;
    font-size: 13px; background: var(--card-bg); color: var(--text);
    transition: border-color .2s;
}}
.filter-bar select:focus, .filter-bar input:focus {{ border-color: var(--manulife-green); outline: none; }}
.filter-bar input {{ width: 200px; }}
.btn-action {{
    padding: 6px 14px; background: var(--manulife-green); color: white;
    border: none; border-radius: 6px; cursor: pointer; font-size: 13px;
    transition: background .2s; display: inline-flex; align-items: center; gap: 4px;
}}
.btn-action:hover {{ background: var(--manulife-dark); }}
.btn-outline {{
    padding: 6px 14px; background: transparent; color: var(--manulife-green);
    border: 1px solid var(--manulife-green); border-radius: 6px; cursor: pointer;
    font-size: 13px; transition: all .2s; display: inline-flex; align-items: center; gap: 4px;
}}
.btn-outline:hover {{ background: var(--manulife-green); color: white; }}

/* ---- Tables ---- */
.section {{
    background: var(--card-bg); border-radius: var(--radius); margin: 16px 0;
    box-shadow: var(--shadow); overflow: hidden;
    transition: background var(--anim-speed);
}}
.section-title {{
    padding: 16px 20px; font-size: 16px; font-weight: 700;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{
    background: #f0f4f8; padding: 10px 12px; text-align: left; font-weight: 700;
    position: sticky; top: 0; z-index: 2; border-bottom: 2px solid var(--border);
    white-space: nowrap; transition: background var(--anim-speed);
    user-select: none;
}}
th.sortable {{ cursor: pointer; }}
th.sortable:hover {{ background: #e3eaf0; }}
th .sort-icon {{ font-size: 10px; margin-left: 4px; opacity: .3; }}
th.sort-asc .sort-icon, th.sort-desc .sort-icon {{ opacity: 1; color: var(--manulife-green); }}
td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; transition: background var(--anim-speed); }}
tbody tr:nth-child(even) {{ background: rgba(0,0,0,.015); }}
tbody tr:hover {{ background: var(--hover-bg); }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.m-yes {{ color: var(--manulife-green); font-weight: 700; }}
.m-no {{ color: var(--text-muted); }}
.m-na {{ color: #ccc; text-align: center; }}
.m-yes-bg {{ background: #e8f5e9; }}
.m-no-bg {{ background: #fff3e0; }}
.ct-id {{ color: var(--text-muted); font-size: 12px; }}
.ct-cd {{ white-space: nowrap; }}
.ct-nm {{ max-width: 240px; }}
.lvl {{ white-space: nowrap; }}

/* ---- Progress Bars ---- */
.progress-bar-track {{
    width: 100%; height: 22px; background: #e8e8e8; border-radius: 11px;
    position: relative; overflow: hidden; min-width: 80px;
}}
.progress-bar-fill {{
    height: 100%; border-radius: 11px;
    background: linear-gradient(90deg, var(--manulife-green), #66bb6a);
    transition: width .6s ease;
}}
.progress-bar-text {{
    position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
    font-size: 11px; font-weight: 700; color: var(--text);
}}

/* ---- Badges ---- */
.badge {{
    display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px;
    font-weight: 600; margin-left: 8px; vertical-align: middle;
}}
.badge-green {{ background: #e8f5e9; color: #2e7d32; }}
.badge-blue {{ background: #e3f2fd; color: #1565c0; }}
.badge-dark {{ background: #eceff1; color: #455a64; }}
.badge-red {{ background: #ffebee; color: #c62828; }}
[data-theme="dark"] .badge-green {{ background: rgba(0,167,88,.2); color: #66bb6a; }}
[data-theme="dark"] .badge-blue {{ background: rgba(25,118,210,.2); color: #64b5f6; }}
[data-theme="dark"] .badge-dark {{ background: rgba(255,255,255,.08); color: #b0bec5; }}

/* ---- Collapsible ---- */
.collapsible-toggle {{ cursor: pointer; user-select: none; }}
.collapsible-toggle:hover {{ opacity: .85; }}
.collapse-icon {{
    display: inline-block; transition: transform .2s; font-size: 12px; margin-right: 4px;
}}
.collapsible-section.collapsed .collapse-icon {{ transform: rotate(-90deg); }}
.collapsible-section.collapsed .collapsible-body {{ display: none; }}

/* ---- Channel / Role blocks ---- */
.channel-block {{ margin-bottom: 28px; }}
.channel-title {{
    font-size: 20px; font-weight: 700; color: var(--manulife-dark);
    padding: 12px 0 8px; border-bottom: 2px solid var(--manulife-green);
    margin-bottom: 12px; display: flex; align-items: center; flex-wrap: wrap;
}}
.role-block {{ margin: 12px 0 20px 0; }}
.role-title {{
    font-size: 15px; color: var(--blue); margin-bottom: 8px;
    display: flex; align-items: center; flex-wrap: wrap;
}}
.pivot-table th {{ font-size: 12px; text-align: center; }}
.pivot-table td {{ text-align: center; }}
.pivot-table td.ct-cd, .pivot-table td.ct-nm, .pivot-table td.ct-id, .pivot-table td.lvl {{ text-align: left; }}

/* ---- Channel Nav ---- */
.matrix-layout {{ display: flex; gap: 20px; }}
.ch-nav {{
    position: sticky; top: 10px; align-self: flex-start;
    background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 12px; min-width: 130px; box-shadow: var(--shadow);
    transition: background var(--anim-speed);
}}
.ch-nav h4 {{ font-size: 12px; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase; letter-spacing: .5px; }}
.ch-nav-link {{
    display: block; padding: 6px 10px; font-size: 13px; font-weight: 600;
    color: var(--text-muted); text-decoration: none; border-radius: 4px;
    transition: all .15s; margin-bottom: 2px;
}}
.ch-nav-link:hover {{ background: #e8f5e9; color: var(--manulife-green); }}
.ch-nav-link.active {{ background: var(--manulife-green); color: white; }}
.matrix-content {{ flex: 1; min-width: 0; }}
.matrix-toolbar {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}

/* ---- Scroll wrapper ---- */
.table-scroll {{ overflow-x: auto; max-height: 70vh; overflow-y: auto; }}

/* ---- Search Highlight ---- */
mark.search-hl {{ background: #fff176; color: #333; padding: 0 2px; border-radius: 2px; }}
[data-theme="dark"] mark.search-hl {{ background: #f9a825; color: #1a1a2e; }}

/* ---- Charts ---- */
.chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; margin-top: 12px; }}
.chart-card {{
    background: var(--card-bg); border-radius: var(--radius); padding: 20px;
    box-shadow: var(--shadow); transition: background var(--anim-speed);
}}
.chart-card h4 {{ margin-bottom: 14px; font-size: 15px; color: var(--text); }}
.chart-container {{ width: 100%; overflow-x: auto; }}

/* SVG chart styles */
.bar-label {{ font-size: 11px; fill: var(--text-muted); }}
.bar-val {{ font-size: 11px; font-weight: 700; fill: var(--text); }}
.axis-label {{ font-size: 12px; fill: var(--text); font-weight: 600; }}
.donut-label {{ fill: var(--text); font-weight: 700; }}
.donut-pct {{ font-size: 28px; }}
.donut-sub {{ font-size: 12px; fill: var(--text-muted); }}

/* Heatmap */
.heatmap-table {{ border-collapse: collapse; }}
.heatmap-table th {{ font-size: 11px; padding: 6px 8px; text-align: center; white-space: normal; max-width: 80px; }}
.heatmap-table td {{ padding: 4px; text-align: center; }}
.heatmap-cell {{
    width: 44px; height: 32px; border-radius: 4px; display: inline-flex;
    align-items: center; justify-content: center; font-size: 11px; font-weight: 700;
    color: #333;
}}

/* ---- Footer ---- */
.footer {{ padding: 16px 32px; text-align: center; font-size: 12px; color: var(--text-muted); }}

/* ---- Legend ---- */
.legend-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; margin-top: 12px; }}
.legend-card {{
    background: var(--card-bg); border-radius: 8px; padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06); transition: background var(--anim-speed);
}}
.legend-card h4 {{ margin-bottom: 8px; font-size: 14px; color: var(--manulife-dark); }}
.legend-card table {{ font-size: 12px; }}

/* ---- Back to Top ---- */
.back-to-top {{
    position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px;
    border-radius: 50%; background: var(--manulife-green); color: white;
    border: none; cursor: pointer; font-size: 20px; box-shadow: var(--shadow-lg);
    display: none; align-items: center; justify-content: center;
    transition: transform .2s, opacity .2s; z-index: 999;
}}
.back-to-top:hover {{ transform: scale(1.1); }}
.back-to-top.visible {{ display: flex; }}

/* ---- Keyboard shortcuts hint ---- */
.kbd {{ display: inline-block; background: var(--border); padding: 1px 6px; border-radius: 3px; font-size: 11px; font-family: monospace; }}

/* ---- Print ---- */
@media print {{
    .filter-bar, .tab-bar, .header-actions, .btn-action, .btn-outline,
    .ch-nav, .back-to-top, .matrix-toolbar {{ display: none !important; }}
    .tab-content {{ display: block !important; page-break-inside: avoid; }}
    body {{ font-size: 11px; background: white; color: #000; }}
    .header {{ background: #003b2e !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .kpi-card {{ box-shadow: none; border: 1px solid #ddd; }}
    .section {{ box-shadow: none; border: 1px solid #ddd; }}
    .matrix-layout {{ display: block; }}
}}

/* ---- Responsive ---- */
@media (max-width: 768px) {{
    .header {{ padding: 16px; }}
    .header-left h1 {{ font-size: 18px; }}
    .kpi-row {{ padding: 12px 16px; gap: 8px; }}
    .kpi-card {{ min-width: 100px; padding: 12px; }}
    .kpi-val {{ font-size: 24px; }}
    .tab-bar {{ padding: 0 16px; }}
    .tab-btn {{ padding: 10px 14px; font-size: 13px; }}
    .tab-content {{ padding: 12px 16px; }}
    .filter-bar {{ padding: 12px 16px; }}
    .ch-nav {{ display: none; }}
    .chart-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<!-- ================================================================ -->
<!-- HEADER                                                           -->
<!-- ================================================================ -->
<div class="header">
    <div class="header-left">
        <h1>DSS Channel Mandatory Requirements — Production</h1>
        <div class="subtitle">
            Source: MS_DSS_A1 &nbsp;|&nbsp; Generated: {generated} &nbsp;|&nbsp;
            Query: GET_MANDATORY_REQUIREMENTS (enhanced with names)
        </div>
    </div>
    <div class="header-actions">
        <button class="header-btn" onclick="exportCSV()" title="Export filtered data as CSV">
            <svg viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
            Export CSV
        </button>
        <button class="header-btn" onclick="window.print()" title="Print report">
            <svg viewBox="0 0 24 24"><path d="M19 8H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zm-3 11H8v-5h8v5zm3-7c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm-1-9H6v4h12V3z"/></svg>
            Print
        </button>
        <button class="header-btn" onclick="toggleDarkMode()" id="dark-mode-btn" title="Toggle dark mode (Ctrl+D)">
            <svg viewBox="0 0 24 24" id="dm-icon"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.82.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>
            <span id="dm-label">Dark</span>
        </button>
    </div>
</div>

<!-- ================================================================ -->
<!-- KPI ROW                                                          -->
<!-- ================================================================ -->
<div class="kpi-row">
    <div class="kpi-card"><div class="kpi-val kpi-blue">{total_rows}</div><div class="kpi-label">Total Mappings</div></div>
    <div class="kpi-card"><div class="kpi-val kpi-green">{len(channels)}</div><div class="kpi-label">Channels</div></div>
    <div class="kpi-card"><div class="kpi-val kpi-blue">{len(roles)}</div><div class="kpi-label">Party Roles</div></div>
    <div class="kpi-card"><div class="kpi-val kpi-orange">{len(contract_types)}</div><div class="kpi-label">Contract Types</div></div>
    <div class="kpi-card"><div class="kpi-val kpi-green">{len(req_codes)}</div><div class="kpi-label">Required Codes</div></div>
    <div class="kpi-card"><div class="kpi-val kpi-green">{mandatory_count}</div><div class="kpi-label">Mandatory (Y)</div></div>
    <div class="kpi-card"><div class="kpi-val kpi-red">{optional_count}</div><div class="kpi-label">Optional (N)</div></div>
    <div class="kpi-card"><div class="kpi-val kpi-purple">{mand_pct}%</div><div class="kpi-label">Mandatory Rate</div></div>
</div>

<!-- ================================================================ -->
<!-- TABS                                                             -->
<!-- ================================================================ -->
<div class="tab-bar" id="tab-bar">
    <button class="tab-btn active" data-tab="summary">Summary</button>
    <button class="tab-btn" data-tab="analytics">Analytics</button>
    <button class="tab-btn" data-tab="matrix">Code Matrix</button>
    <button class="tab-btn" data-tab="detail">Full Detail</button>
    <button class="tab-btn" data-tab="legend">Code Legend</button>
</div>

<!-- ================================================================ -->
<!-- TAB 1: Summary                                                    -->
<!-- ================================================================ -->
<div class="tab-content active" id="tab-summary">
    <div class="section">
        <div class="section-title">
            Channel Summary
            <span style="font-size:12px;color:var(--text-muted);">Click column headers to sort</span>
        </div>
        <div class="table-scroll">
            <table class="sortable-table" id="summary-table">
                <thead>
                    <tr>
                        <th class="sortable" data-col="0">Channel <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="1">Contract Types <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="2">Required Codes <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="3">Roles <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="4">Mandatory (Y) <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="5">Optional (N) <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="6">Total Mappings <span class="sort-icon">&#9650;</span></th>
                        <th>Mandatory %</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(ch_summary_rows)}
                    <tr class="summary-total" style="font-weight:700; background:#f0f4f8;">
                        <td>TOTAL</td>
                        <td class="num">{len(contract_types)}</td>
                        <td class="num">{len(req_codes)}</td>
                        <td class="num">{len(roles)}</td>
                        <td class="num m-yes-bg">{mandatory_count}</td>
                        <td class="num m-no-bg">{optional_count}</td>
                        <td class="num">{total_rows}</td>
                        <td>
                            <div class="progress-bar-track">
                                <div class="progress-bar-fill" style="width:{mand_pct}%"></div>
                                <span class="progress-bar-text">{mand_pct}%</span>
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- ================================================================ -->
<!-- TAB 2: Analytics                                                  -->
<!-- ================================================================ -->
<div class="tab-content" id="tab-analytics">
    <div class="chart-grid">
        <div class="chart-card">
            <h4>Mandatory vs Optional by Channel</h4>
            <div class="chart-container" id="chart-bar"></div>
        </div>
        <div class="chart-card">
            <h4>Overall Mandatory Rate</h4>
            <div class="chart-container" id="chart-donut" style="display:flex;justify-content:center;"></div>
        </div>
        <div class="chart-card">
            <h4>Required Code Distribution</h4>
            <div class="chart-container" id="chart-codes"></div>
        </div>
        <div class="chart-card">
            <h4>Role &times; Channel Heatmap</h4>
            <div class="chart-container" id="chart-heatmap" style="overflow-x:auto;"></div>
        </div>
    </div>
</div>

<!-- ================================================================ -->
<!-- TAB 3: Code Matrix (pivot per channel + role)                    -->
<!-- ================================================================ -->
<div class="tab-content" id="tab-matrix">
    <div class="matrix-toolbar">
        <button class="btn-action" onclick="expandAll()">&#9660; Expand All</button>
        <button class="btn-outline" onclick="collapseAll()">&#9654; Collapse All</button>
    </div>
    <div class="matrix-layout">
        <nav class="ch-nav">
            <h4>Channels</h4>
            {"".join(ch_nav_links)}
        </nav>
        <div class="matrix-content">
            {"".join(channel_blocks)}
        </div>
    </div>
</div>

<!-- ================================================================ -->
<!-- TAB 4: Full Detail (filterable flat table)                       -->
<!-- ================================================================ -->
<div class="tab-content" id="tab-detail">
    <div class="filter-bar">
        <label for="flt-ch">Channel</label>
        <select id="flt-ch">
            <option value="">All</option>
            {ch_options}
        </select>

        <label for="flt-role">Role</label>
        <select id="flt-role">
            <option value="">All</option>
            {role_options}
        </select>

        <label for="flt-mand">Mandatory</label>
        <select id="flt-mand">
            <option value="">All</option>
            <option value="Y">Y — Mandatory</option>
            <option value="N">N — Optional</option>
        </select>

        <label for="flt-search">Search <span class="kbd">Ctrl+K</span></label>
        <input id="flt-search" type="text" placeholder="Type to search…">

        <button class="btn-action" onclick="resetFilters()">Reset</button>
        <button class="btn-outline" onclick="exportCSV()">Export CSV</button>
        <span id="row-count" style="margin-left:8px; font-size:13px; color:var(--text-muted);"></span>
    </div>
    <div class="section">
        <div class="table-scroll" style="max-height:65vh;">
            <table id="detail-table" class="sortable-table">
                <thead>
                    <tr>
                        <th class="sortable" data-col="0">Channel <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="1">Party Role <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="2">Type Code <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="3">Contract Type <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="4">Type ID <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="5">Level <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="6">Level Name <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="7">Req Code ID <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="8">Required Code <span class="sort-icon">&#9650;</span></th>
                        <th class="sortable" data-col="9">Mandatory <span class="sort-icon">&#9650;</span></th>
                    </tr>
                </thead>
                <tbody id="detail-tbody">
                    {"".join(flat_rows)}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- ================================================================ -->
<!-- TAB 5: Code Legend                                                -->
<!-- ================================================================ -->
<div class="tab-content" id="tab-legend">
    <div class="legend-grid">
        <div class="legend-card">
            <h4>Required Code IDs</h4>
            <table>
                <thead><tr><th>req_code_id</th><th>Code Name</th></tr></thead>
                <tbody>{legend_rows}</tbody>
            </table>
        </div>
        <div class="legend-card">
            <h4>Mandatory Indicator</h4>
            <table>
                <tbody>
                    <tr><td class="m-yes"><strong>Y</strong></td><td>Code is <strong>mandatory</strong> — must be assigned for contract setup</td></tr>
                    <tr><td class="m-no">N</td><td>Code is <strong>optional</strong> — available but not enforced</td></tr>
                    <tr><td class="m-na">&mdash;</td><td>Not applicable for this contract type</td></tr>
                </tbody>
            </table>
        </div>
        <div class="legend-card">
            <h4>Excluded Codes (hardcoded in Java)</h4>
            <table>
                <tbody>
                    <tr><td>100001</td><td>Ident — always auto-generated from CODE_BANK</td></tr>
                    <tr><td>100017</td><td>Maritime Life Code — special handling outside this framework</td></tr>
                </tbody>
            </table>
        </div>
        <div class="legend-card">
            <h4>Data Source</h4>
            <table>
                <tbody>
                    <tr><td>Database</td><td>MS_DSS_A1 (Production)</td></tr>
                    <tr><td>Query</td><td>GET_MANDATORY_REQUIREMENTS (enhanced)</td></tr>
                    <tr><td>Tables</td><td>adm_contract_relate_code, adm_contract_type_level,<br>adm_contract_type_channel, adm_contract_required_code,<br>adm_contract_type, adm_party_role, channel_view, adm_levels</td></tr>
                    <tr><td>Generated</td><td>{generated}</td></tr>
                </tbody>
            </table>
        </div>
        <div class="legend-card">
            <h4>Keyboard Shortcuts</h4>
            <table>
                <tbody>
                    <tr><td><span class="kbd">Ctrl+D</span></td><td>Toggle dark mode</td></tr>
                    <tr><td><span class="kbd">Ctrl+K</span></td><td>Focus search in Detail tab</td></tr>
                    <tr><td><span class="kbd">Ctrl+E</span></td><td>Export filtered data as CSV</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- ================================================================ -->
<!-- FOOTER                                                           -->
<!-- ================================================================ -->
<div class="footer">
    DSS Channel Mandatory Requirements Report &nbsp;|&nbsp; Source: MS_DSS_A1 Production &nbsp;|&nbsp;
    {total_rows} mappings across {len(channels)} channels, {len(contract_types)} contract types, {len(req_codes)} required codes &nbsp;|&nbsp;
    Generated {generated}
</div>

<!-- Back to Top -->
<button class="back-to-top" id="btn-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" title="Back to top">&#9650;</button>

<!-- ================================================================ -->
<!-- JAVASCRIPT                                                       -->
<!-- ================================================================ -->
<script>
// ---- Chart Data ----
const CHART_DATA = {json.dumps(chart_data)};
const HEATMAP_DATA = {json.dumps(heatmap_json)};
const CODE_DATA = {json.dumps(code_chart_data)};
const CHANNELS = {json.dumps(channels)};
const ROLES = {json.dumps(list(roles))};
const TOTAL_MANDATORY = {mandatory_count};
const TOTAL_OPTIONAL = {optional_count};

// ==================================================================
// TABS
// ==================================================================
document.getElementById('tab-bar').addEventListener('click', function(e) {{
    const btn = e.target.closest('.tab-btn');
    if (!btn) return;
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');
    btn.classList.add('active');
    if (tab === 'detail') applyFilters();
    if (tab === 'analytics') renderCharts();
}});

// ==================================================================
// DARK MODE
// ==================================================================
function toggleDarkMode() {{
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('dss-theme', isDark ? 'light' : 'dark');
    document.getElementById('dm-label').textContent = isDark ? 'Dark' : 'Light';
    // Re-render charts with new theme
    if (document.getElementById('tab-analytics').classList.contains('active')) renderCharts();
}}
// Restore theme
(function() {{
    const saved = localStorage.getItem('dss-theme');
    if (saved === 'dark') {{
        document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('dm-label').textContent = 'Light';
    }}
}})();

// ==================================================================
// FILTERS & SEARCH HIGHLIGHTING
// ==================================================================
function applyFilters() {{
    const ch = document.getElementById('flt-ch').value;
    const role = document.getElementById('flt-role').value;
    const mand = document.getElementById('flt-mand').value;
    const search = document.getElementById('flt-search').value.toLowerCase();
    const rows = document.querySelectorAll('#detail-tbody .flat-row');
    let shown = 0;

    // Clear previous highlights
    rows.forEach(r => {{
        r.querySelectorAll('mark.search-hl').forEach(m => {{
            m.replaceWith(m.textContent);
        }});
    }});

    rows.forEach(r => {{
        let show = true;
        if (ch && r.dataset.channel !== ch) show = false;
        if (role && r.dataset.role !== role) show = false;
        if (mand && r.dataset.mandatory !== mand) show = false;
        if (search && !r.textContent.toLowerCase().includes(search)) show = false;
        r.style.display = show ? '' : 'none';
        if (show) {{
            shown++;
            // Highlight matches
            if (search) highlightRow(r, search);
        }}
    }});
    document.getElementById('row-count').textContent = shown + ' of ' + rows.length + ' rows';
}}

function highlightRow(row, term) {{
    row.querySelectorAll('td').forEach(td => {{
        const text = td.textContent;
        if (text.toLowerCase().includes(term)) {{
            const regex = new RegExp('(' + term.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
            td.innerHTML = text.replace(regex, '<mark class="search-hl">$1</mark>');
        }}
    }});
}}

function resetFilters() {{
    document.getElementById('flt-ch').value = '';
    document.getElementById('flt-role').value = '';
    document.getElementById('flt-mand').value = '';
    document.getElementById('flt-search').value = '';
    applyFilters();
}}

// Attach filter listeners
['flt-ch', 'flt-role', 'flt-mand'].forEach(id => {{
    document.getElementById(id).addEventListener('change', applyFilters);
}});
document.getElementById('flt-search').addEventListener('input', applyFilters);

// ==================================================================
// TABLE SORTING
// ==================================================================
document.querySelectorAll('.sortable-table').forEach(table => {{
    table.querySelectorAll('th.sortable').forEach(th => {{
        th.addEventListener('click', function() {{
            const col = parseInt(this.dataset.col);
            const tbody = this.closest('table').querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr:not(.summary-total)'));
            const isAsc = this.classList.contains('sort-asc');

            // Reset icons
            this.closest('tr').querySelectorAll('th.sortable').forEach(h => {{
                h.classList.remove('sort-asc', 'sort-desc');
            }});
            this.classList.add(isAsc ? 'sort-desc' : 'sort-asc');

            rows.sort((a, b) => {{
                const aVal = a.cells[col]?.textContent?.trim() || '';
                const bVal = b.cells[col]?.textContent?.trim() || '';
                const aNum = parseFloat(aVal.replace(/[^\\d.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^\\d.-]/g, ''));
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return isAsc ? bNum - aNum : aNum - bNum;
                }}
                return isAsc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
            }});
            rows.forEach(r => tbody.appendChild(r));
        }});
    }});
}});

// ==================================================================
// COLLAPSIBLE SECTIONS
// ==================================================================
function toggleCollapse(el) {{
    const section = el.closest('.collapsible-section') || el.parentElement;
    section.classList.toggle('collapsed');
}}
function expandAll() {{
    document.querySelectorAll('.collapsible-section').forEach(s => s.classList.remove('collapsed'));
    document.querySelectorAll('.channel-block').forEach(s => s.classList.remove('collapsed'));
    // Also remove from channel blocks that use the toggle
    document.querySelectorAll('.channel-block .collapsible-body').forEach(b => b.style.display = '');
}}
function collapseAll() {{
    document.querySelectorAll('#tab-matrix .role-block').forEach(s => s.classList.add('collapsed'));
}}

// Channel title collapse
document.querySelectorAll('.channel-title.collapsible-toggle').forEach(el => {{
    el.addEventListener('click', function() {{
        const block = this.parentElement;
        const body = block.querySelector(':scope > .collapsible-body');
        if (body) {{
            const isHidden = body.style.display === 'none';
            body.style.display = isHidden ? '' : 'none';
            this.querySelector('.collapse-icon').style.transform = isHidden ? '' : 'rotate(-90deg)';
        }}
    }});
}});

// ==================================================================
// CHANNEL NAVIGATION (scroll to)
// ==================================================================
function scrollToChannel(id) {{
    const el = document.getElementById('ch-' + id);
    if (el) {{
        el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        // Flash highlight
        el.style.outline = '2px solid var(--manulife-green)';
        setTimeout(() => el.style.outline = '', 1500);
    }}
}}

// ==================================================================
// CSV EXPORT
// ==================================================================
function exportCSV() {{
    const table = document.getElementById('detail-table');
    const rows = table.querySelectorAll('tr');
    let csv = [];
    rows.forEach(row => {{
        if (row.style.display === 'none') return;
        const cells = Array.from(row.querySelectorAll('th, td'));
        csv.push(cells.map(c => '"' + c.textContent.trim().replace(/"/g, '""') + '"').join(','));
    }});
    const blob = new Blob([csv.join('\\n')], {{ type: 'text/csv' }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dss_mandatory_requirements_export.csv';
    a.click();
    URL.revokeObjectURL(url);
}}

// ==================================================================
// BACK TO TOP
// ==================================================================
window.addEventListener('scroll', function() {{
    const btn = document.getElementById('btn-top');
    btn.classList.toggle('visible', window.scrollY > 300);
}});

// ==================================================================
// KEYBOARD SHORTCUTS
// ==================================================================
document.addEventListener('keydown', function(e) {{
    if (e.ctrlKey && e.key === 'd') {{
        e.preventDefault();
        toggleDarkMode();
    }}
    if (e.ctrlKey && e.key === 'k') {{
        e.preventDefault();
        // Switch to detail tab and focus search
        document.querySelector('[data-tab="detail"]').click();
        setTimeout(() => document.getElementById('flt-search').focus(), 100);
    }}
    if (e.ctrlKey && e.key === 'e') {{
        e.preventDefault();
        exportCSV();
    }}
}});

// ==================================================================
// SVG CHARTS
// ==================================================================
let chartsRendered = false;
function renderCharts() {{
    if (chartsRendered) return;
    chartsRendered = true;
    renderBarChart();
    renderDonutChart();
    renderCodeChart();
    renderHeatmap();
}}

function getThemeColor(cssVar) {{
    return getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
}}

function renderBarChart() {{
    const container = document.getElementById('chart-bar');
    const w = 500, barH = 36, gap = 8, labelW = 60, valW = 40;
    const n = CHART_DATA.length;
    const h = n * (barH + gap) + 40;
    const maxVal = Math.max(...CHART_DATA.map(d => d.total));

    let svg = `<svg width="${{w}}" height="${{h}}" viewBox="0 0 ${{w}} ${{h}}" style="width:100%;max-width:${{w}}px;">`;
    CHART_DATA.forEach((d, i) => {{
        const y = i * (barH + gap) + 20;
        const short = d.channel.split(' - ')[0];
        const mW = (d.mandatory / maxVal) * (w - labelW - valW - 20);
        const oW = (d.optional / maxVal) * (w - labelW - valW - 20);
        svg += `<text x="${{labelW - 4}}" y="${{y + barH/2 + 4}}" text-anchor="end" class="bar-label">${{short}}</text>`;
        svg += `<rect x="${{labelW}}" y="${{y}}" width="${{mW}}" height="${{barH}}" rx="4" fill="#00a758" opacity="0.9">
                    <title>${{d.mandatory}} mandatory</title></rect>`;
        svg += `<rect x="${{labelW + mW}}" y="${{y}}" width="${{oW}}" height="${{barH}}" rx="4" fill="#ff9800" opacity="0.7">
                    <title>${{d.optional}} optional</title></rect>`;
        svg += `<text x="${{labelW + mW + oW + 6}}" y="${{y + barH/2 + 4}}" class="bar-val">${{d.total}}</text>`;
    }});
    // Legend
    const ly = h - 12;
    svg += `<rect x="${{labelW}}" y="${{ly}}" width="12" height="12" rx="2" fill="#00a758"/>`;
    svg += `<text x="${{labelW + 16}}" y="${{ly + 10}}" class="bar-label">Mandatory</text>`;
    svg += `<rect x="${{labelW + 90}}" y="${{ly}}" width="12" height="12" rx="2" fill="#ff9800"/>`;
    svg += `<text x="${{labelW + 106}}" y="${{ly + 10}}" class="bar-label">Optional</text>`;
    svg += '</svg>';
    container.innerHTML = svg;
}}

function renderDonutChart() {{
    const container = document.getElementById('chart-donut');
    const size = 220, cx = size/2, cy = size/2, r = 80, stroke = 28;
    const total = TOTAL_MANDATORY + TOTAL_OPTIONAL;
    const pct = Math.round(TOTAL_MANDATORY / total * 100);
    const circumference = 2 * Math.PI * r;
    const mandArc = (TOTAL_MANDATORY / total) * circumference;

    let svg = `<svg width="${{size}}" height="${{size+40}}" viewBox="0 0 ${{size}} ${{size+40}}">`;
    // Background circle
    svg += `<circle cx="${{cx}}" cy="${{cy}}" r="${{r}}" fill="none" stroke="#e0e0e0" stroke-width="${{stroke}}"/>`;
    // Mandatory arc
    svg += `<circle cx="${{cx}}" cy="${{cy}}" r="${{r}}" fill="none" stroke="#00a758" stroke-width="${{stroke}}"
                stroke-dasharray="${{mandArc}} ${{circumference - mandArc}}"
                stroke-dashoffset="${{circumference/4}}"
                stroke-linecap="round"
                style="transition: stroke-dasharray .8s ease;"/>`;
    // Optional arc
    svg += `<circle cx="${{cx}}" cy="${{cy}}" r="${{r}}" fill="none" stroke="#ff9800" stroke-width="${{stroke}}"
                stroke-dasharray="${{circumference - mandArc}} ${{mandArc}}"
                stroke-dashoffset="${{circumference/4 - mandArc}}"
                stroke-linecap="round"/>`;
    // Center text
    svg += `<text x="${{cx}}" y="${{cy - 6}}" text-anchor="middle" class="donut-label donut-pct">${{pct}}%</text>`;
    svg += `<text x="${{cx}}" y="${{cy + 14}}" text-anchor="middle" class="donut-sub">mandatory</text>`;
    // Bottom legend
    svg += `<text x="${{cx}}" y="${{size + 16}}" text-anchor="middle" class="bar-label">${{TOTAL_MANDATORY}} mandatory &middot; ${{TOTAL_OPTIONAL}} optional &middot; ${{total}} total</text>`;
    svg += '</svg>';
    container.innerHTML = svg;
}}

function renderCodeChart() {{
    const container = document.getElementById('chart-codes');
    const w = 500, barH = 24, gap = 6, labelW = 180, valW = 40;
    const n = CODE_DATA.length;
    const h = n * (barH + gap) + 20;
    const maxVal = Math.max(...CODE_DATA.map(d => d.total));

    let svg = `<svg width="${{w}}" height="${{h}}" viewBox="0 0 ${{w}} ${{h}}" style="width:100%;max-width:${{w}}px;">`;
    CODE_DATA.forEach((d, i) => {{
        const y = i * (barH + gap) + 4;
        const mW = (d.mandatory / maxVal) * (w - labelW - valW - 20);
        const oW = (d.optional / maxVal) * (w - labelW - valW - 20);
        const label = d.code.length > 25 ? d.code.substring(0,23) + '..' : d.code;
        svg += `<text x="${{labelW - 4}}" y="${{y + barH/2 + 4}}" text-anchor="end" class="bar-label" style="font-size:10px;">${{label}}</text>`;
        svg += `<rect x="${{labelW}}" y="${{y}}" width="${{mW}}" height="${{barH}}" rx="3" fill="#00a758" opacity="0.85">
                    <title>${{d.code}}: ${{d.mandatory}} mandatory</title></rect>`;
        svg += `<rect x="${{labelW + mW}}" y="${{y}}" width="${{oW}}" height="${{barH}}" rx="3" fill="#ff9800" opacity="0.7">
                    <title>${{d.code}}: ${{d.optional}} optional</title></rect>`;
        svg += `<text x="${{labelW + mW + oW + 4}}" y="${{y + barH/2 + 4}}" class="bar-val" style="font-size:10px;">${{d.total}}</text>`;
    }});
    svg += '</svg>';
    container.innerHTML = svg;
}}

function renderHeatmap() {{
    const container = document.getElementById('chart-heatmap');
    // Build matrix
    const matrix = {{}};
    let maxCount = 0;
    HEATMAP_DATA.forEach(d => {{
        if (!matrix[d.role]) matrix[d.role] = {{}};
        matrix[d.role][d.channel] = d.count;
        if (d.count > maxCount) maxCount = d.count;
    }});

    const colors = ['#e8f5e9','#a5d6a7','#66bb6a','#43a047','#2e7d32','#1b5e20'];
    function getColor(val) {{
        if (!val) return '#f5f5f5';
        const idx = Math.min(Math.floor((val / maxCount) * (colors.length - 1)), colors.length - 1);
        return colors[idx];
    }}

    let html = '<table class="heatmap-table"><thead><tr><th></th>';
    CHANNELS.forEach(ch => {{
        html += '<th>' + ch.split(' - ')[0] + '</th>';
    }});
    html += '</tr></thead><tbody>';
    ROLES.forEach(role => {{
        html += '<tr><th style="text-align:right;font-size:11px;">' + role + '</th>';
        CHANNELS.forEach(ch => {{
            const v = (matrix[role] && matrix[role][ch]) || 0;
            const bg = getColor(v);
            html += '<td><div class="heatmap-cell" style="background:' + bg + '">' + (v || '&mdash;') + '</div></td>';
        }});
        html += '</tr>';
    }});
    html += '</tbody></table>';
    container.innerHTML = html;
}}

// ==================================================================
// INIT
// ==================================================================
window.addEventListener('DOMContentLoaded', () => {{
    const rows = document.querySelectorAll('#detail-tbody .flat-row');
    document.getElementById('row-count').textContent = rows.length + ' of ' + rows.length + ' rows';

    // Animate progress bars
    setTimeout(() => {{
        document.querySelectorAll('.progress-bar-fill').forEach(bar => {{
            bar.style.width = bar.style.width; // trigger
        }});
    }}, 100);
}});
</script>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def generate(csv_path, out_path):
    """Generate Channel Mandatory Requirements HTML report.
    
    Args:
        csv_path: Path to channel_mandatoryrequirements_finalprod.csv
        out_path: Path for output HTML file
    """
    csv_file = Path(csv_path)
    output_file = Path(out_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Enhanced DSS Channel Mandatory Requirements Report")
    print("=" * 60)

    if not csv_file.exists():
        print(f"ERROR: CSV not found: {csv_file}")
        return False

    df = pd.read_csv(csv_file)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip()

    html_content = build_enhanced_html(df)
    output_file.write_text(html_content, encoding="utf-8")
    print(f"HTML report saved: {output_file}")
    print(f"  Total rows:      {len(df)}")
    print(f"  Channels:        {df['channel_name'].nunique()}")
    print(f"  Contract Types:  {df['contract_type_cd'].nunique()}")
    print(f"  Required Codes:  {df['req_code_name'].nunique()}")
    print(f"  Mandatory (Y):   {(df['mandatory_ind'] == 'Y').sum()}")
    print(f"  Optional (N):    {(df['mandatory_ind'] != 'Y').sum()}")
    print("=" * 60)
    print("Done!")
    return True


def main():
    generate(str(CSV_FILE), str(OUTPUT_FILE))


if __name__ == "__main__":
    main()
