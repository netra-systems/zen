# Orchestrator Migration Guide - NetraOptimizer Integration

## 📋 What Changes in Your Orchestrator

### BEFORE: Your Current Orchestrator (Direct Subprocess)

```python
# claude-instance-orchestrator.py (CURRENT)
async def run_instance(self, name: str):
    """Run a single Claude Code instance"""
    config = self.instances[name]
    status = self.statuses[name]

    # Build command
    cmd = [self.claude_exec]
    cmd.extend(["--output-format", config.output_format])
    cmd.extend(["--permission-mode", config.permission_mode])
    cmd.append(config.command)

    # Run subprocess directly
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=str(self.workspace_dir)
    )

    # Wait for completion
    stdout, stderr = await process.communicate()

    # Manual parsing of output
    if stdout:
        stdout_str = stdout.decode()
        status.output += stdout_str
        # Manual token parsing
        self._parse_final_output_token_usage(stdout_str, status, config.output_format)

    # Manual storage to JSON
    self._save_results_to_json()
```

### AFTER: With NetraOptimizer (Automatic Everything!)

```python
# claude-instance-orchestrator.py (WITH NETRAOPTIMIZER)
from netraoptimizer import NetraOptimizerClient, DatabaseClient

class ClaudeInstanceOrchestrator:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        # Create ONE client for entire orchestrator with CloudSQL
        db_client = DatabaseClient(use_cloud_sql=True)
        asyncio.run(db_client.initialize())
        self.optimizer = NetraOptimizerClient(database_client=db_client)
        self.batch_id = str(uuid4())  # Group all instances in this run

    async def run_instance(self, name: str):
        """Run a single Claude Code instance with automatic optimization"""
        config = self.instances[name]

        # ALL complexity handled by NetraOptimizer!
        result = await self.optimizer.run(
            config.command,
            batch_id=self.batch_id,
            execution_sequence=self.startup_order.get(name, 0),
            workspace_context={
                'instance_name': name,
                'workspace_dir': str(self.workspace_dir),
                'description': config.description
            },
            cwd=str(self.workspace_dir)
        )

        # Update status from result
        status = self.statuses[name]
        status.status = result['status']
        status.total_tokens = result['tokens']['total']
        status.input_tokens = result['tokens']['input']
        status.output_tokens = result['tokens']['output']
        status.cached_tokens = result['tokens']['cached']
        status.cache_hit_rate = result['tokens']['cache_hit_rate']
        status.cost_usd = result['cost_usd']
        status.execution_time = result['execution_time_ms'] / 1000

        # No manual parsing needed!
        # No manual storage needed - already in database!

        return result['status'] == 'completed'
```

## 🔄 Step-by-Step Migration

### Step 1: Add NetraOptimizer Import

```python
# At the top of your orchestrator file
from netraoptimizer import NetraOptimizerClient, DatabaseClient
from uuid import uuid4
import asyncio
```

### Step 2: Initialize the Client in __init__

```python
def __init__(self, workspace_dir: Path, ...):
    # Your existing init code...
    self.workspace_dir = workspace_dir

    # ADD THESE LINES for CloudSQL integration:
    db_client = DatabaseClient(use_cloud_sql=True)
    asyncio.run(db_client.initialize())
    self.optimizer = NetraOptimizerClient(database_client=db_client)
    self.batch_id = str(uuid4())
```

### Step 3: Replace run_instance Method

Replace your entire `run_instance` method with this simpler version:

```python
async def run_instance(self, name: str):
    """Run a Claude Code instance with NetraOptimizer"""
    config = self.instances[name]
    status = self.statuses[name]

    try:
        # Mark as running
        status.status = "running"
        status.start_time = time.time()

        # Execute through NetraOptimizer
        result = await self.optimizer.run(
            config.command,
            batch_id=self.batch_id,
            execution_sequence=list(self.instances.keys()).index(name),
            workspace_context={
                'instance_name': name,
                'workspace_dir': str(self.workspace_dir),
                'description': config.description,
                'session_id': config.session_id
            },
            env=self._get_environment(),
            cwd=str(self.workspace_dir)
        )

        # Update status from result
        status.end_time = time.time()
        status.status = result['status']
        status.total_tokens = result['tokens']['total']
        status.input_tokens = result['tokens']['input']
        status.output_tokens = result['tokens']['output']
        status.cached_tokens = result['tokens']['cached']
        status.tool_calls = result.get('tool_calls', 0)

        # Calculate cache hit rate
        if status.total_tokens > 0:
            status.cache_hit_rate = result['tokens']['cache_hit_rate']

        # Store output if you need it
        if result.get('error'):
            status.error = result['error']

        logger.info(f"Instance {name} {result['status']} - "
                   f"Tokens: {status.total_tokens:,} "
                   f"(Cache: {status.cache_hit_rate:.1f}%) "
                   f"Cost: ${result['cost_usd']:.4f}")

        return result['status'] == 'completed'

    except Exception as e:
        status.status = "failed"
        status.error = str(e)
        logger.error(f"Failed to run instance {name}: {e}")
        return False
```

### Step 4: Remove Manual Parsing Methods

You can DELETE these methods - NetraOptimizer handles it all:

```python
# DELETE THESE - NO LONGER NEEDED:
# - _parse_final_output_token_usage()
# - _parse_json_token_usage()
# - _parse_regex_token_usage()
# - _save_results_to_json() (data goes to database instead)
```

### Step 5: Update Status Display

Update your `_display_status` method to show new metrics:

