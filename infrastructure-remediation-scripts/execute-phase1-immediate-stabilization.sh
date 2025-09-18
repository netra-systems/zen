#!/bin/bash
# PHASE 1: IMMEDIATE STABILIZATION
# Issue #1278 Infrastructure Remediation
# Priority: P0 CRITICAL
# Estimated Time: 30 minutes

set -e  # Exit on any error

echo "========================================================================"
echo "ISSUE #1278 - PHASE 1: IMMEDIATE STABILIZATION"
echo "========================================================================"
echo "Priority: P0 CRITICAL"
echo "Objective: Fix dual revision deployment causing HTTP 503 errors"
echo "Business Impact: Restore $500K+ ARR services"
echo "Started: $(date)"
echo "========================================================================"

# Variables
PROJECT="netra-staging"
REGION="us-central1"
SERVICE="netra-backend-staging"
LATEST_REVISION="netra-backend-staging-00750-69k"
OLD_REVISION="netra-backend-staging-00749-6tr"

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS: $1"
    else
        echo "❌ FAILED: $1"
        echo "CRITICAL: Phase 1 failed. See rollback procedures in remediation plan."
        exit 1
    fi
}

# Function to test health endpoint
test_health() {
    echo "Testing health endpoint..."
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.staging.netrasystems.ai/health)
    HEALTH_TIME=$(curl -s -w "%{time_total}" -o /dev/null https://api.staging.netrasystems.ai/health)

    echo "Health endpoint status: $HEALTH_STATUS"
    echo "Health endpoint response time: ${HEALTH_TIME}s"

    if [ "$HEALTH_STATUS" = "200" ]; then
        if (( $(echo "$HEALTH_TIME < 2.0" | bc -l) )); then
            echo "✅ Health check: EXCELLENT (${HEALTH_TIME}s)"
            return 0
        else
            echo "⚠️ Health check: SLOW (${HEALTH_TIME}s)"
            return 1
        fi
    else
        echo "❌ Health check: FAILED ($HEALTH_STATUS)"
        return 1
    fi
}

echo ""
echo "STEP 1: CHECKING CURRENT REVISION STATUS"
echo "----------------------------------------"

# Check current revisions
echo "Listing current revisions..."
gcloud run revisions list \
    --service=$SERVICE \
    --region=$REGION \
    --project=$PROJECT \
    --format="table(metadata.name,status.conditions[0].status,spec.containers[0].image)" \
    || check_success "Failed to list revisions"

echo ""
echo "Checking current traffic allocation..."
gcloud run services describe $SERVICE \
    --region=$REGION \
    --project=$PROJECT \
    --format="value(status.traffic[].revisionName,status.traffic[].percent)" \
    || check_success "Failed to get traffic allocation"

echo ""
echo "STEP 2: ROUTING 100% TRAFFIC TO LATEST REVISION"
echo "------------------------------------------------"

echo "Routing 100% traffic to latest revision: $LATEST_REVISION"
gcloud run services update-traffic $SERVICE \
    --to-revisions=$LATEST_REVISION=100 \
    --region=$REGION \
    --project=$PROJECT
check_success "Route traffic to latest revision"

echo ""
echo "Waiting 30 seconds for traffic routing to stabilize..."
sleep 30

echo ""
echo "STEP 3: TESTING SERVICE AFTER TRAFFIC ROUTING"
echo "----------------------------------------------"

# Test health endpoint multiple times
echo "Running health check tests (5 attempts)..."
PASS_COUNT=0
for i in {1..5}; do
    echo "Health check attempt $i/5:"
    if test_health; then
        ((PASS_COUNT++))
    fi
    echo ""
    sleep 5
done

echo "Health check results: $PASS_COUNT/5 successful"

if [ $PASS_COUNT -ge 3 ]; then
    echo "✅ Service appears stable after traffic routing"
    PROCEED_WITH_DELETION=true
else
    echo "⚠️ Service still unstable. Consider investigating before deleting old revision."
    echo "You can still proceed with deletion, but monitor closely."
    read -p "Proceed with old revision deletion? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        PROCEED_WITH_DELETION=true
    else
        PROCEED_WITH_DELETION=false
    fi
fi

if [ "$PROCEED_WITH_DELETION" = true ]; then
    echo ""
    echo "STEP 4: DELETING OLD REVISION"
    echo "------------------------------"

    echo "Deleting old revision: $OLD_REVISION"
    gcloud run revisions delete $OLD_REVISION \
        --region=$REGION \
        --project=$PROJECT \
        --quiet
    check_success "Delete old revision"

    echo ""
    echo "Waiting 15 seconds for resource cleanup..."
    sleep 15
