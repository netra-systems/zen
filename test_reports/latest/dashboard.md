# Test Dashboard
**Level**: integration | **Time**: 2025-08-17 17:53:40

## Overall Status: 🔴 Import Errors - Tests Cannot Run

## Component Summary

| Component | Status | Tests | Passed | Failed | Errors | Import Errors | Duration |
|-----------|--------|-------|--------|--------|--------|---------------|----------|
| Backend | 🔴 import_error | 0 | 0 | 0 | 0 | 40 | 110.94s |
| Frontend | ⚫ collection_failed | 0 | 0 | 0 | 0 | 0 | 0.00s |
| E2E | ⚫ collection_failed | 0 | 0 | 0 | 0 | 0 | 0.00s |

## 🔴 Issues Detected

- backend: 40 import error(s)
- frontend: Test collection failed
- e2e: Test collection failed

## Statistics

- **Total Tests**: 0
- **Passed**: 0
- **Failed**: 0
- **Errors**: 0
- **Skipped**: 0
- **Total Duration**: 110.94s

## Quick Actions

```bash
# Fix import errors first
python -m pip install -r requirements.txt
python scripts/check_imports.py

# Run specific test levels
python test_runner.py --level unit
python test_runner.py --level smoke
python test_runner.py --level comprehensive
```
