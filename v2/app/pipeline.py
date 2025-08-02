# v2/app/pipeline.py
import logging
import json
from datetime import datetime
import uuid

from sqlmodel import Session

from .services.security_service import security_service
from .services.analysis_runner import AnalysisRunner
from .db.postgres import SessionLocal
from .schema import AnalysisRun
from .logging_config_custom.logger import logger
from .db.models_clickhouse import AnalysisResult


def run_full_analysis_pipeline(run_id: uuid.UUID, user_id: str, use_deepagents: bool = False, use_deepagents_v2: bool = False):
    """
    The main function that orchestrates the analysis pipeline.
    It's designed to be run in the background.
    """
    logger.info(f"Starting pipeline for run_id: {run_id}")
    db: Session = SessionLocal()
    run = None  # Define run here to be accessible in finally

    def log_to_run(message: str):
        """Helper to append messages to the run's execution log."""
        if run:
            new_log = f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}: {message}"
            if run.execution_log is None:
                run.execution_log = new_log
            else:
                run.execution_log += f"\n{new_log}"
            db.add(run)
            db.commit()

    try:
        # 1. Fetch the AnalysisRun object
        run = db.get(AnalysisRun, run_id)
        if not run:
            logger.error(f"Run with ID {run_id} not found. Aborting pipeline.")
            return

        run.status = "running"
        db.add(run)
        db.commit()
        log_to_run("Analysis run started.")

        # 2. Retrieve user's ClickHouse credentials
        credentials = security_service.get_user_credentials(user_id=user_id, db_session=db)
        if not credentials:
            raise ValueError("ClickHouse credentials not found for user.")
        log_to_run("Successfully retrieved user credentials.")

        # 3. Initialize and run the analysis
        source_table = run.config.get("source_table")
        if not source_table:
            raise ValueError("source_table not defined in run configuration.")
        
        try:
            database, table = source_table.split('.', 1)
        except ValueError:
            raise ValueError(f"Invalid source_table format: '{source_table}'. Expected 'database.table'.")
        
        log_to_run(f"Preparing to analyze table: {source_table}")
            
        runner = AnalysisRunner(
            netra_creds=credentials.model_dump(),
            db_session=db
        )
        
        # This is the main execution block
        analysis_result_dict = runner.execute(
            database=database, 
            table=table, 
            use_deepagents=use_deepagents,
            use_deepagents_v2=use_deepagents_v2
        )
        
        analysis_result = AnalysisResult.model_validate(analysis_result_dict)

        log_to_run("Analysis execution completed.")

        # 4. Update the AnalysisRun with results
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        if analysis_result.cost_comparison:
            run.result_summary = analysis_result.cost_comparison.model_dump()
        
        run.result_details = analysis_result.model_dump(exclude={'span_map'}) 
        
        if analysis_result.execution_log:
             run.execution_log = "\n".join(f"{log.get('timestamp', '')}: {log.get('message', '')}" for log in analysis_result.execution_log)
        
        log_to_run("Analysis results processed and saved.")

    except Exception as e:
        error_message = f"ERROR: {e}"
        logger.error(f"An error occurred in the main pipeline for run {run_id}: {e}", exc_info=True)
        if run:
            run.status = 'failed'
            log_to_run(error_message)
    finally:
        if run:
            run.completed_at = datetime.utcnow()
            db.add(run)
            db.commit()
        db.close()
        logging.info(f"Pipeline finished for run_id: {run_id} with final status: {run.status if run else 'UNKNOWN'}")
