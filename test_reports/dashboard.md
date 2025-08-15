# Test Dashboard
Updated: 2025-08-15 14:12:53

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 14:12 | 85 | 85 | 0 | 0 | 📈 |
| 2 | 08/15 14:12 | 520 | 499 | 2 | 19 | 📈 |
| 3 | 08/15 14:10 | 521 | 499 | 3 | 19 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 85 | 100.0% | 33.7s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 5
- **Average Duration**: 49.1s
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
