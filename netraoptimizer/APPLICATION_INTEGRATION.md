# How to Use NetraOptimizer with Your Application

## Quick Integration Guide

NetraOptimizer can be integrated into any Python application that executes Claude commands. Here's how to use it:

## 1. Basic Integration (Any Python Script)

### Simple Example
```python
import asyncio
from netraoptimizer import NetraOptimizerClient

async def main():
    # Initialize the client
    client = NetraOptimizerClient()

    # Execute any Claude command
    result = await client.run("/gitissueprogressorv3 p0")

    # Access metrics automatically
    print(f"Tokens: {result['tokens']['total']:,}")
    print(f"Cost: ${result['cost_usd']:.4f}")
    print(f"Cache Rate: {result['tokens']['cache_hit_rate']:.1f}%")

asyncio.run(main())
```

## 2. Integration with Existing Orchestrator

If you have an existing orchestrator like `claude-instance-orchestrator.py`, follow these steps:

### Step 1: Add Imports
```python
from netraoptimizer import NetraOptimizerClient, DatabaseClient
from uuid import uuid4
```

### Step 2: Initialize in Constructor
```python
def __init__(self, workspace_dir):
    # Your existing code...

    # Add NetraOptimizer
    self.optimizer = NetraOptimizerClient()
    self.batch_id = str(uuid4())  # Group related commands
```

### Step 3: Replace Subprocess Calls
**BEFORE (Complex subprocess with manual parsing):**
```python
# 200+ lines of subprocess and parsing
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
stdout, stderr = await process.communicate()
# Manual token parsing...
```

**AFTER (Simple NetraOptimizer):**
```python
# 10 lines with automatic everything
result = await self.optimizer.run(
    command,
    batch_id=self.batch_id,
    execution_sequence=i
)
# All metrics in result dictionary!
```

## 3. CloudSQL Integration (Production)

For production environments, use CloudSQL for centralized metrics:

```python
from netraoptimizer import NetraOptimizerClient, DatabaseClient
import asyncio

async def main():
    # Initialize with CloudSQL
    db_client = DatabaseClient(use_cloud_sql=True)
    await db_client.initialize()
    client = NetraOptimizerClient(database_client=db_client)

    # Execute commands
    result = await client.run("/your-command")

asyncio.run(main())
```

## 4. Batch Execution Example

Track multiple related commands as a batch:

```python
import asyncio
from uuid import uuid4
from netraoptimizer import NetraOptimizerClient

async def run_batch():
    client = NetraOptimizerClient()
    batch_id = str(uuid4())

    commands = [
        "/gitissueprogressorv3 critical",
        "/gitissueprogressorv3 p0",
        "/createtestsv2 agent unit"
    ]

    # Execute all commands with batch tracking
    tasks = []
    for i, cmd in enumerate(commands):
        task = client.run(
            cmd,
            batch_id=batch_id,
            execution_sequence=i
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)

    # Analyze batch metrics
    total_cost = sum(r['cost_usd'] for r in results)
    avg_cache = sum(r['tokens']['cache_hit_rate'] for r in results) / len(results)

    print(f"Batch Cost: ${total_cost:.4f}")
    print(f"Average Cache Rate: {avg_cache:.1f}%")

asyncio.run(run_batch())
```

## 5. Web Application Integration

For Flask/FastAPI applications:

```python
from fastapi import FastAPI
from netraoptimizer import NetraOptimizerClient

app = FastAPI()

# Initialize once at startup
optimizer = NetraOptimizerClient()

@app.post("/execute-claude")
async def execute_command(command: str):
    result = await optimizer.run(command)

    return {
        "status": result['status'],
        "tokens": result['tokens']['total'],
        "cost": result['cost_usd'],
        "cache_rate": result['tokens']['cache_hit_rate']
    }
```

## 6. Scheduled Tasks

For cron jobs or scheduled tasks:

```python
import asyncio
from datetime import datetime
from netraoptimizer import NetraOptimizerClient

async def scheduled_task():
    client = NetraOptimizerClient()

    # Run your scheduled commands
    commands = [
        "/daily-report",
        "/cleanup-old-issues",
        "/refresh-metrics"
    ]

    for cmd in commands:
        result = await client.run(
            cmd,
            workspace_context={
                'scheduled_run': datetime.now().isoformat(),
                'task_type': 'daily'
            }
        )
        print(f"{cmd}: ${result['cost_usd']:.4f}")

# Run with cron or task scheduler
if __name__ == "__main__":
    asyncio.run(scheduled_task())
```

## 7. What You Get Automatically

