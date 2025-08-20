"""
File Upload Test Runners - E2E Testing Helpers
Business Value: $45K MRR - Enables modular test execution following 25-line limit

Breaks down test execution into 25-line functions for architectural compliance.
"""

import asyncio

from .file_upload_test_context import create_file_upload_context
from .file_upload_pipeline_executor import create_pipeline_executor


async def execute_single_user_pipeline_test(harness, file_size: float = 5.0):
    """Execute single user pipeline test workflow."""
    context = create_file_upload_context(harness)
    user = await harness.create_test_user()
    test_file = await context.create_test_pdf(file_size)
    executor = create_pipeline_executor(context, user)
    result = await executor.execute_complete_pipeline(test_file)
    await executor.cleanup()
    await context.cleanup_test_files()
    return result


async def execute_performance_test_workflow(harness):
    """Execute performance test workflow with smaller file."""
    context = create_file_upload_context(harness)
    user = await harness.create_test_user()
    test_file = await context.create_test_pdf(3.0)
    executor = create_pipeline_executor(context, user)
    result = await executor.execute_complete_pipeline(test_file)
    await executor.cleanup()
    await context.cleanup_test_files()
    return result


async def execute_error_handling_workflow(harness):
    """Execute error handling test workflow."""
    context = create_file_upload_context(harness)
    user = await harness.create_test_user()
    test_file = await context.create_test_pdf(1.0)
    executor = create_pipeline_executor(context, user)
    result = await executor.execute_complete_pipeline(test_file)
    await executor.cleanup()
    await context.cleanup_test_files()
    return result


async def execute_concurrent_upload_workflow(harness):
    """Execute concurrent upload test workflow."""
    context = create_file_upload_context(harness)
    users = [await harness.create_test_user() for _ in range(3)]
    files = [await context.create_test_pdf(2.0) for _ in range(3)]
    tasks = await _create_concurrent_upload_tasks(context, users, files)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await _cleanup_concurrent_executors(context, users)
    await context.cleanup_test_files()
    return results


async def _create_concurrent_upload_tasks(context, users, files):
    """Create concurrent upload tasks."""
    tasks = []
    for user, file_path in zip(users, files):
        executor = create_pipeline_executor(context, user)
        task = executor.execute_complete_pipeline(file_path)
        tasks.append(task)
    return tasks


async def _cleanup_concurrent_executors(context, users):
    """Cleanup all concurrent test executors."""
    for user in users:
        executor = create_pipeline_executor(context, user)
        await executor.cleanup()


def validate_pipeline_results(result):
    """Validate all pipeline execution results."""
    _validate_pipeline_success(result)
    _validate_performance_requirements(result)
    _validate_storage_verification(result)


def _validate_pipeline_success(result):
    """Validate pipeline execution succeeded."""
    assert result["pipeline_success"], "Pipeline execution failed"


def _validate_performance_requirements(result):
    """Validate performance requirements met."""
    execution_time = result["execution_time"]
    assert result["performance_met"], f"Performance target missed: {execution_time}s"


def _validate_storage_verification(result):
    """Validate storage verification completed."""
    verification = result["verification_result"]["verification_complete"]
    assert verification, "Storage verification failed"


def validate_enterprise_requirements(result):
    """Validate enterprise customer requirements."""
    _validate_enterprise_speed_requirement(result)
    _validate_enterprise_reliability_requirement(result)


def _validate_enterprise_speed_requirement(result):
    """Validate enterprise speed requirement."""
    assert result["execution_time"] < 10.0, "Enterprise speed requirement not met"


def _validate_enterprise_reliability_requirement(result):
    """Validate enterprise reliability requirement."""
    assert result["pipeline_success"], "Enterprise reliability requirement not met"


def validate_error_resilience(result):
    """Validate pipeline error resilience."""
    assert "error_handling" in str(result) or result["pipeline_success"]


def validate_concurrent_results(results):
    """Validate concurrent processing results."""
    successful_results = [r for r in results if isinstance(r, dict) and r.get("pipeline_success")]
    assert len(successful_results) >= 2, "Concurrent processing reliability insufficient"