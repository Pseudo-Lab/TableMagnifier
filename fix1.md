# Fix 1: 데이터 구조화 및 랜덤 샘플링 (Data Organization & Random Sampling)

## 개요 (Overview)
테이블 식별자를 기준으로 이미지를 그룹화하고, QA 생성을 위해 이미지의 일부를 무작위로 추출(샘플링)하는 로직을 구현했습니다. 이를 통해 동일한 테이블에 속한 이미지들의 다양한 조합을 사용하여 다채로운 QA 쌍을 생성할 수 있습니다.

## 새로운 파일: `data_organizer.py`
이 스크립트는 `data` 디렉토리를 스캔하여 `P_origin_{group}_{table}_{index}.png` 명명 규칙에 따라 이미지를 그룹화합니다.

```python
import os
import re
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

class TableDataOrganizer:
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.grouped_data: Dict[str, List[str]] = defaultdict(list)
        self._organize_data()

    def _organize_data(self):
        pattern = re.compile(r"P_origin_(\d+)_(\d+)(?:_(\d+))?\.png")
        if not self.data_root.exists():
            return

        for root, _, files in os.walk(self.data_root):
            for file in files:
                if not file.endswith(".png"): continue
                match = pattern.match(file)
                if match:
                    group_id, table_id, index = match.group(1), match.group(2), match.group(3)
                    idx_val = int(index) if index is not None else -1
                    key = f"P_origin_{group_id}_{table_id}"
                    abs_path = str(Path(root) / file)
                    self.grouped_data[key].append((idx_val, abs_path))

        for key in self.grouped_data:
            self.grouped_data[key].sort(key=lambda x: x[0])
            self.grouped_data[key] = [item[1] for item in self.grouped_data[key]]

    def get_batches(self, sampling: bool = False, min_k: int = 2, max_k: int = 3, num_samples: int = 1) -> Dict[str, List[List[str]]]:
        results = {}
        for key, images in self.grouped_data.items():
            if not sampling:
                results[key] = [images]
            else:
                table_batches = []
                n_images = len(images)
                effective_min = min(n_images, min_k)
                effective_max = min(n_images, max_k)
                
                if n_images == 0:
                     results[key] = []
                     continue

                for _ in range(num_samples):
                    k = random.randint(effective_min, effective_max) if effective_min <= effective_max else n_images
                    if k > 0:
                        batch = sorted(random.sample(images, k))
                        table_batches.append(batch)
                results[key] = table_batches
        return results
```

## `generate_synthetic_table/runner.py` 변경 사항
- CLI 인자 추가: `--sampling`, `--min-k`, `--max-k`, `--num-samples`.
- `TableDataOrganizer`를 통합하여 이미지 배치(batch)를 준비하도록 수정.
- 단일 파일 대신 준비된 배치를 순회하며 실행하도록 루프 수정.

## `generate_synthetic_table/flow.py` 변경 사항
- `TableState` 업데이트: `image_paths: List[str]` 필드 추가.
- `generate_qa_from_image_node` 업데이트: 다중 이미지를 입력받아 LLM에 전달하도록 로직 수정.
