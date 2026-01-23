"""
Capture HTML files from output_* directories as images using Playwright.
"""
import argparse
import asyncio
from pathlib import Path
from typing import List

from playwright.async_api import async_playwright


async def capture_html_file_async(
    html_path: Path,
    output_path: Path,
    width: int = 800,
) -> None:
    """Capture a single HTML file as an image."""
    html_content = html_path.read_text(encoding="utf-8")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport={"width": width, "height": 600})
            await page.set_content(html_content)
            await page.screenshot(path=output_path, full_page=True)
        finally:
            await browser.close()


async def capture_batch_async(
    html_files: List[Path],
    output_dir: Path,
    width: int = 800,
) -> None:
    """Capture multiple HTML files, reusing a single browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for html_path in html_files:
                output_path = output_dir / f"{html_path.stem}.png"
                if output_path.exists():
                    print(f"  [SKIP] {output_path.name} already exists")
                    continue

                try:
                    html_content = html_path.read_text(encoding="utf-8")
                    page = await browser.new_page(viewport={"width": width, "height": 600})
                    await page.set_content(html_content)
                    await page.screenshot(path=output_path, full_page=True)
                    await page.close()
                    print(f"  [OK] {html_path.name} -> {output_path.name}")
                except Exception as e:
                    print(f"  [ERROR] {html_path.name}: {e}")
        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Capture HTML files as images")
    parser.add_argument(
        "--output-dirs",
        nargs="+",
        default=None,
        help="Specific output directories to process (e.g., output_academic output_finance)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=800,
        help="Viewport width for rendering (default: 800)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing images",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent

    # Find output_* directories
    if args.output_dirs:
        output_dirs = [base_dir / d for d in args.output_dirs]
    else:
        output_dirs = sorted(base_dir.glob("output_*"))
        output_dirs = [d for d in output_dirs if d.is_dir()]

    if not output_dirs:
        print("No output_* directories found.")
        return

    print(f"Found {len(output_dirs)} output directories to process")

    for output_dir in output_dirs:
        html_dir = output_dir / "html"
        if not html_dir.exists():
            print(f"\n[SKIP] {output_dir.name}: no html/ subdirectory")
            continue

        # Create images directory
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        html_files = sorted(html_dir.glob("*.html"))
        if not html_files:
            print(f"\n[SKIP] {output_dir.name}: no HTML files found")
            continue

        # Filter out already processed files unless --force
        if not args.force:
            html_files = [
                f for f in html_files
                if not (images_dir / f"{f.stem}.png").exists()
            ]

        if not html_files:
            print(f"\n[SKIP] {output_dir.name}: all files already processed")
            continue

        print(f"\n[Processing] {output_dir.name}: {len(html_files)} HTML files")
        asyncio.run(capture_batch_async(html_files, images_dir, args.width))

    print("\nDone!")


if __name__ == "__main__":
    main()
