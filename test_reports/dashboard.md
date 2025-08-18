# Test Dashboard
Updated: 2025-08-17 18:07:47

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/17 18:07 | 2 | 0 | 0 | 1 | ➡️ |
| 2 | 08/17 18:07 | 2 | 0 | 0 | 1 | ➡️ |
| 3 | 08/17 18:06 | 1 | 0 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 2 | 0.0% | 75.5s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 0
- **Average Duration**: 38.3s
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
