# Notion 업로드 가이드

TableMagnifier 파이프라인 결과를 Notion 데이터베이스에 업로드하는 방법을 안내합니다.

## 📋 목차

1. [개요](#개요)
2. [설정](#설정)
3. [사용 방법](#사용-방법)
4. [FAQ](#faq)

---

## 개요

QA 생성 결과를 Notion 데이터베이스에 업로드하는 두 가지 방법이 있습니다:

### 방법 1: 파이프라인 실행 중 자동 업로드
- 파이프라인 실행과 동시에 Notion에 업로드
- `--upload-to-notion` 플래그 사용

### 방법 2: 기존 결과 선택적 업로드 (권장 ⭐)
- 이미 생성된 결과에서 원하는 것만 선택해서 업로드
- `upload_to_notion_from_json.py` 스크립트 사용
- **중복 업로드 걱정 없음** - 원하는 폴더만 선택적으로 업로드

---

## 설정

### 1. Notion API Key 준비

1. [Notion Developers](https://www.notion.so/my-integrations)에서 Integration 생성
2. API Key 복사

### 2. Database ID 확인

1. Notion에서 데이터베이스 페이지 열기
2. URL에서 Database ID 복사
   ```
   https://www.notion.so/your-workspace/<DATABASE_ID>?v=...
   ```

### 3. 설정 파일 업데이트

`apis/gemini_keys.yaml` 파일에 Notion 설정 추가:

```yaml
# 기존 Gemini/OpenAI 설정들...

# Notion 설정
notion_key: "secret_xxxxxxxxxxxxxxxxxxxxx"

notion_databases:
  public: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  finance: "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
  insurance: "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
```

---

## 사용 방법

### 🎯 방법 1: 파이프라인 실행 중 업로드

파이프라인 실행 시 `--upload-to-notion` 플래그를 추가하세요.

#### JSON 파이프라인 (OpenAI/Claude)

```bash
# run_openai_public.sh 사용 시
./run_openai_public.sh test_input.json --upload-to-notion

# 또는 직접 실행
python run_pipeline_json.py \
  --input test_input.json \
  --output-dir output_test_public \
  --provider openai \
  --model gpt-5-mini \
  --domain public \
  --qa-only \
  --upload-to-notion
```

#### 폴더 기반 파이프라인

```bash
python -m generate_synthetic_table.cli \
  data/Public/Table/P_origin_0 \
  --provider gemini_pool \
  --domain public \
  --qa-only \
  --upload-to-notion
```

---

### ⭐ 방법 2: 기존 결과 선택적 업로드 (권장)

이미 생성된 결과를 나중에 선택적으로 업로드할 수 있습니다.

#### 기본 사용법

```bash
# 폴더 경로 지정 (자동으로 pipeline_output.json 찾음)
python upload_to_notion_from_json.py output_test_public

# 또는 JSON 파일 직접 지정
python upload_to_notion_from_json.py output_test_public/pipeline_output.json
```

#### Dry-run 모드 (테스트)

실제로 업로드하지 않고 무엇이 업로드될지 미리 확인:

```bash
python upload_to_notion_from_json.py output_test_public --dry-run
```

출력 예시:
```
📂 Loaded 10 result(s) from output_test_public/pipeline_output.json
✅ Notion uploader initialized

🔍 [1/10] Would upload P_origin_0_1:
   - Domain: public
   - Image: P_origin_0_1
   - QA pairs: 5
   - Provider: openai
...
```

#### 조용히 실행

진행 메시지 없이 조용히 실행:

```bash
python upload_to_notion_from_json.py output_test_public --quiet
```

#### 다른 설정 파일 사용

```bash
python upload_to_notion_from_json.py output_test_public \
  --config-path path/to/custom_config.yaml
```

---

## 실전 예시 워크플로우

### 시나리오: 여러 파이프라인 실행 후 선택적 업로드

```bash
# 1. 여러 파이프라인 실행 (Notion 업로드 없이)
./run_openai_public.sh test_input.json
# → 결과: output_public/pipeline_output.json

./run_openai_public.sh multi_input.json
# → 결과: output_public/pipeline_output.json (덮어쓰기됨)

# 2. 각 결과를 별도 폴더로 저장
./run_openai_public.sh test_input.json --output-dir output_test_1
./run_openai_public.sh multi_input.json --output-dir output_test_2
./run_openai_public.sh another_input.json --output-dir output_test_3

# 3. 결과 확인 후 원하는 것만 선택적으로 업로드
python upload_to_notion_from_json.py output_test_1 --dry-run  # 먼저 확인
python upload_to_notion_from_json.py output_test_1            # 업로드

python upload_to_notion_from_json.py output_test_3 --dry-run  # 확인
python upload_to_notion_from_json.py output_test_3            # 업로드

# output_test_2는 품질이 안 좋아서 업로드 안 함
```

---

## FAQ

### Q1: 같은 결과를 여러 번 업로드하면 어떻게 되나요?

**A:** 현재는 중복 체크 없이 새로운 레코드가 계속 생성됩니다. 
- **해결책**: `--dry-run`으로 먼저 확인하거나, Notion에서 수동으로 중복 제거
- **권장**: 방법 2 (선택적 업로드)를 사용하여 원하는 폴더만 한 번씩 업로드

### Q2: 업로드 중 에러가 발생하면?

**A:** 스크립트는 에러가 발생해도 계속 진행됩니다.
- 성공/실패 카운트가 마지막에 표시됨
- QA가 없는 결과는 자동으로 스킵됨

### Q3: 특정 QA만 선택해서 업로드할 수 있나요?

**A:** 현재는 `pipeline_output.json` 전체를 업로드합니다.
- **대안**: JSON 파일을 직접 편집하거나 필터링 후 업로드

### Q4: 업로드된 데이터의 구조는?

**A:** 각 QA 쌍이 Notion 데이터베이스의 한 행(row)으로 저장됩니다:
- **Name/Title**: pair_id (예: `P_origin_0_1`)
- **Domain**: 도메인 (예: `public`)
- **Image**: 이미지 파일명
- **Question**: 질문
- **Answer**: 답변
- **Type**: QA 타입 (예: `reasoning`)
- **Count**: QA 순번 (1, 2, 3...)
- **Provider**: 사용한 LLM (예: `openai`)
- **Token**: 사용한 토큰 수
- **reasoning_annotation**: 추론 주석
- **context**: 컨텍스트

### Q5: 여러 도메인을 동시에 업로드할 수 있나요?

**A:** 네, `pipeline_output.json`에 여러 도메인이 섞여 있어도 자동으로 각 도메인의 데이터베이스에 분산 업로드됩니다.

---

## 팁 💡

1. **항상 `--dry-run`으로 먼저 확인하세요**
   ```bash
   python upload_to_notion_from_json.py output_test --dry-run
   ```

2. **출력 폴더를 명확하게 구분하세요**
   ```bash
   --output-dir output_test_openai_v1
   --output-dir output_test_claude_v2
   ```

3. **중요한 결과는 백업하세요**
   ```bash
   cp -r output_test_public output_test_public_backup
   ```

4. **Notion 데이터베이스 속성이 자동 생성됩니다**
   - 처음 업로드 시 필요한 속성들이 자동으로 추가됨
   - Database 권한 확인 필요 (Integration이 접근 가능해야 함)

---

## 관련 파일

- `upload_to_notion_from_json.py` - 선택적 업로드 스크립트
- `run_pipeline_json.py` - JSON 파이프라인 (파라미터로 `--upload-to-notion` 지원)
- `generate_synthetic_table/notion_uploader.py` - Notion 업로더 클래스
- `apis/gemini_keys.yaml` - 설정 파일

---

문제가 있거나 추가 기능이 필요하면 이슈를 열어주세요! 🚀
