# Test Dashboard
Updated: 2025-08-15 13:11:59

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 13:11 | 702 | 679 | 1 | 21 | 📈 |
| 2 | 08/15 12:51 | 1039 | 1015 | 3 | 21 | ➡️ |
| 3 | 08/15 12:04 | 1038 | 1014 | 3 | 21 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 702 | 96.7% | 54.2s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 7
- **Average Duration**: 51.3s
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
