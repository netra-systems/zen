# Staging Environment Optimization Guide

## Problem
The staging GitHub Action was hanging for 5+ hours due to:
1. **Cloud SQL Instance Creation**: 10-15 minutes per PR
2. **SSL Certificate Provisioning**: DNS propagation delays
3. **Global Load Balancer**: Slow global resource provisioning
4. **State Lock Issues**: Stale locks from failed runs
5. **Docker Build Hangs**: pip install without timeouts

## Solution Overview

### 1. Shared Infrastructure Approach
Instead of creating new infrastructure for each PR, use a shared base:

```bash
# One-time setup of shared resources
cd terraform/staging/shared-infrastructure
terraform apply

# Per-PR: Only create database & deploy services (2-3 min vs 15-20 min)
cd terraform/staging
terraform apply  # Uses main-optimized.tf
```

### 2. Key Optimizations

#### Database Strategy
- **Before**: Create new Cloud SQL instance per PR (10-15 min)
- **After**: Create database in shared instance (10-30 sec)

```hcl
# Fast: Just create a database
resource "google_sql_database" "pr" {
  name     = "netra_pr_${var.pr_number}"
  instance = local.shared_sql_instance  # Pre-existing
}
```

#### SSL Certificate
- **Before**: Managed certificate with DNS validation per PR
- **After**: Wildcard certificate `*.staging.domain.com` (instant)

#### Load Balancer
- **Before**: Global load balancer with global forwarding rules
- **After**: Regional Cloud Run with direct URLs or regional LB

#### Redis Strategy
- **Before**: Create Redis instance per PR
- **After**: Use database selection (0-15) in shared instance

```python
# Use PR number to select Redis DB
redis_db = pr_number % 16
redis_url = f"redis://host:port/{redis_db}"
```

### 3. Workflow Concurrency Control

**NEW**: Automatic cancellation of superseded runs:
- When a new commit is pushed, in-progress workflows for the same PR are cancelled
- Only the latest commit's workflow runs to completion
- Destroy operations use separate concurrency group (never cancelled)

```yaml
concurrency:
  group: staging-pr-${{ github.event.pull_request.number }}
  cancel-in-progress: true
```

### 4. Parallel Build Optimization

Backend and frontend containers now build in parallel:
- Separate GitHub Actions jobs run simultaneously
- 5-10 minutes saved per deployment
- Independent failure detection

### 5. Timeout Configuration

All steps now have explicit timeouts:

| Step | Timeout | Previous |
|------|---------|----------|
| Job Level | 30-45 min | 6 hours (GitHub default) |
| Docker Build | 10 min | Unlimited |
| Terraform Apply | 20 min | Unlimited |
| Database Migration | 5 min | Unlimited |
| Health Checks | 10 min | Unlimited |

### 6. State Lock Recovery

Automatically detect and clear stale locks:

```bash
# Check lock age and remove if > 30 minutes old
if [ $LOCK_AGE_MINUTES -gt 30 ]; then
  gsutil rm "$LOCK_FILE"
fi

# Use lock timeout on all Terraform commands
terraform init -lock-timeout=120s
terraform apply -lock-timeout=120s
```

## Implementation Steps

### Step 1: Deploy Shared Infrastructure
```bash
# Run once to set up shared resources
gcloud auth login
cd terraform/staging/shared-infrastructure
terraform init
terraform apply
```

### Step 2: Update GitHub Workflow
Use the optimized `staging-environment.yml` with:
- Timeouts on all steps
- Docker BuildKit with progress tracking
- State lock recovery
- Health check timeouts

### Step 3: Switch to Optimized Terraform
Replace `main.tf` with `main-optimized.tf` that uses:
- Shared SQL instance (database only)
- Shared Redis with DB selection
- Regional resources
- Direct Cloud Run URLs

## Performance Comparison

| Resource | Old Approach | Optimized | Improvement |
|----------|-------------|-----------|-------------|
| Cloud SQL | 10-15 min | 10-30 sec | 95% faster |
| Redis | 5-10 min | 0 sec (shared) | 100% faster |
| SSL Cert | 5-30 min | 0 sec (wildcard) | 100% faster |
| Load Balancer | 3-5 min | 30 sec (regional) | 85% faster |
| **Total** | **23-60 min** | **2-3 min** | **90% faster** |

## Rollback Plan

If issues occur with the optimized approach:

1. Keep original files as backups:
   - `main.tf.backup`
   - `staging-environment.yml.backup`

2. Revert by switching Terraform files:
   ```bash
   mv main-optimized.tf main-optimized.tf.disabled
   mv main.tf.backup main.tf
   ```

3. The shared infrastructure can coexist with per-PR resources

## Monitoring

Add CloudWatch/Stackdriver alerts for:
- Terraform apply duration > 5 minutes
- Docker build duration > 10 minutes
- State lock age > 30 minutes
- Database connection pool exhaustion

## Cost Savings

- **Shared SQL Instance**: $50/month vs $50/month × N PRs
- **Shared Redis**: $30/month vs $30/month × N PRs
- **Reduced Build Time**: Lower GitHub Actions minutes usage
- **Estimated Savings**: 80-90% reduction in staging costs