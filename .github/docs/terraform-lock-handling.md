# Terraform State Lock Handling

## Overview

This document describes the comprehensive Terraform state lock handling implemented in the Netra staging environment workflows to prevent and automatically recover from lock-related failures.

## Problem Statement

Terraform uses state locking to prevent concurrent modifications to infrastructure. When GitHub Actions workflows are cancelled, fail unexpectedly, or experience network issues, they may leave stale lock files in Google Cloud Storage, causing subsequent deployments to fail with errors like:

```
Error acquiring the state lock
Lock Info:
  ID:        1755026831235618
  Path:      gs://netra-staging-terraform-state/staging/pr-4/default.tflock
  Operation: OperationTypeApply
  Who:       runner@pkrvmsl9tci6h6u
  Version:   1.5.0
  Created:   2025-08-12 19:27:11.235618 +0000 UTC
```

## Solution Architecture

### 1. Preventive Measures

#### Intelligent Concurrency Control
```yaml
concurrency:
  group: staging-pr-${{ github.event.pull_request.number }}
  cancel-in-progress: ${{ !contains(github.job, 'destroy') && !contains(github.job, 'cleanup') }}
```
- Prevents concurrent Terraform runs for the same PR
- Never cancels destroy or cleanup operations (they must complete)

#### Lock Timeouts
All Terraform commands use appropriate lock timeouts:
- `terraform init`: 120 seconds
- `terraform plan`: 180 seconds  
- `terraform apply`: 180 seconds
- `terraform destroy`: 180 seconds

### 2. Automatic Lock Detection and Removal

#### Pre-Operation Lock Check
Before any Terraform operation, the workflow:
1. Checks if a lock file exists
2. Retrieves lock metadata (ID, holder, creation time)
3. Calculates lock age
4. Applies intelligent removal logic:
   - GitHub Actions runner locks: Remove if >15 minutes old
   - Other locks: Remove if >30 minutes old
   - Respects active locks from legitimate operations

#### Lock Detection Logic
```bash
# Get lock metadata
LOCK_INFO=$(gsutil cat "$LOCK_FILE" 2>/dev/null || echo "{}")
LOCK_CREATED=$(echo "$LOCK_INFO" | jq -r '.Created // ""')
LOCK_HOLDER=$(echo "$LOCK_INFO" | jq -r '.Who // "unknown"')

# Calculate age
LOCK_TIMESTAMP=$(date -d "${LOCK_CREATED}" +%s)
CURRENT_TIME=$(date +%s)
AGE_MINUTES=$(( (CURRENT_TIME - LOCK_TIMESTAMP) / 60 ))

# Remove if stale
if echo "$LOCK_HOLDER" | grep -q "runner@" && [ $AGE_MINUTES -gt 15 ]; then
  gsutil rm "$LOCK_FILE"
fi
```

### 3. Retry Logic with Exponential Backoff

All Terraform operations implement retry logic:

#### Terraform Init (3 attempts)
- Attempt 1: Standard init with 120s lock timeout
- Attempt 2: After 5s wait, force unlock if needed
- Attempt 3: After 10s wait, final attempt

#### Terraform Plan (3 attempts)
- Attempt 1: Standard plan with 180s lock timeout
- Attempt 2: After 10s wait, check and remove lock
- Attempt 3: After 20s wait, final attempt

#### Terraform Apply (2 attempts)
- Attempt 1: Standard apply with 180s lock timeout
- Attempt 2: After 15s wait, force unlock and retry
- Includes state refresh as fallback

#### Terraform Destroy (2 attempts)
- Always force removes locks before destroy
- Continues with cleanup even if destroy fails
- Removes state files as final cleanup

### 4. Cleanup on Cancellation

#### Automatic Cleanup Job
```yaml
cleanup-on-cancel:
  if: always() && (cancelled() || failure())
```
- Runs when workflow is cancelled or fails
- Removes locks only from GitHub Actions runners
- Preserves legitimate locks from other sources
- Cleans up orphaned plan files

### 5. Scheduled Lock Maintenance

#### Hourly Lock Cleanup (`terraform-lock-cleanup.yml`)
- Runs every hour via cron schedule
- Scans all PR environments for stale locks
- Removes locks based on age thresholds
- Provides detailed reporting

#### Manual Lock Cleanup
```bash
# Clean specific PR
gh workflow run terraform-lock-cleanup.yml -f pr_number=123

# Clean all stale locks
gh workflow run terraform-lock-cleanup.yml

# Force remove all locks (emergency)
gh workflow run terraform-lock-cleanup.yml -f force=true
```

