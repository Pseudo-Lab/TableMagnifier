#!/bin/bash

# ==============================================================================
#  HTML to Image Capture Script
#  Captures HTML files from output_*/html/ directories as PNG images
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==================================="
echo " HTML to Image Capture"
echo "==================================="

# Check if playwright is installed
if ! uv run python -c "import playwright" 2>/dev/null; then
    echo "[INFO] Installing playwright..."
    uv add playwright
    uv run playwright install chromium
fi

# Run the capture script
uv run python "$SCRIPT_DIR/capture_html_images.py" "$@"
