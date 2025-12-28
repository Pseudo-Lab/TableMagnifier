"""
TableMagnifier Pipeline UI - Backend Server

FastAPI + WebSocket 기반 파이프라인 실행 서버
- 단건/배치 이미지 처리
- 실시간 진행 상태 업데이트
- 체크포인트 기반 중단/재개
- 에러 시 사용자 재시도 선택
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from asyncio import Semaphore

# 프로젝트 루트를 path에 추가
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from generate_synthetic_table.flow import run_synthetic_table_flow, TableState


# ============ Models ============

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class PipelineNode(str, Enum):
    IMAGE_TO_HTML = "image_to_html"
    PYMUPDF_PARSE = "pymupdf_parse"
    VALIDATE_PARSED = "validate_parsed_table"
    ANALYZE_TABLE = "analyze_table"
    GENERATE_SYNTHETIC = "generate_synthetic_table"
    GENERATE_SYNTHETIC_FROM_IMAGE = "generate_synthetic_table_from_image"
    SELF_REFLECTION = "self_reflection"
    REVISE_SYNTHETIC = "revise_synthetic_table"
    PARSE_SYNTHETIC = "parse_synthetic_table"
    GENERATE_QA = "generate_qa"


class JobItem(BaseModel):
    id: str
    image_path: str
    image_name: str
    status: JobStatus
    current_node: Optional[str] = None
    progress: int = 0  # 0-100
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


class BatchJob(BaseModel):
    id: str
    items: List[JobItem]
    status: JobStatus
    total: int
    completed: int = 0
    failed: int = 0
    created_at: str
    updated_at: str


class PipelineConfig(BaseModel):
    provider: str = "gemini_pool"
    model: str = "gemini-2.0-flash"
    temperature: float = 0.2
    config_path: Optional[str] = None
    max_concurrent: int = 3  # 동시 처리 수 (API rate limit 고려)


class RunPipelineRequest(BaseModel):
    image_paths: List[str]
    config: Optional[PipelineConfig] = None


class RetryRequest(BaseModel):
    job_id: str
    item_ids: Optional[List[str]] = None  # None이면 실패한 모든 항목 재시도


# ============ State Management ============

class PipelineState:
    """글로벌 파이프라인 상태 관리"""
    
    def __init__(self):
        self.jobs: Dict[str, BatchJob] = {}
        self.websockets: Dict[str, WebSocket] = {}
        self.checkpoints_dir = Path("./checkpoints")
        self.checkpoints_dir.mkdir(exist_ok=True)
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)
        self.upload_dir = Path("./uploads")
        self.upload_dir.mkdir(exist_ok=True)
    
    def create_batch_job(self, image_paths: List[str]) -> BatchJob:
        job_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        items = []
        for path in image_paths:
            item = JobItem(
                id=str(uuid.uuid4())[:8],
                image_path=path,
                image_name=Path(path).name,
                status=JobStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            items.append(item)
        
        batch = BatchJob(
            id=job_id,
            items=items,
            status=JobStatus.PENDING,
            total=len(items),
            created_at=now,
            updated_at=now,
        )
        
        self.jobs[job_id] = batch
        self._save_checkpoint(job_id)
        return batch
    
    def update_item(self, job_id: str, item_id: str, **updates):
        if job_id not in self.jobs:
            return
        
        batch = self.jobs[job_id]
        for item in batch.items:
            if item.id == item_id:
                for key, value in updates.items():
                    setattr(item, key, value)
                item.updated_at = datetime.now().isoformat()
                break
        
        # 배치 상태 업데이트
        completed = sum(1 for i in batch.items if i.status == JobStatus.COMPLETED)
        failed = sum(1 for i in batch.items if i.status == JobStatus.FAILED)
        batch.completed = completed
        batch.failed = failed
        batch.updated_at = datetime.now().isoformat()
        
        if completed + failed == batch.total:
            batch.status = JobStatus.COMPLETED if failed == 0 else JobStatus.FAILED
        
        self._save_checkpoint(job_id)
    
    def _save_checkpoint(self, job_id: str):
        if job_id in self.jobs:
            checkpoint_path = self.checkpoints_dir / f"{job_id}.json"
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(self.jobs[job_id].model_dump(), f, ensure_ascii=False, indent=2)
    
    def load_checkpoint(self, job_id: str) -> Optional[BatchJob]:
        checkpoint_path = self.checkpoints_dir / f"{job_id}.json"
        if checkpoint_path.exists():
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                batch = BatchJob(**data)
                self.jobs[job_id] = batch
                return batch
        return None
    
    def list_checkpoints(self) -> List[str]:
        return [f.stem for f in self.checkpoints_dir.glob("*.json")]


state = PipelineState()


# ============ FastAPI App ============

app = FastAPI(
    title="TableMagnifier Pipeline UI",
    description="한국어 테이블 이미지에서 합성 데이터 및 QA 생성",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ WebSocket ============

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    state.websockets[job_id] = websocket
    
    try:
        while True:
            # 클라이언트로부터 메시지 대기 (keep-alive)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if job_id in state.websockets:
            del state.websockets[job_id]


async def broadcast_update(job_id: str, message: Dict):
    """WebSocket으로 상태 업데이트 브로드캐스트"""
    if job_id in state.websockets:
        try:
            await state.websockets[job_id].send_json(message)
        except:
            pass


# ============ API Endpoints ============

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    """이미지 파일 업로드"""
    uploaded_paths = []
    
    for file in files:
        if not file.filename:
            continue
        
        # 파일 저장
        file_path = state.upload_dir / f"{uuid.uuid4().hex[:8]}_{file.filename}"
        content = await file.read()
        file_path.write_bytes(content)
        uploaded_paths.append(str(file_path.absolute()))
    
    return {"paths": uploaded_paths, "count": len(uploaded_paths)}


@app.post("/api/pipeline/run")
async def run_pipeline(request: RunPipelineRequest):
    """파이프라인 실행 (배치 처리)"""
    
    if not request.image_paths:
        raise HTTPException(status_code=400, detail="No image paths provided")
    
    # 배치 작업 생성
    batch = state.create_batch_job(request.image_paths)
    
    # 비동기로 파이프라인 실행
    config = request.config or PipelineConfig()
    asyncio.create_task(process_batch(batch.id, config))
    
    return {"job_id": batch.id, "total": batch.total}


async def process_batch(job_id: str, config: PipelineConfig):
    """배치 처리 실행 (병렬 처리)"""
    batch = state.jobs.get(job_id)
    if not batch:
        return

    batch.status = JobStatus.RUNNING

    # Semaphore로 동시 처리 수 제한
    sem = Semaphore(config.max_concurrent)

    async def process_with_semaphore(item: JobItem):
        """Semaphore로 동시 처리 수 제한하며 실행"""
        # 취소 상태 확인
        if batch.status == JobStatus.CANCELLED:
            return

        async with sem:
            # 취소 상태 재확인 (semaphore 대기 중 취소될 수 있음)
            if batch.status == JobStatus.CANCELLED:
                return
            await process_single_item(job_id, item, config)

    # 처리할 항목 필터링 (이미 완료된 항목 제외)
    items_to_process = [
        item for item in batch.items
        if item.status != JobStatus.COMPLETED
    ]

    # 병렬 처리 시작 알림
    await broadcast_update(job_id, {
        "type": "batch_parallel_start",
        "job_id": job_id,
        "total": len(items_to_process),
        "max_concurrent": config.max_concurrent,
    })

    # 병렬 처리 실행
    if items_to_process:
        tasks = [process_with_semaphore(item) for item in items_to_process]
        await asyncio.gather(*tasks, return_exceptions=True)

    # 최종 상태 업데이트
    state._save_checkpoint(job_id)
    await broadcast_update(job_id, {
        "type": "batch_complete",
        "job_id": job_id,
        "completed": batch.completed,
        "failed": batch.failed,
        "total": batch.total,
    })


async def process_single_item(job_id: str, item: JobItem, config: PipelineConfig):
    """단일 이미지 처리 (노드별 상태 업데이트 포함)"""
    
    state.update_item(job_id, item.id, status=JobStatus.RUNNING, progress=10)
    await broadcast_update(job_id, {
        "type": "item_start",
        "item_id": item.id,
        "image_name": item.image_name,
        "nodes": {
            "start": "completed",
            "generate_synthetic": "running",
            "self_reflection": "pending",
            "parse_synthetic": "pending",
            "generate_qa": "pending",
            "end": "pending",
        }
    })
    
    try:
        # 노드별 진행률 및 상태 매핑
        node_config = {
            "generate_synthetic_table_from_image": {"progress": 30, "node_id": "generate_synthetic"},
            "self_reflection": {"progress": 50, "node_id": "self_reflection"},
            "revise_synthetic_table": {"progress": 45, "node_id": "generate_synthetic"},  # 재시도
            "parse_synthetic_table": {"progress": 70, "node_id": "parse_synthetic"},
            "generate_qa": {"progress": 90, "node_id": "generate_qa"},
        }
        
        # 노드 상태 추적
        node_states = {
            "start": "completed",
            "generate_synthetic": "pending",
            "self_reflection": "pending",
            "parse_synthetic": "pending",
            "generate_qa": "pending",
            "end": "pending",
        }
        node_results = {}
        retry_count = 0
        
        # LangGraph 파이프라인 실행 (동기 함수를 비동기로 실행)
        result = await asyncio.to_thread(
            run_synthetic_table_flow,
            item.image_path,
            provider=config.provider,
            model=config.model,
            temperature=config.temperature,
            config_path=config.config_path,
        )
        
        # 결과에서 노드 결과 추출
        if result.get("synthetic_table"):
            node_results["generate_synthetic"] = result.get("synthetic_table", "")[:500]
        if result.get("reflection"):
            node_results["self_reflection"] = result.get("reflection", "")[:300]
        if result.get("synthetic_json"):
            node_results["parse_synthetic"] = f"JSON 파싱 완료 ({len(str(result.get('synthetic_json', {})))} bytes)"
        if result.get("qa_results"):
            qa_preview = result.get("qa_results", [])[:2]  # 처음 2개만 미리보기
            node_results["generate_qa"] = json.dumps(qa_preview, ensure_ascii=False, indent=2)
        
        # 재시도 횟수 추출
        retry_count = result.get("attempts", 0)
        
        # 결과 저장
        if result.get("errors"):
            # 실패한 노드 찾기
            failed_node = "generate_synthetic"  # 기본값
            if "reflection" in str(result.get("errors")):
                failed_node = "self_reflection"
            elif "parse" in str(result.get("errors")):
                failed_node = "parse_synthetic"
            elif "qa" in str(result.get("errors")):
                failed_node = "generate_qa"
            
            node_states[failed_node] = "failed"
            
            state.update_item(
                job_id, item.id,
                status=JobStatus.FAILED,
                error="; ".join(result["errors"]),
                progress=100,
            )
            await broadcast_update(job_id, {
                "type": "item_error",
                "item_id": item.id,
                "error": result["errors"],
                "nodes": node_states,
                "node_results": node_results,
                "retry_count": retry_count,
            })
        else:
            # 모든 노드 완료
            for key in node_states:
                node_states[key] = "completed"
            
            # 결과 JSON 저장
            output_path = state.output_dir / f"{item.id}_result.json"
            result_data = {
                "image_path": item.image_path,
                "html_table": result.get("html_table", ""),
                "synthetic_table": result.get("synthetic_table", ""),
                "synthetic_json": result.get("synthetic_json", {}),
                "qa_results": result.get("qa_results", []),
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            state.update_item(
                job_id, item.id,
                status=JobStatus.COMPLETED,
                result=result_data,
                progress=100,
            )
            await broadcast_update(job_id, {
                "type": "item_complete",
                "item_id": item.id,
                "result": result_data,
                "nodes": node_states,
                "node_results": node_results,
                "retry_count": retry_count,
            })
    
    except Exception as e:
        state.update_item(
            job_id, item.id,
            status=JobStatus.FAILED,
            error=str(e),
            progress=100,
        )
        await broadcast_update(job_id, {
            "type": "item_error",
            "item_id": item.id,
            "error": str(e),
            "nodes": {"start": "completed", "generate_synthetic": "failed"},
        })


@app.get("/api/pipeline/status/{job_id}")
async def get_pipeline_status(job_id: str):
    """파이프라인 상태 조회"""
    
    batch = state.jobs.get(job_id)
    if not batch:
        # 체크포인트에서 로드 시도
        batch = state.load_checkpoint(job_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return batch


@app.post("/api/pipeline/pause/{job_id}")
async def pause_pipeline(job_id: str):
    """파이프라인 일시정지 (체크포인트 저장)"""
    
    batch = state.jobs.get(job_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Job not found")
    
    batch.status = JobStatus.PAUSED
    state._save_checkpoint(job_id)
    
    return {"status": "paused", "job_id": job_id}


@app.post("/api/pipeline/resume/{job_id}")
async def resume_pipeline(job_id: str, config: Optional[PipelineConfig] = None):
    """파이프라인 재개"""
    
    batch = state.jobs.get(job_id) or state.load_checkpoint(job_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Job not found")
    
    batch.status = JobStatus.RUNNING
    config = config or PipelineConfig()
    asyncio.create_task(process_batch(job_id, config))
    
    return {"status": "resumed", "job_id": job_id}


@app.post("/api/pipeline/retry")
async def retry_failed(request: RetryRequest):
    """실패한 항목 재시도"""
    
    batch = state.jobs.get(request.job_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # 재시도할 항목 선택
    if request.item_ids:
        items_to_retry = [i for i in batch.items if i.id in request.item_ids]
    else:
        items_to_retry = [i for i in batch.items if i.status == JobStatus.FAILED]
    
    # 상태 초기화
    for item in items_to_retry:
        state.update_item(
            request.job_id, item.id,
            status=JobStatus.PENDING,
            error=None,
            progress=0,
        )
    
    # 재실행
    batch.status = JobStatus.RUNNING
    config = PipelineConfig()
    asyncio.create_task(process_batch(request.job_id, config))
    
    return {"status": "retrying", "count": len(items_to_retry)}


@app.post("/api/pipeline/cancel/{job_id}")
async def cancel_pipeline(job_id: str):
    """파이프라인 취소"""
    
    batch = state.jobs.get(job_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Job not found")
    
    batch.status = JobStatus.CANCELLED
    state._save_checkpoint(job_id)
    
    return {"status": "cancelled", "job_id": job_id}


@app.get("/api/pipeline/list")
async def list_jobs():
    """모든 작업 목록 조회"""
    
    # 메모리와 체크포인트에서 모두 로드
    all_job_ids = set(state.jobs.keys()) | set(state.list_checkpoints())
    
    jobs = []
    for job_id in all_job_ids:
        batch = state.jobs.get(job_id) or state.load_checkpoint(job_id)
        if batch:
            jobs.append({
                "id": batch.id,
                "status": batch.status,
                "total": batch.total,
                "completed": batch.completed,
                "failed": batch.failed,
                "created_at": batch.created_at,
            })
    
    return {"jobs": sorted(jobs, key=lambda x: x["created_at"], reverse=True)}


@app.get("/api/result/{item_id}")
async def get_result(item_id: str):
    """개별 결과 조회"""
    
    result_path = state.output_dir / f"{item_id}_result.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result not found")
    
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Static files (업로드된 이미지 서빙)
app.mount("/uploads", StaticFiles(directory=str(state.upload_dir)), name="uploads")
app.mount("/output", StaticFiles(directory=str(state.output_dir)), name="output")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
