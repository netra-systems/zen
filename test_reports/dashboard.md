# Test Dashboard
Updated: 2025-08-17 18:12:34

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/17 18:12 | 408 | 395 | 3 | 10 | 📉 |
| 2 | 08/17 18:11 | 1 | 0 | 0 | 0 | ➡️ |
| 3 | 08/17 18:10 | 2 | 0 | 0 | 1 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 408 | 96.8% | 48.3s |
| Frontend | ❌ | 0 | 0.0% | 0.1s |
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
