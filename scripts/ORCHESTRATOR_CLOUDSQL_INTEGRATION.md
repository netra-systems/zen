# Claude Instance Orchestrator - CloudSQL Integration

## Overview
The main `claude-instance-orchestrator.py` now includes optional CloudSQL metrics tracking functionality, previously available only in the separate `claude-instance-orchestrator-netra.py` script.

## Changes Made
1. **Integrated NetraOptimizer support** - Optional import of NetraOptimizer library
2. **CloudSQL database saving** - Metrics automatically saved when `--use-cloud-sql` flag is used
3. **Unified codebase** - Removed redundant `claude-instance-orchestrator-netra.py`

## Usage

### Without CloudSQL (default behavior - unchanged)
```bash
python scripts/claude-instance-orchestrator.py --config config.json
```

### With CloudSQL metrics tracking
```bash
# Ensure Cloud SQL proxy is running
cloud-sql-proxy --port=5434 netra-staging:us-central1:staging-shared-postgres &

# Run orchestrator with CloudSQL
python scripts/claude-instance-orchestrator.py --config config.json --use-cloud-sql
```

## CloudSQL Integration Features
When `--use-cloud-sql` is enabled:

1. **Automatic environment configuration**
   - Sets CloudSQL connection parameters (port 5434)
   - Configures staging environment credentials

2. **Batch tracking**
   - Generates unique batch ID for each orchestration run
   - All instances in the run share the same batch ID

3. **Metrics saved to database**
   - Command execution details
   - Token usage (input, output, cached)
   - Cost calculations
   - Execution timing
   - Error messages if any

4. **Database schema compatibility**
   - `command_base`: Always set to 'claude'
   - `cached_tokens`: Combined cache_read + cache_creation
   - `fresh_tokens`: Set to 0 (parsing limitation)
   - `cost_usd`: Calculated using Claude 3.5 Sonnet pricing

## Viewing Metrics

After running with `--use-cloud-sql`, metrics can be viewed:

```bash
# View specific batch
psql -h localhost -p 5434 -U postgres -d netra_optimizer -c \
  "SELECT * FROM command_executions WHERE batch_id = 'YOUR-BATCH-ID';"

# View today's executions
psql -h localhost -p 5434 -U postgres -d netra_optimizer -c \
  "SELECT * FROM command_executions WHERE DATE(timestamp) = CURRENT_DATE;"
```

## Requirements

### Optional (for CloudSQL features)
- NetraOptimizer library (`pip install netraoptimizer`)
- Cloud SQL proxy running on port 5434
- Access to CloudSQL staging database

### Core functionality
- No additional requirements
- Works exactly as before when `--use-cloud-sql` is not specified

## Migration Notes

If you were using `claude-instance-orchestrator-netra.py`:
1. Switch to using `claude-instance-orchestrator.py` with `--use-cloud-sql` flag
2. All functionality is preserved
3. The netra script has been removed to avoid duplication

## Benefits of Integration
1. **Single codebase** - Easier maintenance
2. **Optional functionality** - CloudSQL only when needed
3. **Backward compatibility** - Existing workflows unchanged
4. **Consistent behavior** - Same orchestration logic for all users