# Async Pattern Search Prompts and Detection Guide

## Purpose
This document provides comprehensive search prompts and patterns to identify all instances of the async generator/context manager confusion that causes '_AsyncGeneratorContextManager' object has no attribute 'execute' errors.

## Critical Search Prompts for Immediate Issues

### 1. Find Direct Misuse of Async Generators
```bash
# HIGHEST PRIORITY - Will definitely cause errors
# Find async with on generator functions
rg "async with\s+(get_db|get_.*session|get_async.*)\s*\(\)" --type py

# Find specific anti-pattern
rg "async with get_db\(\) as" --type py

# Find in specific directories
rg "async with.*get_db" netra_backend/app/db/ --type py
rg "async with.*get_db" netra_backend/app/core/ --type py
rg "async with.*get_db" netra_backend/app/routes/ --type py
```

### 2. Find Session Getter Misuse
```bash
# Find all potential session getters being used with async with
rg "async with\s+\w+\.(get_session|get_db_session|get_async_session)\(\)" --type py

# Find DatabaseManager usage
rg "async with DatabaseManager\.get" --type py

# Find TransactionHandler usage  
rg "async with TransactionHandler\.get" --type py

# Find self.get_session patterns in classes
rg "async with self\.(get_session|get_db_session)" --type py
```

### 3. Find Execute Calls After Async With
```bash
# This finds the actual error location
rg -B 5 "\.execute\(" --type py | rg -A 5 "async with.*get"

# Find execute in async with blocks
rg -A 10 "async with.*get.*session.*:" --type py | rg "\.execute\("

# Find potential AttributeError locations
rg "async with.*as (\w+):" -r '$1' --type py | xargs -I {} rg "{}.execute" --type py
```

## Intermediate Priority Searches

### 4. Find Context Manager Confusion
```bash
# Find __aenter__ checks (indicates confusion)
rg "hasattr\([^,]+,\s*['\"]__aenter__['\"]" --type py

# Find isinstance checks for context managers
rg "isinstance.*AsyncContextManager" --type py

# Find getattr on __aenter__
rg "getattr\([^,]+,\s*['\"]__aenter__['\"]" --type py
```

### 5. Find Type Hint Issues
```bash
# Find functions that claim to return AsyncContextManager but might return generators
rg "->.*AsyncContextManager\[.*Session\]" --type py

# Find AsyncGenerator declarations to understand which functions are generators
rg "->.*AsyncGenerator\[.*Session" --type py

# Find Union types that might be confusing
rg "Union\[.*AsyncGenerator.*AsyncContextManager\]" --type py
```

### 6. Find Dependency Injection Issues
```bash
# Find FastAPI Depends usage with database
rg "Depends\(get_db\)" --type py
rg "Depends\(get.*session\)" --type py

# Find manual dependency calls (often problematic)
rg "await get_db\(\)" --type py
rg "await get.*session\(\)" --type py

# Find dependency overrides in tests
rg "app\.dependency_overrides\[get_db\]" --type py
```

## Advanced Pattern Detection

### 7. Find Hidden Context Manager Usage
```bash
# Find 'async with await' pattern (double confusion)
rg "async with await" --type py

# Find try/finally blocks that might hide the issue
rg -A 10 "async with.*get.*:" --type py | rg "finally:"

# Find context manager stacking
rg "async with.*,.*get_db" --type py
```

### 8. Find Test Mocking Issues
```bash
# Find mocked database sessions
rg "Mock.*spec=.*Session" --type py -g "test_*.py"
rg "AsyncMock.*spec=.*Session" --type py -g "test_*.py"

# Find patch decorators on database functions
rg "@patch.*get_db" --type py
rg "@mock.*get_db" --type py

# Find test fixtures that might have issues
rg "async def.*fixture.*session" --type py -g "conftest.py"
```

### 9. Find Middleware-Specific Issues
```bash
# Find middleware with database dependencies
rg "class.*Middleware" -A 20 --type py | rg "get_db\|session"

# Find middleware dispatch methods using sessions
rg "async def dispatch" -A 30 --type py | rg "session\|get_db"

# Find call_next wrapping
rg "call_next.*__aenter__" --type py
```

