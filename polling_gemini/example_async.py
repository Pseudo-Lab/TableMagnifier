"""
비동기 사용 예제 - Gemini API Pulling
비동기로 API를 호출하는 다양한 예제
"""

import sys
import asyncio
import time
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pulling_gemini import ainvoke_gemini, get_gemini_pool, create_gemini_chat_model
from langchain_core.messages import HumanMessage


async def example1_simple_async():
    """예제 1: 가장 간단한 비동기 호출"""
    print("\n" + "="*60)
    print("예제 1: 간단한 비동기 API 호출")
    print("="*60)
    
    # 비동기로 Gemini API 호출
    response = await ainvoke_gemini("Tell me a short joke about async programming.")
    print(f"\n응답:\n{response}")


async def example2_concurrent_requests():
    """예제 2: 여러 요청을 동시에 처리"""
    print("\n" + "="*60)
    print("예제 2: 동시에 여러 요청 처리")
    print("="*60)
    
    start_time = time.time()
    
    questions = [
        "What is Python?",
        "What is JavaScript?",
        "What is Go?",
        "What is Rust?",
        "What is Java?",
    ]
    
    print(f"\n{len(questions)}개의 요청을 동시에 처리합니다...")
    
    # asyncio.gather로 모든 요청을 동시에 처리
    tasks = [ainvoke_gemini(q) for q in questions]
    responses = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    for i, (q, r) in enumerate(zip(questions, responses), 1):
        print(f"\n질문 {i}: {q}")
        print(f"응답 {i}: {r[:80]}...")
    
    print(f"\n⏱️  총 소요 시간: {elapsed:.2f}초")
    print(f"평균 응답 시간: {elapsed/len(questions):.2f}초/요청")


async def example3_sequential_async():
    """예제 3: 순차적 비동기 호출 (await 사용)"""
    print("\n" + "="*60)
    print("예제 3: 순차적 비동기 호출")
    print("="*60)
    
    start_time = time.time()
    
    questions = [
        "Count: 1",
        "Count: 2",
        "Count: 3",
    ]
    
    print("\n순차적으로 처리합니다 (이전 응답을 기다림)...")
    
    for i, question in enumerate(questions, 1):
        response = await ainvoke_gemini(question)
        print(f"\n질문 {i}: {question}")
        print(f"응답 {i}: {response[:50]}...")
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  총 소요 시간: {elapsed:.2f}초")


async def example4_with_pool():
    """예제 4: Pool 객체로 비동기 호출"""
    print("\n" + "="*60)
    print("예제 4: Pool 객체 비동기 사용")
    print("="*60)
    
    pool = get_gemini_pool()
    
    # 비동기 호출
    response1 = await pool.agenerate_content("What is artificial intelligence?")
    print(f"\n응답 1:\n{response1[:100]}...")
    
    # 상태 확인
    status = pool.get_current_key_info()
    print(f"\n현재 사용 중인 키: {status['name']}")
    
    # 동시 호출
    tasks = [
        pool.agenerate_content("Say 'Hello' in Korean."),
        pool.agenerate_content("Say 'Hello' in Japanese."),
        pool.agenerate_content("Say 'Hello' in Spanish."),
    ]
    
    responses = await asyncio.gather(*tasks)
    
    for i, resp in enumerate(responses, 1):
        print(f"\n응답 {i+1}: {resp}")


async def example5_error_handling():
    """예제 5: 비동기에서 에러 처리"""
    print("\n" + "="*60)
    print("예제 5: 비동기 에러 처리")
    print("="*60)
    
    try:
        # 정상 요청
        response = await ainvoke_gemini("Hello!")
        print(f"\n정상 응답: {response[:50]}...")
        
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        
        # Pool 상태 확인
        pool = get_gemini_pool()
        for key_status in pool.get_all_keys_status():
            print(f"\n키 {key_status['name']}: "
                  f"실패 {key_status['failed_count']}회")
            if key_status['last_error']:
                print(f"  에러: {key_status['last_error'][:100]}...")


