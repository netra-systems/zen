from langchain_core.tools import tool
from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field, validator
import json
from app.services.apex_optimizer_agent.models import ToolResult, ToolStatus, IndividualToolResult
import asyncio

class Workload(BaseModel):
    time_range: Union[Dict[str, Any], str] = Field(..., description="The time range for the workload.")
    data_source: Union[Dict[str, Any], str] = Field(..., description="The data source for the workload.")
    timeout: int = Field(default=60, description="The timeout for the workload in seconds.")

    @validator('time_range', 'data_source', pre=True)
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

@tool
async def log_fetcher(workloads: List[Workload], log_fetcher_instance: any) -> ToolResult:
    """
    Fetches raw logs from the database for each workload.
    """
    results = []
    for workload in workloads:
        try:
            time_range = workload.time_range
            data_source = workload.data_source
            if not time_range or not data_source:
                results.append(IndividualToolResult(status=ToolStatus.ERROR, message="Error: time_range and data_source are required for each workload.", payload={}))
                continue
            
            source_table = data_source.get("source_table")
            if not source_table:
                results.append(IndividualToolResult(status=ToolStatus.ERROR, message="Error: source_table is required in the data_source for each workload.", payload={}))
                continue

            logs, trace_ids = await asyncio.wait_for(log_fetcher_instance.fetch_logs(time_range=time_range, source_table=source_table), timeout=workload.timeout)
            results.append(IndividualToolResult(status=ToolStatus.SUCCESS, message=f"Fetched {len(logs)} logs.", payload={"logs": logs, "trace_ids": trace_ids}))
            
        except asyncio.TimeoutError:
            results.append(IndividualToolResult(status=ToolStatus.ERROR, message=f"Error: Log fetching timed out after {workload.timeout} seconds.", payload={}))
        except Exception as e:
            results.append(IndividualToolResult(status=ToolStatus.ERROR, message=f"An unexpected error occurred: {e}", payload={}))

    successful_results = [r for r in results if r.status == ToolStatus.SUCCESS]
    failed_results = [r for r in results if r.status == ToolStatus.ERROR]

    if len(failed_results) == 0:
        status = ToolStatus.SUCCESS
        message = f"Successfully fetched logs for all {len(workloads)} workloads."
    elif len(successful_results) == 0:
        status = ToolStatus.ERROR
        message = f"Failed to fetch logs for all {len(workloads)} workloads."
    else:
        status = ToolStatus.PARTIAL_SUCCESS
        message = f"Successfully fetched logs for {len(successful_results)} out of {len(workloads)} workloads."

    return ToolResult(status=status, message=message, results=results)