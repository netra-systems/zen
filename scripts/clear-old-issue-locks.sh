#!/bin/bash

# Clear Old Issue Locks Script
# Removes "actively-being-worked-on" tags from issues where:
# 1) Last comment (or comment update time) was more than 20 minutes ago
# AND
# 2) There is no recently added agent session tag

set -euo pipefail

# Configuration
CUTOFF_MINUTES=20
REPO_OWNER="netra-systems"
REPO_NAME="netra-apex"
DRY_RUN=${1:-false}

echo "🔍 Scanning for old issue locks..."
echo "📅 Cutoff time: $CUTOFF_MINUTES minutes ago"
echo "🏷️  Target label: actively-being-worked-on"

if [ "$DRY_RUN" = "true" ]; then
    echo "🧪 DRY RUN MODE - No changes will be made"
fi

# Get current timestamp (20 minutes ago)
CUTOFF_TIME=$(date -d "$CUTOFF_MINUTES minutes ago" +%s 2>/dev/null || date -v -${CUTOFF_MINUTES}M +%s)

# Counter for processed issues
PROCESSED_COUNT=0
UNLOCKED_COUNT=0

# Get all open issues with the "actively-being-worked-on" label
echo ""
echo "🔎 Finding issues with 'actively-being-worked-on' label..."

ISSUES=$(gh issue list \
    --repo "$REPO_OWNER/$REPO_NAME" \
    --label "actively-being-worked-on" \
    --state open \
    --json number,title,labels,updatedAt \
    --limit 100)

if [ "$(echo "$ISSUES" | jq length)" -eq 0 ]; then
    echo "✅ No issues found with 'actively-being-worked-on' label"
    exit 0
fi

echo "📊 Found $(echo "$ISSUES" | jq length) issues with 'actively-being-worked-on' label"

# Process each issue
echo "$ISSUES" | jq -c '.[]' | while read -r issue; do
    ISSUE_NUMBER=$(echo "$issue" | jq -r .number)
    ISSUE_TITLE=$(echo "$issue" | jq -r .title)
    ISSUE_UPDATED=$(echo "$issue" | jq -r .updatedAt)
    
    echo ""
    echo "🎯 Processing Issue #$ISSUE_NUMBER: $(echo "$ISSUE_TITLE" | cut -c1-50)..."
    
    ((PROCESSED_COUNT++))
    
    # Convert issue updated time to timestamp
    ISSUE_TIMESTAMP=$(date -d "$ISSUE_UPDATED" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$ISSUE_UPDATED" +%s)
    
    # Check if the issue was updated more than 20 minutes ago
    if [ "$ISSUE_TIMESTAMP" -gt "$CUTOFF_TIME" ]; then
        echo "   ⏰ Issue updated recently ($(date -d @$ISSUE_TIMESTAMP +"%Y-%m-%d %H:%M:%S")), skipping..."
        continue
    fi
    
    echo "   ⏰ Issue updated $(((CUTOFF_TIME - ISSUE_TIMESTAMP) / 60)) minutes ago"
    
    # Get detailed issue info including all labels
    ISSUE_DETAILS=$(gh issue view "$ISSUE_NUMBER" \
        --repo "$REPO_OWNER/$REPO_NAME" \
        --json labels,comments)
    
    # Check for recent agent session tags (format: agent-session-YYYY-MM-DD-HH:MM)
    RECENT_AGENT_TAG=$(echo "$ISSUE_DETAILS" | jq -r '.labels[] | select(.name | test("^agent-session-[0-9]{4}-[0-9]{2}-[0-9]{2}")) | .name' | head -1)
    
    if [ -n "$RECENT_AGENT_TAG" ] && [ "$RECENT_AGENT_TAG" != "null" ]; then
        echo "   🤖 Found recent agent session tag: $RECENT_AGENT_TAG"
        
        # Extract timestamp from agent session tag (format: agent-session-YYYY-MM-DD-HH:MM)
        AGENT_TAG_TIME=$(echo "$RECENT_AGENT_TAG" | sed 's/^agent-session-//' | sed 's/-/ /' | sed 's/-/:/g')
        AGENT_TIMESTAMP=$(date -d "$AGENT_TAG_TIME" +%s 2>/dev/null || date -j -f "%Y %m %d %H:%M" "$AGENT_TAG_TIME" +%s 2>/dev/null || echo "0")
        
        if [ "$AGENT_TIMESTAMP" -gt "$CUTOFF_TIME" ]; then
            echo "   ✅ Agent session is recent, keeping lock"
            continue
        else
            echo "   🕐 Agent session is older than $CUTOFF_MINUTES minutes"
        fi
    fi
    
    # Get the last comment time
    LAST_COMMENT_TIME=$(echo "$ISSUE_DETAILS" | jq -r '.comments[-1].updatedAt // empty')
    
    if [ -n "$LAST_COMMENT_TIME" ] && [ "$LAST_COMMENT_TIME" != "null" ]; then
        COMMENT_TIMESTAMP=$(date -d "$LAST_COMMENT_TIME" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$LAST_COMMENT_TIME" +%s)
        
        if [ "$COMMENT_TIMESTAMP" -gt "$CUTOFF_TIME" ]; then
            echo "   💬 Recent comment found ($(date -d @$COMMENT_TIMESTAMP +"%Y-%m-%d %H:%M:%S")), keeping lock"
            continue
        else
            echo "   💬 Last comment was $(((CUTOFF_TIME - COMMENT_TIMESTAMP) / 60)) minutes ago"
        fi
    else
        echo "   💬 No comments found"
    fi
    
    # If we reach here, the issue qualifies for lock removal
    echo "   🔓 Issue qualifies for lock removal"
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "   🧪 DRY RUN: Would remove 'actively-being-worked-on' label from Issue #$ISSUE_NUMBER"
    else
        echo "   🛠️  Removing 'actively-being-worked-on' label..."
        
        if gh issue edit "$ISSUE_NUMBER" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --remove-label "actively-being-worked-on"; then
            echo "   ✅ Successfully removed 'actively-being-worked-on' label from Issue #$ISSUE_NUMBER"
            
            # Add a comment explaining the automatic removal
            gh issue comment "$ISSUE_NUMBER" \
                --repo "$REPO_OWNER/$REPO_NAME" \
                --body "🤖 **Automatic Lock Removal**

The 'actively-being-worked-on' label has been automatically removed because:
- Last activity was more than $CUTOFF_MINUTES minutes ago
- No recent agent session tag found

If you are still working on this issue, please re-add the 'actively-being-worked-on' label.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>" || echo "   ⚠️  Warning: Could not add comment to Issue #$ISSUE_NUMBER"
            
        else
            echo "   ❌ Failed to remove label from Issue #$ISSUE_NUMBER"
            continue
        fi
    fi
    
    ((UNLOCKED_COUNT++))
done

echo ""
echo "📊 SUMMARY"
echo "🎯 Processed: $PROCESSED_COUNT issues"
echo "🔓 Unlocked: $UNLOCKED_COUNT issues"

if [ "$DRY_RUN" = "true" ]; then
    echo "🧪 This was a dry run - no actual changes were made"
    echo "💡 Run without 'true' parameter to execute changes"
else
    echo "✅ Operation completed successfully"
fi