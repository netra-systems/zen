# Test Dashboard
**Level**: integration | **Time**: 2025-08-17 17:40:45

## Overall Status: ❌ Failed - 2 test(s) failed

## Component Summary

| Component | Status | Tests | Passed | Failed | Errors | Import Errors | Duration |
|-----------|--------|-------|--------|--------|--------|---------------|----------|
| Backend | ❌ failed | 44 | 42 | 2 | 0 | 0 | 30.57s |
| Frontend | ⚫ collection_failed | 0 | 0 | 0 | 0 | 0 | 0.14s |
| E2E | ⚫ collection_failed | 0 | 0 | 0 | 0 | 0 | 0.00s |

## 🔴 Issues Detected

- backend: 2 test(s) failed
- frontend: Test collection failed
- e2e: Test collection failed

## Statistics

- **Total Tests**: 44
- **Passed**: 42
- **Failed**: 2
- **Errors**: 0
- **Skipped**: 0
- **Total Duration**: 30.72s
- **Pass Rate**: 95.5%

## Quick Actions

```bash
# Run specific test levels
python test_runner.py --level unit
python test_runner.py --level smoke
python test_runner.py --level comprehensive
```
