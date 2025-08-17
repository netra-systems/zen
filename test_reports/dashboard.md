# Test Dashboard
Updated: 2025-08-17 10:39:48

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/17 10:39 | 721 | 700 | 2 | 19 | ➡️ |
| 2 | 08/17 10:36 | 814 | 793 | 2 | 19 | ➡️ |
| 3 | 08/17 10:31 | 822 | 799 | 2 | 21 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 721 | 97.1% | 105.3s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 6
- **Average Duration**: 84.4s
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
