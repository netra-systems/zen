# Test Dashboard
Updated: 2025-08-15 23:30:46

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 23:30 | 0 | 0 | 0 | 0 | 📈 |
| 2 | 08/15 23:30 | 435 | 416 | 2 | 17 | 📉 |
| 3 | 08/15 23:27 | 799 | 775 | 1 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 0 | 0.0% | 32.1s |
| Frontend | ❌ | 0 | 0.0% | 0.9s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 3
- **Average Duration**: 70.4s
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
