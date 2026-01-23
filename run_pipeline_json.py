import argparse
import json
import os
import re
import random
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv


# ============================================================
# Style Variation Configuration
# ============================================================

GOOGLE_FONTS = [
    ("Noto Sans KR", "Noto+Sans+KR:wght@400;500;600;700"),
    ("Pretendard", None),  # Self-hosted or system font
    ("IBM Plex Sans KR", "IBM+Plex+Sans+KR:wght@400;500;600;700"),
    ("Nanum Gothic", "Nanum+Gothic:wght@400;700"),
    ("Nanum Myeongjo", "Nanum+Myeongjo:wght@400;700"),
    ("Gothic A1", "Gothic+A1:wght@400;500;600;700"),
    ("Do Hyeon", "Do+Hyeon"),
    ("Jua", "Jua"),
    ("Gowun Dodum", "Gowun+Dodum"),
    ("Gowun Batang", "Gowun+Batang:wght@400;700"),
]

COLOR_SCHEMES = [
    # (name, header_bg_from, header_bg_to, header_text, header_border, body_hover, body_border, text_color)
    ("indigo", "indigo-600", "indigo-700", "white", "indigo-400", "indigo-50", "slate-200", "slate-700"),
    ("slate", "slate-600", "slate-700", "white", "slate-500", "slate-50", "slate-300", "slate-700"),
    ("emerald", "emerald-600", "emerald-700", "white", "emerald-400", "emerald-50", "slate-200", "slate-700"),
    ("blue", "blue-600", "blue-700", "white", "blue-400", "blue-50", "slate-200", "slate-700"),
    ("purple", "purple-600", "purple-700", "white", "purple-400", "purple-50", "slate-200", "slate-700"),
    ("teal", "teal-600", "teal-700", "white", "teal-400", "teal-50", "slate-200", "slate-700"),
    ("amber", "amber-600", "amber-700", "white", "amber-400", "amber-50", "slate-200", "slate-800"),
    ("rose", "rose-600", "rose-700", "white", "rose-400", "rose-50", "slate-200", "slate-700"),
    ("cyan", "cyan-600", "cyan-700", "white", "cyan-400", "cyan-50", "slate-200", "slate-700"),
    ("stone", "stone-600", "stone-700", "white", "stone-500", "stone-50", "stone-300", "stone-700"),
    # Light header variants
    ("light-blue", "blue-100", "blue-200", "blue-900", "blue-300", "blue-50", "blue-200", "slate-700"),
    ("light-gray", "gray-100", "gray-200", "gray-800", "gray-300", "gray-50", "gray-200", "gray-700"),
    ("light-green", "green-100", "green-200", "green-900", "green-300", "green-50", "green-200", "slate-700"),
]

TABLE_STYLES = [
    # (name, table_extra_classes, has_shadow, has_rounded, stripe_odd)
    ("default", "", False, False, False),
    ("shadow", "shadow-lg", True, False, False),
    ("rounded", "rounded-lg overflow-hidden", False, True, False),
    ("shadow-rounded", "shadow-lg rounded-lg overflow-hidden", True, True, False),
    ("striped", "", False, False, True),
    ("striped-rounded", "rounded-lg overflow-hidden", False, True, True),
]

FONT_SIZES = ["text-xs", "text-sm", "text-base"]


def get_random_style() -> Dict[str, Any]:
    """Generate a random style configuration."""
    font_name, font_url = random.choice(GOOGLE_FONTS)
    color = random.choice(COLOR_SCHEMES)
    table_style = random.choice(TABLE_STYLES)
    font_size = random.choice(FONT_SIZES)

    return {
        "font_name": font_name,
        "font_url": font_url,
        "color_name": color[0],
        "header_bg_from": color[1],
        "header_bg_to": color[2],
        "header_text": color[3],
        "header_border": color[4],
        "body_hover": color[5],
        "body_border": color[6],
        "text_color": color[7],
        "table_style_name": table_style[0],
        "table_extra_classes": table_style[1],
        "has_shadow": table_style[2],
        "has_rounded": table_style[3],
        "stripe_odd": table_style[4],
        "font_size": font_size,
    }


