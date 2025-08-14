# Test Dashboard
Updated: 2025-08-14 09:23:40

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/14 09:23 | 7 | 4 | 1 | 1 | ➡️ |
| 2 | 08/14 09:22 | 7 | 4 | 1 | 0 | ➡️ |
| 3 | 08/14 09:20 | 7 | 4 | 1 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 7 | 57.1% | 57.9s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 3
- **Average Duration**: 19.3s
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