With NetraOptimizer, every command execution automatically provides:

### Metrics Returned
```python
result = await client.run(command)

# Available in result dictionary:
result['status']                    # 'completed' or 'failed'
result['tokens']['total']           # Total tokens used
result['tokens']['input']           # Input tokens
result['tokens']['output']          # Output tokens
result['tokens']['cached']          # Cached tokens (saved!)
result['tokens']['cache_hit_rate']  # Cache efficiency %
result['cost_usd']                  # Actual cost in USD
result['cache_savings_usd']         # Money saved by caching
result['execution_time_ms']         # How long it took
result['tool_calls']                # Number of tools used
result['error']                     # Error message if failed
```

### Database Storage
Every execution is automatically saved to PostgreSQL with:
- Complete token breakdown
- Cost analysis
- Cache performance
- Error tracking
- Workspace context
- Batch grouping

### Analytics & Insights
```bash
# View metrics
python netraoptimizer/view_metrics.py --today
python netraoptimizer/view_metrics.py --batch YOUR_BATCH_ID
python netraoptimizer/view_metrics.py --optimize

# Query database
psql -d netra_optimizer -c "
  SELECT command_raw, cost_usd, cache_hit_rate
  FROM command_executions
  WHERE batch_id = 'YOUR_BATCH_ID'
"
```

## 8. Environment Configuration

### For Local Development
```bash
export NETRA_DB_HOST=localhost
export NETRA_DB_PORT=5432
export NETRA_DB_NAME=netra_optimizer
export NETRA_DB_USER=your_user
export NETRA_DB_PASSWORD=your_password
```

### For CloudSQL (Production)
```bash
export USE_CLOUD_SQL=true
export ENVIRONMENT=staging
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5434

# Start Cloud SQL Proxy
cloud-sql-proxy --port=5434 netra-staging:us-central1:staging-shared-postgres
```

## 9. Common Integration Patterns

### Pattern 1: Singleton Client
```python
# app.py
_optimizer = None

def get_optimizer():
    global _optimizer
    if _optimizer is None:
        _optimizer = NetraOptimizerClient()
    return _optimizer
```

### Pattern 2: Context Manager
```python
class OptimizedExecution:
    def __init__(self, use_cloud_sql=False):
        self.use_cloud_sql = use_cloud_sql
        self.client = None

    async def __aenter__(self):
        if self.use_cloud_sql:
            db_client = DatabaseClient(use_cloud_sql=True)
            await db_client.initialize()
            self.client = NetraOptimizerClient(database_client=db_client)
        else:
            self.client = NetraOptimizerClient()
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass

# Usage
async with OptimizedExecution(use_cloud_sql=True) as optimizer:
    result = await optimizer.run("/command")
```

### Pattern 3: Decorator
```python
def track_with_netra(batch_name=None):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            client = NetraOptimizerClient()
            batch_id = str(uuid4()) if batch_name else None

            # Pass client to function
            kwargs['optimizer'] = client
            kwargs['batch_id'] = batch_id

            return await func(*args, **kwargs)
        return wrapper
    return decorator

@track_with_netra(batch_name="daily_tasks")
async def my_task(optimizer=None, batch_id=None):
    result = await optimizer.run("/command", batch_id=batch_id)
    return result
```

## 10. Migration Checklist

When migrating existing code to use NetraOptimizer:

- [ ] Install NetraOptimizer dependencies
- [ ] Set up database (local or CloudSQL)
- [ ] Add NetraOptimizer imports
- [ ] Initialize client in your application
- [ ] Replace subprocess/direct Claude calls
- [ ] Remove manual token parsing code
- [ ] Update result handling to use NetraOptimizer dictionary
- [ ] Test with small batch
- [ ] View metrics to verify tracking
- [ ] Deploy to production

## Examples

### Full Working Examples
- **Orchestrator**: `scripts/claude-instance-orchestrator-netra.py`
- **Basic Usage**: `netraoptimizer/example_usage.py`
- **Migration Guide**: `scripts/ORCHESTRATOR_MIGRATION_EXAMPLE.md`

### Quick Test
```bash
# Test your integration
python -c "
from netraoptimizer import NetraOptimizerClient
import asyncio

async def test():
    client = NetraOptimizerClient()
    print('✅ NetraOptimizer ready!')

asyncio.run(test())
"
```

## Support

- **Setup Issues**: See `netraoptimizer/SETUP_GUIDE.md`
- **Documentation**: See `netraoptimizer/docs/`
- **Examples**: See `netraoptimizer/example_usage.py`

---

**Start tracking your Claude usage today and save 20-30% on costs!**