# Test Dashboard
Updated: 2025-08-15 21:08:03

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 21:08 | 1127 | 1102 | 1 | 23 | 📉 |
| 2 | 08/15 21:06 | 1 | 0 | 0 | 0 | 📈 |
| 3 | 08/15 21:05 | 4 | 3 | 1 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 1127 | 97.8% | 73.0s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 41.3s
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
