# Test Dashboard
Updated: 2025-08-15 23:11:54

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/15 23:11 | 127 | 115 | 1 | 11 | ➡️ |
| 2 | 08/15 23:11 | 2 | 1 | 1 | 0 | 📉 |
| 3 | 08/15 23:09 | 0 | 0 | 0 | 0 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 127 | 90.6% | 85.0s |
| Frontend | ❌ | 0 | 0.0% | 0.5s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 2
- **Average Duration**: 35.3s
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
