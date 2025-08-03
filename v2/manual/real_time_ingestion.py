
import time
import logging
from app.config import settings
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import LLM_EVENTS_TABLE_SCHEMA
from app.data.synthetic.synthetic_data_v1 import SyntheticDataV1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_real_time_ingestion():
    """
    A standalone script to continuously generate synthetic customer data and ingest it
    into a ClickHouse database to simulate a real-time data feed.
    """
    BATCH_SIZE = 100
    DELAY_SECONDS = 5

    logger.info("Starting real-time data ingestion process...")

    try:
        with get_clickhouse_client() as client:
            logger.info(f"Successfully connected to ClickHouse at {settings.clickhouse_host}:{settings.clickhouse_port}")

            client.command(LLM_EVENTS_TABLE_SCHEMA)
            logger.info("Ensured 'LLM_EVENTS' table exists.")

            synthetic_data_generator = SyntheticDataV1()

            while True:
                try:
                    batch_start_time = time.time()
                    
                    logger.info(f"Generating batch of {BATCH_SIZE} records...")
                    records = synthetic_data_generator.generate_records(num_records=BATCH_SIZE)
                    
                    if not records:
                        logger.warning("No records generated, sleeping for a while.")
                        time.sleep(DELAY_SECONDS)
                        continue

                    client.insert_data('LLM_EVENTS', records)
                    
                    batch_end_time = time.time()
                    logger.info(f"  -> Inserted batch in {batch_end_time - batch_start_time:.2f} seconds.")
                    
                    time.sleep(DELAY_SECONDS)

                except Exception as e:
                    logger.error(f"An error occurred during the ingestion loop: {e}")
                    time.sleep(DELAY_SECONDS * 2) # Wait longer after an error

    except Exception as e:
        logger.critical(f"A critical error occurred: {e}")
        logger.critical("Please check your .env configuration and ensure the ClickHouse Docker container is running.")

if __name__ == "__main__":
    run_real_time_ingestion()
