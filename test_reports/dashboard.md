# Test Dashboard
Updated: 2025-08-14 17:12:39

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/14 17:12 | 15 | 11 | 3 | 0 | ➡️ |
| 2 | 08/14 17:12 | 156 | 144 | 3 | 0 | ➡️ |
| 3 | 08/14 17:10 | 123 | 111 | 3 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 15 | 73.3% | 13.6s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 9
- **Average Duration**: 4.5s
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
