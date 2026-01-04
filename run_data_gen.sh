#!/bin/bash

# ==============================================================================
#  TableMagnifier Data Gen (Simplified)
# ==============================================================================

# Default Configuration
TARGET="data"
DEFAULT_ARGS="--provider gemini_pool --model gemini-2.5-flash-lite"

# Check if the first argument is a path (i.e., does not start with '-')
if [[ "$1" != -* ]] && [[ -n "$1" ]]; then
    TARGET="$1"
    shift
fi

echo "Running TableMagnifier on target: '$TARGET'"
echo "Internal Defaults: $DEFAULT_ARGS"

# Run the pipeline
# Note: "$@" appends any remaining arguments, allowing overrides of defaults
uv run python -m generate_synthetic_table.cli "$TARGET" $DEFAULT_ARGS "$@"
