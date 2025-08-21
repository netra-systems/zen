# Import Testing System

## Overview

The Import Testing System provides fast-fail import validation to catch import errors early in the development cycle. It helps identify:
- Missing dependencies
- Circular imports
- Syntax errors in modules
- Module not found errors
- Other import-related issues

## Features

- **Fast-Fail Mode**: Stops on first critical import error for quick feedback
- **Comprehensive Testing**: Can test all modules recursively
- **Clear Error Reporting**: Provides actionable error messages with troubleshooting steps
- **JSON Reports**: Generates detailed reports for CI/CD integration
- **Performance Tracking**: Measures import times to identify slow imports

## Usage

### Via Test Runner

```bash
# Run import tests before main test suite (fast-fail)
python -m test_framework.test_runner --import-test

# Run ONLY import tests
python -m test_framework.test_runner --import-only
```

### Via Standalone Script

```bash
# Quick critical import test (default)
python scripts/test_imports.py

# Comprehensive import test
python scripts/test_imports.py --all

# Test specific module
python scripts/test_imports.py --module netra_backend.app.services

# Verbose output
python scripts/test_imports.py --verbose

# Save JSON report
python scripts/test_imports.py --json import_report.json
```

### In Python Tests

```python
import pytest
from test_framework.import_tester import ImportTester

def test_critical_imports():
    tester = ImportTester()
    result = tester.test_module('netra_backend.app.main')
    assert result.success, f"Import failed: {result.error_message}"
```

## Error Types

The system detects and reports different types of import errors:

### 1. ModuleNotFoundError
- Missing dependencies
- Incorrect module paths
- Missing __init__.py files

### 2. ImportError
- Circular imports
- Partial initialization issues
- Name conflicts

### 3. SyntaxError
- Invalid Python syntax in modules
- Indentation errors
- Missing colons or parentheses

### 4. Other Exceptions
- Attribute errors during import
- Type errors in module initialization
- Runtime errors in module-level code

## Troubleshooting Guide

### Common Issues and Solutions

1. **Missing Dependencies**
   ```
   Error: No module named 'some_package'
   Solution: pip install some_package
   ```

2. **Circular Imports**
   ```
   Error: cannot import name 'X' from partially initialized module
   Solution: Restructure imports to avoid circular dependencies
   ```

3. **Syntax Errors**
   ```
   Error: SyntaxError at line 42
   Solution: Fix the syntax error in the specified file and line
   ```

4. **Path Issues**
   ```
   Error: No module named 'netra_backend'
   Solution: Ensure Python path includes project root
   ```

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Import Tests
  run: |
    python scripts/test_imports.py --json import_report.json
  continue-on-error: false

- name: Upload Import Report
  if: always()
  uses: actions/upload-artifact@v2
  with:
    name: import-test-report
    path: import_report.json
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: import-test
        name: Import Test
        entry: python scripts/test_imports.py
        language: system
        pass_filenames: false
        always_run: true
```

## Performance Considerations

- Fast-fail mode typically completes in < 5 seconds
- Comprehensive testing may take 30-60 seconds for large codebases
- Import times > 2 seconds indicate potential performance issues
- Use `--verbose` to identify slow-importing modules

## Best Practices

1. **Run import tests first** - They're fast and catch common errors
2. **Use fast-fail in development** - Quick feedback loop
3. **Use comprehensive mode in CI** - Catch all issues before merge
4. **Fix import errors immediately** - They block all other tests
5. **Monitor import times** - Slow imports affect application startup

## Architecture

The import testing system consists of:

1. **ImportTester**: Core testing class
2. **ImportResult**: Result data structure
3. **ImportTestReport**: Aggregated report generator
4. **Test Runner Integration**: Hooks in main test runner
5. **Standalone Script**: Direct command-line access

## Configuration

Import tests can be configured through:

1. **Critical Modules List**: Define which modules are critical
2. **Timeout Settings**: Set maximum import time
3. **Recursive Depth**: Control how deep to test
4. **Exclusion Patterns**: Skip certain modules/patterns

## Limitations

- Cannot detect runtime import errors that occur after module initialization
- May not catch all conditional imports
- Dynamic imports (importlib) require special handling
- Some circular imports may only manifest under specific conditions