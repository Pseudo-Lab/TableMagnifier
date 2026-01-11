#!/usr/bin/env python3
"""
Public 데이터셋 평가 스크립트

data/public/public_0/qa_output의 JSON 파일들을 평가합니다.
멀티 이미지 지원을 포함합니다.

사용법:
    # uv run으로 실행 (권장)
    uv run python -m eval.evaluate_public data/public/public_0/qa_output --provider vllm
    
    # 또는 bash 스크립트 사용
    ./eval/evaluate_public.sh
    
    # OpenAI API 사용
    uv run python -m eval.evaluate_public data/public/public_0/qa_output \\
        --provider openai --model gpt-4o-mini --api-key $OPENAI_API_KEY
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from .dataset import load_qa_from_folder, create_inference_prompts
from .evaluate import run_evaluation, evaluate_from_file
from .inference import get_client, run_inference, InferenceRequest
from .llm_judge import create_judge_client, judge_batch
from .config_loader import load_config, get_inference_config, get_judge_config


def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def evaluate_public_dataset(
    qa_output_dir: Path,
    provider: str = "vllm",
    output_dir: Optional[Path] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    max_concurrent: Optional[int] = None,
    include_images: bool = True,
    prompt_template: Optional[str] = None,
    verbose: bool = False,
    use_judge: Optional[bool] = None,
    judge_provider: Optional[str] = None,
    judge_model: Optional[str] = None,
    judge_api_key: Optional[str] = None,
    config_path: Optional[Path] = None,
):
    """
    Public 데이터셋 평가 실행
    
    Args:
        qa_output_dir: qa_output 폴더 경로
        provider: 추론 제공자 (vllm, openai, anthropic)
        output_dir: 결과 저장 디렉토리
        base_url: vLLM 서버 URL
        model: 모델 이름
        api_key: API 키 (OpenAI/Anthropic용)
        max_tokens: 최대 토큰 수
        temperature: 샘플링 온도
        max_concurrent: 최대 동시 요청 수
        include_images: 이미지 포함 여부
        prompt_template: 프롬프트 템플릿
        verbose: 상세 로그 출력
        config_path: 설정 파일 경로 (None이면 기본 설정 파일 사용)
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    # 설정 파일 로드
    config = load_config(config_path)
    inference_config = get_inference_config(config)
    judge_config = get_judge_config(config)
    
    # 명령줄 인자가 있으면 우선 적용, 없으면 config 사용
    if base_url is None:
        base_url = inference_config.get("base_url")
    if model is None:
        model = inference_config.get("model")
    if api_key is None:
        api_key = inference_config.get("api_key")
    if max_tokens is None:
        max_tokens = inference_config.get("max_tokens", 512)
    if temperature is None:
        temperature = inference_config.get("temperature", 0.0)
    if max_concurrent is None:
        max_concurrent = inference_config.get("max_concurrent", 10)
    
    # Judge 설정 (명령줄 인자가 없으면 config 사용)
    if use_judge is None:
        use_judge = judge_config.get("enabled", False)
    if judge_provider is None:
        judge_provider = judge_config.get("provider", "vllm")
    if judge_model is None:
        judge_model = judge_config.get("model")
    if judge_api_key is None:
        judge_api_key = judge_config.get("api_key")
    
    # 경로 확인
    qa_output_dir = Path(qa_output_dir)
    if not qa_output_dir.exists():
        logger.error(f"QA output directory not found: {qa_output_dir}")
        return None
    
    # 출력 디렉토리 설정
    if output_dir is None:
        output_dir = qa_output_dir.parent / "eval_results"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Loading QA dataset from: {qa_output_dir}")
    logger.info(f"Using config: base_url={base_url}, model={model}, use_judge={use_judge}")
    
    # 1. 데이터셋 로드
    dataset = load_qa_from_folder(qa_output_dir, pattern="*_qa.json")
    logger.info(f"Loaded {len(dataset)} QA items")
    logger.info(f"Type distribution: {dataset.get_type_distribution()}")
    
    # 2. 추론 요청 생성
    prompts = create_inference_prompts(
        dataset,
        prompt_template=prompt_template,
        include_image=include_images,
    )
    
    requests = [
        InferenceRequest(
            id=p["id"],
            prompt=p["prompt"],
            ground_truth=p["ground_truth"],
            qa_type=p["qa_type"],
            image_paths=p.get("image_paths"),
        )
        for p in prompts
    ]
    
    # 이미지 경로 확인 및 수정 (상대 경로 처리)
    workspace_root = Path(__file__).resolve().parents[1]
    for req in requests:
        if req.image_paths:
            corrected_paths = []
            for img_path in req.image_paths:
                path = Path(img_path)
                if not path.exists():
                    # 상대 경로인 경우 workspace 기준으로 시도
                    workspace_path = workspace_root / img_path
                    if workspace_path.exists():
                        corrected_paths.append(str(workspace_path))
                    else:
                        # data/Public/Table/... 형식인 경우
                        public_path = workspace_root / img_path
                        if public_path.exists():
                            corrected_paths.append(str(public_path))
                        else:
                            logger.warning(f"Image not found: {img_path}")
                            corrected_paths.append(img_path)  # 원본 유지
                else:
                    corrected_paths.append(img_path)
            req.image_paths = corrected_paths
    
    # 3. 클라이언트 설정
    client_kwargs = {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "max_concurrent": max_concurrent,
    }
    
    if provider == "vllm":
        client_kwargs["base_url"] = base_url or "http://localhost:8000/v1"
        client_kwargs["model"] = model or "default"
        client_kwargs["api_key"] = api_key or "EMPTY"
    elif provider == "openai":
        client_kwargs["model"] = model or "gpt-4o-mini"
        if api_key:
            client_kwargs["api_key"] = api_key
    elif provider in ["anthropic", "claude"]:
        client_kwargs["model"] = model or "claude-sonnet-4-20250514"
        if api_key:
            client_kwargs["api_key"] = api_key
    
    client = get_client(provider, **client_kwargs)
    
    # 4. 추론 실행
    logger.info(f"Running inference with {provider} provider...")
    inference_output = output_dir / "inference_results.json"
    
    responses = await run_inference(
        client,
        requests,
        output_path=inference_output,
    )
    
    # 5. 평가
    from .evaluate import evaluate_predictions
    from .metrics import aggregate_metrics
    
    predictions = [
        {
            "id": r.id,
            "prediction": r.prediction,
            "ground_truth": r.ground_truth,
            "qa_type": r.qa_type,
            "question": p.get("question", ""),
        }
        for r, p in zip(responses, prompts)
    ]
    
    # Judge 클라이언트 생성 (필요시)
    judge_client = None
    if use_judge:
        judge_client = create_judge_client(
            provider=judge_provider,
            model=judge_model,
            api_key=judge_api_key,
        )
    
    questions = [p.get("question", "") for p in prompts]
    results, aggregated = await evaluate_predictions(
        predictions,
        use_judge=use_judge,
        judge_client=judge_client,
        questions=questions,
    )
    
    # 6. 리포트 생성 및 저장
    from .evaluate import generate_report, print_report
    
    print_report(aggregated)
    
    report_path = output_dir / "evaluation_report.json"
    report = generate_report(
        results,
        aggregated,
        metadata={
            "qa_output_dir": str(qa_output_dir),
            "provider": provider,
            "model": model,
            "include_images": include_images,
        }
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, ensure_ascii=False, indent=2, fp=f)
    
    logger.info(f"Evaluation report saved to: {report_path}")
    
    return results, aggregated


