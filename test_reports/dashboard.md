# Test Dashboard
Updated: 2025-08-15 22:27:13

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 22:27 | 327 | 309 | 3 | 15 | 📉 |
| 2 | 08/15 21:27 | 0 | 0 | 0 | 0 | ➡️ |
| 3 | 08/15 21:27 | 0 | 0 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 327 | 94.5% | 69.0s |
| Frontend | ❌ | 0 | 0.0% | 0.2s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 3
- **Average Duration**: 26.2s
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
