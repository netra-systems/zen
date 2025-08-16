# Test Dashboard
Updated: 2025-08-15 20:41:48

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 20:41 | 1125 | 1100 | 1 | 23 | 📉 |
| 2 | 08/15 20:39 | 7 | 7 | 0 | 0 | 📈 |
| 3 | 08/15 20:39 | 1123 | 1098 | 1 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 1125 | 97.8% | 83.3s |
| Frontend | ❌ | 0 | 0.0% | 0.4s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 58.5s
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
