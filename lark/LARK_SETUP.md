# Lark Notifications for GitHub Actions

This integration allows you to send GitHub Actions notifications to Lark messenger.

## Setup Instructions

### 1. Create a Lark Webhook

1. Open Lark and navigate to the group chat where you want to receive notifications
2. Click on the group settings (gear icon)
3. Select "Bots" or "Group Bot"
4. Click "Add Bot" and choose "Custom Bot" or "Webhook"
5. Give your bot a name (e.g., "GitHub Actions")
6. Copy the webhook URL provided by Lark

### 2. Add Webhook URL to GitHub Secrets

1. Go to your GitHub repository settings
2. Navigate to "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add the following secrets:
   - Name: `LARK_WEBHOOK_URL`
   - Value: Your Lark webhook URL
   
   Optional: For separate alert notifications:
   - Name: `LARK_WEBHOOK_URL_ALERTS`
   - Value: Another Lark webhook URL for critical alerts

### 3. Usage Options

#### Option A: Automatic Notifications (All Workflows)

The `lark-notifications.yml` workflow automatically sends notifications for:
- Workflow completions (success/failure)
- Pull request events (opened/closed/merged)
- Issue events (opened/closed)
- Push to main branch
- Release publications

No additional configuration needed in your workflows.

#### Option B: Custom Notifications in Your Workflows

Use the reusable action in your workflows:

```yaml
- name: 'Send Lark Notification'
  uses: './.github/actions/lark-notify'
  with:
    webhook_url: ${{ secrets.LARK_WEBHOOK_URL }}
    title: 'Deployment Successful'
    message: 'Application deployed to production'
    color: 'green'
    status_emoji: '✅'
    buttons: |
      [
        {
          "text": "View Deployment",
          "url": "https://your-app.com",
          "type": "primary"
        }
      ]
```

#### Option C: Direct API Call

For simple notifications, you can also call the Lark API directly:

```yaml
- name: 'Quick Lark notification'
  run: |
    curl -X POST "${{ secrets.LARK_WEBHOOK_URL }}" \
      -H "Content-Type: application/json" \
      -d '{
        "msg_type": "text",
        "content": {
          "text": "Build completed successfully!"
        }
      }'
```

## Notification Types

### Card Messages (Rich formatting)
- Colored headers (blue, green, orange, red, purple, gray, yellow)
- Markdown support in content
- Action buttons
- Timestamps
- Multiple sections

### Text Messages (Simple)
- Plain text notifications
- Quick and simple
- Fallback option

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `LARK_WEBHOOK_URL` | Main webhook URL for notifications | Yes |
| `LARK_WEBHOOK_URL_ALERTS` | Separate webhook for critical alerts | No |

## Examples

### Example 1: Test Results Notification

```yaml
- name: 'Notify test results'
  if: always()
  uses: './.github/actions/lark-notify'
  with:
    webhook_url: ${{ secrets.LARK_WEBHOOK_URL }}
    title: 'Test Results'
    message: |
      **Tests:** ${{ steps.test.outcome }}
      **Coverage:** 95%
      **Failed:** 0
      **Passed:** 150
    color: ${{ steps.test.outcome == 'success' && 'green' || 'red' }}
    status_emoji: ${{ steps.test.outcome == 'success' && '✅' || '❌' }}
```

### Example 2: Deployment Notification

```yaml
- name: 'Notify deployment'
  uses: './.github/actions/lark-notify'
  with:
    webhook_url: ${{ secrets.LARK_WEBHOOK_URL }}
    title: 'Production Deployment'
    message: |
      **Version:** v1.2.3
      **Environment:** Production
      **Deployed by:** ${{ github.actor }}
    color: 'purple'
    status_emoji: '🚀'
    buttons: |
      [
        {"text": "View App", "url": "https://app.example.com", "type": "primary"},
        {"text": "View Logs", "url": "https://logs.example.com", "type": "default"}
      ]
```

### Example 3: Security Alert

```yaml
- name: 'Security alert'
  if: ${{ steps.security-scan.outcome == 'failure' }}
  uses: './.github/actions/lark-notify'
  with:
    webhook_url: ${{ secrets.LARK_WEBHOOK_URL_ALERTS }}
    title: 'Security Vulnerability Detected'
    message: |
      **Severity:** High
      **Package:** lodash
      **Version:** 4.17.20
      **Fix:** Update to 4.17.21
    color: 'red'
    status_emoji: '🚨'
```

## Customization

### Custom Workflow Events

Add more event types to `lark-notifications.yml`:

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily notifications
  deployment:
    types: [created]
  workflow_call:  # Can be called by other workflows
```

### Custom Message Formats

Modify the message preparation in the workflow to match your needs:
- Add more context from GitHub event data
- Include commit SHAs
- Add contributor information
- Include artifact links

## Troubleshooting

### Notifications not sending

1. Check that `LARK_WEBHOOK_URL` is set in repository secrets
2. Verify webhook URL is valid and active in Lark
3. Check workflow logs for error messages
4. Ensure Lark bot has permission to post in the channel

### Message formatting issues

1. Escape special characters in JSON
2. Use proper markdown syntax for Lark
3. Test with simple text messages first

### Rate limiting

Lark may rate limit webhook calls. Consider:
- Batching notifications
- Using conditional notifications
- Implementing retry logic with exponential backoff

## Security Notes

- Never commit webhook URLs directly in code
- Use GitHub Secrets for sensitive data
- Consider using separate webhooks for different environments
- Rotate webhook URLs periodically
- Limit webhook permissions in Lark to specific channels