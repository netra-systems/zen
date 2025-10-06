-- Create or replace view for flattened instance metrics.
CREATE OR REPLACE VIEW `${project_id}.zen_community_curated.fact_instance_usage` AS
SELECT
  trace_id,
  span_id,
  TIMESTAMP_MILLIS(CAST(SAFE_CAST(JSON_VALUE(span.attributes, '$.startTime') AS INT64) / 1e6 AS INT64)) AS start_time,
  TIMESTAMP_MILLIS(CAST(SAFE_CAST(JSON_VALUE(span.attributes, '$.endTime') AS INT64) / 1e6 AS INT64)) AS end_time,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.batch.id') AS STRING) AS batch_id,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.instance.name') AS STRING) AS instance_name,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.instance.command_type') AS STRING) AS command_type,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.instance.command') AS STRING) AS command,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.instance.status') AS STRING) AS status,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.instance.duration_ms') AS INT64) AS duration_ms,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.workspace.hash') AS STRING) AS workspace_hash,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.session.hash') AS STRING) AS session_hash,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.tokens.total') AS INT64) AS tokens_total,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.tokens.input') AS INT64) AS tokens_input,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.tokens.output') AS INT64) AS tokens_output,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.tokens.cache.read') AS INT64) AS tokens_cache_read,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.tokens.cache.creation') AS INT64) AS tokens_cache_creation,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.tokens.tools_total') AS INT64) AS tokens_tool_total,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.cost.usd_total') AS NUMERIC) AS cost_total_usd,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.cost.usd_input') AS NUMERIC) AS cost_input_usd,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.cost.usd_output') AS NUMERIC) AS cost_output_usd,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.cost.usd_cache_read') AS NUMERIC) AS cost_cache_read_usd,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.cost.usd_cache_creation') AS NUMERIC) AS cost_cache_creation_usd,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.cost.usd_tools') AS NUMERIC) AS cost_tools_usd,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.tools.unique') AS INT64) AS unique_tools,
  TIMESTAMP_MICROS(CAST(SAFE_CAST(JSON_VALUE(span.attributes, '$.startTime') AS INT64) AS INT64)) AS ingest_timestamp
FROM `${project_id}.zen_community_raw.cloud_trace_export` AS span
WHERE span.name = 'zen.instance';

-- Extract tool usage to a separate exploded view.
CREATE OR REPLACE VIEW `${project_id}.zen_community_curated.fact_tool_usage` AS
SELECT
  trace_id,
  span_id,
  SAFE_CAST(REGEXP_EXTRACT(attr_name, r"zen\\.tools\\.invocations\\.(.*)") AS STRING) AS tool_name,
  SAFE_CAST(JSON_VALUE(span.attributes, CONCAT('$.attributes.', attr_name)) AS INT64) AS invocations,
  SAFE_CAST(JSON_VALUE(span.attributes, CONCAT('$.attributes.zen.tools.tokens.', REGEXP_EXTRACT(attr_name, r"zen\\.tools\\.invocations\\.(.*)"))) AS INT64) AS tokens,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.instance.command_type') AS STRING) AS command_type,
  SAFE_CAST(JSON_VALUE(span.attributes, '$.attributes.zen.instance.command') AS STRING) AS command
FROM `${project_id}.zen_community_raw.cloud_trace_export` AS span,
UNNEST(JSON_EXTRACT_KEYS(JSON_EXTRACT(span.attributes, '$.attributes'))) AS attr_name
WHERE span.name = 'zen.instance'
  AND attr_name LIKE 'zen.tools.invocations.%';

