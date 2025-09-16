#!/bin/bash
# PHASE 2: INFRASTRUCTURE VALIDATION
# Issue #1278 Infrastructure Remediation
# Priority: P0 CRITICAL
# Estimated Time: 30 minutes

set -e  # Exit on any error

echo "========================================================================"
echo "ISSUE #1278 - PHASE 2: INFRASTRUCTURE VALIDATION"
echo "========================================================================"
echo "Priority: P0 CRITICAL"
echo "Objective: Validate and fix VPC connector and Cloud SQL issues"
echo "Business Impact: Restore database and Redis connectivity"
echo "Started: $(date)"
echo "========================================================================"

# Variables
PROJECT="netra-staging"
REGION="us-central1"
VPC_CONNECTOR="staging-connector"
DB_INSTANCE="netra-staging-db"
SERVICE="netra-backend-staging"

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo "✅ SUCCESS: $1"
    else
        echo "❌ FAILED: $1"
        echo "CRITICAL: Phase 2 failed. See rollback procedures in remediation plan."
        exit 1
    fi
}

# Function to check VPC connector status
check_vpc_connector() {
    echo "Checking VPC connector status..."
    VPC_STATE=$(gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR \
        --region=$REGION \
        --project=$PROJECT \
        --format="value(state)" 2>/dev/null || echo "ERROR")

    echo "VPC Connector State: $VPC_STATE"

    if [ "$VPC_STATE" = "READY" ]; then
        echo "✅ VPC Connector: READY"
        return 0
    elif [ "$VPC_STATE" = "CREATING" ]; then
        echo "⚠️ VPC Connector: CREATING (wait required)"
        return 1
    elif [ "$VPC_STATE" = "ERROR" ]; then
        echo "❌ VPC Connector: Not found or error"
        return 2
    else
        echo "❌ VPC Connector: $VPC_STATE"
        return 1
    fi
}

# Function to check database connections
check_database() {
    echo "Checking database connection utilization..."

    # Get current connections (approximate via operations)
    DB_STATUS=$(gcloud sql instances describe $DB_INSTANCE \
        --project=$PROJECT \
        --format="value(state)" 2>/dev/null || echo "ERROR")

    echo "Database Instance State: $DB_STATUS"

    if [ "$DB_STATUS" = "RUNNABLE" ]; then
        echo "✅ Database: RUNNABLE"
        return 0
    else
        echo "❌ Database: $DB_STATUS"
        return 1
    fi
}

echo ""
echo "STEP 1: VPC CONNECTOR HEALTH CHECK"
echo "-----------------------------------"

check_vpc_connector
VPC_CHECK_RESULT=$?

