# Zen Community Analytics Dashboard

This package sets up the BigQuery data model and automation needed to build the
public dashboard for token usage and cost analytics captured by Zen telemetry.

## 1. Data Flow Overview

```
OpenTelemetry spans (zen.instance)
        │
        ├── Cloud Trace → BigQuery sink (raw table)
        │
        └── analytics pipeline (scheduled query / Dataflow / dbt)
                │
                ├── curated.fact_instance_usage
                └── curated.dim_command, dim_tool
                        │
                        └── Looker Studio / Looker dashboards
```

Zen already emits the following attributes per span (`zen/telemetry/manager.py`):

* Token metrics: `zen.tokens.total`, `zen.tokens.input`, `zen.tokens.output`,
  `zen.tokens.cache.read`, `zen.tokens.cache.creation`, `zen.tokens.tools_total`
* Tool metrics: `zen.tools.invocations.<tool>`, `zen.tools.tokens.<tool>`
* Cost metrics: `zen.cost.usd_total`, `zen.cost.usd_input`, `zen.cost.usd_output`,
  `zen.cost.usd_cache_read`, `zen.cost.usd_cache_creation`, `zen.cost.usd_tools`
* Context metadata: `zen.instance.command`, `zen.instance.command_type`,
  `zen.instance.status`, `zen.instance.duration_ms`, `zen.workspace.hash`,
  `zen.session.hash`, `zen.batch.id`

## 2. BigQuery Setup

1. **Create dataset for raw spans.** When configuring the Cloud Trace sink, set
   the destination to a dataset such as `zen_community_raw`.

   ```bash
   bq --location=US mk --dataset zen-telemetry:zen_community_raw
   ```

2. **Create dataset for curated tables.**

   ```bash
   bq --location=US mk --dataset zen-telemetry:zen_community_curated
   ```

3. **Deploy the auto-generated view and materialized tables.**

   ```bash
   bq query --use_legacy_sql=false < analytics/sql/create_curated_views.sql
   bq query --use_legacy_sql=false < analytics/sql/create_materialized_tables.sql
   ```

4. **Schedule refresh.** Use BigQuery scheduled queries (or dbt) to populate the
   materialized tables hourly. Sample schedule is included in
   `analytics/sql/scheduled_refresh.sql`.

## 3. Dashboard Metrics

Use the curated tables/view to power dashboards:

* `curated.fact_instance_usage`: fact table with one row per span, containing
  token and cost breakdowns plus hashed session/workspace identifiers.
* `curated.fact_tool_usage`: exploded table for per-tool metrics.
* `curated.fact_cost_daily`: daily aggregates by command type, command, and
  prompt hash (for privacy).

Visual components to build:

1. **Usage Pattern Overview**
   * Daily/weekly active instances
   * Top commands/prompts (group by `command_type` and `command_hash`)
   * Success vs failure ratio

2. **Token Analytics**
   * Input/output/cache/tool token trends
   * Token heatmap by command × tool
   * Boxplots of token consumption per prompt hash bucket

3. **Cost Analytics**
   * Total vs component costs (stacked area chart)
   * Cost per command and command type
   * Cost efficiency scatter (cost vs duration)

4. **Tool Adoption**
   * Invocations per tool family (`tool_name`) vs total token contribution
   * Tool usage by command type (`command_type`)

## 4. Automation

* `scripts/setup_trace_sink.sh` – helper script to provision the Cloud Trace →
  BigQuery sink and set retention policy.
* `scripts/run_curated_refresh.py` – Python utility that executes the refresh
  queries via the BigQuery API (useful for Cloud Scheduler + Cloud Run/Functions).

### Running the Python refresh manually

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r analytics/requirements.txt
python scripts/run_curated_refresh.py \
    --project zen-telemetry \
    --dataset zen_community_curated \
    --sql analytics/sql/create_materialized_tables.sql
```

## 5. Privacy & Governance

* All session/workspace identifiers are hashed client-side.
* BigQuery tables are partitioned by event date and set to 180-day retention.
* Use row access policies or authorized views if additional segmentation is
  required before the data becomes public.

## 6. Deployment Status (Project: netra-telemetry-public)

✅ **Completed:**
- Datasets created: `zen_community_raw`, `zen_community_curated`
- Raw table: `zen_community_raw.cloud_trace_export`
- Curated views: `fact_instance_usage`, `fact_tool_usage`
- Materialized table: `fact_cost_daily` (partitioned by date)
- BigQuery Data Transfer API: Enabled
- Telemetry configured to export to Cloud Trace

⏸️ **Pending (requires billing):**
- Cloud Trace → BigQuery export configuration
- Scheduled query for daily refresh (see command below)

### Setting up Cloud Trace Export (Requires Billing)

Once billing is enabled, set up continuous export from Cloud Trace to BigQuery:

**Option 1: Cloud Console UI (Recommended)**
1. Go to [Cloud Trace Console](https://console.cloud.google.com/traces/traces?project=netra-telemetry-public)
2. Navigate to "Settings" or "Export"
3. Configure continuous export to BigQuery
4. Select dataset: `zen_community_raw`
5. Table will be auto-created as `cloud_trace_spans`

**Option 2: Use gcloud CLI**
```bash
# Enable the required APIs
gcloud services enable cloudtrace.googleapis.com bigquery.googleapis.com \
  --project=netra-telemetry-public

# Configure export (via Cloud Console - no direct CLI command)
```

**Note:** Cloud Trace export to BigQuery is a managed feature that requires billing. Once configured, traces will automatically flow to BigQuery with minimal latency.

### Manual Refresh (Until Billing Enabled)

```bash
pip install -r analytics/requirements.txt
python scripts/run_curated_refresh.py \
    --project netra-telemetry-public \
    --sql analytics/sql/create_materialized_tables.sql
```

### Enable Scheduled Query (After Billing Enabled)

```bash
bq mk --transfer_config \
  --project_id=netra-telemetry-public \
  --data_source=scheduled_query \
  --display_name="Zen Community Analytics - Daily Refresh" \
  --schedule="every day 00:00" \
  --target_dataset=zen_community_curated \
  --params='{"query":"INSERT INTO `netra-telemetry-public.zen_community_curated.fact_cost_daily` SELECT DATE(start_time) AS event_date, start_time AS event_timestamp, command_type, COALESCE(command, TO_HEX(SHA256(IFNULL(command, '\'\'')))) AS command_identifier, SUM(tokens_total) AS tokens_total, SUM(tokens_input) AS tokens_input, SUM(tokens_output) AS tokens_output, SUM(tokens_cache_read) AS tokens_cache_read, SUM(tokens_cache_creation) AS tokens_cache_creation, SUM(tokens_tool_total) AS tokens_tool_total, SUM(cost_total_usd) AS cost_total_usd, SUM(cost_input_usd) AS cost_input_usd, SUM(cost_output_usd) AS cost_output_usd, SUM(cost_cache_read_usd) AS cost_cache_read_usd, SUM(cost_cache_creation_usd) AS cost_cache_creation_usd, SUM(cost_tools_usd) AS cost_tool_usd, COUNT(*) AS runs FROM `netra-telemetry-public.zen_community_curated.fact_instance_usage` WHERE DATE(start_time) = CURRENT_DATE() - 1 GROUP BY event_date, event_timestamp, command_type, command_identifier"}'
```

## 7. Next Steps

1. ✅ Wire the scheduled refresh job (pending billing activation)
2. Build the Looker Studio dashboard using the curated tables
3. Embed the dashboard into the community portal and document the metrics
4. Monitor query costs and add caching (materialized views) where needed

