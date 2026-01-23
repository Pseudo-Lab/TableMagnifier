#!/bin/bash

# ==============================================================================
#  TableMagnifier - Master Pipeline Script
# ==============================================================================
#
# 전체 파이프라인을 통합 실행합니다:
#   1. Synthetic Table 생성 (from JSON input)
#   2. HTML → Image 변환
#   3. QA 재생성 (선택)
#   4. QA 난이도 필터링 (vLLM 필요)
#   5. 평가 (vLLM 필요)
#
# Usage:
#   ./run_all.sh --input data.json --domain business [OPTIONS]
#
# Examples:
#   # 기본 파이프라인 (테이블 생성 + 이미지 변환)
#   ./run_all.sh --input test.json --domain business
#
#   # 전체 파이프라인 (vLLM 평가 포함)
#   ./run_all.sh --input test.json --domain business --with-eval --vllm-url http://localhost:8000/v1
#
#   # QA 재생성만
#   ./run_all.sh --domain business --regenerate-qa-only
#
#   # 필터링 + 평가만 (이미 테이블/이미지가 있는 경우)
#   ./run_all.sh --domain business --filter-only --with-eval
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ==============================================================================
#  Configuration
# ==============================================================================

# Default values
INPUT_JSON=""
DOMAIN=""
OUTPUT_DIR=""
PROVIDER="claude"
MODEL="claude-sonnet-4-5"
VLLM_URL="http://localhost:8000/v1"

# Pipeline steps (default: generate + capture)
DO_GENERATE=true
DO_CAPTURE=true
DO_REGENERATE_QA=false
DO_FILTER=false
DO_EVAL=false

# Options
LIMIT=""
DRY_RUN=false
SKIP_QA=false
FILTER_TRIALS=10
FILTER_MIN_ACC=0.3
FILTER_MAX_ACC=0.6

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ==============================================================================
#  Helper Functions
# ==============================================================================

echo_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

echo_step() {
    echo ""
    echo -e "${CYAN}▶ STEP $1: $2${NC}"
    echo -e "${CYAN}─────────────────────────────────────────────────────────────${NC}"
}

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

show_help() {
    cat << 'EOF'
Usage: ./run_all.sh [OPTIONS]

TableMagnifier 전체 파이프라인을 통합 실행합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Required Options
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --domain DOMAIN         도메인 (business, finance, academic, medical, public)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Pipeline Steps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --input FILE            입력 JSON 파일 (테이블 생성 시 필수)
  --regenerate-qa         QA 재생성 포함
  --regenerate-qa-only    QA 재생성만 실행 (테이블 생성 스킵)
  --with-filter           vLLM으로 QA 난이도 필터링 포함
  --filter-only           필터링만 실행 (테이블/이미지 생성 스킵)
  --with-eval             vLLM으로 평가 포함
  --eval-only             평가만 실행

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generation Options
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --output-dir DIR        출력 디렉토리 (default: output_{domain})
  --provider PROVIDER     LLM 제공자: claude, openai, gemini (default: claude)
  --model MODEL           모델 이름 (default: claude-sonnet-4-5)
  --skip-qa               테이블 생성 시 QA 생성 스킵

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  vLLM Options (for filter/eval)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --vllm-url URL          vLLM 서버 URL (default: http://localhost:8000/v1)
  --filter-trials N       필터링 시 QA당 시도 횟수 (default: 10)
  --filter-min-acc FLOAT  필터링 최소 정확도 (default: 0.3)
  --filter-max-acc FLOAT  필터링 최대 정확도 (default: 0.6)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Other Options
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  --limit N               처리할 최대 entry 수 (테스트용)
  --dry-run               실제 실행 없이 확인만
  -h, --help              도움말 표시

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Examples
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  # 1. 기본 파이프라인 (테이블 생성 → 이미지 변환)
  ./run_all.sh --input test.json --domain business

  # 2. 전체 파이프라인 (생성 → 이미지 → 필터링 → 평가)
  ./run_all.sh --input test.json --domain business --with-filter --with-eval

  # 3. QA만 재생성 (기존 테이블 유지)
  ./run_all.sh --domain business --regenerate-qa-only

  # 4. 필터링만 (이미 이미지가 있는 경우)
  ./run_all.sh --domain business --filter-only

  # 5. 평가만
  ./run_all.sh --domain business --eval-only

  # 6. OpenAI 사용
  ./run_all.sh --input test.json --domain business --provider openai --model gpt-4o

  # 7. 테스트 (3개만)
  ./run_all.sh --input test.json --domain business --limit 3 --dry-run

EOF
}

# ==============================================================================
#  Argument Parsing
# ==============================================================================

# Parse first argument as JSON file if it ends with .json
if [[ "$1" == *.json ]]; then
    INPUT_JSON="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --input)
            INPUT_JSON="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
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
        --vllm-url)
            VLLM_URL="$2"
            shift 2
            ;;
        --regenerate-qa)
            DO_REGENERATE_QA=true
            shift
            ;;
        --regenerate-qa-only)
            DO_GENERATE=false
            DO_CAPTURE=false
            DO_REGENERATE_QA=true
            shift
            ;;
        --with-filter)
            DO_FILTER=true
            shift
            ;;
        --filter-only)
            DO_GENERATE=false
            DO_CAPTURE=false
            DO_FILTER=true
            shift
            ;;
        --with-eval)
            DO_EVAL=true
            shift
            ;;
        --eval-only)
            DO_GENERATE=false
            DO_CAPTURE=false
            DO_EVAL=true
            shift
            ;;
        --filter-trials)
            FILTER_TRIALS="$2"
            shift 2
            ;;
        --filter-min-acc)
            FILTER_MIN_ACC="$2"
            shift 2
            ;;
        --filter-max-acc)
            FILTER_MAX_ACC="$2"
            shift 2
            ;;
        --skip-qa)
            SKIP_QA=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo_error "Unknown option: $1"
            echo "Use -h or --help for usage information."
            exit 1
            ;;
    esac
