#!/bin/bash

# Add session tags to Issue #1184 for WebSocket Manager Await Error
# Repository: netra-systems/netra-apex

echo "Adding session tags to Issue #1184..."

# Add the actively-being-worked-on tag and current agent session tag
gh issue edit 1184 --add-label "actively-being-worked-on,agent-session-2025-09-15-162800"

echo "Session tags added to Issue #1184"
echo "Issue URL: https://github.com/netra-systems/netra-apex/issues/1184"