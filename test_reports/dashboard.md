# Test Dashboard
Updated: 2025-08-16 21:04:28

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/16 21:04 | 1171 | 1146 | 1 | 23 | 📈 |
| 2 | 08/16 20:59 | 1169 | 1144 | 2 | 23 | 📉 |
| 3 | 08/16 20:51 | 1168 | 1143 | 1 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 1171 | 97.9% | 68.6s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 4
- **Average Duration**: 72.0s
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