done

# ==============================================================================
#  Validation
# ==============================================================================

# Domain is always required
if [[ -z "$DOMAIN" ]]; then
    echo_error "--domain is required"
    echo "Use -h or --help for usage information."
    exit 1
fi

# Input JSON required for generation
if [[ "$DO_GENERATE" == true ]] && [[ -z "$INPUT_JSON" ]]; then
    echo_error "--input is required for table generation"
    echo "Use --regenerate-qa-only, --filter-only, or --eval-only to skip generation."
    exit 1
fi

# Check input file exists
if [[ -n "$INPUT_JSON" ]] && [[ ! -f "$INPUT_JSON" ]]; then
    echo_error "Input file not found: $INPUT_JSON"
    exit 1
fi

# Set default output directory
if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="output_${DOMAIN}"
fi

# ==============================================================================
#  Check Dependencies
# ==============================================================================

check_vllm_connection() {
    if curl -s --connect-timeout 5 "${VLLM_URL}/models" > /dev/null 2>&1; then
        VLLM_MODEL=$(curl -s "${VLLM_URL}/models" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['data'][0]['id'] if data.get('data') else 'unknown')" 2>/dev/null || echo "unknown")
        echo_info "vLLM connected: ${VLLM_MODEL}"
        return 0
    else
        return 1
    fi
}