### 6. Lock Monitoring

The scheduled cleanup workflow also:
- Monitors for long-running locks (>45 min warning, >90 min critical)
- Reports to Slack if configured
- Creates GitHub issues for critical locks
- Provides lock statistics and trends

## Lock File Structure

Terraform lock files in GCS contain JSON metadata:
```json
{
  "ID": "1755026831235618",
  "Operation": "OperationTypeApply",
  "Info": "",
  "Who": "runner@pkrvmsl9tci6h6u",
  "Version": "1.5.0",
  "Created": "2025-08-12T19:27:11.235618Z",
  "Path": "gs://netra-staging-terraform-state/staging/pr-4/default.tflock"
}
```

## Best Practices

### For Developers
1. **Don't manually remove locks** unless you're certain no operation is running
2. **Use the cleanup workflow** for manual lock removal
3. **Check workflow logs** before assuming a lock is stale
4. **Report persistent lock issues** to the platform team

### For Workflow Authors
1. **Always use lock timeouts** in Terraform commands
2. **Implement retry logic** for transient failures
3. **Include cleanup steps** in workflows that may fail
4. **Never cancel destroy operations** - let them complete

### Emergency Procedures

#### If automated cleanup fails:
1. Check if Terraform operation is actually running:
   ```bash
   gcloud run services list --filter="name:pr-NUMBER"
   ```

2. Manually check lock age:
   ```bash
   gsutil cat gs://netra-staging-terraform-state/staging/pr-NUMBER/default.tflock
   ```

3. Force remove if confirmed stale:
   ```bash
   gsutil rm gs://netra-staging-terraform-state/staging/pr-NUMBER/default.tflock
   ```

4. Trigger workflow retry:
   ```bash
   gh workflow run staging-environment.yml -f pr_number=NUMBER -f action=deploy
   ```

## Configuration

### Environment Variables
- `STALE_LOCK_MINUTES`: Threshold for GitHub Actions locks (default: 15)
- `GCP_PROJECT_ID`: GCP project for state storage
- `TERRAFORM_VERSION`: Terraform version to use

### Tuning Parameters
- Lock timeout durations can be adjusted per operation
- Retry attempts and wait times are configurable
- Stale thresholds can be modified based on typical operation times

## Monitoring and Alerts

### Metrics Tracked
- Number of stale locks removed per day
- Average lock age when removed
- Failed deployment rate due to locks
- Recovery success rate after lock removal

### Alert Conditions
- Lock exists for >90 minutes
- Multiple lock removal failures
- Repeated lock conflicts for same PR
- State corruption detected

## Testing

### Test Scenarios
1. **Normal operation**: Deploy completes successfully
2. **Workflow cancellation**: Lock is cleaned up automatically
3. **Network timeout**: Retry succeeds after lock removal
4. **Concurrent runs**: Second run waits or removes stale lock
5. **Manual intervention**: Force unlock works correctly

### Validation Steps
```bash
# Simulate stale lock
echo '{"ID":"test","Who":"runner@test","Created":"2020-01-01T00:00:00Z"}' | \
  gsutil cp - gs://bucket/test.tflock

# Run cleanup
gh workflow run terraform-lock-cleanup.yml

# Verify removal
gsutil stat gs://bucket/test.tflock  # Should fail
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Lock persists after cleanup | Lock held by non-runner process | Check for manual Terraform operations |
| Cleanup job fails | Insufficient permissions | Verify service account has storage.objects.delete |
| Retry exhausted | Persistent infrastructure issue | Check GCP service health, quotas |
| State corruption | Interrupted apply operation | Restore from backup, use `terraform refresh` |
| Lock age calculation fails | Timezone or date parsing issue | Check lock file format, use fallback to file stats |

## Future Improvements

1. **Lock ownership validation**: Verify runner is actually dead before removing lock
2. **Distributed locking**: Implement Redis-based locking for better control
3. **Lock queue management**: Queue operations instead of failing immediately
4. **Automatic state repair**: Detect and fix corrupted state files
5. **Enhanced monitoring**: Integrate with Datadog/Prometheus for metrics

## References

- [Terraform State Locking](https://www.terraform.io/docs/language/state/locking.html)
- [GCS Backend Configuration](https://www.terraform.io/docs/language/settings/backends/gcs.html)
- [GitHub Actions Concurrency](https://docs.github.com/en/actions/using-jobs/using-concurrency)
- [Google Cloud Storage gsutil](https://cloud.google.com/storage/docs/gsutil)