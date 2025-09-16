#!/bin/bash

# GitHub CLI commands to add labels to Issue #1278
# These commands will need to be executed manually if gh CLI authentication is required

echo "Adding labels to Issue #1278..."

# Add the actively-being-worked-on label
gh issue edit 1278 --add-label "actively-being-worked-on"

# Add the agent-session label
gh issue edit 1278 --add-label "agent-session-20250915-183151"

echo "Labels added to Issue #1278:"
echo "- actively-being-worked-on"
echo "- agent-session-20250915-183151"

# Display current issue status
gh issue view 1278