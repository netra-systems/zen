#!/bin/bash
# Runtime URL Validation for Staging/Production
# This script prevents localhost URLs from being used in staging/production

set -e

ENVIRONMENT=${ENVIRONMENT:-development}

validate_url() {
    local var_name=$1
    local var_value=$2
    local environment=$3
    
    if [[ "$environment" == "staging" || "$environment" == "production" ]]; then
        if [[ "$var_value" == *"localhost"* ]]; then
            echo "ERROR: $var_name contains localhost in $environment environment: $var_value"
            echo "This will cause CORS and authentication failures!"
            exit 1
        fi
        
        if [[ "$environment" == "staging" && "$var_value" != *"staging.netrasystems.ai"* && "$var_value" != "" ]]; then
            echo "WARNING: $var_name may not be correct for staging: $var_value"
        fi
        
        if [[ "$environment" == "production" && "$var_value" != *"netrasystems.ai"* && "$var_value" != "" ]]; then
            echo "WARNING: $var_name may not be correct for production: $var_value"
        fi
    fi
}

echo "Validating URLs for environment: $ENVIRONMENT"

# Check all URL environment variables
validate_url "API_URL" "$API_URL" "$ENVIRONMENT"
validate_url "NEXT_PUBLIC_API_URL" "$NEXT_PUBLIC_API_URL" "$ENVIRONMENT"  
validate_url "AUTH_URL" "$AUTH_URL" "$ENVIRONMENT"
validate_url "NEXT_PUBLIC_AUTH_URL" "$NEXT_PUBLIC_AUTH_URL" "$ENVIRONMENT"
validate_url "FRONTEND_URL" "$FRONTEND_URL" "$ENVIRONMENT"
validate_url "WS_URL" "$WS_URL" "$ENVIRONMENT"
validate_url "NEXT_PUBLIC_WS_URL" "$NEXT_PUBLIC_WS_URL" "$ENVIRONMENT"

echo "PASS - URL validation passed for $ENVIRONMENT"
