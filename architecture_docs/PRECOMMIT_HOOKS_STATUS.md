# Pre-Commit Hooks Configuration

## 🔴 Current Status: DISABLED

The pre-commit architecture enforcement hooks are **temporarily disabled** to allow for development work without constant interruptions.

### Why Disabled?
- Allow rapid development without architecture violations blocking commits
- Enable work on fixing existing violations without being blocked
- Facilitate large refactoring efforts

### What's Preserved?
All configuration and hook files remain intact:
- `.githooks/pre-commit` - Main hook script
- `.githooks/pre-commit-python.py` - Python enforcement logic
- `.githooks/config.json` - Configuration file
- `scripts/manage_precommit.py` - Management utility

## Managing Pre-Commit Hooks

### Check Status
```bash
python scripts/manage_precommit.py status
```

### Disable Hooks
```bash
# With reason
python scripts/manage_precommit.py disable --reason "Working on large refactor"

# Quick disable
python scripts/manage_precommit.py disable
```

### Enable Hooks
```bash
# Simple enable
python scripts/manage_precommit.py enable

# With reason
python scripts/manage_precommit.py enable --reason "Ready for production"
```

## Configuration File

The configuration is stored in `.githooks/config.json`:

```json
{
  "precommit_checks_enabled": false,
  "check_file_size": true,
  "check_function_complexity": true,
  "check_test_stubs": true,
  "max_file_lines": 300,
  "max_function_lines": 8,
  "disabled_reason": "Temporarily disabled for development - re-enable before production",
  "disabled_date": "2024-08-14",
  "disabled_by": "Architecture team"
}
```

## What the Hooks Check (When Enabled)

1. **File Size Limit**
   - Maximum 300 lines per file
   - Encourages modular design

2. **Function Complexity**
   - Maximum 8 lines per function
   - Promotes single-responsibility functions

3. **Test Stubs**
   - No test stubs in production code
   - Ensures real implementations

## When to Re-Enable

### Before Production Deployment
Always re-enable hooks before deploying to production:
```bash
python scripts/manage_precommit.py enable --reason "Production deployment"
```

### After Major Refactoring
Once architecture violations are fixed:
```bash
python scripts/manage_precommit.py enable --reason "Architecture compliance achieved"
```

### For New Development
Enable for greenfield projects or new features:
```bash
python scripts/manage_precommit.py enable --reason "New feature development"
```

## Manual Architecture Check

Even with hooks disabled, you can manually check compliance:

```bash
# Full architecture check
python scripts/check_architecture_compliance.py

# Quick check for specific file
python scripts/check_architecture_compliance.py --path app/services/
```

## Important Notes

### ⚠️ Temporary Measure
This is a **temporary** configuration. The hooks should be re-enabled once:
- Current violations are addressed
- Development stabilizes
- Team is ready for enforcement

### 📊 Track Progress
Monitor architecture compliance even while disabled:
```bash
# Generate compliance report
python scripts/check_architecture_compliance.py --json-output compliance.json
```

### 🔄 Gradual Enforcement
Consider enabling specific checks gradually:
1. First enable file size checks
2. Then function complexity
3. Finally test stub detection

## Quick Commands Reference

| Action | Command |
|--------|---------|
| Check status | `python scripts/manage_precommit.py status` |
| Disable temporarily | `python scripts/manage_precommit.py disable` |
| Enable for production | `python scripts/manage_precommit.py enable --reason "Production"` |
| Manual compliance check | `python scripts/check_architecture_compliance.py` |
| Check specific file | `git add <file> && git commit -m "test"` (will show if enabled) |

## Next Steps

1. **Continue Development** - Work freely without hook interruptions
2. **Fix Violations** - Use `check_architecture_compliance.py` to track progress
3. **Re-enable Gradually** - Enable hooks when ready
4. **Maintain Standards** - Keep hooks enabled in production branches

---

**Remember**: The goal is to maintain high code quality. These hooks are helpers, not obstacles. Use them wisely to improve the codebase while maintaining development velocity.