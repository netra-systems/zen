# v2/app/pipeline_v2_4.py
import os
import logging
import json
from datetime import datetime

from .services.security_service import security_service
from .data.data_copier import DataCopier
from .data.data_enricher import DataEnricher
from .services.analysis_runner import AnalysisRunner
from .db import models_postgres
from .config import settings

def run_full_analysis_pipeline(run_id: uuid.UUID, user_id: str):
    """
    The main function that orchestrates the analysis pipeline.
    It's designed to be run in the background.
    """
    logger.info(f"Starting pipeline for run_id: {run_id}")
    db: Session = SessionLocal()
    
    try:
        # 1. Fetch the AnalysisRun object
        run = db.get(AnalysisRun, run_id)
        if not run:
            logger.error(f"Run with ID {run_id} not found. Aborting pipeline.")
            return

        run.status = "running"
        db.add(run)
        db.commit()

        # 2. Retrieve user's ClickHouse credentials
        credentials = security_service.get_user_credentials(user_id=user_id, db_session=db)
        if not credentials:
            raise ValueError("ClickHouse credentials not found for user.")

        # 3. Initialize and run the analysis
        source_table = run.config.get("source_table")
        if not source_table:
            raise ValueError("source_table not defined in run configuration.")
            
        runner = AnalysisRunner(
            run_id=str(run_id),
            source_table=source_table,
            clickhouse_creds=credentials
        )
        
        # This is the main execution block
        analysis_result = runner.execute()

        # 4. Update the AnalysisRun with results
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.result_summary = analysis_result.cost_comparison.model_dump()
        run.result_details = analysis_result.model_dump(exclude={'span_map'}) # Exclude large fields from details
        run.execution_log = "\n".join(f"{log['timestamp']}: {log['message']}" for log in analysis_result.execution_log)
        
        if analysis_results:
            log_to_run("Analysis completed successfully.")
            run.status = 'completed'
            run.result_summary = analysis_results.get('cost_comparison')
            run.result_details = {
                "discovered_patterns": analysis_results.get('discovered_patterns'),
                "learned_policies": analysis_results.get('learned_policies')
            }
            output_filename = f"analysis_results_{user_id}_{run_id}.json"
            with open(output_filename, 'w') as f:
                json.dump(analysis_results, f, indent=4, default=str)
            log_to_run(f"Detailed analysis results saved to {output_filename}")

    except Exception as e:
        error_message = f"ERROR: {e}"
        logging.error(f"An error occurred in the main pipeline for run {run_id}: {e}", exc_info=True)
        if run:
            run.status = 'failed'
            log_to_run(error_message)
    finally:
        # This block ensures that the final state of the run is always saved.
        if run:
            run.completed_at = datetime.utcnow()
            db_session.commit()
        db_session.close()
        logging.info(f"Pipeline finished for run_id: {run_id} with final status: {run.status if run else 'UNKNOWN'}")