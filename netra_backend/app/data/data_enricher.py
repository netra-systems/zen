# app/data/data_enricher.py
import logging
from typing import Any, Dict, Optional, Tuple

from netra_backend.app.db.clickhouse import get_clickhouse_client

from netra_backend.app.config import get_config
settings = get_config()


class DataEnricher:
    """
    Transforms raw, copied customer data into the structured format required by the analysis engine.
    """
    def __init__(self, customer_id: str) -> None:
        self.netra_creds = settings.clickhouse_native.model_dump()
        self.customer_id = customer_id.replace('-', '_') # Sanitize
        self.client = Client(**self.netra_creds)
        logging.info("DataEnricher initialized.")

    def __enter__(self) -> 'DataEnricher':
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        self.client.disconnect()
        logging.info("DataEnricher client disconnected.")

    def _get_enriched_table_columns(self) -> str:
        """Define the column structure for enriched table."""
        columns = [
            "`event_metadata` String",
            "`trace_context` String",
            "`request` String",
            "`performance` String",
            "`finops` String",
            "`response` String",
            "`workloadName` String",
            "`enriched_metrics` Nullable(String)",
            "`embedding` Nullable(String)"
        ]
        return ",\n            ".join(columns)

    def _get_enriched_table_schema(self, dest_db: str, enriched_table_name: str) -> str:
        """Defines the schema for the enriched table. Columns match `UnifiedLogEntry`."""
        # Storing nested data as JSON strings (ClickHouse String type) is flexible.
        columns = self._get_enriched_table_columns()
        return f"""
        CREATE TABLE IF NOT EXISTS `{dest_db}`.`{enriched_table_name}`
        ({columns}
        )
        ENGINE = MergeTree()
        ORDER BY (workloadName)
        """

    def _setup_enrichment_target(self, source_table: str) -> Tuple[str, str]:
        """Setup target database and table names for enrichment."""
        enriched_table_name = f"{source_table}_enriched"
        dest_db = self.netra_creds.get('database', 'netra')
        logging.info(f"Starting enrichment process. Target table: `{dest_db}`.`{enriched_table_name}`")
        return dest_db, enriched_table_name

    def _prepare_enriched_table(self, dest_db: str, enriched_table_name: str) -> None:
        """Drop existing table and create new empty enriched table."""
        self._drop_existing_enriched_table(dest_db, enriched_table_name)
        self._create_enriched_table(dest_db, enriched_table_name)

    def _drop_existing_enriched_table(self, dest_db: str, table_name: str) -> None:
        """Drop existing enriched table if it exists."""
        self.client.execute(f"DROP TABLE IF EXISTS `{dest_db}`.`{table_name}`")
        logging.info(f"Dropped existing table `{table_name}` if it existed.")

    def _create_enriched_table(self, dest_db: str, table_name: str) -> None:
        """Create new enriched table with schema."""
        create_schema_query = self._get_enriched_table_schema(dest_db, table_name)
        self.client.execute(create_schema_query)
        logging.info(f"Created new empty table `{table_name}` with target schemas.")

    def _get_transformation_select_columns(self) -> str:
        """Define the SELECT column transformations for enrichment query."""
        transformations = self._build_transformation_list()
        return ",\n".join(transformations)

    def _build_transformation_list(self) -> list[str]:
        """Build list of transformation columns."""
        return [
            self._get_event_metadata_transformation(),
            self._get_trace_context_transformation(),
            self._get_request_data_transformation(),
            self._get_performance_data_transformation(),
            self._get_remaining_transformations()
        ]
        
    def _get_event_metadata_transformation(self) -> str:
        """Get event metadata transformation."""
        return "toJSONString(map('log_schema_version', '23.4.0', 'event_id', generateUUIDv4(), 'timestamp_utc', toUnixTimestamp(now()))) as event_metadata"
        
    def _get_trace_context_transformation(self) -> str:
        """Get trace context transformation."""
        return "toJSONString(map('trace_id', trace_id, 'span_id', span_id, 'parent_span_id', parent_span_id)) as trace_context"
        
    def _get_request_data_transformation(self) -> str:
        """Get request data transformation."""
        return """toJSONString(map(
                'model', toJSONString(map('provider', model_provider, 'family', model_family, 'name', model_name)),
                'prompt_text', prompt,
                'user_goal', user_goal
            )) as request"""
            
    def _get_performance_data_transformation(self) -> str:
        """Get performance data transformation."""
        return "toJSONString(map('latency_ms', toJSONString(map('total_e2e_ms', total_latency_ms, 'time_to_first_token_ms', ttft_ms)))) as performance"
        
    def _get_remaining_transformations(self) -> str:
        """Get remaining data transformations."""
        return """toJSONString(map('total_cost_usd', cost_usd)) as finops,
            toJSONString(map('usage', toJSONString(map('prompt_tokens', prompt_tokens, 'completion_tokens', completion_tokens, 'total_tokens', prompt_tokens + completion_tokens)))) as response,
            workload_name as workloadName,
            NULL as enriched_metrics,
            NULL as embedding"""

    def _build_transformation_query(self, source_db: str, source_table: str, dest_db: str, enriched_table_name: str) -> str:
        """Build the core transformation query for data enrichment."""
        # This core transformation logic assumes a flat source table and builds the
        # nested JSON structures required by the analysis engine's UnifiedLogEntry model.
        # This MUST be adapted based on the customer's actual source table columns.
        select_columns = self._get_transformation_select_columns()
        return self._format_insert_query(dest_db, enriched_table_name, select_columns, source_db, source_table)

    def _format_insert_query(self, dest_db: str, enriched_table_name: str, select_columns: str, source_db: str, source_table: str) -> str:
        """Format the INSERT query with proper structure."""
        return f"""
        INSERT INTO `{dest_db}`.`{enriched_table_name}`
        SELECT{select_columns}
        FROM `{source_db}`.`{source_table}`
        """

    def _execute_transformation(self, transformation_query: str, dest_db: str, enriched_table_name: str) -> None:
        """Execute transformation query with error handling."""
        try:
            self._run_transformation_query(transformation_query, enriched_table_name)
        except Exception as e:
            self._handle_transformation_error(e, dest_db, enriched_table_name)

    def _run_transformation_query(self, query: str, table_name: str) -> None:
        """Run the transformation query and log success."""
        logging.info("Executing transformation query to populate the enriched table...")
        self.client.execute(query)
        logging.info(f"Successfully enriched data and inserted into `{table_name}`.")

    def _handle_transformation_error(self, e: Exception, dest_db: str, enriched_table_name: str) -> None:
        """Handle transformation errors with cleanup."""
        logging.error(f"Failed during data enrichment transformation: {e}", exc_info=True)
        self.client.execute(f"DROP TABLE IF EXISTS `{dest_db}`.`{enriched_table_name}`")
        raise

    def enrich_data(self, source_db: str, source_table: str) -> Tuple[str, str]:
        """Creates a new, enriched table from the raw source data."""
        dest_db, enriched_table_name = self._setup_enrichment_target(source_table)
        self._prepare_enriched_table(dest_db, enriched_table_name)
        self._execute_enrichment_workflow(source_db, source_table, dest_db, enriched_table_name)
        return dest_db, enriched_table_name

    def _execute_enrichment_workflow(self, source_db: str, source_table: str, dest_db: str, enriched_table_name: str) -> None:
        """Execute the enrichment workflow."""
        transformation_query = self._build_transformation_query(source_db, source_table, dest_db, enriched_table_name)
        self._execute_transformation(transformation_query, dest_db, enriched_table_name)
