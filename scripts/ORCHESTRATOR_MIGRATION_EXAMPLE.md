# Claude Instance Orchestrator - NetraOptimizer Migration Guide

This guide shows exactly how to modify your existing `claude-instance-orchestrator.py` to use NetraOptimizer for automatic metrics tracking.

## Quick Migration (5 minutes)

### Step 1: Add Imports

At the top of your file, add NetraOptimizer imports:

```python
# Existing imports
import asyncio
import json
# ... other imports ...

# ADD THESE LINES:
from uuid import uuid4
from netraoptimizer import NetraOptimizerClient, DatabaseClient
```

### Step 2: Initialize NetraOptimizer in `__init__`

Find your `ClaudeInstanceOrchestrator.__init__` method and add:

```python
def __init__(self, workspace_dir: Path, ...):
    # Your existing init code
    self.workspace_dir = workspace_dir
    self.instances = {}
    self.statuses = {}
    # ... other initialization ...

    # ADD THESE LINES:
    # Initialize NetraOptimizer (use CloudSQL for production)
    # For CloudSQL:
    # db_client = DatabaseClient(use_cloud_sql=True)
    # asyncio.run(db_client.initialize())
    # self.optimizer = NetraOptimizerClient(database_client=db_client)

    # For local development:
    self.optimizer = NetraOptimizerClient()
    self.batch_id = str(uuid4())  # Group all instances in this run
```

### Step 3: Replace `run_instance` Method

Replace your entire subprocess execution with NetraOptimizer. Find your `run_instance` method:

#### BEFORE (200+ lines):
```python
async def run_instance(self, name: str) -> bool:
    """Run a single Claude Code instance asynchronously"""
    config = self.instances[name]
    status = self.statuses[name]

    try:
        # Build command
        cmd = self.build_claude_command(config)

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workspace_dir,
            env=env
        )

        # Complex output streaming logic...
        # Manual token parsing...
        # Error handling...
        # ... 150+ more lines ...

        # Manual parsing
        self._parse_final_output_token_usage(stdout_str, status, config.output_format)

    except Exception as e:
        # Error handling
```

#### AFTER (20 lines):
```python
async def run_instance(self, name: str) -> bool:
    """Run a single Claude Code instance through NetraOptimizer"""
    config = self.instances[name]
    status = self.statuses[name]

    try:
        status.status = "running"
        status.start_time = time.time()

        # Execute through NetraOptimizer - EVERYTHING IS AUTOMATIC!
        result = await self.optimizer.run(
            config.command,
            batch_id=self.batch_id,
            execution_sequence=list(self.instances.keys()).index(name),
            workspace_context={
                'instance_name': name,
                'workspace_dir': str(self.workspace_dir),
                'description': config.description
            },
            cwd=str(self.workspace_dir)
        )

        # Update status from result
        status.end_time = time.time()
        status.status = result['status']
        status.total_tokens = result['tokens']['total']
        status.input_tokens = result['tokens']['input']
        status.output_tokens = result['tokens']['output']
        status.cached_tokens = result['tokens']['cached']
        status.cache_hit_rate = result['tokens']['cache_hit_rate']
        status.cost_usd = result['cost_usd']
        status.tool_calls = result.get('tool_calls', 0)

        logger.info(f"Instance {name} {result['status']} - "
                   f"Tokens: {status.total_tokens:,} "
                   f"Cost: ${status.cost_usd:.4f}")

        return result['status'] == 'completed'

    except Exception as e:
        status.status = "failed"
        status.error = str(e)
        return False
```

### Step 4: Remove These Methods (No Longer Needed)

You can DELETE these methods - NetraOptimizer handles everything:

```python
# DELETE ALL OF THESE:
def _parse_final_output_token_usage(...)  # Not needed
def _parse_json_token_usage(...)          # Not needed
def _parse_regex_token_usage(...)         # Not needed
def _parse_token_usage(...)               # Not needed
def _try_parse_json_token_usage(...)      # Not needed
def _extract_usage_stats(...)             # Not needed
async def _stream_output(...)             # Not needed
async def _stream_output_parallel(...)    # Not needed
```

### Step 5: Update Status Display

Update your `_display_status` or final report to show NetraOptimizer metrics:

```python
def _display_final_report(self):
    """Display final report with NetraOptimizer metrics"""
    print("\n" + "=" * 80)
    print("ORCHESTRATION REPORT")
    print(f"Batch ID: {self.batch_id}")
    print("=" * 80)

    # Aggregate metrics from NetraOptimizer
    total_tokens = sum(s.total_tokens for s in self.statuses.values())
    total_cost = sum(s.cost_usd for s in self.statuses.values())
    total_savings = sum(s.cache_savings_usd for s in self.statuses.values())
    avg_cache_rate = sum(s.cache_hit_rate for s in self.statuses.values()) / len(self.statuses)

    print(f"\nTotal Tokens: {total_tokens:,}")
    print(f"Average Cache Rate: {avg_cache_rate:.1f}%")
    print(f"Total Cost: ${total_cost:.4f}")
    print(f"Cache Savings: ${total_savings:.4f}")
    print(f"Net Cost: ${total_cost - total_savings:.4f}")

    # View in database
    print(f"\n📊 View detailed analytics:")
    print(f"   python netraoptimizer/view_metrics.py --batch {self.batch_id}")
```

