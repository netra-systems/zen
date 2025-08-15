# Test Dashboard
Updated: 2025-08-15 10:58:12

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 10:58 | 754 | 729 | 3 | 21 | 📉 |
| 2 | 08/15 10:48 | 780 | 757 | 2 | 21 | 📉 |
| 3 | 08/15 10:43 | 7 | 7 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 754 | 96.7% | 47.6s |
| Frontend | ❌ | 0 | 0.0% | 0.4s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 5
- **Average Duration**: 33.5s
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
