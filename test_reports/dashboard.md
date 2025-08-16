# Test Dashboard
Updated: 2025-08-16 09:35:14

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/16 09:35 | 549 | 528 | 2 | 19 | ➡️ |
| 2 | 08/16 09:07 | 549 | 528 | 2 | 19 | ➡️ |
| 3 | 08/16 08:27 | 665 | 640 | 2 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 549 | 96.2% | 73.1s |
| Frontend | ❌ | 0 | 0.0% | 0.5s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 6
- **Average Duration**: 72.7s
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
