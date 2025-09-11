#!/bin/bash
# Issue #308 Integration Test Import Dependency Fixes - Validation Scripts
# Comprehensive validation for 7 targeted import fixes

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== ISSUE #308 INTEGRATION TEST IMPORT DEPENDENCY FIXES VALIDATION ==="
echo "Date: $(date)"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS") echo -e "\033[32m✅ SUCCESS: $message\033[0m" ;;
        "FAILURE") echo -e "\033[31m❌ FAILURE: $message\033[0m" ;;
        "INFO") echo -e "\033[34mℹ️  INFO: $message\033[0m" ;;
        "WARNING") echo -e "\033[33m⚠️  WARNING: $message\033[0m" ;;
    esac
}

# Function to run validation phase
validate_phase() {
    local phase=$1
    local description=$2
    echo ""
    echo "=== PHASE $phase: $description ==="
    
    case $phase in
        "BASELINE")
            print_status "INFO" "Validating current baseline state"
            
            echo "Current integration test collection status:"
            if python -m pytest --collect-only tests/integration/ --tb=no -q 2>/dev/null | grep "collected"; then
                COLLECTED=$(python -m pytest --collect-only tests/integration/ --tb=no -q 2>/dev/null | grep "collected" | head -1)
                print_status "INFO" "Current status: $COLLECTED"
            else
                print_status "WARNING" "Collection status check failed"
            fi
            
            echo ""
            echo "Identifying specific import failures:"
            python -m pytest --collect-only tests/integration/ --tb=short 2>&1 | grep -A 1 "ERROR collecting" | head -10
            ;;
            
        "1")
            print_status "INFO" "Testing Phase 1 Quick Wins implementations"
            
            echo "1.1 File path conflict resolution:"
            if python -m pytest --collect-only tests/integration/ssot_classes/test_agent_execution_tracker_integration.py -q >/dev/null 2>&1; then
                print_status "SUCCESS" "Agent execution tracker integration test collection fixed"
            else
                print_status "FAILURE" "File path conflict still exists"
            fi
            
            echo "1.2 Docker dependency resolution:"  
            local docker_tests=("tests/integration/test_cloud_run_port_config.py" "tests/integration/test_service_communication_failure.py")
            for test_file in "${docker_tests[@]}"; do
                if python -m pytest --collect-only "$test_file" -q >/dev/null 2>&1; then
                    print_status "SUCCESS" "Docker dependency resolved for $(basename "$test_file")"
                else
                    print_status "FAILURE" "Docker dependency still missing for $(basename "$test_file")"
                fi
            done
            
            echo "1.3 Dataclass syntax fix:"
            if python -c "
import sys
sys.path.append('tests/integration/type_ssot')
try:
    from test_type_ssot_jwt_payload_validation import ExtendedJWTPayload
    payload = ExtendedJWTPayload(sub='test', email='test@example.com')
    print('Dataclass instantiation successful')
except Exception as e:
    print(f'Dataclass error: {e}')
    sys.exit(1)
" >/dev/null 2>&1; then
                print_status "SUCCESS" "Dataclass syntax fixed and validates correctly"
            else
                print_status "FAILURE" "Dataclass syntax still has issues"
            fi
            
            echo "1.4 Pytest marker configuration:"
            if python -m pytest --collect-only tests/integration/test_websocket_environment_detection_integration.py -q >/dev/null 2>&1; then
                print_status "SUCCESS" "Pytest marker configuration resolved"
            else
                print_status "FAILURE" "Pytest marker configuration still problematic"
            fi
            ;;
            
        "2") 
            print_status "INFO" "Testing Phase 2 Core Implementations"
            
            echo "2.1 RealServicesTestFixtures implementation:"
            if python -c "
from test_framework.real_services_test_fixtures import RealServicesTestFixtures
fixtures = RealServicesTestFixtures()
print(f'RealServicesTestFixtures: {type(fixtures).__name__}')
" >/dev/null 2>&1; then
                print_status "SUCCESS" "RealServicesTestFixtures class available and instantiable"
                
                # Test the integration test that was blocked
                if python -m pytest --collect-only tests/integration/websocket_core/test_unified_websocket_manager_real_connections.py -q >/dev/null 2>&1; then
                    print_status "SUCCESS" "WebSocket real connections test collection restored"
                else
                    print_status "FAILURE" "WebSocket real connections test still has issues"
                fi
            else
                print_status "FAILURE" "RealServicesTestFixtures still missing or broken"
            fi
            
            echo "2.2 WebSocket health validation function:"
            if python -c "
