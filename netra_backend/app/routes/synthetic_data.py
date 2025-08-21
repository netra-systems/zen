"""
Synthetic Data Generation API Routes
Provides endpoints for generating and managing synthetic AI workload data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field
from datetime import datetime

from netra_backend.app import schemas
from netra_backend.app.services.synthetic_data_service import synthetic_data_service
from netra_backend.app.dependencies import get_db_session, get_db_dependency, DbDep
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.schemas.shared_types import BaseAgentConfig
from netra_backend.app.db.models_postgres import User
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.services.synthetic_data_service import SyntheticDataService
from netra_backend.app.core.configuration.services import synthetic_data_service as sds
from netra_backend.app.routes.utils.synthetic_data_helpers import (
    build_generation_config, execute_generation_safely, extract_result_fields,
    fetch_and_validate_job_status, extract_status_fields, cancel_job_safely,
    build_cancel_response, get_preview_samples_safely, calculate_characteristics,
    generate_test_user_data
)
from netra_backend.app.routes.utils.error_handlers import handle_service_error
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


async def _process_generation_request(
    request: GenerationRequest, db: Session, user_id: int
) -> GenerationResponse:
    """Process generation request and build response."""
    config = build_generation_config(request)
    result = await _execute_generation(db, config, user_id, request.corpus_id)
    fields = extract_result_fields(result, request.scale_parameters.num_traces)
    return GenerationResponse(**fields)

@router.post("/generate", response_model=GenerationResponse)
async def generate_synthetic_data(
    request: GenerationRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Initiate synthetic data generation job"""
    return await _process_generation_request(request, db, current_user.id)





async def _execute_generation(
    db: Session, config: schemas.LogGenParams, user_id: int, corpus_id: Optional[str]
) -> Dict:
    """Execute data generation"""
    try:
        return await execute_generation_safely(db, config, user_id, corpus_id)
    except Exception as e:
        handle_service_error(e, "Generation")




@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get generation job status"""
    job_status = await fetch_and_validate_job_status(job_id, current_user.id)
    return _build_status_response(job_id, job_status)





def _build_status_response(job_id: str, status: Dict) -> JobStatusResponse:
    """Build status response"""
    fields = extract_status_fields(status)
    return JobStatusResponse(job_id=job_id, **fields)




async def _execute_job_cancellation(job_id: str, user_id: int) -> Dict:
    """Execute job cancellation process."""
    status = await fetch_and_validate_job_status(job_id, user_id)
    await cancel_job_safely(job_id)
    return build_cancel_response(job_id, status)

@router.post("/cancel/{job_id}")
async def cancel_generation(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel running generation job"""
    return await _execute_job_cancellation(job_id, current_user.id)




def _build_preview_response(samples: List[Dict]) -> PreviewResponse:
    """Build preview response from samples."""
    return PreviewResponse(
        samples=samples,
        estimated_characteristics=calculate_characteristics(samples)
    )

async def _generate_preview_data(
    corpus_id: Optional[str], workload_type: str, sample_size: int
) -> PreviewResponse:
    """Generate preview data response."""
    samples = await get_preview_samples_safely(corpus_id, workload_type, sample_size)
    return _build_preview_response(samples)

@router.get("/preview", response_model=PreviewResponse)
async def preview_synthetic_data(
    corpus_id: Optional[str] = Query(None),
    workload_type: str = Query(...),
    sample_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Preview sample generated data"""
    return await _generate_preview_data(corpus_id, workload_type, sample_size)








# Corpus endpoints moved to synthetic_data_corpus.py for modularity

@router.get("/templates")
async def get_templates(db: AsyncSession = Depends(get_db_dependency)):
    """Get available templates"""
    return await _fetch_templates(db)


async def _get_templates_safe(db: AsyncSession) -> Dict:
    """Get templates with error handling."""
    try:
        templates = await SyntheticDataService.get_available_templates(db)
        return {"templates": templates, "status": "ok"}
    except Exception as e:
        logger.error(f"Error fetching templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _fetch_templates(db: AsyncSession) -> Dict:
    """Fetch synthetic data templates"""
    return await _get_templates_safe(db)


# Additional endpoints for synthetic data management
@router.post("/export")
async def export_synthetic_data(
    export_request: dict,
    current_user: User = Depends(get_current_user),
):
    """Export synthetic data"""
    try:
        result = await sds.export_data(export_request)
        return result
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_synthetic_data_quality(
    analysis_request: dict,
    current_user: User = Depends(get_current_user),
):
    """Analyze synthetic data quality"""
    try:
        result = await sds.analyze_quality(analysis_request)
        return result
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_synthetic_data(
    cleanup_request: dict,
    current_user: User = Depends(get_current_user),
):
    """Clean up synthetic data jobs"""
    try:
        result = await sds.cleanup_jobs(cleanup_request)
        return result
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert")
async def convert_synthetic_data_format(
    conversion_request: dict,
    current_user: User = Depends(get_current_user),
):
    """Convert synthetic data format"""
    try:
        result = await sds.convert_format(conversion_request)
        return result
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_synthetic_with_real_data(
    comparison_request: dict,
    current_user: User = Depends(get_current_user),
):
    """Compare synthetic with real data"""
    try:
        result = await sds.compare_with_real_data(comparison_request)
        return result
    except Exception as e:
        logger.error(f"Comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/version")
async def create_synthetic_data_version(
    versioning_request: dict,
    current_user: User = Depends(get_current_user),
):
    """Create synthetic data version"""
    try:
        result = await sds.create_version(versioning_request)
        return result
    except Exception as e:
        logger.error(f"Versioning error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-refresh")
async def setup_auto_refresh(
    refresh_config: dict,
    current_user: User = Depends(get_current_user),
):
    """Setup automated synthetic data refresh"""
    try:
        result = await sds.setup_auto_refresh(refresh_config)
        return result
    except Exception as e:
        logger.error(f"Auto-refresh setup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



