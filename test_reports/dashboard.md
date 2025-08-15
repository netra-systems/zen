# Test Dashboard
Updated: 2025-08-15 13:24:28

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 13:24 | 4 | 3 | 1 | 0 | 📉 |
| 2 | 08/15 13:19 | 2 | 0 | 0 | 1 | 📈 |
| 3 | 08/15 13:11 | 702 | 679 | 1 | 21 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 4 | 75.0% | 27.3s |
| Frontend | ❌ | 0 | 0.0% | 0.5s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 34.9s
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
