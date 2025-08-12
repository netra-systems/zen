# GitHub Staging Workflow Enhancements

## Overview
This document describes the enhancements made to the GitHub staging workflow to improve commit detection and comment updating.

## Key Enhancements

### 1. Commit Detection & Process Termination

#### Enhanced Concurrency Control
- **Location**: Lines 21-23 of enhanced workflow
- **Feature**: Automatically cancels in-progress runs when new commits are pushed (`synchronize` event)
- **Protection**: Cleanup and destroy operations are never cancelled to prevent resource leaks

#### Commit Monitoring Job
- **New Job**: `commit-monitor` (lines 127-187)
- **Function**: Continuously monitors PR for new commits during deployment
- **Behavior**: 
  - Checks every 30 seconds for 5 minutes
  - Detects if PR head SHA changes from initial deployment SHA
  - Updates PR comment when new commit detected
  - Signals other jobs to cancel via output variable

#### Deployment SHA Tracking
- **Environment Variable**: `DEPLOYMENT_SHA` tracks the commit being deployed
- **Usage**: All jobs reference this SHA to ensure consistency
- **Verification**: Each critical job checks for new commits before proceeding

### 2. Comprehensive Comment Updates

#### Initialize Deployment Job
- **Purpose**: Creates initial PR comment with deployment tracking
- **Features**:
  - Generates unique deployment ID for tracking
  - Creates structured comment with progress table
  - Returns comment ID for other jobs to update
  - Includes collapsible sections for details

#### Comment Structure
```markdown
## 🚀 Staging Environment Status
- Status emoji changes based on state (🚀, ✅, ❌, ⏳, 🧹)
- Deployment metadata (ID, SHA, timestamp)
- Current status message

### 📋 Deployment Progress
| Stage | Status | Details | Time |
- Real-time updates for each stage
- Visual status indicators
- Timing information

### 📝 Activity Log
- Timestamped log of all events
- Collapsible for cleaner view
```

#### Update Points
Each major stage updates the comment:

1. **Backend Build** (lines 288-456)
   - Start: Updates status to "🔄 In Progress"
   - Complete: Shows success/failure with image details and duration

2. **Frontend Build** (lines 458-625)
   - Similar pattern to backend build
   - Parallel execution with backend

3. **Deployment** (lines 627-1114)
   - Infrastructure provisioning status
   - Terraform apply progress
   - URLs added when successful

4. **Database Setup** (lines 1116-1262)
   - Migration status updates
   - Seeding progress
   - Error details if failures occur

5. **Testing** (lines 1264-1380)
   - Test execution progress
   - Results summary (passed/failed/skipped)
   - Duration tracking

### 3. Error Handling & Recovery

#### Enhanced Error Reporting
- Each failure updates comment with specific error context
- Suggestions for recovery included where applicable
- Activity log maintains full history

#### State Management
- Comment always shows current state
- Failed stages marked with ❌
- Overall status reflects deployment health

#### Resource Cleanup
- Stale lock detection and removal
- Automatic retry logic with exponential backoff
- Force cleanup for cancelled workflows

### 4. Implementation Details

#### Comment Update Pattern
```javascript
// Standard pattern for all comment updates
const { data: currentComment } = await github.rest.issues.getComment({
  owner: context.repo.owner,
  repo: context.repo.repo,
  comment_id: parseInt(comment_id)
});

// Modify specific parts of comment
let body = currentComment.body;
body = body.replace(/regex_pattern/, 'new_content');

// Update comment
await github.rest.issues.updateComment({
  owner: context.repo.owner,
  repo: context.repo.repo,
  comment_id: parseInt(comment_id),
  body: body
});
```

#### Commit Detection Pattern
```bash
# Check if new commit pushed
CURRENT_SHA=$(gh pr view ${PR_NUMBER} --json headRefOid -q .headRefOid)
if [[ "$CURRENT_SHA" != "$INITIAL_SHA" ]]; then
  echo "New commit detected: ${CURRENT_SHA}"
  # Cancel current deployment
  # Update comment about cancellation
fi
```

## Benefits

1. **Better User Experience**
   - Single comment thread with all updates
   - Visual progress indicators
   - Clear error messages

2. **Resource Efficiency**
   - Automatic cancellation saves compute resources
   - No orphaned deployments from old commits
   - Parallel builds reduce total time

3. **Debugging Support**
   - Complete activity log in comment
   - Timing information for performance analysis
   - Error context for troubleshooting

4. **Reliability**
   - Proper cleanup on cancellation
   - Retry logic for transient failures
   - Lock handling for concurrent operations

## Usage

1. **For Regular PRs**: 
   - Workflow automatically creates and updates comment
   - New commits cancel old deployments and start fresh

2. **For Manual Triggers**:
   - Use workflow_dispatch with PR number
   - Same comment updating behavior

3. **Monitoring**:
   - Watch the PR comment for real-time updates
   - Check activity log for detailed history
   - Review failed stages for specific errors

## Migration from Original Workflow

To use the enhanced workflow:
1. Review and update secrets if needed
2. Update workflow file reference in repository settings
3. Test with a sample PR to verify functionality
4. Monitor first few deployments for any issues

## Future Enhancements

Potential improvements to consider:
- WebSocket-based real-time updates
- Deployment preview screenshots in comments
- Performance metrics and trends
- Cost tracking per deployment
- Integration with external monitoring tools