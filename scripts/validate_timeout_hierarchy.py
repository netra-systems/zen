#!/usr/bin/env python3
"""Priority 3 Timeout Hierarchy Validation Script

**BUSINESS CONTEXT**: Validates $200K+ MRR business value restoration through
proper timeout hierarchy implementation for cloud-native GCP Cloud Run environment.

**VALIDATION CRITERIA**:
1. WebSocket recv timeout (35s) > Agent execution timeout (30s) in staging
2. Timeout hierarchy properly configured across all environments
3. Environment detection working correctly
4. Centralized timeout configuration accessible

**SUCCESS CRITERIA**:
- All timeout validations pass
- No premature WebSocket timeout failures
- Coordination between 35s WebSocket  ->  30s Agent maintained
- Tests work in both local and Cloud Run environments

Usage:
    python scripts/validate_timeout_hierarchy.py
    python scripts/validate_timeout_hierarchy.py --environment staging
    python scripts/validate_timeout_hierarchy.py --validate-integration
"""

import sys
import os
import argparse
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_timeout_configuration() -> Dict[str, Any]:
    """Validate the centralized timeout configuration system."""
    
    print("[VALIDATION] Validating Priority 3 Timeout Hierarchy Implementation...")
    print("="*70)
    
    results = {
        "success": True,
        "environment": None,
        "timeout_hierarchy": {},
        "validation_errors": [],
        "business_impact": "$200K+ MRR reliability validation"
    }
    
    try:
        # Test 1: Import centralized timeout configuration
        print("1. Testing centralized timeout configuration import...")
        from netra_backend.app.core.timeout_configuration import (
            timeout_manager, 
            get_websocket_recv_timeout,
            get_agent_execution_timeout,
            validate_timeout_hierarchy,
            get_timeout_hierarchy_info
        )
        print("   [OK] Centralized timeout configuration imported successfully")
        
        # Test 2: Environment detection
        print("\n2. Testing environment detection...")
        hierarchy_info = get_timeout_hierarchy_info()
        environment = hierarchy_info["environment"]
        results["environment"] = environment
        print(f"   [INFO] Detected environment: {environment}")
        
        # Test 3: Timeout hierarchy validation
        print("\n3. Testing timeout hierarchy coordination...")
        websocket_timeout = get_websocket_recv_timeout()
        agent_timeout = get_agent_execution_timeout()
        
        print(f"   [DATA] WebSocket recv timeout: {websocket_timeout}s")
        print(f"   [DATA] Agent execution timeout: {agent_timeout}s")
        
        # Critical business validation: WebSocket > Agent
        if websocket_timeout > agent_timeout:
            gap = websocket_timeout - agent_timeout
            print(f"   [OK] Timeout hierarchy valid: {gap}s coordination gap")
            results["timeout_hierarchy"]["valid"] = True
            results["timeout_hierarchy"]["gap"] = gap
        else:
            error = f"CRITICAL: WebSocket timeout ({websocket_timeout}s) <= Agent timeout ({agent_timeout}s)"
            print(f"   [ERROR] {error}")
            results["validation_errors"].append(error)
            results["success"] = False
            
        # Test 4: Full hierarchy validation
        print("\n4. Testing complete timeout hierarchy...")
        hierarchy_valid = validate_timeout_hierarchy()
        if hierarchy_valid:
            print("   [OK] Complete timeout hierarchy validation passed")
        else:
            error = "Complete timeout hierarchy validation failed"
            print(f"   [ERROR] {error}")
            results["validation_errors"].append(error)
            results["success"] = False
            
        # Test 5: Environment-specific validation
        print(f"\n5. Testing {environment} environment-specific timeouts...")
        
        if environment == "staging":
            # PRIORITY 3 FIX: Staging should have 35s WebSocket, 30s Agent
            expected_ws_timeout = 35
            expected_agent_timeout = 30
            
            if websocket_timeout == expected_ws_timeout:
                print(f"   [OK] Staging WebSocket timeout correct: {websocket_timeout}s")
            else:
                error = f"Staging WebSocket timeout incorrect: expected {expected_ws_timeout}s, got {websocket_timeout}s"
                print(f"   [ERROR] {error}")
                results["validation_errors"].append(error)
                results["success"] = False
                
            if agent_timeout == expected_agent_timeout:
                print(f"   [OK] Staging Agent timeout correct: {agent_timeout}s")
            else:
                error = f"Staging Agent timeout incorrect: expected {expected_agent_timeout}s, got {agent_timeout}s"
                print(f"   [ERROR] {error}")
                results["validation_errors"].append(error)
                results["success"] = False
                
        elif environment == "local":
            # Local development: shorter timeouts for fast feedback
            if websocket_timeout <= 15 and agent_timeout <= 10:
                print(f"   [OK] Local development timeouts appropriate")
            else:
                print(f"   [WARN] Local timeouts may be high for development feedback")
                
        elif environment == "production":
            # Production: longer timeouts for reliability
            if websocket_timeout >= 40 and agent_timeout >= 35:
                print(f"   [OK] Production timeouts appropriate for reliability")
            else:
                error = "Production timeouts may be too low for reliability"
                print(f"   [ERROR] {error}")
                results["validation_errors"].append(error)
                
        # Store hierarchy information
        results["timeout_hierarchy"].update(hierarchy_info)
        
    except ImportError as e:
        error = f"Failed to import timeout configuration: {e}"
        print(f"   [ERROR] {error}")
        results["validation_errors"].append(error)
        results["success"] = False
        
    except Exception as e:
        error = f"Unexpected validation error: {e}"
        print(f"   [ERROR] {error}")
        results["validation_errors"].append(error)
        results["success"] = False
        
    return results