## Complete Working Example

Here's a minimal orchestrator with NetraOptimizer:

```python
#!/usr/bin/env python3
"""Minimal orchestrator with NetraOptimizer integration"""

import asyncio
from pathlib import Path
from uuid import uuid4
from netraoptimizer import NetraOptimizerClient, DatabaseClient

class MinimalOrchestrator:
    def __init__(self, workspace_dir: Path, use_cloud_sql: bool = False):
        self.workspace_dir = workspace_dir

        # Initialize NetraOptimizer
        if use_cloud_sql:
            db_client = DatabaseClient(use_cloud_sql=True)
            asyncio.run(db_client.initialize())
            self.optimizer = NetraOptimizerClient(database_client=db_client)
        else:
            self.optimizer = NetraOptimizerClient()

        self.batch_id = str(uuid4())

        # Your commands
        self.commands = [
            "/gitissueprogressorv3 p0",
            "/gitissueprogressorv3 p1",
            "/createtestsv2 agent unit",
            "/refreshgardener"
        ]

    async def run_all(self):
        """Run all commands with automatic optimization"""
        print(f"Starting batch: {self.batch_id}")

        tasks = []
        for i, command in enumerate(self.commands):
            task = self.optimizer.run(
                command,
                batch_id=self.batch_id,
                execution_sequence=i,
                workspace_context={'workspace': str(self.workspace_dir)},
                cwd=str(self.workspace_dir)
            )
            tasks.append(task)

        # Run all in parallel
        results = await asyncio.gather(*tasks)

        # Display results
        total_tokens = sum(r['tokens']['total'] for r in results)
        total_cost = sum(r['cost_usd'] for r in results)
        avg_cache = sum(r['tokens']['cache_hit_rate'] for r in results) / len(results)

        print(f"\nBatch Complete!")
        print(f"Total Tokens: {total_tokens:,}")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"Average Cache Rate: {avg_cache:.1f}%")

        return results

if __name__ == "__main__":
    orchestrator = MinimalOrchestrator(Path.cwd(), use_cloud_sql=True)
    asyncio.run(orchestrator.run_all())
```

## What You Get Automatically

With NetraOptimizer integration, you automatically get:

### 1. **Comprehensive Metrics** (No Parsing Needed)
- Total, input, output, cached tokens
- Cache hit rate percentage
- Actual cost in USD
- Cache savings amount
- Tool call counts
- Execution time

### 2. **Database Storage** (Automatic)
Every execution is saved to PostgreSQL/CloudSQL with:
- Complete token metrics
- Command classification
- Workspace context
- Batch grouping
- Error details

### 3. **Analytics & Insights**
```bash
# View today's executions
python netraoptimizer/view_metrics.py --today

# View specific batch
python netraoptimizer/view_metrics.py --batch YOUR_BATCH_ID

# See optimization opportunities
python netraoptimizer/view_metrics.py --optimize

# Query database directly
psql -d netra_optimizer -c "
  SELECT command_raw, total_tokens, cost_usd, cache_hit_rate
  FROM command_executions
  WHERE batch_id = 'YOUR_BATCH_ID'
  ORDER BY execution_sequence;
"
```

### 4. **Cost Optimization**
- Automatic cache warming
- Pattern recognition
- Command ordering optimization
- 20-30% cost reduction

## Migration Checklist

- [ ] Add NetraOptimizer imports
- [ ] Initialize in `__init__` with `self.optimizer` and `self.batch_id`
- [ ] Replace subprocess calls with `self.optimizer.run()`
- [ ] Update status from result dictionary
- [ ] Remove manual parsing methods
- [ ] Update display/reporting methods
- [ ] Test with a small batch
- [ ] Deploy to production

## Comparison

| Aspect | Before (Subprocess) | After (NetraOptimizer) |
|--------|-------------------|------------------------|
| **Lines of Code** | 200+ for execution | ~20 lines |
| **Token Parsing** | Complex regex/JSON parsing | Automatic |
| **Error Handling** | Manual try/catch | Built-in |
| **Database** | Manual JSON files | Automatic PostgreSQL |
| **Cost Tracking** | Estimates only | Actual costs |
| **Cache Insights** | None | Full visibility |
| **Analytics** | Build yourself | Included |

## Testing Your Migration

```bash
# 1. Test with dry run
python claude-instance-orchestrator.py --dry-run

# 2. Test with single command
python claude-instance-orchestrator.py --config test-config.json

# 3. View results
python netraoptimizer/view_metrics.py --today

# 4. Check database
psql -d netra_optimizer -c "SELECT * FROM command_executions ORDER BY timestamp DESC LIMIT 5;"
```

## Support

- **Setup Issues**: See `netraoptimizer/SETUP_GUIDE.md`
- **Full Migration Guide**: See `netraoptimizer/docs/ORCHESTRATOR_MIGRATION.md`
- **Examples**: See `netraoptimizer/example_usage.py`

---

**Ready to save 20-30% on Claude costs?** The migration takes less than 30 minutes!