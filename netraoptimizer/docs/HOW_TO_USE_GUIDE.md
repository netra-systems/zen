# How-To-Use Guide for NetraOptimizer

## 🚀 Complete Developer Guide

This guide provides practical examples and patterns for using NetraOptimizer in your applications.

## Table of Contents
- [Basic Usage](#basic-usage)
- [Advanced Patterns](#advanced-patterns)
- [Batch Execution](#batch-execution)
- [Context Management](#context-management)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Migration Guide](#migration-guide)

## Basic Usage

### Simple Command Execution with CloudSQL

```python
import asyncio
from netraoptimizer import NetraOptimizerClient, DatabaseClient

async def main():
    # Initialize with CloudSQL (recommended for production)
    db_client = DatabaseClient(use_cloud_sql=True)
    await db_client.initialize()

    client = NetraOptimizerClient(database_client=db_client)

    # Execute a command - automatically tracked in CloudSQL
    result = await client.run("/gitissueprogressorv3 p0")

    # Access results
    print(f"Status: {result['status']}")
    print(f"Tokens: {result['tokens']['total']:,}")
    print(f"Cost: ${result['cost_usd']:.4f}")
    print(f"Execution time: {result['execution_time_ms']}ms")

    # Close database connection
    await db_client.close()

# Run the async function
asyncio.run(main())
```

### Singleton Pattern with CloudSQL (Recommended)

```python
# app/services/claude_service.py
from netraoptimizer import NetraOptimizerClient, DatabaseClient

class ClaudeService:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        if self._client is None:
            # Initialize with CloudSQL for production/staging
            db_client = DatabaseClient(use_cloud_sql=True)
            await db_client.initialize()
            self._client = NetraOptimizerClient(database_client=db_client)

    async def execute(self, command: str, **kwargs):
        if self._client is None:
            await self.initialize()
        return await self._client.run(command, **kwargs)

# Usage across your application
service = ClaudeService()
result = await service.execute("/test command")
```

## Advanced Patterns

### Custom Configuration

```python
from netraoptimizer import NetraOptimizerClient
from netraoptimizer.config import NetraOptimizerConfig

# Create custom configuration
config = NetraOptimizerConfig(
    db_host="production-db.example.com",
    db_name="prod_optimizer",
    claude_timeout=1200,  # 20 minutes for long operations
    enable_analytics=True
)

# Pass custom database URL
client = NetraOptimizerClient(
    database_client=DatabaseClient(config.database_url),
    timeout=config.claude_timeout
)
```

### With Context Managers

```python
from contextlib import asynccontextmanager
from netraoptimizer import NetraOptimizerClient, DatabaseClient

@asynccontextmanager
async def optimized_claude():
    """Context manager for NetraOptimizer client with CloudSQL."""
    db_client = DatabaseClient(use_cloud_sql=True)
    await db_client.initialize()
    client = NetraOptimizerClient(database_client=db_client)
    try:
        yield client
    finally:
        await db_client.close()

# Usage
async def process_issues():
    async with optimized_claude() as client:
        result = await client.run("/gitissueprogressorv3 critical")
        # Client automatically cleans up after context exit
```

## Batch Execution

### Parallel Batch Processing

```python
import asyncio
from uuid import uuid4

async def run_batch_commands(commands: list):
    """Execute multiple commands in parallel with shared batch context."""
    client = NetraOptimizerClient()
    batch_id = str(uuid4())

    # Create tasks for parallel execution
    tasks = []
    for i, command in enumerate(commands):
        task = client.run(
            command,
            batch_id=batch_id,
            execution_sequence=i
        )
        tasks.append(task)

    # Execute all commands in parallel
    results = await asyncio.gather(*tasks)

    # Aggregate results
    total_tokens = sum(r['tokens']['total'] for r in results)
    total_cost = sum(r['cost_usd'] for r in results)
    cache_rate = sum(r['tokens']['cache_hit_rate'] for r in results) / len(results)

    print(f"Batch {batch_id} completed:")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Total cost: ${total_cost:.2f}")
    print(f"  Average cache rate: {cache_rate:.1f}%")

    return results

# Example usage
commands = [
    "/gitissueprogressorv3 p0",
    "/gitissueprogressorv3 p1",
    "/createtestsv2 agent goldenpath unit",
    "/refreshgardener"
]

results = await run_batch_commands(commands)
```

### Sequential Execution with Cache Warming

```python
async def run_sequential_with_cache_warming(commands: list):
    """Execute commands sequentially to maximize cache benefits."""
    client = NetraOptimizerClient()
    batch_id = str(uuid4())
    results = []

    for i, command in enumerate(commands):
        # Add delay for cache warming (except first command)
        if i > 0:
            await asyncio.sleep(2)

        result = await client.run(
            command,
            batch_id=batch_id,
            execution_sequence=i
        )
        results.append(result)

        # Monitor cache improvement
        if i > 0:
            cache_improvement = (
                result['tokens']['cache_hit_rate'] -
                results[0]['tokens']['cache_hit_rate']
            )
            print(f"Cache improvement: +{cache_improvement:.1f}%")

    return results
```

## Context Management

### Workspace Context

```python
import os
from pathlib import Path

async def run_with_workspace_context(command: str, workspace_path: str):
    """Execute command with rich workspace context."""
    client = NetraOptimizerClient()

    # Gather workspace information
    workspace = Path(workspace_path)
    workspace_context = {
        "workspace_path": str(workspace),
        "file_count": len(list(workspace.rglob("*"))),
        "total_size_mb": sum(f.stat().st_size for f in workspace.rglob("*") if f.is_file()) / (1024 * 1024),
        "languages": detect_languages(workspace),  # Custom function
        "git_branch": get_git_branch(workspace),   # Custom function
        "uncommitted_changes": count_uncommitted_changes(workspace)
    }

    # Execute with context
    result = await client.run(
        command,
        workspace_context=workspace_context,
        cwd=str(workspace)
    )

    return result
```

### Session Context

```python
class SessionManager:
    """Manage execution sessions with context preservation."""

    def __init__(self):
        self.client = NetraOptimizerClient()
        self.session_id = str(uuid4())
        self.command_history = []

    async def execute(self, command: str):
        """Execute command with session context."""
        session_context = {
            "session_id": self.session_id,
            "position_in_session": len(self.command_history) + 1,
            "prior_commands": self.command_history[-5:],  # Last 5 commands
            "session_duration_minutes": self._get_session_duration()
        }

        result = await self.client.run(
            command,
            session_context=session_context
        )

        self.command_history.append(command)
        return result

    def _get_session_duration(self):
        # Implementation details...
        pass
```

## Error Handling

### Comprehensive Error Management

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def safe_execute(command: str, max_retries: int = 3) -> Optional[dict]:
    """Execute command with comprehensive error handling."""
    client = NetraOptimizerClient()

    for attempt in range(max_retries):
        try:
            result = await client.run(command)

            # Check for failures
            if result['status'] == 'failed':
                logger.error(f"Command failed: {result.get('error')}")
                if "rate limit" in str(result.get('error', '')).lower():
                    # Wait longer for rate limits
                    await asyncio.sleep(60 * (attempt + 1))
                    continue
                else:
                    # Don't retry non-transient errors
                    return result

            return result

        except asyncio.TimeoutError:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                return {
                    'status': 'timeout',
                    'error': f'Command timed out after {max_retries} attempts'
                }

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    return None
```

### Timeout Management

```python
async def run_with_dynamic_timeout(command: str):
    """Adjust timeout based on command complexity."""
    client = NetraOptimizerClient()

    # Parse command to estimate complexity
    from netraoptimizer.analytics import parse_command, extract_features
    parsed = parse_command(command)
    features = extract_features(command, parsed)

    # Dynamic timeout based on complexity
    if features['estimated_complexity'] > 7:
        timeout = 1800  # 30 minutes for complex commands
    elif features['estimated_complexity'] > 4:
        timeout = 600   # 10 minutes for medium commands
    else:
        timeout = 300   # 5 minutes for simple commands

    # Override client timeout for this execution
    client.timeout = timeout

    result = await client.run(command)
    return result
```

## Performance Optimization

### Cache Optimization Strategy

```python
async def optimize_command_order(commands: list):
    """Reorder commands for maximum cache benefit."""
    from netraoptimizer.analytics import parse_command

    # Group similar commands
    command_groups = {}
    for cmd in commands:
        parsed = parse_command(cmd)
        base = parsed['base']
        if base not in command_groups:
            command_groups[base] = []
        command_groups[base].append(cmd)

    # Execute groups with cache-friendly ordering
    client = NetraOptimizerClient()
    results = []

    for base, group_commands in command_groups.items():
        # Sort by priority within group
        sorted_commands = sorted(
            group_commands,
            key=lambda x: _get_priority_score(x),
            reverse=True
        )

        for cmd in sorted_commands:
            result = await client.run(cmd)
            results.append(result)
            await asyncio.sleep(1)  # Brief pause for cache propagation

    return results

def _get_priority_score(command: str) -> int:
    """Score command priority for execution order."""
    if 'p0' in command or 'critical' in command:
        return 10
    elif 'p1' in command or 'high' in command:
        return 5
    else:
        return 1
```

### Resource Management

```python
class ResourceManagedExecutor:
    """Execute commands with resource limits."""

    def __init__(self, max_concurrent: int = 5, max_tokens_per_minute: int = 100000):
        self.client = NetraOptimizerClient()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.token_bucket = TokenBucket(max_tokens_per_minute)

    async def execute(self, command: str):
        """Execute with resource management."""
        async with self.semaphore:
            # Wait for token availability
            await self.token_bucket.acquire(estimate_tokens(command))

            # Execute command
            result = await self.client.run(command)

            # Track actual usage
            self.token_bucket.report_usage(result['tokens']['total'])

            return result
```

## Migration Guide

### Migrating from Direct Subprocess Calls

#### Before (Direct Subprocess)
```python
import subprocess

def run_claude_command(command):
    result = subprocess.run(
        ["claude", command],
        capture_output=True,
        text=True
    )
    return result.stdout
```

#### After (NetraOptimizer)
```python
from netraoptimizer import NetraOptimizerClient

async def run_claude_command(command):
    client = NetraOptimizerClient()
    result = await client.run(command)
    return result  # Now with full metrics!
```

### Migrating the Orchestrator

#### Before (orchestrator.py)
```python
# Old implementation with direct subprocess
async def run_instance(self, name: str):
    config = self.instances[name]
    process = await asyncio.create_subprocess_exec(
        "claude", config.command,
        stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    # Manual parsing and storage...
```

#### After (orchestrator.py with NetraOptimizer)
```python
from netraoptimizer import NetraOptimizerClient

async def run_instance(self, name: str):
    config = self.instances[name]

    # All complexity handled by the client!
    result = await self.client.run(
        config.command,
        batch_id=self.batch_id,
        execution_sequence=self.execution_order[name]
    )

    # Metrics automatically stored in database
    return result
```

## Best Practices

### 1. Initialize Once
```python
# Good: Single client instance
class Application:
    def __init__(self):
        self.claude_client = NetraOptimizerClient()

# Bad: Creating new client for each call
async def bad_pattern(command):
    client = NetraOptimizerClient()  # Don't do this repeatedly!
    return await client.run(command)
```

### 2. Use Batch Context
```python
# Good: Group related commands
batch_id = str(uuid4())
for i, cmd in enumerate(related_commands):
    await client.run(cmd, batch_id=batch_id, execution_sequence=i)

# Bad: No context for related commands
for cmd in related_commands:
    await client.run(cmd)  # Loses optimization opportunity
```

### 3. Handle Errors Gracefully
```python
# Good: Comprehensive error handling
try:
    result = await client.run(command)
    if result['status'] == 'failed':
        handle_failure(result['error'])
except asyncio.TimeoutError:
    handle_timeout()

# Bad: Ignoring potential failures
result = await client.run(command)  # What if it fails?
```

### 4. Leverage Analytics
```python
# Good: Use parsed features for decisions
from netraoptimizer.analytics import extract_features
features = extract_features(command)
if features['estimated_complexity'] > 8:
    # Prepare for long execution
    notify_user("This may take a while...")
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Database connection failed | Check `NETRA_DB_*` environment variables |
| Timeout errors | Increase `claude_timeout` in config |
| Low cache hit rates | Group similar commands together |
| High costs | Review command complexity, optimize scope |
| Missing metrics | Ensure output is JSON format |

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Client will now log detailed execution info
client = NetraOptimizerClient()
result = await client.run("/test command")
```

## Support

For help and questions:
1. Check test cases in `tests/netraoptimizer/`
2. Review the API documentation
3. Examine the example scripts
4. Create an issue with reproduction steps

---

**Remember**: Every execution through NetraOptimizerClient is an opportunity to learn and optimize!