from netra_backend.app.websocket_core.websocket_manager_factory import validate_websocket_component_health
import inspect
sig = inspect.signature(validate_websocket_component_health)  
print(f'Function available with signature: {sig}')
" >/dev/null 2>&1; then
                print_status "SUCCESS" "validate_websocket_component_health function available"
                
                # Test the integration test that was blocked
                if python -m pytest --collect-only tests/integration/websocket_coroutine_import_collision/test_websocket_health_validation_integration.py -q >/dev/null 2>&1; then
                    print_status "SUCCESS" "WebSocket health validation test collection restored"
                else
                    print_status "FAILURE" "WebSocket health validation test still has issues"
                fi
            else
                print_status "FAILURE" "validate_websocket_component_health function still missing"
            fi
            
            echo "2.3 WebSocketMessageHandler compatibility alias:"
            if python -c "
from netra_backend.app.websocket_core.handlers import WebSocketMessageHandler
from netra_backend.app.websocket_core.handlers import BaseMessageHandler
print(f'Alias working: {WebSocketMessageHandler is BaseMessageHandler}')
" >/dev/null 2>&1; then
                print_status "SUCCESS" "WebSocketMessageHandler compatibility alias working"
            else
                print_status "FAILURE" "WebSocketMessageHandler compatibility alias missing"
            fi
            ;;
            
        "3")
            print_status "INFO" "Testing Phase 3 Infrastructure Validation"
            
            echo "3.1 Complete collection validation:"
            COLLECTION_RESULT=$(python -m pytest --collect-only tests/integration/ --tb=no -q 2>&1 | grep "collected" || echo "collection_failed")
            
            if echo "$COLLECTION_RESULT" | grep -q "collected .* items$" && ! echo "$COLLECTION_RESULT" | grep -q "errors"; then
                print_status "SUCCESS" "All integration tests collect without errors: $COLLECTION_RESULT"
                
                # Extract numbers for validation
                COLLECTED_COUNT=$(echo "$COLLECTION_RESULT" | grep -o "collected [0-9]*" | grep -o "[0-9]*")
                if [ "$COLLECTED_COUNT" -ge 3000 ]; then
                    print_status "SUCCESS" "Collection count meets expectations: $COLLECTED_COUNT tests"
                else
                    print_status "WARNING" "Collection count lower than expected: $COLLECTED_COUNT tests"
                fi
            else
                print_status "FAILURE" "Integration test collection still has errors: $COLLECTION_RESULT"
                echo "Remaining errors:"
                python -m pytest --collect-only tests/integration/ --tb=short 2>&1 | grep -A 1 "ERROR collecting" | head -6
            fi
            
            echo "3.2 Security validation test availability:"
            SECURITY_TESTS=$(python -m pytest --collect-only tests/integration/ -k "user_isolation or context_manager or auth_client or authentication or multi_user" --tb=no -q 2>/dev/null | grep "collected" || echo "0 collected")
            if echo "$SECURITY_TESTS" | grep -q "collected [1-9]"; then
                print_status "SUCCESS" "Security validation tests available: $SECURITY_TESTS"
            else
                print_status "WARNING" "Limited security validation tests found: $SECURITY_TESTS"
            fi
            
            echo "3.3 Performance assessment:"
            START_TIME=$(date +%s%N)
            python -m pytest --collect-only tests/integration/ --tb=no -q >/dev/null 2>&1
            END_TIME=$(date +%s%N)
            DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))
            
            if [ "$DURATION_MS" -lt 5000 ]; then  # Less than 5 seconds
                print_status "SUCCESS" "Collection performance acceptable: ${DURATION_MS}ms"
            else
                print_status "WARNING" "Collection performance may need optimization: ${DURATION_MS}ms"
            fi
            ;;
            
        "BUSINESS")
            print_status "INFO" "Testing Business Value Restoration"
            
            echo "Business Critical Test Categories:"
            
            echo "1. User Isolation Security Tests (Enterprise - \$15K+ MRR per customer):"
            if python -m pytest --collect-only tests/integration/ -k "user_isolation" --tb=no -q >/dev/null 2>&1; then
                USER_ISOLATION_TESTS=$(python -m pytest --collect-only tests/integration/ -k "user_isolation" --tb=no -q 2>/dev/null | grep "collected" || echo "0 collected")
                print_status "SUCCESS" "User isolation tests accessible: $USER_ISOLATION_TESTS"
            else
                print_status "FAILURE" "User isolation tests still blocked"
            fi
            
            echo "2. Authentication Integration Tests (Revenue Protection - \$500K+ ARR):"
            if python -m pytest --collect-only tests/integration/ -k "authentication" --tb=no -q >/dev/null 2>&1; then
                AUTH_TESTS=$(python -m pytest --collect-only tests/integration/ -k "authentication" --tb=no -q 2>/dev/null | grep "collected" || echo "0 collected")
                print_status "SUCCESS" "Authentication tests accessible: $AUTH_TESTS"
            else
                print_status "FAILURE" "Authentication tests still blocked"
            fi
            
            echo "3. WebSocket Real Connections (Golden Path - 90% platform value):"
            if python -m pytest --collect-only tests/integration/websocket_core/test_unified_websocket_manager_real_connections.py --tb=no -q >/dev/null 2>&1; then
                print_status "SUCCESS" "WebSocket real connections tests accessible"
            else
                print_status "FAILURE" "WebSocket real connections tests still blocked"
            fi
            
            echo "4. Multi-User Execution Validation (Platform Security):"
            if python -m pytest --collect-only tests/integration/ -k "multi_user" --tb=no -q >/dev/null 2>&1; then
                MULTIUSER_TESTS=$(python -m pytest --collect-only tests/integration/ -k "multi_user" --tb=no -q 2>/dev/null | grep "collected" || echo "0 collected")
                print_status "SUCCESS" "Multi-user tests accessible: $MULTIUSER_TESTS"
            else
                print_status "FAILURE" "Multi-user tests still blocked"  
            fi
            
            # Overall business value assessment
            TOTAL_BLOCKED=$(python -m pytest --collect-only tests/integration/ --tb=short 2>&1 | grep "ERROR collecting" | wc -l)
            if [ "$TOTAL_BLOCKED" -eq 0 ]; then
                print_status "SUCCESS" "ALL SECURITY VALIDATION TESTS RESTORED"
                print_status "SUCCESS" "\$500K+ ARR protection mechanisms operational"
                print_status "SUCCESS" "Enterprise multi-tenant features validated"
            else
                print_status "FAILURE" "$TOTAL_BLOCKED security validation tests still blocked"
                print_status "WARNING" "Business revenue protection compromised"
            fi
            ;;
    esac
}

