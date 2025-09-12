#!/usr/bin/env python3
"""
GitHub Issue #113 WebSocket Authentication Header Stripping Validation
CRITICAL: Manual validation of test scenarios to verify issue detection

This script manually tests the scenarios that the existing tests SHOULD catch
to validate if they properly detect the GCP Load Balancer header stripping issue.
"""

import asyncio
import logging
import json
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from tests.e2e.staging_config import StagingTestConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketHeaderStrippingValidator:
    """
    Validates the WebSocket header stripping scenarios manually.
    
    This simulates what the tests should catch when the GCP Load Balancer
    strips authentication headers from WebSocket upgrade requests.
    """
    
    def __init__(self):
        self.staging_config = StagingTestConfig()
        try:
            self.e2e_helper = E2EWebSocketAuthHelper(environment="staging") 
        except Exception as e:
            logger.warning(f"E2E helper initialization failed: {e}")
            self.e2e_helper = None
            
        # Use local WebSocket for testing if staging not available
        self.test_websocket_url = "ws://localhost:8002/ws"
        
    async def validate_missing_auth_headers_scenario(self) -> Dict[str, Any]:
        """
        CRITICAL: Test scenario where GCP Load Balancer strips Authorization headers.
        
        This simulates the exact issue from GitHub #113 - WebSocket connections
        without authentication headers should FAIL HARD.
        """
        result = {
            "test_name": "missing_auth_headers_scenario",
            "description": "Simulates GCP Load Balancer stripping Authorization headers",
            "expected_outcome": "CONNECTION_SHOULD_FAIL",
            "actual_outcome": None,
            "issue_detected": False,
            "error_details": None
        }
        
        # Headers that simulate what gets through Load Balancer WITHOUT auth
        stripped_headers = {
            "host": "staging.netra.ai", 
            "via": "1.1 google",
            "x-forwarded-for": "203.0.113.1",
            "x-forwarded-proto": "https",
            "connection": "upgrade",
            "upgrade": "websocket",
            "sec-websocket-key": "test-key-123",
            "sec-websocket-version": "13"
            # CRITICAL: NO "authorization" header - simulates Load Balancer stripping
        }
        
        logger.info(" SEARCH:  Testing missing Authorization header scenario")
        logger.info(f"[U+1F4CB] Headers without auth: {list(stripped_headers.keys())}")
        
        try:
            # Attempt WebSocket connection without authentication headers
            async with websockets.connect(
                self.test_websocket_url,
                additional_headers=stripped_headers,
                timeout=10.0
            ) as websocket:
                # If connection succeeds, this is a SECURITY ISSUE
                result["actual_outcome"] = "CONNECTION_SUCCEEDED"
                result["issue_detected"] = False
                result["error_details"] = "CRITICAL: WebSocket connected without auth headers!"
                
                logger.error(" FAIL:  SECURITY ISSUE: WebSocket connection succeeded without auth!")
                logger.error(" FAIL:  This indicates auth bypass is possible!")
                
                # Try to send a message to see if we can interact
                test_message = {
                    "type": "unauthorized_test",
                    "message": "This should not work without authentication",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                logger.error(" FAIL:  CRITICAL: Successfully sent message without auth!")
                
        except websockets.exceptions.ConnectionClosedError as e:
            result["actual_outcome"] = "CONNECTION_CLOSED"
            result["issue_detected"] = True
            result["error_details"] = f"Connection properly rejected: {e}"
            logger.info(" PASS:  GOOD: Connection rejected due to missing auth")
            
        except websockets.exceptions.InvalidHandshake as e:
            result["actual_outcome"] = "HANDSHAKE_FAILED"
            result["issue_detected"] = True
            result["error_details"] = f"Handshake failed (proper auth rejection): {e}"
            logger.info(" PASS:  GOOD: Handshake failed due to missing auth")
            
        except ConnectionRefusedError as e:
            result["actual_outcome"] = "SERVICE_UNAVAILABLE"
            result["issue_detected"] = None  # Cannot test due to service unavailable
            result["error_details"] = f"WebSocket service not available: {e}"
            logger.warning(" WARNING: [U+FE0F] Cannot test: WebSocket service unavailable")
            
        except Exception as e:
            result["actual_outcome"] = "UNEXPECTED_ERROR"
            result["issue_detected"] = None
            result["error_details"] = f"Unexpected error: {e}"
            logger.error(f" FAIL:  Unexpected error during test: {e}")
            
        return result
    
    async def validate_malformed_auth_headers_scenario(self) -> Dict[str, Any]:
        """
        Test scenario with malformed Authorization headers.
        
        This tests if the system properly rejects malformed tokens that might
        result from partial header stripping or corruption.
        """
        result = {
            "test_name": "malformed_auth_headers_scenario", 
            "description": "Tests malformed Authorization headers rejection",
            "expected_outcome": "CONNECTION_SHOULD_FAIL",
            "actual_outcome": None,
            "issue_detected": False,
            "error_details": None
        }
        
        # Test various malformed auth headers
        malformed_scenarios = [
            {"authorization": "Bearer "},  # Empty token
            {"authorization": "Bearer malformed"},  # Invalid JWT structure
            {"authorization": "Basic dGVzdA=="},  # Wrong auth type
            {"authorization": "token.without.bearer"},  # Missing Bearer prefix
        ]
        
        logger.info(" SEARCH:  Testing malformed Authorization header scenarios")
        
        for i, headers in enumerate(malformed_scenarios):
            logger.info(f"[U+1F4CB] Testing malformed scenario {i+1}: {headers['authorization']}")
            
            try:
                async with websockets.connect(
                    self.test_websocket_url,
                    additional_headers=headers,
                    timeout=5.0
                ) as websocket:
                    # Connection should NOT succeed with malformed auth
                    result["actual_outcome"] = f"SCENARIO_{i+1}_SUCCEEDED"
                    result["issue_detected"] = False
                    result["error_details"] = f"CRITICAL: Malformed auth accepted: {headers['authorization']}"
                    logger.error(f" FAIL:  SECURITY ISSUE: Malformed auth scenario {i+1} succeeded!")
                    break
                    
            except (websockets.exceptions.ConnectionClosedError, 
                   websockets.exceptions.InvalidHandshake) as e:
                result["actual_outcome"] = f"SCENARIO_{i+1}_REJECTED" 
                result["issue_detected"] = True
                result["error_details"] = f"Properly rejected malformed auth: {e}"
                logger.info(f" PASS:  GOOD: Malformed scenario {i+1} properly rejected")
                
            except ConnectionRefusedError:
                result["actual_outcome"] = "SERVICE_UNAVAILABLE"
                result["issue_detected"] = None
                logger.warning(" WARNING: [U+FE0F] Cannot test: WebSocket service unavailable")
                break
                
            except Exception as e:
                logger.error(f" FAIL:  Unexpected error in scenario {i+1}: {e}")
                continue
        
        return result
    
    async def validate_proper_auth_headers_scenario(self) -> Dict[str, Any]:
        """
        Test scenario with proper Authorization headers.
        
        This validates that legitimate auth headers work correctly,
        providing a baseline for comparison.
        """
        result = {
            "test_name": "proper_auth_headers_scenario",
            "description": "Tests proper Authorization headers acceptance", 
            "expected_outcome": "CONNECTION_SHOULD_SUCCEED",
            "actual_outcome": None,
            "issue_detected": False,
            "error_details": None
        }
        
        if not self.e2e_helper:
            result["actual_outcome"] = "HELPER_UNAVAILABLE"
            result["error_details"] = "E2E helper not available for auth token generation"
            return result
            
        try:
            # Create proper authentication headers
            auth_user = await self.e2e_helper.create_authenticated_user(
                email="test_header_validation@example.com",
                permissions=["read", "write", "websocket"]
            )
            
            proper_headers = self.e2e_helper.get_websocket_headers(auth_user.jwt_token)
            
            logger.info(" SEARCH:  Testing proper Authorization header scenario")
            logger.info(f"[U+1F4CB] Headers with auth: {list(proper_headers.keys())}")
            
            async with websockets.connect(
                self.test_websocket_url,
                additional_headers=proper_headers,
                timeout=10.0
            ) as websocket:
                result["actual_outcome"] = "CONNECTION_SUCCEEDED"
                result["issue_detected"] = True  # This is the expected good outcome
                result["error_details"] = "Proper auth headers accepted successfully"
                logger.info(" PASS:  GOOD: Proper auth headers accepted")
                
                # Send a test message to validate full functionality
                test_message = {
                    "type": "auth_validation_test",
                    "user_id": auth_user.user_id,
                    "message": "Testing with proper authentication",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(test_message))
                logger.info(" PASS:  Successfully sent authenticated message")
                
        except ConnectionRefusedError as e:
            result["actual_outcome"] = "SERVICE_UNAVAILABLE"
            result["issue_detected"] = None
            result["error_details"] = f"WebSocket service not available: {e}"
            logger.warning(" WARNING: [U+FE0F] Cannot test: WebSocket service unavailable")
            
        except Exception as e:
            result["actual_outcome"] = "UNEXPECTED_ERROR"
            result["issue_detected"] = False
            result["error_details"] = f"Unexpected error with proper auth: {e}"
            logger.error(f" FAIL:  Unexpected error with proper auth: {e}")
            
        return result
    
    async def run_all_validations(self) -> Dict[str, Any]:
        """
        Run all WebSocket header stripping validation scenarios.
        """
        logger.info("[U+1F680] Starting GitHub Issue #113 WebSocket Header Stripping Validation")
        logger.info(f"[U+1F310] Testing against WebSocket URL: {self.test_websocket_url}")
        
        validations = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "github_issue": "113", 
            "test_purpose": "Validate detection of GCP Load Balancer auth header stripping",
            "websocket_url": self.test_websocket_url,
            "results": {}
        }
        
        # Run validation scenarios
        scenarios = [
            ("missing_auth_headers", self.validate_missing_auth_headers_scenario),
            ("malformed_auth_headers", self.validate_malformed_auth_headers_scenario),
            ("proper_auth_headers", self.validate_proper_auth_headers_scenario)
        ]
        
        for scenario_name, scenario_func in scenarios:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running scenario: {scenario_name}")
            logger.info(f"{'='*60}")
            
            try:
                result = await scenario_func()
                validations["results"][scenario_name] = result
                
            except Exception as e:
                validations["results"][scenario_name] = {
                    "test_name": scenario_name,
                    "actual_outcome": "TEST_ERROR",
                    "issue_detected": False,
                    "error_details": f"Test execution error: {e}"
                }
                logger.error(f" FAIL:  Test execution error in {scenario_name}: {e}")
        
        # Analyze overall results
        validations["analysis"] = self._analyze_results(validations["results"])
        
        return validations
    
    def _analyze_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the validation results to determine overall test health."""
        analysis = {
            "total_scenarios": len(results),
            "scenarios_with_issues": 0,
            "scenarios_unavailable": 0,
            "critical_security_issues": [],
            "test_effectiveness": "unknown",
            "recommendations": []
        }
        
        for scenario_name, result in results.items():
            if result.get("issue_detected") is False:
                analysis["scenarios_with_issues"] += 1
                
                if "SUCCEEDED" in result.get("actual_outcome", ""):
                    analysis["critical_security_issues"].append({
                        "scenario": scenario_name,
                        "issue": result.get("error_details", "Unknown security issue")
                    })
                    
            elif result.get("issue_detected") is None:
                analysis["scenarios_unavailable"] += 1
                
        # Determine test effectiveness
        if analysis["scenarios_unavailable"] == analysis["total_scenarios"]:
            analysis["test_effectiveness"] = "cannot_evaluate_service_unavailable"
            analysis["recommendations"].append("Start WebSocket service for proper testing")
            
        elif len(analysis["critical_security_issues"]) > 0:
            analysis["test_effectiveness"] = "critical_security_issues_detected"
            analysis["recommendations"].append("URGENT: Fix authentication bypass vulnerabilities")
            
        elif analysis["scenarios_with_issues"] > 0:
            analysis["test_effectiveness"] = "some_issues_detected"
            analysis["recommendations"].append("Review test scenarios that are not working as expected")
            
        else:
            analysis["test_effectiveness"] = "tests_working_correctly"
            analysis["recommendations"].append("Tests properly detect and reject unauthorized connections")
            
        return analysis


async def main():
    """Main execution function."""
    validator = WebSocketHeaderStrippingValidator()
    
    try:
        results = await validator.run_all_validations()
        
        # Print summary
        print("\n" + "="*80)
        print("GITHUB ISSUE #113 WEBSOCKET HEADER STRIPPING VALIDATION SUMMARY")
        print("="*80)
        
        print(f"[U+1F4C5] Test Date: {results['timestamp']}")
        print(f"[U+1F310] WebSocket URL: {results['websocket_url']}")
        print(f" TARGET:  Purpose: {results['test_purpose']}")
        
        print(f"\n CHART:  SCENARIO RESULTS:")
        for scenario_name, result in results["results"].items():
            status_emoji = " PASS: " if result.get("issue_detected") else " FAIL: "
            if result.get("issue_detected") is None:
                status_emoji = " WARNING: [U+FE0F]"
                
            print(f"  {status_emoji} {scenario_name}: {result.get('actual_outcome', 'Unknown')}")
            if result.get("error_details"):
                print(f"      [U+1F4AC] {result['error_details']}")
        
        print(f"\n SEARCH:  ANALYSIS:")
        analysis = results["analysis"]
        print(f"  [U+1F4C8] Test Effectiveness: {analysis['test_effectiveness']}")
        print(f"   ALERT:  Critical Security Issues: {len(analysis['critical_security_issues'])}")
        print(f"   WARNING: [U+FE0F] Scenarios Unavailable: {analysis['scenarios_unavailable']}")
        
        if analysis["critical_security_issues"]:
            print(f"\n ALERT:  CRITICAL SECURITY ISSUES DETECTED:")
            for issue in analysis["critical_security_issues"]:
                print(f"   FAIL:  {issue['scenario']}: {issue['issue']}")
                
        print(f"\n IDEA:  RECOMMENDATIONS:")
        for rec in analysis["recommendations"]:
            print(f"  [U+1F527] {rec}")
            
        # Save results to file for documentation
        results_file = f"websocket_header_stripping_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        print(f"\n[U+1F4C4] Full results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f" FAIL:  Validation execution failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())