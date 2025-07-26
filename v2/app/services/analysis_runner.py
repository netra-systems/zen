# /v2/app/services/analysis_runner.py
import logging
import time
import uuid
import json
import pandas as pd
from typing import Dict, List, Any
from clickhouse_driver import Client
from .engine import AnalysisPipeline
from ..db.models_clickhouse import UnifiedLogEntry, AnalysisRequest

class AnalysisRunner:
    """
    Handles fetching pre-enriched data and running the analysis pipeline.
    """
    def __init__(self, netra_creds: Dict, db_session):
        self.netra_creds = netra_creds
        self.client = Client(**netra_creds)
        self.db_session = db_session
        logging.info("AnalysisRunner initialized.")

    def _fetch_enriched_data(self, database: str, table: str) -> List[UnifiedLogEntry]:
        """Fetches the already-structured data and loads it into SQLModel models."""
        logging.info(f"Fetching enriched data from `{database}`.`{table}` for analysis...")
        query = f"SELECT * FROM {database}.{table}"
        
        query_result = self.client.execute(query, with_column_types=True)
        
        if not query_result or not query_result[0]:
            logging.warning("No data found in the enriched table for analysis.")
            return []
            
        column_names = [col[0] for col in query_result[1]]
        data_rows = query_result[0]

        log_entries = []
        for row in data_rows:
            try:
                row_dict = dict(zip(column_names, row))
                
                # Pydantic/SQLModel will expect nested objects, so parse JSON strings
                for key, value in row_dict.items():
                    if isinstance(value, str) and value.startswith('{'):
                        try:
                            row_dict[key] = json.loads(value)
                        except json.JSONDecodeError:
                            # Not a json string, leave as is
                            pass
                
                log_entries.append(UnifiedLogEntry.model_validate(row_dict))
            except Exception as e:
                logging.warning(f"Skipping a row due to parsing/validation error: {e}. Row data: {row}")
                continue
        
        logging.info(f"Successfully fetched and parsed {len(log_entries)} enriched log entries.")
        return log_entries
        
    def _create_workloads_from_logs(self, logs: List[UnifiedLogEntry]) -> List[Dict]:
        """Aggregates log data to create the workload summary required by the analysis engine."""
        if not logs:
            return []
            
        df = pd.DataFrame([log.model_dump() for log in logs])

        # Handle nested structures for DataFrame creation
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
        
        pipeline = AnalysisPipeline(run_id, analysis_request, self.db_session, preloaded_spans=log_entries)
        
        # Using asyncio to run the pipeline
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            task = loop.create_task(pipeline.run())
        else:
            loop.run_until_complete(pipeline.run())
            
        from .engine import analysis_runs
        
        result = analysis_runs.get(run_id)
        if not result or result.get('status') != 'completed':
            error_msg = result.get('error', 'Unknown error during analysis.') if result else 'Analysis did not complete.'
            logging.error(f"Analysis failed: {error_msg}")
            raise RuntimeError(f"Analysis pipeline failed with error: {error_msg}")

        return result.get('result')