## Repository-Wide Analysis Commands

### 10. Statistical Analysis
```bash
# Count total occurrences of each pattern
echo "=== Async With Get_DB Occurrences ==="
rg "async with.*get_db" --type py -c

echo "=== Async For Get_DB Occurrences (Correct) ==="
rg "async for.*get_db" --type py -c

echo "=== Total Session Execute Calls ==="
rg "session\.execute\(" --type py -c

echo "=== Files with Most Session Usage ==="
rg "session\." --type py -c | sort -t: -k2 -rn | head -20
```

### 11. Find Specific Error Patterns
```bash
# Find error handling that might hide the issue
rg "except.*AttributeError" -A 5 --type py | rg "execute"

# Find logging of the specific error
rg "AsyncGeneratorContextManager" --type py
rg "_AsyncGeneratorContextManager.*execute" --type py

# Find workarounds people might have added
rg "hasattr.*execute" --type py
```

## Interactive Investigation Script

Create `scripts/find_async_issues.py`:

```python
#!/usr/bin/env python3
"""Interactive async pattern issue finder."""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

class AsyncPatternFinder(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.issues = defaultdict(list)
        self.current_function = None
        self.in_async_with = False
        self.async_with_vars = {}
    
    def visit_AsyncFunctionDef(self, node):
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func
    
    def visit_AsyncWith(self, node):
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                func_name = self.get_call_name(item.context_expr)
                if func_name and ('get_db' in func_name or 'session' in func_name):
                    var_name = item.optional_vars.id if item.optional_vars else 'unknown'
                    self.issues['async_with_generator'].append({
                        'line': node.lineno,
                        'function': self.current_function,
                        'pattern': f'async with {func_name}() as {var_name}',
                        'file': self.filename
                    })
                    self.async_with_vars[var_name] = node.lineno
        
        self.in_async_with = True
        self.generic_visit(node)
        self.in_async_with = False
    
    def visit_Attribute(self, node):
        if node.attr == 'execute':
            if isinstance(node.value, ast.Name):
                var_name = node.value.id
                if var_name in self.async_with_vars:
                    self.issues['execute_on_context_manager'].append({
                        'line': node.lineno,
                        'function': self.current_function,
                        'pattern': f'{var_name}.execute() after async with on line {self.async_with_vars[var_name]}',
                        'file': self.filename
                    })
        self.generic_visit(node)
    
    def get_call_name(self, node):
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return None

def analyze_file(filepath: Path) -> Dict[str, List]:
    """Analyze a single file for async pattern issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        finder = AsyncPatternFinder(str(filepath))
        finder.visit(tree)
        return finder.issues
    except Exception as e:
        return {'parse_error': [{'file': str(filepath), 'error': str(e)}]}

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Find async pattern issues')
    parser.add_argument('path', nargs='?', default='netra_backend', help='Path to analyze')
    parser.add_argument('--include-tests', action='store_true', help='Include test files')
    parser.add_argument('--verbose', action='store_true', help='Show all issues')
    
    args = parser.parse_args()
    
    path = Path(args.path)
    all_issues = defaultdict(list)
    
    for filepath in path.rglob('*.py'):
        if not args.include_tests and 'test' in str(filepath):
            continue
        
        file_issues = analyze_file(filepath)
        for issue_type, issues in file_issues.items():
            all_issues[issue_type].extend(issues)
    
    # Report findings
    print("=" * 80)
    print("ASYNC PATTERN ISSUE REPORT")
    print("=" * 80)
    
    if all_issues.get('async_with_generator'):
        print(f"\n⚠️  CRITICAL: async with on generators ({len(all_issues['async_with_generator'])} found)")
        print("-" * 80)
        for issue in all_issues['async_with_generator'][:10 if not args.verbose else None]:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    Function: {issue['function'] or 'module-level'}")
            print(f"    Pattern: {issue['pattern']}")
        if len(all_issues['async_with_generator']) > 10 and not args.verbose:
            print(f"  ... and {len(all_issues['async_with_generator']) - 10} more (use --verbose to see all)")
    
    if all_issues.get('execute_on_context_manager'):
        print(f"\n🔥 CRITICAL: .execute() on potential context managers ({len(all_issues['execute_on_context_manager'])} found)")
        print("-" * 80)
        for issue in all_issues['execute_on_context_manager'][:10 if not args.verbose else None]:
            print(f"  {issue['file']}:{issue['line']}")
            print(f"    Function: {issue['function'] or 'module-level'}")
            print(f"    Pattern: {issue['pattern']}")
    
    if all_issues.get('parse_error'):
        print(f"\n⚠️  Parse errors ({len(all_issues['parse_error'])} files)")
        for issue in all_issues['parse_error'][:5]:
            print(f"  {issue['file']}: {issue['error']}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_issues = sum(len(issues) for issues in all_issues.values() if issues)
    print(f"Total issues found: {total_issues}")
    
    if total_issues > 0:
        print("\n📋 RECOMMENDED ACTIONS:")
        print("1. Fix all 'async with generator' patterns immediately")
        print("2. Review all .execute() calls after async with blocks")
        print("3. Run: python scripts/fix_async_patterns.py --dry-run")
        print("4. Test with: python tests/unified_test_runner.py --real-services")
        return 1
    else:
        print("✅ No async pattern issues found!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
```

