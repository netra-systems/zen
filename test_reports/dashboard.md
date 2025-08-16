# Test Dashboard
Updated: 2025-08-15 20:37:45

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 20:37 | 782 | 762 | 1 | 19 | 📉 |
| 2 | 08/15 20:36 | 7 | 7 | 0 | 0 | 📈 |
| 3 | 08/15 20:36 | 784 | 764 | 1 | 19 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 782 | 97.4% | 60.3s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 53.6s
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
