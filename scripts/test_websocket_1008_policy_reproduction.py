#!/usr/bin/env python3
"""
WebSocket 1008 Policy Violation Reproduction Test
TASK: Reproduce and fix the SSOT Authentication Policy Violation causing WebSocket 1008 errors

This test reproduces the exact error scenario happening in staging to identify the root cause.
"""

import asyncio
import json
import time
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Import test configuration
from tests.e2e.staging_test_config import get_staging_config


class WebSocket1008PolicyReproduction:
    """Reproduce the WebSocket 1008 SSOT Auth failed error."""
    
    def __init__(self):
        self.config = get_staging_config()
        self.test_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "staging",
            "test_purpose": "Reproduce 1008 policy violation",
            "attempts": []
        }
    
    async def test_scenario_1_direct_staging_connection(self):
        """
        SCENARIO 1: Direct connection to staging WebSocket with authentic JWT
        This replicates what test_real_websocket_message_flow does
        """
        print("\n" + "="*80)
        print("SCENARIO 1: Direct Staging Connection with Authentic JWT")
        print("="*80)
        
        attempt = {
            "scenario": "direct_staging_connection",
            "start_time": time.time(),
            "jwt_source": "staging_config.create_test_jwt_token()",
            "headers_used": [],
            "connection_result": None,
            "error_details": {}
        }
        
        try:
            # Get WebSocket headers the same way the failing test does
            headers = self.config.get_websocket_headers()
            attempt["headers_used"] = list(headers.keys())
            
            print(f"[INFO] Using WebSocket URL: {self.config.websocket_url}")
            print(f"[INFO] Headers being sent: {list(headers.keys())}")
            
            # Log JWT token details for debugging
            auth_header = headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                print(f"[INFO] JWT token length: {len(token)}")
                print(f"[INFO] JWT token parts: {token.count('.') + 1} (should be 3)")
                print(f"[INFO] Token prefix: {token[:20]}...")
                print(f"[INFO] Token suffix: ...{token[-20:]}")
            
            print(f"\n[ATTEMPT] Connecting to staging WebSocket...")
            
            # Attempt connection with timeout
            async with websockets.connect(
                self.config.websocket_url,
                close_timeout=10,
                additional_headers=headers
            ) as ws:
                attempt["connection_result"] = "SUCCESS"
                print(f"[SUCCESS] WebSocket connection established!")
                
                # Send a test message to see if we get the 1008 error
                test_message = {
                    "type": "ping",
                    "timestamp": time.time()
                }
                
                await ws.send(json.dumps(test_message))
                print(f"[INFO] Sent test message: {test_message['type']}")
                
                # Wait for response
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_data = json.loads(response)
                print(f"[INFO] Received response: {response_data}")
                
                attempt["first_message_response"] = response_data
                
        except websockets.exceptions.ConnectionClosedError as e:
            # This is where we expect to see the 1008 error
            attempt["connection_result"] = "CLOSED_WITH_ERROR"
            attempt["error_details"] = {
                "exception_type": "ConnectionClosedError",
                "code": e.code,
                "reason": e.reason,
                "is_1008_policy_violation": e.code == 1008,
                "reason_contains_ssot": "SSOT" in str(e.reason) if e.reason else False
            }
            
            print(f"[ERROR] Connection closed with code {e.code}: {e.reason}")
            
            if e.code == 1008:
                print(f"[REPRODUCE SUCCESS]  PASS:  Successfully reproduced 1008 policy violation!")
                print(f"[ERROR DETAILS] Reason: {e.reason}")
                
                if "SSOT Auth failed" in str(e.reason):
                    print(f"[EXACT MATCH]  PASS:  Found exact error: 'SSOT Auth failed'")
                    attempt["exact_error_reproduced"] = True
            else:
                print(f"[DIFFERENT ERROR] Got code {e.code} instead of 1008")
                
        except Exception as e:
            attempt["connection_result"] = "UNEXPECTED_ERROR"
            attempt["error_details"] = {
                "exception_type": type(e).__name__,
                "message": str(e),
                "unexpected": True
            }
            print(f"[UNEXPECTED ERROR] {type(e).__name__}: {e}")
        
        attempt["duration"] = time.time() - attempt["start_time"]
        self.test_results["attempts"].append(attempt)
        
        return attempt
    
    async def test_scenario_2_manual_jwt_validation(self):
        """
        SCENARIO 2: Test the JWT validation chain manually
        This tests the authentication path without WebSocket complications
        """
        print("\n" + "="*80)
        print("SCENARIO 2: Manual JWT Validation Chain Testing")
        print("="*80)
        
        attempt = {
            "scenario": "manual_jwt_validation",
            "start_time": time.time(),
            "validation_steps": [],
            "final_result": None
        }
        
        try:
            # Get a JWT token the same way the test does
            jwt_token = self.config.create_test_jwt_token()
            
            if not jwt_token:
                print("[ERROR] Failed to create JWT token")
                attempt["final_result"] = "NO_TOKEN_CREATED"
                return attempt
            
            print(f"[INFO] Created JWT token: {len(jwt_token)} characters")
            
            # Test 1: Basic JWT format validation
            from netra_backend.app.clients.auth_client_core import validate_jwt_format
            format_valid = validate_jwt_format(jwt_token)
            attempt["validation_steps"].append({
                "step": "format_validation",
                "result": format_valid,
                "details": f"JWT format valid: {format_valid}"
            })
            print(f"[STEP 1] JWT format validation: {format_valid}")
            
            # Test 2: Unified Authentication Service validation
            from netra_backend.app.services.unified_authentication_service import get_unified_auth_service, AuthenticationContext, AuthenticationMethod
            
            auth_service = get_unified_auth_service()
            
            print(f"[STEP 2] Testing unified authentication service...")
            auth_result = await auth_service.authenticate_token(
                jwt_token, 
                context=AuthenticationContext.WEBSOCKET,
                method=AuthenticationMethod.JWT_TOKEN
            )
            
            attempt["validation_steps"].append({
                "step": "unified_auth_service",
                "result": auth_result.success,
                "details": {
                    "success": auth_result.success,
                    "error": auth_result.error,
                    "error_code": auth_result.error_code,
                    "metadata": auth_result.metadata
                }
            })
            
            print(f"[STEP 2] Unified auth result: {auth_result.success}")
            if not auth_result.success:
                print(f"[ERROR] Auth failure: {auth_result.error_code} - {auth_result.error}")
                print(f"[METADATA] {json.dumps(auth_result.metadata, indent=2)}")
            
            # Test 3: Direct WebSocket authentication wrapper
            from netra_backend.app.websocket_core.unified_websocket_auth import get_websocket_authenticator
            
            # We can't test WebSocket authenticator without actual WebSocket, but we can check if it's properly initialized
            websocket_authenticator = get_websocket_authenticator()
            stats = websocket_authenticator.get_websocket_auth_stats()
            
            attempt["validation_steps"].append({
                "step": "websocket_authenticator_stats",
                "result": True,
                "details": stats
            })
            
            print(f"[STEP 3] WebSocket authenticator stats: {stats}")
            
            # Determine final result
            if not format_valid:
                attempt["final_result"] = "JWT_FORMAT_INVALID"
            elif not auth_result.success:
                attempt["final_result"] = f"AUTH_FAILED_{auth_result.error_code}"
            else:
                attempt["final_result"] = "ALL_VALIDATIONS_PASSED"
                
        except Exception as e:
            attempt["final_result"] = f"VALIDATION_EXCEPTION_{type(e).__name__}"
            attempt["validation_steps"].append({
                "step": "exception_occurred",
                "result": False,
                "details": {
                    "exception_type": type(e).__name__,
                    "message": str(e)
                }
            })
            print(f"[EXCEPTION] During validation: {e}")
        
        attempt["duration"] = time.time() - attempt["start_time"]
        self.test_results["attempts"].append(attempt)
        
        return attempt
    
    async def test_scenario_3_environment_differences(self):
        """
        SCENARIO 3: Test environment-specific differences that might cause staging issues
        """
        print("\n" + "="*80) 
        print("SCENARIO 3: Environment-Specific Configuration Analysis")
        print("="*80)
        
        attempt = {
            "scenario": "environment_analysis",
            "start_time": time.time(),
            "environment_checks": [],
            "differences_found": []
        }
        
        try:
            # Check environment variables and configuration
            from shared.isolated_environment import get_env
            env = get_env()
            
            # Critical environment checks
            critical_env_vars = [
                "ENVIRONMENT", 
                "AUTH_SERVICE_URL",
                "SERVICE_ID",
                "SERVICE_SECRET",
                "JWT_SECRET",
                "E2E_OAUTH_SIMULATION_KEY",
                "TESTING"
            ]
            
            env_status = {}
            for var_name in critical_env_vars:
                value = env.get(var_name)
                env_status[var_name] = {
                    "set": value is not None,
                    "value_length": len(value) if value else 0,
                    "value_preview": value[:20] + "..." if value and len(value) > 20 else value
                }
            
            attempt["environment_checks"].append({
                "check": "critical_environment_variables", 
                "results": env_status
            })
            
            print("[ENV CHECK] Critical environment variables:")
            for var_name, status in env_status.items():
                print(f"  {var_name}: {'SET' if status['set'] else 'NOT SET'} ({status['value_length']} chars)")
            
            # Check auth service settings
            from netra_backend.app.clients.auth_client_core import get_auth_service_client
            auth_client = get_auth_service_client()
            
            auth_config = {
                "base_url": auth_client.settings.base_url,
                "enabled": auth_client.settings.enabled,
                "service_id_set": bool(auth_client.service_id),
                "service_secret_set": bool(auth_client.service_secret),
            }
            
            attempt["environment_checks"].append({
                "check": "auth_client_configuration",
                "results": auth_config
            })
            
            print("[AUTH CONFIG] Auth client settings:")
            for key, value in auth_config.items():
                print(f"  {key}: {value}")
            
            # Analyze potential issues
            issues_found = []
            
            if not env_status.get("SERVICE_SECRET", {}).get("set"):
                issues_found.append({
                    "issue": "SERVICE_SECRET not set",
                    "impact": "Inter-service authentication will fail",
                    "severity": "HIGH"
                })
            
            if not env_status.get("AUTH_SERVICE_URL", {}).get("set"):
                issues_found.append({
                    "issue": "AUTH_SERVICE_URL not set", 
                    "impact": "Cannot connect to auth service",
                    "severity": "CRITICAL"
                })
            
            if env_status.get("ENVIRONMENT", {}).get("value_preview") != "staging":
                issues_found.append({
                    "issue": f"Environment is '{env_status.get('ENVIRONMENT', {}).get('value_preview')}' not 'staging'",
                    "impact": "May be using wrong configuration for staging tests",
                    "severity": "MEDIUM"
                })
            
            if not auth_config.get("enabled"):
                issues_found.append({
                    "issue": "Auth service is disabled",
                    "impact": "All authentication will fail",
                    "severity": "CRITICAL"
                })
            
            attempt["differences_found"] = issues_found
            
            print(f"\n[ANALYSIS] Found {len(issues_found)} potential issues:")
            for issue in issues_found:
                print(f"  [CRITICAL] {issue['severity']}: {issue['issue']}")
                print(f"     Impact: {issue['impact']}")
                
        except Exception as e:
            attempt["environment_checks"].append({
                "check": "exception_occurred",
                "results": {
                    "exception_type": type(e).__name__,
                    "message": str(e)
                }
            })
            print(f"[EXCEPTION] During environment analysis: {e}")
        
        attempt["duration"] = time.time() - attempt["start_time"]
        self.test_results["attempts"].append(attempt)
        
        return attempt
    
    async def run_all_scenarios(self):
        """Run all reproduction scenarios and generate report."""
        print("[DEBUG] WebSocket 1008 Policy Violation Reproduction Test")
        print("="*80)
        print("GOAL: Reproduce the exact 'received 1008 (policy violation) SSOT Auth failed' error")
        print("CONTEXT: This error is blocking staging WebSocket message flow tests")
        print("="*80)
        
        # Run all scenarios
        scenario_1 = await self.test_scenario_1_direct_staging_connection()
        scenario_2 = await self.test_scenario_2_manual_jwt_validation()  
        scenario_3 = await self.test_scenario_3_environment_differences()
        
        # Generate analysis
        print("\n" + "="*80)
        print("[ROOT CAUSE ANALYSIS]")
        print("="*80)
        
        # Check if we reproduced the 1008 error
        reproduced_1008 = scenario_1.get("error_details", {}).get("is_1008_policy_violation", False)
        exact_match = scenario_1.get("exact_error_reproduced", False)
        
        if reproduced_1008:
            print(" PASS:  SUCCESS: Reproduced the 1008 policy violation error!")
            if exact_match:
                print(" PASS:  EXACT MATCH: Found the exact 'SSOT Auth failed' error message!")
        else:
            print(" FAIL:  Could not reproduce the 1008 error in this environment")
        
        # Analyze the authentication chain
        auth_validation = scenario_2.get("final_result")
        if auth_validation and "AUTH_FAILED" in auth_validation:
            print(f"[DEBUG] AUTHENTICATION ISSUE IDENTIFIED: {auth_validation}")
            
            # Find the specific auth failure details
            for step in scenario_2.get("validation_steps", []):
                if step.get("step") == "unified_auth_service" and not step.get("result"):
                    auth_details = step.get("details", {})
                    print(f"[DEBUG] AUTH FAILURE DETAILS:")
                    print(f"   Error Code: {auth_details.get('error_code')}")
                    print(f"   Error Message: {auth_details.get('error')}")
                    
                    # This is likely the root cause
                    if auth_details.get("error_code") in ["NO_TOKEN", "INVALID_FORMAT", "VALIDATION_FAILED"]:
                        print(f"[ROOT CAUSE] IDENTIFIED: {auth_details.get('error_code')}")
        
        # Check environment issues
        env_issues = scenario_3.get("differences_found", [])
        critical_issues = [issue for issue in env_issues if issue.get("severity") == "CRITICAL"]
        
        if critical_issues:
            print(f"[CRITICAL] ENVIRONMENT ISSUES FOUND:")
            for issue in critical_issues:
                print(f"   {issue['issue']}: {issue['impact']}")
        
        # Generate final report
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate a comprehensive report of the reproduction test."""
        print("\n" + "="*80)
        print("[REPORT] COMPREHENSIVE REPRODUCTION REPORT")
        print("="*80)
        
        print(f"Test completed at: {self.test_results['timestamp']}")
        print(f"Total scenarios tested: {len(self.test_results['attempts'])}")
        
        # Summary of each scenario
        for attempt in self.test_results['attempts']:
            print(f"\n[SCENARIO] {attempt['scenario']}")
            print(f"   Duration: {attempt.get('duration', 0):.2f}s")
            
            if attempt['scenario'] == 'direct_staging_connection':
                result = attempt.get('connection_result')
                print(f"   Connection Result: {result}")
                if attempt.get('error_details', {}).get('is_1008_policy_violation'):
                    print(f"    PASS:  1008 Error Reproduced: {attempt['error_details']['reason']}")
            
            elif attempt['scenario'] == 'manual_jwt_validation':
                print(f"   Validation Result: {attempt.get('final_result')}")
                passed_steps = len([s for s in attempt.get('validation_steps', []) if s.get('result')])
                total_steps = len(attempt.get('validation_steps', []))
                print(f"   Validation Steps: {passed_steps}/{total_steps} passed")
            
            elif attempt['scenario'] == 'environment_analysis':
                issues = len(attempt.get('differences_found', []))
                print(f"   Issues Found: {issues}")
        
        # Recommendations
        print(f"\n[RECOMMENDATIONS] FIXES:")
        
        # Check if we found specific issues
        for attempt in self.test_results['attempts']:
            if attempt['scenario'] == 'manual_jwt_validation':
                final_result = attempt.get('final_result', '')
                if 'AUTH_FAILED_NO_TOKEN' in final_result:
                    print("   1. Fix JWT token extraction from WebSocket headers")
                elif 'AUTH_FAILED_INVALID_FORMAT' in final_result:
                    print("   2. Fix JWT token format validation logic")
                elif 'AUTH_FAILED_VALIDATION_FAILED' in final_result:
                    print("   3. Fix JWT token validation against auth service")
                    
            elif attempt['scenario'] == 'environment_analysis':
                for issue in attempt.get('differences_found', []):
                    if issue.get('severity') == 'CRITICAL':
                        print(f"   4. Fix environment: {issue['issue']}")
        
        # Save report to file
        report_filename = f"websocket_1008_reproduction_report_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n[FILES] Detailed report saved to: {report_filename}")
        print("="*80)


async def main():
    """Run the WebSocket 1008 policy violation reproduction test."""
    reproduction_test = WebSocket1008PolicyReproduction()
    await reproduction_test.run_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())