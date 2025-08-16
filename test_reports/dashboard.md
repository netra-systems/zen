# Test Dashboard
Updated: 2025-08-16 06:17:51

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/16 06:17 | 799 | 775 | 1 | 23 | 📉 |
| 2 | 08/16 00:02 | 0 | 0 | 0 | 0 | 📈 |
| 3 | 08/16 00:01 | 799 | 775 | 1 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 799 | 97.0% | 68.0s |
| Frontend | ❌ | 0 | 0.0% | 0.2s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 49.6s
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
