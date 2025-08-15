# Test Dashboard
Updated: 2025-08-15 10:41:02

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 10:41 | 56 | 54 | 0 | 2 | 📈 |
| 2 | 08/15 10:40 | 12 | 10 | 2 | 0 | ➡️ |
| 3 | 08/15 10:39 | 776 | 753 | 2 | 21 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ✅ | 56 | 96.4% | 17.4s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 4
- **Average Duration**: 40.6s
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
