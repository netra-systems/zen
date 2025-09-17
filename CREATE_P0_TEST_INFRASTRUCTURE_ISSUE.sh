#!/bin/bash

# Create P0 Test Infrastructure Crisis GitHub Issue
# Agent Session: 20250117-1230

echo "Creating P0 Test Infrastructure Crisis GitHub Issue..."

gh issue create \
  --title "P0: Test Infrastructure Crisis Blocking Golden Path Validation" \
  --body-file "GITHUB_ISSUE_P0_TEST_INFRASTRUCTURE_CRISIS.md" \
  --label "P0,golden-path,critical-blocker,agent-session-20250117-1230,actively-being-worked-on" \
  --assignee "@me"

if [ $? -eq 0 ]; then
    echo "✅ GitHub issue created successfully"
    echo "📋 Issue tracking P0 test infrastructure crisis"
    echo "🏷️  Labels: P0, golden-path, critical-blocker, agent-session-20250117-1230, actively-being-worked-on"
else
    echo "❌ Failed to create GitHub issue"
    echo "💡 Try running manually: gh issue create --title \"P0: Test Infrastructure Crisis Blocking Golden Path Validation\" --body-file \"GITHUB_ISSUE_P0_TEST_INFRASTRUCTURE_CRISIS.md\" --label \"P0,golden-path,critical-blocker,agent-session-20250117-1230,actively-being-worked-on\""
fi