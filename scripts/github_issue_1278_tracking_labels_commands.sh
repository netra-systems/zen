#!/bin/bash

# GitHub Issue #1278 Tracking Labels Commands
# Agent Session: agent-session-20250915_185102

echo "🏷️ Adding required tracking labels to Issue #1278..."

# Add actively-being-worked-on label
echo "Adding 'actively-being-worked-on' label..."
gh issue edit 1278 --add-label "actively-being-worked-on"

# Add current session tracking label
echo "Adding 'agent-session-20250915_185102' label..."
gh issue edit 1278 --add-label "agent-session-20250915_185102"

echo "✅ Tracking labels added successfully"
echo "📋 Labels added:"
echo "   - actively-being-worked-on"
echo "   - agent-session-20250915_185102"

# Verify labels were added
echo "🔍 Verifying labels..."
gh issue view 1278 --json labels