# Test Dashboard
Updated: 2025-08-15 14:42:11

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 14:42 | 1068 | 1041 | 3 | 23 | 📉 |
| 2 | 08/15 14:40 | 959 | 936 | 2 | 21 | ➡️ |
| 3 | 08/15 14:38 | 1038 | 1014 | 2 | 22 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 1068 | 97.5% | 56.2s |
| Frontend | ❌ | 0 | 0.0% | 0.4s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 7
- **Average Duration**: 58.4s
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
