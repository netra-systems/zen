"""Synthetic data route specific utilities."""

from typing import Dict, Any, List, Optional
from netra_backend.app import schemas
from netra_backend.app.routes.utils.validators import validate_job_ownership
from netra_backend.app.routes.utils.error_handlers import handle_validation_error


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
    from netra_backend.app.services.synthetic_data_service import synthetic_data_service
    return await synthetic_data_service.generate_synthetic_data(
        db=db, config=config, user_id=user_id, corpus_id=corpus_id
    )


def calculate_estimated_duration(num_traces: int) -> int:
    """Calculate estimated generation duration."""
    return int(num_traces / 100)


def _get_result_basic_fields(result: Dict) -> Dict:
    """Get basic result fields."""
    return {"job_id": result["job_id"], "status": result["status"]}

def _get_result_extended_fields(result: Dict, num_traces: int) -> Dict:
    """Get extended result fields."""
    return {
        "websocket_channel": result["websocket_channel"],
        "table_name": result["table_name"],
        "estimated_duration_seconds": calculate_estimated_duration(num_traces)
    }

def _build_result_fields_dict(result: Dict, num_traces: int) -> Dict:
    """Build result fields dictionary."""
    basic = _get_result_basic_fields(result)
    extended = _get_result_extended_fields(result, num_traces)
    return {**basic, **extended}

def extract_result_fields(result: Dict, num_traces: int) -> Dict:
    """Extract fields for generation response."""
    return _build_result_fields_dict(result, num_traces)


async def fetch_and_validate_job_status(job_id: str, user_id: int) -> Dict:
    """Fetch and validate job status."""
    from netra_backend.app.services.synthetic_data_service import synthetic_data_service
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


def _extract_basic_status_fields(status: Dict) -> Dict:
    """Extract basic status fields."""
    return {
        "status": status["status"],
        "progress_percentage": calculate_progress(status),
        "records_generated": status["records_generated"],
        "records_ingested": status["records_ingested"]
    }

def _extract_timing_and_error_fields(status: Dict) -> Dict:
    """Extract timing and error fields."""
    return {
        "errors": status["errors"],
        "started_at": status["start_time"],
        "completed_at": status.get("end_time")
    }

def extract_status_fields(status: Dict) -> Dict:
    """Extract status fields for response building."""
    basic_fields = _extract_basic_status_fields(status)
    timing_fields = _extract_timing_and_error_fields(status)
    return {**basic_fields, **timing_fields}


async def cancel_job_safely(job_id: str) -> None:
    """Cancel job execution safely."""
    from netra_backend.app.services.synthetic_data_service import synthetic_data_service
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


async def _call_preview_service(corpus_id: Optional[str], workload_type: str, sample_size: int) -> List[Dict]:
    """Call preview service with parameters."""
    from netra_backend.app.services.synthetic_data_service import synthetic_data_service
    return await synthetic_data_service.get_preview(
        corpus_id=corpus_id,
        workload_type=workload_type,
        sample_size=sample_size
    )

async def get_preview_samples_safely(
    corpus_id: Optional[str], workload_type: str, sample_size: int
) -> List[Dict]:
    """Get preview samples safely."""
    return await _call_preview_service(corpus_id, workload_type, sample_size)


def _get_empty_characteristics() -> Dict:
    """Get empty characteristics dictionary."""
    return {"avg_latency_ms": 0, "tool_diversity": 0, "sample_count": 0}

def _build_characteristics_dict(samples: List[Dict]) -> Dict:
    """Build characteristics dictionary from samples."""
    return {
        "avg_latency_ms": _calculate_avg_latency(samples),
        "tool_diversity": _calculate_tool_diversity(samples),
        "sample_count": len(samples)
    }

def calculate_characteristics(samples: List[Dict]) -> Dict:
    """Calculate sample characteristics."""
    if not samples:
        return _get_empty_characteristics()
    return _build_characteristics_dict(samples)


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


def _get_test_data_constants() -> tuple:
    """Get constant data for test user generation."""
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    domains = ["example.com", "test.org", "demo.net", "sample.co"]
    statuses = ["active", "inactive", "pending"]
    return first_names, last_names, domains, statuses

def _generate_random_user_id() -> str:
    """Generate random user ID."""
    import uuid
    return f"usr_{uuid.uuid4().hex[:8]}"

def _generate_random_name(first_names: List[str], last_names: List[str]) -> str:
    """Generate random full name."""
    import random
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def _generate_random_email(i: int, domains: List[str]) -> str:
    """Generate random email address."""
    import random
    return f"user{i}@{random.choice(domains)}"

def _generate_random_created_date() -> str:
    """Generate random creation date."""
    import random
    from datetime import datetime, UTC, timedelta
    return (datetime.now(UTC) - timedelta(days=random.randint(1, 365))).isoformat()

def _build_user_basic_fields(i: int, first_names: List[str], last_names: List[str], domains: List[str]) -> Dict:
    """Build basic user fields."""
    return {
        "user_id": _generate_random_user_id(),
        "name": _generate_random_name(first_names, last_names),
        "email": _generate_random_email(i, domains)
    }


def _build_user_additional_fields(statuses: List[str]) -> Dict:
    """Build additional user fields."""
    import random
    return {
        "age": random.randint(18, 75),
        "created_at": _generate_random_created_date(),
        "status": random.choice(statuses)
    }


def _create_single_user_record(i: int, first_names: List[str], last_names: List[str], domains: List[str], statuses: List[str]) -> Dict:
    """Create single user record."""
    basic_fields = _build_user_basic_fields(i, first_names, last_names, domains)
    additional_fields = _build_user_additional_fields(statuses)
    return {**basic_fields, **additional_fields}

def generate_test_user_data(count: int) -> List[Dict]:
    """Generate realistic test user data records using production-quality patterns."""
    first_names, last_names, domains, statuses = _get_test_data_constants()
    return [
        _create_single_user_record(i, first_names, last_names, domains, statuses)
        for i in range(count)
    ]