else
    echo ""
    echo "STEP 4: SKIPPED - OLD REVISION DELETION"
    echo "----------------------------------------"
    echo "⚠️ Old revision deletion skipped by user"
    echo "RECOMMENDATION: Monitor service and delete old revision once stable"
    echo "Command: gcloud run revisions delete $OLD_REVISION --region=$REGION --project=$PROJECT --quiet"
fi

echo ""
echo "STEP 5: FINAL VALIDATION"
echo "------------------------"

echo "Final revision check..."
gcloud run revisions list \
    --service=$SERVICE \
    --region=$REGION \
    --project=$PROJECT \
    --filter="status.conditions.type=Active" \
    --format="table(metadata.name,status.conditions[0].status,metadata.creationTimestamp)"

echo ""
echo "Final traffic allocation check..."
gcloud run services describe $SERVICE \
    --region=$REGION \
    --project=$PROJECT \
    --format="table(status.traffic[].revisionName,status.traffic[].percent)"

echo ""
echo "Final health check validation..."
if test_health; then
    echo "✅ Final health check: PASSED"
    PHASE1_SUCCESS=true
else
    echo "❌ Final health check: FAILED"
    PHASE1_SUCCESS=false
fi

echo ""
echo "========================================================================"
echo "PHASE 1 COMPLETION SUMMARY"
echo "========================================================================"
echo "Completed: $(date)"

if [ "$PHASE1_SUCCESS" = true ]; then
    echo "STATUS: ✅ SUCCESS"
    echo ""
    echo "ACHIEVEMENTS:"
    echo "- ✅ Resolved dual revision deployment state"
    echo "- ✅ Eliminated revision-based resource contention"
    echo "- ✅ Health endpoint responding successfully"
    echo "- ✅ Service stabilized for Phase 2"
    echo ""
    echo "NEXT STEPS:"
    echo "1. Execute Phase 2: Infrastructure Validation"
    echo "   Command: ./execute-phase2-infrastructure-validation.sh"
    echo "2. Monitor service for next 15 minutes"
    echo "3. Check GCP logs for reduction in 503 errors"
    echo ""
    echo "EXPECTED IMPACT:"
    echo "- HTTP 503 errors should be significantly reduced"
    echo "- WebSocket connections should improve"
    echo "- Service response times should normalize"
else
    echo "STATUS: ❌ PARTIAL SUCCESS WITH ISSUES"
    echo ""
    echo "ACHIEVED:"
    echo "- ✅ Traffic routing updated"
    if [ "$PROCEED_WITH_DELETION" = true ]; then
        echo "- ✅ Old revision deleted"
    else
        echo "- ⚠️ Old revision deletion skipped"
    fi
    echo ""
    echo "REMAINING ISSUES:"
    echo "- ❌ Health endpoint still failing or slow"
    echo "- ⚠️ May indicate deeper infrastructure problems"
    echo ""
    echo "NEXT STEPS:"
    echo "1. Check Phase 1 rollback procedures if service is worse"
    echo "2. Proceed to Phase 2 for VPC/database investigation"
    echo "3. Monitor logs for underlying issues"
    echo ""
    echo "ROLLBACK COMMAND (if needed):"
    echo "gcloud run services update-traffic $SERVICE --to-revisions=$OLD_REVISION=100 --region=$REGION --project=$PROJECT"
fi

echo ""
echo "========================================================================"
echo "MONITORING COMMANDS FOR NEXT 15 MINUTES:"
echo "========================================================================"
echo ""
echo "1. Check HTTP 503 errors:"
echo 'gcloud logging read "resource.type=\"cloud_run_revision\" AND httpRequest.status=503 AND timestamp>=\"'$(date -u -d '1 minute ago' '+%Y-%m-%dT%H:%M:%SZ')'\"" --project='$PROJECT' --limit=10'
echo ""
echo "2. Monitor health endpoint:"
echo "watch -n 10 'curl -s -w \"Status: %{http_code}, Time: %{time_total}s\\n\" https://api.staging.netrasystems.ai/health -o /dev/null'"
echo ""
echo "3. Check service logs:"
echo 'gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"'$SERVICE'\" AND severity>=WARNING" --project='$PROJECT' --limit=20'

echo ""
echo "Phase 1 script completed."
echo "========================================================================"