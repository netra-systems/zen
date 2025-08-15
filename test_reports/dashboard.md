# Test Dashboard
Updated: 2025-08-15 13:35:46

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 13:35 | 2 | 0 | 0 | 1 | 📈 |
| 2 | 08/15 13:24 | 4 | 3 | 1 | 0 | 📉 |
| 3 | 08/15 13:19 | 2 | 0 | 0 | 1 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 2 | 0.0% | 29.3s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 1
- **Average Duration**: 26.5s
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