check_api_key() {
    case $PROVIDER in
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

# ==============================================================================
#  Main Pipeline
# ==============================================================================

echo_header "TableMagnifier - Master Pipeline"

echo ""
echo "Configuration:"
echo "  Domain:      $DOMAIN"
echo "  Output Dir:  $OUTPUT_DIR"
echo "  Provider:    $PROVIDER"
echo "  Model:       $MODEL"
if [[ -n "$INPUT_JSON" ]]; then
    echo "  Input JSON:  $INPUT_JSON"
fi
if [[ -n "$LIMIT" ]]; then
    echo "  Limit:       $LIMIT entries"
fi
if [[ "$DRY_RUN" == true ]]; then
    echo "  Mode:        DRY RUN"
fi
echo ""
echo "Pipeline Steps:"
echo "  1. Generate Tables:  $([ "$DO_GENERATE" == true ] && echo "✓" || echo "✗")"
echo "  2. Capture Images:   $([ "$DO_CAPTURE" == true ] && echo "✓" || echo "✗")"
echo "  3. Regenerate QA:    $([ "$DO_REGENERATE_QA" == true ] && echo "✓" || echo "✗")"
echo "  4. Filter QA:        $([ "$DO_FILTER" == true ] && echo "✓" || echo "✗")"
echo "  5. Evaluate:         $([ "$DO_EVAL" == true ] && echo "✓" || echo "✗")"
echo ""

# Check API key for generation steps
if [[ "$DO_GENERATE" == true ]] || [[ "$DO_REGENERATE_QA" == true ]]; then
    check_api_key
fi

# Check vLLM for filter/eval steps
if [[ "$DO_FILTER" == true ]] || [[ "$DO_EVAL" == true ]]; then
    echo_info "Checking vLLM connection..."
    if ! check_vllm_connection; then
        echo_error "Cannot connect to vLLM server at ${VLLM_URL}"
        echo_error "Please ensure vLLM server is running for filter/eval steps."
        exit 1
    fi
fi

STEP_NUM=0

# ------------------------------------------------------------------------------
#  Step 1: Generate Synthetic Tables
# ------------------------------------------------------------------------------
if [[ "$DO_GENERATE" == true ]]; then
    STEP_NUM=$((STEP_NUM + 1))
    echo_step $STEP_NUM "Generate Synthetic Tables"

    GENERATE_ARGS="--input \"$INPUT_JSON\" --output-dir \"$OUTPUT_DIR\" --provider \"$PROVIDER\" --model \"$MODEL\" --domain \"$DOMAIN\""

    if [[ "$SKIP_QA" == true ]]; then
        GENERATE_ARGS="$GENERATE_ARGS --skip-qa"
    fi

    if [[ -n "$LIMIT" ]]; then
        GENERATE_ARGS="$GENERATE_ARGS --limit $LIMIT"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        echo_info "[DRY RUN] Would run: uv run python run_pipeline_json.py $GENERATE_ARGS"
    else
        eval "uv run python run_pipeline_json.py $GENERATE_ARGS"
        echo_success "Table generation completed"
    fi
fi

# ------------------------------------------------------------------------------
#  Step 2: Capture HTML to Images
# ------------------------------------------------------------------------------
if [[ "$DO_CAPTURE" == true ]]; then
    STEP_NUM=$((STEP_NUM + 1))
    echo_step $STEP_NUM "Capture HTML to Images"

    CAPTURE_ARGS="--output-dirs $OUTPUT_DIR"

    if [[ "$DRY_RUN" == true ]]; then
        echo_info "[DRY RUN] Would run: uv run python capture_html_images.py $CAPTURE_ARGS"
    else
        uv run python capture_html_images.py $CAPTURE_ARGS
        echo_success "Image capture completed"
    fi
fi

# ------------------------------------------------------------------------------
#  Step 3: Regenerate QA (Optional)
# ------------------------------------------------------------------------------
if [[ "$DO_REGENERATE_QA" == true ]]; then
    STEP_NUM=$((STEP_NUM + 1))
    echo_step $STEP_NUM "Regenerate QA"

    REGEN_ARGS="--domain $DOMAIN --provider $PROVIDER --model $MODEL"

    if [[ -n "$LIMIT" ]]; then
        REGEN_ARGS="$REGEN_ARGS --limit $LIMIT"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        REGEN_ARGS="$REGEN_ARGS --dry-run"
    fi

    uv run python regenerate_qa.py $REGEN_ARGS
    echo_success "QA regeneration completed"
fi

# ------------------------------------------------------------------------------
#  Step 4: Filter QA by Difficulty (Optional)
# ------------------------------------------------------------------------------
if [[ "$DO_FILTER" == true ]]; then
    STEP_NUM=$((STEP_NUM + 1))
    echo_step $STEP_NUM "Filter QA by Difficulty"

    FILTER_ARGS="--domain $DOMAIN --vllm-url $VLLM_URL --trials $FILTER_TRIALS --min-acc $FILTER_MIN_ACC --max-acc $FILTER_MAX_ACC"

    if [[ -n "$LIMIT" ]]; then
        FILTER_ARGS="$FILTER_ARGS --limit $LIMIT"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        FILTER_ARGS="$FILTER_ARGS --dry-run"
    fi

    uv run python filter_qa_by_difficulty.py $FILTER_ARGS
    echo_success "QA filtering completed"
fi

# ------------------------------------------------------------------------------
#  Step 5: Evaluate (Optional)
# ------------------------------------------------------------------------------
if [[ "$DO_EVAL" == true ]]; then
    STEP_NUM=$((STEP_NUM + 1))
    echo_step $STEP_NUM "Evaluate with vLLM"

    EVAL_ARGS="--domain $DOMAIN --vllm-url $VLLM_URL"

    if [[ -n "$LIMIT" ]]; then
        EVAL_ARGS="$EVAL_ARGS --limit $LIMIT"
    fi

    if [[ "$DRY_RUN" == true ]]; then
        EVAL_ARGS="$EVAL_ARGS --dry-run"
    fi

    uv run python -m eval.evaluate_vllm $EVAL_ARGS
    echo_success "Evaluation completed"
fi

# ==============================================================================
#  Summary
# ==============================================================================

echo_header "Pipeline Completed"

echo ""
echo "Output Directory: $OUTPUT_DIR/"
echo ""
echo "Generated Files:"

if [[ -d "$OUTPUT_DIR" ]]; then
    # Count files
    JSON_COUNT=$(find "$OUTPUT_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)
    HTML_COUNT=$(find "$OUTPUT_DIR/html" -name "*.html" 2>/dev/null | wc -l)
    IMAGE_COUNT=$(find "$OUTPUT_DIR/images" -name "*.png" 2>/dev/null | wc -l)

    echo "  - JSON files:  $JSON_COUNT"
    echo "  - HTML files:  $HTML_COUNT (in html/)"
    echo "  - Images:      $IMAGE_COUNT (in images/)"

    if [[ "$DO_FILTER" == true ]] && [[ "$DRY_RUN" != true ]]; then
        REVIEW_FILE=$(ls -t "$OUTPUT_DIR"/qa_for_review_*.json 2>/dev/null | head -1)
        if [[ -n "$REVIEW_FILE" ]]; then
            REVIEW_COUNT=$(python3 -c "import json; print(json.load(open('$REVIEW_FILE'))['count'])" 2>/dev/null || echo "?")
            echo ""
            echo "  Review File: $(basename $REVIEW_FILE)"
            echo "  QA for Review: $REVIEW_COUNT items"
        fi
    fi

    if [[ "$DO_EVAL" == true ]] && [[ "$DRY_RUN" != true ]]; then
        EVAL_FILE=$(ls -t "$OUTPUT_DIR"/eval_results_*.json 2>/dev/null | head -1)
        if [[ -n "$EVAL_FILE" ]]; then
            echo ""
            echo "  Eval Results: $(basename $EVAL_FILE)"
        fi
    fi
fi

echo ""
echo -e "${GREEN}Done!${NC}"
