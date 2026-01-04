# Gemini API Pulling System - 사용 가이드

이 모듈은 여러 Gemini API 키를 자동으로 로테이션하며 사용하는 풀링 시스템입니다.  
무료 사용량이 끝나면 자동으로 다음 API 키로 전환되어 중단 없이 작업할 수 있습니다.

---

## 📋 목차

1. [설치 방법](#1-설치-방법)
2. [API 키 설정](#2-api-키-설정)
3. [기본 사용법](#3-기본-사용법)
4. [LangGraph 통합](#4-langgraph-통합)
5. [고급 사용법](#5-고급-사용법)
6. [테스트 실행](#6-테스트-실행)
7. [트러블슈팅](#7-트러블슈팅)

---

## 1. 설치 방법

### 필수 패키지 설치

프로젝트 루트 디렉토리에서 다음 명령어를 실행하세요:

```bash
uv venv .venv
uv sync
uv add -r requirements.txt
```

설치되는 패키지:
- `google-generativeai`: Gemini API 클라이언트
- `pyyaml`: YAML 설정 파일 파싱
- `langgraph`: LangGraph 프레임워크
- `langchain-core`: LangChain 메시지 타입
- `langchain`: LangChain 기본 라이브러리

---

## 2. API 키 설정

### 2.1 API 키 발급

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. "Create API Key" 또는 "Get API Key" 클릭
3. 새 프로젝트 선택 또는 생성
4. API 키 복사

💡 **팁**: 무료 할당량을 최대한 활용하려면 여러 개의 API 키를 발급받으세요!

### 2.2 설정 파일 작성

`apis/gemini_keys.yaml` 파일을 열고 발급받은 API 키를 입력하세요:

```yaml
api_keys:
  - key: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # 첫 번째 키
    name: "primary_key"
    enabled: true
    
  - key: "AIzaSyYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"  # 두 번째 키
    name: "backup_key"
    enabled: true
    
  - key: "AIzaSyZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"  # 세 번째 키
    name: "emergency_key"
    enabled: true

settings:
  model: "gemini-2.5-flash"       # 사용할 모델 (gemini-1.5-pro, gemini-2.5-flash 등)
  temperature: 0.1                # 응답 온도 (0.0~1.0)
  max_retries: 3                  # API 호출 실패 시 재시도 횟수
  retry_delay: 2                  # 재시도 간 대기 시간 (초)
```

#### 설정 항목 설명

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `key` | Gemini API 키 | (필수) |
| `name` | 키 식별용 이름 | unknown |
| `enabled` | 키 활성화 여부 | true |
| `model` | 사용할 Gemini 모델 | gemini-2.5-flash |
| `temperature` | 응답의 창의성 (0: 일관적, 1: 창의적) | 0.1 |
| `max_retries` | 재시도 횟수 | 3 |
| `retry_delay` | 재시도 대기 시간(초) | 2 |

### 2.3 보안 주의사항

⚠️ **중요**: API 키를 절대 Git에 커밋하지 마세요!

- `.gitignore`에 `gemini_keys.yaml`이 포함되어 있습니다
- API 키가 노출되면 즉시 Google AI Studio에서 해당 키를 삭제하세요
- 프로덕션 환경에서는 환경 변수나 보안 볼트 사용을 권장합니다

---

## 3. 기본 사용법

### 3.1 동기 방식 - 가장 간단한 방법

```python
from pulling_gemini import invoke_gemini

# 한 줄로 API 호출 (동기)
response = invoke_gemini("안녕하세요! 자기소개를 한 문장으로 해주세요.")
print(response)
```

### 3.2 비동기 방식 - 간단한 방법

```python
from pulling_gemini import ainvoke_gemini
import asyncio

async def main():
    # 비동기로 API 호출
    response = await ainvoke_gemini("안녕하세요! 자기소개를 한 문장으로 해주세요.")
    print(response)

# 실행
asyncio.run(main())
```

### 3.3 API Pool 직접 사용 (동기)

```python
from pulling_gemini import get_gemini_pool

# API Pool 가져오기
pool = get_gemini_pool()

# 컨텐츠 생성
response = pool.generate_content("Python에서 리스트와 튜플의 차이점을 설명해주세요.")
print(response)

# 현재 사용 중인 API 키 정보 확인
status = pool.get_current_key_info()
print(f"현재 키: {status['name']}")
print(f"실패 횟수: {status['failed_count']}")
```

### 3.4 API Pool 직접 사용 (비동기)

```python
from pulling_gemini import get_gemini_pool
import asyncio

async def main():
    pool = get_gemini_pool()
    
    # 비동기로 컨텐츠 생성
    response = await pool.agenerate_content("Python에서 리스트와 튜플의 차이점을 설명해주세요.")
    print(response)
    
    # 상태 확인
    status = pool.get_current_key_info()
    print(f"현재 키: {status['name']}")

asyncio.run(main())
```

### 3.5 여러 번 호출하기 (동기 - 순차)

```python
from pulling_gemini import invoke_gemini

questions = [
    "Python이란 무엇인가요?",
    "대한민국의 수도는?",
    "모나리자를 그린 화가는?",
]

for i, question in enumerate(questions, 1):
    print(f"\n질문 {i}: {question}")
    response = invoke_gemini(question)
    print(f"답변: {response}")
```

### 3.6 동시에 여러 요청 처리 (비동기 - 병렬)

```python
from pulling_gemini import ainvoke_gemini
import asyncio

async def main():
    questions = [
        "Python이란 무엇인가요?",
        "대한민국의 수도는?",
        "모나리자를 그린 화가는?",
    ]
    
    # asyncio.gather로 동시 처리
    tasks = [ainvoke_gemini(q) for q in questions]
    responses = await asyncio.gather(*tasks)
    
    for i, (q, r) in enumerate(zip(questions, responses), 1):
        print(f"\n질문 {i}: {q}")
        print(f"답변 {i}: {r}")

asyncio.run(main())
```

💡 **성능 팁**: 비동기 방식으로 여러 요청을 동시에 처리하면 전체 처리 시간을 크게 단축할 수 있습니다!

---

## 4. LangGraph 통합

### 4.1 기본 LangGraph 사용

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

from pulling_gemini import create_gemini_chat_model

# State 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Gemini 모델 생성 (자동 키 로테이션 포함)
model = create_gemini_chat_model()

# 챗봇 노드 정의
def chatbot(state: State):
    """사용자 메시지에 대한 응답 생성"""
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# 그래프 생성
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

# 실행
result = graph.invoke({
    "messages": [HumanMessage(content="안녕하세요!")]
})

# 결과 출력
for msg in result["messages"]:
    if isinstance(msg, AIMessage):
        print(f"AI: {msg.content}")
```

### 4.2 비동기 LangGraph 사용

```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage
import asyncio

from pulling_gemini import create_gemini_chat_model

class State(TypedDict):
    messages: Annotated[list, add_messages]

model = create_gemini_chat_model()

# 비동기 챗봇 노드
async def async_chatbot(state: State):
    """비동기로 응답 생성"""
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}

# 그래프 생성
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", async_chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

async def main():
    # 비동기 실행
    result = await graph.ainvoke({
        "messages": [HumanMessage(content="안녕하세요!")]
    })
    
    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"AI: {msg.content}")

asyncio.run(main())
```

### 4.3 대화형 LangGraph (멀티턴)

```python
from langgraph.graph import StateGraph, START, END
from pulling_gemini import create_gemini_chat_model

class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]
    turn_count: int

model = create_gemini_chat_model()

def chatbot(state: ConversationState):
    """응답 생성 및 턴 카운트 증가"""
    response = model.invoke(state["messages"])
    return {
        "messages": [response],
        "turn_count": state["turn_count"] + 1
    }

def should_continue(state: ConversationState):
    """5턴 후 종료"""
    if state["turn_count"] >= 5:
        return "end"
    return "continue"

# 그래프 구성
graph_builder = StateGraph(ConversationState)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges(
    "chatbot",
    should_continue,
    {
        "continue": "chatbot",
        "end": END
    }
)

graph = graph_builder.compile()

# 실행 (스트리밍으로 각 턴 확인)
print("대화 시작...")
for event in graph.stream({
    "messages": [HumanMessage(content="1부터 5까지 세어주세요. 한 번에 하나씩만요.")],
    "turn_count": 0
}):
    if "chatbot" in event:
        for msg in event["chatbot"]["messages"]:
            if isinstance(msg, AIMessage):
                print(f"\nAI: {msg.content}")
```

### 4.3 복잡한 그래프 예제

```python
from langgraph.graph import StateGraph, START, END
from pulling_gemini import create_gemini_chat_model

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    task_type: str
    result: str

model = create_gemini_chat_model()

def classifier(state: AgentState):
    """작업 유형 분류"""
    prompt = f"다음 요청의 유형을 'question', 'creative', 'coding' 중 하나로 분류하세요: {state['messages'][-1].content}"
    response = model.invoke([HumanMessage(content=prompt)])
    
    task_type = response.content.lower()
    if 'creative' in task_type:
        return {"task_type": "creative"}
    elif 'coding' in task_type:
        return {"task_type": "coding"}
    else:
        return {"task_type": "question"}

def handle_question(state: AgentState):
    """질문 답변"""
    response = model.invoke(state["messages"])
    return {"messages": [response], "result": "answered"}

def handle_creative(state: AgentState):
    """창의적 작업"""
    # Temperature를 높여서 창의적인 응답 생성
    creative_model = create_gemini_chat_model()
    response = creative_model.invoke(state["messages"])
    return {"messages": [response], "result": "created"}

def handle_coding(state: AgentState):
    """코딩 작업"""
    # Temperature를 낮춰서 정확한 코드 생성
    response = model.invoke(state["messages"])
    return {"messages": [response], "result": "coded"}

def route_task(state: AgentState):
    """작업 유형에 따라 라우팅"""
    return state["task_type"]

# 그래프 구성
graph_builder = StateGraph(AgentState)
graph_builder.add_node("classifier", classifier)
graph_builder.add_node("question", handle_question)
graph_builder.add_node("creative", handle_creative)
graph_builder.add_node("coding", handle_coding)

graph_builder.add_edge(START, "classifier")
graph_builder.add_conditional_edges(
    "classifier",
    route_task,
    {
        "question": "question",
        "creative": "creative",
        "coding": "coding"
    }
)
graph_builder.add_edge("question", END)
graph_builder.add_edge("creative", END)
graph_builder.add_edge("coding", END)

graph = graph_builder.compile()

# 실행
result = graph.invoke({
    "messages": [HumanMessage(content="Python에서 리스트를 정렬하는 코드를 작성해주세요.")],
    "task_type": "",
    "result": ""
})

print(f"작업 유형: {result['task_type']}")
print(f"결과: {result['messages'][-1].content}")
```

---

## 5. 고급 사용법

### 5.1 커스텀 설정

```python
from pulling_gemini import create_gemini_chat_model

# 특정 설정 파일 경로 지정
model = create_gemini_chat_model(
    config_path="/path/to/your/gemini_keys.yaml"
)

# Generation 파라미터 커스터마이징
response = model.invoke(
    [HumanMessage(content="커피숍을 위한 창의적인 슬로건을 만들어주세요.")],
    generation_config={
        'temperature': 0.9,       # 높은 창의성
        'top_p': 0.95,
        'max_output_tokens': 2048,
    }
)
```

### 5.2 API Pool 상태 모니터링

```python
from pulling_gemini import create_gemini_chat_model

model = create_gemini_chat_model()

# API 호출
response = model.invoke([HumanMessage(content="안녕하세요")])

# 전체 상태 확인
status = model.get_pool_status()

# 현재 키 정보
current = status['current_key']
print(f"현재 사용 키: {current['name']}")
print(f"키 인덱스: {current['index'] + 1} / {current['total_keys']}")
print(f"실패 횟수: {current['failed_count']}")
if current['last_error']:
    print(f"마지막 에러: {current['last_error']}")

# 모든 키 상태
print("\n전체 API 키 상태:")
for key in status['all_keys']:
    status_icon = "✅" if key['enabled'] else "❌"
    print(f"{status_icon} {key['name']}: 실패 {key['failed_count']}회")
    if key['last_error']:
        print(f"   └─ 에러: {key['last_error'][:50]}...")
```

### 5.3 에러 처리

```python
from pulling_gemini import get_gemini_pool

pool = get_gemini_pool()

try:
    response = pool.generate_content("당신의 질문")
    print(response)
    
except Exception as e:
    print(f"❌ 모든 API 키로 시도했으나 실패: {e}")
    
    # 에러 발생 시 각 키의 상태 확인
    print("\n각 키의 상태:")
    for key_status in pool.get_all_keys_status():
        print(f"\n키: {key_status['name']}")
        print(f"  - 활성화: {key_status['enabled']}")
        print(f"  - 실패 횟수: {key_status['failed_count']}")
        if key_status['last_error']:
            print(f"  - 마지막 에러: {key_status['last_error']}")
```

### 5.4 수동 키 전환

```python
from pulling_gemini import get_gemini_pool

pool = get_gemini_pool()

# 현재 키 정보
print(f"현재 키: {pool.get_current_key_info()['name']}")

# 다음 키로 수동 전환
if pool._rotate_key():
    print(f"전환 후 키: {pool.get_current_key_info()['name']}")
else:
    print("사용 가능한 다른 키가 없습니다.")
```

### 5.5 프로그래밍 방식으로 키 추가

```python
from pulling_gemini.api_pool import GeminiAPIPool, APIKeyInfo

# 커스텀 Pool 생성
pool = GeminiAPIPool()

# 런타임에 키 추가 (권장하지 않음 - 설정 파일 사용 권장)
new_key = APIKeyInfo(
    key="NEW_API_KEY",
    name="runtime_key",
    enabled=True
)
pool.api_keys.append(new_key)
```

---

## 6. 테스트 실행

### 6.1 전체 테스트

```bash
cd pulling_gemini
python test_pulling.py
```

테스트 항목:
1. ✅ 단일 API 호출 테스트
2. ✅ 기본 LangGraph 통합 테스트
3. ✅ 3턴 대화 시뮬레이션
4. ✅ API 키 상태 모니터링

### 6.2 간단한 예제

```bash
python pulling_gemini/example_simple.py
```

예제 내용:
1. 간단한 API 호출
2. 여러 번 호출
3. Pool 객체로 상태 모니터링
4. 커스텀 설정 사용

### 6.3 수동 테스트

```python
# Python 인터프리터에서
from pulling_gemini import invoke_gemini

print(invoke_gemini("테스트 메시지"))
```

---

## 7. 트러블슈팅

### 7.1 일반적인 문제

#### Q1: "API 키 설정 파일을 찾을 수 없습니다" 에러

```
FileNotFoundError: API 키 설정 파일을 찾을 수 없습니다: .../apis/gemini_keys.yaml
```

**해결 방법**:
1. `apis/gemini_keys.yaml` 파일이 존재하는지 확인
2. 파일 경로가 올바른지 확인
3. 파일 권한 확인

#### Q2: "활성화된 API 키가 없습니다" 에러

```
ValueError: 활성화된 API 키가 없습니다. gemini_keys.yaml을 확인하세요.
```

**해결 방법**:
1. `gemini_keys.yaml`에서 최소 하나의 키가 `enabled: true`인지 확인
2. 실제 API 키가 입력되어 있는지 확인 (YOUR_GEMINI_API_KEY_X가 아닌)

#### Q3: "모든 API 키로 시도했으나 실패" 에러

```
Exception: 모든 API 키로 시도했으나 실패했습니다.
```

**해결 방법**:
1. API 키가 유효한지 Google AI Studio에서 확인
2. 각 키의 할당량이 모두 소진되었는지 확인
3. 인터넷 연결 확인
4. 다음 명령어로 키 상태 확인:
   ```python
   from pulling_gemini import get_gemini_pool
   pool = get_gemini_pool()
   print(pool.get_all_keys_status())
   ```

#### Q4: LangGraph import 에러

```
ImportError: cannot import name 'StateGraph' from 'langgraph.graph'
```

**해결 방법**:
```bash
pip install --upgrade langgraph langchain-core langchain
```

### 7.2 API 키 관련

#### API 키 유효성 확인

```python
import google.generativeai as genai

# 특정 키 테스트
genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel('gemini-2.5-flash')
response = model.generate_content("Hello")
print(response.text)  # 성공하면 응답 출력
```

#### 할당량 확인

무료 할당량 (2024년 12월 기준):
- **Gemini 1.5 Flash**: 분당 15 요청, 일일 1,500 요청
- **Gemini 1.5 Pro**: 분당 2 요청, 일일 50 요청

할당량 초과 시:
- 다른 API 키로 자동 전환됨
- 또는 24시간 후 할당량 리셋 대기

### 7.3 성능 최적화

#### 응답 속도가 느린 경우

1. **모델 선택**: `gemini-2.5-flash`가 `gemini-1.5-pro`보다 빠름
   ```yaml
   settings:
     model: "gemini-2.5-flash"  # 더 빠른 모델
   ```

2. **토큰 수 제한**:
   ```python
   pool.generate_content(
       "질문",
       generation_config={'max_output_tokens': 512}
   )
   ```

3. **프롬프트 최적화**: 간결하고 명확한 프롬프트 사용

#### 메모리 사용량이 높은 경우

- Pool 싱글톤 패턴 사용으로 인스턴스 재사용:
  ```python
  from pulling_gemini import get_gemini_pool
  pool = get_gemini_pool()  # 항상 같은 인스턴스 반환
  ```

### 7.4 디버깅

#### 로그 활성화

```python
import logging

# 상세 로그 출력
logging.basicConfig(level=logging.DEBUG)

from pulling_gemini import invoke_gemini
response = invoke_gemini("테스트")
```

#### 상태 덤프

```python
from pulling_gemini import get_gemini_pool
import json

pool = get_gemini_pool()

# 현재 상태를 JSON으로 출력
status = {
    'current_key': pool.get_current_key_info(),
    'all_keys': pool.get_all_keys_status(),
    'settings': pool.settings
}

print(json.dumps(status, indent=2, ensure_ascii=False))
```
