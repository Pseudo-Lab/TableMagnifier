#!/bin/bash

# ==============================================================================
#  TableMagnifier - Claude Sonnet (Public Domain)
# ==============================================================================

# Default Configuration
TARGET="data"
DEFAULT_ARGS="--provider claude --model claude-sonnet-4.5 --domain public"

# Check if the first argument is a path (i.e., does not start with '-')
if [[ "$1" != -* ]] && [[ -n "$1" ]]; then
    TARGET="$1"
    shift
fi

echo "=============================================="
echo "  TableMagnifier - Claude Sonnet (Public)"
echo "=============================================="
echo "Target: $TARGET"
echo "Provider: claude"
echo "Model: claude-sonnet-4.5"
echo "Domain: public"
echo ""

# Check for ANTHROPIC_API_KEY
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY is not set."
    echo "   Please set it in your environment or .env file."
    echo ""
fi

# Run the pipeline
# Note: "$@" appends any remaining arguments, allowing overrides of defaults
uv run python -m generate_synthetic_table.cli "$TARGET" $DEFAULT_ARGS "$@"
