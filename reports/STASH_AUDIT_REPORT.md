# Git Stash Audit Report

## Current Stashes (6 total)

### stash@{0}: GitHub Desktop stash
**Branch:** critical-remediation-20250823  
**Date:** Recent  
**Files:** 496 changed, 7252 insertions(+), 88 deletions(-)  
**Content:** Large test suite refactoring with multiple iteration reports
**Recommendation:** ❌ **DISCARD** - This appears to be a massive automated test refactoring that adds many debug/fix scripts. Current branch already has better organized tests.

### stash@{1}: WIP on critical-remediation-20250823
**Branch:** critical-remediation-20250823  
**Date:** After commit c3b2b56dd  
**Files:** 8 changed, 110 insertions(+), 118 deletions(-)  
**Content:** Auth proxy updates, login page simplification, test fixes
**Recommendation:** ⚠️ **REVIEW** - Contains auth proxy route changes that might be useful

### stash@{2}: Pre-merge stash
**Branch:** critical-remediation-20250823  
**Date:** Before merge with 8-22-25-pm  
**Files:** ~20 changed  
**Content:** Pre-commit config, test utils cleanup, removed backup files
**Recommendation:** ✅ **PARTIAL KEEP** - The .pre-commit-config.yaml might be useful, backup removals are good

### stash@{3}: Work from other branch
**Branch:** 8-22-25-pm  
**Date:** Older  
**Recommendation:** ❌ **DISCARD** - Old branch work, likely outdated

### stash@{4}: WIP on 8-20-25
**Branch:** 8-20-25  
**Date:** Aug 20, 2025  
**Files:** Unknown  
**Recommendation:** ❌ **DISCARD** - Very old, from different branch

### stash@{5}: GCP deployment changes
**Branch:** business-8-16-2025  
**Date:** Aug 16, 2025  
**Files:** Unknown  
**Recommendation:** ❌ **DISCARD** - Old deployment changes, likely superseded

## Summary

### To Keep/Review:
1. **stash@{1}** - Review auth proxy changes before discarding
2. **stash@{2}** - Extract .pre-commit-config.yaml if needed

### To Discard:
1. **stash@{0}** - Massive test refactoring with many debug files
2. **stash@{3}** - Old branch work
3. **stash@{4}** - Very old WIP
4. **stash@{5}** - Old GCP deployment

## Cleanup Commands

```bash
# Review specific files from stash@{1}
git stash show -p stash@{1} -- netra_backend/app/routes/auth_proxy.py

# Extract pre-commit config from stash@{2}
git checkout stash@{2} -- .pre-commit-config.yaml

# After reviewing/extracting needed files, clean up:
git stash drop stash@{0}  # Drop the massive test refactor
git stash drop stash@{3}  # Drop old branch work
git stash drop stash@{4}  # Drop old WIP
git stash drop stash@{5}  # Drop old GCP deployment

# Keep stash@{1} and stash@{2} for now until reviewed
```

## Legacy Files to Remove (from cleanup script)

The cleanup script `cleanup-legacy-files.js` will remove:
- 50+ debug and fix scripts
- Test output logs
- Backup files
- Redundant Jest configurations
- Temporary test files

Run: `node cleanup-legacy-files.js --dry-run` first to preview