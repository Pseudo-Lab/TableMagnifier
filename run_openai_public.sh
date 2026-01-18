#!/bin/bash

# ==============================================================================
#  TableMagnifier - JSON Pipeline (Public Domain)
# ==============================================================================

# Default Configuration
INPUT_JSON="test_input.json"
OUTPUT_DIR="output_public"
DEFAULT_ARGS="--provider openai --model gpt-5-mini --domain public --qa-only --upload-to-notion"

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
echo "Provider: openai"
echo "Model: gpt-5-mini"
echo "Domain: public"
echo ""

# Check for OPENAI_API_KEY
if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "⚠️  Warning: OPENAI_API_KEY is not set."
    echo "   Please set it in your environment or .env file."
    echo ""
fi

# Run the pipeline
# Note: "$@" appends any remaining arguments, allowing overrides of defaults
uv run python run_pipeline_json.py --input "$INPUT_JSON" --output-dir "$OUTPUT_DIR" $DEFAULT_ARGS "$@"
