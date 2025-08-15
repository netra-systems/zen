# Test Dashboard
Updated: 2025-08-15 11:55:02

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 11:55 | 0 | 0 | 0 | 0 | 📈 |
| 2 | 08/15 11:55 | 1038 | 1014 | 3 | 21 | 📉 |
| 3 | 08/15 18:53 | 0 | 0 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 0 | 0.0% | 44.5s |
| Frontend | ❌ | 0 | 0.0% | 0.4s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 3
- **Average Duration**: 34.4s
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
