# Test Dashboard
Updated: 2025-08-15 15:13:51

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 15:13 | 957 | 936 | 2 | 19 | ➡️ |
| 2 | 08/15 15:11 | 958 | 936 | 2 | 19 | ➡️ |
| 3 | 08/15 14:59 | 1072 | 1046 | 2 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 957 | 97.8% | 51.1s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 6
- **Average Duration**: 58.9s
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
