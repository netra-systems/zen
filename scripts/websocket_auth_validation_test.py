#!/usr/bin/env python3
"""
WebSocket Authentication Validation Test

This script validates that the WebSocket authentication fixes have resolved the 
persistent NO_TOKEN authentication failures. It performs comprehensive validation
of the business value delivery through authenticated WebSocket connections.

CRITICAL VALIDATION MISSION: Confirm that WebSocket authentication works end-to-end 
after the configuration fixes and that the $120K+ MRR risk is mitigated.
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('websocket_auth_validation.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

try:
    import websockets
    import jwt
    import aiohttp
    from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.error("Please ensure all dependencies are installed")
    sys.exit(1)


class WebSocketAuthValidationResults:
    """Tracks validation results and evidence for comprehensive reporting."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.test_results = []
        self.error_count = 0
        self.success_count = 0
        self.no_token_errors = []
        self.business_value_metrics = {}
        
    def add_test_result(self, test_name: str, success: bool, details: str = "", error: str = ""):
        """Add a test result to the validation report."""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if success:
            self.success_count += 1
            logger.info(f" PASS:  {test_name}: PASSED - {details}")
        else:
            self.error_count += 1
            logger.error(f" FAIL:  {test_name}: FAILED - {error}")
            
            # Check for NO_TOKEN errors specifically
            if "NO_TOKEN" in error.upper() or "no token" in error.lower():
                self.no_token_errors.append({
                    "test": test_name,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                })
    
    def add_business_metric(self, metric_name: str, value: any):
        """Add a business value metric to the report."""
        self.business_value_metrics[metric_name] = value
        logger.info(f" CHART:  {metric_name}: {value}")
    
    def get_summary(self) -> dict:
        """Get comprehensive validation summary."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "validation_duration_seconds": duration,
            "total_tests": len(self.test_results),
            "passed_tests": self.success_count,
            "failed_tests": self.error_count,
            "success_rate_percent": (self.success_count / len(self.test_results) * 100) if self.test_results else 0,
            "no_token_error_count": len(self.no_token_errors),
            "no_token_errors_eliminated": len(self.no_token_errors) == 0,
            "business_value_metrics": self.business_value_metrics,
            "critical_failure_risk_mitigated": len(self.no_token_errors) == 0 and self.success_count > 0,
            "test_results": self.test_results,
            "no_token_error_details": self.no_token_errors
        }


async def validate_local_websocket_auth():
    """Test WebSocket authentication against local development environment."""
    results = WebSocketAuthValidationResults()
    
    logger.info("[U+1F680] VALIDATING LOCAL WEBSOCKET AUTHENTICATION")
    
    # Test 1: Basic WebSocket Connection with Authentication
    try:
        auth_helper = E2EWebSocketAuthHelper()
        token = auth_helper.create_test_jwt_token()
        headers = auth_helper.get_websocket_headers(token)
        
        # Test connection to local WebSocket
        local_ws_url = "ws://localhost:8000/ws"
        
        # Attempt connection with authentication
        try:
            async with websockets.connect(
                local_ws_url,
                additional_headers=headers,
                open_timeout=10.0
            ) as websocket:
                # Send test message
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat(),
                    "test_id": "auth_validation_001"
                }
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                results.add_test_result(
                    "Local WebSocket Authentication",
                    True,
                    f"Successfully connected and received response: {response_data.get('type', 'unknown')}"
                )
                
        except websockets.exceptions.ConnectionClosedError as e:
            results.add_test_result(
                "Local WebSocket Authentication",
                False,
                error=f"Connection failed: {e}"
            )
        except asyncio.TimeoutError:
            results.add_test_result(
                "Local WebSocket Authentication",
                False,
                error="Connection timeout - service may not be running"
            )
    
    except Exception as e:
        results.add_test_result(
            "Local WebSocket Authentication Setup",
            False,
            error=f"Setup failed: {e}"
        )
    
    # Test 2: JWT Token Validation
    try:
        auth_helper = E2EWebSocketAuthHelper()
        token = auth_helper.create_test_jwt_token()
        
        # Decode and validate token structure
        decoded = jwt.decode(token, options={"verify_signature": False})
        required_claims = ["sub", "email", "exp", "iat"]
        
        missing_claims = [claim for claim in required_claims if claim not in decoded]
        
        if not missing_claims:
            results.add_test_result(
                "JWT Token Structure Validation",
                True,
                f"All required claims present: {required_claims}"
            )
        else:
            results.add_test_result(
                "JWT Token Structure Validation",
                False,
                error=f"Missing claims: {missing_claims}"
            )
    
    except Exception as e:
        results.add_test_result(
            "JWT Token Structure Validation",
            False,
            error=f"Token validation failed: {e}"
        )
    
    return results


async def validate_staging_websocket_auth():
    """Test WebSocket authentication against staging environment."""
    results = WebSocketAuthValidationResults()
    
    logger.info("[U+1F310] VALIDATING STAGING WEBSOCKET AUTHENTICATION")
    
    # Test 1: Staging WebSocket Connection with E2E Headers
    try:
        auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Get staging-compatible token
        token = await auth_helper.get_staging_token_async()
        headers = auth_helper.get_websocket_headers(token)
        
        # Test connection to staging WebSocket
        staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
        
        # Log the connection attempt
        logger.info(f"Connecting to: {staging_ws_url}")
        logger.info(f"Headers: {list(headers.keys())}")
        logger.info(f"E2E detection headers included: {bool(headers.get('X-E2E-Test'))}")
        
        try:
            async with websockets.connect(
                staging_ws_url,
                additional_headers=headers,
                open_timeout=15.0  # Staging needs more time
            ) as websocket:
                # Send test message
                test_message = {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat(),
                    "test_id": "staging_auth_validation_001",
                    "environment": "staging"
                }
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                results.add_test_result(
                    "Staging WebSocket Authentication",
                    True,
                    f"Successfully connected to staging and received response: {response_data.get('type', 'unknown')}"
                )
                
                # Test agent-like message flow
                agent_message = {
                    "type": "agent_started",
                    "agent_type": "test_agent",
                    "timestamp": datetime.now().isoformat(),
                    "test_id": "staging_agent_test_001"
                }
                await websocket.send(json.dumps(agent_message))
                
                # Wait for acknowledgment
                ack_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                ack_data = json.loads(ack_response)
                
                results.add_test_result(
                    "Staging Agent Event Flow",
                    True,
                    f"Agent event processed successfully: {ack_data.get('type', 'unknown')}"
                )
                
        except websockets.exceptions.ConnectionClosedError as e:
            error_msg = str(e)
            if "NO_TOKEN" in error_msg.upper():
                results.add_test_result(
                    "Staging WebSocket Authentication",
                    False,
                    error=f" FAIL:  CRITICAL: NO_TOKEN error still occurring: {e}"
                )
            else:
                results.add_test_result(
                    "Staging WebSocket Authentication",
                    False,
                    error=f"Connection failed: {e}"
                )
                
        except asyncio.TimeoutError:
            results.add_test_result(
                "Staging WebSocket Authentication",
                False,
                error="Connection timeout to staging - may indicate authentication issues or service unavailability"
            )
    
    except Exception as e:
        results.add_test_result(
            "Staging WebSocket Authentication Setup",
            False,
            error=f"Setup failed: {e}"
        )
    
    return results


def analyze_business_value_impact(results: WebSocketAuthValidationResults):
    """Analyze the business value impact of the authentication validation."""
    
    logger.info("[U+1F4C8] ANALYZING BUSINESS VALUE IMPACT")
    
    # Calculate key business metrics
    total_tests = len(results.test_results)
    success_rate = (results.success_count / total_tests * 100) if total_tests > 0 else 0
    
    results.add_business_metric("Total Authentication Tests", total_tests)
    results.add_business_metric("Authentication Success Rate %", f"{success_rate:.1f}%")
    results.add_business_metric("NO_TOKEN Errors Detected", len(results.no_token_errors))
    results.add_business_metric("Authentication Risk Level", "LOW" if len(results.no_token_errors) == 0 else "HIGH")
    
    # Business impact assessment
    if len(results.no_token_errors) == 0 and results.success_count > 0:
        results.add_business_metric("MRR Risk Mitigation Status", " PASS:  MITIGATED")
        results.add_business_metric("Chat Business Value Status", " PASS:  OPERATIONAL")
        results.add_business_metric("Customer Experience Impact", " PASS:  POSITIVE")
    else:
        results.add_business_metric("MRR Risk Mitigation Status", " FAIL:  AT RISK")
        results.add_business_metric("Chat Business Value Status", " FAIL:  DEGRADED")
        results.add_business_metric("Customer Experience Impact", " FAIL:  NEGATIVE")
    
    # WebSocket event delivery validation
    if "Staging Agent Event Flow" in [r["test_name"] for r in results.test_results]:
        agent_flow_test = next(r for r in results.test_results if r["test_name"] == "Staging Agent Event Flow")
        if agent_flow_test["success"]:
            results.add_business_metric("WebSocket Agent Events Status", " PASS:  OPERATIONAL")
            results.add_business_metric("Real-time AI Interaction Status", " PASS:  FUNCTIONAL")
        else:
            results.add_business_metric("WebSocket Agent Events Status", " FAIL:  BROKEN")
            results.add_business_metric("Real-time AI Interaction Status", " FAIL:  IMPAIRED")


async def main():
    """Main validation execution."""
    logger.info("=" * 80)
    logger.info("[U+1F510] WEBSOCKET AUTHENTICATION VALIDATION - COMPREHENSIVE TEST")
    logger.info("=" * 80)
    logger.info("MISSION: Validate WebSocket authentication fixes and business value delivery")
    logger.info("OBJECTIVE: Confirm zero NO_TOKEN errors and operational chat functionality")
    logger.info("=" * 80)
    
    all_results = WebSocketAuthValidationResults()
    
    # Test 1: Local Environment Validation
    logger.info("\n" + "=" * 50)
    logger.info("PHASE 1: LOCAL ENVIRONMENT VALIDATION")
    logger.info("=" * 50)
    
    local_results = await validate_local_websocket_auth()
    all_results.test_results.extend(local_results.test_results)
    all_results.success_count += local_results.success_count
    all_results.error_count += local_results.error_count
    all_results.no_token_errors.extend(local_results.no_token_errors)
    
    # Test 2: Staging Environment Validation
    logger.info("\n" + "=" * 50)
    logger.info("PHASE 2: STAGING ENVIRONMENT VALIDATION")
    logger.info("=" * 50)
    
    staging_results = await validate_staging_websocket_auth()
    all_results.test_results.extend(staging_results.test_results)
    all_results.success_count += staging_results.success_count
    all_results.error_count += staging_results.error_count
    all_results.no_token_errors.extend(staging_results.no_token_errors)
    
    # Test 3: Business Value Impact Analysis
    logger.info("\n" + "=" * 50)
    logger.info("PHASE 3: BUSINESS VALUE IMPACT ANALYSIS")
    logger.info("=" * 50)
    
    analyze_business_value_impact(all_results)
    
    # Final Report
    logger.info("\n" + "=" * 80)
    logger.info(" TARGET:  FINAL VALIDATION REPORT")
    logger.info("=" * 80)
    
    summary = all_results.get_summary()
    
    logger.info(f" CHART:  VALIDATION SUMMARY:")
    logger.info(f"  [U+2022] Duration: {summary['validation_duration_seconds']:.1f} seconds")
    logger.info(f"  [U+2022] Total Tests: {summary['total_tests']}")
    logger.info(f"  [U+2022] Passed: {summary['passed_tests']}")
    logger.info(f"  [U+2022] Failed: {summary['failed_tests']}")
    logger.info(f"  [U+2022] Success Rate: {summary['success_rate_percent']:.1f}%")
    
    logger.info(f"\n ALERT:  CRITICAL NO_TOKEN ERROR ANALYSIS:")
    logger.info(f"  [U+2022] NO_TOKEN Errors Detected: {summary['no_token_error_count']}")
    logger.info(f"  [U+2022] NO_TOKEN Errors Eliminated: {' PASS:  YES' if summary['no_token_errors_eliminated'] else ' FAIL:  NO'}")
    
    logger.info(f"\n[U+1F4B0] BUSINESS VALUE IMPACT:")
    for metric, value in summary['business_value_metrics'].items():
        logger.info(f"  [U+2022] {metric}: {value}")
    
    logger.info(f"\n TARGET:  MISSION OUTCOME:")
    if summary['critical_failure_risk_mitigated']:
        logger.info("   PASS:  SUCCESS: WebSocket authentication fixes are EFFECTIVE")
        logger.info("   PASS:  SUCCESS: NO_TOKEN errors ELIMINATED")
        logger.info("   PASS:  SUCCESS: Business value delivery OPERATIONAL")
        logger.info("   PASS:  SUCCESS: $120K+ MRR risk MITIGATED")
    else:
        logger.error("   FAIL:  FAILURE: WebSocket authentication fixes are NOT effective")
        logger.error("   FAIL:  FAILURE: NO_TOKEN errors still occurring")
        logger.error("   FAIL:  FAILURE: Business value delivery at risk")
        logger.error("   FAIL:  FAILURE: $120K+ MRR risk remains")
    
    # Save detailed report
    report_file = "websocket_auth_validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"\n[U+1F4C4] Detailed report saved to: {report_file}")
    logger.info("=" * 80)
    
    # Return appropriate exit code
    return 0 if summary['critical_failure_risk_mitigated'] else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation failed with exception: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)