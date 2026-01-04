# TableMagnifier Annotation Tool (테이블 확대기 주석 도구)

TableMagnifier 파이프라인에서 생성된 합성 테이블 데이터를 검증하고 개선하기 위한 웹 기반 도구입니다. 사용자는 원본 이미지, 파싱된 HTML, 합성 HTML을 나란히 비교하고, 합성된 JSON 구조와 QA 쌍을 직접 수정하여 MongoDB에 검증된 데이터를 바로 저장할 수 있습니다.

## 주요 기능
- **시각적 비교**: 원본 이미지, 파싱된 HTML, 합성 HTML을 한 화면에서 비교 검토.
- **JSON 편집**: 합성된 JSON 구조 및 QA(질의응답) 쌍을 직접 수정 가능.
- **DB 연동**: 검증 완료된 결과물을 도메인별 컬렉션을 지정하여 MongoDB에 저장.

## 사전 요구 사항 (Prerequisites)
- **Python 3.12+**
- **uv** (의존성 관리 도구)
- **Node.js** (프론트엔드 빌드용, 빌드된 정적 파일이 있다면 선택 사항)
- **MongoDB 접속 권한**: 유효한 MongoDB 연결 문자열 또는 IP 접근 허용 필요.

## 설정 (Setup)

1.  **의존성 설치**
    프로젝트 루트 경로에서 실행하세요:
    ```bash
    uv sync
    ```

2.  **출력 데이터 준비**
    이 도구는 `output.json` 파일이 필요합니다 (보통 `pipeline_ui` 실행 결과로 생성됨).

## 사용 방법 (Usage)

### 서버 실행
`uv`를 사용하여 FastAPI 서버를 실행합니다:

```bash
# 프로젝트 루트에서 실행
# 기본적으로 ./output.json 파일을 찾습니다.
uv run annotate_tools/server.py

# 특정 파일 경로 지정
uv run annotate_tools/server.py --file path/to/your/output.json

# MongoDB 비밀번호 지정 (선택 사항, UI에서 입력하거나 환경변수 MONGODB_PASSWORD 사용 가능)
uv run annotate_tools/server.py --password YOUR_DB_PASSWORD
```

### 작업 절차
1.  브라우저에서 `http://localhost:8000`으로 접속합니다.
2.  **Original Image(원본)**, **Parsed HTML(파싱됨)**, **Synthetic HTML(합성됨)**을 확인합니다.
3.  수정이 필요한 경우 **Synthetic JSON** 또는 **QA Pairs** 내용을 편집합니다.
4.  **Save Locally (로컬 저장)**: 로컬 파일(`output.json`)을 업데이트합니다.
5.  **Save to DB (DB 저장)**: 
    - "Save to DB" 버튼을 클릭합니다.
    - 적절한 **Domain (Collection Name)**을 선택합니다.
    - DB 비밀번호를 입력합니다 (환경변수로 설정된 경우 생략 가능).
    - "Confirm Save"를 눌러 MongoDB에 문서를 저장합니다.

## 개발 정보
- 프론트엔드: `App.tsx` (React/Vite)
- 백엔드: `server.py` (FastAPI)
