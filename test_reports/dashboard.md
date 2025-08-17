# Test Dashboard
Updated: 2025-08-16 21:09:53

## Last 3 Runs

| Run | Time | Total | ✅ Pass | ❌ Fail | ⏭️ Skip | Trend |
|-----|------|-------|---------|---------|---------|-------|
| 1 | 08/16 21:09 | 1174 | 1149 | 2 | 23 | 📉 |
| 2 | 08/16 21:04 | 1171 | 1146 | 1 | 23 | 📈 |
| 3 | 08/16 20:59 | 1169 | 1144 | 2 | 23 | — |

## Latest Run Details

| Component | Status | Tests | Pass Rate | Duration |
|-----------|--------|-------|-----------|----------|
| Backend | ❌ | 1174 | 97.9% | 69.7s |
| Frontend | ❌ | 0 | 0.0% | 0.3s |
| E2E | ❌ | 0 | 0.0% | 0.0s |

## Key Metrics

- **Total Failures (last 3 runs)**: 5
- **Average Duration**: 71.8s
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