def apply_style_to_html(table_html: str, style: Dict[str, Any]) -> str:
    """Apply style variations to the table HTML by replacing Tailwind classes."""
    html = table_html

    # Replace header gradient colors
    # Pattern: bg-gradient-to-r from-{color}-{shade} to-{color}-{shade}
    html = re.sub(
        r'from-\w+-\d+\s+to-\w+-\d+',
        f'from-{style["header_bg_from"]} to-{style["header_bg_to"]}',
        html
    )

    # Replace header text color
    html = re.sub(
        r'(<thead[^>]*class="[^"]*?)text-white',
        f'\\1text-{style["header_text"]}',
        html
    )

    # Replace header border color
    html = re.sub(
        r'border-\w+-300(?=\s|")',
        f'border-{style["header_border"]}',
        html
    )

    # Replace hover color
    html = re.sub(
        r'hover:bg-\w+-50',
        f'hover:bg-{style["body_hover"]}',
        html
    )

    # Replace body border color
    html = re.sub(
        r'border-slate-200',
        f'border-{style["body_border"]}',
        html
    )

    # Replace text color
    html = re.sub(
        r'text-slate-700',
        f'text-{style["text_color"]}',
        html
    )
    html = re.sub(
        r'text-slate-600',
        f'text-{style["text_color"]}',
        html
    )

    # Replace font size in table tag
    html = re.sub(
        r'(<table[^>]*class="[^"]*?)text-(?:xs|sm|base)',
        f'\\1{style["font_size"]}',
        html
    )

    # Add table extra classes (shadow, rounded)
    if style["table_extra_classes"]:
        html = re.sub(
            r'<table\s+class="([^"]*)"',
            f'<table class="\\1 {style["table_extra_classes"]}"',
            html
        )

    # Add striped rows if enabled
    if style["stripe_odd"]:
        # Add odd:bg-{color}-50 to tr elements in tbody
        html = re.sub(
            r'(<tr[^>]*class="[^"]*hover:bg-)',
            f'<tr class="odd:bg-{style["body_hover"]} hover:bg-',
            html
        )

    return html


def build_html_document(table_html: str, style: Dict[str, Any]) -> str:
    """Build complete HTML document with fonts and styles."""

    # Google Fonts link
    font_link = ""
    if style["font_url"]:
        font_link = f'<link rel="preconnect" href="https://fonts.googleapis.com">\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n    <link href="https://fonts.googleapis.com/css2?family={style["font_url"]}&display=swap" rel="stylesheet">'

    # Font family CSS
    font_css = f"""
    <style>
        body, table, th, td {{
            font-family: '{style["font_name"]}', 'Malgun Gothic', sans-serif;
        }}
    </style>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    {font_link}
    {font_css}
</head>
<body class="bg-white p-4">
{table_html}
</body>
</html>"""

# Add parent directory to path to allow imports if running from root
sys.path.append(str(Path(__file__).parent))

from generate_synthetic_table.runner import run_synthetic_table_flow, _auto_detect_domain
from generate_synthetic_table.flow import TableState
from generate_synthetic_table.notion_uploader import NotionUploader


