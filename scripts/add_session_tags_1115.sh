#!/bin/bash

# Add session tags to issue #1115
# Current datetime: 2025-09-15T16:28:00

echo "Adding session tags to issue #1115..."

# Use specified session identifier
SESSION_TAG="agent-session-2025-09-15-162800"

# Create labels if they don't exist
echo "Creating labels if they don't exist..."
gh label create "actively-being-worked-on" --description "Issue is actively being worked on" --color "0e8a16" 2>/dev/null || echo "Label 'actively-being-worked-on' already exists or could not be created"
gh label create "${SESSION_TAG}" --description "Agent session tracking tag for ${SESSION_TAG}" --color "1d76db" 2>/dev/null || echo "Label '${SESSION_TAG}' already exists or could not be created"

# Add the session tags
echo "Adding labels to issue..."
gh issue edit 1115 --add-label "actively-being-worked-on" || echo "Failed to add actively-being-worked-on label"
gh issue edit 1115 --add-label "${SESSION_TAG}" || echo "Failed to add ${SESSION_TAG} label"

echo "Session tags added:"
echo "- actively-being-worked-on"
echo "- ${SESSION_TAG}"

# Show updated issue status
echo ""
echo "Updated issue status:"
gh issue view 1115 --json labels,title,state | jq '.labels[].name, .title, .state'