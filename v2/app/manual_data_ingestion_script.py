import time
from config  import settings
from db.clickhouse import ClickHouseClient
from data.synthetic.synthetic_data_v1 import SyntheticDataV1

def run_ingestion():
    """
    A standalone script to generate synthetic customer data and ingest it
    into a ClickHouse database.

    This script leverages the existing configuration and modules from the Netra V2
    application to perform the following steps:
    1. Loads database credentials from the .env file.
    2. Connects to the ClickHouse database.
    3. Ensures the 'customers' table exists, creating it if necessary.
    4. Generates synthetic customer data in batches.
    5. Inserts each batch into the 'customers' table.
    6. Prints progress and timing information.
    """
    # --- Configuration ---
    TOTAL_RECORDS = 1_000_000
    BATCH_SIZE = 10_000  # Process records in chunks

    print("Starting data ingestion process...")

    try:
        # --- Step 1: Load Settings and Initialize Services ---
        settings = get_settings()
        db = ClickHouseDatabase(settings)
        synthetic_data_generator = SyntheticDataV1()
        
        print(f"Successfully connected to ClickHouse at {settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_PORT}")

        # --- Step 2: Ensure the 'customers' table exists ---
        print("Ensuring 'customers' table exists...")
        db.create_table()
        print("'customers' table is ready.")

        # --- Step 3: Generate and Insert Data in Batches ---
        start_time = time.time()
        total_inserted = 0

        for i in range(0, TOTAL_RECORDS, BATCH_SIZE):
            batch_start_time = time.time()
            num_to_generate = min(BATCH_SIZE, TOTAL_RECORDS - i)
            
            print(f"Generating batch {i//BATCH_SIZE + 1}: {num_to_generate} records...")
            
            # Generate a batch of records
            records = synthetic_data_generator.generate_records(num_records=num_to_generate)
            
            if not records:
                print("No records generated, stopping.")
                break

            # Insert the batch into the database
            db.insert_data('customers', records)
            total_inserted += len(records)
            
            batch_end_time = time.time()
            print(f"  -> Inserted batch in {batch_end_time - batch_start_time:.2f} seconds. "
                  f"Total inserted: {total_inserted}/{TOTAL_RECORDS}")

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
