@echo off
REM Script to close Issue #1181 with comprehensive status comment

echo Posting closure comment to Issue #1181...
gh issue comment 1181 --body-file "github_issue_1181_closure_comment.md"

echo Removing actively-being-worked-on label...
gh issue edit 1181 --remove-label "actively-being-worked-on"

echo Adding resolved label...
gh issue edit 1181 --add-label "resolved"

echo Closing Issue #1181...
gh issue close 1181 --reason completed

echo Issue #1181 closure process complete.