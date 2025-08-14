# Test Dashboard
Updated: 2025-08-14 16:49:47

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/14 16:49 | 4 | 0 | 0 | 0 | 📈 |
| 2 | 08/14 16:49 | 9 | 5 | 4 | 0 | 📉 |
| 3 | 08/14 16:49 | 2 | 0 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 4 | 0.0% | 46.1s |
| Frontend | ❌ | 0 | 0.0% | 0.6s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 4
- **Average Duration**: 15.5s
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