def main():
    """
    메인 엔트리포인트
    
    사용 예시:
        # uv run으로 실행 (권장)
        uv run python -m eval.evaluate_public data/public/public_0/qa_output --provider vllm
        
        # 또는 bash 스크립트 사용
        ./eval/evaluate_public.sh
        
        # OpenAI API 사용
        uv run python -m eval.evaluate_public data/public/public_0/qa_output \\
            --provider openai --model gpt-4o-mini --api-key $OPENAI_API_KEY
    """
    parser = argparse.ArgumentParser(
        description="Public 데이터셋 평가 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "qa_output_dir",
        type=str,
        help="QA output 디렉토리 경로 (예: data/public/public_0/qa_output)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="설정 파일 경로 (default: eval/vllm_config.json)",
    )
    parser.add_argument(
        "--provider",
        choices=["vllm", "openai", "anthropic", "claude"],
        default="vllm",
        help="추론 제공자 (default: vllm, 설정 파일에서 오버라이드 가능)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="결과 저장 디렉토리 (default: qa_output_dir/../eval_results)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="vLLM 서버 URL (default: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="모델 이름",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API 키 (OpenAI/Anthropic용)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="최대 토큰 수 (미지정 시 설정 파일/기본값 사용)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="샘플링 온도 (미지정 시 설정 파일/기본값 사용)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=None,
        help="최대 동시 요청 수 (미지정 시 설정 파일/기본값 사용)",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="이미지 포함하지 않기",
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        help="프롬프트 템플릿 파일 경로",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="상세 로그 출력",
    )

    # LLM-as-Judge 옵션
    parser.add_argument(
        "--use-judge",
        action="store_true",
        default=None,
        help="LLM-as-Judge 평가 사용 (미지정 시 설정 파일의 judge.enabled 따름)",
    )
    parser.add_argument(
        "--judge-provider",
        choices=["vllm", "openai", "anthropic", "claude"],
        default=None,
        help="Judge 제공자 (미지정 시 설정 파일/기본값 사용)",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=None,
        help="Judge 모델 이름 (미지정 시 설정 파일/기본값 사용)",
    )
    parser.add_argument(
        "--judge-api-key",
        type=str,
        default=None,
        help="Judge API 키 (미지정 시 설정 파일/환경변수 사용)",
    )
    
    args = parser.parse_args()
    
    # 프롬프트 템플릿 로드
    prompt_template = None
    if args.prompt_template:
        prompt_template = Path(args.prompt_template).read_text(encoding="utf-8")
    
    # 비동기 실행
    try:
        config_path = Path(args.config) if getattr(args, 'config', None) else None
        
        results, aggregated = asyncio.run(
            evaluate_public_dataset(
                qa_output_dir=Path(args.qa_output_dir),
                provider=args.provider,
                output_dir=Path(args.output_dir) if args.output_dir else None,
                base_url=args.base_url,
                model=args.model,
                api_key=args.api_key,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                max_concurrent=args.max_concurrent,
                include_images=not args.no_images,
                prompt_template=prompt_template,
                verbose=args.verbose,
                use_judge=args.use_judge,
                judge_provider=args.judge_provider,
                judge_model=args.judge_model,
                judge_api_key=args.judge_api_key,
                config_path=config_path,
            )
        )
        
        if results is None:
            return 1
        
        return 0
    except Exception as e:
        logging.error(f"Evaluation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

