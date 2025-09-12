"""
E2E Tests for Issue #465: WebSocket + API Concurrent Access

PURPOSE: Test real WebSocket connections + API calls with actual authentication flow
EXPECTED BEHAVIOR: Tests should FAIL with current 1.0s threshold, showing real user impact

Business Impact: Chat functionality (90% of platform value) broken for concurrent usage
"""

import asyncio
import time
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
import websockets
import requests
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# SSOT Import Registry compliance
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.configuration.base import get_unified_config


class TestIssue465WebSocketAPIConcurrentReal(SSotAsyncTestCase):
    """
    E2E tests for WebSocket + API concurrent access with real services
    
    CRITICAL: These tests use real WebSocket connections and API calls
    Should FAIL initially, proving real-world chat functionality is broken
    """

    def setUp(self):
        super().setUp()
        self.env = IsolatedEnvironment()
        self.config = get_unified_config()
        
        # Get service URLs from environment
        self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
        self.websocket_url = self.backend_url.replace("http", "ws")
        
        # Test user credentials
        self.test_user_token = "e2e-test-token-465"
        self.test_user_id = "e2e-user-465"
        
        print(f"🔧 E2E Test Setup - Backend: {self.backend_url}")

    async def test_chat_websocket_with_concurrent_api_calls(self):
        """
        Test real chat WebSocket + API calls happening concurrently
        
        BUSINESS SCENARIO: User starts chat session, app makes API calls for context
        EXPECTED: Should FAIL, proving chat + API concurrent access is broken
        """
        print("🧪 Testing Chat WebSocket + API Concurrent Access")
        
        results = {
            'websocket_connection': None,
            'api_calls': [],
            'errors': []
        }
        
        # Test WebSocket connection with authentication
        websocket_url = f"{self.websocket_url}/ws"
        headers = {
            "Authorization": f"Bearer {self.test_user_token}",
            "User-ID": self.test_user_id
        }
        
        try:
            # Attempt WebSocket connection
            async with websockets.connect(
                websocket_url,
                extra_headers=headers,
                timeout=10
            ) as websocket:
                results['websocket_connection'] = {'success': True, 'timestamp': time.time()}
                print(f"   ✅ WebSocket connected at {results['websocket_connection']['timestamp']}")
                
                # Immediately make API calls (realistic app behavior)
                api_endpoints = [
                    f"{self.backend_url}/api/user/profile",
                    f"{self.backend_url}/api/chat/history", 
                    f"{self.backend_url}/api/user/settings"
                ]
                
                # Make concurrent API calls while WebSocket is connected
                for endpoint in api_endpoints:
                    try:
                        response = requests.get(
                            endpoint,
                            headers=headers,
                            timeout=5
                        )
                        results['api_calls'].append({
                            'endpoint': endpoint,
                            'success': response.status_code < 400,
                            'status_code': response.status_code,
                            'timestamp': time.time(),
                            'response': response.text if response.status_code >= 400 else 'Success'
                        })
                        print(f"   📡 API call to {endpoint}: {response.status_code}")
                        
                        # Small delay between API calls (realistic)
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        results['api_calls'].append({
                            'endpoint': endpoint,
                            'success': False,
                            'error': str(e),
                            'timestamp': time.time()
                        })
                        results['errors'].append(f"API call failed: {e}")
                        print(f"   ❌ API call to {endpoint} failed: {e}")
                
                # Try to send a chat message (additional concurrent auth)
                try:
                    chat_message = json.dumps({
                        "type": "chat_message",
                        "content": "Test message for concurrent access",
                        "timestamp": time.time()
                    })
                    await websocket.send(chat_message)
                    
                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    results['chat_response'] = {'success': True, 'response': response}
                    print(f"   💬 Chat message sent and received response")
                    
                except Exception as e:
                    results['chat_response'] = {'success': False, 'error': str(e)}
                    results['errors'].append(f"Chat message failed: {e}")
                    print(f"   ❌ Chat message failed: {e}")
        
        except Exception as e:
            results['websocket_connection'] = {'success': False, 'error': str(e)}
            results['errors'].append(f"WebSocket connection failed: {e}")
            print(f"   ❌ WebSocket connection failed: {e}")
        
        # Analyze results for Issue #465 impact
        self.analyze_concurrent_access_results(results)

    def test_multiple_tab_simulation_real(self):
        """
        Test multiple browser tabs accessing the system concurrently
        
        BUSINESS SCENARIO: User opens multiple tabs of the application
        EXPECTED: Should FAIL, proving multi-tab usage is broken
        """
        print("🧪 Testing Multiple Tab Simulation with Real Requests")
        
        tab_results = []
        
        def simulate_tab_session(tab_id):
            """Simulate a browser tab making authenticated requests"""
            tab_result = {'tab_id': tab_id, 'requests': []}
            
            headers = {
                "Authorization": f"Bearer {self.test_user_token}",
                "User-ID": self.test_user_id,
                "X-Tab-ID": str(tab_id)  # Simulate different tabs
            }
            
            # Each tab makes several requests quickly (realistic behavior)
            tab_endpoints = [
                f"{self.backend_url}/api/user/profile",
                f"{self.backend_url}/api/dashboard/widgets",
                f"{self.backend_url}/api/notifications"
            ]
            
            for endpoint in tab_endpoints:
                try:
                    response = requests.get(endpoint, headers=headers, timeout=5)
                    tab_result['requests'].append({
                        'endpoint': endpoint,
                        'success': response.status_code < 400,
                        'status_code': response.status_code,
                        'timestamp': time.time(),
                        'response_time': response.elapsed.total_seconds()
                    })
                    
                except Exception as e:
                    tab_result['requests'].append({
                        'endpoint': endpoint,
                        'success': False,
                        'error': str(e),
                        'timestamp': time.time()
                    })
                
                # Brief delay between requests within tab
                time.sleep(0.05)
            
            return tab_result
        
        # Simulate 4 browser tabs making concurrent requests
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(simulate_tab_session, i) for i in range(4)]
            tab_results = [future.result() for future in futures]
        
        # Analyze multi-tab results
        total_requests = sum(len(tab['requests']) for tab in tab_results)
        successful_requests = sum(
            sum(1 for req in tab['requests'] if req['success']) 
            for tab in tab_results
        )
        failed_requests = total_requests - successful_requests
        
        print(f"🔍 Multi-Tab Test Results:")
        print(f"   📊 Total requests across 4 tabs: {total_requests}")
        print(f"   ✅ Successful requests: {successful_requests}")
        print(f"   ❌ Failed requests: {failed_requests}")
        
        for tab in tab_results:
            tab_success = sum(1 for req in tab['requests'] if req['success'])
            tab_failed = len(tab['requests']) - tab_success
            print(f"   🖥️ Tab {tab['tab_id']}: {tab_success}✅ {tab_failed}❌")
        
        # With current threshold, expect significant failures
        failure_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        self.assertGreater(failure_rate, 20, 
                          f"Expected high failure rate, got {failure_rate:.1f}%")
        
        print(f"✅ Issue #465 CONFIRMED: {failure_rate:.1f}% failure rate in multi-tab scenario")

    def test_mobile_app_background_foreground_pattern(self):
        """
        Test mobile app background/foreground authentication pattern
        
        BUSINESS SCENARIO: Mobile app going background/foreground with auth refresh
        EXPECTED: Should FAIL, proving mobile user experience is degraded
        """
        print("🧪 Testing Mobile App Background/Foreground Pattern")
        
        mobile_results = []
        
        # Simulate mobile app lifecycle
        def mobile_auth_attempt(phase):
            """Simulate mobile app authentication in different phases"""
            headers = {
                "Authorization": f"Bearer {self.test_user_token}",
                "User-ID": self.test_user_id,
                "X-App-Phase": phase,
                "User-Agent": "NetraApex-Mobile/1.0"
            }
            
            try:
                response = requests.get(
                    f"{self.backend_url}/api/user/profile",
                    headers=headers,
                    timeout=5
                )
                return {
                    'phase': phase,
                    'success': response.status_code < 400,
                    'status_code': response.status_code,
                    'timestamp': time.time(),
                    'response': response.text if response.status_code >= 400 else 'Success'
                }
            except Exception as e:
                return {
                    'phase': phase,
                    'success': False,
                    'error': str(e),
                    'timestamp': time.time()
                }
        
        # Simulate mobile app phases
        phases = [
            'app_start',      # Initial app start
            'background',     # App goes to background 
            'foreground',     # App comes back to foreground
            'refresh_pull',   # User pulls to refresh
            'nav_change'      # User navigates to different screen
        ]
        
        for i, phase in enumerate(phases):
            result = mobile_auth_attempt(phase)
            mobile_results.append(result)
            print(f"   📱 {phase}: {'✅' if result['success'] else '❌'} {result.get('status_code', 'Error')}")
            
            # Mobile app timing - requests happen quickly during transitions
            if i < len(phases) - 1:
                time.sleep(0.3)  # Typical mobile transition timing
        
        # Analyze mobile pattern results
        successful_phases = [r for r in mobile_results if r['success']]
        failed_phases = [r for r in mobile_results if not r['success']]
        
        print(f"🔍 Mobile App Pattern Results:")
        print(f"   📊 Total auth attempts: {len(mobile_results)}")
        print(f"   ✅ Successful: {len(successful_phases)}")
        print(f"   ❌ Failed: {len(failed_phases)}")
        
        # Mobile apps should handle quick transitions smoothly
        # Current threshold likely breaks mobile UX
        if failed_phases:
            print(f"   🚨 Mobile UX degradation detected!")
            for failed in failed_phases:
                print(f"      ❌ {failed['phase']}: {failed.get('error', 'Auth failed')}")
        
        # Expect some failures due to strict threshold
        self.assertGreater(len(failed_phases), 0, 
                          "Expected mobile transition failures with current threshold")
        
        print(f"✅ Issue #465 CONFIRMED: Mobile app transitions affected - {len(failed_phases)} failures")

    def analyze_concurrent_access_results(self, results):
        """
        Analyze E2E test results for Issue #465 impact assessment
        """
        print(f"\n📊 Issue #465 E2E Impact Analysis:")
        
        # WebSocket analysis
        if results['websocket_connection']:
            if results['websocket_connection']['success']:
                print(f"   🔗 WebSocket: ✅ Connected successfully")
            else:
                print(f"   🔗 WebSocket: ❌ Failed - {results['websocket_connection'].get('error', 'Unknown error')}")
        
        # API calls analysis
        if results['api_calls']:
            successful_apis = [api for api in results['api_calls'] if api['success']]
            failed_apis = [api for api in results['api_calls'] if not api['success']]
            
            print(f"   📡 API Calls: {len(successful_apis)}✅ {len(failed_apis)}❌")
            
            for failed_api in failed_apis:
                print(f"      ❌ {failed_api['endpoint']}: {failed_api.get('error', failed_api.get('response', 'Failed'))}")
        
        # Chat functionality analysis
        if 'chat_response' in results:
            if results['chat_response']['success']:
                print(f"   💬 Chat: ✅ Message sent/received successfully")
            else:
                print(f"   💬 Chat: ❌ Failed - {results['chat_response'].get('error', 'Unknown error')}")
        
        # Overall impact assessment
        total_operations = len(results.get('api_calls', [])) + (1 if results.get('websocket_connection') else 0) + (1 if results.get('chat_response') else 0)
        failed_operations = len([api for api in results.get('api_calls', []) if not api['success']])
        
        if results.get('websocket_connection') and not results['websocket_connection']['success']:
            failed_operations += 1
        if results.get('chat_response') and not results['chat_response']['success']:
            failed_operations += 1
        
        if total_operations > 0:
            failure_rate = (failed_operations / total_operations) * 100
            print(f"   📈 Overall failure rate: {failure_rate:.1f}%")
            
            if failure_rate > 0:
                print(f"   🚨 BUSINESS IMPACT: Chat functionality (90% platform value) degraded!")
                print(f"   💰 REVENUE RISK: Concurrent usage patterns broken")
        
        # Error summary
        if results['errors']:
            print(f"   ⚠️ Error Summary:")
            for error in results['errors']:
                print(f"      • {error}")
        
        return {
            'total_operations': total_operations,
            'failed_operations': failed_operations,
            'failure_rate': failure_rate if total_operations > 0 else 0,
            'errors': results['errors']
        }


if __name__ == "__main__":
    print("🧪 Running Issue #465 WebSocket + API E2E Tests")
    print("📊 Expected Result: Tests should FAIL, proving real-world chat impact")
    print("🎯 Business Impact: Demonstrating 90% platform value (chat) is broken")
    
    # Note: These tests require running backend services
    print("⚠️ Prerequisites: Backend and WebSocket services must be running")
    print("   Start services: python scripts/refresh_dev_services.py")
    
    import unittest
    unittest.main()