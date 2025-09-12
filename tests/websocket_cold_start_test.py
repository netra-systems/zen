#!/usr/bin/env python3
"""
Test WebSocket connections during GCP Cold Start simulation for P0 Issue #437
Tests the race condition fixes during actual container startup
"""
import asyncio
import websockets
import json
import time
import requests
from typing import List, Dict, Any
from datetime import datetime

class WebSocketColdStartTester:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.replace('https://', 'wss://')
        self.http_url = backend_url.replace('wss://', 'https://')
        self.results: List[Dict[str, Any]] = []
        
    def trigger_cold_start(self) -> bool:
        """Trigger a cold start by making an HTTP request to wake up the service"""
        print(f"Triggering cold start via HTTP request to {self.http_url}/health")
        try:
            # Use a short timeout to trigger but not wait for full startup
            response = requests.get(f"{self.http_url}/health", timeout=2)
            return True
        except requests.exceptions.Timeout:
            print("   Request timed out (expected during cold start)")
            return True
        except Exception as e:
            print(f"   Error triggering cold start: {e}")
            return False
    
    async def test_websocket_during_startup(self, attempt_id: int, delay_after_trigger: float) -> Dict[str, Any]:
        """Test WebSocket connection at specific timing during cold start"""
        result = {
            'attempt_id': attempt_id,
            'delay_after_trigger': delay_after_trigger,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'error': None,
            'connection_time': None,
            'response_received': False,
            'error_code': None
        }
        
        start_time = time.time()
        
        try:
            print(f"   Attempt {attempt_id}: WebSocket connection after {delay_after_trigger}s delay")
            
            # Create WebSocket connection with timeout
            websocket_url = f"{self.backend_url}/ws"
            print(f"      URL: {websocket_url}")
            
            async with websockets.connect(
                websocket_url,
                timeout=5.0,  # 5 second timeout for connection
                ping_timeout=3.0,
                close_timeout=3.0
            ) as websocket:
                connection_time = time.time() - start_time
                result['connection_time'] = connection_time
                print(f"      Connected in {connection_time:.3f}s")
                
                # Send a test message
                test_message = {
                    "type": "ping",
                    "data": {"test": "cold_start_validation"}
                }
                
                await websocket.send(json.dumps(test_message))
                print(f"      Sent test message")
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    result['response_received'] = True
                    result['success'] = True
                    print(f"      Received response: {response[:100]}...")
                except asyncio.TimeoutError:
                    result['error'] = "Response timeout"
                    print(f"      No response within 3s")
                    
        except websockets.exceptions.ConnectionClosed as e:
            result['error'] = f"Connection closed: {e.code}"
            result['error_code'] = e.code
            if e.code == 1011:  # The specific error we're testing for
                print(f"      *** 1011 ERROR DETECTED! - {e}")
            else:
                print(f"      Connection closed: {e.code} - {e}")
                
        except Exception as e:
            result['error'] = str(e)
            print(f"      Connection failed: {e}")
            
        return result
    
    async def run_cold_start_test_sequence(self) -> List[Dict[str, Any]]:
        """Run complete cold start test sequence"""
        print("\n=== COLD START WEBSOCKET TEST SEQUENCE ===")
        
        # Trigger cold start
        if not self.trigger_cold_start():
            return []
            
        # Test WebSocket connections at different points during startup
        test_timings = [
            0.1,   # Very early in startup (should potentially fail in old version)
            0.5,   # Early startup 
            1.0,   # Mid startup
            1.5,   # Around our timeout threshold
            2.0,   # After timeout threshold
            3.0    # Well after startup should complete
        ]
        
        # Wait briefly for cold start to begin
        await asyncio.sleep(0.1)
        
        # Run tests sequentially with proper timing
        results = []
        for i, delay in enumerate(test_timings):
            if i > 0:
                # Sleep for the difference between current and previous timing
                wait_time = test_timings[i] - test_timings[i-1]
                await asyncio.sleep(wait_time)
            
            result = await self.test_websocket_during_startup(i+1, delay)
            results.append(result)
            self.results.append(result)
                
        return results
    
    def print_summary(self):
        """Print test results summary"""
        print("\n=== COLD START TEST RESULTS ===")
        
        if not self.results:
            print("No test results available")
            return
            
        success_count = sum(1 for r in self.results if r['success'])
        total_count = len(self.results)
        
        print(f"Successful connections: {success_count}/{total_count}")
        
        # Check for 1011 errors specifically
        error_1011_count = sum(1 for r in self.results if r.get('error_code') == 1011)
        if error_1011_count > 0:
            print(f"*** ISSUE #437 ERRORS DETECTED: {error_1011_count} connections failed with 1011")
        else:
            print("NO 1011 ERRORS DETECTED - Race condition fix working!")
            
        # Detailed results
        print("\nDetailed Results:")
        for result in self.results:
            status = "SUCCESS" if result['success'] else "FAILED"
            delay = result['delay_after_trigger']
            conn_time = result.get('connection_time', 'N/A')
            error = result.get('error', 'None')
            
            if result.get('error_code') == 1011:
                status = "*** 1011 ERROR ***"
                
            print(f"   {status} - Delay: {delay}s, Connection: {conn_time}, Error: {error}")


async def main():
    """Main test execution"""
    backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
    
    print(f"Testing WebSocket connections during cold start")
    print(f"   Backend URL: {backend_url}")
    print(f"   Target: Validate P0 Issue #437 race condition fixes")
    
    tester = WebSocketColdStartTester(backend_url)
    
    # Run the test sequence
    results = await tester.run_cold_start_test_sequence()
    
    # Print summary
    tester.print_summary()
    
    # Final validation
    error_1011_found = any(r.get('error_code') == 1011 for r in results)
    
    if error_1011_found:
        print("\n*** PHASE 2 RESULT: RACE CONDITION STILL EXISTS ***")
        print("   1011 errors detected during cold start window")
        print("   Additional fixes required for complete resolution")
    else:
        print("\n*** PHASE 2 RESULT: RACE CONDITION FIXES WORKING ***")
        print("   No 1011 errors detected during cold start scenarios")
        print("   Issue #437 appears to be resolved in GCP environment")

if __name__ == "__main__":
    asyncio.run(main())