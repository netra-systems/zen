# Claude Metrics Tracking System

## Overview
Automatic metrics tracking for all Claude CLI usage, saving to CloudSQL staging database.

## ✅ Current Status - WORKING
- **Database**: CloudSQL on port 5434 (staging)
- **Metrics**: Correctly tracking tokens, costs, and cache usage
- **Integration**: Transparent wrapper via PATH precedence

## Fixed Issues
1. ✅ **CloudSQL Connection** - Now correctly uses port 5434 instead of local 5433
2. ✅ **Metric Calculations** - Fixed negative tokens and >100% cache rates
3. ✅ **Command Base** - Always "claude" instead of parsing first word
4. ✅ **Cache Metrics** - Properly tracks cache_read and cache_creation tokens

## Database Schema
```sql
-- command_executions table fields:
- id: UUID
- timestamp: When command was run
- command_raw: Full command with arguments
- command_base: Always "claude"
- input_tokens: Tokens sent to model
- output_tokens: Tokens received from model
- cached_tokens: Tokens read from cache (cache_read_input_tokens)
- fresh_tokens: Tokens written to cache (cache_creation_input_tokens)
- total_tokens: input_tokens + output_tokens
- cache_hit_rate: Percentage of context from cache (0-100%)
- cost_usd: Total cost in USD
- cache_savings_usd: Amount saved by cache hits
```

## Setup Instructions

### One-Time Setup
```bash
# Add scripts directory to PATH
bash /Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts/enable-claude-tracking.sh

# Activate (or open new terminal)
source ~/.zshrc
```

### Usage
```bash
# Use Claude normally - metrics tracked automatically
claude
claude -p "Your prompt here"

# View statistics
/Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts/claude-stats
```

## How It Works
1. **PATH Precedence**: `/scripts/claude` wrapper intercepts all claude commands
2. **Pass-Through**: All output passed to user unchanged
3. **Metric Capture**: Parses JSON output for usage data
4. **Database Save**: Direct PostgreSQL connection to CloudSQL
5. **Cost Summary**: Shows session cost after completion

## Files
- `/scripts/claude` - Main wrapper script (Python)
- `/scripts/claude-stats` - View usage statistics (Bash)
- `/scripts/enable-claude-tracking.sh` - Setup script

## Cost Calculation
```python
cost = (
    (input_tokens / 1_000_000) * 3.00 +      # Input: $3/million
    (output_tokens / 1_000_000) * 15.00 +    # Output: $15/million
    (cache_read / 1_000_000) * 0.30 +        # Cache read: $0.30/million
    (cache_creation / 1_000_000) * 3.75      # Cache write: $3.75/million
)
```

## Troubleshooting

### If metrics aren't being saved:
1. Check Cloud SQL proxy is running: `lsof -i:5434`
2. Start if needed: `cloud-sql-proxy --port=5434 netra-staging:us-central1:staging-shared-postgres &`
3. Verify PATH: `which claude` should show `/Users/.../scripts/claude`

### To clean bad data:
```sql
-- Remove entries with invalid metrics
DELETE FROM command_executions
WHERE fresh_tokens < 0
   OR cache_hit_rate > 100
   OR command_base != 'claude';
```

## Notes
- Metrics saved silently - failures don't interrupt Claude usage
- Cache metrics show as 0 for non-cached sessions (normal)
- Fresh tokens represent cache_creation_input_tokens (tokens written to cache)