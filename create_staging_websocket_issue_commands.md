# Commands to Create Critical Staging WebSocket Issue

## Option 1: Using GitHub CLI (Recommended)
```bash
# First authenticate if needed:
gh auth login

# Create the issue:
gh issue create \
  --title "🚨 CRITICAL: Staging WebSocket Infrastructure Complete Breakdown - Mission Critical Test Failures" \
  --body-file "C:\netra-apex\temp_critical_staging_websocket_issue.md" \
  --label "critical,staging,websocket,infrastructure,golden-path,mission-critical,p0"
```

## Option 2: Manual GitHub Web Interface
1. Go to: https://github.com/your-org/netra-apex/issues/new
2. Copy the title: `🚨 CRITICAL: Staging WebSocket Infrastructure Complete Breakdown - Mission Critical Test Failures`
3. Copy the body from: `C:\netra-apex\temp_critical_staging_websocket_issue.md`
4. Add labels: `critical`, `staging`, `websocket`, `infrastructure`, `golden-path`, `mission-critical`, `p0`
5. Submit the issue

## Option 3: Alternative CLI Command (if first fails)
```bash
# Read the issue body into a variable and create
gh issue create \
  --title "🚨 CRITICAL: Staging WebSocket Infrastructure Complete Breakdown - Mission Critical Test Failures" \
  --body "$(cat temp_critical_staging_websocket_issue.md)" \
  --label critical \
  --label staging \
  --label websocket \
  --label infrastructure \
  --label golden-path \
  --label mission-critical \
  --label p0
```

## Cleanup After Issue Creation
```bash
# Remove temporary files
rm "C:\netra-apex\temp_critical_staging_websocket_issue.md"
rm "C:\netra-apex\create_staging_websocket_issue_commands.md"
```