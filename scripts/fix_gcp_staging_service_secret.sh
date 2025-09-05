#!/bin/bash

# GCP Staging SERVICE_SECRET Emergency Fix Script
# Author: Five Whys Analysis Report
# Date: September 5, 2025
# Purpose: Immediate remediation of SERVICE_SECRET outage

set -e  # Exit on any error

# Configuration
PROJECT="netra-staging"
REGION="us-central1"
BACKEND_SERVICE="netra-backend-staging"
AUTH_SERVICE="netra-auth-service-pnovr5vsba-uc"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚨 GCP Staging SERVICE_SECRET Emergency Fix${NC}"
echo "=============================================="
echo "Date: $(date)"
echo "Project: $PROJECT"
echo "Region: $REGION"
echo ""

# Function to check if gcloud is authenticated
check_gcloud_auth() {
    echo -e "${BLUE}🔍 Checking gcloud authentication...${NC}"
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${RED}❌ Not authenticated with gcloud${NC}"
        echo "Run: gcloud auth login"
        exit 1
    fi
    
    local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    echo -e "${GREEN}✅ Authenticated as: $account${NC}"
}

# Function to check current SERVICE_SECRET status
check_service_secret_status() {
    echo -e "${BLUE}🔍 Checking current SERVICE_SECRET status...${NC}"
    
    # Check backend service
    local service_secret_present=$(gcloud run services describe $BACKEND_SERVICE \
        --project=$PROJECT \
        --region=$REGION \
        --format="value(spec.template.spec.containers[0].env[?(@.name=='SERVICE_SECRET')].name)" 2>/dev/null)
    
    if [ -n "$service_secret_present" ]; then
        echo -e "${GREEN}✅ SERVICE_SECRET is present in backend service${NC}"
        return 0
    else
        echo -e "${RED}❌ SERVICE_SECRET is MISSING from backend service${NC}"
        return 1
    fi
}

# Function to check if SECRET exists in Secret Manager
check_secret_manager() {
    echo -e "${BLUE}🔍 Checking GCP Secret Manager for SERVICE_SECRET...${NC}"
    
    if gcloud secrets describe SERVICE_SECRET --project=$PROJECT >/dev/null 2>&1; then
        echo -e "${GREEN}✅ SERVICE_SECRET exists in Secret Manager${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ SERVICE_SECRET not found in Secret Manager${NC}"
        return 1
    fi
}

# Function to create SERVICE_SECRET in Secret Manager
create_service_secret() {
    echo -e "${BLUE}🔧 Creating SERVICE_SECRET in Secret Manager...${NC}"
    
    # Generate a secure 32-character secret
    local secret_value=$(openssl rand -base64 32 | tr -d '\n')
    
    echo "Creating SERVICE_SECRET with generated value..."
    echo -n "$secret_value" | gcloud secrets create SERVICE_SECRET \
        --project=$PROJECT \
        --data-file=- \
        --replication-policy="automatic"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ SERVICE_SECRET created in Secret Manager${NC}"
        echo -e "${YELLOW}📝 Generated secret value: ${secret_value:0:8}...${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to create SERVICE_SECRET in Secret Manager${NC}"
        return 1
    fi
}

# Function to get SERVICE_SECRET value from Secret Manager
get_service_secret_value() {
    echo -e "${BLUE}🔍 Retrieving SERVICE_SECRET from Secret Manager...${NC}"
    
    local secret_value=$(gcloud secrets versions access latest \
        --secret="SERVICE_SECRET" \
        --project=$PROJECT 2>/dev/null)
    
    if [ -n "$secret_value" ]; then
        echo -e "${GREEN}✅ Successfully retrieved SERVICE_SECRET${NC}"
        echo "$secret_value"
        return 0
    else
        echo -e "${RED}❌ Failed to retrieve SERVICE_SECRET${NC}"
        return 1
    fi
}

