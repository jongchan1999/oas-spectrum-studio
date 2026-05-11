#!/usr/bin/env python
"""CLI: pull raw CL submissions from Supabase, curate into a release pack.

Usage:
    # Default: release_id = current UTC timestamp
    python scripts/curate.py

    # Pin a release tag (recommended for promoted releases)
    python scripts/curate.py --release-id v2

    # Trial run — fetches everything but never PATCHes statuses, no DB writes
    python scripts/curate.py --dry-run

Required env vars:
    SUPABASE_URL                  e.g. https://abc.supabase.co
    SUPABASE_SERVICE_ROLE_KEY     service-role JWT
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running directly from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oas_web.curation import CurationError, run_curation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--release-id", default=None,
        help="Release identifier. Defaults to a UTC timestamp.",
    )
    parser.add_argument(
        "--output-root", default="curated",
        help="Directory under which the release pack is written (default: ./curated).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip PATCH calls; report what would happen.",
    )
    args = parser.parse_args()

    release_id = args.release_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_root)

    print(f"[curate] release_id={release_id}  output_root={output_root}  dry_run={args.dry_run}")
    try:
        stats = run_curation(release_id=release_id, output_root=output_root, dry_run=args.dry_run)
    except CurationError as exc:
        print(f"[curate] FAILED: {exc}", file=sys.stderr)
        return 1

    print("\n[curate] summary")
    print(f"  scanned          {stats['scanned']}")
    print(f"  accepted         {stats['accepted']}")
    print(f"  rejected         {stats['rejected']}")
    print(f"  duplicates       {stats['duplicates']}")
    print(f"  dataset_path     {stats['dataset_path']}")
    print(f"  manifest_path    {stats['manifest_path']}")
    print(f"  report_path      {stats['report_path']}")
    if stats["method_counts"]:
        print("  by method:")
        for method, count in stats["method_counts"].items():
            print(f"    {method:<22} {count}")
    if stats["rejection_reasons"]:
        print("  rejection reasons:")
        for reason, count in stats["rejection_reasons"].items():
            print(f"    {reason:<40} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