if [ $VPC_CHECK_RESULT -eq 0 ]; then
    echo "VPC connector is healthy. Checking utilization..."

    # Check recent VPC connector logs for errors
    echo "Checking VPC connector logs for errors in last 15 minutes..."
    VPC_ERRORS=$(gcloud logging read \
        'resource.type="vpc_access_connector" AND
         resource.labels.connector_name="'$VPC_CONNECTOR'" AND
         severity>=ERROR AND
         timestamp>="'$(date -u -d '15 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')'"' \
        --project=$PROJECT \
        --limit=5 \
        --format="value(timestamp)" | wc -l)

    echo "VPC connector errors in last 15 minutes: $VPC_ERRORS"

    if [ $VPC_ERRORS -gt 0 ]; then
        echo "⚠️ VPC connector has recent errors. Scaling up for safety."
        SCALE_VPC=true
    else
        echo "✅ VPC connector appears healthy."
        SCALE_VPC=false
    fi

elif [ $VPC_CHECK_RESULT -eq 1 ]; then
    echo "⚠️ VPC connector not ready. Will attempt to scale or wait."
    SCALE_VPC=true
else
    echo "❌ VPC connector has serious issues. May need recreation."
    echo "CRITICAL: VPC connector not found or in error state."
    echo "This requires manual intervention or terraform recreation."
    exit 1
fi

echo ""
echo "STEP 2: VPC CONNECTOR SCALING (IF NEEDED)"
echo "-----------------------------------------"

if [ "$SCALE_VPC" = true ]; then
    echo "Scaling VPC connector to handle increased load..."

    # Get current scaling configuration
    echo "Current VPC connector configuration:"
    gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR \
        --region=$REGION \
        --project=$PROJECT \
        --format="table(name,state,minInstances,maxInstances,machineType)"

    echo ""
    echo "Updating VPC connector scaling..."
    gcloud compute networks vpc-access connectors update $VPC_CONNECTOR \
        --region=$REGION \
        --project=$PROJECT \
        --max-instances=20 \
        --min-instances=4
    check_success "Scale VPC connector"

    echo ""
    echo "Waiting 60 seconds for VPC connector scaling to apply..."
    sleep 60

    # Re-check status
    check_vpc_connector
    if [ $? -ne 0 ]; then
        echo "⚠️ VPC connector still not ready after scaling. Continuing with caution."
    fi
else
    echo "VPC connector scaling not needed."
fi

echo ""
echo "STEP 3: CLOUD SQL HEALTH CHECK"
echo "-------------------------------"

check_database
if [ $? -ne 0 ]; then
    echo "❌ Database instance not in runnable state"
    echo "CRITICAL: Database issues require immediate investigation"
    exit 1
fi

# Check database connections and performance
echo ""
echo "Checking database connection settings..."
gcloud sql instances describe $DB_INSTANCE \
    --project=$PROJECT \
    --format="table(name,state,settings.tier,settings.dataDiskSizeGb)" \
    || check_success "Failed to describe database instance"

echo ""
echo "Checking current database flags..."
gcloud sql instances describe $DB_INSTANCE \
    --project=$PROJECT \
    --format="value(settings.databaseFlags[].name,settings.databaseFlags[].value)" \
    || echo "No custom database flags set"

echo ""
echo "STEP 4: DATABASE OPTIMIZATION"
echo "------------------------------"

echo "Current max_connections setting check..."
CURRENT_MAX_CONN=$(gcloud sql instances describe $DB_INSTANCE \
    --project=$PROJECT \
    --format="value(settings.databaseFlags[?(@.name=='max_connections')].value)" \
    2>/dev/null || echo "default")

echo "Current max_connections: $CURRENT_MAX_CONN"

if [ "$CURRENT_MAX_CONN" = "default" ] || [ -z "$CURRENT_MAX_CONN" ]; then
    echo "Database using default max_connections. Updating to 200..."
    gcloud sql instances patch $DB_INSTANCE \
        --project=$PROJECT \
        --database-flags=max_connections=200
    check_success "Update database max_connections"

    echo "Waiting 90 seconds for database configuration to apply..."
    sleep 90

elif [ "$CURRENT_MAX_CONN" -lt 200 ]; then
    echo "Database max_connections ($CURRENT_MAX_CONN) is below recommended. Updating to 200..."
    gcloud sql instances patch $DB_INSTANCE \
        --project=$PROJECT \
        --database-flags=max_connections=200
    check_success "Update database max_connections"

    echo "Waiting 90 seconds for database configuration to apply..."
    sleep 90
else
    echo "✅ Database max_connections ($CURRENT_MAX_CONN) is adequate."
fi

echo ""
echo "STEP 5: NETWORK CONNECTIVITY VALIDATION"
echo "----------------------------------------"

echo "Testing Cloud SQL connectivity from Cloud Run..."

# Test database connectivity via health endpoint
echo "Testing database health endpoint..."
DB_HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.staging.netrasystems.ai/health/db)
DB_HEALTH_TIME=$(curl -s -w "%{time_total}" -o /dev/null https://api.staging.netrasystems.ai/health/db)

echo "Database health endpoint status: $DB_HEALTH_STATUS"
echo "Database health endpoint response time: ${DB_HEALTH_TIME}s"

if [ "$DB_HEALTH_STATUS" = "200" ]; then
    echo "✅ Database connectivity: OK"
    DB_CONNECTIVITY_OK=true
else
    echo "❌ Database connectivity: FAILED ($DB_HEALTH_STATUS)"
    DB_CONNECTIVITY_OK=false
fi

# Test Redis connectivity if available
echo ""
echo "Testing Redis connectivity..."
REDIS_HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.staging.netrasystems.ai/health/redis)
REDIS_HEALTH_TIME=$(curl -s -w "%{time_total}" -o /dev/null https://api.staging.netrasystems.ai/health/redis)

echo "Redis health endpoint status: $REDIS_HEALTH_STATUS"
echo "Redis health endpoint response time: ${REDIS_HEALTH_TIME}s"

if [ "$REDIS_HEALTH_STATUS" = "200" ]; then
    echo "✅ Redis connectivity: OK"
    REDIS_CONNECTIVITY_OK=true
else
    echo "❌ Redis connectivity: FAILED ($REDIS_HEALTH_STATUS)"
    REDIS_CONNECTIVITY_OK=false
fi

echo ""
echo "STEP 6: SERVICE CONFIGURATION VALIDATION"
echo "-----------------------------------------"

echo "Checking Cloud Run service VPC configuration..."
gcloud run services describe $SERVICE \
    --region=$REGION \
    --project=$PROJECT \
    --format="value(spec.template.metadata.annotations)" | grep vpc

echo ""
echo "Verifying service has correct VPC connector annotation..."
VPC_ANNOTATION=$(gcloud run services describe $SERVICE \
    --region=$REGION \
    --project=$PROJECT \
    --format="value(spec.template.metadata.annotations['run.googleapis.com/vpc-access-connector'])")

echo "Current VPC connector annotation: $VPC_ANNOTATION"

if [[ "$VPC_ANNOTATION" == *"$VPC_CONNECTOR"* ]]; then
    echo "✅ Service has correct VPC connector annotation"
else
    echo "⚠️ Service VPC connector annotation may be incorrect"
    echo "Expected to contain: $VPC_CONNECTOR"
    echo "Actual: $VPC_ANNOTATION"
fi

echo ""
echo "STEP 7: INFRASTRUCTURE HEALTH SUMMARY"
echo "--------------------------------------"

echo "Infrastructure component health check:"
echo ""

# VPC Connector Final Check
check_vpc_connector > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ VPC Connector: HEALTHY"
    VPC_FINAL_OK=true
else
    echo "❌ VPC Connector: ISSUES REMAIN"
    VPC_FINAL_OK=false
fi

# Database Final Check
check_database > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database Instance: HEALTHY"
    DB_FINAL_OK=true
else
    echo "❌ Database Instance: ISSUES REMAIN"
    DB_FINAL_OK=false
fi

# Connectivity Summary
if [ "$DB_CONNECTIVITY_OK" = true ]; then
    echo "✅ Database Connectivity: OK"
else
    echo "❌ Database Connectivity: FAILED"
fi

if [ "$REDIS_CONNECTIVITY_OK" = true ]; then
    echo "✅ Redis Connectivity: OK"
else
    echo "❌ Redis Connectivity: FAILED"
fi

echo ""
echo "========================================================================"
echo "PHASE 2 COMPLETION SUMMARY"
echo "========================================================================"
echo "Completed: $(date)"

# Determine overall success
OVERALL_SUCCESS=true
if [ "$VPC_FINAL_OK" = false ] || [ "$DB_FINAL_OK" = false ]; then
    OVERALL_SUCCESS=false
fi

if [ "$DB_CONNECTIVITY_OK" = false ] && [ "$REDIS_CONNECTIVITY_OK" = false ]; then
    OVERALL_SUCCESS=false
fi

if [ "$OVERALL_SUCCESS" = true ]; then
    echo "STATUS: ✅ SUCCESS"
    echo ""
    echo "ACHIEVEMENTS:"
    echo "- ✅ VPC connector validated and optimized"
    echo "- ✅ Database configuration improved"
    echo "- ✅ Network connectivity restored"
    echo "- ✅ Infrastructure ready for Phase 3"
    echo ""
    echo "NEXT STEPS:"
    echo "1. Execute Phase 3: Service Recovery"
    echo "   Command: ./execute-phase3-service-recovery.sh"
    echo "2. Monitor connectivity for 10 minutes"
    echo "3. Check for improved service performance"
else
    echo "STATUS: ⚠️ PARTIAL SUCCESS WITH REMAINING ISSUES"
    echo ""
    echo "ACHIEVED:"
    if [ "$VPC_FINAL_OK" = true ]; then
        echo "- ✅ VPC connector healthy"
    else
        echo "- ❌ VPC connector issues remain"
    fi

    if [ "$DB_FINAL_OK" = true ]; then
        echo "- ✅ Database instance healthy"
    else
        echo "- ❌ Database instance issues remain"
    fi

    echo ""
    echo "REMAINING ISSUES:"
    if [ "$DB_CONNECTIVITY_OK" = false ]; then
        echo "- ❌ Database connectivity failing"
    fi
    if [ "$REDIS_CONNECTIVITY_OK" = false ]; then
        echo "- ❌ Redis connectivity failing"
    fi

    echo ""
    echo "RECOMMENDED ACTIONS:"
    echo "1. Investigate VPC routing if connectivity issues persist"
    echo "2. Check firewall rules for VPC connector"
    echo "3. Verify Cloud SQL private IP configuration"
    echo "4. Consider manual VPC connector recreation if critical"
fi

echo ""
echo "========================================================================"
echo "MONITORING COMMANDS FOR NEXT 10 MINUTES:"
echo "========================================================================"
echo ""
echo "1. Monitor VPC connector health:"
echo "watch -n 30 'gcloud compute networks vpc-access connectors describe $VPC_CONNECTOR --region=$REGION --project=$PROJECT --format=\"value(state)\"'"
echo ""
echo "2. Monitor database connectivity:"
echo "watch -n 30 'curl -s -w \"DB: %{http_code} (%{time_total}s), Redis: \" https://api.staging.netrasystems.ai/health/db -o /dev/null; curl -s -w \"%{http_code} (%{time_total}s)\\n\" https://api.staging.netrasystems.ai/health/redis -o /dev/null'"
echo ""
echo "3. Check VPC connector errors:"
echo 'gcloud logging read "resource.type=\"vpc_access_connector\" AND severity>=ERROR" --project='$PROJECT' --limit=10'

echo ""
echo "Phase 2 script completed."
echo "========================================================================"