# Function to update Cloud Run service with SERVICE_SECRET
update_backend_service() {
    local secret_value="$1"
    
    echo -e "${BLUE}🔧 Updating backend service with SERVICE_SECRET...${NC}"
    
    gcloud run services update $BACKEND_SERVICE \
        --project=$PROJECT \
        --region=$REGION \
        --set-env-vars="SERVICE_SECRET=$secret_value" \
        --quiet
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backend service updated with SERVICE_SECRET${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to update backend service${NC}"
        return 1
    fi
}

# Function to force service restart
restart_backend_service() {
    echo -e "${BLUE}🔄 Forcing backend service restart to reset circuit breaker...${NC}"
    
    local timestamp=$(date +%s)
    
    gcloud run services update $BACKEND_SERVICE \
        --project=$PROJECT \
        --region=$REGION \
        --set-env-vars="FORCE_RESTART=$timestamp" \
        --quiet
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backend service restart initiated${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to restart backend service${NC}"
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service_ready() {
    echo -e "${BLUE}⏳ Waiting for service to be ready...${NC}"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo -n "Attempt $attempt/$max_attempts: "
        
        local status=$(gcloud run services describe $BACKEND_SERVICE \
            --project=$PROJECT \
            --region=$REGION \
            --format="value(status.conditions[0].status)" 2>/dev/null)
        
        if [ "$status" = "True" ]; then
            echo -e "${GREEN}Service is ready${NC}"
            return 0
        else
            echo -e "${YELLOW}Service not ready yet (status: $status)${NC}"
            sleep 10
            ((attempt++))
        fi
    done
    
    echo -e "${RED}❌ Service did not become ready within expected time${NC}"
    return 1
}

# Function to test service health
test_service_health() {
    echo -e "${BLUE}🏥 Testing service health...${NC}"
    
    # Get service URL
    local service_url=$(gcloud run services describe $BACKEND_SERVICE \
        --project=$PROJECT \
        --region=$REGION \
        --format="value(status.url)")
    
    echo "Testing URL: $service_url/health"
    
    # Test health endpoint
    local http_status=$(curl -s -o /dev/null -w "%{http_code}" "$service_url/health" --max-time 30)
    
    if [ "$http_status" = "200" ]; then
        echo -e "${GREEN}✅ Health endpoint responding (HTTP $http_status)${NC}"
        return 0
    else
        echo -e "${RED}❌ Health endpoint not responding (HTTP $http_status)${NC}"
        return 1
    fi
}

# Function to check for circuit breaker errors
check_circuit_breaker_errors() {
    echo -e "${BLUE}🔍 Checking for circuit breaker errors...${NC}"
    
    # Check recent logs for circuit breaker errors
    local error_count=$(gcloud logging read \
        --project=$PROJECT \
        --filter="resource.labels.service_name=$BACKEND_SERVICE AND textPayload:(\"Circuit breaker\" AND \"open\")" \
        --limit=10 \
        --format="value(timestamp)" \
        --freshness=10m | wc -l)
    
    if [ "$error_count" -eq 0 ]; then
        echo -e "${GREEN}✅ No recent circuit breaker errors found${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ Found $error_count recent circuit breaker errors${NC}"
        echo "Recent errors:"
        gcloud logging read \
            --project=$PROJECT \
            --filter="resource.labels.service_name=$BACKEND_SERVICE AND textPayload:(\"Circuit breaker\" AND \"open\")" \
            --limit=3 \
            --format="value(timestamp,textPayload)" \
            --freshness=10m
        return 1
    fi
}

# Function to run comprehensive validation
run_validation() {
    echo -e "${BLUE}🧪 Running comprehensive validation...${NC}"
    
    local validation_passed=true
    
    # Test 1: SERVICE_SECRET present
    echo -n "1. SERVICE_SECRET present: "
    if check_service_secret_status >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        validation_passed=false
    fi
    
    # Test 2: Service health
    echo -n "2. Service health: "
    if test_service_health >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC}"
        validation_passed=false
    fi
    
    # Test 3: No circuit breaker errors
    echo -n "3. No circuit breaker errors: "
    if check_circuit_breaker_errors >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${YELLOW}WARN${NC}"
        # Don't fail validation for warnings
    fi
    
    if [ "$validation_passed" = true ]; then
        echo -e "${GREEN}✅ All critical validations passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Some validations failed${NC}"
        return 1
    fi
}

# Function to display final status
show_final_status() {
    echo ""
    echo -e "${BLUE}📊 Final Status Summary${NC}"
    echo "========================"
    
    # Service URL
    local service_url=$(gcloud run services describe $BACKEND_SERVICE \
        --project=$PROJECT \
        --region=$REGION \
        --format="value(status.url)")
    
    echo "🔗 Backend Service URL: $service_url"
    echo "🏥 Health Endpoint: $service_url/health"
    
    # Configuration status
    echo ""
    echo "📋 Configuration Status:"
    if check_service_secret_status >/dev/null 2>&1; then
        echo -e "   SERVICE_SECRET: ${GREEN}✅ Present${NC}"
    else
        echo -e "   SERVICE_SECRET: ${RED}❌ Missing${NC}"
    fi
    
    # Next steps
    echo ""
    echo "🔍 Next Steps:"
    echo "   1. Monitor logs for 10 minutes: gcloud logging read --project=$PROJECT --filter=\"resource.labels.service_name=$BACKEND_SERVICE\" --limit=20"
    echo "   2. Test authentication endpoints manually"
    echo "   3. Run integration tests: python tests/integration/test_auth_flow.py"
    echo "   4. Update monitoring alerts for SERVICE_SECRET"
}

# Main execution flow
main() {
    echo -e "${BLUE}🚀 Starting SERVICE_SECRET emergency fix...${NC}"
    
    # Step 1: Check prerequisites
    check_gcloud_auth
    
    # Step 2: Diagnose current state
    echo ""
    echo -e "${BLUE}📋 DIAGNOSIS PHASE${NC}"
    echo "=================="
    
    if check_service_secret_status; then
        echo -e "${YELLOW}⚠️ SERVICE_SECRET appears to be present${NC}"
        echo "This may not be the root cause. Proceeding with additional checks..."
    fi
    
    # Step 3: Ensure SERVICE_SECRET exists in Secret Manager
    echo ""
    echo -e "${BLUE}🔧 SECRET MANAGER PHASE${NC}"
    echo "======================="
    
    if ! check_secret_manager; then
        echo "Creating SERVICE_SECRET in Secret Manager..."
        if ! create_service_secret; then
            echo -e "${RED}❌ Failed to create SERVICE_SECRET. Manual intervention required.${NC}"
            exit 1
        fi
    fi
    
    # Step 4: Get secret value and update service
    echo ""
    echo -e "${BLUE}🔄 SERVICE UPDATE PHASE${NC}"
    echo "======================="
    
    local secret_value
    if ! secret_value=$(get_service_secret_value); then
        echo -e "${RED}❌ Cannot retrieve SERVICE_SECRET. Manual intervention required.${NC}"
        exit 1
    fi
    
    # Update backend service
    if ! update_backend_service "$secret_value"; then
        echo -e "${RED}❌ Failed to update backend service. Manual intervention required.${NC}"
        exit 1
    fi
    
    # Force restart to reset circuit breaker
    if ! restart_backend_service; then
        echo -e "${RED}❌ Failed to restart backend service. Manual intervention required.${NC}"
        exit 1
    fi
    
    # Step 5: Wait and validate
    echo ""
    echo -e "${BLUE}✅ VALIDATION PHASE${NC}"
    echo "==================="
    
    if ! wait_for_service_ready; then
        echo -e "${RED}❌ Service did not become ready. Check logs manually.${NC}"
        exit 1
    fi
    
    # Run comprehensive validation
    if ! run_validation; then
        echo -e "${RED}❌ Validation failed. Manual investigation required.${NC}"
        exit 1
    fi
    
    # Step 6: Final status
    show_final_status
    
    echo ""
    echo -e "${GREEN}🎉 SERVICE_SECRET emergency fix completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}⚠️ IMPORTANT: Monitor the system for the next 30 minutes to ensure stability.${NC}"
}

# Handle script interruption
trap 'echo -e "\n${RED}❌ Script interrupted. Check system state manually.${NC}"; exit 1' INT TERM

# Run main function
main "$@"