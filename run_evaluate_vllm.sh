#!/bin/bash
#
# vLLM 서버를 사용한 Table QA 평가 스크립트
#
# 사전 요구사항:
#   1. vLLM 서버가 실행 중이어야 합니다
#   2. HTML 파일들이 이미지로 캡처되어 있어야 합니다 (./run_capture_html.sh 실행)
#
# Usage:
#   ./run_evaluate_vllm.sh [OPTIONS]
#
# Examples:
#   # 모든 도메인 평가
#   ./run_evaluate_vllm.sh --all-domains
#
#   # 단일 도메인 평가
#   ./run_evaluate_vllm.sh --domain public
#
#   # 커스텀 vLLM URL
#   ./run_evaluate_vllm.sh --domain public --vllm-url http://gpu-server:8000/v1
#
#   # 특정 모델 사용
#   ./run_evaluate_vllm.sh --domain business --model Qwen/Qwen2.5-VL-7B-Instruct
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 기본 설정
VLLM_URL="${VLLM_URL:-http://localhost:8000/v1}"
MODEL="${MODEL:-default}"
OUTPUT_DIR="${OUTPUT_DIR:-eval_results}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 헬프 메시지
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

vLLM 서버를 사용한 Table QA 평가

Options:
  --domain DOMAIN       평가할 도메인 (academic, business, finance, medical, public)
  --all-domains         모든 도메인 평가
  --vllm-url URL        vLLM 서버 URL (default: $VLLM_URL)
  --model MODEL         사용할 모델 이름 (default: $MODEL)
  --output-dir DIR      결과 저장 디렉토리 (default: $OUTPUT_DIR)
  --use-judge           LLM-as-Judge 평가 사용
  --judge-model MODEL   Judge 모델 (default: gpt-4o-mini)
  --limit N             평가할 최대 샘플 수 (디버깅용)
  --qa-types TYPES      특정 QA 타입만 평가 (예: "lookup compare")
  --capture-html        평가 전 HTML을 이미지로 캡처
  -h, --help            이 도움말 표시

Environment Variables:
  VLLM_URL              vLLM 서버 URL
  MODEL                 사용할 모델 이름
  OUTPUT_DIR            결과 저장 디렉토리
  OPENAI_API_KEY        LLM-as-Judge 사용 시 OpenAI API 키

Examples:
  # 모든 도메인 평가
  $0 --all-domains

  # public 도메인만 평가
  $0 --domain public

  # LLM-as-Judge 포함 평가
  $0 --domain finance --use-judge --judge-model gpt-4o

  # 10개 샘플로 빠른 테스트
  $0 --domain public --limit 10
EOF
}

# vLLM 서버 연결 확인
check_vllm_connection() {
    local url=$1
    echo_info "vLLM 서버 연결 확인: $url"

    # /v1/models 엔드포인트로 연결 테스트
    if curl -s --connect-timeout 5 "$url/models" > /dev/null 2>&1; then
        echo_info "vLLM 서버 연결 성공"
        return 0
    else
        echo_error "vLLM 서버에 연결할 수 없습니다: $url"
        echo_error "vLLM 서버가 실행 중인지 확인하세요."
        return 1
    fi
}

# 이미지 디렉토리 확인
check_images() {
    local domains=("academic" "business" "finance" "medical" "public")
    local missing=0

    for domain in "${domains[@]}"; do
        local output_dir="output_${domain}"
        local images_dir="${output_dir}/images"

        if [[ -d "$output_dir" ]]; then
            if [[ ! -d "$images_dir" ]] || [[ -z "$(ls -A "$images_dir" 2>/dev/null)" ]]; then
                echo_warn "$domain: 이미지 디렉토리가 비어있거나 없습니다 ($images_dir)"
                ((missing++))
            fi
        fi
    done

    if [[ $missing -gt 0 ]]; then
        echo_warn "일부 도메인에 이미지가 없습니다. HTML 캡처가 필요할 수 있습니다."
        echo_warn "실행: ./run_capture_html.sh"
    fi
}

# 인자 파싱
DOMAIN=""
ALL_DOMAINS=false
CAPTURE_HTML=false
USE_JUDGE=false
JUDGE_MODEL=""
LIMIT=""
QA_TYPES=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --all-domains)
            ALL_DOMAINS=true
            shift
            ;;
        --vllm-url)
            VLLM_URL="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --use-judge)
            USE_JUDGE=true
            shift
            ;;
        --judge-model)
            JUDGE_MODEL="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --qa-types)
            QA_TYPES="$2"
            shift 2
            ;;
        --capture-html)
            CAPTURE_HTML=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo_error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
done

# 인자 검증
if [[ -z "$DOMAIN" ]] && [[ "$ALL_DOMAINS" != true ]]; then
    echo_error "--domain 또는 --all-domains를 지정해야 합니다."
    show_help
    exit 1
fi

# HTML 캡처 (옵션)
if [[ "$CAPTURE_HTML" == true ]]; then
    echo_info "HTML 파일을 이미지로 캡처합니다..."
    if [[ -f "./run_capture_html.sh" ]]; then
        ./run_capture_html.sh
    else
        echo_warn "run_capture_html.sh를 찾을 수 없습니다. 스킵합니다."
    fi
fi

# vLLM 연결 확인
check_vllm_connection "$VLLM_URL" || exit 1

# 이미지 확인
check_images

# 평가 명령어 구성
CMD="uv run python -m eval.evaluate_vllm"
CMD="$CMD --vllm-url $VLLM_URL"
CMD="$CMD --model $MODEL"
CMD="$CMD --output-dir $OUTPUT_DIR"

if [[ "$ALL_DOMAINS" == true ]]; then
    CMD="$CMD --all-domains"
elif [[ -n "$DOMAIN" ]]; then
    CMD="$CMD --domain $DOMAIN"
fi

if [[ "$USE_JUDGE" == true ]]; then
    CMD="$CMD --use-judge"
    if [[ -n "$JUDGE_MODEL" ]]; then
        CMD="$CMD --judge-model $JUDGE_MODEL"
    fi
fi

if [[ -n "$LIMIT" ]]; then
    CMD="$CMD --limit $LIMIT"
fi

if [[ -n "$QA_TYPES" ]]; then
    CMD="$CMD --qa-types $QA_TYPES"
fi

# 평가 실행
echo_info "평가 시작..."
echo_info "Command: $CMD"
echo ""

eval $CMD

echo ""
echo_info "평가 완료. 결과: $OUTPUT_DIR/"