async def example6_langchain_async():
    """예제 6: LangChain 모델로 비동기 호출"""
    print("\n" + "="*60)
    print("예제 6: LangChain 모델 비동기 사용")
    print("="*60)
    
    model = create_gemini_chat_model()
    
    # 비동기로 여러 메시지 처리
    messages_list = [
        [HumanMessage(content="What is 2+2?")],
        [HumanMessage(content="What is 3+3?")],
        [HumanMessage(content="What is 4+4?")],
    ]
    
    print("\n3개의 계산을 동시에 처리합니다...")
    
    # ainvoke를 사용한 비동기 호출
    tasks = [model.ainvoke(messages) for messages in messages_list]
    responses = await asyncio.gather(*tasks)
    
    for i, response in enumerate(responses, 1):
        print(f"\n응답 {i}: {response.content}")


async def example7_streaming_simulation():
    """예제 7: 스트리밍 시뮬레이션 (순차 처리)"""
    print("\n" + "="*60)
    print("예제 7: 스트리밍 시뮬레이션")
    print("="*60)
    
    questions = [
        "Part 1: Introduction",
        "Part 2: Main content",
        "Part 3: Conclusion",
    ]
    
    print("\n순차적으로 처리하며 실시간으로 출력합니다...\n")
    
    for i, question in enumerate(questions, 1):
        print(f"[처리 중] {question}...", end=" ", flush=True)
        response = await ainvoke_gemini(f"Briefly explain: {question}")
        print(f"✓")
        print(f"  → {response[:60]}...\n")


async def example8_batch_processing():
    """예제 8: 대량 요청 배치 처리"""
    print("\n" + "="*60)
    print("예제 8: 대량 요청 배치 처리")
    print("="*60)
    
    # 10개의 요청을 3개씩 배치로 처리
    all_questions = [f"Question {i}: What is {i} + {i}?" for i in range(1, 11)]
    batch_size = 3
    
    print(f"\n총 {len(all_questions)}개 요청을 {batch_size}개씩 배치 처리합니다...\n")
    
    all_responses = []
    
    for i in range(0, len(all_questions), batch_size):
        batch = all_questions[i:i+batch_size]
        print(f"배치 {i//batch_size + 1} 처리 중... ({len(batch)}개)", end=" ", flush=True)
        
        # 배치 내에서는 동시 처리
        tasks = [ainvoke_gemini(q) for q in batch]
        responses = await asyncio.gather(*tasks)
        all_responses.extend(responses)
        
        print("✓")
    
    print(f"\n총 {len(all_responses)}개의 응답을 받았습니다.")
    
    # 몇 개만 샘플 출력
    for i in range(min(3, len(all_responses))):
        print(f"\n응답 {i+1}: {all_responses[i][:60]}...")


async def main():
    """모든 예제 실행"""
    print("\n" + "🌟 " * 20)
    print("Gemini API Pulling - 비동기 예제")
    print("🌟 " * 20)
    
    # API 키 설정 확인
    config_path = project_root / "apis" / "gemini_keys.yaml"
    if not config_path.exists():
        print(f"\n❌ 오류: API 키 설정 파일이 없습니다: {config_path}")
        print("\napis/gemini_keys.yaml 파일을 생성하고 API 키를 입력하세요.")
        return
    
    try:
        # 각 예제 실행
        await example1_simple_async()
        input("\n계속하려면 Enter를 누르세요...")
        
        await example2_concurrent_requests()
        input("\n계속하려면 Enter를 누르세요...")
        
        await example3_sequential_async()
        input("\n계속하려면 Enter를 누르세요...")
        
        await example4_with_pool()
        input("\n계속하려면 Enter를 누르세요...")
        
        await example5_error_handling()
        input("\n계속하려면 Enter를 누르세요...")
        
        await example6_langchain_async()
        input("\n계속하려면 Enter를 누르세요...")
        
        await example7_streaming_simulation()
        input("\n계속하려면 Enter를 누르세요...")
        
        await example8_batch_processing()
        
        print("\n" + "="*60)
        print("✅ 모든 예제가 완료되었습니다!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("\nAPI 키가 올바르게 설정되어 있는지 확인하세요.")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # asyncio.run()으로 메인 함수 실행
    asyncio.run(main())
