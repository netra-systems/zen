# Commands to Create CRITICAL SSOT Test Framework Event Loop Issue

## Option 1: Using GitHub CLI (Recommended)
```bash
# First authenticate if needed:
gh auth login

# Create the issue:
gh issue create \
  --title "🚨 CRITICAL: SSOT Test Framework Event Loop Failure Blocking All Integration Tests" \
  --body-file "C:\netra-apex\github_issue_ssot_event_loop_critical.md" \
  --label "critical,test-infrastructure,ssot,event-loop,blocking,golden-path,mission-critical,p0"
```

## Option 2: Manual GitHub Web Interface
1. Go to: https://github.com/netra-systems/netra-apex/issues/new
2. Copy the title: `🚨 CRITICAL: SSOT Test Framework Event Loop Failure Blocking All Integration Tests`
3. Copy the body from: `C:\netra-apex\github_issue_ssot_event_loop_critical.md`
4. Add labels: `critical`, `test-infrastructure`, `ssot`, `event-loop`, `blocking`, `golden-path`, `mission-critical`, `p0`
5. Submit the issue

## Option 3: Alternative CLI Command (if first fails)
```bash
# Read the issue body into a variable and create
gh issue create \
  --title "🚨 CRITICAL: SSOT Test Framework Event Loop Failure Blocking All Integration Tests" \
  --body "$(cat github_issue_ssot_event_loop_critical.md)" \
  --label critical \
  --label test-infrastructure \
  --label ssot \
  --label event-loop \
  --label blocking \
  --label golden-path \
  --label mission-critical \
  --label p0
```

## Expected Issue Number
Based on recent issue creation patterns, this should create issue #1280+ (estimated)

## Cleanup After Issue Creation
```bash
# Keep issue documentation for reference, remove creation commands
rm "C:\netra-apex\create_ssot_event_loop_issue_commands.md"
```

## Follow-up Commands After Issue Creation
```bash
# Check issue was created successfully
gh issue list --label "critical" --limit 5

# Add initial comment with technical analysis if needed
gh issue comment <ISSUE_NUMBER> --body "Initial technical analysis confirms this is blocking all business-critical test validation. Priority fix required for deployment confidence."
```