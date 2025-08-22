import asyncio
import json
from typing import Any, Dict, List, Optional, Union

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from netra_backend.app.services.apex_optimizer_agent.models import (
    ToolInvocation,
    ToolStatus,
)
from netra_backend.app.services.context import ToolContext


class Workload(BaseModel):
    time_range: Union[Dict[str, Any], str] = Field(..., description="The time range for the workload.")
    data_source: Union[Dict[str, Any], str] = Field(..., description="The data source for the workload.")
    timeout: int = Field(default=60, description="The timeout for the workload in seconds.")

    @field_validator('time_range', 'data_source', mode='before')
    @classmethod
    def parse_str_to_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                if 'days' in v:
                    return {'type': 'relative', 'value': v}
                elif v == 'production':
                    return {'source_table': 'production_logs'}
                else:
                    raise ValueError("Cannot parse string to dictionary")
        return v

def _check_basic_params(workload: Workload) -> Optional[ToolInvocation]:
    """Check basic workload parameters"""
    if not workload.time_range or not workload.data_source:
        return ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, 
                            message="Error: time_range and data_source are required for each workload.", payload={})
    return None

def _check_source_table(workload: Workload) -> Optional[ToolInvocation]:
    """Check source table parameter"""
    source_table = workload.data_source.get("source_table")
    if not source_table:
        return ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, 
                            message="Error: source_table is required in the data_source for each workload.", payload={})
    return None

def _validate_workload_params(workload: Workload) -> Optional[ToolInvocation]:
    """Validate workload parameters"""
    basic_error = _check_basic_params(workload)
    if basic_error:
        return basic_error
    return _check_source_table(workload)

async def _execute_log_fetch(context: ToolContext, workload: Workload) -> tuple:
    """Execute log fetching operation"""
    return await asyncio.wait_for(
        context.db_session.fetch_logs(time_range=workload.time_range, 
                                    source_table=workload.data_source.get("source_table")), 
        timeout=workload.timeout)

def _create_success_result(logs, trace_ids) -> ToolInvocation:
    """Create success result for log fetching"""
    return ToolInvocation(tool_name="log_fetcher", status=ToolStatus.SUCCESS, 
                        message=f"Fetched {len(logs)} logs.", payload={"logs": logs, "trace_ids": trace_ids})

def _create_timeout_error(workload: Workload) -> ToolInvocation:
    """Create timeout error result"""
    return ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, 
                        message=f"Error: Log fetching timed out after {workload.timeout} seconds.", payload={})

def _create_connection_error() -> ToolInvocation:
    """Create connection error result"""
    return ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, 
                        message="Error: Failed to connect to the database.", payload={})

def _create_general_error(error: Exception) -> ToolInvocation:
    """Create general error result"""
    return ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, 
                        message=f"An unexpected error occurred: {error}", payload={})

async def _fetch_workload_logs(context: ToolContext, workload: Workload) -> ToolInvocation:
    """Fetch logs for a single workload"""
    try:
        logs, trace_ids = await _execute_log_fetch(context, workload)
        return _create_success_result(logs, trace_ids)
    except asyncio.TimeoutError:
        return _create_timeout_error(workload)
    except ConnectionError:
        return _create_connection_error()
    except Exception as e:
        return _create_general_error(e)

async def _process_single_workload(context: ToolContext, workload: Workload) -> ToolInvocation:
    """Process a single workload with validation"""
    validation_error = _validate_workload_params(workload)
    if validation_error:
        return validation_error
    return await _fetch_workload_logs(context, workload)

def _determine_final_status(successful_results: List, failed_results: List, total_workloads: int) -> tuple[ToolStatus, str]:
    """Determine final status and message"""
    if len(failed_results) == 0:
        return ToolStatus.SUCCESS, f"Successfully fetched logs for all {total_workloads} workloads."
    elif len(successful_results) == 0:
        return ToolStatus.ERROR, f"Failed to fetch logs for all {total_workloads} workloads."
    else:
        return ToolStatus.PARTIAL_SUCCESS, f"Successfully fetched logs for {len(successful_results)} out of {total_workloads} workloads."

@tool
async def log_fetcher(context: ToolContext, workloads: List[Workload]) -> ToolInvocation:
    """
    Fetches raw logs from the database for each workload.
    """
    invocation = ToolInvocation(tool_name="log_fetcher", workloads=workloads)
    results = [await _process_single_workload(context, workload) for workload in workloads]
    successful_results = [r for r in results if r.tool_result.status == ToolStatus.SUCCESS]
    failed_results = [r for r in results if r.tool_result.status == ToolStatus.ERROR]
    status, message = _determine_final_status(successful_results, failed_results, len(workloads))
    invocation.set_result(status=status, message=message, payload=results)
    return invocation