#!/bin/bash

# ==============================================================================
#  TableMagnifier - JSON Pipeline (Public Domain)
# ==============================================================================

# Default Configuration
INPUT_JSON="test_business.json"
OUTPUT_DIR="output_business"
DEFAULT_ARGS="--provider claude --model claude-sonnet-4-5 --domain business"

# Check if the first argument is a JSON file path
if [[ "$1" == *.json ]]; then
    INPUT_JSON="$1"
    shift
fi

echo "=============================================="
echo "  TableMagnifier - JSON Pipeline (Public)"
echo "=============================================="
echo "Input JSON: $INPUT_JSON"
echo "Output Dir: $OUTPUT_DIR"
echo "Provider: claude"
echo "Model: claude-sonnet-4-5"
echo "Domain: business"
echo ""
echo "💡 Tip: To upload to Notion during pipeline execution:"
echo "   Add --upload-to-notion flag to the command"
echo ""
echo "💡 To upload existing results later:"
echo "   python upload_to_notion_from_json.py $OUTPUT_DIR"
echo ""

# Check for ANTHROPIC_API_KEY
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY is not set."
    echo "   Please set it in your environment or .env file."
    echo ""
fi

# Run the pipeline
# Note: "$@" appends any remaining arguments, allowing overrides of defaults
uv run python run_pipeline_json.py --input "$INPUT_JSON" --output-dir "$OUTPUT_DIR" $DEFAULT_ARGS "$@"