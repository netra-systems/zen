#!/bin/bash

# Script to create GitHub issues based on Issue #1029 analysis
# Run this script after getting approval for gh commands

echo "Creating GitHub issues based on Issue #1029 analysis..."

# Issue 1: Startup Validation Architecture
echo "Creating Issue 1: Startup Validation Architecture..."
ISSUE1=$(gh issue create \
  --title "Redesign Startup Validation Architecture to Prevent Circular Dependencies" \
  --body-file "C:\netra-apex\issue_1_startup_validation_architecture.md" \
  --label "enhancement,architecture,high-priority" \
  --assignee "@me")

echo "Created Issue 1: $ISSUE1"

# Issue 2: Documentation and Diagrams
echo "Creating Issue 2: Documentation and Diagrams..."
ISSUE2=$(gh issue create \
  --title "Create Comprehensive Startup Sequence Documentation and Diagrams" \
  --body-file "C:\netra-apex\issue_2_startup_documentation_diagrams.md" \
  --label "documentation,enhancement,medium-priority" \
  --assignee "@me")

echo "Created Issue 2: $ISSUE2"

# Issue 3: Monitoring Improvements
echo "Creating Issue 3: Monitoring Improvements..."
ISSUE3=$(gh issue create \
  --title "Implement Advanced Startup Monitoring and Circular Dependency Detection" \
  --body-file "C:\netra-apex\issue_3_startup_monitoring_improvements.md" \
  --label "enhancement,monitoring,high-priority" \
  --assignee "@me")

echo "Created Issue 3: $ISSUE3"

# Issue 4: Error Message Cleanup
echo "Creating Issue 4: Error Message Cleanup..."
ISSUE4=$(gh issue create \
  --title "Clean Up Misleading Error Messages and Improve Error Attribution" \
  --body-file "C:\netra-apex\issue_4_error_message_cleanup.md" \
  --label "enhancement,developer-experience,medium-priority" \
  --assignee "@me")

echo "Created Issue 4: $ISSUE4"

# Create comment on Issue #1029
echo "Adding summary comment to Issue #1029..."
COMMENT_BODY=$(cat "C:\netra-apex\issue_1029_summary_comment.md" | sed "s/\[Issue #XXXX\]/Issue $ISSUE1/g" | sed "s/\[Issue #YYYY\]/Issue $ISSUE2/g" | sed "s/\[Issue #ZZZZ\]/Issue $ISSUE3/g" | sed "s/\[Issue #AAAA\]/Issue $ISSUE4/g")

gh issue comment 1029 --body "$COMMENT_BODY"

echo "Summary comment added to Issue #1029"

echo "All issues created successfully!"
echo "Issue 1 (Architecture): $ISSUE1"
echo "Issue 2 (Documentation): $ISSUE2"
echo "Issue 3 (Monitoring): $ISSUE3"
echo "Issue 4 (Error Messages): $ISSUE4"
echo ""
echo "Next step: Close Issue #1029 as resolved"