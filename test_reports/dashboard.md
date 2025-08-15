# Test Dashboard
Updated: 2025-08-14 21:53:04

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/14 21:53 | 321 | 297 | 3 | 20 | ➡️ |
| 2 | 08/14 21:38 | 244 | 222 | 3 | 0 | ➡️ |
| 3 | 08/14 21:29 | 135 | 128 | 3 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 321 | 92.5% | 30.0s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 9
- **Average Duration**: 10.1s
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
