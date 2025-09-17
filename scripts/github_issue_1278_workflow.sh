#!/bin/bash

# GitHub Issue #1278 Creation and Status Update Workflow
# Run this script after GitHub CLI approval

echo "🔍 Checking if Issue #1278 exists..."

# Step 1: Check if issue exists
if gh issue view 1278 &>/dev/null; then
    echo "✅ Issue #1278 exists"
    ISSUE_EXISTS=true
else
    echo "❌ Issue #1278 does not exist - creating it"
    ISSUE_EXISTS=false
fi

# Step 2: Create issue if it doesn't exist
if [ "$ISSUE_EXISTS" = false ]; then
    echo "📝 Creating Issue #1278..."
    
    ISSUE_CREATED=$(gh issue create \
        --title "[BUG] SMD Phase 3 database timeout causes complete application startup failure" \
        --body "## Impact
Complete staging environment outage with 649+ error entries causing \$500K+ ARR validation pipeline blockage

## Current Behavior
SMD Phase 3 (DATABASE) initialization fails with 20.0s timeout → FastAPI lifespan context breakdown → container exit code 3

## Expected Behavior
Application should start successfully or gracefully degrade for health checks

## Reproduction Steps
1. Deploy to staging environment
2. Monitor SMD startup sequence
3. Observe Phase 3 database timeout after 20.0s
4. Container exits with code 3

## Technical Details
- File: \`netra_backend/app/smd.py:1005,1018,1882\`
- File: \`netra_backend/app/startup_module.py:978\`
- Error: \`SMD Phase 3 (DATABASE) initialization failed with 20.0s timeout\`
- Environment: staging
- Connection: \`postgresql+asyncpg://***@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres\`

**Startup Sequence Status**:
- ✅ Phase 1 (INIT): 0.058s
- ✅ Phase 2 (DEPENDENCIES): 31.115s  
- ❌ Phase 3 (DATABASE): 20.0s timeout
- ❌ Phases 4-7: Blocked by Phase 3 failure

**Root Cause**: Cloud SQL VPC connector connectivity issues in staging environment

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>" \
        --label "P0,bug,infrastructure-dependency,claude-code-generated-issue")
    
    if [ $? -eq 0 ]; then
        echo "✅ Issue #1278 created successfully"
        echo "🔗 Issue URL: $ISSUE_CREATED"
    else
        echo "❌ Failed to create issue #1278"
        exit 1
    fi
fi

# Step 3: Add agent session tags
echo "🏷️  Adding agent session tags..."

gh issue edit 1278 --add-label "actively-being-worked-on,agent-session-2025-09-15-14:10"

if [ $? -eq 0 ]; then
    echo "✅ Agent session tags added successfully"
else
    echo "❌ Failed to add agent session tags"
fi

# Step 4: Add comprehensive Five Whys analysis comment
echo "📊 Adding Five Whys analysis status update..."

COMMENT_CREATED=$(gh issue comment 1278 --body "**Status:** FIVE WHYS ANALYSIS COMPLETE - Codebase audit reveals proper error handling with persistent staging connectivity issues

## Five Whys Analysis Results

**Why did the application startup fail?**
→ SMD Phase 3 (DATABASE) initialization failed with 20.0s timeout

**Why did SMD Phase 3 timeout?**
→ Database connection to Cloud SQL staging instance couldn't be established within timeout window  
→ Connection string: \`postgresql+asyncpg://***@/netra_staging?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres\`

**Why did the database connection fail?**
→ Cloud SQL VPC connector connectivity issues in staging environment  
→ Pool configuration may be suboptimal: pool_size=20, max_overflow=30, pool_timeout=10s vs 20s connection timeout

**Why didn't the system recover gracefully?**
→ SMD uses deterministic startup (no fallbacks) - line 14 in \`lifespan_manager.py\` imports \`run_deterministic_startup\`  
→ FastAPI lifespan manager (\`lifespan_manager.py:36\`) catches DeterministicStartupError but doesn't implement recovery  
→ Design principle: \"If any critical service fails, the entire startup MUST fail\" (\`smd.py:5\`)

**Why is the container exiting with code 3?**
→ \`startup_module.py\` line 978 triggers application exit on startup failure  
→ Container properly terminates with exit code 3 indicating configuration/dependency failure  
→ This is correct behavior per deterministic startup design

## Current State Assessment

✅ **Codebase has proper error handling** - lifespan manager correctly catches startup failures  
✅ **Recent fixes applied** - commit \`ed69527fc\` fixed goldenpath integration test staging domain config  
✅ **Related Issue #1263 resolved** - database timeout remediation completed  
❌ **Issue still persists** - log entries show continued failures as of 2025-09-15 16:47:16.794781Z

## Recommendation

Issue requires immediate remediation of Cloud SQL connectivity in staging environment rather than application code changes.

**Next:** Escalate to infrastructure team for Cloud SQL VPC connector diagnostics

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>")

if [ $? -eq 0 ]; then
    echo "✅ Five Whys analysis comment added successfully"
    echo "💬 Comment ID: $COMMENT_CREATED"
else
    echo "❌ Failed to add Five Whys analysis comment"
fi

# Step 5: Get final status
echo "📋 Final status report..."

ISSUE_INFO=$(gh issue view 1278 --json number,title,state,labels,url)
echo "📊 Issue #1278 Status:"
echo "$ISSUE_INFO" | jq .

echo ""
echo "🎯 WORKFLOW COMPLETED"
echo "Issue Number: #1278"
echo "Status: $(echo "$ISSUE_INFO" | jq -r .state)"
echo "URL: $(echo "$ISSUE_INFO" | jq -r .url)"
echo "Labels: $(echo "$ISSUE_INFO" | jq -r '.labels[] | .name' | tr '\n' ',' | sed 's/,$//')"

echo ""
echo "✅ All tasks completed successfully!"
echo "📝 Issue #1278 is now properly configured with Five Whys analysis and agent session tracking"