def validate_integration_with_test_files() -> Dict[str, Any]:
    """Validate integration with existing test files."""
    
    print("\n[INTEGRATION] Validating Integration with Test Files...")
    print("="*50)
    
    integration_results = {
        "success": True,
        "test_file_updates": [],
        "integration_errors": []
    }
    
    try:
        # Test 1: Staging test config integration
        print("1. Testing staging test config integration...")
        from tests.e2e.staging_test_config import get_staging_config
        
        staging_config = get_staging_config()
        
        # Test cloud-native timeout method
        if hasattr(staging_config, 'get_cloud_native_timeout'):
            cloud_timeout = staging_config.get_cloud_native_timeout()
            print(f"   [OK] Staging config cloud timeout: {cloud_timeout}s")
            integration_results["test_file_updates"].append("staging_test_config.py: get_cloud_native_timeout() method added")
        else:
            error = "Staging config missing get_cloud_native_timeout() method"
            print(f"   [ERROR] {error}")
            integration_results["integration_errors"].append(error)
            integration_results["success"] = False
            
        # Test updated timeout values
        if hasattr(staging_config, 'websocket_recv_timeout'):
            if staging_config.websocket_recv_timeout == 35:
                print(f"   [OK] Staging config WebSocket recv timeout: {staging_config.websocket_recv_timeout}s")
                integration_results["test_file_updates"].append("staging_test_config.py: WebSocket recv timeout updated to 35s")
            else:
                error = f"Staging config WebSocket timeout incorrect: {staging_config.websocket_recv_timeout}s"
                print(f"   [ERROR] {error}")
                integration_results["integration_errors"].append(error)
                
        if hasattr(staging_config, 'agent_execution_timeout'):
            if staging_config.agent_execution_timeout == 30:
                print(f"   [OK] Staging config Agent execution timeout: {staging_config.agent_execution_timeout}s")
                integration_results["test_file_updates"].append("staging_test_config.py: Agent execution timeout updated to 30s")
            else:
                error = f"Staging config Agent timeout incorrect: {staging_config.agent_execution_timeout}s"
                print(f"   [ERROR] {error}")
                integration_results["integration_errors"].append(error)
                
    except ImportError as e:
        error = f"Failed to import staging test config: {e}"
        print(f"   [ERROR] {error}")
        integration_results["integration_errors"].append(error)
        integration_results["success"] = False
        
    except Exception as e:
        error = f"Integration validation error: {e}"
        print(f"   [ERROR] {error}")
        integration_results["integration_errors"].append(error)
        integration_results["success"] = False
        
    return integration_results


