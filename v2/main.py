# /main.py
import os
import logging
from dotenv import load_dotenv
from services.credential_manager import get_credentials
from services.data.data_copier import DataCopier
from services.data.data_enricher import DataEnricher # Import the new service
from services.analysis_runner import AnalysisRunner

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# --- Environment & Customer Configuration ---
CUSTOMER_ID = 'customer_abc'
CUSTOMER_CLICKHOUSE_SECRET_NAME = os.getenv('CUSTOMER_CLICKHOUSE_SECRET_NAME', 'customer_abc_ch_creds')
NETRA_CLICKHOUSE_SECRET_NAME = os.getenv('NETRA_CLICKHOUSE_SECRET_NAME', 'netra_ch_creds')

def main():
    """
    Orchestrates the entire workflow:
    1. Fetches credentials.
    2. Copies data from the customer's source to a raw table in Netra's ClickHouse.
    3. Enriches the raw data into a new, analysis-ready table.
    4. Runs the workload pattern analysis on the enriched data.
    """
    logging.info("Starting Netra Log Ingest and Analysis Pipeline...")

    try:
        # 1. Access credentials
        logging.info(f"Fetching credentials for customer: {CUSTOMER_ID}")
        
        customer_creds = get_credentials(CUSTOMER_CLICKHOUSE_SECRET_NAME)
        netra_creds = get_credentials(NETRA_CLICKHOUSE_SECRET_NAME)
        logging.info("Successfully fetched credentials.")

        # 2. Make a copy of the data for analysis
        copier = DataCopier(source_creds=customer_creds, dest_creds=netra_creds, customer_id=CUSTOMER_ID)
        source_table_name = 'logs' 
        raw_dest_db, raw_dest_table = copier.copy_data(source_table_name=source_table_name)
        logging.info(f"Raw data copy complete. Stored in: `{raw_dest_db}`.`{raw_dest_table}`")
        
        # 3. Enrich the newly copied data
        enricher = DataEnricher(netra_creds=netra_creds, customer_id=CUSTOMER_ID)
        enriched_db, enriched_table = enricher.enrich_data(source_db=raw_dest_db, source_table=raw_dest_table)
        logging.info(f"Data enrichment complete. Analysis-ready data is in: `{enriched_db}`.`{enriched_table}`")

        # 4. Run workload pattern recognition on the enriched data
        logging.info("Starting workload pattern recognition analysis...")
        analysis_runner = AnalysisRunner(netra_creds=netra_creds)
        analysis_results = analysis_runner.run_analysis(database=enriched_db, table=enriched_table)
        
        if analysis_results:
            logging.info("Analysis successfully completed!")
            print("\n--- Analysis Summary ---")
            print(f"Run ID: {analysis_results['run_id']}")
            print(f"Total Patterns Discovered: {len(analysis_results['discovered_patterns'])}")
            print(f"Projected Monthly Savings: ${analysis_results['cost_comparison']['projected_monthly_savings']:.2f} ({analysis_results['cost_comparison']['delta_percent']:.2f}%)")
            print("--- End of Summary ---\n")
            
            output_filename = f"analysis_results_{CUSTOMER_ID}.json"
            with open(output_filename, 'w') as f:
                import json
                json.dump(analysis_results, f, indent=4)
            logging.info(f"Detailed analysis results saved to {output_filename}")

    except Exception as e:
        logging.error(f"An error occurred in the main pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    main()
