#!/bin/bash

# GitHub Issue Creation Script for SERVICE_ID Whitespace Configuration Issue
# Priority: P2 | Configuration Hygiene Issue
# Created: 2025-09-16T01:33:00Z

set -e

echo "🔍 Creating GitHub Issue: SERVICE_ID Whitespace Configuration Issue"
echo "Priority: P2 (Medium)"
echo "Type: Configuration Drift"
echo ""

# Verify GitHub CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo "❌ Error: GitHub CLI not authenticated. Please run 'gh auth login' first."
    exit 1
fi

# Verify we're in the correct repository
if ! git rev-parse --git-dir &>/dev/null; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

echo "✅ GitHub CLI authenticated and in git repository"
echo ""

# Create the GitHub issue
echo "📝 Creating issue with the following details:"
echo "Title: P2 | SERVICE_ID Environment Variable Contains Whitespace - Configuration Hygiene Issue"
echo "Labels: claude-code-generated-issue, P2, configuration, environment, backend, staging, configuration-drift"
echo ""

ISSUE_BODY_FILE="/Users/anthony/Desktop/netra-apex/github_issue_serviceid_whitespace_p2_20250916.md"

if [ ! -f "$ISSUE_BODY_FILE" ]; then
    echo "❌ Error: Issue body file not found: $ISSUE_BODY_FILE"
    exit 1
fi

# Create the issue
echo "🚀 Creating GitHub issue..."
ISSUE_URL=$(gh issue create \
  --title "P2 | SERVICE_ID Environment Variable Contains Whitespace - Configuration Hygiene Issue" \
  --label "claude-code-generated-issue,P2,configuration,environment,backend,staging,configuration-drift" \
  --body-file "$ISSUE_BODY_FILE")

if [ $? -eq 0 ]; then
    echo "✅ Successfully created GitHub issue!"
    echo "🔗 Issue URL: $ISSUE_URL"
    echo ""
    
    # Extract issue number from URL
    ISSUE_NUMBER=$(echo "$ISSUE_URL" | grep -o '[0-9]*$')
    echo "📊 Issue Number: #$ISSUE_NUMBER"
    
    # Add additional context comment with log evidence
    echo "📝 Adding supplementary log evidence comment..."
    
    LOG_COMMENT="## Latest Log Evidence Summary

**Analysis Period:** 2025-09-15T21:38:00Z to 2025-09-15T22:38:00Z  
**Warning Count:** 19+ occurrences in last hour  
**Pattern:** SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'  

**Log Source Files:**
- \`gcp_backend_logs_last_1hour_20250915_143747.md\`
- \`gcp_backend_logs_last_1hour_20250915_143747.json\`  
- \`gcp_log_analysis_report.md\`

**Business Impact:**
- Configuration hygiene degradation
- 19+ warning logs per hour affecting monitoring signal-to-noise ratio
- Runtime sanitization overhead
- Potential service discovery confusion

**Immediate Action Required:**
1. Identify source of whitespace in SERVICE_ID environment variable definition
2. Clean configuration source (deployment scripts, Docker files, etc.)
3. Add pre-deployment validation to prevent recurrence
4. Monitor for elimination of warnings post-fix

This issue is part of broader configuration hygiene improvements for staging environment stability."

    echo "$LOG_COMMENT" | gh issue comment "$ISSUE_NUMBER" --body-file -
    
    echo "✅ Added supplementary log evidence comment"
    echo ""
    echo "🎯 Next Steps:"
    echo "1. Review the created issue at: $ISSUE_URL"
    echo "2. Assign appropriate team members"
    echo "3. Schedule resolution (estimated 1 hour total effort)"
    echo "4. Monitor staging logs for improvement post-fix"
    
else
    echo "❌ Failed to create GitHub issue"
    exit 1
fi

echo ""
echo "📋 Summary:"
echo "- Issue Type: P2 Configuration Hygiene"
echo "- Evidence: 19+ WARNING logs in last hour"
echo "- Impact: Service discovery, configuration validation"
echo "- Estimated Fix Time: 1 hour"
echo "- Prevention: Pre-deployment validation enhancement"
echo ""
echo "🔗 Issue URL: $ISSUE_URL"