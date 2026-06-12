#!/usr/bin/env python3
"""
DSS Reports — Main Launcher
============================
Generate interactive HTML dashboards from DSS data exports.

Usage:
    python run.py --all          Generate all reports
    python run.py --advisors     Advisors by Channel report
    python run.py --mandatory    Channel Mandatory Requirements report
    python run.py --entity       Entity Classification report
    python run.py --serve        Start HTTP server to view reports
    python run.py --serve 9000   Start on specific port
"""

import argparse
import functools
import http.server
import os
import sys
import shutil
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
STATIC_DIR = PROJECT_ROOT / "static"


def ensure_dirs():
    """Create data/ and output/ directories if missing."""
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def run_mandatory():
    """Generate Channel Mandatory Requirements report."""
    from reports.channel_mandatory_requirements import generate
    csv_path = DATA_DIR / "channel_mandatoryrequirements.csv"
    out_path = OUTPUT_DIR / "channel_mandatoryrequirements.html"
    if not csv_path.exists():
        print(f"ERROR: Input file not found: {csv_path}")
        print(f"  Place channel_mandatoryrequirements.csv in {DATA_DIR}")
        return False
    generate(str(csv_path), str(out_path))
    return True



def serve_reports(port=8800):
    """Start HTTP server to browse generated reports."""
    if not OUTPUT_DIR.exists() or not any(OUTPUT_DIR.glob("*.html")):
        print(f"No reports found in {OUTPUT_DIR}. Generate reports first with --all")
        return

    # Copy styled index from static/ and fix links to match output filenames
    static_index = STATIC_DIR / "index.html"
    index_path = OUTPUT_DIR / "index.html"

    if static_index.exists():
        html = static_index.read_text(encoding="utf-8")
        # Map static hrefs → actual output filenames
        link_map = {
            'href="Code_Matrix.html"':          'href="channel_mandatoryrequirements.html"',
            
        }
        for old, new in link_map.items():
            html = html.replace(old, new)
        index_path.write_text(html, encoding="utf-8")
    else:
        # Fallback: auto-generate a simple index
        reports = sorted(f for f in OUTPUT_DIR.glob("*.html") if f.name != "index.html")
        body = "".join(
            f'<a href="./{r.name}">{r.stem.replace("_"," ").title()}</a>' for r in reports
        )
        index_path.write_text(
            f"<!DOCTYPE html><html><body>{body}</body></html>", encoding="utf-8"
        )

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUTPUT_DIR))
    server = http.server.HTTPServer(("0.0.0.0", port), handler)
    url = f"http://localhost:{port}"
    print(f"\n  DSS Reports Server running at {url}")
    print(f"  Serving from: {OUTPUT_DIR}")
    print(f"  Press Ctrl+C to stop\n")

    try:
        webbrowser.open(url)
    except:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


def prepare_dynamic():
    """Prepare dynamic HTML files: copy CSVs into static/data/ and generate entity JSON."""
    data_dest = STATIC_DIR / "data"
    data_dest.mkdir(parents=True, exist_ok=True)

    # Copy CSV files
    csv_files = [
        ("Advisors_by_Channel.csv", "Advisors CSV"),
        ("channel_mandatoryrequirements_finalprod.csv", "Mandatory Requirements CSV"),
    ]
    for fname, label in csv_files:
        src = DATA_DIR / fname
        dst = data_dest / fname
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  Copied: {label} ({src.stat().st_size / 1024 / 1024:.1f} MB)")
        else:
            print(f"  WARNING: {src} not found — {label} will not load")

    # Generate entity classification JSON
    ddl_path = DATA_DIR / "tables.sql"
    if ddl_path.exists():
        from reports.generate_entity_json import generate as gen_json
        gen_json(str(ddl_path), str(data_dest / "entity_classification.json"))
    else:
        print(f"  WARNING: {ddl_path} not found — Entity Classification will not load")

    print(f"\n  Dynamic files ready in: {STATIC_DIR}")
    return True


def serve_dynamic(port=8800):
    """Serve the static/ directory (dynamic HTML files that fetch data at runtime)."""
    if not STATIC_DIR.exists() or not any(STATIC_DIR.glob("*.html")):
        print(f"No HTML files in {STATIC_DIR}. Run with --dynamic first.")
        return

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(STATIC_DIR))
    server = http.server.HTTPServer(("0.0.0.0", port), handler)
    url = f"http://localhost:{port}"
    print(f"\n  DSS Dynamic Reports Server running at {url}")
    print(f"  Serving from: {STATIC_DIR}")
    print(f"  Press Ctrl+C to stop\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="DSS Reports — Generate interactive HTML dashboards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --all              Generate all reports
  python run.py --advisors         Advisors by Channel only
  python run.py --serve            Start dashboard server (port 8800)
  python run.py --serve 9000       Start on port 9000
  python run.py --all --serve      Generate all, then serve
        """,
    )
    parser.add_argument("--all", action="store_true", help="Generate all reports")
    parser.add_argument("--mandatory", action="store_true", help="Generate Channel Mandatory Requirements report")
    parser.add_argument("--serve", nargs="?", const=8800, type=int, metavar="PORT",
                        help="Start HTTP server (default port 8800)")
    parser.add_argument("--dynamic", nargs="?", const=8800, type=int, metavar="PORT",
                        help="Prepare & serve dynamic HTML reports (IIS-style, default port 8800)")

    args = parser.parse_args()

    if not any([args.all, args.advisors, args.mandatory, args.entity, args.hierarchy, args.serve, args.dynamic is not None]):
        parser.print_help()
        return

    ensure_dirs()
    results = []


    if args.all or args.mandatory:
        print("=" * 60)
        print("  Generating: Channel Mandatory Requirements")
        print("=" * 60)
        results.append(("Channel Mandatory Requirements", run_mandatory()))


    if results:
        print("\n" + "=" * 60)
        print("  Summary")
        print("=" * 60)
        for name, ok in results:
            icon = "OK" if ok else "FAIL"
            print(f"  [{icon}] {name}")
        print(f"\n  Reports saved to: {OUTPUT_DIR}\n")

    if args.serve is not None:
        serve_reports(args.serve)

    if args.dynamic is not None:
        print("=" * 60)
        print("  Preparing dynamic HTML reports")
        print("=" * 60)
        prepare_dynamic()
        serve_dynamic(args.dynamic)


if __name__ == "__main__":
    main()
