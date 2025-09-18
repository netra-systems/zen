#!/bin/bash

# Add resolution status comment to GitHub issue #1278
gh issue comment 1278 --body-file /Users/anthony/Desktop/netra-apex/issue_1278_resolution_status.md

# Remove the actively-being-worked-on label since the issue is resolved
gh issue edit 1278 --remove-label "actively-being-worked-on"

# Add a resolved label if it exists
gh issue edit 1278 --add-label "resolved" 2>/dev/null || echo "Note: 'resolved' label may not exist"

echo "Resolution status added to issue #1278"
echo "Issue is ready for closure - all fixes are committed and deployed"