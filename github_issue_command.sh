#!/bin/bash

# GitHub Issue Creation Command for WebSocket Connection Failure
# Run this command to create the GitHub issue

gh issue create \
  --title "failing-test-active-dev-P0-websocket-connection-failure" \
  --body-file "/Users/anthony/Desktop/netra-apex/github_issue_websocket_connection_failure.md" \
  --label "claude-code-generated-issue" \
  --label "P0" \
  --label "test-failure" \
  --label "infrastructure" \
  --label "websocket" \
  --label "golden-path"

echo "GitHub issue created successfully!"