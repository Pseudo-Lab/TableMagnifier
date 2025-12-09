"""
Gemini API Pulling 테스트 코드
간단한 LangGraph 예제를 통해 API 풀링이 잘 동작하는지 테스트
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

from polling_gemini import create_gemini_chat_model, ainvoke_gemini, get_gemini_pool


# State 정의
class State(TypedDict):
    """LangGraph 상태 정의"""
    messages: Annotated[list, add_messages]
    counter: int


def test_simple_call():
    """1. 간단한 단일 호출 테스트"""
    print("\n" + "="*60)
    print("테스트 1: 간단한 단일 API 호출")
    print("="*60)
    
    try:
        model = create_gemini_chat_model()
        
        # 단일 메시지 호출
        messages = [HumanMessage(content="Hi! Please introduce yourself in one sentence.")]
        response = model.invoke(messages)
        
        print(f"\n입력: {messages[0].content}")
        print(f"응답: {response.content}")
        print("\n✅ 테스트 1 성공!")
        
        # API Pool 상태 확인
        status = model.get_pool_status()
        print(f"\n현재 사용 중인 키: {status['current_key']['name']}")
        
        return True
    except Exception as e:
        print(f"\n❌ 테스트 1 실패: {e}")
        return False


def test_langgraph_simple():
    """2. 간단한 LangGraph 통합 테스트"""
    print("\n" + "="*60)
    print("테스트 2: 간단한 LangGraph 통합")
    print("="*60)
    
    try:
        # Gemini 모델 생성
        model = create_gemini_chat_model()
        
        # 챗봇 노드 정의
        def chatbot(state: State):
            """메시지에 대한 응답 생성"""
            response = model.invoke(state["messages"])
            return {"messages": [response]}
        
        # 그래프 생성
        graph_builder = StateGraph(State)
        graph_builder.add_node("chatbot", chatbot)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_edge("chatbot", END)
        graph = graph_builder.compile()
        
        # 그래프 실행
        user_input = "What is the capital of France? Answer in one word."
        print(f"\n사용자 입력: {user_input}")
        
        result = graph.invoke({
            "messages": [HumanMessage(content=user_input)],
            "counter": 0
        })
        
        for msg in result["messages"]:
            if isinstance(msg, AIMessage):
                print(f"AI 응답: {msg.content}")
        
        print("\n✅ 테스트 2 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 2 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_langgraph_conversation():
    """3. 대화형 LangGraph 테스트 (여러 턴)"""
    print("\n" + "="*60)
    print("테스트 3: 대화형 LangGraph (3턴)")
    print("="*60)
    
    try:
        # Gemini 모델 생성
        model = create_gemini_chat_model()
        
        # 대화 카운터 증가 노드
        def increment_counter(state: State):
            """카운터 증가"""
            return {"counter": state["counter"] + 1}
        
        # 챗봇 노드
        def chatbot(state: State):
            """메시지에 대한 응답 생성"""
            response = model.invoke(state["messages"])
            return {"messages": [response]}
        
        # 종료 조건 체크
        def should_continue(state: State):
            """3턴이 지나면 종료"""
            if state["counter"] >= 3:
                return "end"
            return "continue"
        
        # 그래프 생성
        graph_builder = StateGraph(State)
        graph_builder.add_node("increment", increment_counter)
        graph_builder.add_node("chatbot", chatbot)
        
        graph_builder.add_edge(START, "increment")
        graph_builder.add_edge("increment", "chatbot")
        graph_builder.add_conditional_edges(
            "chatbot",
            should_continue,
            {
                "continue": "increment",
                "end": END
            }
        )
        
        graph = graph_builder.compile()
        
        # 초기 상태
        initial_messages = [
            HumanMessage(content="Count from 1 to 3, one number at a time. Start now.")
        ]
        
        print(f"\n초기 입력: {initial_messages[0].content}")
        
        # 그래프 실행 (스트림으로 각 턴 확인)
        for i, event in enumerate(graph.stream({
            "messages": initial_messages,
            "counter": 0
        })):
            if "chatbot" in event:
                messages = event["chatbot"]["messages"]
                for msg in messages:
                    if isinstance(msg, AIMessage):
                        print(f"\n턴 {i}: {msg.content}")
        
        print("\n✅ 테스트 3 성공!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 3 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_key_rotation_simulation():
    """4. API 키 로테이션 시뮬레이션 (수동 확인용)"""
    print("\n" + "="*60)
    print("테스트 4: API 키 상태 확인")
    print("="*60)
    
    try:
        model = create_gemini_chat_model()
        
        # 여러 번 호출하여 키 상태 확인
        print("\n5번의 API 호출을 수행합니다...")
        
        for i in range(5):
            messages = [HumanMessage(content=f"Say 'Test {i+1}' in Korean.")]
            response = model.invoke(messages)
            
            status = model.get_pool_status()
            current_key = status['current_key']
            
            print(f"\n호출 #{i+1}:")
            print(f"  - 응답: {response.content[:50]}...")
            print(f"  - 사용 키: {current_key['name']}")
            print(f"  - 실패 횟수: {current_key['failed_count']}")
        
        # 전체 키 상태 출력
        print("\n전체 API 키 상태:")
        all_keys = model.get_pool_status()['all_keys']
        for key in all_keys:
            print(f"  - {key['name']}: "
                  f"실패 {key['failed_count']}회, "
                  f"활성화: {key['enabled']}")
        
        print("\n✅ 테스트 4 성공!")
        print("\n💡 참고: 실제 API 할당량 초과 시 자동으로 다음 키로 전환됩니다.")
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 4 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_async_simple_call():
    """5. 비동기 단일 호출 테스트"""
    print("\n" + "="*60)
    print("테스트 5: 비동기 단일 API 호출")
    print("="*60)
    
    async def async_test():
        try:
            # 비동기 함수 사용
            response = await ainvoke_gemini("Hi! Tell me a fun fact about Python programming in one sentence.")
            
            print(f"\n응답: {response}")
            print("\n✅ 테스트 5 성공!")
            return True
        except Exception as e:
            print(f"\n❌ 테스트 5 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # asyncio.run으로 비동기 함수 실행
    return asyncio.run(async_test())


def test_async_concurrent_calls():
    """6. 비동기 동시 호출 테스트"""
    print("\n" + "="*60)
    print("테스트 6: 비동기 동시 호출 (3개)")
    print("="*60)
    
    async def async_test():
        try:
            import time
            start_time = time.time()
            
            # 3개의 요청을 동시에 처리
            questions = [
                "What is 1+1?",
                "What is the capital of France?",
                "Name one programming language.",
            ]
            
            print("\n3개의 요청을 동시에 처리합니다...")
            
            # asyncio.gather로 동시 실행
            tasks = [ainvoke_gemini(q) for q in questions]
            responses = await asyncio.gather(*tasks)
            
            elapsed = time.time() - start_time
            
            for i, (q, r) in enumerate(zip(questions, responses), 1):
                print(f"\n질문 {i}: {q}")
                print(f"응답 {i}: {r[:100]}...")
            
            print(f"\n⏱️  총 소요 시간: {elapsed:.2f}초")
            print("✅ 테스트 6 성공!")
            return True
            
        except Exception as e:
            print(f"\n❌ 테스트 6 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return asyncio.run(async_test())


def test_async_langgraph():
    """7. 비동기 LangGraph 통합 테스트"""
    print("\n" + "="*60)
    print("테스트 7: 비동기 LangGraph 통합")
    print("="*60)
    
    async def async_test():
        try:
            model = create_gemini_chat_model()
            
            # 비동기 챗봇 노드
            async def async_chatbot(state: State):
                """비동기로 응답 생성"""
                messages = state["messages"]
                response = await model.ainvoke(messages)
                return {"messages": [response]}
            
            # 그래프 생성
            graph_builder = StateGraph(State)
            graph_builder.add_node("chatbot", async_chatbot)
            graph_builder.add_edge(START, "chatbot")
            graph_builder.add_edge("chatbot", END)
            graph = graph_builder.compile()
            
            # 비동기 실행
            user_input = "Say 'Hello' in Korean."
            print(f"\n사용자 입력: {user_input}")
            
            result = await graph.ainvoke({
                "messages": [HumanMessage(content=user_input)],
                "counter": 0
            })
            
            for msg in result["messages"]:
                if isinstance(msg, AIMessage):
                    print(f"AI 응답: {msg.content}")
            
            print("\n✅ 테스트 7 성공!")
            return True
            
        except Exception as e:
            print(f"\n❌ 테스트 7 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return asyncio.run(async_test())


def test_async_pool_direct():
    """8. Pool 객체로 비동기 호출 테스트"""
    print("\n" + "="*60)
    print("테스트 8: Pool 객체 비동기 호출")
    print("="*60)
    
    async def async_test():
        try:
            pool = get_gemini_pool()
            
            # 비동기로 여러 요청 순차 처리
            questions = [
                "Count: 1",
                "Count: 2",
                "Count: 3",
            ]
            
            print("\n비동기로 3개 요청을 순차 처리합니다...")
            for i, question in enumerate(questions, 1):
                response = await pool.agenerate_content(question)
                print(f"\n요청 {i}: {question}")
                print(f"응답 {i}: {response[:50]}...")
            
            # 현재 키 상태 확인
            status = pool.get_current_key_info()
            print(f"\n현재 사용 중인 키: {status['name']}")
            
            print("\n✅ 테스트 8 성공!")
            return True
            
        except Exception as e:
            print(f"\n❌ 테스트 8 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return asyncio.run(async_test())


def main():
    """모든 테스트 실행"""
    print("\n" + "🚀 " * 20)
    print("Gemini API Pulling 테스트 시작")
    print("🚀 " * 20)
    
    # API 키 설정 확인
    config_path = project_root / "apis" / "gemini_keys.yaml"
    ssh_config_path = project_root / "apis" / "ssh.yaml"
    
    if not config_path.exists() and not ssh_config_path.exists():
        print(f"\n❌ 오류: API 키 설정 파일이 없습니다.")
        print("\n다음 단계를 수행하세요:")
        print("1. apis/ssh.yaml 또는 apis/gemini_keys.yaml 파일을 열어 실제 API 키를 입력하세요")
        print("2. 여러 개의 API 키를 등록할 수 있습니다")
        print("3. Google AI Studio에서 무료 API 키를 발급받을 수 있습니다:")
        print("   https://makersuite.google.com/app/apikey")
        return
    
    # 테스트 실행
    tests = [
        ("단일 호출", test_simple_call),
        ("LangGraph 기본", test_langgraph_simple),
        ("LangGraph 대화", test_langgraph_conversation),
        ("API 키 상태", test_api_key_rotation_simulation),
        ("비동기 단일 호출", test_async_simple_call),
        ("비동기 동시 호출", test_async_concurrent_calls),
        ("비동기 LangGraph", test_async_langgraph),
        ("비동기 Pool 직접", test_async_pool_direct),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except KeyboardInterrupt:
            print("\n\n⚠️  사용자가 테스트를 중단했습니다.")
            break
        except Exception as e:
            print(f"\n❌ 예상치 못한 오류: {e}")
            results.append((name, False))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{status} - {name}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    print(f"\n총 {total_count}개 테스트 중 {success_count}개 성공")
    
    if success_count == total_count:
        print("\n🎉 모든 테스트가 성공했습니다!")
    else:
        print(f"\n⚠️  {total_count - success_count}개의 테스트가 실패했습니다.")


if __name__ == "__main__":
    main()
