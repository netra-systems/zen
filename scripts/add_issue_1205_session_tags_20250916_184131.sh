#!/bin/bash

# Add session tracking tags to Issue #1205
# AgentRegistryAdapter missing get_async method (P0 CRITICAL)

ISSUE_NUMBER=1205
SESSION_TAG="agent-session-20250916_184131"

echo "Adding session tracking tags to Issue #$ISSUE_NUMBER"
echo "Session tag: $SESSION_TAG"

# Add actively-being-worked-on label
gh issue edit $ISSUE_NUMBER --add-label "actively-being-worked-on"

# Add agent session tag
gh issue edit $ISSUE_NUMBER --add-label "$SESSION_TAG"

echo "Tags added successfully to Issue #$ISSUE_NUMBER"
echo "- actively-being-worked-on"
echo "- $SESSION_TAG"