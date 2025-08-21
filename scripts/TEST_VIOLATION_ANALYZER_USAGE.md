# Test Violation Analyzer Usage Guide

## ⚠️ CRITICAL SAFETY NOTICE ⚠️

**This script is primarily designed for ANALYSIS and REPORTING, not automatic fixing!**

The auto-fix capabilities are **DANGEROUS** and should **NEVER** be used in production code without extensive review and testing.

## Purpose

The `auto_fix_test_violations.py` script is designed to:
1. **ANALYZE** test files for size violations (PRIMARY PURPOSE)
2. **REPORT** violations and suggest manual improvements (RECOMMENDED)
3. **SIMULATE** potential fixes in dry-run mode (SAFE)
4. **AUTO-FIX** violations (DANGEROUS - NOT RECOMMENDED)

## Safe Usage (RECOMMENDED)

### 1. Analysis and Reporting Only
```bash
# Default safe mode - only generates a report
python scripts/auto_fix_test_violations.py

# With test validation to check which tests are already failing
python scripts/auto_fix_test_violations.py --validate-tests

# Specify a different root directory
python scripts/auto_fix_test_violations.py --root-dir ./app/tests
```

### 2. Dry-Run Mode (Preview Changes)
```bash
# Preview what changes would be made (no actual modifications)
python scripts/auto_fix_test_violations.py --dry-run

# Preview with test validation
python scripts/auto_fix_test_violations.py --dry-run --validate-tests
```

## Unsafe Usage (NOT RECOMMENDED)

### ⚠️ WARNING: The following operations can break your tests!

The script includes auto-fix capabilities that are **intentionally difficult to enable** because they are dangerous:

```bash
# DANGEROUS: Requires multiple confirmations
python scripts/auto_fix_test_violations.py \
    --force-unsafe-fix \
    --confirm-unsafe \
    --disable-safe-mode

# You will be prompted to type: "YES I UNDERSTAND THE RISKS"
```

## Why Auto-Fix is Dangerous

1. **Test Dependencies**: Splitting files can break imports and shared fixtures
2. **Test Logic**: Automatic refactoring can alter test behavior
3. **Context Loss**: Automated tools don't understand test intent
4. **Hidden State**: Tests may rely on execution order or shared state
5. **Framework Specifics**: Different test frameworks have different requirements

## Recommended Manual Refactoring Approach

Instead of using auto-fix, follow these best practices:

### For Large Test Files (>300 lines)

1. **Identify logical groupings** in your tests
2. **Create focused test modules** with clear responsibilities:
   ```
   test_user_auth.py → test_user_login.py
                     → test_user_registration.py  
                     → test_user_permissions.py
   ```

3. **Extract shared fixtures** to conftest.py or dedicated fixture files:
   ```python
   # conftest.py or test_fixtures.py
   @pytest.fixture
   def test_user():
       return User(name="test", email="test@example.com")
   ```

4. **Use test classes** to group related tests:
   ```python
   class TestUserAuthentication:
       def test_valid_login(self):
           pass
       
       def test_invalid_password(self):
           pass
   ```

### For Long Test Functions (>8 lines)

1. **Extract setup code** into fixtures or helper methods:
   ```python
   # Before
   def test_complex_scenario():
       user = User(name="test")
       user.email = "test@example.com"
       user.role = "admin"
       db.session.add(user)
       db.session.commit()
       response = client.post("/api/action", ...)
       assert response.status_code == 200
   
   # After
   def test_complex_scenario(admin_user):
       response = client.post("/api/action", ...)
       assert response.status_code == 200
   ```

2. **Use parameterized tests** for similar test cases:
   ```python
   @pytest.mark.parametrize("input,expected", [
       ("valid", 200),
       ("invalid", 400),
       ("", 422),
   ])
   def test_api_responses(input, expected):
       response = client.post("/api", json={"data": input})
       assert response.status_code == expected
   ```

3. **Extract assertion helpers**:
   ```python
   def assert_valid_user_response(response):
       assert response.status_code == 200
       assert "user" in response.json()
       assert response.json()["user"]["id"] is not None
   ```

## Violation Limits

The script checks for:
- **File size limit**: 300 lines per test file
- **Function size limit**: 8 lines per test function

These are based on Netra's coding standards for maintainability.

## Output Files

The script generates:
- `test_violations_report.md` - Detailed violation report
- `.test_backups_YYYYMMDD_HHMMSS/` - Backup directory (if fixes are applied)

## Integration with CI/CD

For CI/CD pipelines, use the script in report-only mode:

```yaml
# GitHub Actions example
- name: Check test violations
  run: |
    python scripts/auto_fix_test_violations.py --report-only
    if [ -f test_violations_report.md ]; then
      echo "Test violations found. Please review the report."
      cat test_violations_report.md
    fi
```

## Recovery from Bad Auto-Fix

If you accidentally used auto-fix and broke your tests:

1. **Check the backup directory**:
   ```bash
   ls -la .test_backups_*/
   ```

2. **Restore from backup**:
   ```bash
   cp -r .test_backups_YYYYMMDD_HHMMSS/* .
   ```

3. **Or use git to revert**:
   ```bash
   git status  # Check modified files
   git checkout -- .  # Revert all changes
   ```

## Best Practices

1. **Always use report-only mode first** to understand violations
2. **Manually refactor** based on the suggestions
3. **Run tests after each change** to ensure nothing breaks
4. **Use version control** - commit before any refactoring
5. **Review the suggestions critically** - not all violations need fixing
6. **Consider the context** - some large test files are acceptable if well-organized

## When NOT to Use This Script

- **In production pipelines** - Only use for analysis, never for automatic fixes
- **Without backup** - Always ensure you can revert changes
- **On passing test suites** - Don't fix what isn't broken
- **Without understanding** - Manual refactoring requires understanding the test logic

## Support

For questions or issues with test refactoring, consult:
- The Netra engineering standards in CLAUDE.md
- The test specifications in SPEC/testing.xml
- Your team's test architecture guidelines

Remember: **Manual refactoring with understanding > Automatic fixes without context**