def save_synthetic_table_as_html(
    synthetic_table: str,
    output_path: Path,
    pair_id: str,
    table_index: int,
    randomize_style: bool = True
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Save synthetic table as HTML file with optional style randomization.

    Args:
        synthetic_table: The HTML table string
        output_path: Directory to save the file
        pair_id: Identifier for the pair
        table_index: Index of the table within the pair
        randomize_style: Whether to apply random style variations

    Returns:
        Tuple of (html_filepath, style_info) or (None, None) if failed
    """
    if not synthetic_table:
        return None, None

    # Clean up markdown code blocks if present
    table_html = synthetic_table
    if table_html.startswith("```html"):
        table_html = table_html[7:]
    if table_html.startswith("```"):
        table_html = table_html[3:]
    if table_html.endswith("```"):
        table_html = table_html[:-3]
    table_html = table_html.strip()

    # Apply style randomization if enabled
    style_info = None
    if randomize_style:
        style_info = get_random_style()
        table_html = apply_style_to_html(table_html, style_info)
        full_html = build_html_document(table_html, style_info)
    else:
        # Basic HTML without style randomization
        full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-white p-4">
{table_html}
</body>
</html>"""

    # Create html subdirectory
    html_dir = output_path / "html"
    html_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    safe_pair_id = "".join([c for c in pair_id if c.isalnum() or c in ('-', '_')])
    html_filename = f"{safe_pair_id}_table_{table_index}.html"
    html_filepath = html_dir / html_filename

    html_filepath.write_text(full_html, encoding="utf-8")

    return str(html_filepath), style_info

def resolve_paths(pair: List[str], data_root: Path) -> List[Path]:
    """Resolves a list of relative paths to absolute Paths."""
    paths = []
    for pid in pair:
        # Prioritize using the path exactly as given in the JSON
        p = Path(pid)
        if p.exists():
            paths.append(p)
            continue
            
        # Fallback: Try joining with data_root if provided (for backward compatibility or convenience)
        p_joined = data_root / pid
        if p_joined.exists():
            paths.append(p_joined)
        else:
            print(f"Warning: File not found: {pid} (checked {p.absolute()} and {p_joined.absolute()})")
            return []
    return paths

def process_single_pair(
    pair_input: Any,
    index: int,
    total_count: int,
    data_root: Path,
    output_dir: Path,
    provider: str,
    model: str,
    config_path: str,
    arg_domain: str,
    qa_only: bool,
    notion_uploader: Any,
    randomize_style: bool = True
) -> Dict:
    """Process a single pair of images."""
    
    # Extract pair info
    if isinstance(pair_input, dict):
        # Structured format
        pair_id_override = pair_input.get("pair_id")
        pair_ids = pair_input.get("image_paths", [])
        domain_override = pair_input.get("domain")
        
        print(f"\n[Pair {index+1}/{total_count}] Processing: {pair_id_override or pair_ids}")
    else:
        # Legacy format (array)
        pair_id_override = None
        pair_ids = pair_input
        domain_override = None
        
        print(f"\n[Pair {index+1}/{total_count}] Processing: {pair_ids}")
    
    paths = resolve_paths(pair_ids, data_root)
    if len(paths) != len(pair_ids):
        print(f"[Pair {index+1}] Skipping due to missing files.")
        return {
            "pair_id": pair_id_override or f"error_{index}",
            "image_paths": pair_ids,
            "error": "Missing files"
        }

    # Detect domain: priority order is domain_override > arg_domain > auto_detect
    domain = domain_override or arg_domain
    if not domain:
        domain = _auto_detect_domain(pair_ids[0])
        if not domain: 
            # fallback try second
            domain = _auto_detect_domain(pair_ids[1]) if len(pair_ids) > 1 else None
    
    # Generate pair_id from override or common path elements
    if pair_id_override:
        pair_id = pair_id_override
    else:
        pair_id = Path(paths[0]).stem if paths else f"pair_{index}"
    
    # Store paths as strings
    image_paths_str = [str(p) for p in paths]
    
    # Initialize result structure
    pair_tables = []
    pair_qa = []
    
    # Logic Branching: Use qa_only flag OR domain-based logic
    should_skip_tables = qa_only or (domain == "public")
    
    try:
        if should_skip_tables:
            # QA only mode
            print(f"[Pair {index+1}] Mode: QA only (tables skipped)")
            
            # QA Generation (Pair)
            qa_state = run_synthetic_table_flow(
                image_path=str(paths[0]),  # Primary path
                image_paths=image_paths_str,
                provider=provider,
                model=model,
                config_path=config_path,
                qa_only=True,
                domain=domain
            )
            
            if qa_state.get("qa_results"):
                pair_qa = qa_state["qa_results"]
            
            pair_tables = [None] * len(paths)
            
        else:
            # Full mode: Both Tables + Pair QA
            print(f"[Pair {index+1}] Mode: Synthetic Table + QA")
            
            # 1. Generate Tables Individually
            temp_tables = []
            for path in paths:
                print(f"  [Pair {index+1}] Generating table for {path.name}...")
                table_state = run_synthetic_table_flow(
                    image_path=str(path),
                    provider=provider,
                    model=model,
                    config_path=config_path,
                    qa_only=False,  # We want the table
                    skip_qa=True,   # Skip QA here - we'll generate QA for the pair later
                    domain=domain
                )
                
                # Check errors
                if table_state.get("errors"):
                    print(f"    [Pair {index+1}] Error generating table: {table_state['errors']}")
                
                # Save synthetic table as HTML file with style randomization
                html_path = None
                style_info = None
                if table_state.get("synthetic_table"):
                    html_path, style_info = save_synthetic_table_as_html(
                        synthetic_table=table_state.get("synthetic_table"),
                        output_path=output_dir,
                        pair_id=pair_id,
                        table_index=len(temp_tables),
                        randomize_style=randomize_style
                    )
                    if html_path:
                        style_desc = f" (font: {style_info['font_name']}, color: {style_info['color_name']})" if style_info else ""
                        print(f"    [Pair {index+1}] Saved HTML: {html_path}{style_desc}")

                # Filter state
                safe_state = {
                    "image_path": str(path),
                    "synthetic_table": table_state.get("synthetic_table"),
                    "synthetic_json": table_state.get("synthetic_json"),
                    "table_summary": table_state.get("table_summary"),
                    "html_path": html_path,
                    "style_info": style_info,  # Store applied style for reference
                }
                temp_tables.append(safe_state)
            
            pair_tables = temp_tables

            # 2. Generate QA for the Pair
            print(f"  [Pair {index+1}] Generating QA for pair...")
            qa_state = run_synthetic_table_flow(
                image_path=str(paths[0]),
                image_paths=image_paths_str,
                provider=provider,
                model=model,
                config_path=config_path,
                qa_only=True,  # Focus on QA from these images
                domain=domain
            )
                
            if qa_state.get("qa_results"):
                pair_qa = qa_state["qa_results"]

        # Create structured result with keys
        result_item = {
            "pair_id": pair_id,
            "image_paths": image_paths_str,
            "domain": domain,
            "tables": pair_tables,
            "qa_results": pair_qa,
            "metadata": {
                "provider": provider,
                "model": model,
                "qa_only": should_skip_tables
            }
        }
        
        # Upload to Notion if enabled
        if notion_uploader and pair_qa:
            try:
                print(f"  [Pair {index+1}] Uploading to Notion database...")
                upload_result = notion_uploader.upload_qa_result(
                    domain=domain or "unknown",
                    image_path=pair_id,  # Use pair_id as identifier
                    qa_results=pair_qa,
                    provider=provider
                )
                result_item["notion_upload"] = {
                    "success": True,
                    "created_count": upload_result.get("created_count", 0)
                }
                print(f"  ✅ [Pair {index+1}] Uploaded {upload_result.get('created_count', 0)} QA rows to Notion")
            except Exception as e:
                result_item["notion_upload"] = {
                    "success": False,
                    "error": str(e)
                }
                print(f"  ❌ [Pair {index+1}] Notion upload failed: {e}")
        
        return result_item

    except Exception as e:
        print(f"❌ [Pair {index+1}] Critical error: {e}")
        return {
            "pair_id": pair_id,
            "image_paths": image_paths_str,
            "error": str(e)
        }

def run_pipeline(
    json_input: List[List[str]],
    data_root: Path,
    output_dir: Path,
    provider: str = "gemini_pool",
    model: str = "gemini-2.5-flash",
    config_path: str = "apis/gemini_keys.yaml",
    arg_domain: str = None,
    qa_only: bool = False,
    upload_to_notion: bool = False,
    max_workers: int = 3,
    randomize_style: bool = True
):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize Notion uploader if needed
    notion_uploader = None
    if upload_to_notion:
        try:
            notion_uploader = NotionUploader(config_path=config_path)
            print("✅ Notion uploader initialized")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize Notion uploader: {e}")
            print("   Continuing without Notion upload...")
    
    final_results = []
    total_count = len(json_input)
    
    print(f"Starting pipeline with {max_workers} workers for {total_count} pairs...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create futures
        futures = {
            executor.submit(
                process_single_pair,
                item,
                i,
                total_count,
                data_root,
                output_dir,
                provider,
                model,
                config_path,
                arg_domain,
                qa_only,
                notion_uploader,
                randomize_style
            ): i for i, item in enumerate(json_input)
        }
        
        # Collect results as they finish
        for future in as_completed(futures):
            i = futures[future]
            try:
                result = future.result()
                final_results.append(result)
                
                # Save intermediate per pair (optional)
                # pair_id = result.get("pair_id", f"pair_{i}")
                # safe_name = "".join([c for c in pair_id if c.isalnum() or c in ('-','_')])
                # (output_dir / f"{safe_name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                
            except Exception as e:
                print(f"❌ Failed to process pair index {i}: {e}")

    # Sort results by original index for consistency (optional but nice)
    # Note: final_results might process out of order. If we want original order, we'd need to track it better,
    # but strictly speaking JSON lists don't guarantee order if we are just dumping a collection. 
    # Let's just dump.
    
    # Save Final JSON
    output_file = output_dir / "pipeline_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    
    print(f"\nPipeline Complete. Saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Run Table/QA pipeline from JSON input")
    parser.add_argument("--input", required=True, help="Path to JSON input file or JSON string")
    parser.add_argument("--data-root", default="data", help="Root directory to scan for images")
    parser.add_argument("--output-dir", default="output_json", help="Directory to save results")
    parser.add_argument("--provider", default="gemini_pool", help="LLM provider (default: gemini_pool)")
    parser.add_argument("--model", default="gemini-1.5-flash", help="Model name (default: gemini-1.5-flash)")
    parser.add_argument("--config-path", default="apis/gemini_keys.yaml", help="Path to gemini_keys.yaml")
    parser.add_argument("--domain", help="Force specific domain")
    parser.add_argument("--qa-only", action="store_true", help="Skip table generation, only generate QA (applies to all domains)")
    parser.add_argument("--upload-to-notion", action="store_true", help="Upload QA results to Notion database")
    parser.add_argument("--max-workers", type=int, default=3, help="Maximum number of parallel workers (default: 3)")
    parser.add_argument("--randomize-style", action="store_true", default=True, help="Randomize HTML table styles (fonts, colors) for diversity (default: True)")
    parser.add_argument("--no-randomize-style", dest="randomize_style", action="store_false", help="Disable style randomization")
    parser.add_argument("--limit", type=int, help="Limit number of entries to process (for testing)")

    args = parser.parse_args()

    # Parse JSON input
    input_data = []
    if os.path.isfile(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    else:
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            print("Error: Input is neither a valid file path nor a valid JSON string.")
            return

    # Validate structure roughly
    if not isinstance(input_data, list):
        print("Error: Input JSON must be a list of pairs.")
        return

    # Apply limit if specified
    if args.limit:
        input_data = input_data[:args.limit]
        print(f"Limited to {len(input_data)} entries")

    data_root = Path(args.data_root)
    output_dir = Path(args.output_dir)

    run_pipeline(
        json_input=input_data,
        data_root=data_root,
        output_dir=output_dir,
        provider=args.provider,
        model=args.model,
        config_path=args.config_path,
        arg_domain=args.domain,
        qa_only=args.qa_only,
        upload_to_notion=args.upload_to_notion,
        max_workers=args.max_workers,
        randomize_style=args.randomize_style
    )

if __name__ == "__main__":
    main()
