import json
import time
from app.config import settings 
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import LLM_EVENTS_TABLE_SCHEMA

def _flatten_json(nested_json, parent_key='', sep='_'):
    """
    Flattens a nested dictionary.
    If the input `nested_json` is not a dictionary, it returns an empty dictionary
    to prevent errors and handle malformed records gracefully.
    """
    items = {}

    # FIX: Check if the input is a dictionary. The function is designed to flatten
    # a dictionary, so if it receives a list or another type (e.g., from a
    # malformed JSON record), we prevent a crash by returning early.
    if not isinstance(nested_json, dict):
        return {}

    for k, v in nested_json.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.update(_flatten_json(v, new_key, sep=sep))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            # This part handles lists of dictionaries by creating separate columns
            # for each key in the nested dictionaries, which is useful for columnar DBs.
            nested_keys = v[0].keys()
            for nested_key in nested_keys:
                column_name = new_key + '_' + nested_key
                items[column_name] = [item.get(nested_key) for item in v]
        else:
            items[new_key] = v
    return items


def run_ingestion():
    JSON_FILE_PATH = "generated_logs.json"

    print("Starting data ingestion process from local file...")

    with get_clickhouse_client() as client:
        
        print(f"Successfully connected to ClickHouse at {client.database} : {settings.clickhouse_host}:{settings.clickhouse_port}")

        client.command(LLM_EVENTS_TABLE_SCHEMA)

        start_time = time.time()
        print(f"Reading records from {JSON_FILE_PATH}...")
        
        with open(JSON_FILE_PATH, 'r') as f:
            records = json.load(f)

        if not records or not isinstance(records, list):
            print("No records found or file format is incorrect. Nothing to insert.")
            return

        print(f"Successfully read {len(records)} records from the file.")
        print("Flattening records for ingestion...")

        flattened_records = [_flatten_json(record) for record in records]

        print("Inserting records into the 'netra_llm_events' table...")
        client.insert('netra_llm_events', flattened_records)
        total_inserted = len(flattened_records)
        
        end_time = time.time()
        print("\n--------------------------------------------------")
        print("Data ingestion completed successfully!")
        print(f"Total records inserted: {total_inserted}")
        print(f"Total time taken: {end_time - start_time:.2f} seconds")
        print("--------------------------------------------------")

if __name__ == "__main__":

    run_ingestion()

