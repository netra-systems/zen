# Test Dashboard
Updated: 2025-08-14 09:09:47

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/14 09:09 | 4 | 1 | 2 | 1 | 📈 |
| 2 | 08/14 09:08 | 217 | 194 | 3 | 20 | ➡️ |
| 3 | 08/14 06:31 | 217 | 194 | 3 | 20 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 4 | 25.0% | 74.3s |
| Frontend | ❌ | 0 | 0.0% | 0.0s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 8
- **Average Duration**: 53.6s
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
