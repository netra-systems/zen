# Test Dashboard
Updated: 2025-08-15 14:36:03

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 14:36 | 1042 | 1018 | 3 | 21 | ➡️ |
| 2 | 08/15 14:34 | 1038 | 1014 | 3 | 21 | 📉 |
| 3 | 08/15 14:34 | 1041 | 1016 | 2 | 22 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 1042 | 97.7% | 55.9s |
| Frontend | ❌ | 0 | 0.0% | 0.4s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 8
- **Average Duration**: 59.4s
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
