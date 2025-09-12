"""
E2E Test #7: Complete File Upload Pipeline Validation
Business Value: $45K MRR - Document analysis features for enterprise customers

Tests real file upload through entire pipeline:
Frontend  ->  Backend  ->  Agent  ->  Storage  ->  WebSocket Response

NO MOCKING - Uses real file processing and agent analysis.
Execution time: < 10 seconds for complete pipeline validation.

Modular architecture following 450-line and 25-line function limits.
"""

import asyncio
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.integration.file_upload_test_runners import (
    execute_concurrent_upload_workflow,
    execute_error_handling_workflow,
    execute_performance_test_workflow,
    execute_single_user_pipeline_test,
    validate_concurrent_results,
    validate_enterprise_requirements,
    validate_error_resilience,
    validate_pipeline_results,
)
from tests.e2e.integration.unified_e2e_harness import create_e2e_harness


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_file_upload_pipeline():
    """Test complete file upload and processing pipeline."""
    async with create_e2e_harness().test_environment() as harness:
        result = await execute_single_user_pipeline_test(harness, 5.0)
        validate_pipeline_results(result)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_pipeline_performance_requirements():
    """Validate pipeline meets performance requirements for enterprise customers."""
    async with create_e2e_harness().test_environment() as harness:
        result = await execute_performance_test_workflow(harness)
        validate_enterprise_requirements(result)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_file_upload_error_handling():
    """Test file upload pipeline error handling and recovery."""
    async with create_e2e_harness().test_environment() as harness:
        result = await execute_error_handling_workflow(harness)
        validate_error_resilience(result)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_file_uploads():
    """Test concurrent file upload processing."""
    async with create_e2e_harness().test_environment() as harness:
        results = await execute_concurrent_upload_workflow(harness)
        validate_concurrent_results(results)


if __name__ == "__main__":
    print("Running E2E File Upload Pipeline Test...")
    asyncio.run(test_complete_file_upload_pipeline())
    print("[U+2713] File upload pipeline test completed successfully")
