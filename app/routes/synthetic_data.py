"""
Synthetic Data Generation API Routes
Provides endpoints for generating and managing synthetic AI workload data
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

from app import schemas
from app.services.synthetic_data_service import synthetic_data_service
from app.services.corpus_service import corpus_service
from app.dependencies import get_db_session
from app.auth.auth_dependencies import get_current_user
from app.db.models_postgres import User


# Request/Response Models
class ToolConfig(BaseModel):
    """Tool configuration for generation"""
    name: str
    type: str
    latency_ms_range: tuple[int, int] = Field(default=(50, 500))
    failure_rate: float = Field(default=0.01, ge=0, le=1)


class ScaleConfig(BaseModel):
    """Scale configuration for generation"""
    num_traces: int = Field(gt=0)
    time_window_hours: int = Field(default=24, gt=0)
    concurrent_users: int = Field(default=100, gt=0)
    peak_load_multiplier: float = Field(default=1.0, gt=0)


class AgentConfig(BaseModel):
    """Agent configuration for generation"""
    supervisor_strategy: str = Field(default="round_robin")
    max_retries: int = Field(default=3, ge=0)
    backoff_strategy: str = Field(default="exponential")


class GenerationRequest(BaseModel):
    """Synthetic data generation request"""
    corpus_id: Optional[str] = None
    domain_focus: str
    tool_catalog: List[ToolConfig]
    workload_distribution: Dict[str, float]
    scale_parameters: ScaleConfig
    agent_configuration: Optional[AgentConfig] = None


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


router = APIRouter(prefix="/api/synthetic", tags=["synthetic_data"])


@router.post("/generate", response_model=GenerationResponse)
async def generate_synthetic_data(
    request: GenerationRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate synthetic data generation job
    
    Creates a background task to generate synthetic AI workload data
    based on the provided configuration. Data is streamed to ClickHouse
    in real-time with progress updates via WebSocket.
    """
    try:
        # Convert request to internal schema
        config = schemas.LogGenParams(
            num_logs=request.scale_parameters.num_traces,
            corpus_id=request.corpus_id
        )
        
        # Generate synthetic data
        result = await synthetic_data_service.generate_synthetic_data(
            db=db,
            config=config,
            user_id=current_user.id,
            corpus_id=request.corpus_id
        )
        
        # Calculate estimated duration (rough estimate)
        estimated_duration = request.scale_parameters.num_traces / 100  # 100 records/second estimate
        
        return GenerationResponse(
            job_id=result["job_id"],
            status=result["status"],
            estimated_duration_seconds=int(estimated_duration),
            websocket_channel=result["websocket_channel"],
            table_name=result["table_name"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get generation job status
    
    Returns the current status and progress of a generation job.
    """
    job_status = await synthetic_data_service.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Check if user owns this job
    if job_status.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return JobStatusResponse(
        job_id=job_id,
        status=job_status["status"],
        progress_percentage=(
            job_status["records_generated"] / job_status["config"].num_logs * 100
            if job_status["config"] else 0
        ),
        records_generated=job_status["records_generated"],
        records_ingested=job_status["records_ingested"],
        errors=job_status["errors"],
        started_at=job_status["start_time"],
        completed_at=job_status.get("end_time")
    )


@router.post("/cancel/{job_id}")
async def cancel_generation(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel running generation job
    
    Stops a running generation job and returns the number of records
    that were completed before cancellation.
    """
    job_status = await synthetic_data_service.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Check if user owns this job
    if job_status.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = await synthetic_data_service.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel job")
    
    return {
        "job_id": job_id,
        "status": "cancelled",
        "records_completed": job_status["records_generated"]
    }


@router.get("/preview", response_model=PreviewResponse)
async def preview_synthetic_data(
    corpus_id: Optional[str] = Query(None),
    workload_type: str = Query(...),
    sample_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    Preview sample generated data before full generation
    
    Generates a small sample of synthetic data to preview the output
    before committing to a full generation job.
    """
    samples = await synthetic_data_service.get_preview(
        corpus_id=corpus_id,
        workload_type=workload_type,
        sample_size=sample_size
    )
    
    # Calculate estimated characteristics
    total_latency = sum(
        s["metrics"]["total_latency_ms"] for s in samples
    ) / len(samples) if samples else 0
    
    tool_diversity = len(set(
        tool for s in samples 
        for tool in s["tool_invocations"]
    )) if samples else 0
    
    estimated_characteristics = {
        "avg_latency_ms": total_latency,
        "tool_diversity": tool_diversity,
        "sample_count": len(samples)
    }
    
    return PreviewResponse(
        samples=samples,
        estimated_characteristics=estimated_characteristics
    )


# Corpus Management Endpoints
@router.post("/corpus/create")
async def create_corpus(
    corpus_data: schemas.CorpusCreate,
    content_source: str = Query("upload", pattern="^(upload|generate|import)$"),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create new corpus table in ClickHouse
    
    Creates a new corpus for storing content that will be used
    in synthetic data generation.
    """
    from ..services.corpus_service import ContentSource
    
    source = ContentSource[content_source.upper()]
    
    corpus = await corpus_service.create_corpus(
        db=db,
        corpus_data=corpus_data,
        user_id=current_user.id,
        content_source=source
    )
    
    return {
        "corpus_id": corpus.id,
        "table_name": corpus.table_name,
        "status": corpus.status
    }


@router.post("/corpus/{corpus_id}/upload")
async def upload_corpus_content(
    corpus_id: str,
    records: List[Dict],
    batch_id: Optional[str] = None,
    is_final_batch: bool = False,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Upload content to corpus
    
    Uploads content records to a corpus. Supports batch uploads
    where multiple requests can be made with the same batch_id.
    """
    # Verify corpus ownership
    corpus = await corpus_service.get_corpus(db, corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    if corpus.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await corpus_service.upload_content(
        db=db,
        corpus_id=corpus_id,
        records=records,
        batch_id=batch_id,
        is_final_batch=is_final_batch
    )
    
    return result


@router.get("/corpus/{corpus_id}/content")
async def get_corpus_content(
    corpus_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    workload_type: Optional[str] = None,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get corpus content
    
    Retrieves content from a corpus with optional filtering.
    """
    # Verify corpus ownership
    corpus = await corpus_service.get_corpus(db, corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    if corpus.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    content = await corpus_service.get_corpus_content(
        db=db,
        corpus_id=corpus_id,
        limit=limit,
        offset=offset,
        workload_type=workload_type
    )
    
    return {"content": content}


@router.get("/corpus/{corpus_id}/statistics")
async def get_corpus_statistics(
    corpus_id: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get corpus statistics
    
    Returns statistical information about a corpus including
    record counts, workload distribution, and content metrics.
    """
    # Verify corpus ownership
    corpus = await corpus_service.get_corpus(db, corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    if corpus.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    stats = await corpus_service.get_corpus_statistics(db, corpus_id)
    
    if not stats:
        raise HTTPException(status_code=500, detail="Failed to get statistics")
    
    return stats


@router.delete("/corpus/{corpus_id}")
async def delete_corpus(
    corpus_id: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete corpus
    
    Deletes a corpus and its associated ClickHouse table.
    """
    # Verify corpus ownership
    corpus = await corpus_service.get_corpus(db, corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    if corpus.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success = await corpus_service.delete_corpus(db, corpus_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete corpus")
    
    return {"message": "Corpus deleted successfully"}


@router.post("/corpus/{corpus_id}/clone")
async def clone_corpus(
    corpus_id: str,
    new_name: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """
    Clone an existing corpus
    
    Creates a copy of an existing corpus with a new name.
    """
    # Verify corpus exists and user has access
    corpus = await corpus_service.get_corpus(db, corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    
    # For cloning, we allow if user owns it or it's public (simplified for now)
    if corpus.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    new_corpus = await corpus_service.clone_corpus(
        db=db,
        source_corpus_id=corpus_id,
        new_name=new_name,
        user_id=current_user.id
    )
    
    if not new_corpus:
        raise HTTPException(status_code=500, detail="Failed to clone corpus")
    
    return {
        "corpus_id": new_corpus.id,
        "table_name": new_corpus.table_name,
        "status": new_corpus.status
    }

