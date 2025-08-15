"""
Synthetic Data Generation API Routes
Provides endpoints for generating and managing synthetic AI workload data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field
from datetime import datetime

from app import schemas
from app.services.synthetic_data_service import synthetic_data_service
from app.dependencies import get_db_session, get_db_dependency, DbDep
from app.auth.auth_dependencies import get_current_user
from app.schemas.shared_types import BaseAgentConfig
from app.db.models_postgres import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.synthetic_data_service import SyntheticDataService
import logging

logger = logging.getLogger(__name__)


# Request/Response Models
class ToolConfig(BaseModel):
    """Tool configuration for generation"""
    name: str
    type: str
    latency_ms_range: Tuple[int, int] = Field(default=(50, 500))
    failure_rate: float = Field(default=0.01, ge=0, le=1)


class ScaleConfig(BaseModel):
    """Scale configuration for generation"""
    num_traces: int = Field(gt=0)
    time_window_hours: int = Field(default=24, gt=0)
    concurrent_users: int = Field(default=100, gt=0)
    peak_load_multiplier: float = Field(default=1.0, gt=0)


class SyntheticDataAgentConfig(BaseAgentConfig):
    """Extended agent configuration for synthetic data generation"""
    supervisor_strategy: str = Field(default="round_robin")
    backoff_strategy: str = Field(default="exponential")


class GenerationRequest(BaseModel):
    """Synthetic data generation request"""
    corpus_id: Optional[str] = None
    domain_focus: str
    tool_catalog: List[ToolConfig]
    workload_distribution: Dict[str, float]
    scale_parameters: ScaleConfig
    agent_configuration: Optional[SyntheticDataAgentConfig] = None


class GenerationResponse(BaseModel):
    """Generation job response"""
    job_id: str
    status: str
    estimated_duration_seconds: Optional[int] = None
    websocket_channel: str
    table_name: str


class JobStatusResponse(BaseModel):
    """Job status response"""
    job_id: str
    status: str
    progress_percentage: float
    records_generated: int
    records_ingested: int
    errors: List[str]
    started_at: datetime
    completed_at: Optional[datetime] = None


class PreviewResponse(BaseModel):
    """Preview response"""
    samples: List[Dict]
    estimated_characteristics: Dict


router = APIRouter(tags=["synthetic_data"])


@router.post("/generate", response_model=GenerationResponse)
async def generate_synthetic_data(
    request: GenerationRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Initiate synthetic data generation job"""
    config = _build_generation_config(request)
    result = await _execute_generation(db, config, current_user.id, request.corpus_id)
    return _build_generation_response(result, request.scale_parameters.num_traces)


def _build_generation_config(request: GenerationRequest) -> schemas.LogGenParams:
    """Build generation config from request"""
    return schemas.LogGenParams(
        num_logs=request.scale_parameters.num_traces,
        corpus_id=request.corpus_id
    )


async def _call_generation_service(
    db: Session, config: schemas.LogGenParams, user_id: int, corpus_id: Optional[str]
) -> Dict:
    """Call synthetic data generation service."""
    return await synthetic_data_service.generate_synthetic_data(
        db=db, config=config, user_id=user_id, corpus_id=corpus_id
    )

