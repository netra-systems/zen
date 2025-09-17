#!/bin/bash

# Create GitHub Issue for Critical Test Import Failures
# Priority: P0 Critical
# Business Impact: $500K+ ARR functionality validation blocked

echo "Creating GitHub issue for critical test import failures..."

# Method 1: Full comprehensive body
gh issue create \
  --title "P0 Critical Test Import Failures Blocking \$500K+ ARR Functionality Validation" \
  --body-file "GITHUB_ISSUE_CRITICAL_TEST_IMPORT_FAILURES_COMPREHENSIVE.md" \
  --label "test-infrastructure-critical" \
  --label "P0" \
  --label "critical" \
  --label "import-errors" \
  --label "websocket" \
  --label "golden-path" \
  --label "deployment-safety"

echo "GitHub issue creation command executed."
echo ""
echo "Alternative method using shorter body:"

# Method 2: Shorter body version
gh issue create \
  --title "P0 Critical Test Import Failures - 7 Import Error Patterns Blocking Mission Critical Tests" \
  --body-file "GITHUB_ISSUE_IMPORT_FAILURES_BODY.md" \
  --label "test-infrastructure-critical" \
  --label "P0" \
  --label "critical" \
  --label "import-errors"

echo ""
echo "Issue creation commands prepared and ready to execute."
echo "Files created:"
echo "  - GITHUB_ISSUE_CRITICAL_TEST_IMPORT_FAILURES_COMPREHENSIVE.md (full documentation)"
echo "  - GITHUB_ISSUE_IMPORT_FAILURES_BODY.md (concise version)"
echo "  - create_import_failures_issue.sh (this script)"
echo "  - github_issue_commands.txt (command reference)"