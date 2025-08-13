# GitHub Actions Configuration

This directory contains GitHub Actions workflows and configurations for CI/CD pipeline.

## 📁 Directory Structure

```
.github/
├── workflows/           # GitHub Actions workflow files
│   ├── staging-environment.yml # Staging deployment management
│   └── test-suite.yml          # Comprehensive test execution
├── actions/            # Reusable composite actions
│   └── command-executor/# Execute commands
└── templates/          # Workflow templates (if needed)
```

Note: Lark integration components have been moved to `work_in_progress/` folder for future implementation.

## 🚀 Quick Start

### Available Workflows

#### Staging Environment (`staging-environment.yml`)
Manages staging deployments for pull requests.

**Triggers:**
- Pull request opened/synchronized/closed
- Manual deployment via workflow dispatch

**Commands:**
```bash
# Via GitHub CLI
gh workflow run staging-environment.yml -f action=deploy -f pr_number=123
gh workflow run staging-environment.yml -f action=destroy -f pr_number=123
```

#### Test Suite (`test-suite.yml`)
Comprehensive test execution with multiple levels.

**Test Levels:**
- `smoke`: Quick validation (< 30s)
- `unit`: Component tests (1-2 min)
- `integration`: Feature tests (3-5 min)
- `comprehensive`: Full coverage (10-15 min)
- `critical`: Essential paths (1-2 min)

**Triggers:**
- Pull requests with code changes
- Manual via workflow dispatch
- Daily schedule (2 AM UTC)

## 🔧 Reusable Actions

### Command Executor
Execute various commands and operations.

```yaml
- uses: ./.github/actions/command-executor
  with:
    command: staging-deploy
    params: '{"pr_number": "123"}'
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## 📋 Required Secrets

Configure these in your GitHub repository settings:

- `GCP_SA_KEY`: Google Cloud Platform service account key
- `TF_STATE_BUCKET`: Terraform state storage bucket name
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

## 🧪 Testing

### Running Tests Locally

```bash
# Run unit tests
python test_runner.py --level unit

# Run specific test level
python test_runner.py --level integration

# Run with coverage
python test_runner.py --level comprehensive --coverage
```

### Triggering Tests via GitHub

```bash
# Manual trigger
gh workflow run test-suite.yml -f test_level=unit

# Check status
gh run list --workflow=test-suite.yml
```

## 📦 Deployment

### Staging Deployments

Staging environments are automatically created for pull requests:

1. Open a PR → Staging environment deployed
2. Push updates → Environment updated
3. Close PR → Environment destroyed

### Manual Deployment

```bash
# Deploy staging for PR #123
gh workflow run staging-environment.yml \
  -f action=deploy \
  -f pr_number=123

# Check deployment status
gh run list --workflow=staging-environment.yml
```

## 🔍 Monitoring

### Workflow Status

```bash
# List recent workflow runs
gh run list --limit 10

# View specific run details
gh run view <run-id>

# Watch run in real-time
gh run watch <run-id>
```

### Logs

```bash
# Download logs for a run
gh run download <run-id>

# View logs in terminal
gh run view <run-id> --log
```

## 🆘 Troubleshooting

### Common Issues

1. **Workflow not triggering**
   - Check workflow file syntax
   - Verify trigger conditions
   - Check repository settings

2. **Test failures**
   - Review test logs in Actions tab
   - Check test artifacts
   - Run tests locally to debug

3. **Deployment issues**
   - Verify GCP credentials
   - Check Terraform state
   - Review deployment logs

### Debug Mode

Enable debug logging:
```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
  ACTIONS_STEP_DEBUG: true
```

## 📚 Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub CLI Manual](https://cli.github.com/manual/)