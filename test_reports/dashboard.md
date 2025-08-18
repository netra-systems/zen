# Test Dashboard
**Level**: unit | **Time**: 2025-08-17 18:41:25

## Overall Status: ❌ Failed - 3 test(s) failed

## Component Summary

| Component | Status | Tests | Passed | Failed | Errors | Import Errors | Duration |
|-----------|--------|-------|--------|--------|--------|---------------|----------|
| Backend | ❌ failed | 408 | 395 | 3 | 0 | 0 | 53.83s |
| Frontend | ❌ failed | 0 | 0 | 0 | 0 | 0 | 0.28s |
| E2E | ⚠️ pending | 0 | 0 | 0 | 0 | 0 | 0.00s |

## Test Categories

| Category | Description | Expected | Actual | Status | Last Success |
|----------|-------------|----------|--------|--------|--------------|
| smoke | Quick smoke tests | 10 | 0 | ⚪ | Never |
| unit | Unit tests | 100 | 0 | ⚪ | Never |
| integration | Integration tests | 50 | 0 | ⚪ | Never |
| critical | Critical path tests | 20 | 0 | ⚪ | Never |
| agents | Agent tests | 30 | 0 | ⚪ | Never |
| websocket | WebSocket tests | 15 | 0 | ⚪ | Never |
| database | Database tests | 25 | 0 | ⚪ | Never |
| api | API tests | 40 | 0 | ⚪ | Never |
| e2e | End-to-end tests | 20 | 0 | ⚪ | Never |
| real_services | Real service tests | 15 | 0 | ⚪ | Never |

## 🔴 Issues Detected

- backend: 3 test(s) failed

## Statistics

- **Total Tests**: 408
- **Passed**: 395
- **Failed**: 3
- **Errors**: 0
- **Skipped**: 10
- **Total Duration**: 54.10s
- **Pass Rate**: 96.8%

## Available Test Levels

| Level | Command | Purpose |
|-------|---------|---------|
| smoke | `python test_runner.py --level smoke` | See test_config.py |
| unit | `python test_runner.py --level unit` | See test_config.py |
| agents | `python test_runner.py --level agents` | See test_config.py |
| integration | `python test_runner.py --level integration` | See test_config.py |
| critical | `python test_runner.py --level critical` | See test_config.py |
| ... | See all levels with `python test_runner.py --list` | ... |

## Quick Actions

```bash
# Run specific test levels
python test_runner.py --level unit
python test_runner.py --level smoke
python test_runner.py --level comprehensive

# List all available tests
python test_runner.py --list

# Run failing tests
python test_runner.py --run-failing
```
