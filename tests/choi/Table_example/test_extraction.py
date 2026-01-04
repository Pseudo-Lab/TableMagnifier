"""
보험 테이블 추출 테스트 코드
Table_example 패키지를 사용하여 이미지에서 테이블을 추출하는 예제
"""

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Table_example import (
    InsuranceTableExtractor,
    extract_table_from_image,
    aextract_table_from_image,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)


def test_prompt_display():
    """1. 프롬프트 내용 확인"""
    print("\n" + "="*70)
    print("테스트 1: 프롬프트 내용 확인")
    print("="*70)
    
    print("\n📋 System Prompt:")
    print("-"*50)
    print(SYSTEM_PROMPT[:500] + "...")
    
    print("\n📋 User Prompt Template (일부):")
    print("-"*50)
    print(USER_PROMPT_TEMPLATE[:500] + "...")
    
    print("\n✅ 프롬프트 로드 성공!")
    return True


def test_extractor_initialization():
    """2. 추출기 초기화 테스트"""
    print("\n" + "="*70)
    print("테스트 2: InsuranceTableExtractor 초기화")
    print("="*70)
    
    try:
        extractor = InsuranceTableExtractor()
        
        status = extractor.get_pool_status()
        print(f"\n현재 사용 중인 키: {status['current_key']['name']}")
        print(f"총 API 키 수: {status['current_key']['total_keys']}")
        
        print("\n✅ 추출기 초기화 성공!")
        return True
        
    except FileNotFoundError as e:
        print(f"\n⚠️ API 키 파일이 없습니다: {e}")
        print("apis/gemini_keys.yaml 파일을 생성하세요.")
        return False
    except Exception as e:
        print(f"\n❌ 초기화 실패: {e}")
        return False


