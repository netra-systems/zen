# Test Dashboard
Updated: 2025-08-16 06:39:19

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/16 06:39 | 811 | 787 | 1 | 23 | ➡️ |
| 2 | 08/16 06:37 | 811 | 787 | 1 | 23 | 📉 |
| 3 | 08/16 06:36 | 35 | 34 | 0 | 1 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 811 | 97.0% | 67.0s |
| Frontend | ❌ | 0 | 0.0% | 0.2s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 68.0s
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
