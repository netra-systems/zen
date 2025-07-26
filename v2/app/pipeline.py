# /v2/pipeline.py
import os
import logging
import json
from dotenv import load_dotenv

# Note the relative imports for when this is called from the API
from .services.security_service import security_service
from .data.data_copier import DataCopier
from .data.data_enricher import DataEnricher
from .services.analysis_runner import AnalysisRunner
from . import database as db
from .dependencies import get_db

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# This is the main end-to-end workflow
def run_full_analysis_pipeline(run_id: str, user_id: str):
    """
    Orchestrates the entire analysis workflow for a given user.
    This function is designed to be run in the background and update the
    AnalysisRun record in the database.

    Args:
        run_id: The ID of the AnalysisRun record to update.
        user_id: The ID of the user initiating the run.
    """
    logging.info(f"Starting Netra Log Ingest and Analysis Pipeline for run_id: {run_id}, user_id: {user_id}")
    
    db_session = next(get_db())
    run = db_session.query(db.AnalysisRun).filter(db.AnalysisRun.id == run_id).first()

    try:
        if not run:
            logging.error(f"AnalysisRun with id {run_id} not found. Aborting pipeline.")
            return

        # 1. Access credentials using the security service
        logging.info(f"Fetching credentials for user: {user_id}")
        run.execution_log = (run.execution_log or "") + "Fetching credentials...\n"
        db_session.commit()
        
        customer_creds_model = security_service.get_user_credentials(user_id)
        if not customer_creds_model:
            raise ValueError(f"Could not find or access credentials for user {user_id}.")
        customer_creds = customer_creds_model.dict()

        netra_creds_model = security_service.get_netra_credentials()
        if not netra_creds_model:
            raise ValueError("Could not find or access Netra's internal credentials.")
        netra_creds = netra_creds_model.dict()
        
        logging.info("Successfully fetched all required credentials.")
        run.execution_log += "Credentials fetched successfully.\n"
        db_session.commit()

        # 2. Make a copy of the data for analysis
        run.execution_log += "Starting data copy...\n"
        db_session.commit()
        copier = DataCopier(source_creds=customer_creds, dest_creds=netra_creds, customer_id=user_id)
        source_table_name = run.config.get('source_table', 'logs') 
        raw_dest_db, raw_dest_table = copier.copy_data(source_table_name=source_table_name)
        logging.info(f"Raw data copy complete. Stored in: `{raw_dest_db}`.`{raw_dest_table}`")
        run.execution_log += f"Data copied to {raw_dest_db}.{raw_dest_table}.\n"
        db_session.commit()
        
        # 3. Enrich the newly copied data
        run.execution_log += "Starting data enrichment...\n"
        db_session.commit()
        enricher = DataEnricher(netra_creds=netra_creds, customer_id=user_id)
        enriched_db, enriched_table = enricher.enrich_data(source_db=raw_dest_db, source_table=raw_dest_table)
        logging.info(f"Data enrichment complete. Analysis-ready data is in: `{enriched_db}`.`{enriched_table}`")
        run.execution_log += f"Data enriched into {enriched_db}.{enriched_table}.\n"
        db_session.commit()

        # 4. Run workload pattern recognition on the enriched data
        logging.info("Starting workload pattern recognition analysis...")
        run.execution_log += "Starting pattern analysis...\n"
        db_session.commit()
        analysis_runner = AnalysisRunner(netra_creds=netra_creds)
        analysis_results = analysis_runner.run_analysis(database=enriched_db, table=enriched_table)
        
        if analysis_results:
            logging.info("Analysis successfully completed!")
            run.status = 'completed'
            run.result_summary = analysis_results.get('cost_comparison')
            run.result_details = {
                "discovered_patterns": analysis_results.get('discovered_patterns'),
                "learned_policies": analysis_results.get('learned_policies')
            }
            run.execution_log += "Analysis completed successfully."
            db_session.commit()
            
            output_filename = f"analysis_results_{user_id}_{run_id}.json"
            with open(output_filename, 'w') as f:
                # Use a custom encoder for Pydantic models if they are in results
                json.dump(analysis_results, f, indent=4, default=str)
            logging.info(f"Detailed analysis results saved to {output_filename}")

    except Exception as e:
        logging.error(f"An error occurred in the main pipeline for run {run_id}: {e}", exc_info=True)
        if run:
            run.status = 'failed'
            run.execution_log = (run.execution_log or "") + f"\nERROR: {e}"
            db_session.commit()
    finally:
        db_session.close()

