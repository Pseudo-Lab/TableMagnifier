#!/bin/bash
#
# Public 데이터셋 평가 스크립트
#
# 사용법:
#   ./eval/evaluate_public.sh [옵션]
#   또는
#   uv run python -m eval.evaluate_public [옵션]
#
# 예시:
#   # vLLM 서버 사용 (기본)
#   ./eval/evaluate_public.sh
#
#   # OpenAI API 사용
#   ./eval/evaluate_public.sh --provider openai --model gpt-4o-mini --api-key $OPENAI_API_KEY
#
#   # Anthropic Claude 사용
#   ./eval/evaluate_public.sh --provider anthropic --model claude-sonnet-4-20250514 --api-key $ANTHROPIC_API_KEY
#
#   # uv run으로 직접 실행
#   uv run python -m eval.evaluate_public data/public/public_0/qa_output --provider vllm
#

set -e  # 에러 발생 시 중단

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/vllm_config.json"
QA_OUTPUT_DIR="${PROJECT_ROOT}/data/public/public_0/qa_output"
OUTPUT_DIR="${PROJECT_ROOT}/data/public/public_0/eval_results"
PROVIDER="vllm"
BASE_URL=""
MODEL=""
API_KEY=""
MAX_TOKENS=""
TEMPERATURE=""
MAX_CONCURRENT=""
INCLUDE_IMAGES=true
PROMPT_TEMPLATE=""
VERBOSE=false
USE_JUDGE=""
JUDGE_PROVIDER=""
JUDGE_MODEL=""
JUDGE_API_KEY=""
CONFIG_PATH="$CONFIG_FILE"

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 도움말 출력
show_help() {
    cat << EOF
Public 데이터셋 평가 스크립트

사용법:
    $0 [옵션]

옵션:
    --config FILE           설정 파일 경로
                            (기본: eval/vllm_config.json)
    --qa-output-dir DIR     QA output 디렉토리 경로
                            (기본: data/public/public_0/qa_output)
    --output-dir DIR         결과 저장 디렉토리
                            (기본: data/public/public_0/eval_results)
    --provider PROVIDER      추론 제공자: vllm, openai, anthropic, claude
                            (기본: vllm)
    --base-url URL          vLLM 서버 URL
                            (기본: http://localhost:8000/v1)
    --model MODEL           모델 이름
    --api-key KEY           API 키 (OpenAI/Anthropic용)
    --max-tokens N          최대 토큰 수 (기본: 512)
    --temperature T         샘플링 온도 (기본: 0.0)
    --max-concurrent N      최대 동시 요청 수 (기본: 10)
    --no-images             이미지 포함하지 않기
    --prompt-template FILE  프롬프트 템플릿 파일 경로
    -v, --verbose           상세 로그 출력
    -h, --help              이 도움말 출력

예시:
    # vLLM 서버 사용
    $0

    # OpenAI API 사용
    $0 --provider openai --model gpt-4o-mini --api-key \$OPENAI_API_KEY

    # Anthropic Claude 사용
    $0 --provider anthropic --model claude-sonnet-4-20250514 --api-key \$ANTHROPIC_API_KEY

    # 커스텀 QA 디렉토리 사용
    $0 --qa-output-dir data/public/public_1/qa_output

    # uv run으로 직접 실행 (bash 스크립트 없이)
    uv run python -m eval.evaluate_public data/public/public_0/qa_output --provider vllm

EOF
}

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            CONFIG_PATH="$2"
            shift 2
            ;;
        --qa-output-dir)
            QA_OUTPUT_DIR="$2"
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
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --max-tokens)
            MAX_TOKENS="$2"
            shift 2
            ;;
        --temperature)
            TEMPERATURE="$2"
            shift 2
            ;;
        --max-concurrent)
            MAX_CONCURRENT="$2"
            shift 2
            ;;
        --no-images)
            INCLUDE_IMAGES=false
            shift
            ;;
        --prompt-template)
            PROMPT_TEMPLATE="$2"
            shift 2
            ;;
        --use-judge)
            USE_JUDGE=true
            shift
            ;;
        --judge-provider)
            JUDGE_PROVIDER="$2"
            shift 2
            ;;
        --judge-model)
            JUDGE_MODEL="$2"
            shift 2
            ;;
        --judge-api-key)
            JUDGE_API_KEY="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}알 수 없는 옵션: $1${NC}" >&2
            show_help
            exit 1
            ;;
    esac
done

# 프로젝트 루트로 이동
cd "$PROJECT_ROOT"

