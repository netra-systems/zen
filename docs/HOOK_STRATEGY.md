# Pre-commit Hook Strategy

## Overview

Our pre-commit hook system now supports two modes to balance code quality with development velocity:

1. **Permissive Mode** (Default for Development) - Focus on new code quality
2. **Strict Mode** - Full compliance enforcement for releases

## Quick Start

```bash
# Check current mode
python scripts/switch_hooks_mode.py status

# Switch to permissive mode (recommended for development)
python scripts/switch_hooks_mode.py permissive

# Switch to strict mode (before releases)
python scripts/switch_hooks_mode.py strict

# Apply changes
pre-commit install
```

## Permissive Mode (Recommended Default)

### Philosophy
- **Progressive Enhancement**: Apply strict standards to new code while being lenient with legacy
- **Incremental Improvement**: Check only modified lines in existing files
- **Practical Focus**: Prioritize main codebase over test sprawl
- **Developer-Friendly**: Allow quick fixes without full refactoring
- **Fail-Fast**: Stop at first error for immediate feedback (configurable)

### What It Checks

#### New Files (Strict)
- File size limit: 300 lines
- Absolute imports required
- Type hints required for functions
- No duplicate patterns

#### Modified Lines Only (Incremental)
- Line length: 120 characters
- No relative imports in new code
- No bare except clauses
- Prefer logging over print statements

#### Priority-Based Checking
1. **CRITICAL (Core)**: `netra_backend/app/core`, `auth_service/auth_core` - Strictest
2. **HIGH (App)**: General application code - Moderate
3. **MEDIUM (Scripts)**: Utility scripts - Relaxed
4. **LOW (Tests)**: Test files - Very lenient (1000 line limit)
5. **MINIMAL (Other)**: Everything else - Minimal checks

### Emergency Bypass
Add one of these flags to your commit message for emergency fixes:
- `[EMERGENCY]`
- `[HOTFIX]`
- `[BYPASS]`
- `EMERGENCY_FIX`

Example:
```bash
git commit -m "[HOTFIX] Fix critical production issue"
```

## Strict Mode (For Releases)

Use before production releases or major refactors:
- 300-line file limit (strict)
- 25-line function limit
- Full type safety enforcement
- Complete duplicate detection
- No test stubs allowed

## Implementation Details

### Hook Scripts Location
- Permissive hooks: `scripts/permissive_hooks/`
- Enforcement scripts: `scripts/`
- Configuration files:
  - `.pre-commit-config-permissive.yaml` (permissive mode)
  - `.pre-commit-config-strict.yaml` (strict mode)

### Key Features

1. **Git-Aware**: Hooks understand git status and only check relevant changes
2. **Incremental Checks**: Only validate modified lines, not entire files
3. **Priority System**: Different standards for different parts of codebase
4. **Progress Tracking**: Monitor quality improvements over time
5. **CI/CD Compatible**: Relaxed checks in CI environments
6. **Fail-Fast Default**: Stops at first error for faster feedback (can be disabled)

## Best Practices

### During Development
1. Use **permissive mode** for feature development
2. Focus on writing clean new code
3. Incrementally improve legacy code when touching it
4. Use emergency bypass sparingly and follow up with cleanup

### Before Commits
1. Let hooks guide you on critical issues
2. Address errors in high-priority files first
3. Warnings in test files can be addressed later

### Before Releases
1. Switch to **strict mode**
2. Run full compliance checks
3. Address all critical issues
4. Document any technical debt

## Configuration Options

### Fail-Fast Behavior
By default, hooks stop at the first error for faster feedback. To check all files:

```bash
# Disable fail-fast temporarily (check all files)
pre-commit run --all-files --no-fail-fast

# Or edit .pre-commit-config.yaml
# Change: fail_fast: true
# To:     fail_fast: false
```

## Troubleshooting

### Hooks Not Running
```bash
# Reinstall hooks
pre-commit install

# Or bypass once
git commit --no-verify
```

### Too Many False Positives
```bash
# Switch to permissive mode
python scripts/switch_hooks_mode.py permissive
pre-commit install
```

### Need to Disable Temporarily
```bash
# Disable hooks
python scripts/switch_hooks_mode.py off

# Re-enable when done
python scripts/switch_hooks_mode.py permissive
```

### Want to See All Errors (Not Just First)
```bash
# Run without fail-fast
pre-commit run --no-fail-fast

# Or for specific hook
pre-commit run check-new-files --no-fail-fast
```

## Migration Plan

### Phase 1 (Current)
- Default to permissive mode for all developers
- Apply strict checks only to new files
- Track quality metrics without blocking

### Phase 2 (Future)
- Gradually increase standards for modified code
- Implement automated refactoring suggestions
- Create quality dashboards

### Phase 3 (Long-term)
- Full codebase compliance
- Automated quality gates in CI/CD
- Context-aware AI-assisted refactoring

## Summary

The permissive hook strategy allows us to:
- Ship features quickly without being blocked by legacy code issues
- Maintain high standards for new code
- Incrementally improve the codebase
- Focus enforcement where it matters most (core application code)
- Provide escape hatches for emergencies

This balanced approach ensures we can maintain velocity while progressively improving code quality.