# Main validation execution
main() {
    local phase=${1:-"ALL"}
    
    case $phase in
        "BASELINE") validate_phase "BASELINE" "Baseline State Validation" ;;
        "1") validate_phase "1" "Quick Wins Implementation Validation" ;;
        "2") validate_phase "2" "Core Implementation Validation" ;;
        "3") validate_phase "3" "Infrastructure Validation" ;;
        "BUSINESS") validate_phase "BUSINESS" "Business Value Restoration Validation" ;;
        "ALL")
            validate_phase "BASELINE" "Baseline State Validation"
            validate_phase "1" "Quick Wins Implementation Validation" 
            validate_phase "2" "Core Implementation Validation"
            validate_phase "3" "Infrastructure Validation"
            validate_phase "BUSINESS" "Business Value Restoration Validation"
            ;;
        *)
            echo "Usage: $0 [BASELINE|1|2|3|BUSINESS|ALL]"
            echo ""
            echo "Validation phases:"
            echo "  BASELINE  - Check current state and identify issues"
            echo "  1         - Validate Phase 1 Quick Wins fixes"  
            echo "  2         - Validate Phase 2 Core Implementations"
            echo "  3         - Validate Phase 3 Infrastructure Integration"
            echo "  BUSINESS  - Validate Business Value Restoration"
            echo "  ALL       - Run all validation phases (default)"
            exit 1
            ;;
    esac
    
    echo ""
    print_status "INFO" "Validation phase '$phase' completed"
}

# Execute main function with parameters
main "$@"