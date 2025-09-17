@echo off
echo Creating Emergency PR for Critical Infrastructure Failures...
echo.

echo Step 1: Pushing changes to remote...
git push -u origin develop-long-lived

echo.
echo Step 2: Creating PR with GitHub CLI...
gh pr create ^
  --title "🚨 EMERGENCY: Critical Infrastructure Failures + System Stability Violations - $500K+ ARR at Risk" ^
  --body-file "EMERGENCY_PR_CRITICAL_INFRASTRUCTURE_FAILURES.md" ^
  --label "claude-code-generated-issue" ^
  --label "critical" ^
  --label "infrastructure" ^
  --label "deployment" ^
  --label "security"

echo.
echo Emergency PR creation completed!
echo Please review the PR and ensure all critical issues are addressed.