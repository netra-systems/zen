#!/bin/bash

echo "GCP Log Gardener - GitHub Issue Updates"
echo "========================================"
echo ""
echo "This script will execute the following GitHub operations:"
echo ""
echo "1. UPDATE Issue #1278 (503 Health Check Failures)"
echo "   - Add comment with latest log analysis"
echo "   - Confirm VPC Connector root cause"
echo ""
echo "2. CREATE New Issue (Empty Log Payloads)"
echo "   - P2 severity observability gap"
echo "   - 92% of ERROR/WARNING logs affected"
echo ""

read -p "Do you want to proceed? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Updating Issue #1278..."
    gh issue comment 1278 < issue-1278-update-comment.md

    echo "Creating new issue for empty log payloads..."
    chmod +x create-empty-logs-issue.sh
    ./create-empty-logs-issue.sh

    echo ""
    echo "GitHub updates complete!"
else
    echo "GitHub updates cancelled."
fi