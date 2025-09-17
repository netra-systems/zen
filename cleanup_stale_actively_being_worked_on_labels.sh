#!/bin/bash

# Script to remove "actively-being-worked-on" labels from stale GitHub issues
# Removes labels from issues that haven't been updated in more than 20 minutes

REPO="netra-systems/netra-apex"
LABEL="actively-being-worked-on"
CUTOFF_MINUTES=20

echo "=== Cleanup Script for Stale 'actively-being-worked-on' Labels ==="
echo "Repository: $REPO"
echo "Label: $LABEL"
echo "Cutoff: $CUTOFF_MINUTES minutes"
echo ""

# Get current timestamp (20 minutes ago)
cutoff_time=$(date -u -v-${CUTOFF_MINUTES}M '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u -d "${CUTOFF_MINUTES} minutes ago" '+%Y-%m-%dT%H:%M:%SZ')

echo "Cutoff time: $cutoff_time"
echo ""

# Function to check if gh CLI is authenticated
check_auth() {
    if ! gh auth status &>/dev/null; then
        echo "❌ Error: Not authenticated with GitHub CLI"
        echo "Run: gh auth login"
        exit 1
    fi
}

# Function to get issues with the specified label
get_labeled_issues() {
    echo "📋 Fetching issues with '$LABEL' label..."
    gh issue list \
        --repo "$REPO" \
        --label "$LABEL" \
        --state open \
        --json number,title,updatedAt,url \
        --limit 100
}

# Function to remove label from an issue
remove_label() {
    local issue_number=$1
    local issue_title=$2
    echo "🏷️  Removing label from issue #$issue_number: $issue_title"
    gh issue edit "$issue_number" --repo "$REPO" --remove-label "$LABEL"
    if [ $? -eq 0 ]; then
        echo "✅ Successfully removed label from issue #$issue_number"
    else
        echo "❌ Failed to remove label from issue #$issue_number"
    fi
}

# Function to check if issue is stale
is_stale() {
    local updated_at=$1
    # Convert times to seconds since epoch for comparison
    updated_seconds=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$updated_at" "+%s" 2>/dev/null || date -d "$updated_at" "+%s" 2>/dev/null)
    cutoff_seconds=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$cutoff_time" "+%s" 2>/dev/null || date -d "$cutoff_time" "+%s" 2>/dev/null)
    
    if [ "$updated_seconds" -lt "$cutoff_seconds" ]; then
        return 0  # true - is stale
    else
        return 1  # false - not stale
    fi
}

# Main execution
main() {
    check_auth
    
    echo "🔍 Searching for stale issues..."
    issues_json=$(get_labeled_issues)
    
    if [ "$issues_json" = "[]" ] || [ -z "$issues_json" ]; then
        echo "✅ No issues found with '$LABEL' label"
        exit 0
    fi
    
    echo "📊 Processing issues..."
    stale_count=0
    total_count=0
    
    # Process each issue
    echo "$issues_json" | jq -r '.[] | @base64' | while read -r encoded_issue; do
        issue=$(echo "$encoded_issue" | base64 --decode)
        number=$(echo "$issue" | jq -r '.number')
        title=$(echo "$issue" | jq -r '.title')
        updated_at=$(echo "$issue" | jq -r '.updatedAt')
        url=$(echo "$issue" | jq -r '.url')
        
        total_count=$((total_count + 1))
        
        echo ""
        echo "🔎 Checking issue #$number: $title"
        echo "   Last updated: $updated_at"
        echo "   URL: $url"
        
        if is_stale "$updated_at"; then
            echo "   ⏰ Issue is stale (>$CUTOFF_MINUTES minutes old)"
            remove_label "$number" "$title"
            stale_count=$((stale_count + 1))
        else
            echo "   ✅ Issue is recent (≤$CUTOFF_MINUTES minutes old) - keeping label"
        fi
    done
    
    echo ""
    echo "=== Summary ==="
    echo "Total issues with '$LABEL' label: $total_count"
    echo "Stale issues (label removed): $stale_count"
    echo "Recent issues (label kept): $((total_count - stale_count))"
}

# Run the script
main "$@"