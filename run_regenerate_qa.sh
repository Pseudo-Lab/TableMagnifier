#!/bin/bash

# ==============================================================================
#  TableMagnifier - QA Regeneration Script
# ==============================================================================
#
# 기존 synthetic 테이블에서 QA를 재생성합니다.
# output_public은 제외됩니다.
#
# Usage:
#   ./run_regenerate_qa.sh [OPTIONS]
#
# Examples:
#   ./run_regenerate_qa.sh --all                    # 모든 도메인
#   ./run_regenerate_qa.sh --domain business        # 특정 도메인
#   ./run_regenerate_qa.sh --domain business finance # 여러 도메인
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

기존 synthetic 테이블에서 QA를 재생성합니다.

Options:
  --domain DOMAIN [DOMAIN ...]   재생성할 도메인(들) (business, finance, academic, medical)
  --all                          모든 도메인 재생성 (output_public 제외)
  --provider PROVIDER            LLM 제공자 (claude, openai, gemini) (default: claude)
  --model MODEL                  모델 이름 (default: claude-sonnet-4-5)
  --no-long-sequence             long_sequence QA 생성 스킵
  --limit N                      처리할 최대 entry 수 (테스트용)
  --dry-run                      실제 재생성 없이 확인만
  -h, --help                     도움말 표시

Examples:
  # 모든 도메인 재생성
  $0 --all

  # business 도메인만
  $0 --domain business

  # OpenAI 사용
  $0 --domain business --provider openai --model gpt-4o

  # 테스트 (5개만)
  $0 --domain business --limit 5

  # Dry run
  $0 --all --dry-run
EOF
}

# Check for required arguments
if [[ $# -eq 0 ]]; then
    show_help
    exit 1
fi

# Check for help flag
for arg in "$@"; do
    if [[ "$arg" == "-h" ]] || [[ "$arg" == "--help" ]]; then
        show_help
        exit 0
    fi
done

# Check API keys
check_api_keys() {
    local provider="$1"
    case $provider in
        claude|anthropic)
            if [[ -z "$ANTHROPIC_API_KEY" ]]; then
                echo_warn "ANTHROPIC_API_KEY is not set"
            fi
            ;;
        openai)
            if [[ -z "$OPENAI_API_KEY" ]]; then
                echo_warn "OPENAI_API_KEY is not set"
            fi
            ;;
        gemini|google)
            if [[ -z "$GOOGLE_API_KEY" ]]; then
                echo_warn "GOOGLE_API_KEY is not set"
            fi
            ;;
    esac
}

# Parse provider from arguments
PROVIDER="claude"
for i in "${!@}"; do
    if [[ "${!i}" == "--provider" ]]; then
        next=$((i + 1))
        PROVIDER="${!next}"
        break
    fi
done

check_api_keys "$PROVIDER"

echo "=============================================="
echo "  TableMagnifier - QA Regeneration"
echo "=============================================="
echo ""

# Run the regeneration script
uv run python regenerate_qa.py "$@"
