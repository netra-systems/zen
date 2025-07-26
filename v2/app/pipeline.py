# /v2/app/pipeline.py
import os
import logging
import json
from dotenv import load_dotenv
from datetime import datetime

from .services.security_service import security_service
from .data.data_copier import DataCopier
from .data.data_enricher import DataEnricher
from .services.analysis_runner import AnalysisRunner
from . import database
from .db import models_postgres
from .config import settings

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

def run_full_analysis_pipeline(run_id: str, user_id: int):
    """
    Orchestrates the entire analysis workflow.
    This function is run in the background.
    """
    logging.info(f"Starting Netra Log Ingest and Analysis Pipeline for run_id: {run_id}, user_id: {user_id}")
    
    db_session = next(database.get_db())
    run = db_session.get(models_postgres.AnalysisRun, run_id)

    def log_to_run(message: str):
        nonlocal run
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        log_entry = f"[{timestamp}] {message}\n"
        run.execution_log = (run.execution_log or "") + log_entry
        db_session.commit()
        logging.info(f"Run {run_id}: {message}")

    try:
        if not run:
            logging.error(f"AnalysisRun with id {run_id} not found. Aborting pipeline.")
            return

        run.status = 'running'
        db_session.commit()

        log_to_run("Fetching credentials...")
        customer_creds_model = security_service.get_user_credentials(user_id=user_id, db_session=db_session)
        if not customer_creds_model:
            raise ValueError(f"Could not find or access credentials for user {user_id}.")
        customer_creds = customer_creds_model.model_dump()

        netra_creds = {
            "host": settings.CLICKHOUSE_HOST,
            "port": settings.CLICKHOUSE_PORT,
            "user": settings.CLICKHOUSE_USER,
            "password": settings.CLICKHOUSE_PASSWORD,
            "database": settings.CLICKHOUSE_DB
        }
        log_to_run("Credentials fetched successfully.")

        log_to_run("Starting data copy...")
        with DataCopier(source_creds=customer_creds, dest_creds=netra_creds, customer_id=str(user_id)) as copier:
            source_table_name = run.config.get('source_table', 'logs') 
            raw_dest_db, raw_dest_table = copier.copy_data(source_table_name=source_table_name)
        log_to_run(f"Data copied to {raw_dest_db}.{raw_dest_table}.")
        
        log_to_run("Starting data enrichment...")
        with DataEnricher(netra_creds=netra_creds, customer_id=str(user_id)) as enricher:
            enriched_db, enriched_table = enricher.enrich_data(source_db=raw_dest_db, source_table=raw_dest_table)
        log_to_run(f"Data enriched into {enriched_db}.{enriched_table}.")

        log_to_run("Starting pattern analysis...")
        analysis_runner = AnalysisRunner(netra_creds=netra_creds, db_session=db_session)
        analysis_results = analysis_runner.run_analysis(database=enriched_db, table=enriched_table)
        
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
        if run:
            run.completed_at = datetime.utcnow()
            db_session.commit()
        db_session.close()
