from langchain_core.tools import tool
from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field, validator
import json
from app.services.apex_optimizer_agent.models import ToolInvocation, ToolStatus
import asyncio
from app.services.context import ToolContext

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
async def log_fetcher(context: ToolContext, workloads: List[Workload]) -> ToolInvocation:
    """
    Fetches raw logs from the database for each workload.
    """
    invocation = ToolInvocation(tool_name="log_fetcher", workloads=workloads)
    results = []
    for workload in workloads:
        try:
            time_range = workload.time_range
            data_source = workload.data_source
            if not time_range or not data_source:
                results.append(ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, message="Error: time_range and data_source are required for each workload.", payload={}))
                continue
            
            source_table = data_source.get("source_table")
            if not source_table:
                results.append(ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, message="Error: source_table is required in the data_source for each workload.", payload={}))
                continue

            logs, trace_ids = await asyncio.wait_for(context.db_session.fetch_logs(time_range=time_range, source_table=source_table), timeout=workload.timeout)
            results.append(ToolInvocation(tool_name="log_fetcher", status=ToolStatus.SUCCESS, message=f"Fetched {len(logs)} logs.", payload={"logs": logs, "trace_ids": trace_ids}))
            
        except asyncio.TimeoutError:
            results.append(ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, message=f"Error: Log fetching timed out after {workload.timeout} seconds.", payload={}))
        except ConnectionError:
            results.append(ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, message="Error: Failed to connect to the database.", payload={}))
        except Exception as e:
            results.append(ToolInvocation(tool_name="log_fetcher", status=ToolStatus.ERROR, message=f"An unexpected error occurred: {e}", payload={}))

    successful_results = [r for r in results if r.tool_result.status == ToolStatus.SUCCESS]
    failed_results = [r for r in results if r.tool_result.status == ToolStatus.ERROR]

    if len(failed_results) == 0:
        status = ToolStatus.SUCCESS
        message = f"Successfully fetched logs for all {len(workloads)} workloads."
    elif len(successful_results) == 0:
        status = ToolStatus.ERROR
        message = f"Failed to fetch logs for all {len(workloads)} workloads."
    else:
        status = ToolStatus.PARTIAL_SUCCESS
        message = f"Successfully fetched logs for {len(successful_results)} out of {len(workloads)} workloads."

    invocation.set_result(status=status, message=message, payload=results)
    return invocation