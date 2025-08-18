# ACT Local Testing Guide

## Overview

ACT enables local execution of GitHub Actions workflows, providing a validation loop before deployment and the ability to manually trigger workflows locally.

## Quick Start

### Installation

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows
choco install act-cli
```

### Prerequisites

- Docker Desktop installed and running
- Python 3.11+
- Project dependencies installed

## Using the ACT Wrapper

### Basic Commands

```bash
# List all workflows
python scripts/act_wrapper.py list

# Validate all workflows
python scripts/act_wrapper.py validate

# Run a specific workflow
python scripts/act_wrapper.py run test-smoke

# Run a specific job
python scripts/act_wrapper.py run ci-enhanced --job lint

# Run staging deployment locally
python scripts/act_wrapper.py staging-deploy --env staging
```

### Workflow Validation

```bash
# Validate workflow syntax and ACT compatibility
python scripts/workflow_validator.py

# This checks:
# - YAML syntax validity
# - GitHub Actions schema compliance
# - ACT compatibility issues
# - Required secrets availability
```

## Secrets Management

### Initialize Secrets Storage

```bash
# Initialize encrypted secrets store
python scripts/local_secrets_manager.py init

# Add secrets
python scripts/local_secrets_manager.py add GITHUB_TOKEN
python scripts/local_secrets_manager.py add NPM_TOKEN --value "npm_xxx"

# List stored secrets
python scripts/local_secrets_manager.py list

# Export to ACT format
python scripts/local_secrets_manager.py export

# Import from environment
python scripts/local_secrets_manager.py import
```

### Required Secrets

Create `.act.secrets` file with:
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
NPM_TOKEN=npm_xxxxxxxxxxxx
DOCKER_PASSWORD=xxxxxxxxxxxx
TEST_DATABASE_URL=sqlite:///test.db
TEST_REDIS_URL=redis://localhost:6379
```

## Environment Configuration

Create `.act.env` file with:
```
# Local testing configuration
LOCAL_DEPLOY=true
ACT_VERBOSE=true
ACT_DRY_RUN=false
ACT_MOCK_SERVICES=true
ACT_SKIP_EXTERNAL=true
```

## Workflow Categories

### Test Workflows
```bash
# Run unit tests locally
act push -W .github/workflows/test-unit.yml

# Run smoke tests
act push -W .github/workflows/test-smoke.yml

# Run comprehensive tests
act workflow_dispatch -W .github/workflows/test-comprehensive.yml
```

### CI/CD Workflows
```bash
# Run CI pipeline
act push -W .github/workflows/ci-enhanced.yml

# Run pipeline optimization
act workflow_dispatch -W .github/workflows/pipeline-optimization.yml
```

### Staging Workflows
```bash
# Deploy to local staging
act workflow_dispatch -W .github/workflows/staging-environment.yml \
  --input environment=staging \
  --input action=deploy

# Check staging status
act workflow_dispatch -W .github/workflows/staging-workflows/status.yml
```

### Monitoring Workflows
```bash
# Run health monitoring
act schedule -W .github/workflows/health-monitoring.yml

# Check architecture health
act workflow_dispatch -W .github/workflows/architecture-health.yml
```

### AI/Gemini Workflows
```bash
# Test AI autofix (dry-run)
act workflow_dispatch -W .github/workflows/ai-autofix.yml \
  --input dry_run=true

# Test PR review
act pull_request -W .github/workflows/gemini-pr-review.yml
```

### Infrastructure Workflows
```bash
# Test terraform operations (dry-run)
ACT_DRY_RUN=true act schedule -W .github/workflows/terraform-lock-cleanup.yml

# Test boundary enforcement
act push -W .github/workflows/boundary-enforcement.yml

# Test orchestrator
act workflow_dispatch -W .github/workflows/orchestrator.yml
```

## ACT Compatibility Features

### Environment Detection
All workflows detect ACT using:
```yaml
env:
  ACT: ${{ env.ACT || 'false' }}
```

