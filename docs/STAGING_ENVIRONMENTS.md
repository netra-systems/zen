# Staging Environments

Automatic staging environments for every pull request, providing isolated testing environments with production-like infrastructure.

## Overview

Every pull request automatically gets a dedicated staging environment deployed to Google Cloud Platform. These environments are:

- **Isolated**: Each PR gets its own infrastructure
- **Production-like**: Uses the same tech stack as production
- **Ephemeral**: Automatically destroyed when PR is closed
- **Cost-optimized**: Resources scale to zero when idle

## Quick Links

- **Spec**: [SPEC/staging_environment.xml](../SPEC/staging_environment.xml)
- **Configuration**: [.github/staging.yml](../.github/staging.yml)
- **Workflow**: [.github/workflows/staging-environment.yml](../.github/workflows/staging-environment.yml)

## How It Works

### 1. PR Created/Updated
When you create or update a PR, the staging workflow automatically:
1. **Cancels any in-progress deployments** for the same PR (only latest commit runs)
2. Builds Docker containers for backend and frontend **in parallel**
3. Deploys infrastructure using Terraform
4. Seeds test data
5. Runs integration tests
6. Posts the staging URL as a PR comment

**Note**: If you push multiple commits in quick succession (within ~3 minutes), only the latest commit's workflow will complete. Previous runs are automatically cancelled to save resources and provide faster feedback.

### 2. Access Your Staging Environment
Each staging environment gets unique URLs:
- Frontend: `https://pr-{number}.staging.netra-ai.dev`
- API: `https://pr-{number}-api.staging.netra-ai.dev`

### 3. Automatic Cleanup
Environments are automatically destroyed when:
- PR is closed or merged
- Environment exceeds 7 days age
- No activity for 24 hours
- Monthly cost limit exceeded

## Configuration

### Disable Staging for a PR
Add one of these labels to skip staging deployment:
- `no-staging`
- `WIP`
- `draft`

### Resource Limits
Default limits per staging environment:
- **CPU**: 2 cores
- **Memory**: 4GB
- **Instances**: 0-3 (auto-scaling)
- **Database**: 10GB storage
- **Cost**: $50/month max

Configure in [.github/staging.yml](../.github/staging.yml)

### Test Levels
The system automatically selects test level based on PR size:
- **Small changes** (< 3 files): Smoke tests
- **Normal changes**: Integration tests  
- **Critical changes** (labeled): Comprehensive tests

## Testing Against Staging

### Manual Testing
Simply visit the staging URLs posted in the PR comment.

### Automated Testing
Run tests against staging:
```bash
python test_runner.py --level integration --staging
```

With specific URLs:
```bash
python test_runner.py --staging-url https://pr-123.staging.netra-ai.dev --staging-api-url https://pr-123-api.staging.netra-ai.dev
```

### E2E Testing
Cypress tests automatically run against staging:
```bash
CYPRESS_BASE_URL=https://pr-123.staging.netra-ai.dev npm run cypress:run
```

## Performance Optimizations

### Workflow Concurrency
- **Automatic Cancellation**: When you push a new commit, any in-progress workflow for the same PR is cancelled
- **Benefits**: Faster feedback, reduced resource usage, cleaner workflow history
- **Exception**: Destroy operations are never cancelled to ensure proper cleanup

### Parallel Builds
- Backend and frontend containers build simultaneously
- Saves 5-10 minutes per deployment
- Independent failure detection

### Build Caching
- Successful builds are cached in Google Cloud Storage
- If no code changes detected, cached images are reused
- Saves 10-15 minutes on unchanged components

## Cost Management

### Automatic Cost Controls
- Environments scale to zero after 15 minutes idle
- Automatic cleanup after 7 days
- Per-PR budget limit of $50/month
- Daily cleanup job removes stale environments
- **Workflow cancellation** prevents redundant builds

### Monitor Costs
View staging costs in:
- GitHub Actions summary (daily)
- GCP Console billing dashboard
- Monthly cost reports (if configured)

## Troubleshooting

### Deployment Failed
Check the GitHub Actions logs:
1. Go to Actions tab
2. Find "Staging Environment Management" workflow
3. Check logs for your PR number

Common issues:
- **Resource quota exceeded**: Too many staging environments active
- **Build failed**: Check Dockerfile and dependencies
- **Terraform error**: Check infrastructure configuration

### Can't Access Staging URL
1. Check if deployment completed (see PR comment)
2. Verify you're authorized (GitHub account linked)
3. Check health endpoint: `https://pr-{number}-api.staging.netra-ai.dev/health`

