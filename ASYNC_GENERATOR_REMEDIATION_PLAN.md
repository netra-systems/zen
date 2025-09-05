# Async Generator Context Manager Remediation Plan

## Executive Summary
This remediation plan addresses the systematic misuse of async generators as async context managers throughout the Netra codebase, which causes '_AsyncGeneratorContextManager' object has no attribute 'execute' errors and SecurityResponseMiddleware bypasses.

## Critical Issues Identified

### 1. Direct `async with get_db()` Usage (HIGH PRIORITY)
**Files with confirmed issues:**
- `netra_backend/app/db/postgres_session.py:168`
- `netra_backend/tests/integration/critical_paths/test_integration_failures_audit.py`
- `netra_backend/tests/unit/test_database_dependencies.py`

### 2. Potential Context Manager Confusion (MEDIUM PRIORITY)
**Files using `async with` on session getters:**
- `netra_backend/app/core/health_checkers.py` - Multiple uses with DatabaseManager.get_async_session
- `netra_backend/app/core/interfaces_repository.py` - 6+ instances with self.get_db_session()
- `netra_backend/app/database/__init__.py` - DatabaseManager.get_async_session usage
- `netra_backend/app/db/client_postgres.py` - TransactionHandler.get_session()
- `netra_backend/app/db/client_postgres_executors.py` - Multiple TransactionHandler.get_session()
- `netra_backend/app/db/database_manager.py` - DatabaseManager.get_async_session usage
- `netra_backend/app/db/postgres.py` - get_async_db usage
- `netra_backend/app/db/postgres_cloud.py` - cloud_db.get_session()
- `netra_backend/app/db/postgres_core.py` - self.get_session()

### 3. Middleware Pattern Issues (LOW PRIORITY - Tests Only)
**Files checking for __aenter__:**
- Tests only (regression and unit tests) - No production code affected

## Remediation Steps

### Phase 1: Immediate Critical Fixes (Day 1)

#### 1.1 Fix Direct `async with get_db()` Patterns
```python
# File: netra_backend/app/db/postgres_session.py:168
# BEFORE:
async with get_db() as session:
    # use session

# AFTER:
async for session in get_db():
    try:
        # use session
        break  # Only need one session
    finally:
        await session.close()
```

#### 1.2 Create Helper Function for Single Session Use
```python
# Add to netra_backend/app/database/__init__.py
async def get_single_session() -> AsyncSession:
    """Get a single database session for one-off operations."""
    async for session in get_db():
        return session
    raise RuntimeError("Failed to get database session")
```

### Phase 2: Audit Session Getter Methods (Day 2)

#### 2.1 Verify Each Session Getter's Return Type
For each method listed in "Potential Context Manager Confusion", verify:
1. Does it return `AsyncGenerator[AsyncSession, None]`?
2. Does it return `AsyncContextManager[AsyncSession]`?
3. Does it return `AsyncSession` directly?

#### 2.2 Apply Correct Pattern Based on Return Type
```python
# For AsyncGenerator - use async for
async for session in get_generator():
    # use session
    break

# For AsyncContextManager - use async with
async with get_context_manager() as session:
    # use session

# For direct AsyncSession - use directly
session = await get_session()
# use session
```

### Phase 3: Add Runtime Validation (Day 3)

#### 3.1 Create Session Validator Decorator
```python
# Add to netra_backend/app/db/session_validator.py
from functools import wraps
from typing import TypeVar, Callable
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

def validate_session_type(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to validate session is AsyncSession, not context manager."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if 'session' in kwargs:
            session = kwargs['session']
            if not hasattr(session, 'execute'):
                raise TypeError(
                    f"Expected AsyncSession with execute method, got {type(session).__name__}. "
                    f"This usually means async with was used on an async generator."
                )
        return result
    return wrapper
```

#### 3.2 Apply Validator to Critical Paths
```python
# Apply to repository methods
@validate_session_type
async def create_thread(self, session: AsyncSession, ...):
    result = await session.execute(query)  # Will catch wrong type early
```

### Phase 4: Testing and Verification (Day 4)

