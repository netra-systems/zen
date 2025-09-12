#!/usr/bin/env python3
"""
WebSocket HTTP 500 Error Fix Validation Test
Comprehensive test to verify WebSocket connections work properly after fixes.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosedError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketFixValidator:
    """Validates WebSocket fixes for HTTP 500 errors."""
    
    def __init__(self, base_url: str = "localhost:8000", use_ssl: bool = False):
        self.base_url = base_url
        self.use_ssl = use_ssl
        self.protocol = "wss" if use_ssl else "ws"
        self.http_protocol = "https" if use_ssl else "http"
        self.results: List[Dict] = []
        
    async def run_comprehensive_test(self) -> Dict:
        """Run comprehensive WebSocket validation tests."""
        logger.info("[U+1F680] Starting WebSocket HTTP 500 Fix Validation")
        logger.info(f"Target: {self.base_url} (SSL: {self.use_ssl})")
        
        test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "target": self.base_url,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }
        
        # Test 1: Basic health check
        await self._test_health_endpoint(test_results)
        
        # Test 2: WebSocket config endpoint
        await self._test_websocket_config(test_results)
        
        # Test 3: Basic WebSocket connection (test endpoint, no auth)
        await self._test_basic_websocket_connection(test_results)
        
        # Test 4: WebSocket connection with mock JWT (main endpoint)
        await self._test_authenticated_websocket_connection(test_results)
        
        # Test 5: WebSocket message handling
        await self._test_websocket_message_flow(test_results)
        
        # Test 6: WebSocket error handling
        await self._test_websocket_error_handling(test_results)
        
        # Test 7: Concurrent connections
        await self._test_concurrent_websocket_connections(test_results)
        
        # Calculate final results
        test_results["success_rate"] = (
            test_results["passed_tests"] / max(1, test_results["total_tests"]) * 100
        )
        
        self._print_test_summary(test_results)
        return test_results
    
    async def _test_health_endpoint(self, results: Dict) -> None:
        """Test health endpoint availability."""
        test_name = "Health Endpoint"
        results["total_tests"] += 1
        
        try:
            url = f"{self.http_protocol}://{self.base_url}/ws/health"
            timeout = aiohttp.ClientTimeout(total=10.0)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("status", "unknown")
                        
                        results["passed_tests"] += 1
                        results["test_details"].append({
                            "test": test_name,
                            "status": "PASSED",
                            "details": f"Health status: {status}",
                            "response_time": response.headers.get("X-Response-Time", "N/A")
                        })
                        logger.info(f" PASS:  {test_name}: PASSED - Status: {status}")
                    else:
                        results["failed_tests"] += 1
                        results["test_details"].append({
                            "test": test_name,
                            "status": "FAILED",
                            "details": f"HTTP {response.status}: {await response.text()}"
                        })
                        logger.error(f" FAIL:  {test_name}: FAILED - HTTP {response.status}")
                        
        except Exception as e:
            results["failed_tests"] += 1
            results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "details": str(e)
            })
            logger.error(f" FAIL:  {test_name}: ERROR - {e}")
    
    async def _test_websocket_config(self, results: Dict) -> None:
        """Test WebSocket configuration endpoint."""
        test_name = "WebSocket Config"
        results["total_tests"] += 1
        
        try:
            url = f"{self.http_protocol}://{self.base_url}/ws/config"
            timeout = aiohttp.ClientTimeout(total=10.0)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        websocket_config = data.get("websocket", {})
                        endpoint = websocket_config.get("endpoint", "")
                        
                        results["passed_tests"] += 1
                        results["test_details"].append({
                            "test": test_name,
                            "status": "PASSED",
                            "details": f"Endpoint: {endpoint}, Features: {len(websocket_config.get('features', {}))}"
                        })
                        logger.info(f" PASS:  {test_name}: PASSED - Endpoint: {endpoint}")
                    else:
                        results["failed_tests"] += 1
                        results["test_details"].append({
                            "test": test_name,
                            "status": "FAILED",
                            "details": f"HTTP {response.status}"
                        })
                        logger.error(f" FAIL:  {test_name}: FAILED - HTTP {response.status}")
                        
        except Exception as e:
            results["failed_tests"] += 1
            results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "details": str(e)
            })
            logger.error(f" FAIL:  {test_name}: ERROR - {e}")
    
    async def _test_basic_websocket_connection(self, results: Dict) -> None:
        """Test basic WebSocket connection to test endpoint (no auth required)."""
        test_name = "Basic WebSocket Connection"
        results["total_tests"] += 1
        
        try:
            uri = f"{self.protocol}://{self.base_url}/ws/test"
            
            async with websockets.connect(uri, timeout=10.0) as websocket:
                # Send ping
                ping_msg = {"type": "ping"}
                await websocket.send(json.dumps(ping_msg))
                
                # Receive response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "pong":
                    results["passed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "PASSED",
                        "details": "Ping/Pong successful"
                    })
                    logger.info(f" PASS:  {test_name}: PASSED - Ping/Pong successful")
                else:
                    results["failed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "FAILED",
                        "details": f"Unexpected response: {response_data}"
                    })
                    logger.error(f" FAIL:  {test_name}: FAILED - Unexpected response")
                    
        except Exception as e:
            results["failed_tests"] += 1
            results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "details": str(e)
            })
            logger.error(f" FAIL:  {test_name}: ERROR - {e}")
    
    async def _test_authenticated_websocket_connection(self, results: Dict) -> None:
        """Test WebSocket connection with authentication to main endpoint."""
        test_name = "Authenticated WebSocket Connection"
        results["total_tests"] += 1
        
        try:
            # First get a JWT token (if auth service is available)
            jwt_token = await self._get_test_jwt_token()
            
            if not jwt_token:
                logger.warning(f" WARNING: [U+FE0F] {test_name}: SKIPPED - No JWT token available")
                results["test_details"].append({
                    "test": test_name,
                    "status": "SKIPPED",
                    "details": "JWT token not available"
                })
                return
            
            uri = f"{self.protocol}://{self.base_url}/ws"
            headers = {"Authorization": f"Bearer {jwt_token}"}
            
            async with websockets.connect(uri, extra_headers=headers, timeout=10.0) as websocket:
                # Wait for welcome message
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data.get("event") == "connection_established":
                    results["passed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "PASSED", 
                        "details": f"Connection ID: {welcome_data.get('connection_id', 'N/A')}"
                    })
                    logger.info(f" PASS:  {test_name}: PASSED - Connection established")
                else:
                    results["failed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "FAILED",
                        "details": f"No welcome message: {welcome_data}"
                    })
                    logger.error(f" FAIL:  {test_name}: FAILED - No welcome message")
                    
        except websockets.exceptions.InvalidStatus as e:
            if e.status_code == 500:
                results["failed_tests"] += 1
                results["test_details"].append({
                    "test": test_name,
                    "status": "FAILED",
                    "details": f"HTTP 500 ERROR - The fix did not work! {e}"
                })
                logger.error(f" FAIL:  {test_name}: FAILED - HTTP 500 ERROR (Fix unsuccessful)")
            else:
                results["failed_tests"] += 1
                results["test_details"].append({
                    "test": test_name,
                    "status": "FAILED", 
                    "details": f"HTTP {e.status_code}: {e}"
                })
                logger.error(f" FAIL:  {test_name}: FAILED - HTTP {e.status_code}")
        except Exception as e:
            results["failed_tests"] += 1
            results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "details": str(e)
            })
            logger.error(f" FAIL:  {test_name}: ERROR - {e}")
    
    async def _test_websocket_message_flow(self, results: Dict) -> None:
        """Test WebSocket message handling flow."""
        test_name = "WebSocket Message Flow"
        results["total_tests"] += 1
        
        try:
            uri = f"{self.protocol}://{self.base_url}/ws/test"
            
            async with websockets.connect(uri, timeout=10.0) as websocket:
                # Test echo functionality
                test_message = {
                    "type": "echo",
                    "content": "Test message for WebSocket 500 fix validation"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Receive echo response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "echo_response":
                    results["passed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "PASSED",
                        "details": "Echo message flow successful"
                    })
                    logger.info(f" PASS:  {test_name}: PASSED - Echo flow successful")
                else:
                    results["failed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "FAILED",
                        "details": f"Unexpected response: {response_data}"
                    })
                    logger.error(f" FAIL:  {test_name}: FAILED - Unexpected response")
                    
        except Exception as e:
            results["failed_tests"] += 1
            results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "details": str(e)
            })
            logger.error(f" FAIL:  {test_name}: ERROR - {e}")
    
    async def _test_websocket_error_handling(self, results: Dict) -> None:
        """Test WebSocket error handling."""
        test_name = "WebSocket Error Handling"
        results["total_tests"] += 1
        
        try:
            uri = f"{self.protocol}://{self.base_url}/ws/test"
            
            async with websockets.connect(uri, timeout=10.0) as websocket:
                # Send invalid JSON
                await websocket.send("invalid json {")
                
                # Should receive error response
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "error":
                    results["passed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "PASSED",
                        "details": "Error handling working correctly"
                    })
                    logger.info(f" PASS:  {test_name}: PASSED - Error handling works")
                else:
                    results["failed_tests"] += 1
                    results["test_details"].append({
                        "test": test_name,
                        "status": "FAILED",
                        "details": f"No error response: {response_data}"
                    })
                    logger.error(f" FAIL:  {test_name}: FAILED - No error response")
                    
        except Exception as e:
            results["failed_tests"] += 1
            results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "details": str(e)
            })
            logger.error(f" FAIL:  {test_name}: ERROR - {e}")
    
    async def _test_concurrent_websocket_connections(self, results: Dict) -> None:
        """Test multiple concurrent WebSocket connections."""
        test_name = "Concurrent WebSocket Connections"
        results["total_tests"] += 1
        
        try:
            uri = f"{self.protocol}://{self.base_url}/ws/test"
            concurrent_connections = 3
            
            async def single_connection_test(conn_id: int):
                async with websockets.connect(uri, timeout=10.0) as websocket:
                    # Send ping
                    ping_msg = {"type": "ping", "connection_id": conn_id}
                    await websocket.send(json.dumps(ping_msg))
                    
                    # Receive pong
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    return response_data.get("type") == "pong"
            
            # Run concurrent connections
            tasks = [single_connection_test(i) for i in range(concurrent_connections)]
            connection_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_connections = sum(
                1 for result in connection_results 
                if result is True
            )
            
            if successful_connections == concurrent_connections:
                results["passed_tests"] += 1
                results["test_details"].append({
                    "test": test_name,
                    "status": "PASSED",
                    "details": f"{successful_connections}/{concurrent_connections} connections successful"
                })
                logger.info(f" PASS:  {test_name}: PASSED - All {concurrent_connections} connections successful")
            else:
                results["failed_tests"] += 1
                results["test_details"].append({
                    "test": test_name,
                    "status": "FAILED",
                    "details": f"Only {successful_connections}/{concurrent_connections} connections successful"
                })
                logger.error(f" FAIL:  {test_name}: FAILED - Only {successful_connections}/{concurrent_connections} successful")
                
        except Exception as e:
            results["failed_tests"] += 1
            results["test_details"].append({
                "test": test_name,
                "status": "ERROR", 
                "details": str(e)
            })
            logger.error(f" FAIL:  {test_name}: ERROR - {e}")
    
    async def _get_test_jwt_token(self) -> Optional[str]:
        """Get a test JWT token for authentication."""
        try:
            # Try to get token from health endpoint or use a mock token for testing
            # In a real scenario, this would call the auth service
            
            # For testing purposes, use a mock JWT token structure
            # This won't validate but will test the WebSocket connection attempt
            import base64
            
            mock_payload = {
                "sub": "test_user_12345",
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,
                "roles": ["user"]
            }
            
            # Create a mock JWT (this is just for testing connection, not real auth)
            payload_b64 = base64.urlsafe_b64encode(json.dumps(mock_payload).encode()).decode()
            mock_jwt = f"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.{payload_b64}.mock_signature"
            
            return mock_jwt
            
        except Exception as e:
            logger.warning(f"Could not generate test JWT token: {e}")
            return None
    
    def _print_test_summary(self, results: Dict) -> None:
        """Print comprehensive test summary."""
        print("\n" + "="*80)
        print("[U+1F52C] WEBSOCKET HTTP 500 FIX VALIDATION RESULTS")
        print("="*80)
        
        print(f" CHART:  Test Summary:")
        print(f"   Total Tests:    {results['total_tests']}")
        print(f"   Passed:         {results['passed_tests']}  PASS: ")
        print(f"   Failed:         {results['failed_tests']}  FAIL: ") 
        print(f"   Success Rate:   {results['success_rate']:.1f}%")
        
        if results['success_rate'] >= 85:
            print(f"   Overall Status:  CELEBRATION:  EXCELLENT - WebSocket fixes working well!")
        elif results['success_rate'] >= 70:
            print(f"   Overall Status:  PASS:  GOOD - Minor issues remain")
        else:
            print(f"   Overall Status:  FAIL:  POOR - Significant issues remain")
        
        print(f"\n[U+1F4CB] Test Details:")
        for test_detail in results['test_details']:
            status_emoji = {
                'PASSED': ' PASS: ',
                'FAILED': ' FAIL: ', 
                'ERROR': '[U+1F4A5]',
                'SKIPPED': '[U+23ED][U+FE0F]'
            }.get(test_detail['status'], '[U+2753]')
            
            print(f"   {status_emoji} {test_detail['test']}: {test_detail['status']}")
            print(f"      {test_detail['details']}")
        
        print("\n" + "="*80)

async def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='WebSocket HTTP 500 Fix Validator')
    parser.add_argument('--url', default='localhost:8000', help='Target URL (default: localhost:8000)')
    parser.add_argument('--ssl', action='store_true', help='Use SSL/TLS')
    parser.add_argument('--staging', action='store_true', help='Test staging environment')
    
    args = parser.parse_args()
    
    if args.staging:
        base_url = 'api.staging.netrasystems.ai'
        use_ssl = True
    else:
        base_url = args.url
        use_ssl = args.ssl
    
    validator = WebSocketFixValidator(base_url, use_ssl)
    results = await validator.run_comprehensive_test()
    
    # Return exit code based on results
    if results['success_rate'] >= 70:
        print("\n CELEBRATION:  WebSocket fixes are working! Staging tests should now pass.")
        sys.exit(0)
    else:
        print("\n FAIL:  WebSocket fixes need more work. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())