def generate_summary_report(results: Dict[str, Any], integration_results: Dict[str, Any] = None) -> None:
    """Generate summary report of timeout hierarchy validation."""
    
    print("\n[SUMMARY] PRIORITY 3 TIMEOUT HIERARCHY VALIDATION SUMMARY")
    print("="*70)
    
    # Overall status
    overall_success = results["success"] and (integration_results is None or integration_results["success"])
    status_text = "[PASS]" if overall_success else "[FAIL]"
    business_impact = "RESTORED" if overall_success else "AT RISK"
    
    print(f"{status_text} Overall Validation: {'PASSED' if overall_success else 'FAILED'}")
    print(f"[BUSINESS] Business Impact ($200K+ MRR): {business_impact}")
    print(f"[ENV] Environment: {results.get('environment', 'Unknown')}")
    
    # Timeout hierarchy details
    if "timeout_hierarchy" in results:
        hierarchy = results["timeout_hierarchy"]
        if hierarchy.get("valid"):
            gap = hierarchy.get("gap", 0)
            print(f"[TIMEOUT] Coordination: {hierarchy.get('websocket_recv_timeout')}s WebSocket -> {hierarchy.get('agent_execution_timeout')}s Agent ({gap}s gap)")
        else:
            print(f"[WARN] Timeout Coordination: HIERARCHY BROKEN")
    
    # Validation errors
    if results.get("validation_errors"):
        print(f"\n[ERROR] Validation Errors ({len(results['validation_errors'])}):")
        for i, error in enumerate(results["validation_errors"], 1):
            print(f"   {i}. {error}")
            
    # Integration status
    if integration_results:
        if integration_results["success"]:
            print(f"\n[OK] Integration Status: Test files successfully updated")
            if integration_results.get("test_file_updates"):
                print(f"[FILES] File Updates ({len(integration_results['test_file_updates'])}):")
                for update in integration_results["test_file_updates"]:
                    print(f"   - {update}")
        else:
            print(f"\n[ERROR] Integration Status: Test file integration issues")
            if integration_results.get("integration_errors"):
                print(f"[ERROR] Integration Errors ({len(integration_results['integration_errors'])}):")
                for error in integration_results["integration_errors"]:
                    print(f"   - {error}")
    
    # Business recommendations
    print(f"\n[RECOMMENDATIONS] BUSINESS ACTIONS:")
    if overall_success:
        print("   [ACTION] Deploy changes to staging to restore $200K+ MRR reliability")
        print("   [ACTION] Monitor WebSocket/Agent coordination in Cloud Run environment") 
        print("   [ACTION] Run staging tests to validate timeout hierarchy effectiveness")
    else:
        print("   [CRITICAL] Fix validation errors before deploying to prevent MRR impact")
        print("   [CRITICAL] Review timeout hierarchy configuration for business continuity")
        print("   [CRITICAL] Address integration issues to ensure test stability")


def main():
    """Main validation execution with command line arguments."""
    
    parser = argparse.ArgumentParser(description="Validate Priority 3 timeout hierarchy fixes")
    parser.add_argument("--environment", help="Force specific environment for testing")
    parser.add_argument("--validate-integration", action="store_true", help="Include test file integration validation")
    parser.add_argument("--json-output", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    
    # Set environment if specified
    if args.environment:
        os.environ["ENVIRONMENT"] = args.environment
        print(f"[CONFIG] Forcing environment: {args.environment}")
        
    # Run core validation
    results = validate_timeout_configuration()
    
    # Run integration validation if requested
    integration_results = None
    if args.validate_integration:
        integration_results = validate_integration_with_test_files()
    
    # Output results
    if args.json_output:
        import json
        output = {
            "validation_results": results,
            "integration_results": integration_results
        }
        print(json.dumps(output, indent=2))
    else:
        generate_summary_report(results, integration_results)
    
    # Return appropriate exit code for CI/CD
    overall_success = results["success"] and (integration_results is None or integration_results["success"])
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()