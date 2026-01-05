"""
간단한 테이블 추출 예제
실제 이미지 파일 경로를 지정하여 테이블을 추출합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Table_example import extract_table_from_image, InsuranceTableExtractor


def main():
    """
    사용 예제:
    1. sample_images 폴더에 테이블 이미지를 추가하세요
    2. 아래 IMAGE_PATH를 해당 이미지 경로로 수정하세요
    3. 스크립트를 실행하세요
    """
    
    # ============================================
    # 📌 이미지 경로 설정
    # ============================================
    # 방법 1: sample_images 폴더의 이미지 사용
    sample_dir = Path(__file__).parent / "sample_images"
    
    # sample_images 폴더의 첫 번째 이미지 자동 선택
    image_files = list(sample_dir.glob("*.png")) + \
                  list(sample_dir.glob("*.jpg")) + \
                  list(sample_dir.glob("*.jpeg"))
    
    if not image_files:
        print("❌ sample_images 폴더에 이미지가 없습니다.")
        print(f"   경로: {sample_dir}")
        print("\n📝 테이블 이미지를 추가한 후 다시 실행하세요.")
        return
    
    IMAGE_PATH = image_files[0]
    
    # 방법 2: 직접 경로 지정 (주석 해제하여 사용)
    # IMAGE_PATH = "/path/to/your/table_image.png"
    
    # ============================================
    # 📌 OCR 참조 텍스트 (선택적)
    # ============================================
    # OCR로 먼저 추출한 텍스트가 있으면 여기에 입력
    # 이미지가 흐릿할 때 숫자 정확도 향상에 도움됩니다
    OCR_MARKDOWN = "N/A"  # 없으면 "N/A"
    
    # 예시:
    # OCR_MARKDOWN = """
    # | 구분 | 보험료 |
    # | 상해 | 10000 |
    # | 질병 | 15000 |
    # """
    
    # ============================================
    # 🚀 테이블 추출 실행
    # ============================================
    print("🏥 보험 테이블 추출 시작")
    print("=" * 60)
    print(f"📁 이미지: {IMAGE_PATH}")
    print(f"📝 OCR 참조: {'있음' if OCR_MARKDOWN != 'N/A' else '없음'}")
    print("=" * 60)
    
    try:
        # 테이블 추출
        result = extract_table_from_image(
            image_path=IMAGE_PATH,
            ocr_markdown=OCR_MARKDOWN
        )
        
        print("\n✅ 추출 완료!")
        print("\n📊 결과 (Markdown Table):")
        print("-" * 60)
        print(result)
        print("-" * 60)
        
        # 결과를 파일로 저장
        output_path = Path(IMAGE_PATH).with_suffix(".md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\n💾 결과 저장됨: {output_path}")
        
    except FileNotFoundError as e:
        print(f"❌ 파일을 찾을 수 없습니다: {e}")
    except Exception as e:
        print(f"❌ 추출 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
