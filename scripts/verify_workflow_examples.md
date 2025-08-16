# GitHub Workflow Status Verification Examples

This document provides examples of how to use `verify_workflow_status.py` in various scenarios.

## Basic Usage

### Check specific workflow run by ID
```bash
python scripts/verify_workflow_status.py \
  --repo "owner/repository" \
  --run-id 123456789 \
  --token "$GITHUB_TOKEN"
```

### Check latest run of a workflow by name
```bash
python scripts/verify_workflow_status.py \
  --repo "owner/repository" \
  --workflow-name "test-suite" \
  --token "$GITHUB_TOKEN"
```

### Wait for workflow completion
```bash
python scripts/verify_workflow_status.py \
  --repo "owner/repository" \
  --workflow-name "deploy-staging" \
  --wait-for-completion \
  --timeout 3600 \
  --token "$GITHUB_TOKEN"
```

## GitHub Actions Integration

### In workflow steps
```yaml
- name: Verify deployment workflow
  run: |
    python scripts/verify_workflow_status.py \
      --repo "${{ github.repository }}" \
      --workflow-name "deploy-staging" \
      --wait-for-completion \
      --timeout 1800 \
      --token "${{ secrets.GITHUB_TOKEN }}"
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Using environment variable for token
```bash
export GITHUB_TOKEN="your_token_here"
python scripts/verify_workflow_status.py \
  --repo "owner/repository" \
  --workflow-name "test-suite"
```

## Output Formats

### Table output (default)
```bash
python scripts/verify_workflow_status.py \
  --repo "owner/repository" \
  --workflow-name "test-suite" \
  --output table
```

### JSON output for scripting
```bash
python scripts/verify_workflow_status.py \
  --repo "owner/repository" \
  --workflow-name "test-suite" \
  --output json | jq '.[] | .conclusion'
```

## Exit Codes

- `0`: Workflow completed successfully
- `1`: Workflow failed, error occurred, or validation failed

## Advanced Examples

### Poll with custom intervals
```bash
python scripts/verify_workflow_status.py \
  --repo "owner/repository" \
  --workflow-name "long-running-test" \
  --wait-for-completion \
  --poll-interval 60 \
  --timeout 7200
```

### Script integration with error handling
```bash
#!/bin/bash
set -e

REPO="owner/repository"
WORKFLOW="deploy-production"

echo "Starting production deployment verification..."

if python scripts/verify_workflow_status.py \
  --repo "$REPO" \
  --workflow-name "$WORKFLOW" \
  --wait-for-completion \
  --timeout 3600; then
  echo "Deployment completed successfully!"
  # Continue with post-deployment tasks
else
  echo "Deployment failed!"
  # Handle failure case
  exit 1
fi
```

## Integration with MASTER_GITHUB_WORKFLOW.xml

This script implements the "API Verify" requirement from MASTER_GITHUB_WORKFLOW.xml:

> "API Verify: All workflows must be verified to completion success via Github Python Workflow Status script."

Use this script to:
1. Verify staging deployments complete successfully
2. Wait for test workflows before proceeding with deployments
3. Validate production deployments in CI/CD pipelines
4. Monitor long-running workflows programmatically

## Error Handling

The script provides detailed error messages and appropriate exit codes for:
- Missing authentication tokens
- Invalid repository names
- Network connectivity issues
- API rate limiting
- Workflow timeouts

## Dependencies

Required packages (already in requirements.txt):
- `httpx` - HTTP client for GitHub API
- `rich` - Console output formatting
- `tenacity` - Retry logic for API calls