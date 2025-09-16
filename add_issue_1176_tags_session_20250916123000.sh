#!/bin/bash

# Script to add required tags to Issue #1176 for agent session tracking
# Generated: 2025-09-16 12:30:00

echo "Adding required tags to Issue #1176..."

# Generate current timestamp in required format
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
SESSION_TAG="agent-session-${TIMESTAMP}"

echo "Using session tag: ${SESSION_TAG}"

# Add the required labels to Issue #1176
gh issue edit 1176 --add-label "actively-being-worked-on" --add-label "${SESSION_TAG}"

if [ $? -eq 0 ]; then
    echo "✅ Successfully added tags to Issue #1176:"
    echo "   - actively-being-worked-on"
    echo "   - ${SESSION_TAG}"
else
    echo "❌ Failed to add tags to Issue #1176"
    exit 1
fi

echo "Issue #1176 is now tagged for active agent session work."