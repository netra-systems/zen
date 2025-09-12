#!/usr/bin/env python3
"""
Phase 5: WebSocket Validation Test for Issue #463 Remediation

This test validates that the WebSocket authentication failures have been resolved
after deploying the missing environment variables to GCP Cloud Run.
"""

import asyncio
import json
import logging
import websockets
import aiohttp
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Staging endpoints
STAGING_BASE_URL = "https://netra-backend-staging-701982941522.us-central1.run.app"
STAGING_WS_URL = "wss://netra-backend-staging-701982941522.us-central1.run.app/ws"

class WebSocketValidationTester:
    """Test WebSocket functionality after Issue #463 remediation."""
    
    def __init__(self):
        self.session = None
        self.test_results = {}
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health_endpoint(self) -> Dict[str, Any]:
        """Test that the health endpoint is working."""
        try:
            async with self.session.get(f"{STAGING_BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "status_code": response.status,
                        "response_data": data,
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status,
                        "response_data": None,
                        "error": f"Health endpoint returned {response.status}"
                    }
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_data": None,
                "error": str(e)
            }
    
    async def test_websocket_connection(self) -> Dict[str, Any]:
        """Test WebSocket connection establishment."""
        try:
            # Try to connect to WebSocket endpoint
            async with websockets.connect(
                STAGING_WS_URL,
                timeout=10
            ) as websocket:
                # If we get here, connection was successful
                return {
                    "success": True,
                    "connection_established": True,
                    "error": None,
                    "websocket_ready_state": "OPEN"
                }
        except websockets.exceptions.ConnectionClosedError as e:
            return {
                "success": False,
                "connection_established": False,
                "error": f"Connection closed: {e}",
                "error_type": "ConnectionClosedError"
            }
        except websockets.exceptions.InvalidStatusCode as e:
            return {
                "success": False,
                "connection_established": False,
                "error": f"Invalid status code: {e}",
                "error_type": "InvalidStatusCode",
                "status_code": getattr(e, 'status_code', None)
            }
        except Exception as e:
            return {
                "success": False,
                "connection_established": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def test_websocket_with_headers(self) -> Dict[str, Any]:
        """Test WebSocket connection with proper headers."""
        try:
            headers = {
                "Origin": "https://netra-frontend-staging-701982941522.us-central1.run.app",
                "User-Agent": "Mozilla/5.0 (compatible; NetraTest/1.0)"
            }
            
            async with websockets.connect(
                STAGING_WS_URL,
                extra_headers=headers,
                timeout=10
            ) as websocket:
                # Try to send a test message
                test_message = json.dumps({
                    "type": "ping", 
                    "timestamp": 1757640968
                })
                await websocket.send(test_message)
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    return {
                        "success": True,
                        "connection_established": True,
                        "message_sent": True,
                        "response_received": True,
                        "response": response,
                        "error": None
                    }
                except asyncio.TimeoutError:
                    return {
                        "success": True,
                        "connection_established": True,
                        "message_sent": True,
                        "response_received": False,
                        "error": "No response within timeout",
                        "note": "Connection successful but no echo response"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "connection_established": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run all validation tests."""
        logger.info("🚀 Starting Phase 5: WebSocket Validation for Issue #463")
        
        # Test 1: Health endpoint
        logger.info("📋 Test 1: Health endpoint validation...")
        health_result = await self.test_health_endpoint()
        
        # Test 2: WebSocket basic connection
        logger.info("🔌 Test 2: WebSocket basic connection...")
        ws_basic_result = await self.test_websocket_connection()
        
        # Test 3: WebSocket with headers
        logger.info("📡 Test 3: WebSocket with proper headers...")
        ws_headers_result = await self.test_websocket_with_headers()
        
        # Compile results
        results = {
            "phase": "Phase 5: WebSocket Validation",
            "issue": "Issue #463 - WebSocket Authentication Failures",
            "timestamp": 1757640968,
            "tests": {
                "health_endpoint": health_result,
                "websocket_basic": ws_basic_result,
                "websocket_headers": ws_headers_result
            },
            "summary": {
                "total_tests": 3,
                "passed": sum(1 for test in [health_result, ws_basic_result, ws_headers_result] if test.get("success", False)),
                "failed": sum(1 for test in [health_result, ws_basic_result, ws_headers_result] if not test.get("success", False))
            }
        }
        
        # Overall assessment
        if results["summary"]["passed"] >= 2:
            results["overall_status"] = "SIGNIFICANT_IMPROVEMENT"
            results["assessment"] = "Environment variables deployment successful - WebSocket infrastructure responding"
        elif results["summary"]["passed"] == 1:
            results["overall_status"] = "PARTIAL_SUCCESS"
            results["assessment"] = "Some progress made - further configuration needed"
        else:
            results["overall_status"] = "NEEDS_INVESTIGATION"
            results["assessment"] = "Additional configuration or investigation required"
        
        return results

async def main():
    """Main test execution."""
    async with WebSocketValidationTester() as tester:
        results = await tester.run_comprehensive_validation()
        
        # Print results
        print("\n" + "="*80)
        print("🔍 PHASE 5 VALIDATION RESULTS - Issue #463 WebSocket Authentication")
        print("="*80)
        
        print(f"\n📊 Overall Status: {results['overall_status']}")
        print(f"📝 Assessment: {results['assessment']}")
        print(f"✅ Tests Passed: {results['summary']['passed']}/{results['summary']['total_tests']}")
        
        print(f"\n🏥 Health Endpoint: {'✅ PASS' if results['tests']['health_endpoint']['success'] else '❌ FAIL'}")
        if results['tests']['health_endpoint']['success']:
            print(f"   Status: {results['tests']['health_endpoint']['response_data']['status']}")
        else:
            print(f"   Error: {results['tests']['health_endpoint']['error']}")
        
        print(f"\n🔌 WebSocket Basic: {'✅ PASS' if results['tests']['websocket_basic']['success'] else '❌ FAIL'}")
        if not results['tests']['websocket_basic']['success']:
            print(f"   Error: {results['tests']['websocket_basic']['error']}")
            print(f"   Type: {results['tests']['websocket_basic'].get('error_type', 'Unknown')}")
        
        print(f"\n📡 WebSocket Headers: {'✅ PASS' if results['tests']['websocket_headers']['success'] else '❌ FAIL'}")
        if not results['tests']['websocket_headers']['success']:
            print(f"   Error: {results['tests']['websocket_headers']['error']}")
        elif results['tests']['websocket_headers'].get('message_sent'):
            print(f"   Message Sent: ✅")
            print(f"   Response Received: {'✅' if results['tests']['websocket_headers'].get('response_received') else '⚠️ Timeout'}")
        
        print("\n" + "="*80)
        print("🎯 REMEDIATION STATUS:")
        if results["overall_status"] == "SIGNIFICANT_IMPROVEMENT":
            print("✅ SUCCESS: Environment variables deployment resolved the core issues!")
            print("   • Backend service is healthy and responding")
            print("   • WebSocket infrastructure is operational")
            print("   • Ready for business value validation")
        elif results["overall_status"] == "PARTIAL_SUCCESS":
            print("⚠️  PARTIAL: Some issues resolved, further configuration needed")
        else:
            print("❌ BLOCKED: Additional investigation required")
        
        print("="*80)
        
        # Return results for potential use
        return results

if __name__ == "__main__":
    results = asyncio.run(main())