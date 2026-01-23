#!/bin/bash

# ==============================================================================
#  TableMagnifier - JSON Pipeline
# ==============================================================================
#
# Usage:
#   ./run_pipeline.sh [INPUT_JSON] [OPTIONS]
#
# Examples:
#   ./run_pipeline.sh test_public.json --domain public
#   ./run_pipeline.sh test_business.json --domain business --provider openai
#   ./run_pipeline.sh --input data.json --output-dir output_custom
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default Configuration
INPUT_JSON=""
OUTPUT_DIR=""
PROVIDER="claude"
MODEL="claude-sonnet-4-5"
DOMAIN="public"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    cat << EOF
Usage: $0 [INPUT_JSON] [OPTIONS]

TableMagnifier JSON Pipeline Runner

Arguments:
  INPUT_JSON              Input JSON file path (optional, can use --input instead)

Options:
  --input FILE            Input JSON file
  --output-dir DIR        Output directory (default: output_{domain})
  --provider PROVIDER     LLM provider: claude, openai, gemini (default: claude)
  --model MODEL           Model name (default: claude-sonnet-4-5)
  --domain DOMAIN         Domain: public, business, finance, medical, academic (default: public)
  --qa-only               Generate QA only (skip table generation)
  --skip-qa               Skip QA generation (table only)
  --upload-to-notion      Upload results to Notion
  -h, --help              Show this help

Examples:
  # Public domain with Claude
  $0 test_public.json --domain public

  # Business domain with OpenAI
  $0 test_business.json --domain business --provider openai --model gpt-4o

  # Finance domain, QA only mode
  $0 test_finance.json --domain finance --qa-only

  # Custom output directory
  $0 data.json --output-dir my_output --domain medical
EOF
}

# Parse first argument as JSON file if it ends with .json
if [[ "$1" == *.json ]]; then
    INPUT_JSON="$1"
    shift
fi

# Parse remaining arguments
EXTRA_ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_JSON="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Set default output directory based on domain
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="output_${DOMAIN}"
fi

# Validate input
if [[ -z "$INPUT_JSON" ]]; then
    echo -e "${YELLOW}[WARN]${NC} No input JSON specified."
    show_help
    exit 1
fi

if [[ ! -f "$INPUT_JSON" ]]; then
    echo -e "${YELLOW}[ERROR]${NC} Input file not found: $INPUT_JSON"
    exit 1
fi

echo "=============================================="
echo "  TableMagnifier - JSON Pipeline"
echo "=============================================="
echo "Input JSON: $INPUT_JSON"
echo "Output Dir: $OUTPUT_DIR"
echo "Provider:   $PROVIDER"
echo "Model:      $MODEL"
echo "Domain:     $DOMAIN"
echo ""

# Check API keys based on provider
case $PROVIDER in
    claude|anthropic)
        if [[ -z "$ANTHROPIC_API_KEY" ]]; then
            echo -e "${YELLOW}[WARN]${NC} ANTHROPIC_API_KEY is not set."
        fi
        ;;
    openai)
        if [[ -z "$OPENAI_API_KEY" ]]; then
            echo -e "${YELLOW}[WARN]${NC} OPENAI_API_KEY is not set."
        fi
        ;;
    gemini|google)
        if [[ -z "$GOOGLE_API_KEY" ]]; then
            echo -e "${YELLOW}[WARN]${NC} GOOGLE_API_KEY is not set."
        fi
        ;;
esac

echo -e "${GREEN}[INFO]${NC} Starting pipeline..."
echo ""

# Run the pipeline
uv run python run_pipeline_json.py \
    --input "$INPUT_JSON" \
    --output-dir "$OUTPUT_DIR" \
    --provider "$PROVIDER" \
    --model "$MODEL" \
    --domain "$DOMAIN" \
    $EXTRA_ARGS

echo ""
echo -e "${GREEN}[INFO]${NC} Pipeline completed. Results saved to: $OUTPUT_DIR/"
echo ""
echo "To upload results to Notion:"
echo "   python upload_to_notion_from_json.py $OUTPUT_DIR"
