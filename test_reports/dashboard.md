# Test Dashboard
Updated: 2025-08-14 17:15:15

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/14 17:15 | 176 | 164 | 3 | 8 | 📉 |
| 2 | 08/14 17:15 | 20 | 16 | 1 | 0 | 📈 |
| 3 | 08/14 17:14 | 17 | 13 | 3 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 176 | 93.2% | 34.1s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 7
- **Average Duration**: 11.5s
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
