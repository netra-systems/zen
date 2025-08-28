"""Synthetic data generation job service.

Provides job management wrapper for synthetic data generation,
following the pattern of other generation services.
"""

from typing import Dict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.generation import SyntheticDataGenParams
from netra_backend.app.services.generation_job_manager import (
    update_job_status,
    validate_job_params,
)
from netra_backend.app.services.synthetic_data_service import synthetic_data_service

logger = central_logger.get_logger(__name__)


def _convert_params_to_schema(params: dict) -> SyntheticDataGenParams:
    """Convert dict params to SyntheticDataGenParams schema."""
    return SyntheticDataGenParams(**params)


async def _execute_synthetic_data_generation(job_id: str, params: dict):
    """Execute synthetic data generation with proper job tracking."""
    schema_params = _convert_params_to_schema(params)
    await update_job_status(job_id, "running", progress=0)
    result = await synthetic_data_service.generate_synthetic_data(
        schema_params, job_id=job_id
    )
    return result


async def _handle_generation_error(job_id: str, error: Exception):
    """Handle generation errors with proper status updates."""
    logger.exception("Error during synthetic data generation")
    error_message = f"Synthetic data generation failed: {str(error)}"
    await update_job_status(job_id, "failed", error=error_message)


async def run_synthetic_data_generation_job(job_id: str, params: dict):
    """Main job runner for synthetic data generation."""
    if not await validate_job_params(job_id, api_key_required=False):
        return
    try:
        result = await _execute_synthetic_data_generation(job_id, params)
        await update_job_status(job_id, "completed", summary=result)
    except Exception as e:
        await _handle_generation_error(job_id, e)