#### 4.1 Create Comprehensive Test Suite
```python
# Create: netra_backend/tests/integration/test_async_pattern_validation.py
import pytest
from netra_backend.app.database import get_db

class TestAsyncPatterns:
    @pytest.mark.asyncio
    async def test_generator_pattern_correct(self):
        """Test correct async generator usage."""
        async for session in get_db():
            assert hasattr(session, 'execute')
            result = await session.execute("SELECT 1")
            assert result is not None
            break
    
    @pytest.mark.asyncio
    async def test_generator_pattern_incorrect_fails(self):
        """Test that async with on generator fails properly."""
        with pytest.raises(AttributeError, match="__aenter__"):
            async with get_db() as session:
                pass
    
    @pytest.mark.asyncio
    async def test_context_manager_detection(self):
        """Test that we can detect context manager vs generator."""
        from netra_backend.app.database import get_db
        gen = get_db()
        assert not hasattr(gen, '__aenter__')
        assert hasattr(gen, '__anext__')
```

#### 4.2 Run Full Test Suite with Real Services
```bash
# Run with real database to catch integration issues
python tests/unified_test_runner.py --real-services --category integration
```

### Phase 5: Prevention Measures (Ongoing)

#### 5.1 Add Pre-commit Hook
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: check-async-patterns
      name: Check Async Patterns
      entry: python scripts/check_async_patterns.py
      language: python
      files: \.py$
```

#### 5.2 Create Pattern Checker Script
```python
# scripts/check_async_patterns.py
import ast
import sys
from pathlib import Path

