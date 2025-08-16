"""Synthetic data route specific utilities."""

from typing import Dict, Any, List, Optional
from app import schemas
from app.routes.utils.validators import validate_job_ownership
from app.routes.utils.error_handlers import handle_validation_error


def build_generation_config(request) -> schemas.LogGenParams:
    """Build generation config from request."""
    return schemas.LogGenParams(
        num_logs=request.scale_parameters.num_traces,
        corpus_id=request.corpus_id
    )


async def execute_generation_safely(
    db, config: schemas.LogGenParams, user_id: int, corpus_id: Optional[str]
):
    """Execute generation with error handling."""
    from app.services.synthetic_data_service import synthetic_data_service
    return await synthetic_data_service.generate_synthetic_data(
        db=db, config=config, user_id=user_id, corpus_id=corpus_id
    )


def calculate_estimated_duration(num_traces: int) -> int:
    """Calculate estimated generation duration."""
    return int(num_traces / 100)


def extract_result_fields(result: Dict, num_traces: int) -> Dict:
    """Extract fields for generation response."""
    return {
        "job_id": result["job_id"],
        "status": result["status"],
        "websocket_channel": result["websocket_channel"],
        "table_name": result["table_name"],
        "estimated_duration_seconds": calculate_estimated_duration(num_traces)
    }


async def fetch_and_validate_job_status(job_id: str, user_id: int) -> Dict:
    """Fetch and validate job status."""
    from app.services.synthetic_data_service import synthetic_data_service
    status = await synthetic_data_service.get_job_status(job_id)
    validate_job_ownership(status, user_id, job_id)
    return status


def calculate_progress(status: Dict) -> float:
    """Calculate generation progress."""
    if not status.get("config"):
        return 0
    generated = status["records_generated"]
    total = status["config"].num_logs
    return (generated / total * 100) if total > 0 else 0


def extract_status_fields(status: Dict) -> Dict:
    """Extract status fields for response building."""
    return {
        "status": status["status"],
        "progress_percentage": calculate_progress(status),
        "records_generated": status["records_generated"],
        "records_ingested": status["records_ingested"],
        "errors": status["errors"],
        "started_at": status["start_time"],
        "completed_at": status.get("end_time")
    }


async def cancel_job_safely(job_id: str) -> None:
    """Cancel job execution safely."""
    from app.services.synthetic_data_service import synthetic_data_service
    success = await synthetic_data_service.cancel_job(job_id)
    if not success:
        handle_validation_error("Failed to cancel job")


def build_cancel_response(job_id: str, status: Dict) -> Dict:
    """Build cancellation response."""
    return {
        "job_id": job_id,
        "status": "cancelled",
        "records_completed": status["records_generated"]
    }


async def get_preview_samples_safely(
    corpus_id: Optional[str], workload_type: str, sample_size: int
) -> List[Dict]:
    """Get preview samples safely."""
    from app.services.synthetic_data_service import synthetic_data_service
    return await synthetic_data_service.get_preview(
        corpus_id=corpus_id,
        workload_type=workload_type,
        sample_size=sample_size
    )


def calculate_characteristics(samples: List[Dict]) -> Dict:
    """Calculate sample characteristics."""
    if not samples:
        return {"avg_latency_ms": 0, "tool_diversity": 0, "sample_count": 0}
    return {
        "avg_latency_ms": _calculate_avg_latency(samples),
        "tool_diversity": _calculate_tool_diversity(samples),
        "sample_count": len(samples)
    }


def _calculate_avg_latency(samples: List[Dict]) -> float:
    """Calculate average latency."""
    total = sum(s["metrics"]["total_latency_ms"] for s in samples)
    return total / len(samples)


def _calculate_tool_diversity(samples: List[Dict]) -> int:
    """Calculate tool diversity."""
    tools = set()
    for sample in samples:
        tools.update(sample.get("tool_invocations", []))
    return len(tools)


def generate_test_user_data(count: int) -> List[Dict]:
    """Generate realistic test user data records using production-quality patterns."""
    import uuid
    import random
    from datetime import datetime, UTC, timedelta
    
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    domains = ["example.com", "test.org", "demo.net", "sample.co"]
    
    return [
        {
            "user_id": f"usr_{uuid.uuid4().hex[:8]}",
            "name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "age": random.randint(18, 75),
            "email": f"user{i}@{random.choice(domains)}",
            "created_at": (datetime.now(UTC) - timedelta(days=random.randint(1, 365))).isoformat(),
            "status": random.choice(["active", "inactive", "pending"])
        }
        for i in range(count)
    ]