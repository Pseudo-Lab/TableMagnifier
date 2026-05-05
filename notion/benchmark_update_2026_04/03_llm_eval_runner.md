# OpenAI-Compatible LLM Evaluation Runner

## 왜 추가했나

기존에는 random/heuristic/restricted baseline 중심으로 benchmark를 돌릴 수 있었지만, 실제 LLM API를 통해 같은 환경을 평가하는 경로는 없었다.

이번 패스에서는 benchmark core를 바꾸지 않고, LLM이 기존 action contract 위에서 움직이도록 평가 러너를 추가했다.

## 첫 버전 설계

첫 버전은 아래 원칙으로 고정했다.

- `WorkbookEnv`를 in-process로 직접 실행
- 모델 입력은 `viewport_svg + question + compact state`
- 모델 출력은 JSON action 1개만 허용
- provider 범위는 `OpenAI-compatible` API만 지원

즉, HTTP session layer를 거치지 않고 env를 바로 돌려 결정론성을 최대한 유지했다.

## 추가된 구성요소

### `LLMAgent`

역할:

- observation을 prompt로 직렬화
- 모델 응답을 JSON action으로 파싱
- 실패 시 제한된 재시도 수행
- run metadata를 누적

### OpenAI-compatible client

설정 항목:

- `model`
- `base_url`
- `api_key`

기본적으로 `chat/completions` 스타일 endpoint를 사용한다.

### `eval_llm.py`

지원 범위:

- `canonical_dev`
- `eval_hard_dev`
- `eval_hard_holdout`
- family / level / template / seed 필터

## 기록되는 추가 artifact

LLM runner는 baseline 결과에 더해 아래 필드를 남긴다.

- `model_config`
- `llm_trace`
- `usage`
- `latency_ms`
- `finish_reason`
- `parse_retry_count`
- `api_error`

이 덕분에 단순 accuracy뿐 아니라,

- 파싱 안정성
- 추론 step 수 대비 토큰 사용량
- API 실패 패턴
- 어떤 episode에서 응답이 흔들리는지

까지 같이 볼 수 있다.

## 실행 예시

```bash
cd /mnt/c/Users/imssh/Documents/poc_1
OPENAI_API_KEY=... uv run python -m table_env_bench.scripts.eval_llm --suite canonical_dev --model gpt-4o-mini
```

## 기대 효과

- heuristic baseline과 LLM을 같은 evaluator로 비교 가능
- family/level/operator/cue slice별 실패 패턴 분석 가능
- 앞으로 multimodal 입력이나 HTTP-backed agent를 붙일 때도 현재 runner를 기준선으로 삼을 수 있음