### Runner Compatibility
**IMPORTANT:** All GitHub Actions workflows MUST use `warp-custom-default` runner in production.
ACT automatically overrides this for local testing:
```yaml
# For production workflows (MANDATORY):
runs-on: warp-custom-default

# For ACT compatibility (optional):
runs-on: ${{ github.event.act && 'ubuntu-latest' || 'warp-custom-default' }}
```
Note: The `warp-custom-default` runner is MANDATORY for all workflows. Never use `ubuntu-latest` directly.

### Mock Services
- **GitHub API**: Skipped in ACT mode
- **External APIs**: Mock responses provided
- **Cloud Services**: Local alternatives used
- **Artifacts**: Stored locally in `act-results/`

### Local Storage
Test results and artifacts stored in:
- `act-results/` - Test outputs
- `/tmp/act-artifacts/` - Build artifacts
- `.act.secrets` - Encrypted secrets
- `.act.env` - Environment variables

## Troubleshooting

### Common Issues

**Docker not running**
```bash
# Start Docker Desktop
# macOS: open -a Docker
# Linux: sudo systemctl start docker
# Windows: Start Docker Desktop from Start Menu
```

**Missing secrets**
```bash
# Check required secrets
python scripts/workflow_validator.py

# Add missing secrets
python scripts/local_secrets_manager.py add SECRET_NAME
```

**Workflow syntax errors**
```bash
# Validate before running
python scripts/workflow_validator.py

# Check specific workflow
act -l -W .github/workflows/workflow-name.yml
```

**Resource constraints**
```bash
# Limit parallel jobs
act -j 1

# Use lighter container
act -P ubuntu-latest=node:16-slim
```

## Best Practices

### 1. Validate First
Always validate workflows before running:
```bash
python scripts/workflow_validator.py
```

### 2. Use Dry-Run Mode
Test destructive operations safely:
```bash
ACT_DRY_RUN=true act workflow_dispatch -W .github/workflows/staging-cleanup.yml
```

### 3. Start Small
Begin with simple workflows:
```bash
# Start with smoke tests
act push -W .github/workflows/test-smoke.yml

# Then move to complex workflows
act push -W .github/workflows/ci-enhanced.yml
```

### 4. Monitor Resources
ACT can be resource-intensive:
- Close unnecessary applications
- Limit parallel jobs with `-j 1`
- Use lightweight containers when possible

### 5. Keep Secrets Secure
- Never commit `.act.secrets` or `.act.env`
- Use encrypted storage for sensitive data
- Rotate secrets regularly

## Advanced Usage

### Custom Event Payloads
```bash
# Create event.json
echo '{"pull_request": {"number": 123}}' > event.json

# Run with custom event
act pull_request -e event.json
```

### Specific Platform
```bash
# Use specific container
act -P ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-latest
```

### Debug Mode
```bash
# Enable verbose output
act -v push

# Super verbose (debug)
act -vv push
```

### Reuse Containers
```bash
# Keep containers for debugging
act --reuse push
```

## Integration with Dev Launcher

The ACT wrapper integrates with the dev launcher:

```python
# In dev_launcher.py, add:
if args.test_workflows:
    subprocess.run(["python", "scripts/act_wrapper.py", "validate"])
    subprocess.run(["python", "scripts/act_wrapper.py", "run", "test-smoke"])
```

## Workflow Examples

### Complete Test Suite
```bash
#!/bin/bash
# run_local_tests.sh

# Validate workflows
python scripts/workflow_validator.py

# Run test suite
python scripts/act_wrapper.py run test-smoke
python scripts/act_wrapper.py run test-unit
python scripts/act_wrapper.py run test-comprehensive
```

### Staging Deployment
```bash
#!/bin/bash
# deploy_local_staging.sh

# Setup secrets
python scripts/local_secrets_manager.py export

# Deploy staging
python scripts/act_wrapper.py staging-deploy --env staging

# Check status
act workflow_dispatch -W .github/workflows/staging-workflows/status.yml
```

## Summary

ACT integration provides:
- **Pre-deployment validation** of workflows
- **Local testing** without GitHub Actions minutes
- **Faster feedback** during development
- **Cost savings** on CI/CD resources
- **Offline development** capability

All workflows maintain dual compatibility, working seamlessly in both GitHub Actions and ACT environments.