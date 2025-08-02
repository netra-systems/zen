import time
import json
from app.config import settings # Assuming get_settings is the correct function
from app.db.clickhouse import get_clickhouse_client # Assuming this is the correct class
from app.db.models_clickhouse import LOGS_TABLE_SCHEMA, LLM_EVENTS_TABLE_SCHEMA
# https://gemini.google.com/u/0/app/1b8b45e460f7556a

def run_ingestion():
    """
    A standalone script to ingest customer data from a local JSON file
    into a ClickHouse database.

    This script performs the following steps:
    1. Loads database credentials from the .env file.
    2. Connects to the ClickHouse database.
    3. Ensures the 'customers' table exists, creating it if necessary.
    4. Reads customer data from 'generated_logs.json'.
    5. Inserts the data into the 'customers' table.
    6. Prints progress and timing information.
    """
    # --- Configuration ---
    JSON_FILE_PATH = "generated_logs.json"

    print("Starting data ingestion process from local file...")

    try:
        # --- Step 1: Load Settings and Initialize DB ---
        client = get_clickhouse_client()
        
        print(f"Successfully connected to ClickHouse at {settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}")

        # --- Step 2: Ensure the 'customers' table exists ---
        print("Ensuring 'customers' table exists...")
        client.command(LLM_EVENTS_TABLE_SCHEMA)
        print("'customers' table is ready.")

        # --- Step 3: Read Data from JSON file ---
        start_time = time.time()
        print(f"Reading records from {JSON_FILE_PATH}...")
        
        try:
            with open(JSON_FILE_PATH, 'r') as f:
                records = json.load(f)
        except FileNotFoundError:
            print(f"Error: The file '{JSON_FILE_PATH}' was not found.")
            print("Please ensure the file exists in the correct directory.")
            return
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{JSON_FILE_PATH}'.")
            print("Please ensure the file contains valid JSON.")
            return

        if not records or not isinstance(records, list):
            print("No records found or file format is incorrect. Nothing to insert.")
            return

        print(f"Successfully read {len(records)} records from the file.")

        # --- Step 4: Insert Data into Database ---
        print("Inserting records into the 'netra_llm_events' table...")
        client.insert_data('netra_llm_events', records)
        total_inserted = len(records)
        
        end_time = time.time()
        print("\n--------------------------------------------------")
        print("Data ingestion completed successfully!")
        print(f"Total records inserted: {total_inserted}")
        print(f"Total time taken: {end_time - start_time:.2f} seconds")
        print("--------------------------------------------------")

    except Exception as e:
        print(f"\nAn error occurred during the ingestion process: {e}")
        print("Please check your .env configuration and ensure the ClickHouse Docker container is running.")

if __name__ == "__main__":
    run_ingestion()
