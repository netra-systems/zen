#!/bin/bash

# Issue #596 Agent Session Tracking Script
# Created: 2025-09-16 09:04:22

echo "Adding agent session tag to Issue #596..."

# Add actively-being-worked-on tag if not present
gh issue edit 596 --add-label "actively-being-worked-on" --add-label "agent-session-20250916_090422"

echo "Checking Issue #596 current status..."
gh issue view 596

echo "Checking for any recent work..."
gh issue view 596 --comments | tail -20

echo "Agent session tag added successfully."