class AsyncPatternChecker(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
    
    def visit_AsyncWith(self, node):
        # Check for problematic patterns
        if isinstance(node.items[0].context_expr, ast.Call):
            func = node.items[0].context_expr
            if hasattr(func.func, 'id') and 'get_db' in func.func.id:
                self.errors.append(f"Line {node.lineno}: async with {func.func.id}() detected")
        self.generic_visit(node)

def check_file(filepath):
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    checker = AsyncPatternChecker()
    checker.visit(tree)
    return checker.errors

if __name__ == '__main__':
    errors = []
    for filepath in Path('netra_backend').rglob('*.py'):
        file_errors = check_file(filepath)
        if file_errors:
            errors.extend([f"{filepath}: {e}" for e in file_errors])
    
    if errors:
        print("Async pattern issues found:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
```

## Search Prompts for Identifying Additional Issues

### Prompt 1: Find Direct Async With on Generators
```bash
# Find all async with get_db patterns
rg "async with\s+(get_db|get_.*session|get_async.*)\s*\(\)" --type py

# Find async with on any getter function
rg "async with\s+\w+\.get_\w+\(\)" --type py
```

### Prompt 2: Find Context Manager Checks
```bash
# Find hasattr __aenter__ checks
rg "hasattr\([^,]+,\s*['\"]__aenter__['\"]" --type py

# Find isinstance AsyncContextManager checks  
rg "isinstance.*AsyncContextManager" --type py
```

### Prompt 3: Find Execute Calls That Might Fail
```bash
# Find .execute( calls that aren't on obvious sessions
rg "(?<!session)(?<!db)(?<!cursor)\.execute\(" --type py

# Find execute after async with
rg -A 5 "async with.*get_.*\(\)" --type py | rg "\.execute\("
```

### Prompt 4: Find Generator Type Hints
```bash
# Find AsyncGenerator type hints to verify return types
rg "AsyncGenerator\[.*Session" --type py

# Find functions that should return generators
rg "def get_.*session.*->.*AsyncGenerator" --type py
```

### Prompt 5: Find Potential Mock Issues
```bash
# Find test mocks that might cause issues
rg "mock.*get_db|patch.*get_db" --type py -g "test_*.py"

# Find AsyncMock usage with sessions
rg "AsyncMock.*spec.*Session" --type py
```

## Automated Fix Script

```python
#!/usr/bin/env python3
"""
Automated fixer for async generator pattern issues.
Usage: python fix_async_patterns.py [--dry-run] [--backup]
"""

import re
import argparse
from pathlib import Path
from typing import List, Tuple

class AsyncPatternFixer:
    def __init__(self, dry_run=False, backup=False):
        self.dry_run = dry_run
        self.backup = backup
        self.fixes_applied = []
    
    def fix_file(self, filepath: Path) -> List[Tuple[int, str, str]]:
        """Fix async patterns in a single file."""
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        fixes = []
        for i, line in enumerate(lines):
            # Pattern 1: async with get_db() as session:
            match = re.match(r'(\s*)async with get_db\(\) as (\w+):', line)
            if match:
                indent = match.group(1)
                var_name = match.group(2)
                new_line = f'{indent}async for {var_name} in get_db():\n'
                fixes.append((i, line.rstrip(), new_line.rstrip()))
                lines[i] = new_line
                
                # Add break after the block if not present
                # (This is simplified - real implementation would need proper AST parsing)
        
        if fixes and not self.dry_run:
            if self.backup:
                backup_path = filepath.with_suffix('.py.bak')
                filepath.rename(backup_path)
                filepath = backup_path.with_suffix('')
            
            with open(filepath, 'w') as f:
                f.writelines(lines)
        
        return fixes
    
    def run(self, directory: Path):
        """Run fixer on all Python files in directory."""
        for filepath in directory.rglob('*.py'):
            if 'test' in str(filepath):
                continue  # Skip test files for now
            
            fixes = self.fix_file(filepath)
            if fixes:
                print(f"\n{filepath}:")
                for line_no, old, new in fixes:
                    print(f"  Line {line_no + 1}:")
                    print(f"    - {old}")
                    print(f"    + {new}")
                
                self.fixes_applied.extend([(filepath, f) for f in fixes])
        
        print(f"\nTotal fixes: {len(self.fixes_applied)}")
        if self.dry_run:
            print("(Dry run - no files modified)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fix async pattern issues')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    parser.add_argument('--backup', action='store_true', help='Create backup files')
    parser.add_argument('--path', default='netra_backend', help='Path to scan')
    
    args = parser.parse_args()
    
    fixer = AsyncPatternFixer(dry_run=args.dry_run, backup=args.backup)
    fixer.run(Path(args.path))
```

## Monitoring and Alerting

### Add Logging for Pattern Detection
```python
# Add to netra_backend/app/middleware/async_pattern_monitor.py
import logging
from typing import Any

logger = logging.getLogger(__name__)

class AsyncPatternMonitor:
    @staticmethod
    def check_session(obj: Any, context: str) -> None:
        """Log warning if object looks like wrong type."""
        if hasattr(obj, '__aenter__') and not hasattr(obj, 'execute'):
            logger.error(
                f"Potential async pattern issue in {context}: "
                f"Object has __aenter__ but no execute method. "
                f"Type: {type(obj).__name__}"
            )
        elif type(obj).__name__ == '_AsyncGeneratorContextManager':
            logger.error(
                f"CRITICAL: AsyncGeneratorContextManager detected in {context}! "
                f"This will cause execute() AttributeError. "
                f"Fix: Use 'async for' instead of 'async with' on generators."
            )
```

## Timeline

- **Day 1**: Fix critical issues in postgres_session.py and test files
- **Day 2**: Audit and fix session getter methods
- **Day 3**: Implement runtime validation
- **Day 4**: Run comprehensive tests
- **Week 2**: Deploy monitoring and prevention measures
- **Ongoing**: Regular audits using search prompts

## Success Criteria

1. No '_AsyncGeneratorContextManager' errors in logs
2. SecurityResponseMiddleware no longer bypassed due to this error
3. All tests pass with real database services
4. Pattern checker finds no issues in production code
5. Monitoring shows no async pattern warnings for 7 days

## Risk Mitigation

1. **Test in staging first** - Deploy fixes incrementally
2. **Keep backups** - Use automated fixer with --backup flag
3. **Monitor closely** - Watch error rates after each fix
4. **Rollback plan** - Git commits for each phase allow easy reversion
5. **Communication** - Alert team about pattern requirements