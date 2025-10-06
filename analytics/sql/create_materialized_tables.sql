-- Aggregate daily cost and token usage by command.
CREATE TABLE IF NOT EXISTS `${project_id}.zen_community_curated.fact_cost_daily`
PARTITION BY DATE(event_timestamp)
AS
SELECT
  DATE(start_time) AS event_date,
  start_time AS event_timestamp,
  command_type,
  COALESCE(command, SHA256(IFNULL(command, ''))) AS command_identifier,
  SUM(tokens_total) AS tokens_total,
  SUM(tokens_input) AS tokens_input,
  SUM(tokens_output) AS tokens_output,
  SUM(tokens_cache_read) AS tokens_cache_read,
  SUM(tokens_cache_creation) AS tokens_cache_creation,
  SUM(tokens_tool_total) AS tokens_tool_total,
  SUM(cost_total_usd) AS cost_total_usd,
  SUM(cost_input_usd) AS cost_input_usd,
  SUM(cost_output_usd) AS cost_output_usd,
  SUM(cost_cache_read_usd) AS cost_cache_read_usd,
  SUM(cost_cache_creation_usd) AS cost_cache_creation_usd,
  SUM(cost_tools_usd) AS cost_tool_usd,
  COUNT(*) AS runs
FROM `${project_id}.zen_community_curated.fact_instance_usage`
GROUP BY event_date, event_timestamp, command_type, command_identifier;

