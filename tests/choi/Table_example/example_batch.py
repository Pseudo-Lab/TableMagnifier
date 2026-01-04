"""
비동기 배치 테이블 추출 예제
여러 이미지를 동시에 처리하여 효율적으로 테이블을 추출합니다.
"""

import sys
import asyncio
import time
from pathlib import Path
from typing import List, Tuple, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Table_example import aextract_table_from_image, InsuranceTableExtractor


async def process_single_image(
    image_path: Path,
    ocr_markdown: str = "N/A"
) -> Tuple[Path, Optional[str], Optional[str]]:
    """
    단일 이미지 처리 (비동기)
    
    Returns:
        (이미지 경로, 결과 또는 None, 에러 메시지 또는 None)
    """
    try:
        result = await aextract_table_from_image(
            image_path=image_path,
            ocr_markdown=ocr_markdown
        )
        return (image_path, result, None)
    except Exception as e:
        return (image_path, None, str(e))


async def batch_extract_tables(
    image_paths: List[Path],
    max_concurrent: int = 3
) -> List[Tuple[Path, Optional[str], Optional[str]]]:
    """
    여러 이미지를 배치로 처리 (동시성 제한)
    
    Args:
        image_paths: 처리할 이미지 경로 리스트
        max_concurrent: 동시 처리 최대 개수
        
    Returns:
        (이미지 경로, 결과, 에러) 튜플 리스트
    """
    # 세마포어로 동시 실행 제한
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(image_path: Path):
        async with semaphore:
            return await process_single_image(image_path)
    
    # 모든 이미지 동시 처리 (세마포어로 제한)
    tasks = [process_with_semaphore(path) for path in image_paths]
    results = await asyncio.gather(*tasks)
    
    return results


def find_all_images(directory: Path) -> List[Path]:
    """디렉토리에서 모든 이미지 파일 찾기"""
    extensions = ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp", "*.bmp"]
    images = []
    for ext in extensions:
        images.extend(directory.glob(ext))
    return sorted(images)


async def main():
    """
    배치 처리 예제
    sample_images 폴더의 모든 이미지를 처리합니다.
    """
    print("🏥 보험 테이블 배치 추출 시작")
    print("=" * 70)
    
    # ============================================
    # 📌 설정
    # ============================================
    sample_dir = Path(__file__).parent / "sample_images"
    output_dir = Path(__file__).parent / "output"
    max_concurrent = 3  # 동시 처리 최대 개수
    
    # 출력 디렉토리 생성
    output_dir.mkdir(exist_ok=True)
    
    # ============================================
    # 📌 이미지 파일 수집
    # ============================================
    image_paths = find_all_images(sample_dir)
    
    if not image_paths:
        print(f"❌ 이미지 파일이 없습니다: {sample_dir}")
        print("\n📝 sample_images 폴더에 테이블 이미지를 추가하세요.")
        return
    
    print(f"📁 처리할 이미지: {len(image_paths)}개")
    for i, path in enumerate(image_paths, 1):
        print(f"   {i}. {path.name}")
    print(f"⚡ 동시 처리 수: {max_concurrent}")
    print("=" * 70)
    
    # ============================================
    # 🚀 배치 처리 실행
    # ============================================
    start_time = time.time()
    
    results = await batch_extract_tables(
        image_paths=image_paths,
        max_concurrent=max_concurrent
    )
    
    elapsed = time.time() - start_time
    
    # ============================================
    # 📊 결과 처리
    # ============================================
    success_count = 0
    failed_count = 0
    
    print("\n📊 처리 결과:")
    print("-" * 70)
    
    for image_path, result, error in results:
        if result:
            success_count += 1
            status = "✅ 성공"
            
            # 결과 파일 저장
            output_path = output_dir / f"{image_path.stem}_table.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {image_path.name}\n\n")
                f.write(result)
            
            print(f"\n{status}: {image_path.name}")
            print(f"   💾 저장: {output_path.name}")
            print(f"   📝 미리보기: {result[:100]}...")
        else:
            failed_count += 1
            status = "❌ 실패"
            print(f"\n{status}: {image_path.name}")
            print(f"   ⚠️  에러: {error}")
    
    # ============================================
    # 📈 최종 요약
    # ============================================
    print("\n" + "=" * 70)
    print("📈 처리 완료!")
    print(f"   ⏱️  총 소요 시간: {elapsed:.2f}초")
    print(f"   ✅ 성공: {success_count}개")
    print(f"   ❌ 실패: {failed_count}개")
    print(f"   📁 출력 폴더: {output_dir}")
    
    if success_count > 0:
        avg_time = elapsed / success_count
        print(f"   ⚡ 평균 처리 시간: {avg_time:.2f}초/이미지")


if __name__ == "__main__":
    asyncio.run(main())