### Tests Failing in Staging
1. Check if services are healthy
2. Verify test data was seeded
3. Check for environment-specific issues (URLs, credentials)

### Environment Not Cleaning Up
Manual cleanup:
```bash
# Trigger cleanup workflow
gh workflow run staging-cleanup.yml

# Or run cleanup script directly
python scripts/cleanup_staging_environments.py --pr-number 123
```

## Manual Deployment

### Deploy Specific PR
```bash
gh workflow run staging-environment.yml -f action=deploy -f pr_number=123
```

### Destroy Specific PR
```bash
gh workflow run staging-environment.yml -f action=destroy -f pr_number=123
```

### Redeploy
```bash
gh workflow run staging-environment.yml -f action=redeploy -f pr_number=123
```

## Security

### Access Control
- Protected by GitHub OAuth
- Only PR author, reviewers, and maintainers have access
- Optional IP whitelisting available

### Secrets Management
- Secrets isolated per PR
- Automatic rotation
- Never exposed in logs or UI

### Data Protection
- Test data only (no production data)
- Encrypted at rest and in transit
- Automatic cleanup on environment destroy

## Advanced Configuration

### Custom Resource Limits
Edit `.github/staging.yml`:
```yaml
resource_limits:
  compute:
    cpu_limit: "4"        # Increase CPU
    memory_limit: "8Gi"   # Increase memory
    max_instances: 5      # More instances
```

### Custom Test Data
Edit seeding configuration:
```yaml
data_seeding:
  test_data:
    users:
      count: 50           # More test users
    optimization_requests:
      count: 100          # More test requests
```

### Enable Slack Notifications
```yaml
notifications:
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/..."
```

## Infrastructure Details

### Technology Stack
- **Compute**: Google Cloud Run (serverless containers)
- **Database**: Cloud SQL (PostgreSQL)
- **Cache**: Memorystore (Redis)
- **Files**: Cloud Storage
- **CDN**: Cloud CDN
- **DNS**: Cloud DNS
- **SSL**: Let's Encrypt

### Terraform Modules
- `terraform/staging/main.tf`: Main configuration
- `terraform/staging/modules/compute`: Cloud Run services
- `terraform/staging/modules/database`: Cloud SQL and Redis
- `terraform/staging/modules/networking`: VPC and load balancers
- `terraform/staging/modules/security`: IAM and certificates

### GitHub Actions Workflows
- `.github/workflows/staging-environment.yml`: Main deployment workflow
- `.github/workflows/staging-cleanup.yml`: Daily cleanup job

## Best Practices

### For Developers
1. **Keep PRs focused**: Smaller PRs deploy faster
2. **Use appropriate labels**: Mark WIP to skip staging
3. **Clean up manually**: If keeping PR open long-term
4. **Monitor costs**: Check staging costs in PR comments

### For Reviewers
1. **Test in staging**: Always test features in staging before approving
2. **Check test results**: Review automated test results in PR
3. **Verify cleanup**: Ensure environments are cleaned up after merge

### For Maintainers
1. **Monitor total costs**: Check daily/weekly cost reports
2. **Adjust limits**: Update resource limits based on usage
3. **Clean up orphans**: Run manual cleanup for stuck environments
4. **Update test data**: Keep test data realistic and current

## FAQ

**Q: How much does a staging environment cost?**
A: Typically $1-5 per day when active, $0 when idle (scaled to zero).

**Q: Can I keep a staging environment longer than 7 days?**
A: Add the `keep-staging` label to prevent automatic cleanup.

**Q: How do I debug a failing deployment?**
A: Check GitHub Actions logs, then Cloud Console logs for detailed errors.

**Q: Can I share my staging environment?**
A: Yes, anyone with the URL and GitHub access can view it.

**Q: What happens to data in staging?**
A: All data is destroyed when the environment is cleaned up.

**Q: Can I run load tests against staging?**
A: Yes, but be mindful of costs and resource limits.

## Support

For issues or questions:
1. Check this documentation
2. Review the [spec file](../SPEC/staging_environment.xml)
3. Check GitHub Actions logs
4. Contact the platform team

## Future Enhancements

Planned improvements:
- [ ] Blue-green deployments for staging
- [ ] Persistent test data snapshots
- [ ] Performance testing automation
- [ ] Cost prediction before deployment
- [ ] Multi-region staging support
- [ ] Staging environment templates
- [ ] A/B testing support