#!/bin/bash

# Add final update comment to Issue #1278
gh issue comment 1278 --body-file issue_1278_final_update.md

# Update issue labels
gh issue edit 1278 --remove-label "actively-being-worked-on" --add-label "infrastructure-team-required,application-resilience-complete"

echo "Issue #1278 updated with final status and handed off to infrastructure team"