def test_extract_from_sample_image():
    """3. 샘플 이미지에서 테이블 추출 테스트"""
    print("\n" + "="*70)
    print("테스트 3: 샘플 이미지에서 테이블 추출")
    print("="*70)
    
    # 샘플 이미지 경로 확인
    sample_images_dir = project_root / "Table_example" / "sample_images"
    
    if not sample_images_dir.exists():
        print(f"\n⚠️ 샘플 이미지 디렉토리가 없습니다: {sample_images_dir}")
        print("sample_images 폴더에 테스트 이미지를 추가하세요.")
        return None
    
    # 샘플 이미지 찾기
    image_files = list(sample_images_dir.glob("*.png")) + \
                  list(sample_images_dir.glob("*.jpg")) + \
                  list(sample_images_dir.glob("*.jpeg"))
    
    if not image_files:
        print(f"\n⚠️ 샘플 이미지가 없습니다: {sample_images_dir}")
        print("PNG, JPG, JPEG 형식의 이미지를 추가하세요.")
        return None
    
    # 첫 번째 이미지로 테스트
    image_path = image_files[0]
    print(f"\n테스트 이미지: {image_path.name}")
    
    try:
        # 테이블 추출
        result = extract_table_from_image(image_path)
        
        print("\n📊 추출 결과:")
        print("-"*50)
        print(result)
        print("-"*50)
        
        print("\n✅ 테이블 추출 성공!")
        return result
        
    except Exception as e:
        print(f"\n❌ 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_extract_with_ocr_reference():
    """4. OCR 참조 텍스트와 함께 추출 테스트"""
    print("\n" + "="*70)
    print("테스트 4: OCR 참조 텍스트와 함께 추출")
    print("="*70)
    
    sample_images_dir = project_root / "Table_example" / "sample_images"
    
    if not sample_images_dir.exists():
        print(f"\n⚠️ 샘플 이미지 디렉토리가 없습니다.")
        return None
    
    image_files = list(sample_images_dir.glob("*.png")) + \
                  list(sample_images_dir.glob("*.jpg"))
    
    if not image_files:
        print(f"\n⚠️ 샘플 이미지가 없습니다.")
        return None
    
    image_path = image_files[0]
    print(f"\n테스트 이미지: {image_path.name}")
    
    # OCR 참조 텍스트 예시 (실제로는 OCR 결과를 사용)
    sample_ocr_markdown = """| 구분 | 보험기간 | 납입기간 | 가입금액 |
| 상해사망 | 80세 | 20년 | 1억원 |
| 질병사망 | 80세 | 20년 | 5천만원 |"""
    
    try:
        result = extract_table_from_image(
            image_path,
            ocr_markdown=sample_ocr_markdown
        )
        
        print("\n📊 추출 결과 (OCR 참조 사용):")
        print("-"*50)
        print(result)
        print("-"*50)
        
        print("\n✅ OCR 참조 추출 성공!")
        return result
        
    except Exception as e:
        print(f"\n❌ 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_async_extraction():
    """5. 비동기 테이블 추출 테스트"""
    print("\n" + "="*70)
    print("테스트 5: 비동기 테이블 추출")
    print("="*70)
    
    async def async_test():
        sample_images_dir = project_root / "Table_example" / "sample_images"
        
        if not sample_images_dir.exists():
            print(f"\n⚠️ 샘플 이미지 디렉토리가 없습니다.")
            return None
        
        image_files = list(sample_images_dir.glob("*.png")) + \
                      list(sample_images_dir.glob("*.jpg"))
        
        if not image_files:
            print(f"\n⚠️ 샘플 이미지가 없습니다.")
            return None
        
        image_path = image_files[0]
        print(f"\n테스트 이미지: {image_path.name}")
        
        try:
            import time
            start_time = time.time()
            
            result = await aextract_table_from_image(image_path)
            
            elapsed = time.time() - start_time
            
            print(f"\n⏱️  소요 시간: {elapsed:.2f}초")
            print("\n📊 추출 결과:")
            print("-"*50)
            print(result[:500] + "..." if len(result) > 500 else result)
            print("-"*50)
            
            print("\n✅ 비동기 추출 성공!")
            return result
            
        except Exception as e:
            print(f"\n❌ 추출 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    return asyncio.run(async_test())


def test_multiple_images():
    """6. 여러 이미지 동시 처리 테스트"""
    print("\n" + "="*70)
    print("테스트 6: 여러 이미지 동시 처리 (비동기)")
    print("="*70)
    
    async def async_test():
        sample_images_dir = project_root / "Table_example" / "sample_images"
        
        if not sample_images_dir.exists():
            print(f"\n⚠️ 샘플 이미지 디렉토리가 없습니다.")
            return None
        
        image_files = list(sample_images_dir.glob("*.png")) + \
                      list(sample_images_dir.glob("*.jpg")) + \
                      list(sample_images_dir.glob("*.jpeg"))
        
        if len(image_files) < 2:
            print(f"\n⚠️ 2개 이상의 샘플 이미지가 필요합니다. 현재: {len(image_files)}개")
            return None
        
        # 최대 3개 이미지 처리
        images_to_process = image_files[:3]
        
        print(f"\n처리할 이미지 {len(images_to_process)}개:")
        for img in images_to_process:
            print(f"  - {img.name}")
        
        try:
            import time
            start_time = time.time()
            
            # 동시에 여러 이미지 처리
            tasks = [aextract_table_from_image(img) for img in images_to_process]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            elapsed = time.time() - start_time
            
            print(f"\n⏱️  총 소요 시간: {elapsed:.2f}초")
            
            for i, (img, result) in enumerate(zip(images_to_process, results), 1):
                print(f"\n📊 이미지 {i} ({img.name}) 결과:")
                print("-"*40)
                if isinstance(result, Exception):
                    print(f"❌ 에러: {result}")
                else:
                    print(result[:300] + "..." if len(result) > 300 else result)
            
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            print(f"\n✅ {len(images_to_process)}개 중 {success_count}개 성공!")
            return results
            
        except Exception as e:
            print(f"\n❌ 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    return asyncio.run(async_test())


def main():
    """모든 테스트 실행"""
    print("\n" + "🏥 " * 20)
    print("보험 테이블 추출 테스트 시작")
    print("🏥 " * 20)
    
    # API 키 설정 확인
    config_path = project_root / "apis" / "gemini_keys.yaml"
    if not config_path.exists():
        print(f"\n❌ 오류: API 키 설정 파일이 없습니다: {config_path}")
        print("\n다음 단계를 수행하세요:")
        print("1. apis/gemini_keys-example.yaml을 apis/gemini_keys.yaml로 복사")
        print("2. 실제 Gemini API 키를 입력")
        print("3. Google AI Studio에서 무료 API 키 발급:")
        print("   https://makersuite.google.com/app/apikey")
        return
    
    # 샘플 이미지 디렉토리 확인/생성
    sample_images_dir = project_root / "Table_example" / "sample_images"
    if not sample_images_dir.exists():
        sample_images_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 샘플 이미지 디렉토리를 생성했습니다: {sample_images_dir}")
        print("⚠️ 테스트할 보험 테이블 이미지를 이 폴더에 추가하세요.")
    
    # 테스트 실행
    tests = [
        ("프롬프트 확인", test_prompt_display),
        ("추출기 초기화", test_extractor_initialization),
        ("이미지 추출", test_extract_from_sample_image),
        ("OCR 참조 추출", test_extract_with_ocr_reference),
        ("비동기 추출", test_async_extraction),
        ("다중 이미지", test_multiple_images),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            # None은 이미지가 없어서 스킵된 경우
            if result is None:
                results.append((name, "skipped"))
            else:
                results.append((name, "success"))
        except KeyboardInterrupt:
            print("\n\n⚠️ 사용자가 테스트를 중단했습니다.")
            break
        except Exception as e:
            print(f"\n❌ 예상치 못한 오류: {e}")
            results.append((name, "failed"))
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)
    
    for name, status in results:
        if status == "success":
            icon = "✅"
        elif status == "skipped":
            icon = "⏭️ "
        else:
            icon = "❌"
        print(f"{icon} {name}: {status}")
    
    success_count = sum(1 for _, s in results if s == "success")
    skipped_count = sum(1 for _, s in results if s == "skipped")
    total_count = len(results)
    
    print(f"\n총 {total_count}개 테스트 중 {success_count}개 성공, {skipped_count}개 스킵")
    
    if skipped_count > 0:
        print("\n💡 팁: sample_images 폴더에 보험 테이블 이미지를 추가하면 더 많은 테스트가 실행됩니다.")


if __name__ == "__main__":
    main()
