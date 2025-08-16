# Test Dashboard
Updated: 2025-08-15 21:11:42

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 21:11 | 832 | 809 | 1 | 22 | ➡️ |
| 2 | 08/15 21:09 | 1141 | 1116 | 1 | 23 | 📉 |
| 3 | 08/15 21:08 | 7 | 7 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 832 | 97.2% | 74.2s |
| Frontend | ❌ | 0 | 0.0% | 0.4s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 51.1s
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
