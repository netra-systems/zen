#!/bin/bash

# Agent Session Tagging for Issue #1278
# Generated: 2025-09-16 08:59:00
# Agent Session ID: agent-session-20250916-085900

echo "Adding agent session tracking labels to Issue #1278..."

# Add actively-being-worked-on label
gh issue edit 1278 --add-label "actively-being-worked-on"

# Add agent session tracking label
gh issue edit 1278 --add-label "agent-session-20250916-085900"

echo "Labels added successfully to Issue #1278"
echo "Agent Session: agent-session-20250916-085900"