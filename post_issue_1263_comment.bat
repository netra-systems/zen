@echo off
echo Posting comprehensive status update comment to Issue #1263...

REM Post the comment using GitHub CLI
gh issue comment 1263 --body-file "issue_1263_comprehensive_status_update_comment.md"

REM Add labels to the issue
gh issue edit 1263 --add-label "actively-being-worked-on"
gh issue edit 1263 --add-label "agent-session-20250915-134"

echo.
echo Comment posted successfully to Issue #1263
echo Labels added: actively-being-worked-on, agent-session-20250915-134
echo.
echo GitHub Issue URL: https://github.com/your-org/netra-apex/issues/1263