"""
간단한 사용 예제 - Gemini API Pulling
LangGraph 없이 기본적인 사용법을 보여주는 예제
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pulling_gemini import invoke_gemini, get_gemini_pool


def example1_simple_call():
    """예제 1: 가장 간단한 사용법"""
    print("\n" + "="*60)
    print("예제 1: 간단한 API 호출")
    print("="*60)
    
    # 한 줄로 Gemini API 호출
    response = invoke_gemini("Tell me a short joke about programming.")
    print(f"\n응답:\n{response}")


def example2_multiple_calls():
    """예제 2: 여러 번 호출하기"""
    print("\n" + "="*60)
    print("예제 2: 여러 번 호출")
    print("="*60)
    
    questions = [
        "What is Python?",
        "What is the capital of South Korea?",
        "Who painted the Mona Lisa?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n질문 {i}: {question}")
        response = invoke_gemini(question)
        print(f"응답: {response}")


def example3_with_pool():
    """예제 3: Pool 객체 직접 사용"""
    print("\n" + "="*60)
    print("예제 3: Pool 객체로 상태 모니터링")
    print("="*60)
    
    # Pool 객체 가져오기
    pool = get_gemini_pool()
    
    # API 호출
    response = pool.generate_content("What is artificial intelligence?")
    print(f"\n응답:\n{response}")
    
    # 현재 키 상태 확인
    status = pool.get_current_key_info()
    print(f"\n현재 사용 중인 키: {status['name']}")
    print(f"전체 키 개수: {status['total_keys']}")
    print(f"실패 횟수: {status['failed_count']}")
    
    # 모든 키 상태 확인
    print("\n모든 키 상태:")
    for key_status in pool.get_all_keys_status():
        print(f"  - {key_status['name']}: "
              f"활성화={key_status['enabled']}, "
              f"실패={key_status['failed_count']}회")


def example4_custom_settings():
    """예제 4: 커스텀 설정으로 호출"""
    print("\n" + "="*60)
    print("예제 4: 커스텀 설정")
    print("="*60)
    
    pool = get_gemini_pool()
    
    # 높은 temperature로 창의적인 응답 생성
    response = pool.generate_content(
        "Write a creative tagline for a coffee shop.",
        generation_config={
            'temperature': 0.9,
            'max_output_tokens': 100,
        }
    )
    print(f"\n창의적인 응답 (temperature=0.9):\n{response}")
    
    # 낮은 temperature로 일관된 응답 생성
    response = pool.generate_content(
        "What is 2 + 2?",
        generation_config={
            'temperature': 0.1,
        }
    )
    print(f"\n정확한 응답 (temperature=0.1):\n{response}")


def main():
    """모든 예제 실행"""
    print("\n" + "🌟 " * 20)
    print("Gemini API Pulling - 간단한 예제")
    print("🌟 " * 20)
    
    # API 키 설정 확인
    config_path = project_root / "apis" / "gemini_keys.yaml"
    if not config_path.exists():
        print(f"\n❌ 오류: API 키 설정 파일이 없습니다: {config_path}")
        print("\napis/gemini_keys.yaml 파일을 생성하고 API 키를 입력하세요.")
        return
    
    try:
        # 각 예제 실행
        example1_simple_call()
        input("\n계속하려면 Enter를 누르세요...")
        
        example2_multiple_calls()
        input("\n계속하려면 Enter를 누르세요...")
        
        example3_with_pool()
        input("\n계속하려면 Enter를 누르세요...")
        
        example4_custom_settings()
        
        print("\n" + "="*60)
        print("✅ 모든 예제가 완료되었습니다!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("\nAPI 키가 올바르게 설정되어 있는지 확인하세요.")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
