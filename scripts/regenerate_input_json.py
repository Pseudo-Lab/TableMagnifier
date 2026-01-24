#!/usr/bin/env python3
"""
Regenerate single_table_{domain}_input.json from actual files in data/{Domain}/Table/
"""

import json
import re
from pathlib import Path
from typing import Optional

# Domain configurations
DOMAIN_CONFIG = {
    "finance": {"prefix": "F", "folder": "Finance"},
    "business": {"prefix": "B", "folder": "Business"},
    "academic": {"prefix": "A", "folder": "Academic"},
    "medical": {"prefix": "M", "folder": "Medical"},
    "public": {"prefix": "P", "folder": "Public"},
    "insurance": {"prefix": "I", "folder": "Insurance"},
}


def natural_sort_key(s: str):
    """Sort strings with numbers naturally (e.g., F_origin_2 before F_origin_10)"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', str(s))]


def regenerate_input_json(
    domain: str,
    data_root: Path,
    output_path: Path,
    dry_run: bool = False
) -> int:
    """
    Scan data/{Domain}/Table/ and regenerate input JSON.

    Returns:
        Number of entries generated
    """
    config = DOMAIN_CONFIG.get(domain.lower())
    if not config:
        raise ValueError(f"Unknown domain: {domain}. Available: {list(DOMAIN_CONFIG.keys())}")

    prefix = config["prefix"]
    folder = config["folder"]
    table_dir = data_root / folder / "Table"

    if not table_dir.exists():
        raise FileNotFoundError(f"Table directory not found: {table_dir}")

    # Collect all PNG files
    entries = []

    # Get all origin directories
    origin_dirs = sorted(
        [d for d in table_dir.iterdir() if d.is_dir()],
        key=lambda x: natural_sort_key(x.name)
    )

    for origin_dir in origin_dirs:
        origin = origin_dir.name

        # Get all PNG files in this origin directory
        png_files = sorted(
            origin_dir.glob("*.png"),
            key=lambda x: natural_sort_key(x.name)
        )

        for png_file in png_files:
            table_id = png_file.stem  # filename without extension

            # Build relative path from project root
            rel_path = f"data/{folder}/Table/{origin}/{png_file.name}"

            entry = {
                "index": len(entries),
                "pair_id": f"{origin}_{table_id}",
                "image_paths": [rel_path],
                "domain": folder,
                "origin": origin,
                "table_id": table_id
            }
            entries.append(entry)

    if dry_run:
        print(f"[DRY RUN] Would generate {len(entries)} entries")
        print(f"[DRY RUN] Output path: {output_path}")
        print(f"\nFirst 5 entries:")
        for entry in entries[:5]:
            print(f"  - {entry['pair_id']}: {entry['image_paths'][0]}")
        if len(entries) > 5:
            print(f"  ... and {len(entries) - 5} more")
        return len(entries)

    # Write JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(entries)} entries -> {output_path}")
    return len(entries)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Regenerate single table input JSON from actual files")
    parser.add_argument("--domain", "-d", required=True,
                       choices=list(DOMAIN_CONFIG.keys()),
                       help="Domain to regenerate")
    parser.add_argument("--data-root", "-r", type=Path, default=Path("data"),
                       help="Data root directory (default: data)")
    parser.add_argument("--output", "-o", type=Path, default=None,
                       help="Output JSON path (default: single_image_json_list/single_table_{domain}_input.json)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be generated without writing")
    parser.add_argument("--all", action="store_true",
                       help="Regenerate all domains")

    args = parser.parse_args()

    # Find project root (where data/ and single_image_json_list/ are)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_root = project_root / args.data_root

    if args.all:
        domains = list(DOMAIN_CONFIG.keys())
    else:
        domains = [args.domain]

    total = 0
    for domain in domains:
        config = DOMAIN_CONFIG[domain]

        if args.output and len(domains) == 1:
            output_path = args.output
        else:
            output_path = project_root / "single_image_json_list" / f"single_table_{domain}_input.json"

        try:
            count = regenerate_input_json(
                domain=domain,
                data_root=data_root,
                output_path=output_path,
                dry_run=args.dry_run
            )
            total += count
        except FileNotFoundError as e:
            print(f"[SKIP] {domain}: {e}")

    print(f"\nTotal: {total} entries")


if __name__ == "__main__":
    main()
