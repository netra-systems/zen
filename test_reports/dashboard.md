# Test Dashboard
Updated: 2025-08-15 17:45:17

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 17:45 | 799 | 779 | 1 | 19 | ➡️ |
| 2 | 08/15 17:43 | 702 | 678 | 1 | 23 | ➡️ |
| 3 | 08/15 17:42 | 1079 | 1054 | 1 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 799 | 97.5% | 50.2s |
| Frontend | ❌ | 0 | 0.0% | 1.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 3
- **Average Duration**: 59.0s
- **Flaky Tests**: 0

## Quick Actions

```bash
# Run smoke tests
python test_runner.py --level smoke

# Run comprehensive tests
python test_runner.py --level comprehensive

# View critical changes
cat test_reports/latest/critical_changes.md
```
