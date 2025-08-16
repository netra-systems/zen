# PR Comment Updater Action

A GitHub Action for managing PR comments with support for finding, updating, or creating comments based on unique identifiers. This action follows the comment management patterns from the Netra AI Platform's master workflow architecture.

## Features

- **Smart Comment Management**: Finds existing comments by identifier and updates them, or creates new ones
- **Template Support**: Process template variables in comment content
- **Flexible Identification**: Uses HTML comment identifiers for reliable comment tracking
- **Error Handling**: Configurable failure behavior with detailed logging
- **Integration Ready**: Designed to work with deployment status and test result comments

## Usage

### Basic Example

```yaml
- name: Update Deployment Comment
  uses: ./.github/actions/comment-updater
  with:
    identifier: '<!-- netra-staging-deployment -->'
    content: |
      ## 🚀 Deployment Status
      
      **Environment:** `staging`
      **Status:** ✅ Success
      
      **Frontend:** https://staging.example.com
      **Backend:** https://api-staging.example.com
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Advanced Example with Template Variables

```yaml
- name: Update Test Results Comment
  uses: ./.github/actions/comment-updater
  with:
    identifier: '<!-- netra-test-results -->'
    template-variables: |
      {
        "unit_status": "✅ Passed",
        "unit_coverage": "95",
        "unit_duration": "2m 15s",
        "int_status": "✅ Passed", 
        "int_coverage": "88",
        "int_duration": "5m 30s",
        "e2e_status": "✅ Passed",
        "e2e_duration": "12m 45s",
        "total_coverage": "92"
      }
    content: |
      ## ✅ Test Results
      
      | Test Type | Status | Coverage | Duration |
      |-----------|--------|----------|----------|
      | Unit | {{ unit_status }} | {{ unit_coverage }}% | {{ unit_duration }} |
      | Integration | {{ int_status }} | {{ int_coverage }}% | {{ int_duration }} |
      | E2E | {{ e2e_status }} | - | {{ e2e_duration }} |
      
      **Overall Coverage:** {{ total_coverage }}%
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Deployment Status Example

```yaml
- name: Update Deployment Status
  uses: ./.github/actions/comment-updater
  with:
    identifier: '<!-- netra-staging-deployment -->'
    content: |
      ## 🚀 Deployment Status
      
      **Environment:** `${{ inputs.environment }}`
      **Status:** ${{ job.status == 'success' && '✅ Success' || '❌ Failed' }}
      
      ${{ job.status == 'success' && format('
      ### Access URLs:
      - **Frontend:** {0}
      - **Backend:** {1}
      - **API Docs:** {1}/docs
      
      ### Deployment Info:
      - **Commit:** {2}
      - **Deployed:** {3}
      - **Version:** {4}
      ', env.FRONTEND_URL, env.BACKEND_URL, github.sha, env.DEPLOY_TIME, env.VERSION) || format('
      ### Error Details:
      ```
      {0}
      ```
      [View Logs]({1})
      ', env.ERROR_MESSAGE, env.WORKFLOW_URL) }}
      
      ### Actions:
      - 🔄 **Rebuild:** Run workflow with `action=rebuild`
      - 🗑️ **Destroy:** Close PR or run with `action=destroy`
    github-token: ${{ secrets.GITHUB_TOKEN }}
    fail-on-error: false
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `identifier` | Unique HTML comment identifier (e.g., `<!-- netra-staging-deployment -->`) | ✅ Yes | - |
| `content` | Comment content to set (supports template variables) | ✅ Yes | - |
| `template-variables` | JSON object containing template variables for content substitution | ❌ No | `{}` |
| `github-token` | GitHub token for API operations | ❌ No | `${{ github.token }}` |
| `pr-number` | Pull request number (auto-detected if not provided) | ❌ No | Auto-detected |
| `fail-on-error` | Whether to fail the action if comment update fails | ❌ No | `true` |

## Outputs

| Output | Description |
|--------|-------------|
| `comment-id` | ID of the created or updated comment |
| `comment-url` | URL of the created or updated comment |
| `operation` | Operation performed: "created" or "updated" |
| `success` | Whether the operation was successful |

## Comment Identifiers

The action uses HTML comment identifiers to reliably track and update specific comments. Common identifiers used in the Netra AI Platform:

- `<!-- netra-staging-deployment -->` - Staging deployment status
- `<!-- netra-test-results -->` - Test execution results
- `<!-- netra-security-scan -->` - Security scan results
- `<!-- netra-performance -->` - Performance test results

## Template Variables

The action supports basic template variable substitution in the content. Variables should be provided as a JSON object and referenced in the content using `{{ variable_name }}` syntax.

### Example Template Processing

```yaml
template-variables: |
  {
    "status": "success",
    "environment": "staging",
    "url": "https://staging.example.com"
  }
content: |
  Deployment {{ status }} to {{ environment }}
  Access at: {{ url }}
```

## Error Handling

The action provides flexible error handling:

- **`fail-on-error: true`** (default): Action fails if comment operation fails
- **`fail-on-error: false`**: Action continues with warning if comment operation fails

All operations are logged with detailed information for debugging.

## Permissions Required

The action requires the following GitHub token permissions:

```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write
```

## Integration with Master Workflow

This action is designed to integrate with the Netra AI Platform's master workflow architecture:

```yaml
jobs:
  deploy:
    runs-on: warp-custom-default
    permissions:
      contents: read
      pull-requests: write
      issues: write
      deployments: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy Application
        id: deploy
        run: |
          # Deployment logic here
          
      - name: Update Deployment Comment
        if: always()
        uses: ./.github/actions/comment-updater
        with:
          identifier: '<!-- netra-staging-deployment -->'
          content: |
            ## 🚀 Deployment Status
            **Status:** ${{ steps.deploy.outcome == 'success' && '✅ Success' || '❌ Failed' }}
            **Environment:** staging
```

## Best Practices

1. **Consistent Identifiers**: Use consistent HTML comment identifiers across workflows
2. **Error Handling**: Set `fail-on-error: false` for non-critical comment updates
3. **Content Templates**: Use template variables for dynamic content
4. **Permissions**: Always include required permissions in workflow
5. **Conditional Updates**: Use `if: always()` to update comments even on job failure

## Troubleshooting

### Common Issues

1. **Permission Denied (403)**
   - Ensure `pull-requests: write` and `issues: write` permissions are set
   - Verify GitHub token has sufficient permissions

2. **PR Number Not Found**
   - Provide explicit `pr-number` input for non-PR events
   - Ensure action runs in PR context or provide PR number

3. **Template Variables Not Processed**
   - Verify JSON format of `template-variables` input
   - Check variable names match between input and content

### Debug Mode

Enable debug logging by setting repository secrets:
- `ACTIONS_STEP_DEBUG=true`
- `ACTIONS_RUNNER_DEBUG=true`

## Architecture Compliance

This action follows the Netra AI Platform architecture requirements:

- ✅ **Module-based**: Single responsibility action under 300 lines
- ✅ **Type Safety**: All inputs/outputs properly typed
- ✅ **Error Handling**: Comprehensive error handling and logging
- ✅ **Documentation**: Complete usage documentation
- ✅ **Integration**: Designed for master workflow architecture

## References

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [GitHub Script Action](https://github.com/actions/github-script)
- [Netra AI Platform Specifications](../../SPEC/MASTER_GITHUB_WORKFLOW.xml)