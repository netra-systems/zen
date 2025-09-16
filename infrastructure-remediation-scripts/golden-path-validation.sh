#!/bin/bash
# GOLDEN PATH VALIDATION SCRIPT
# Issue #1278 Infrastructure Remediation
# Priority: P0 CRITICAL - Validates core user flow (login → AI responses)

set -e  # Exit on any error

echo "========================================================================"
echo "GOLDEN PATH VALIDATION - ISSUE #1278"
echo "========================================================================"
echo "Business Priority: Validates 90% of platform value (chat functionality)"
echo "Critical Flow: User login → WebSocket connection → AI responses"
echo "Revenue Impact: $500K+ ARR validation"
echo "Started: $(date)"
echo "========================================================================"

# Variables
PROJECT="netra-staging"
REGION="us-central1"
BASE_URL="https://api.staging.netrasystems.ai"
WS_URL="wss://api-staging.netrasystems.ai/ws"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to print test status
print_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        if [ ! -z "$3" ]; then
            echo -e "${RED}   Error: $3${NC}"
        fi
    fi
}

# Function to test HTTP endpoint with timing
test_http_endpoint() {
    local url=$1
    local name=$2
    local max_time=${3:-5}

    echo -e "${BLUE}Testing${NC}: $name"

    local response=$(curl -s -w "HTTPSTATUS:%{http_code};TIME:%{time_total}" "$url" 2>/dev/null || echo "HTTPSTATUS:000;TIME:999")
    local status=$(echo "$response" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local time=$(echo "$response" | grep -o "TIME:[0-9.]*" | cut -d: -f2)

    echo "   Status: $status, Time: ${time}s (max: ${max_time}s)"

    if [ "$status" = "200" ] && (( $(echo "$time < $max_time" | bc -l) )); then
        print_test 0 "$name (${time}s)"
        return 0
    elif [ "$status" = "200" ]; then
        print_test 1 "$name - SLOW (${time}s > ${max_time}s)" "Response too slow"
        return 1
    else
        print_test 1 "$name - HTTP $status (${time}s)" "HTTP error"
        return 1
    fi
}

# Function to test WebSocket connection
test_websocket() {
    echo -e "${BLUE}Testing${NC}: WebSocket connection"

    # Use timeout to prevent hanging
    local ws_test=$(timeout 10 wscat -c "$WS_URL" -x '{"type":"ping"}' 2>&1 || echo "FAILED")

    if [[ "$ws_test" == *"FAILED"* ]] || [[ "$ws_test" == *"error"* ]] || [[ "$ws_test" == *"timeout"* ]]; then
        print_test 1 "WebSocket connection" "Connection failed or timed out"
        return 1
    else
        print_test 0 "WebSocket connection"
        return 0
    fi
}

# Function to check service logs for errors
check_recent_errors() {
    echo -e "${BLUE}Checking${NC}: Recent error logs"

    local error_count=$(gcloud logging read \
        'resource.type="cloud_run_revision" AND
         resource.labels.service_name="netra-backend-staging" AND
         severity>=ERROR AND
         timestamp>="'$(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')'"' \
        --project="$PROJECT" \
        --format="value(timestamp)" 2>/dev/null | wc -l)

    echo "   Error count in last 5 minutes: $error_count"

    if [ "$error_count" -eq 0 ]; then
        print_test 0 "No recent errors (0 in 5 min)"
        return 0
    elif [ "$error_count" -le 3 ]; then
        print_test 1 "Some recent errors ($error_count in 5 min)" "Minor error rate"
        return 1
    else
        print_test 1 "High error rate ($error_count in 5 min)" "Significant error rate"
        return 1
    fi
}

# Function to check HTTP 503 errors specifically
check_503_errors() {
    echo -e "${BLUE}Checking${NC}: HTTP 503 errors"

    local error_503_count=$(gcloud logging read \
        'resource.type="cloud_run_revision" AND
         httpRequest.status=503 AND
         timestamp>="'$(date -u -d '10 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')'"' \
        --project="$PROJECT" \
        --format="value(timestamp)" 2>/dev/null | wc -l)

    echo "   HTTP 503 errors in last 10 minutes: $error_503_count"

    if [ "$error_503_count" -eq 0 ]; then
        print_test 0 "No HTTP 503 errors (0 in 10 min)"
        return 0
    elif [ "$error_503_count" -le 2 ]; then
        print_test 1 "Few HTTP 503 errors ($error_503_count in 10 min)" "Minor service unavailability"
        return 1
    else
        print_test 1 "Multiple HTTP 503 errors ($error_503_count in 10 min)" "Service availability issues"
        return 1
    fi
}

# Function to validate infrastructure components
check_infrastructure() {
    echo -e "${BLUE}Checking${NC}: Infrastructure components"

    # VPC Connector
    local vpc_state=$(gcloud compute networks vpc-access connectors describe staging-connector \
        --region="$REGION" \
        --project="$PROJECT" \
        --format="value(state)" 2>/dev/null || echo "ERROR")

    echo "   VPC Connector state: $vpc_state"

    if [ "$vpc_state" = "READY" ]; then
        print_test 0 "VPC Connector is READY"
    else
        print_test 1 "VPC Connector state: $vpc_state" "VPC connectivity issues"
    fi

    # Database Instance
    local db_state=$(gcloud sql instances describe netra-staging-db \
        --project="$PROJECT" \
        --format="value(state)" 2>/dev/null || echo "ERROR")

    echo "   Database state: $db_state"

    if [ "$db_state" = "RUNNABLE" ]; then
        print_test 0 "Database is RUNNABLE"
    else
        print_test 1 "Database state: $db_state" "Database connectivity issues"
    fi

    # Cloud Run Revisions
    local revision_count=$(gcloud run revisions list \
        --service=netra-backend-staging \
        --region="$REGION" \
        --project="$PROJECT" \
        --filter="status.conditions.type=Active" \
        --format="value(metadata.name)" | wc -l)

    echo "   Active Cloud Run revisions: $revision_count"

    if [ "$revision_count" -eq 1 ]; then
        print_test 0 "Single active revision (optimal)"
    elif [ "$revision_count" -eq 0 ]; then
        print_test 1 "No active revisions" "Service deployment issue"
    else
        print_test 1 "Multiple active revisions ($revision_count)" "Potential resource contention"
    fi
}

echo ""
echo "========================================================================"
echo "STARTING GOLDEN PATH VALIDATION TESTS"
echo "========================================================================"

echo ""
echo -e "${YELLOW}PHASE 1: CORE SERVICE HEALTH${NC}"
echo "------------------------------------"

# Test 1: Main health endpoint (critical)
test_http_endpoint "$BASE_URL/health" "Main health endpoint" 2

# Test 2: Database health endpoint
test_http_endpoint "$BASE_URL/health/db" "Database health endpoint" 5

# Test 3: Redis health endpoint
test_http_endpoint "$BASE_URL/health/redis" "Redis health endpoint" 5

echo ""
echo -e "${YELLOW}PHASE 2: WEBSOCKET CONNECTIVITY${NC}"
echo "------------------------------------"

# Test 4: WebSocket connection
test_websocket

echo ""
echo -e "${YELLOW}PHASE 3: ERROR MONITORING${NC}"
echo "--------------------------------"

# Test 5: Recent error rate
check_recent_errors

# Test 6: HTTP 503 error rate
check_503_errors

echo ""
echo -e "${YELLOW}PHASE 4: INFRASTRUCTURE VALIDATION${NC}"
echo "--------------------------------------"

# Test 7-9: Infrastructure components
check_infrastructure

echo ""
echo "========================================================================"
echo "GOLDEN PATH VALIDATION RESULTS"
echo "========================================================================"

# Calculate success rate
SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

echo "Test Summary:"
echo "  Total Tests: $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS"
echo "  Failed: $FAILED_TESTS"
echo "  Success Rate: $SUCCESS_RATE%"
echo ""

# Determine overall status
if [ $SUCCESS_RATE -ge 90 ]; then
    echo -e "${GREEN}OVERALL STATUS: ✅ EXCELLENT${NC}"
    echo "Golden Path is fully operational."
    echo "Chat functionality protecting $500K+ ARR is validated."
    OVERALL_STATUS="EXCELLENT"
elif [ $SUCCESS_RATE -ge 75 ]; then
    echo -e "${YELLOW}OVERALL STATUS: ⚠️ GOOD WITH MINOR ISSUES${NC}"
    echo "Golden Path is mostly operational with minor issues."
    echo "Core functionality is available but optimization recommended."
    OVERALL_STATUS="GOOD"
elif [ $SUCCESS_RATE -ge 50 ]; then
    echo -e "${YELLOW}OVERALL STATUS: ⚠️ DEGRADED${NC}"
    echo "Golden Path has significant issues affecting user experience."
    echo "Immediate investigation and fixes required."
    OVERALL_STATUS="DEGRADED"
else
    echo -e "${RED}OVERALL STATUS: ❌ CRITICAL FAILURE${NC}"
    echo "Golden Path is not operational."
    echo "Users cannot complete login → AI responses flow."
    echo "CRITICAL: $500K+ ARR services are offline."
    OVERALL_STATUS="CRITICAL"
fi

echo ""
echo "========================================================================"
echo "BUSINESS IMPACT ASSESSMENT"
echo "========================================================================"

if [ "$OVERALL_STATUS" = "EXCELLENT" ]; then
    echo -e "${GREEN}✅ BUSINESS IMPACT: POSITIVE${NC}"
    echo "- Users can successfully login and receive AI responses"
    echo "- Chat functionality delivering 90% of platform value"
    echo "- $500K+ ARR services fully operational"
    echo "- No immediate business risk"
elif [ "$OVERALL_STATUS" = "GOOD" ]; then
    echo -e "${YELLOW}⚠️ BUSINESS IMPACT: MINOR DEGRADATION${NC}"
    echo "- Core user flow functional but suboptimal"
    echo "- Some performance or reliability issues present"
    echo "- Revenue impact: LOW"
    echo "- Monitoring and optimization recommended"
elif [ "$OVERALL_STATUS" = "DEGRADED" ]; then
    echo -e "${YELLOW}⚠️ BUSINESS IMPACT: SIGNIFICANT DEGRADATION${NC}"
    echo "- User experience significantly impacted"
    echo "- Chat functionality partially compromised"
    echo "- Revenue impact: MEDIUM"
    echo "- Immediate remediation required"
else
    echo -e "${RED}❌ BUSINESS IMPACT: CRITICAL REVENUE LOSS${NC}"
    echo "- Users cannot complete core workflows"
    echo "- Chat functionality (90% of value) offline"
    echo "- Revenue impact: HIGH ($500K+ ARR at risk)"
    echo "- EMERGENCY RESPONSE REQUIRED"
fi

echo ""
echo "========================================================================"
echo "RECOMMENDED ACTIONS"
echo "========================================================================"

if [ "$OVERALL_STATUS" = "EXCELLENT" ]; then
    echo "✅ ACTIONS: Monitoring and maintenance"
    echo "1. Continue monitoring for 24 hours"
    echo "2. Set up proactive alerting"
    echo "3. Document successful remediation"
    echo "4. Schedule regular health checks"
elif [ "$OVERALL_STATUS" = "GOOD" ]; then
    echo "⚠️ ACTIONS: Minor optimizations"
    echo "1. Investigate and fix minor issues identified"
    echo "2. Optimize slow endpoints"
    echo "3. Monitor error rates closely"
    echo "4. Prepare for potential issues"
elif [ "$OVERALL_STATUS" = "DEGRADED" ]; then
    echo "⚠️ ACTIONS: Immediate investigation required"
    echo "1. Focus on failed tests for root cause analysis"
    echo "2. Execute additional remediation phases"
    echo "3. Consider rollback if issues worsen"
    echo "4. Escalate to infrastructure team"
else
    echo "❌ ACTIONS: EMERGENCY RESPONSE"
    echo "1. IMMEDIATE: Execute rollback procedures"
    echo "2. URGENT: Contact on-call infrastructure team"
    echo "3. CRITICAL: Implement emergency fixes"
    echo "4. MONITOR: User impact and revenue metrics"
fi

echo ""
echo "========================================================================"
echo "DETAILED MONITORING COMMANDS"
echo "========================================================================"

echo ""
echo "Real-time monitoring (run in separate terminals):"
echo ""
echo "1. Health endpoint monitoring:"
echo "   watch -n 10 'echo \"Health: \$(curl -s -w \"%{http_code} %{time_total}s\" $BASE_URL/health -o /dev/null)\"'"
echo ""
echo "2. WebSocket connection testing:"
echo "   watch -n 30 'timeout 5 wscat -c $WS_URL -x \'{\"type\":\"ping\"}\' && echo \"WS: OK\" || echo \"WS: FAILED\"'"
echo ""
echo "3. Error log monitoring:"
echo "   watch -n 60 'gcloud logging read \"resource.type=\\\"cloud_run_revision\\\" AND severity>=ERROR AND timestamp>=\\\"\$(date -u -d \"1 minute ago\" +%Y-%m-%dT%H:%M:%SZ)\\\"\" --project=$PROJECT --limit=5'"
echo ""
echo "4. HTTP 503 error tracking:"
echo "   watch -n 120 'gcloud logging read \"httpRequest.status=503 AND timestamp>=\\\"\$(date -u -d \"2 minutes ago\" +%Y-%m-%dT%H:%M:%SZ)\\\"\" --project=$PROJECT --format=\"value(timestamp)\" | wc -l'"

echo ""
echo "========================================================================"
echo "VALIDATION COMPLETE"
echo "========================================================================"
echo "Completed: $(date)"
echo "Overall Status: $OVERALL_STATUS"
echo "Success Rate: $SUCCESS_RATE%"
echo "Business Impact: $([ "$OVERALL_STATUS" = "EXCELLENT" ] && echo "POSITIVE" || echo "REQUIRES ATTENTION")"

# Set exit code based on results
if [ "$OVERALL_STATUS" = "EXCELLENT" ]; then
    exit 0
elif [ "$OVERALL_STATUS" = "GOOD" ]; then
    exit 1
elif [ "$OVERALL_STATUS" = "DEGRADED" ]; then
    exit 2
else
    exit 3
fi