## Quick Check Commands

### For CI/CD Pipeline
```bash
# One-liner to check for critical issues
if rg "async with.*get_db\(\)" --type py -q; then echo "❌ CRITICAL: async with get_db() found!"; exit 1; else echo "✅ No direct async with get_db() issues"; fi

# Check for any async with on getters
rg "async with.*get_(db|session|async)" --type py || echo "✅ Clean"
```

### For Pre-commit Hook
```bash
#!/bin/bash
# Add to .git/hooks/pre-commit

echo "Checking for async pattern issues..."

# Check staged files only
git diff --cached --name-only --diff-filter=ACM | grep '\.py$' | while read file; do
    if grep -q "async with.*get_db()" "$file"; then
        echo "❌ ERROR: $file contains 'async with get_db()' pattern"
        echo "  Fix: Use 'async for session in get_db():' instead"
        exit 1
    fi
done

echo "✅ Async patterns check passed"
```

## Common False Positives

### These patterns are OKAY:
```python
# ✅ CORRECT - Context manager returns session directly
async with async_session_maker() as session:  # async_session_maker is a context manager
    await session.execute(query)

# ✅ CORRECT - Using async for with generator
async for session in get_db():  # get_db is a generator
    await session.execute(query)

# ✅ CORRECT - Direct session creation
session = AsyncSession(bind=engine)
await session.execute(query)
```

### These patterns are PROBLEMATIC:
```python
# ❌ WRONG - Generator used as context manager
async with get_db() as session:  # get_db returns AsyncGenerator
    await session.execute(query)  # ERROR: AttributeError

# ❌ WRONG - Await on generator
session = await get_db()  # Can't await a generator
await session.execute(query)

# ❌ WRONG - Missing async iteration
session = get_db()  # This is a generator object, not a session
await session.execute(query)  # ERROR: generator has no execute
```

## Automated Monitoring

Add to your monitoring system:
```python
# Log pattern to watch for
error_pattern = r"'_AsyncGeneratorContextManager' object has no attribute 'execute'"

# Alert condition
if error_pattern in log_line:
    send_alert("Critical: Async pattern issue detected", {
        'pattern': 'AsyncGeneratorContextManager.execute error',
        'likely_cause': 'async with used on generator function',
        'fix': 'Change async with get_db() to async for session in get_db()',
        'severity': 'CRITICAL'
    })
```

## Usage Instructions

1. **Immediate Action**: Run searches 1-3 to find critical issues
2. **Comprehensive Audit**: Run searches 4-9 for thorough analysis
3. **Automated Check**: Use the interactive script for detailed report
4. **CI Integration**: Add quick check commands to CI pipeline
5. **Prevention**: Install pre-commit hook to catch new issues

## Expected Output

After running all searches, you should have:
- List of all files with `async with get_db()` patterns
- List of all potential session getter misuses
- Identification of where .execute() errors would occur
- Understanding of which tests might be hiding issues
- Full picture of async pattern usage in codebase