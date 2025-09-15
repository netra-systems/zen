# Integration Guide - NetraOptimizer

## 🔄 Complete Integration Strategy

This guide provides step-by-step instructions for integrating NetraOptimizer into existing systems and enforcing its use across your entire codebase.

## Table of Contents
- [Phase 1: Assessment](#phase-1-assessment)
- [Phase 2: Pilot Integration](#phase-2-pilot-integration)
- [Phase 3: Full Migration](#phase-3-full-migration)
- [Phase 4: Enforcement](#phase-4-enforcement)
- [Integration Examples](#integration-examples)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Phase 1: Assessment

### 1.1 Identify Current Claude Usage

```bash
# Find all direct Claude subprocess calls
grep -r "subprocess.*claude" . --include="*.py"
grep -r "asyncio.create_subprocess.*claude" . --include="*.py"
grep -r "os.system.*claude" . --include="*.py"
grep -r "Popen.*claude" . --include="*.py"

# Find all potential integration points
find . -name "*.py" -exec grep -l "claude" {} \;
```

### 1.2 Catalog Usage Patterns

Create an inventory of how Claude is currently used:

```python
# usage_audit.py
import ast
import os
from pathlib import Path

class ClaudeUsageAuditor(ast.NodeVisitor):
    def __init__(self):
        self.usages = []

    def visit_Call(self, node):
        # Check for subprocess calls
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['run', 'Popen', 'call']:
                for arg in node.args:
                    if isinstance(arg, ast.List):
                        for element in arg.elts:
                            if isinstance(element, ast.Str) and 'claude' in element.s:
                                self.usages.append({
                                    'file': self.current_file,
                                    'line': node.lineno,
                                    'type': 'subprocess'
                                })
        self.generic_visit(node)

# Run audit
auditor = ClaudeUsageAuditor()
for py_file in Path('.').rglob('*.py'):
    auditor.current_file = str(py_file)
    tree = ast.parse(py_file.read_text())
    auditor.visit(tree)

print(f"Found {len(auditor.usages)} Claude usages to migrate")
```

## Phase 2: Pilot Integration

### 2.1 Setup NetraOptimizer with CloudSQL

First, ensure NetraOptimizer is configured with CloudSQL for production use:

```bash
# Install dependencies
pip install -r netraoptimizer/requirements.txt

# Setup CloudSQL proxy (for local development)
cloud-sql-proxy --port=5434 netra-staging:us-central1:staging-shared-postgres

# Configure environment
export USE_CLOUD_SQL=true
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5434
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD="[from Secret Manager]"

# Initialize database
python netraoptimizer/database/setup.py
```

### 2.2 Start with High-Value Target

Choose your highest-usage component first (e.g., orchestrator):

```python
# OLD: claude_instance_orchestrator.py (BEFORE)
import asyncio
import subprocess

class ClaudeInstanceOrchestrator:
    async def run_instance(self, name: str):
        config = self.instances[name]

        # Direct subprocess call - NEEDS MIGRATION
        process = await asyncio.create_subprocess_exec(
            "claude",
            config.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        # Manual parsing
        tokens = self._parse_tokens(stdout)

        # Manual storage
        self._save_to_json(name, tokens)
```

```python
# NEW: claude_instance_orchestrator.py (AFTER)
from netraoptimizer import NetraOptimizerClient, DatabaseClient
from uuid import uuid4

class ClaudeInstanceOrchestrator:
    def __init__(self):
        # Initialize with CloudSQL for production
        db_client = DatabaseClient(use_cloud_sql=True)
        asyncio.run(db_client.initialize())
        self.optimizer_client = NetraOptimizerClient(database_client=db_client)
        self.batch_id = str(uuid4())

    async def run_instance(self, name: str):
        config = self.instances[name]

        # ALL complexity handled by NetraOptimizer!
        result = await self.optimizer_client.run(
            config.command,
            batch_id=self.batch_id,
            execution_sequence=self.execution_order.get(name, 0),
            workspace_context={
                'instance_name': name,
                'workspace_dir': str(self.workspace_dir)
            }
        )

        # Metrics automatically stored in database
        # No manual parsing or storage needed!

        return result
```

### 2.2 Create Migration Wrapper

For gradual migration, create a compatibility wrapper:

```python
# migration_wrapper.py
import asyncio
import logging
from typing import Optional, Dict, Any
from netraoptimizer import NetraOptimizerClient

logger = logging.getLogger(__name__)

class ClaudeMigrationWrapper:
    """
    Drop-in replacement for subprocess calls.
    Provides backward compatibility during migration.
    """

    def __init__(self, use_optimizer: bool = True):
        self.use_optimizer = use_optimizer
        if use_optimizer:
            self.client = NetraOptimizerClient()

    async def run_command(
        self,
        command: str,
        legacy_mode: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Unified interface for both old and new patterns.
        """
        if legacy_mode or not self.use_optimizer:
            # Fall back to legacy for comparison
            return await self._legacy_run(command, **kwargs)
        else:
            # Use NetraOptimizer
            return await self.client.run(command, **kwargs)

    async def _legacy_run(self, command: str, **kwargs):
        """Legacy subprocess implementation for comparison."""
        logger.warning(f"Using legacy mode for: {command}")

        process = await asyncio.create_subprocess_exec(
            "claude", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        return {
            'status': 'completed' if process.returncode == 0 else 'failed',
            'output': stdout.decode(),
            'error': stderr.decode()
        }

# Global instance for easy migration
claude = ClaudeMigrationWrapper()
```

## Phase 3: Full Migration

### 3.1 Systematic File-by-File Migration

```python
# migration_script.py
import os
import re
from pathlib import Path

def migrate_file(filepath: Path):
    """Migrate a single file to use NetraOptimizer."""
    content = filepath.read_text()
    original = content

    # Pattern replacements
    replacements = [
        # Subprocess patterns
        (
            r'subprocess\.run\(\["claude",\s*([^]]+)\]',
            r'await optimizer_client.run(\1'
        ),
        (
            r'asyncio\.create_subprocess_exec\(\s*"claude",\s*([^)]+)\)',
            r'optimizer_client.run(\1)'
        ),
        # Import statements
        (
            r'import subprocess',
            'from netraoptimizer import NetraOptimizerClient\n# import subprocess  # Replaced by NetraOptimizer'
        ),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    # Add client initialization if needed
    if 'NetraOptimizerClient' in content and 'optimizer_client = ' not in content:
        # Add initialization after imports
        import_end = content.find('\n\n')
        if import_end > 0:
            content = (
                content[:import_end] +
                '\n\n# NetraOptimizer client (singleton pattern)\n' +
                'optimizer_client = NetraOptimizerClient()\n' +
                content[import_end:]
            )

    if content != original:
        # Backup original
        backup_path = filepath.with_suffix('.py.backup')
        filepath.rename(backup_path)

        # Write migrated version
        filepath.write_text(content)
        print(f"Migrated: {filepath}")
        return True

    return False

# Run migration
migrated_count = 0
for py_file in Path('.').rglob('*.py'):
    if migrate_file(py_file):
        migrated_count += 1

print(f"Migrated {migrated_count} files")
```

### 3.2 Update Import Statements

```python
# Before
import subprocess
import json
import time

# After
from netraoptimizer import NetraOptimizerClient
# Removed: subprocess, manual JSON parsing, manual timing
```

### 3.3 Service-Specific Migrations

#### Web API Service
```python
# api/routes/claude.py (BEFORE)
@app.post("/execute")
async def execute_command(command: str):
    result = subprocess.run(["claude", command], capture_output=True)
    return {"output": result.stdout.decode()}

# api/routes/claude.py (AFTER)
from netraoptimizer import NetraOptimizerClient

# Initialize once at module level
optimizer = NetraOptimizerClient()

@app.post("/execute")
async def execute_command(command: str):
    result = await optimizer.run(command)
    return {
        "output": result,
        "metrics": {
            "tokens": result['tokens']['total'],
            "cost": result['cost_usd'],
            "cache_rate": result['tokens']['cache_hit_rate']
        }
    }
```

#### Background Job Processor
```python
# jobs/processor.py (BEFORE)
class JobProcessor:
    def process_claude_job(self, job_data):
        cmd = job_data['command']
        result = os.system(f"claude {cmd}")
        # No metrics, no tracking

# jobs/processor.py (AFTER)
from netraoptimizer import NetraOptimizerClient

class JobProcessor:
    def __init__(self):
        self.optimizer = NetraOptimizerClient()

    async def process_claude_job(self, job_data):
        result = await self.optimizer.run(
            job_data['command'],
            workspace_context={'job_id': job_data['id']},
            batch_id=job_data.get('batch_id')
        )

        # Rich metrics available
        await self.report_metrics(result['tokens'], result['cost_usd'])
```

## Phase 4: Enforcement

### 4.1 Pre-Commit Hook

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: no-direct-claude
        name: Prevent direct Claude subprocess calls
        entry: ./scripts/check_claude_usage.py
        language: python
        files: \.py$
```

```python
# scripts/check_claude_usage.py
#!/usr/bin/env python3
import sys
import re
from pathlib import Path

FORBIDDEN_PATTERNS = [
    r'subprocess.*claude',
    r'os\.system.*claude',
    r'Popen.*claude',
    r'asyncio\.create_subprocess.*claude'
]

def check_file(filepath):
    content = Path(filepath).read_text()
    violations = []

    for i, line in enumerate(content.split('\n'), 1):
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                violations.append(f"{filepath}:{i}: Direct Claude call forbidden. Use NetraOptimizerClient")

    return violations

if __name__ == "__main__":
    violations = []
    for filepath in sys.argv[1:]:
        violations.extend(check_file(filepath))

    if violations:
        print("❌ Direct Claude calls detected:")
        for v in violations:
            print(f"  {v}")
        print("\n✅ Fix: Replace with NetraOptimizerClient")
        sys.exit(1)
```

### 4.2 CI/CD Pipeline Check

```yaml
# .github/workflows/enforce-netraoptimizer.yml
name: Enforce NetraOptimizer Usage

on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Check for direct Claude calls
        run: |
          if grep -r "subprocess.*claude" . --include="*.py"; then
            echo "❌ Direct Claude calls found!"
            echo "Use NetraOptimizerClient instead"
            exit 1
          fi

      - name: Verify NetraOptimizer imports
        run: |
          # Check that files using Claude import NetraOptimizer
          for file in $(grep -l "claude" . -r --include="*.py"); do
            if ! grep -q "from netraoptimizer import" "$file"; then
              echo "❌ $file uses Claude but doesn't import NetraOptimizer"
              exit 1
            fi
          done
```

### 4.3 Runtime Enforcement

```python
# monkey_patch.py
# Apply at application startup to catch any missed calls

import subprocess
import os

original_subprocess_run = subprocess.run
original_os_system = os.system

def enforced_subprocess_run(cmd, *args, **kwargs):
    if isinstance(cmd, list) and 'claude' in cmd[0]:
        raise RuntimeError(
            "Direct Claude subprocess calls are forbidden! "
            "Use NetraOptimizerClient instead:\n"
            "from netraoptimizer import NetraOptimizerClient\n"
            "client = NetraOptimizerClient()\n"
            "result = await client.run(command)"
        )
    return original_subprocess_run(cmd, *args, **kwargs)

def enforced_os_system(command):
    if 'claude' in command:
        raise RuntimeError("Direct Claude calls forbidden! Use NetraOptimizerClient")
    return original_os_system(command)

# Apply patches
subprocess.run = enforced_subprocess_run
os.system = enforced_os_system
```

## Integration Examples

### Example 1: Celery Task
```python
# tasks.py
from celery import shared_task
from netraoptimizer import NetraOptimizerClient

optimizer = NetraOptimizerClient()

@shared_task
async def process_claude_task(command, context=None):
    result = await optimizer.run(command, workspace_context=context)
    return {
        'success': result['status'] == 'completed',
        'tokens_used': result['tokens']['total'],
        'cost': result['cost_usd']
    }
```

### Example 2: Django Management Command
```python
# management/commands/run_claude.py
from django.core.management.base import BaseCommand
from netraoptimizer import NetraOptimizerClient
import asyncio

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('command', type=str)

    def handle(self, *args, **options):
        client = NetraOptimizerClient()
        result = asyncio.run(client.run(options['command']))

        self.stdout.write(f"Tokens: {result['tokens']['total']}")
        self.stdout.write(f"Cost: ${result['cost_usd']:.4f}")
```

### Example 3: FastAPI Endpoint
```python
# main.py
from fastapi import FastAPI, BackgroundTasks
from netraoptimizer import NetraOptimizerClient

app = FastAPI()
optimizer = NetraOptimizerClient()

@app.post("/claude/execute")
async def execute_claude(
    command: str,
    background_tasks: BackgroundTasks
):
    # Execute immediately
    result = await optimizer.run(command)

    # Schedule analysis in background
    background_tasks.add_task(analyze_execution, result)

    return result
```

## Common Patterns

### Pattern 1: Singleton Client
```python
class ClaudeService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = NetraOptimizerClient()
        return cls._client
```

### Pattern 2: Dependency Injection
```python
class MyService:
    def __init__(self, claude_client=None):
        self.claude = claude_client or NetraOptimizerClient()
```

### Pattern 3: Context Manager
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def claude_context():
    client = NetraOptimizerClient()
    await client.database_client.initialize()
    try:
        yield client
    finally:
        await client.database_client.close()
```

## Troubleshooting

### Issue: Import Errors
```python
# Error: ModuleNotFoundError: No module named 'netraoptimizer'

# Solution: Ensure package is in PYTHONPATH
import sys
sys.path.insert(0, '/path/to/netra-apex')
```

### Issue: Async/Await Conflicts
```python
# Error: RuntimeWarning: coroutine was never awaited

# Solution: Use asyncio.run() for sync contexts
import asyncio

def sync_wrapper(command):
    return asyncio.run(optimizer.run(command))
```

### Issue: Database Connection
```python
# Error: Cannot connect to database

# Solution: Check environment variables
export NETRA_DB_HOST=localhost
export NETRA_DB_NAME=netra_optimizer
export NETRA_DB_USER=your_user
export NETRA_DB_PASSWORD=your_password
```

## Validation Checklist

After integration, verify:

- [ ] No direct subprocess calls to Claude remain
- [ ] All executions go through NetraOptimizerClient
- [ ] Database is receiving execution records
- [ ] Metrics are being captured correctly
- [ ] No performance degradation
- [ ] Error handling works properly
- [ ] Batch operations use batch_id
- [ ] Context is being captured
- [ ] Tests pass with new implementation
- [ ] Documentation is updated

## Migration Timeline

| Week | Task | Validation |
|------|------|------------|
| 1 | Pilot integration (orchestrator) | Metrics captured |
| 2 | Core services migration | 50% coverage |
| 3 | Background jobs migration | 75% coverage |
| 4 | Complete migration & enforcement | 100% coverage |

---

**Remember**: Every direct Claude call is a missed optimization opportunity. Centralize with NetraOptimizer!