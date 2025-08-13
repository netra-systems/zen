# GitHub Actions & Lark Integration

This directory contains GitHub Actions workflows and configurations for CI/CD pipeline and Lark messaging integration.

## 📁 Directory Structure

```
.github/
├── workflows/           # GitHub Actions workflow files
│   ├── lark-integration.yml    # Main Lark integration hub
│   ├── staging-environment.yml # Staging deployment management
│   └── test-suite.yml          # Comprehensive test execution
├── actions/            # Reusable composite actions
│   ├── lark-notifier/  # Send notifications to Lark
│   ├── lark-status/    # Send status updates to Lark
│   └── command-executor/# Execute Lark commands
├── config/             # Configuration files
│   ├── secrets.yml     # Secret requirements documentation
│   └── environments.yml# Environment configurations
└── templates/          # Workflow templates (if needed)
```

## 🚀 Quick Start

### 1. Setting Up Lark Integration

1. **Deploy Lark Bot Server**
   - Use the server code from the original `lark_github_integration.xml`
   - Deploy to Vercel, Netlify, or your preferred platform
   - Note the deployment URL

2. **Configure Secrets**
   ```bash
   # Required secrets in GitHub repository settings:
   LARK_BOT_URL=https://your-bot-server.vercel.app
   LARK_WEBHOOK_URL=https://open.larksuite.com/open-apis/bot/v2/hook/xxx
   GCP_SA_KEY=<your-gcp-service-account-key>
   TF_STATE_BUCKET=your-terraform-state-bucket
   ```

3. **Set Up Lark App**
   - Create app at https://open.larksuite.com/app
   - Add bot to your Lark groups
   - Configure webhook URLs

### 2. Available Workflows

#### Lark Integration Hub (`lark-integration.yml`)
Main workflow that handles all Lark-GitHub communication.

**Triggers:**
- Workflow completions
- Pull request events
- Lark commands via repository dispatch
- Manual workflow dispatch

**Features:**
- Automatic notifications to Lark channels
- Command execution from Lark
- Interactive status updates

#### Staging Environment (`staging-environment.yml`)
Manages staging deployments for pull requests.

**Triggers:**
- Pull request opened/synchronized/closed
- Manual deployment via workflow dispatch
- Lark commands (deploy/destroy/restart)

**Commands:**
```bash
# Via Lark
/staging deploy 123
/staging destroy 123
/staging status 123

# Via GitHub CLI
gh workflow run staging-environment.yml -f action=deploy -f pr_number=123
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
- Lark commands
- Daily schedule (2 AM UTC)

## 🔧 Reusable Actions

### Lark Notifier
Send notifications to Lark channels.

```yaml
- uses: ./.github/actions/lark-notifier
  with:
    type: error
    status: failure
    webhook_url: ${{ secrets.LARK_WEBHOOK_URL }}
    title: Build Failed
    message: Error details here
```

### Lark Status
Send status updates for long-running operations.

```yaml
- uses: ./.github/actions/lark-status
  with:
    status: starting
    environment: staging-pr-123
    action: deploy
    webhook_url: ${{ secrets.LARK_WEBHOOK_URL }}
```

### Command Executor
Execute commands received from Lark.

```yaml
- uses: ./.github/actions/command-executor
  with:
    command: staging-deploy
    params: '{"pr_number": "123"}'
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## 📋 Lark Commands

Available commands in Lark chat:

| Command | Description | Example |
|---------|-------------|---------|
| `/staging [action] [pr]` | Manage staging environments | `/staging deploy 123` |
| `/test [level]` | Run test suite | `/test comprehensive` |
| `/workflow run [name]` | Trigger workflow | `/workflow run deploy` |
| `/workflow cancel [id]` | Cancel running workflow | `/workflow cancel 12345` |
| `/status` | Check workflow status | `/status` |
| `/help` | Show available commands | `/help` |

## 🔐 Required Secrets

See `.github/config/secrets.yml` for detailed secret requirements.

**Essential secrets:**
- `LARK_BOT_URL`: Lark bot server URL
- `LARK_WEBHOOK_URL`: Lark webhook for notifications
- `GCP_SA_KEY`: GCP service account for deployments
- `TF_STATE_BUCKET`: Terraform state storage
- `GITHUB_TOKEN`: GitHub PAT with workflow permissions

## 🌍 Environments

Configured environments with protection rules:

| Environment | Branch Policy | Reviewers | Wait Time |
|-------------|--------------|-----------|-----------|
| development | any | 0 | 0 min |
| staging | feature/*, fix/* | 0 | 0 min |
| production | main, release/* | 2 | 5 min |

## 🔄 Workflow Triggers

| Workflow | PR | Schedule | Manual | Lark | Push |
|----------|-----|----------|--------|------|------|
| lark-integration | ✅ | ❌ | ✅ | ✅ | ❌ |
| staging-environment | ✅ | ❌ | ✅ | ✅ | ❌ |
| test-suite | ✅ | ✅ | ✅ | ✅ | ❌ |

## 📊 Monitoring

### Success Metrics
- Workflow success rate
- Deployment duration
- Test execution time
- Error resolution time

### Notifications
- **General Channel**: All workflow completions
- **Alerts Channel**: Failures and errors
- **Staging Channel**: Staging deployments

## 🐛 Troubleshooting

### Common Issues

1. **Lark bot not responding**
   - Check bot server logs
   - Verify environment variables
   - Ensure webhook URLs are correct

2. **Staging deployment fails**
   - Check GCP credentials
   - Verify Terraform state bucket access
   - Review Cloud Run logs

3. **Tests timing out**
   - Increase timeout in workflow
   - Check for hanging tests
   - Review resource limits

### Debug Commands

```bash
# Check workflow runs
gh run list --limit 10

# View workflow logs
gh run view <run-id> --log

# Trigger workflow manually
gh workflow run <workflow-name> -f param=value

# Check secrets
gh secret list
```

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Lark Open Platform](https://open.larksuite.com/document)
- [Terraform Documentation](https://www.terraform.io/docs)
- Original spec: `SPEC/lark_github_integration.xml`

## 🤝 Contributing

1. Test workflows in a feature branch
2. Update documentation for any changes
3. Ensure all secrets are documented
4. Add appropriate error handling
5. Include Lark notifications for failures

## 📝 License

Part of the Netra AI Optimization Platform.