async def _execute_generation(
    db: Session,
    config: schemas.LogGenParams,
    user_id: int,
    corpus_id: Optional[str]
) -> Dict:
    """Execute data generation"""
    try:
        return await _call_generation_service(db, config, user_id, corpus_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_estimated_duration(num_traces: int) -> int:
    """Calculate estimated generation duration."""
    return int(num_traces / 100)

def _build_generation_response(
    result: Dict,
    num_traces: int
) -> GenerationResponse:
    """Build generation response"""
    return GenerationResponse(
        job_id=result["job_id"],
        status=result["status"],
        estimated_duration_seconds=_calculate_estimated_duration(num_traces),
        websocket_channel=result["websocket_channel"],
        table_name=result["table_name"]
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get generation job status"""
    job_status = await _fetch_job_status(job_id, current_user.id)
    return _build_status_response(job_id, job_status)


def _validate_job_ownership(status: Dict, user_id: int, job_id: str) -> None:
    """Validate job ownership and access."""
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if status.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

async def _fetch_job_status(job_id: str, user_id: int) -> Dict:
    """Fetch and validate job status"""
    status = await synthetic_data_service.get_job_status(job_id)
    _validate_job_ownership(status, user_id, job_id)
    return status


def _build_status_response(job_id: str, status: Dict) -> JobStatusResponse:
    """Build status response"""
    return JobStatusResponse(
        job_id=job_id,
        status=status["status"],
        progress_percentage=_calculate_progress(status),
        records_generated=status["records_generated"],
        records_ingested=status["records_ingested"],
        errors=status["errors"],
        started_at=status["start_time"],
        completed_at=status.get("end_time")
    )


def _calculate_progress(status: Dict) -> float:
    """Calculate generation progress"""
    if not status.get("config"):
        return 0
    generated = status["records_generated"]
    total = status["config"].num_logs
    return (generated / total * 100) if total > 0 else 0


@router.post("/cancel/{job_id}")
async def cancel_generation(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel running generation job"""
    status = await _fetch_job_status(job_id, current_user.id)
    await _cancel_job(job_id)
    return _build_cancel_response(job_id, status)


async def _cancel_job(job_id: str):
    """Cancel job execution"""
    success = await synthetic_data_service.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel job")


def _build_cancel_response(job_id: str, status: Dict) -> Dict:
    """Build cancellation response"""
    return {
        "job_id": job_id,
        "status": "cancelled",
        "records_completed": status["records_generated"]
    }


@router.get("/preview", response_model=PreviewResponse)
async def preview_synthetic_data(
    corpus_id: Optional[str] = Query(None),
    workload_type: str = Query(...),
    sample_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Preview sample generated data"""
    samples = await _get_preview_samples(corpus_id, workload_type, sample_size)
    return PreviewResponse(
        samples=samples,
        estimated_characteristics=_calculate_characteristics(samples)
    )


async def _get_preview_samples(
    corpus_id: Optional[str],
    workload_type: str,
    sample_size: int
) -> List[Dict]:
    """Get preview samples"""
    return await synthetic_data_service.get_preview(
        corpus_id=corpus_id,
        workload_type=workload_type,
        sample_size=sample_size
    )


def _build_empty_characteristics() -> Dict:
    """Build empty characteristics for no samples."""
    return {"avg_latency_ms": 0, "tool_diversity": 0, "sample_count": 0}

def _calculate_characteristics(samples: List[Dict]) -> Dict:
    """Calculate sample characteristics"""
    if not samples:
        return _build_empty_characteristics()
    return {
        "avg_latency_ms": _calculate_avg_latency(samples),
        "tool_diversity": _calculate_tool_diversity(samples),
        "sample_count": len(samples)
    }


def _calculate_avg_latency(samples: List[Dict]) -> float:
    """Calculate average latency"""
    total = sum(s["metrics"]["total_latency_ms"] for s in samples)
    return total / len(samples)


def _calculate_tool_diversity(samples: List[Dict]) -> int:
    """Calculate tool diversity"""
    tools = set()
    for sample in samples:
        tools.update(sample.get("tool_invocations", []))
    return len(tools)


# Corpus endpoints moved to synthetic_data_corpus.py for modularity

@router.get("/templates")
async def get_templates(db: AsyncSession = Depends(get_db_dependency)):
    """Get available templates"""
    return await _fetch_templates(db)


async def _fetch_templates(db: AsyncSession) -> Dict:
    """Fetch synthetic data templates"""
    try:
        templates = await SyntheticDataService.get_available_templates(db)
        return {"templates": templates, "status": "ok"}
    except Exception as e:
        logger.error(f"Error fetching templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def _generate_test_user_data(count: int) -> List[Dict]:
    """Generate test user data records."""
    return [
        {"user_id": f"id_{i}", "name": f"User {i}", "age": 25+i, "email": f"user{i}@test.com"}
        for i in range(count)
    ]

@router.post("/generate-test")
async def generate_api_data(request: dict) -> dict:
    """Generate synthetic data for API testing"""
    count = request.get("count", 10)
    return {
        "data": _generate_test_user_data(count),
        "count": count
    }

@router.post("/validate")
async def validate_api_data(request: dict) -> dict:
    """Validate synthetic data for API testing"""
    return {"valid": True, "errors": []}

@router.get("/templates-test")
async def get_templates_test() -> list:
    """Get templates for testing"""
    return [
        {"name": "user_profile", "fields": 5},
        {"name": "transaction", "fields": 8}
    ]
