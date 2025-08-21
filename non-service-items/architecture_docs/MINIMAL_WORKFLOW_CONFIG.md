# Minimal Workflow Configuration

## Current Setup: Only Staging and Smoke Tests

### What's Enabled

#### 1. **Smoke Tests** 
- Quick validation tests (<30 seconds)
- Run on every push and PR
- Basic health checks only
- 5-minute timeout
- No retries to save resources

#### 2. **Staging Deployments**
- Auto-deploy PRs to staging environments
- Maximum 3 concurrent environments (reduced from 5)
- 20-minute deployment timeout
- More aggressive cleanup:
  - Clean up after 3 days (vs 7 days)
  - Clean up after 12 hours of inactivity (vs 24 hours)
  - Force cleanup when PR closes

#### 3. **Staging Cleanup**
- Runs every 6 hours
- Terraform lock cleanup every hour
- Automatic removal of stale environments

### What's Disabled

❌ **All Testing Except Smoke:**
- Unit tests - DISABLED
- Integration tests - DISABLED  
- Comprehensive tests - DISABLED
- On-demand tests - DISABLED

❌ **AI Features:**
- AI Auto-fix - DISABLED
- AI PR Review - DISABLED
- Issue triage - DISABLED

❌ **Monitoring:**
- Architecture health checks - DISABLED
- Workflow health monitoring - DISABLED

❌ **Advanced Features:**
- Hierarchical test execution - DISABLED
- Smart retry logic - DISABLED
- Parallel execution - DISABLED

### Cost Controls

**Conservative Budget Limits:**
- Daily limit: $10
- Monthly budget: $200
- Per PR limit: $20

**Resource Limits:**
- Max staging environments: 3
- Max parallel jobs: 2

**Alert Thresholds:**
- 80% of budget → Notification
- 100% of budget → Halt all non-critical workflows

### Configuration File

The configuration is stored in `.github/workflow-config.yml` and can be modified using:

```bash
# View current configuration
python scripts/manage_workflows.py show

# Enable a specific workflow if needed
python scripts/manage_workflows.py enable <workflow-name>

# Disable a workflow
python scripts/manage_workflows.py disable <workflow-name>

# Adjust budget if needed
python scripts/manage_workflows.py budget --daily 15 --monthly 300
```

### Workflow Behavior

With this minimal configuration:

1. **On PR Creation:**
   - Smoke tests run (5 minutes max)
   - If smoke passes → Staging deployment (20 minutes max)
   - Total time: ~25 minutes maximum

2. **On PR Close:**
   - Staging environment immediately destroyed
   - Resources freed up

3. **Cost Savings:**
   - ~80% reduction in test execution costs
   - ~60% reduction in staging costs (aggressive cleanup)
   - Estimated monthly cost: $50-100 (vs $300-500 full setup)

### When to Use This Configuration

This minimal setup is ideal for:
- Development phases with limited budget
- Small teams not needing extensive testing
- Projects in maintenance mode
- Cost optimization periods

### How to Restore Full Testing

To re-enable more comprehensive testing:

```bash
# Standard configuration (smoke + unit + integration)
python scripts/manage_workflows.py preset standard

# Full configuration (all tests + AI features)
python scripts/manage_workflows.py preset full

# Or enable specific tests
python scripts/manage_workflows.py enable unit
python scripts/manage_workflows.py enable integration
```

### Monitoring Your Costs

Even with minimal configuration, cost monitoring remains active:

```bash
# Check current month's usage (if workflow health monitor is enabled)
python scripts/manage_workflows.py enable workflow-health-monitor

# View cost alerts in GitHub Issues (automatically created at 80% budget)
```

### Important Notes

1. **Smoke tests are your only safety net** - Make sure they cover critical functionality
2. **Staging environments will be aggressively cleaned** - Don't store important data there
3. **No automatic fixes** - You'll need to manually fix any test failures
4. **Limited parallelization** - Builds may be slower but cheaper

This configuration prioritizes **cost savings** over **comprehensive testing**. It's suitable for situations where budget is the primary concern and you can accept the trade-off of reduced test coverage.