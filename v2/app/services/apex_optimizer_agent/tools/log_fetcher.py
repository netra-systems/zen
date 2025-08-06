from langchain_core.tools import tool
from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field, validator
import json

class Workload(BaseModel):
    time_range: Union[Dict[str, Any], str] = Field(..., description="The time range for the workload.")
    data_source: Union[Dict[str, Any], str] = Field(..., description="The data source for the workload.")

    @validator('time_range', 'data_source', pre=True)
    def parse_str_to_dict(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Handle simple strings that are not JSON by wrapping them in a dict.
                # This is a simplistic approach. You may need to adjust this based on expected string formats.
                # For example, if the string is 'last_30_days', you might want to convert it to {'type': 'relative', 'value': 'last_30_days'}
                if 'days' in v:
                    return {'type': 'relative', 'value': v}
                elif v == 'production':
                    return {'source_table': 'production_logs'}
                else:
                    raise ValueError("Cannot parse string to dictionary")
        return v

@tool
async def log_fetcher(workloads: List[Workload], log_fetcher: any) -> str:
    """
    Fetches raw logs from the database for each workload.
    """
    all_logs = []
    all_trace_ids = []
    for workload in workloads:
        time_range = workload.time_range
        data_source = workload.data_source
        if not time_range or not data_source:
            return "Error: time_range and data_source are required for each workload."
        
        source_table = data_source.get("source_table")
        if not source_table:
            return "Error: source_table is required in the data_source for each workload."

        logs, trace_ids = log_fetcher.fetch_logs(time_range=time_range, source_table=source_table)
        all_logs.extend(logs)
        all_trace_ids.extend(trace_ids)
        
    return f"Fetched {len(all_logs)} logs for {len(workloads)} workloads."
