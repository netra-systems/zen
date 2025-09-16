#!/bin/bash

# GitIssueProgressorv3 - Add Session Tags to Issue #1278
# Generated: 2025-09-16 09:00:24

echo "Adding session tags to Issue #1278..."

# Add actively-being-worked-on label
gh issue edit 1278 --add-label "actively-being-worked-on"
echo "✅ Added 'actively-being-worked-on' label"

# Add agent session timestamp label
gh issue edit 1278 --add-label "agent-session-20250916-090024"
echo "✅ Added 'agent-session-20250916-090024' label"

echo "🚀 Session tags successfully added to Issue #1278"