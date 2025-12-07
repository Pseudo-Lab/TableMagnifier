"""
Utility to capture HTML content as an image using Playwright.
"""
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright


async def capture_html_as_image_async(
    html_content: str,
    output_path: str | Path,
    width: int = 800,
) -> None:
    """
    Render HTML content and save it as an image using Playwright (async).

    Args:
        html_content: The HTML string to render.
        output_path: Path to save the image to.
        width: Viewport width (default: 800). Height is automatic.
    """
    output_path = Path(output_path)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            # Create a new page
            page = await browser.new_page(viewport={"width": width, "height": 600})
            
            # Set content
            await page.set_content(html_content)
            
            # Wait for a bit to ensure rendering (optional, but good for fonts/styles)
            # await page.wait_for_timeout(100) 

            # Take screenshot of the full page content
            # We can target the table specifically if we want, but full page is safer for now.
            # If the content is just the table, full_page=True works well.
            await page.screenshot(path=output_path, full_page=True)
            
        finally:
            await browser.close()


def capture_html_as_image(
    html_content: str,
    output_path: str | Path,
    width: int = 800,
) -> None:
    """
    Render HTML content and save it as an image using Playwright (sync wrapper).
    """
    asyncio.run(capture_html_as_image_async(html_content, output_path, width))