# uv 설치 확인
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}경고: uv가 설치되어 있지 않습니다. uv를 설치하거나 python을 직접 사용하세요.${NC}" >&2
    echo -e "${YELLOW}uv 설치: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}" >&2
    echo -e "${YELLOW}또는 python을 직접 사용: python -m eval.evaluate_public ...${NC}" >&2
    # uv가 없어도 계속 진행 (python 직접 사용)
    USE_UV=false
else
    USE_UV=true
fi

# QA output 디렉토리 확인
if [ ! -d "$QA_OUTPUT_DIR" ]; then
    echo -e "${RED}오류: QA output 디렉토리를 찾을 수 없습니다: $QA_OUTPUT_DIR${NC}" >&2
    exit 1
fi

# QA 파일 확인
QA_FILES=$(find "$QA_OUTPUT_DIR" -name "*_qa.json" | wc -l)
if [ "$QA_FILES" -eq 0 ]; then
    echo -e "${YELLOW}경고: QA 파일을 찾을 수 없습니다: $QA_OUTPUT_DIR/*_qa.json${NC}" >&2
    exit 1
fi

echo -e "${GREEN}=== Public 데이터셋 평가 시작 ===${NC}"
echo "QA Output 디렉토리: $QA_OUTPUT_DIR"
echo "QA 파일 수: $QA_FILES"
echo "Provider: $PROVIDER"
echo "Output 디렉토리: $OUTPUT_DIR"
echo ""

# Python 스크립트 실행 (uv run 사용, 없으면 python 직접 사용)
if [ "$USE_UV" = true ]; then
    PYTHON_CMD="uv run python -m eval.evaluate_public"
else
    PYTHON_CMD="python -m eval.evaluate_public"
fi
PYTHON_CMD="$PYTHON_CMD \"$QA_OUTPUT_DIR\""
PYTHON_CMD="$PYTHON_CMD --provider $PROVIDER"
PYTHON_CMD="$PYTHON_CMD --output-dir \"$OUTPUT_DIR\""
PYTHON_CMD="$PYTHON_CMD --config \"$CONFIG_PATH\""

if [ -n "$BASE_URL" ]; then
    PYTHON_CMD="$PYTHON_CMD --base-url \"$BASE_URL\""
fi

if [ -n "$MODEL" ]; then
    PYTHON_CMD="$PYTHON_CMD --model \"$MODEL\""
fi

if [ -n "$API_KEY" ]; then
    PYTHON_CMD="$PYTHON_CMD --api-key \"$API_KEY\""
fi

if [ -n "$MAX_TOKENS" ]; then
    PYTHON_CMD="$PYTHON_CMD --max-tokens $MAX_TOKENS"
fi

if [ -n "$TEMPERATURE" ]; then
    PYTHON_CMD="$PYTHON_CMD --temperature $TEMPERATURE"
fi

if [ -n "$MAX_CONCURRENT" ]; then
    PYTHON_CMD="$PYTHON_CMD --max-concurrent $MAX_CONCURRENT"
fi

if [ "$INCLUDE_IMAGES" = false ]; then
    PYTHON_CMD="$PYTHON_CMD --no-images"
fi

if [ -n "$PROMPT_TEMPLATE" ]; then
    PYTHON_CMD="$PYTHON_CMD --prompt-template \"$PROMPT_TEMPLATE\""
fi

if [ "$VERBOSE" = true ]; then
    PYTHON_CMD="$PYTHON_CMD --verbose"
fi

if [ "$USE_JUDGE" = true ]; then
    PYTHON_CMD="$PYTHON_CMD --use-judge"
    PYTHON_CMD="$PYTHON_CMD --judge-provider \"$JUDGE_PROVIDER\""
    if [ -n "$JUDGE_MODEL" ]; then
        PYTHON_CMD="$PYTHON_CMD --judge-model \"$JUDGE_MODEL\""
    fi
    if [ -n "$JUDGE_API_KEY" ]; then
        PYTHON_CMD="$PYTHON_CMD --judge-api-key \"$JUDGE_API_KEY\""
    fi
fi

# 실행
echo -e "${GREEN}평가 실행 중...${NC}"
eval $PYTHON_CMD

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== 평가 완료 ===${NC}"
    echo "결과 저장 위치: $OUTPUT_DIR"
    echo "  - inference_results.json: 추론 결과"
    echo "  - evaluation_report.json: 평가 리포트"
else
    echo ""
    echo -e "${RED}=== 평가 실패 ===${NC}"
    exit $EXIT_CODE
fi

