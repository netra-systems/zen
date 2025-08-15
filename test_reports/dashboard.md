# Test Dashboard
Updated: 2025-08-15 14:22:29

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 14:22 | 520 | 499 | 2 | 19 | ➡️ |
| 2 | 08/15 14:18 | 520 | 499 | 2 | 19 | 📉 |
| 3 | 08/15 14:13 | 7 | 7 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 520 | 96.0% | 36.9s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 4
- **Average Duration**: 26.7s
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