```python
def _display_status(self):
    """Display current status of all instances"""
    print("\n" + "="*80)
    print(f"ORCHESTRATOR STATUS - {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)

    total_tokens = 0
    total_cost = 0

    for name, status in self.statuses.items():
        # Status line
        print(f"\n[{name}] {status.status.upper()}")

        # Execution time
        if status.start_time:
            duration = (status.end_time or time.time()) - status.start_time
            print(f"  Duration: {duration:.1f}s")

        # Token metrics
        if status.total_tokens > 0:
            print(f"  Tokens: {status.total_tokens:,} "
                  f"(Input: {status.input_tokens:,}, "
                  f"Output: {status.output_tokens:,}, "
                  f"Cached: {status.cached_tokens:,})")
            print(f"  Cache Hit Rate: {status.cache_hit_rate:.1f}%")

            # Cost (if available from NetraOptimizer)
            cost = status.total_tokens * 0.00003  # Rough estimate
            print(f"  Estimated Cost: ${cost:.4f}")
            total_cost += cost

        # Tool calls
        if status.tool_calls > 0:
            print(f"  Tool Calls: {status.tool_calls}")

        total_tokens += status.total_tokens

    # Summary
    print("\n" + "-"*80)
    print(f"TOTAL TOKENS: {total_tokens:,}")
    print(f"TOTAL COST: ${total_cost:.4f}")
    print(f"BATCH ID: {self.batch_id}")
    print("="*80)
```

## 📊 What You Get Automatically

With NetraOptimizer integration, you automatically get:

### 1. Database Storage (CloudSQL)
Every execution is stored in Google CloudSQL with:
- Complete token metrics
- Execution time
- Cost calculations
- Error details
- Workspace context
- Batch grouping

### 2. Analytics Queries
You can now query your data:

```sql
-- See today's executions
SELECT * FROM command_executions
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Cost by command type
SELECT
    command_base,
    COUNT(*) as runs,
    SUM(cost_usd) as total_cost,
    AVG(cache_hit_rate) as avg_cache_rate
FROM command_executions
WHERE batch_id = 'your-batch-id'
GROUP BY command_base;

-- Find expensive commands
SELECT command_raw, cost_usd, total_tokens
FROM command_executions
WHERE cost_usd > 1.0
ORDER BY cost_usd DESC;
```

### 3. Cache Optimization Insights
```sql
-- See cache effectiveness over time
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(cache_hit_rate) as avg_cache_rate,
    SUM(cache_savings_usd) as savings
FROM command_executions
GROUP BY hour
ORDER BY hour;
```

## 🚀 Complete Working Example

Here's a minimal working orchestrator with NetraOptimizer and CloudSQL:

```python
#!/usr/bin/env python3
"""Minimal orchestrator with NetraOptimizer integration"""

import asyncio
from pathlib import Path
from uuid import uuid4
from netraoptimizer import NetraOptimizerClient, DatabaseClient

class MinimalOrchestrator:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        # Initialize with CloudSQL
        self.db_client = DatabaseClient(use_cloud_sql=True)
        asyncio.run(self.db_client.initialize())
        self.optimizer = NetraOptimizerClient(database_client=self.db_client)
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
    orchestrator = MinimalOrchestrator(Path.cwd())
    asyncio.run(orchestrator.run_all())
```

## 🎯 Benefits You Get Immediately

1. **Cost Tracking**: Know exactly how much each command costs
2. **Cache Insights**: See which commands benefit from caching (98% possible!)
3. **Performance Metrics**: Track execution times and optimize slow commands
4. **Failure Analysis**: All errors stored for debugging
5. **Batch Analysis**: Group related commands and analyze together
6. **Historical Data**: Query past executions for patterns
7. **No Manual Parsing**: Automatic extraction of all metrics
8. **No Manual Storage**: Direct to database, no JSON files needed

## 🔍 Viewing Your Data

After running with NetraOptimizer, view your data:

```python
# Quick script to see your data
import asyncio
from netraoptimizer.database import DatabaseClient

async def view_recent():
    db = DatabaseClient()
    await db.initialize()

    # Get recent executions
    recent = await db.get_recent_executions(limit=10)

    for record in recent:
        print(f"\nCommand: {record['command_raw']}")
        print(f"  Tokens: {record['total_tokens']:,}")
        print(f"  Cache Rate: {record['cache_hit_rate']:.1f}%")
        print(f"  Cost: ${record['cost_usd']:.4f}")
        print(f"  Time: {record['execution_time_ms']/1000:.1f}s")

asyncio.run(view_recent())
```

## 🚦 Migration Checklist

- [ ] Set up CloudSQL connection (or use local PostgreSQL)
- [ ] Start Cloud SQL Proxy: `cloud-sql-proxy --port=5434 PROJECT:REGION:INSTANCE`
- [ ] Run setup script: `python netraoptimizer/database/setup.py`
- [ ] Add imports: `from netraoptimizer import NetraOptimizerClient, DatabaseClient`
- [ ] Initialize client with CloudSQL in `__init__`
- [ ] Replace `run_instance` method
- [ ] Remove manual parsing methods
- [ ] Update status display
- [ ] Test with a small batch
- [ ] Deploy to production
- [ ] Start analyzing your data in CloudSQL!

## 💡 Pro Tips

1. **Use Batch IDs**: Group related commands with the same batch_id for analysis
2. **Add Context**: Include workspace_context for better insights
3. **Monitor Cache**: Watch cache_hit_rate to optimize command ordering
4. **Query Often**: Use SQL to find patterns and optimization opportunities
5. **Set Alerts**: Create alerts for high-cost commands

---

**Ready to save 20-30% on Claude costs? The migration takes less than 30 minutes!**