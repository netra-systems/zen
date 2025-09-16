#!/bin/bash

# GitHub Issue Creation Script for Middleware Setup Failure
# This script creates a new GitHub issue for the middleware setup critical failure cascade

# Issue details
TITLE="GCP-regression | P0 | Middleware Setup Critical Failure Cascade"
LABELS="claude-code-generated-issue,P0,middleware,regression,critical,cascade-failure"
BODY_FILE="github_issue_middleware_setup_failure.md"

# Create the GitHub issue
echo "Creating GitHub issue for middleware setup failure..."
echo "Title: $TITLE"
echo "Labels: $LABELS"
echo "Body file: $BODY_FILE"

# Command to run (requires GitHub CLI authentication)
gh issue create \
    --title "$TITLE" \
    --body-file "$BODY_FILE" \
    --label "$LABELS"

echo "Issue creation command executed."
echo ""
echo "To manually create this issue:"
echo "1. Go to GitHub repository issues page"
echo "2. Click 'New Issue'"
echo "3. Copy content from $BODY_FILE"
echo "4. Add labels: $LABELS"
echo "5. Submit with title: $TITLE"