# Test Dashboard
**Level**: unit | **Time**: 2025-08-17 17:48:50

## Overall Status: ❌ Failed - 1 test(s) failed

## Component Summary

| Component | Status | Tests | Passed | Failed | Errors | Import Errors | Duration |
|-----------|--------|-------|--------|--------|--------|---------------|----------|
| Backend | ❌ failed | 41 | 39 | 1 | 0 | 0 | 41.63s |
| Frontend | ⚫ collection_failed | 0 | 0 | 0 | 0 | 0 | 0.00s |
| E2E | ⚫ collection_failed | 0 | 0 | 0 | 0 | 0 | 0.00s |

## 🔴 Issues Detected

- backend: 1 test(s) failed
- frontend: Test collection failed
- e2e: Test collection failed

## Statistics

- **Total Tests**: 41
- **Passed**: 39
- **Failed**: 1
- **Errors**: 0
- **Skipped**: 1
- **Total Duration**: 41.63s
- **Pass Rate**: 95.1%

## Quick Actions

```bash
# Run specific test levels
python test_runner.py --level unit
python test_runner.py --level smoke
python test_runner.py --level comprehensive
```
