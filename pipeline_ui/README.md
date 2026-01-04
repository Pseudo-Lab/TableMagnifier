# TableMagnifier Pipeline UI

한국어 테이블 이미지에서 합성 데이터와 QA를 생성하는 웹 UI입니다.

## 기능

- **이미지 업로드**: 드래그 앤 드롭으로 PNG 이미지 업로드
- **배치 처리**: 여러 이미지를 동시에 처리
- **실시간 진행 상태**: WebSocket으로 파이프라인 진행 상태 확인
- **중단/재개**: 배치 처리 중간에 일시정지 후 이어서 처리 가능
- **에러 재시도**: 실패한 항목을 선택적으로 재시도
- **결과 시각화**: HTML 테이블, 합성 테이블, QA 쌍 확인
- **결과 다운로드**: JSON 형태로 결과 다운로드

## 시작하기

### 1. 백엔드 실행

```bash
cd pipeline_ui/backend

# 의존성 설치 (프로젝트 루트의 가상환경 사용)
source ../../.venv/bin/activate

# 서버 실행
python main.py
```

백엔드가 http://localhost:8001 에서 실행됩니다.

### 2. 프론트엔드 실행

```bash
cd pipeline_ui/frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

프론트엔드가 http://localhost:5173 에서 실행됩니다.

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/upload` | 이미지 파일 업로드 |
| POST | `/api/pipeline/run` | 파이프라인 실행 |
| GET | `/api/pipeline/status/{job_id}` | 작업 상태 조회 |
| POST | `/api/pipeline/pause/{job_id}` | 작업 일시정지 |
| POST | `/api/pipeline/resume/{job_id}` | 작업 재개 |
| POST | `/api/pipeline/retry` | 실패 항목 재시도 |
| POST | `/api/pipeline/cancel/{job_id}` | 작업 취소 |
| GET | `/api/pipeline/list` | 모든 작업 목록 |
| WS | `/ws/{job_id}` | 실시간 상태 업데이트 |

## 설정

### 파이프라인 설정

```json
{
  "provider": "gemini_pool",  // openai, gemini, gemini_pool
  "model": "gemini-2.0-flash",
  "temperature": 0.2
}
```

### 환경 변수

- `OPENAI_API_KEY`: OpenAI 사용 시
- `GOOGLE_API_KEY`: Gemini 단일 키 사용 시
- `apis/gemini_keys.yaml`: gemini_pool 사용 시 API 키 목록

## 디렉토리 구조

```
pipeline_ui/
├── backend/
│   └── main.py          # FastAPI 서버
├── frontend/
│   ├── src/
│   │   ├── App.tsx      # 메인 UI 컴포넌트
│   │   ├── api.ts       # API 클라이언트
│   │   └── types.ts     # 타입 정의
│   └── package.json
└── README.md
```

## 체크포인트

작업이 중단되면 `checkpoints/` 폴더에 상태가 저장됩니다.
서버 재시작 후에도 `/api/pipeline/resume/{job_id}`로 이어서 처리할 수 있습니다.
