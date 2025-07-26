# /services/analysis_runner.py
import logging
import time
import uuid
import json
import pandas as pd
from typing import Dict, List, Any
from clickhouse_driver import Client
from .engine import AnalysisPipeline, AnalysisRequest, UnifiedLogEntry
from services.data.database import SupplyOptionDB

class AnalysisRunner:
    """
    Handles fetching pre-enriched data and running the analysis pipeline.
    """
    def __init__(self, netra_creds: Dict):
        self.netra_creds = netra_creds
        self.client = Client(**netra_creds)
        logging.info("AnalysisRunner initialized.")

    def _fetch_enriched_data(self, database: str, table: str) -> List[UnifiedLogEntry]:
        """Fetches the already-structured data and loads it into Pydantic models."""
        logging.info(f"Fetching enriched data from `{database}`.`{table}` for analysis...")
        # The schema of this table is created by DataEnricher to match UnifiedLogEntry
        query = f"SELECT * FROM {database}.{table}"
        
        query_result = self.client.execute(query, with_column_types=True)
        
        if not query_result[0]:
            logging.warning("No data found in the enriched table for analysis.")
            return []
            
        column_names = [col[0] for col in query_result[1]]
        data_rows = query_result[0]

        log_entries = []
        for row in data_rows:
            try:
                # Convert the row tuple to a dictionary
                row_dict = {name: val for name, val in zip(column_names, row)}
                
                # Parse the JSON strings back into Python objects
                for key, value in row_dict.items():
                    if isinstance(value, str) and key != 'workloadName':
                        # Only parse if it's a non-empty string that looks like a JSON object
                        if value and value.startswith('{'):
                            row_dict[key] = json.loads(value)

                # Validate with the main Pydantic model
                log_entries.append(UnifiedLogEntry(**row_dict))
            except (json.JSONDecodeError, TypeError, Exception) as e:
                logging.warning(f"Skipping a row due to parsing/validation error: {e}. Row data: {row}")
                continue
        
        logging.info(f"Successfully fetched and parsed {len(log_entries)} enriched log entries.")
        return log_entries
        
    def _create_workloads_from_logs(self, logs: List[UnifiedLogEntry]) -> List[Dict]:
        """Aggregates log data to create the workload summary required by the analysis engine."""
        if not logs:
            return []
            
        # This function remains useful as it summarizes the detailed logs into high-level workloads.
        df = pd.DataFrame([log.dict() for log in logs])

        df['total_cost_usd'] = df['finops'].apply(lambda x: x.get('total_cost_usd', 0))
        df['model_name'] = df['request'].apply(lambda x: x['model'].get('name', 'unknown'))
        df['user_goal'] = df['request'].apply(lambda x: x.get('user_goal', 'quality'))
        
        workloads = df.groupby('workloadName').agg(
            spend=('total_cost_usd', 'sum'),
            model=('model_name', 'first'),
            goal=('user_goal', 'first')
        ).reset_index()
        
        workloads.rename(columns={'workloadName': 'name'}, inplace=True)
        
        logging.info(f"Aggregated logs into {len(workloads)} workloads.")
        return workloads.to_dict('records')

    def run_analysis(self, database: str, table: str) -> Dict[str, Any]:
        """Runs the full analysis pipeline on the pre-enriched data."""
        log_entries = self._fetch_enriched_data(database, table)
        if not log_entries:
            raise ValueError("Cannot run analysis, no data was fetched from the enriched table.")
            
        workloads = self._create_workloads_from_logs(log_entries)
        if not workloads:
            raise ValueError("Cannot run analysis, failed to create workloads summary from log entries.")
        
        analysis_request = AnalysisRequest(
            workloads=workloads,
            debug_mode=True,
            negotiated_discount_percent=5.0
        )

        import asyncio
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        
        # Pass the pre-loaded and pre-enriched spans directly to the pipeline
        pipeline = AnalysisPipeline(run_id, analysis_request, preloaded_spans=log_entries)
        
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(pipeline.run())
        else:
            task = loop.run_until_complete(pipeline.run())
            
        from services.engine_adapted import analysis_runs
        
        result = analysis_runs.get(run_id, {})
        if result.get('status') == 'completed':
            return result.get('result')
        else:
            error_msg = result.get('error', 'Unknown error during analysis.')
            logging.error(f"Analysis failed: {error_msg}")
            raise RuntimeError(f"Analysis pipeline failed with error: {error_msg}")
