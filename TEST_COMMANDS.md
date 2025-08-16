# Easy Test Commands for Netra Platform

## Quick Start - Most Common Commands

### 1. Run Default Unit Tests (RECOMMENDED - 1-2 min)
```bash
python test_runner.py --level unit
```
This is the **DEFAULT** command. Run this before and after making code changes.

### 2. Quick Smoke Test (30 seconds)
```bash
python test_runner.py --level smoke
```
Fast pre-commit validation for basic functionality.

### 3. Discover All Test Categories
```bash
python test_runner.py --discover
```
Shows all available test levels and categories with descriptions.

## Test Levels Overview

| Level | Time | Purpose | Command |
|-------|------|---------|---------|
| **smoke** | 30s | Quick pre-commit validation | `python test_runner.py --level smoke` |
| **unit** | 1-2 min | **DEFAULT** - Component testing | `python test_runner.py --level unit` |
| **agents** | 2-3 min | Agent functionality validation | `python test_runner.py --level agents` |
| **integration** | 3-5 min | Feature & API testing | `python test_runner.py --level integration` |
| **real_e2e** | 15-20 min | Real LLM & service testing | `python test_runner.py --level real_e2e` |
| **all** | 45-60 min | Complete system validation | `python test_runner.py --level all` |

## When to Use Each Test Level

### Before Committing Code
```bash
python test_runner.py --level unit  # Always run this
```

### After Agent Changes
```bash
python test_runner.py --level agents  # Quick agent validation
python test_runner.py --level real_e2e  # If significant agent changes
```

### Before Pull Request
```bash
python test_runner.py --level integration  # Full feature validation
```

### Before Release
```bash
python test_runner.py --level comprehensive  # Complete testing
```

## Running Specific Tests

### Run a Single Test File
```bash
python -m pytest app/tests/services/test_clickhouse_query_fixer.py -xvs
```

### Run a Specific Test Method
```bash
python -m pytest app/tests/services/test_file.py::TestClass::test_method -xvs
```

### Run Tests Matching a Pattern
```bash
python -m pytest -k "clickhouse" -xvs  # Runs all tests with "clickhouse" in name
```

## Frontend Tests

### Run Frontend Unit Tests
```bash
cd frontend
npm test
```

### Run Specific Frontend Test Categories
```bash
cd frontend
./node_modules/.bin/jest --testPathPatterns="__tests__/(lib|utils)/.*\.test\.[jt]sx?$"
```

## Test Output & Reports

Test reports are automatically generated in:
- **Unified Report**: `test_reports/unified_report.md`
- **Dashboard**: `test_reports/dashboard.md`
- **Coverage**: `reports/coverage/html/index.html`

## Troubleshooting

### If Tests Fail
1. Check the test output for specific error messages
2. Run the specific failing test with `-xvs` for detailed output
3. Check `SPEC/learnings/testing.xml` for documented fixes

### Common Issues & Fixes
- **Exit code 255**: Frontend test pattern issue - see learnings
- **ClickHouse array syntax**: Fixed in `clickhouse_query_fixer.py`
- **Test isolation**: Ensure proper setup/teardown for singletons

## Best Practices

1. **Always run unit tests** before and after code changes
2. **Fix test failures immediately** - never commit broken tests
3. **Use test discovery** to understand available test categories
4. **Check learnings** in `SPEC/learnings/testing.xml` for known issues

## Quick Reference Card

```bash
# Essential Commands (memorize these)
python test_runner.py --level unit      # DEFAULT - run before/after changes
python test_runner.py --discover         # See all test categories
python test_runner.py --level smoke      # Quick validation (30s)

# Development Workflow
python dev_launcher.py                   # Start development servers
python test_runner.py --level unit       # Test your changes
python scripts/check_architecture_compliance.py  # Check code compliance
```

## Need Help?

- Check `SPEC/learnings/testing.xml` for documented test issues and fixes
- Review `docs/TESTING_GUIDE.md` for comprehensive testing documentation
- Run `python test_runner.py --help` for all command options