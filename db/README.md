# Data Handling Module Guide

`db/data_handling.py`는 **Google Drive**에 저장된 테이블 이미지 데이터를 자동으로 탐색하고, 해당 파일의 메타데이터를 **MongoDB**에 적재하는 스크립트입니다.

## 📋 사전 준비 (Prerequisites)

이 스크립트를 실행하기 위해서는 다음과 같은 준비가 필요합니다.

### 1. Google Drive API 설정
1.  [Google Cloud Console](https://console.cloud.google.com/)에 접속하여 프로젝트를 생성하거나 선택합니다.
2.  **"API 및 서비스" > "라이브러리"** 메뉴에서 **"Google Drive API"**를 검색하고 활성화합니다.
3.  **"API 및 서비스" > "사용자 인증 정보"** 메뉴로 이동합니다.
4.  **"사용자 인증 정보 만들기" > "OAuth 클라이언트 ID"**를 선택합니다.
    *   애플리케이션 유형: **데스크톱 앱**
5.  생성된 클라이언트 ID의 JSON 파일을 다운로드하고 `client.json`으로 이름을 변경합니다.
6.  프로젝트 루트에 `info` 폴더를 만들고, 그 안에 `client.json` 파일을 위치시킵니다.
    *   경로: `TableMagnifier/info/client.json`

### 2. MongoDB 설정
1.  [MongoDB Atlas](https://www.mongodb.com/atlas) 등을 사용하여 MongoDB 클러스터를 준비합니다.
2.  데이터베이스 접속 정보를 확인합니다 (Connection URI).
3.  스크립트 실행 시 필요한 비밀번호를 준비합니다.

### 3. 의존성 설치
프로젝트 루트에서 다음 명령어를 실행하여 필요한 패키지를 설치합니다. (이미 프로젝트 의존성에 포함되어 있습니다.)

```bash
uv sync
# 또는
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib pandas pymongo tqdm
```

---

## ⚙️ 설정 및 실행 (Configuration & Usage)

### 환경 변수 설정
스크립트 실행 전, 다음 환경 변수를 설정하면 코드를 수정하지 않고도 실행할 수 있습니다.

*   `GOOGLE_DRIVE_START_FOLDER_ID`: 탐색을 시작할 Google Drive의 최상위 폴더 ID입니다. (브라우저 주소창의 폴더 ID 확인)
*   `GOOGLE_DRIVE_CLIENT_JSON`: `client.json` 파일의 경로입니다. (기본값: `info/client.json`)

### 실행 방법

터미널에서 다음과 같이 실행합니다.

**PowerShell 예시:**
```powershell
# 환경 변수 설정 (필요시)
$env:GOOGLE_DRIVE_START_FOLDER_ID = "여기에_폴더_ID_입력"

# 스크립트 실행
uv run python db/data_handling.py
```

> **참고:** 스크립트 코드 내의 `PASSWORD = ""` 부분에 MongoDB 비밀번호를 직접 입력하거나, 보안을 위해 환경 변수로 처리하는 것을 권장합니다. 현재 코드는 실행 시 `database_data_insert(PASSWORD)` 함수를 호출하도록 되어 있습니다.

---

## 🔍 주요 함수 설명

| 함수명 | 설명 |
| :--- | :--- |
| `get_drive_service()` | Google Drive API 서비스 객체를 생성하고 인증을 처리합니다. 최초 실행 시 브라우저 창이 열려 로그인을 요청할 수 있습니다. |
| `find_root_folder(service)` | 'root' 폴더를 찾아 반환합니다. |
| `child_folders(service, folder_id)` | 특정 폴더 ID의 하위 폴더 목록을 조회합니다. |
| `list_all_files_in_folder(service, folder_id)` | 특정 폴더 내의 모든 파일(하위 폴더 제외) 목록을 조회합니다. 페이징을 처리하여 1000개 이상의 파일도 가져옵니다. |
| `download_file_bytes(service, file_id)` | Google Drive의 파일을 바이트 스트림으로 다운로드합니다. |
| `save_image_to_local(file_bytes, file_path)` | 다운로드한 바이트 데이터를 로컬 파일로 저장합니다. |
| `mongo_client(PASSWORD, collection_name)` | MongoDB에 연결하고 특정 도메인(Collection)을 선택합니다. |
| `database_data_insert(PASSWORD)` | **메인 실행 로직**입니다. 설정된 시작 폴더부터 하위 폴더를 순회하며 파일 정보를 수집하고 MongoDB에 `UserDict` 형태로 저장합니다. |

## 📁 데이터 구조
MongoDB에 저장되는 데이터 형식은 다음과 같습니다 (`table_json_format` 참조):

```json
{
    "Domain": "도메인명 (폴더명)",
    "ImageFileName": "파일명",
    "ImageFileID": "Google Drive 파일 ID",
    "HTMLText": "",
    "QAPair": {},
    "Evaluation_Result": {}
}
```
