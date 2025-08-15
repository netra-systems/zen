# Test Dashboard
Updated: 2025-08-15 13:45:17

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 13:45 | 521 | 499 | 3 | 19 | ➡️ |
| 2 | 08/15 13:41 | 37 | 33 | 3 | 1 | 📉 |
| 3 | 08/15 13:40 | 2 | 0 | 0 | 1 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 521 | 95.8% | 56.9s |
| Frontend | ❌ | 0 | 0.0% | 0.5s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 6
- **Average Duration**: 38.4s
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
