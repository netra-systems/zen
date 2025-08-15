# Test Dashboard
Updated: 2025-08-15 14:45:08

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 14:45 | 0 | 0 | 0 | 0 | 📈 |
| 2 | 08/15 14:42 | 1068 | 1041 | 3 | 23 | 📉 |
| 3 | 08/15 14:40 | 959 | 936 | 2 | 21 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 0 | 0.0% | 0.0s |
| Frontend | ❌ | 0 | 0.0% | 0.2s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 5
- **Average Duration**: 40.5s
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
