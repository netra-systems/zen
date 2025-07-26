# /services/data_enricher.py
import logging
from typing import Dict, Tuple
from clickhouse_driver import Client

class DataEnricher:
    """
    Transforms raw, copied customer data into the structured format required by the analysis engine.
    This class assumes a hypothetical "flat" source schema and builds the required nested JSON objects.
    """
    def __init__(self, netra_creds: Dict, customer_id: str):
        self.netra_creds = netra_creds
        self.customer_id = customer_id
        self.client = Client(**netra_creds)
        logging.info("DataEnricher initialized.")

    def _get_enriched_table_schema(self, dest_db: str, enriched_table_name: str) -> str:
        """
        Defines the schema for the enriched table. The columns match the fields
        in the `UnifiedLogEntry` Pydantic model from the analysis engine.
        """
        # Note: Storing nested data as JSON strings is a common and flexible approach.
        # ClickHouse's Map and Nested types could also be used for more advanced query capabilities.
        return f"""
        CREATE TABLE {dest_db}.{enriched_table_name}
        (
            `event_metadata` String,
            `trace_context` String,
            `request` String,
            `performance` String,
            `finops` String,
            `response` String,
            `workloadName` String,
            `enriched_metrics` Nullable(String),
            `embedding` Nullable(String)
        )
        ENGINE = MergeTree()
        ORDER BY (workloadName)
        """

    def enrich_data(self, source_db: str, source_table: str) -> Tuple[str, str]:
        """
        Creates a new, enriched table from the raw source data using a single,
        powerful ClickHouse query to perform the transformation.

        Args:
            source_db: The database containing the raw copied data.
            source_table: The table containing the raw copied data.

        Returns:
            A tuple with the database and name of the newly created enriched table.
        """
        enriched_table_name = f"{source_table}_enriched"
        logging.info(f"Starting enrichment process. Target table: `{source_db}`.`{enriched_table_name}`")

        # 1. Drop the enriched table if it already exists to ensure a fresh run
        self.client.execute(f"DROP TABLE IF EXISTS {source_db}.{enriched_table_name}")
        logging.info(f"Dropped existing table `{enriched_table_name}` if it existed.")

        # 2. Create the new, empty enriched table with the correct schema
        create_schema_query = self._get_enriched_table_schema(source_db, enriched_table_name)
        self.client.execute(create_schema_query)
        logging.info(f"Created new empty table `{enriched_table_name}` with target schema.")

        # 3. Build and execute the main transformation and insertion query.
        #    This query reads from the flat source table and uses ClickHouse functions
        #    to construct the JSON objects needed by the analysis engine.
        #    *** THIS IS THE CORE TRANSFORMATION LOGIC ***
        #    It needs to be adapted based on the actual columns in the customer's source table.
        transformation_query = f"""
        INSERT INTO {source_db}.{enriched_table_name}
        SELECT
            -- event_metadata (building a JSON object as a string)
            toJSONString(map('log_schema_version', '23.4.0', 'event_id', generateUUIDv4(), 'timestamp_utc', toUnixTimestamp(now()))),

            -- trace_context
            toJSONString(map('trace_id', trace_id, 'span_id', span_id, 'parent_span_id', parent_span_id)),

            -- request
            toJSONString(map(
                'model', toJSONString(map('provider', model_provider, 'family', model_family, 'name', model_name)),
                'prompt_text', prompt,
                'user_goal', user_goal
            )),

            -- performance
            toJSONString(map('latency_ms', toJSONString(map('total_e2e_ms', total_latency_ms, 'time_to_first_token_ms', ttft_ms)))),

            -- finops
            toJSONString(map('total_cost_usd', cost_usd)),

            -- response
            toJSONString(map('usage', toJSONString(map('prompt_tokens', prompt_tokens, 'completion_tokens', completion_tokens, 'total_tokens', prompt_tokens + completion_tokens)))),
            
            -- workloadName (passed through)
            workload_name,

            -- enriched_metrics and embedding (initially null)
            NULL,
            NULL
        FROM {source_db}.{source_table}
        """

        try:
            logging.info("Executing transformation query to populate the enriched table...")
            self.client.execute(transformation_query)
            # You can get progress/summary from the client if needed
            logging.info(f"Successfully enriched data and inserted into `{enriched_table_name}`.")
        except Exception as e:
            logging.error(f"Failed during data enrichment transformation: {e}", exc_info=True)
            # Depending on requirements, you might want to clean up the partially created table
            self.client.execute(f"DROP TABLE IF EXISTS {source_db}.{enriched_table_name}")
            raise

        return source_db, enriched_table_name
