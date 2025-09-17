#!/bin/bash

# Script to update Issue #1278 with Five Whys analysis results
# Usage: ./update_issue_1278_five_whys.sh

echo "Issue #1278 Five Whys Analysis - GitHub Update Script"
echo "===================================================="

# Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not available"
    echo "Please install gh CLI or run commands manually"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI"
    echo "Please run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI available and authenticated"
echo

# Display issue status
echo "📋 Current Issue #1278 Status:"
echo "gh issue view 1278"
gh issue view 1278 --json number,title,state,labels,assignees,body | jq '.'
echo

# Add comprehensive Five Whys analysis comment
echo "📝 Adding Five Whys Analysis Comment..."
echo "gh issue comment 1278 --body-file ISSUE_1278_GITHUB_COMMENT_FIVE_WHYS.md"

if [ -f "ISSUE_1278_GITHUB_COMMENT_FIVE_WHYS.md" ]; then
    COMMENT_URL=$(gh issue comment 1278 --body-file ISSUE_1278_GITHUB_COMMENT_FIVE_WHYS.md)
    echo "✅ Comment added successfully"
    echo "📍 Comment URL: $COMMENT_URL"
else
    echo "❌ Comment file not found: ISSUE_1278_GITHUB_COMMENT_FIVE_WHYS.md"
    exit 1
fi

echo

# Add appropriate labels for resolution
echo "🏷️ Adding Resolution Labels..."
echo "gh issue edit 1278 --add-label 'resolved' --add-label 'five-whys-complete' --add-label 'infrastructure-remediated'"
gh issue edit 1278 --add-label "resolved" --add-label "five-whys-complete" --add-label "infrastructure-remediated"
echo "✅ Labels added"

echo

# Optional: Close issue if appropriate
read -p "🔒 Close Issue #1278 as resolved? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "gh issue close 1278 --reason completed"
    gh issue close 1278 --reason completed
    echo "✅ Issue #1278 closed as completed"
else
    echo "ℹ️ Issue remains open for monitoring"
fi

echo
echo "✅ Issue #1278 update completed successfully"
echo
echo "📄 Full analysis available in: ISSUE_1278_FIVE_WHYS_ANALYSIS_20250917.md"
echo "📍 Comment ID returned for reference"

# Display final status
echo
echo "📊 Final Issue Status:"
gh issue view 1278 --json number,title,state,labels | jq '.'