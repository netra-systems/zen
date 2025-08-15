# Test Dashboard
Updated: 2025-08-15 12:04:20

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 12:04 | 1038 | 1014 | 3 | 21 | 📉 |
| 2 | 08/15 11:55 | 0 | 0 | 0 | 0 | 📈 |
| 3 | 08/15 11:55 | 1038 | 1014 | 3 | 21 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 1038 | 97.7% | 47.5s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 6
- **Average Duration**: 48.2s
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
