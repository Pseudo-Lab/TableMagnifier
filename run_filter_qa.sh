#!/bin/bash

# ==============================================================================
#  TableMagnifier - QA Difficulty Filtering
# ==============================================================================
#
# vLLM 서버를 사용하여 QA 난이도를 측정하고 검수 대상을 필터링합니다.
# 모델이 너무 쉽게 맞추는 문제(90%+)는 제외하고,
# 적당한 난이도(30-60%)의 QA만 검수 리스트로 추출합니다.
#
# Usage:
#   ./run_filter_qa.sh [OPTIONS]
#
# Examples:
#   ./run_filter_qa.sh --domain business
#   ./run_filter_qa.sh --all --trials 5
#   ./run_filter_qa.sh --domain business --vllm-url http://gpu-server:8000/v1
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

vLLM 서버를 사용하여 QA 난이도를 측정하고 검수 대상을 필터링합니다.

Options:
  --domain DOMAIN [...]   필터링할 도메인(들) (business, finance, academic, medical, public)
  --all                   모든 도메인 필터링
  --vllm-url URL          vLLM 서버 URL (default: http://localhost:8000/v1)
  --model MODEL           모델 이름 (미지정시 자동 감지)
  --trials N              각 QA당 시도 횟수 (default: 10)
  --min-acc FLOAT         최소 정확도 (default: 0.3)
  --max-acc FLOAT         최대 정확도 (default: 0.6)
  --limit N               처리할 최대 entry 수 (테스트용)
  --dry-run               실제 추론 없이 확인만
  -h, --help              도움말 표시

Difficulty Categories:
  - too_easy: 90-100% (제외 - 모델이 다 맞춤)
  - easy: 70-89%
  - medium: 30-69% (검수 대상 ✓)
  - hard: 1-29%
  - very_hard: 0%

Examples:
  # business 도메인 필터링
  $0 --domain business

  # 빠른 테스트 (5회 시도, 2개 entry만)
  $0 --domain business --trials 5 --limit 2

  # 외부 vLLM 서버 사용
  $0 --domain business --vllm-url http://gpu-server:8000/v1

Output:
  - qa_difficulty_analysis_*.json: 전체 분석 결과
  - qa_for_review_*.json: 검수용 필터링된 QA 리스트
EOF
}

# Check for help
for arg in "$@"; do
    if [[ "$arg" == "-h" ]] || [[ "$arg" == "--help" ]]; then
        show_help
        exit 0
    fi
done

# Check for required arguments
if [[ $# -eq 0 ]]; then
    show_help
    exit 1
fi

# Parse vllm-url for connection check
VLLM_URL="http://localhost:8000/v1"
for i in $(seq 1 $#); do
    arg="${!i}"
    if [[ "$arg" == "--vllm-url" ]]; then
        next=$((i + 1))
        VLLM_URL="${!next}"
        break
    fi
done

echo "=============================================="
echo "  TableMagnifier - QA Difficulty Filtering"
echo "=============================================="
echo ""

# Check vLLM connection
echo_info "Checking vLLM server connection..."
if curl -s --connect-timeout 5 "${VLLM_URL}/models" > /dev/null 2>&1; then
    MODEL_INFO=$(curl -s "${VLLM_URL}/models" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['data'][0]['id'] if data.get('data') else 'unknown')" 2>/dev/null || echo "unknown")
    echo_info "vLLM server connected. Model: ${MODEL_INFO}"
else
    echo_error "Cannot connect to vLLM server at ${VLLM_URL}"
    echo_error "Please ensure vLLM server is running."
    exit 1
fi

echo ""
echo_info "Starting QA difficulty filtering..."
echo ""

# Run the filter script
uv run python filter_qa_by_difficulty.py "$@"

echo ""
echo_info "Filtering completed!"
echo ""
echo "Generated files:"
echo "  - qa_difficulty_analysis_*.json: Full analysis results"
echo "  - qa_for_review_*.json: Filtered QA for human review"
