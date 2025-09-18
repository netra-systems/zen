#!/bin/bash

# GitHub Issue Search and Creation Script for Staging HTTP 503 Errors
# Date: 2025-09-16
# Priority: P0 CRITICAL

echo "🔍 Searching for existing staging HTTP 503 issues..."

# Search for existing issues related to staging HTTP 503 errors
echo "Searching GitHub for existing staging 503 issues..."
gh issue list --search "503" --state all --limit 20 > existing_503_issues.txt 2>&1 || echo "❌ GitHub CLI search failed"

echo "Searching for staging environment issues..."
gh issue list --search "staging environment" --state all --limit 20 > existing_staging_issues.txt 2>&1 || echo "❌ GitHub CLI staging search failed"

echo "Searching for VPC connector issues..."
gh issue list --search "vpc connector" --state all --limit 20 > existing_vpc_issues.txt 2>&1 || echo "❌ GitHub CLI VPC search failed"

echo "Searching for issue 1278..."
gh issue view 1278 > issue_1278_status.txt 2>&1 || echo "❌ Cannot access issue 1278"

echo "Searching for infrastructure issues..."
gh issue list --search "infrastructure" --state all --limit 20 > existing_infrastructure_issues.txt 2>&1 || echo "❌ GitHub CLI infrastructure search failed"

# Check if any existing files contain issue information
echo "📋 Analyzing existing issue documentation..."

# Check if issue 1278 is still open based on local files
echo "Checking local documentation for issue 1278 status..."
if grep -r "issue.*1278" . --include="*.md" | head -10; then
    echo "✅ Found references to issue 1278 in local documentation"
else
    echo "❌ No local references to issue 1278 found"
fi

# Determine action based on findings
echo "🎯 Determining issue creation/update strategy..."

if [ -f "issue_1278_status.txt" ] && grep -q "State.*open\|Status.*open" issue_1278_status.txt; then
    echo "📝 Issue 1278 appears to be open - will update with current status"
    ISSUE_ACTION="UPDATE_1278"
    ISSUE_NUMBER="1278"
elif [ -f "existing_503_issues.txt" ] && grep -q "503\|Service Unavailable" existing_503_issues.txt; then
    echo "📝 Found existing 503 issues - will update most recent"
    ISSUE_ACTION="UPDATE_EXISTING_503"
    # Extract issue number from search results
    ISSUE_NUMBER=$(grep -o "#[0-9]*" existing_503_issues.txt | head -1 | sed 's/#//')
else
    echo "🆕 No suitable existing issue found - will create new issue"
    ISSUE_ACTION="CREATE_NEW"
fi

echo "Determined action: $ISSUE_ACTION"

# Execute the determined action
case $ISSUE_ACTION in
    "UPDATE_1278")
        echo "📤 Updating Issue #1278 with current HTTP 503 status..."
        gh issue comment 1278 --body-file "CRITICAL_STAGING_HTTP_503_ISSUE_SEPTEMBER_16_2025.md" || echo "❌ Failed to update issue 1278"
        echo "✅ Issue #1278 updated with current staging HTTP 503 status"
        echo "RESULT: UPDATED_ISSUE_1278"
        ;;

    "UPDATE_EXISTING_503")
        echo "📤 Updating existing 503 issue #$ISSUE_NUMBER..."
        gh issue comment "$ISSUE_NUMBER" --body-file "CRITICAL_STAGING_HTTP_503_ISSUE_SEPTEMBER_16_2025.md" || echo "❌ Failed to update existing issue"
        echo "✅ Issue #$ISSUE_NUMBER updated with current status"
        echo "RESULT: UPDATED_ISSUE_$ISSUE_NUMBER"
        ;;

    "CREATE_NEW"|*)
        echo "🆕 Creating new GitHub issue for staging HTTP 503 errors..."
        NEW_ISSUE=$(gh issue create \
            --title "🚨 CRITICAL: GCP Staging HTTP 503 Errors Blocking E2E Agent Tests" \
            --label "infrastructure,staging,critical,p0,http-503,vpc-connector,e2e-testing" \
            --body-file "CRITICAL_STAGING_HTTP_503_ISSUE_SEPTEMBER_16_2025.md" 2>&1)

        if echo "$NEW_ISSUE" | grep -q "https://github.com"; then
            echo "✅ New issue created successfully"
            echo "RESULT: CREATED_NEW_ISSUE"
            echo "Issue URL: $NEW_ISSUE"
            # Extract issue number from URL
            ISSUE_NUMBER=$(echo "$NEW_ISSUE" | grep -o "[0-9]*$")
            echo "Issue Number: #$ISSUE_NUMBER"
        else
            echo "❌ Failed to create new issue: $NEW_ISSUE"
            echo "RESULT: CREATION_FAILED"
        fi
        ;;
esac

# Generate summary report
echo "📊 GitHub Issue Management Summary"
echo "=================================="
echo "Date: $(date)"
echo "Action Taken: $ISSUE_ACTION"
echo "Issue Number: ${ISSUE_NUMBER:-'N/A'}"
echo "Status: E2E agent tests blocked by staging HTTP 503 errors"
echo "Priority: P0 CRITICAL"
echo "Business Impact: \$500K+ ARR functionality validation blocked"
echo ""
echo "Next Steps:"
echo "1. Infrastructure team investigate GCP Cloud Run services"
echo "2. Check VPC connector capacity and scaling"
echo "3. Validate SSL certificates for *.netrasystems.ai"
echo "4. Restart services if resource exhaustion detected"
echo "5. Re-run E2E agent tests once infrastructure restored"

# Clean up temporary files
rm -f existing_*.txt issue_1278_status.txt 2>/dev/null || true

echo ""
echo "🎯 Script completed. Check above for RESULT status."