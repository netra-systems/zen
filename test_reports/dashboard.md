# Test Dashboard
**Level**: smoke | **Time**: 2025-08-17 18:52:55

## Overall Status: ✅ All tests passed

## Component Summary

| Component | Status | Tests | Passed | Failed | Errors | Import Errors | Duration |
|-----------|--------|-------|--------|--------|--------|---------------|----------|
| Backend | ✅ passed | 7 | 7 | 0 | 0 | 0 | 7.79s |
| Frontend | ⚠️ skipped | 0 | 0 | 0 | 0 | 0 | 0.00s |
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

## Statistics

- **Total Tests**: 7
- **Passed**: 7
- **Failed**: 0
- **Errors**: 0
- **Skipped**: 0
- **Total Duration**: 7.79s
- **Pass Rate**: 100.0%

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
