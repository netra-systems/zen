# Test Dashboard
Updated: 2025-08-14 16:00:28

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/14 16:00 | 7 | 7 | 0 | 0 | ➡️ |
| 2 | 08/14 15:44 | 7 | 7 | 0 | 0 | ➡️ |
| 3 | 08/14 15:44 | 1 | 0 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ✅ | 7 | 100.0% | 13.8s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 0
- **Average Duration**: 12.0s
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
