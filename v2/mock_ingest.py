import json
import time
from app.config import settings 
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import LLM_EVENTS_TABLE_SCHEMA

def _flatten_json_first_level(nested_json, sep='_'):
    """
    Flattens the first level of a nested dictionary.
    
    This function iterates through a dictionary and unnests any sub-dictionaries
    by one level, combining their keys. It's designed to prepare a complex
    JSON object for ingestion into a flat table structure where top-level
    JSON keys correspond to columns.
    
    Example:
        Input: {'event': {'id': 1}, 'details': {'user': 'test'}}
        Output: {'event_id': 1, 'details_user': 'test'}

    Unlike the previous version, this function does not recurse and does not
    have special handling for lists of dictionaries, as the new schema's
    JSON column type can handle them directly.
    """
    items = {}
    if not isinstance(nested_json, dict):
        return {}

    for k, v in nested_json.items():
        if isinstance(v, dict):
            # If the value is a dictionary, iterate its items
            for sub_k, sub_v in v.items():
                # Create a new key by joining the parent and child keys
                items[f"{k}{sep}{sub_k}"] = sub_v
        else:
            # If the value is not a dictionary (e.g., string, int, list),
            # keep it as is. This is crucial for inserting into JSON columns.
            items[k] = v
            
    return items


def run_ingestion():
    JSON_FILE_PATH = "generated_logs.json"

    print("Starting data ingestion process from local file...")

    with get_clickhouse_client() as client:
        
        client.command(LLM_EVENTS_TABLE_SCHEMA)
        start_time = time.time()
        
        with open(JSON_FILE_PATH, 'r') as f:
            records = json.load(f)

        if not records or not isinstance(records, list):
            print("No records found or file format is incorrect. Nothing to insert.")
            return

        flattened_records = [_flatten_json_first_level(record[0]) for record in records]

        column_names = set()
        for record in flattened_records:
            column_names.update(record.keys())
        
        print(f"Discovered column names: {sorted(list(column_names))}")

        client.insert_data('JSON_HYBRID_EVENTS', flattened_records, column_names=list(column_names))
        total_inserted = len(flattened_records)
        
        end_time = time.time()
        print("\n--------------------------------------------------")
        print("Data ingestion completed successfully!")
        print(f"Total records inserted: {total_inserted}")
        print(f"Total time taken: {end_time - start_time:.2f} seconds")
        print("--------------------------------------------------")

if __name__ == "__main__":

    run_ingestion()

