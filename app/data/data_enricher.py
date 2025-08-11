# app/data/data_enricher.py
import logging
from typing import Dict, Tuple
from clickhouse_driver import Client
from ..config import settings

class DataEnricher:
    """
    Transforms raw, copied customer data into the structured format required by the analysis engine.
    """
    def __init__(self, customer_id: str):
        self.netra_creds = settings.clickhouse_native.model_dump()
        self.customer_id = customer_id.replace('-', '_') # Sanitize
        self.client = Client(**self.netra_creds)
        logging.info("DataEnricher initialized.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.disconnect()
        logging.info("DataEnricher client disconnected.")

    def _get_enriched_table_schema(self, dest_db: str, enriched_table_name: str) -> str:
        """
        Defines the schema for the enriched table. Columns match `UnifiedLogEntry`.
        """
        # Storing nested data as JSON strings (ClickHouse String type) is flexible.
        return f"""
        CREATE TABLE IF NOT EXISTS `{dest_db}`.`{enriched_table_name}`
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
        Creates a new, enriched table from the raw source data.
        """
        enriched_table_name = f"{source_table}_enriched"
        dest_db = self.netra_creds.get('database', 'netra')
        logging.info(f"Starting enrichment process. Target table: `{dest_db}`.`{enriched_table_name}`")

        self.client.execute(f"DROP TABLE IF EXISTS `{dest_db}`.`{enriched_table_name}`")
        logging.info(f"Dropped existing table `{enriched_table_name}` if it existed.")

        create_schema_query = self._get_enriched_table_schema(dest_db, enriched_table_name)
        self.client.execute(create_schema_query)
        logging.info(f"Created new empty table `{enriched_table_name}` with target schemas.")

        # This core transformation logic assumes a flat source table and builds the
        # nested JSON structures required by the analysis engine's UnifiedLogEntry model.
        # This MUST be adapted based on the customer's actual source table columns.
        transformation_query = f"""
        INSERT INTO `{dest_db}`.`{enriched_table_name}`
        SELECT
            toJSONString(map('log_schema_version', '23.4.0', 'event_id', generateUUIDv4(), 'timestamp_utc', toUnixTimestamp(now()))) as event_metadata,
            toJSONString(map('trace_id', trace_id, 'span_id', span_id, 'parent_span_id', parent_span_id)) as trace_context,
            toJSONString(map(
                'model', toJSONString(map('provider', model_provider, 'family', model_family, 'name', model_name)),
                'prompt_text', prompt,
                'user_goal', user_goal
            )) as request,
            toJSONString(map('latency_ms', toJSONString(map('total_e2e_ms', total_latency_ms, 'time_to_first_token_ms', ttft_ms)))) as performance,
            toJSONString(map('total_cost_usd', cost_usd)) as finops,
            toJSONString(map('usage', toJSONString(map('prompt_tokens', prompt_tokens, 'completion_tokens', completion_tokens, 'total_tokens', prompt_tokens + completion_tokens)))) as response,
            workload_name as workloadName,
            NULL as enriched_metrics,
            NULL as embedding
        FROM `{source_db}`.`{source_table}`
        """

        try:
            logging.info("Executing transformation query to populate the enriched table...")
            self.client.execute(transformation_query)
            logging.info(f"Successfully enriched data and inserted into `{enriched_table_name}`.")
        except Exception as e:
            logging.error(f"Failed during data enrichment transformation: {e}", exc_info=True)
            self.client.execute(f"DROP TABLE IF EXISTS `{dest_db}`.`{enriched_table_name}`")
            raise

        return dest_db, enriched_table_name
