"""
Dataset utilities for Table QA evaluation.

QA 데이터를 로드하고 평가용 데이터셋으로 변환합니다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator

logger = logging.getLogger(__name__)


@dataclass
class QAItem:
    """단일 QA 항목"""
    id: str
    question: str
    answer: str
    qa_type: str
    image_paths: List[str] = field(default_factory=list)
    reasoning_annotation: Optional[str] = None
    context: Optional[str] = None
    source_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "type": self.qa_type,
            "image_paths": self.image_paths,
            "reasoning_annotation": self.reasoning_annotation,
            "context": self.context,
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], id: str, image_paths: List[str] = None, source_file: str = None) -> "QAItem":
        return cls(
            id=id,
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            qa_type=data.get("type", "unknown"),
            image_paths=image_paths or [],
            reasoning_annotation=data.get("reasoning_annotation"),
            context=data.get("context"),
            source_file=source_file,
        )


@dataclass
class EvalDataset:
    """평가용 데이터셋"""
    items: List[QAItem] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[QAItem]:
        return iter(self.items)

    def __getitem__(self, idx: int) -> QAItem:
        return self.items[idx]

    def add(self, item: QAItem) -> None:
        self.items.append(item)

    def filter_by_type(self, qa_type: str) -> "EvalDataset":
        """특정 QA 유형만 필터링"""
        filtered = [item for item in self.items if item.qa_type == qa_type]
        return EvalDataset(items=filtered, metadata={**self.metadata, "filtered_by": qa_type})

    def get_type_distribution(self) -> Dict[str, int]:
        """QA 유형별 분포"""
        dist = {}
        for item in self.items:
            dist[item.qa_type] = dist.get(item.qa_type, 0) + 1
        return dist

    def to_jsonl(self, path: Path) -> None:
        """JSONL 형식으로 저장 (vLLM batch inference용)"""
        with open(path, "w", encoding="utf-8") as f:
            for item in self.items:
                f.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(self.items)} items to {path}")

    def to_json(self, path: Path) -> None:
        """JSON 형식으로 저장"""
        data = {
            "metadata": self.metadata,
            "items": [item.to_dict() for item in self.items],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, ensure_ascii=False, indent=2, fp=f)
        logger.info(f"Saved {len(self.items)} items to {path}")

    @classmethod
    def from_jsonl(cls, path: Path) -> "EvalDataset":
        """JSONL 파일에서 로드"""
        items = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    item = QAItem(
                        id=data["id"],
                        question=data["question"],
                        answer=data["answer"],
                        qa_type=data.get("type", "unknown"),
                        image_paths=data.get("image_paths", []),
                        reasoning_annotation=data.get("reasoning_annotation"),
                        context=data.get("context"),
                        source_file=data.get("source_file"),
                    )
                    items.append(item)
        return cls(items=items, metadata={"source": str(path)})

    @classmethod
    def from_json(cls, path: Path) -> "EvalDataset":
        """JSON 파일에서 로드"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = []
        for item_data in data.get("items", []):
            item = QAItem(
                id=item_data["id"],
                question=item_data["question"],
                answer=item_data["answer"],
                qa_type=item_data.get("type", "unknown"),
                image_paths=item_data.get("image_paths", []),
                reasoning_annotation=item_data.get("reasoning_annotation"),
                context=item_data.get("context"),
                source_file=item_data.get("source_file"),
            )
            items.append(item)

        return cls(items=items, metadata=data.get("metadata", {}))


def load_qa_from_file(file_path: Path) -> List[QAItem]:
    """
    단일 QA 결과 파일에서 QA 항목들을 로드합니다.

    Args:
        file_path: *_qa.json 파일 경로

    Returns:
        QAItem 리스트
    """
    items = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        name = data.get("name", file_path.stem)
        image_paths = data.get("image_paths", [])
        qa_results = data.get("qa_results", [])

        for idx, qa in enumerate(qa_results):
            item_id = f"{name}_{idx}"
            item = QAItem.from_dict(
                qa,
                id=item_id,
                image_paths=image_paths,
                source_file=str(file_path),
            )
            items.append(item)

    except Exception as e:
        logger.warning(f"Failed to load {file_path}: {e}")

    return items


def load_qa_from_folder(folder_path: Path, pattern: str = "*_qa.json") -> EvalDataset:
    """
    폴더에서 모든 QA 결과 파일을 로드합니다.

    Args:
        folder_path: qa_output 폴더 경로
        pattern: 파일 패턴 (기본: *_qa.json)

    Returns:
        EvalDataset
    """
    folder = Path(folder_path)
    all_items = []

    # 재귀적으로 모든 QA 파일 찾기
    qa_files = list(folder.rglob(pattern))
    logger.info(f"Found {len(qa_files)} QA files in {folder}")

    for qa_file in qa_files:
        items = load_qa_from_file(qa_file)
        all_items.extend(items)

    metadata = {
        "source_folder": str(folder),
        "file_count": len(qa_files),
        "total_qa_count": len(all_items),
    }

    return EvalDataset(items=all_items, metadata=metadata)


def create_eval_dataset(
    source: str | Path,
    output_path: Optional[Path] = None,
    format: str = "jsonl",
) -> EvalDataset:
    """
    평가용 데이터셋을 생성합니다.

    Args:
        source: QA 파일 또는 폴더 경로
        output_path: 저장할 경로 (None이면 저장하지 않음)
        format: 저장 형식 (jsonl 또는 json)

    Returns:
        EvalDataset
    """
    source = Path(source)

    if source.is_file():
        items = load_qa_from_file(source)
        dataset = EvalDataset(
            items=items,
            metadata={"source": str(source), "total_qa_count": len(items)}
        )
    elif source.is_dir():
        dataset = load_qa_from_folder(source)
    else:
        raise ValueError(f"Invalid source: {source}")

    logger.info(f"Created dataset with {len(dataset)} items")
    logger.info(f"Type distribution: {dataset.get_type_distribution()}")

    if output_path:
        output_path = Path(output_path)
        if format == "jsonl":
            dataset.to_jsonl(output_path)
        else:
            dataset.to_json(output_path)

    return dataset


def create_inference_prompts(
    dataset: EvalDataset,
    prompt_template: Optional[str] = None,
    include_image: bool = False,
) -> List[Dict[str, Any]]:
    """
    추론용 프롬프트를 생성합니다.

    Args:
        dataset: 평가 데이터셋
        prompt_template: 프롬프트 템플릿 (None이면 기본 템플릿 사용)
        include_image: 이미지 경로 포함 여부

    Returns:
        추론 요청 리스트
    """
    if prompt_template is None:
        prompt_template = """다음 질문에 대해 간결하게 답변해주세요.

질문: {question}

답변:"""

    prompts = []
    for item in dataset:
        prompt = prompt_template.format(
            question=item.question,
            context=item.context or "",
        )

        request = {
            "id": item.id,
            "question": item.question,
            "prompt": prompt,
            "ground_truth": item.answer,
            "qa_type": item.qa_type,
        }

        if include_image and item.image_paths:
            request["image_paths"] = item.image_paths

        prompts.append(request)

    return prompts
