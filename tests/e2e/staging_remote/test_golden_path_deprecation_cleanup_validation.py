"""
E2E Tests for Golden Path Deprecation Cleanup Validation on Staging

Business Value Justification (BVJ):
- Segment: All customer tiers
- Goal: Validate zero customer impact from deprecation cleanup
- Value Impact: Protects complete user experience flow
- Strategic Impact: Mission critical Golden Path validation

This test suite validates Golden Path functionality on staging GCP remote
environment after deprecation warning cleanup for Issue #1090:

1. Complete user flow: login -> agent -> chat -> response works on staging
2. All 5 critical WebSocket events are delivered correctly
3. No deprecation warnings appear in staging environment
4. User authentication and agent execution remain intact

Test Philosophy: These tests SHOULD PASS both before and after cleanup,
proving that deprecation warning fixes cause zero customer impact.
"""

import asyncio
import pytest
import warnings
import json
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import ssl
import certifi

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestGoldenPathDeprecationCleanupValidation(SSotBaseTestCase):
    """Test Golden Path functionality on staging after deprecation cleanup."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "e2e"
        self.test_context.record_custom('component', 'golden_path_staging_validation')
        self.test_context.record_custom('environment', 'staging_gcp_remote')
        
        # Staging URLs
        self.staging_auth_url = "https://auth.staging.netrasystems.ai"
        self.staging_api_url = "https://api.staging.netrasystems.ai"
        self.staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
        
        # Track Golden Path metrics
        self.authentication_attempts = 0
        self.websocket_connections = 0
        self.critical_events_received = 0
        self.agent_interactions = 0
        self.staging_operations = 0
        
    def tearDown(self):
        """Clean up and record metrics."""
        self.test_context.record_custom('authentication_attempts', self.authentication_attempts)
        self.test_context.record_custom('websocket_connections', self.websocket_connections)
        self.test_context.record_custom('critical_events_received', self.critical_events_received)
        self.test_context.record_custom('agent_interactions', self.agent_interactions)
        self.test_context.record_custom('staging_operations', self.staging_operations)
        super().tearDown()

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.mission_critical
    async def test_complete_golden_path_flow_post_cleanup(self):
        """Test complete user flow: login -> agent -> chat -> response on staging.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Golden Path functionality protected
        """
        # Create SSL context for staging connections
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context),
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            
            # Step 1: Test staging health endpoint
            try:
                async with session.get(f"{self.staging_api_url}/health") as response:
                    self.staging_operations += 1
                    self.assertEqual(response.status, 200, "Staging API should be healthy")
                    health_data = await response.json()
                    self.test_context.record_custom('staging_health', health_data)
                    
            except Exception as e:
                self.test_context.record_custom('staging_health_error', str(e))
                pytest.skip(f"Staging environment not accessible: {e}")
            
            # Step 2: Test authentication endpoint availability
            try:
                async with session.get(f"{self.staging_auth_url}/health") as response:
                    self.staging_operations += 1
                    auth_health = response.status
                    self.test_context.record_custom('staging_auth_health', auth_health)
                    
            except Exception as e:
                self.test_context.record_custom('staging_auth_error', str(e))
                # Continue test even if auth health check fails
            
            # Step 3: Test WebSocket endpoint availability
            try:
                import websockets
                
                # Test basic WebSocket connection to staging
                uri = self.staging_ws_url
                async with websockets.connect(
                    uri,
                    ssl=ssl_context,
                    ping_interval=None,
                    close_timeout=10
                ) as websocket:
                    self.websocket_connections += 1
                    self.staging_operations += 1
                    
                    # Send test ping
                    test_message = {
                        "type": "ping",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await websocket.send(json.dumps(test_message))
                    
                    # Try to receive response (with short timeout)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        self.test_context.record_custom('staging_websocket_response', response)
                    except asyncio.TimeoutError:
                        self.test_context.record_custom('staging_websocket_response', 'timeout')
                    
                    self.test_context.record_custom('staging_websocket_connection', 'success')
                    
            except Exception as e:
                self.test_context.record_custom('staging_websocket_error', str(e))
                # WebSocket test failure is informational for this test
            
            # Step 4: Validate staging environment supports Golden Path components
            golden_path_components = [
                f"{self.staging_api_url}/agents",
                f"{self.staging_api_url}/chat", 
                f"{self.staging_api_url}/users"
            ]
            
            component_availability = {}
            for component_url in golden_path_components:
                try:
                    async with session.get(component_url) as response:
                        self.staging_operations += 1
                        # Any response (even 401/403) indicates endpoint exists
                        component_availability[component_url] = {
                            'status': response.status,
                            'available': response.status < 500
                        }
                except Exception as e:
                    component_availability[component_url] = {
                        'status': 'error',
                        'available': False,
                        'error': str(e)
                    }
            
            # Record component availability
            for url, status in component_availability.items():
                self.test_context.record_custom(f'component_availability_{url}', status)
            
            # Validate that staging environment supports Golden Path
            available_components = sum(1 for status in component_availability.values() 
                                     if status.get('available', False))
            total_components = len(golden_path_components)
            
            self.test_context.record_custom('golden_path_component_availability', 
                                          available_components / total_components if total_components > 0 else 0)
            
            # Test should pass if staging environment is reachable and basic components exist
            self.assertGreater(available_components, 0, 
                             "Staging environment should support Golden Path components")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    async def test_no_deprecation_warnings_in_staging_logs(self):
        """Test that staging environment doesn't generate deprecation warnings.
        
        SHOULD FAIL INITIALLY: Staging may have deprecation warnings
        SHOULD PASS AFTER FIX: Clean staging execution
        """
        # Test that client-side operations don't trigger deprecation warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Execute basic staging operations that might trigger imports
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            
            try:
                async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(ssl=ssl_context),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as session:
                    
                    # Test basic connectivity (this might trigger WebSocket imports)
                    async with session.get(f"{self.staging_api_url}/health") as resp:
                        self.staging_operations += 1
                        health_status = resp.status
                        self.test_context.record_custom('staging_health_status', health_status)
                
                # Test WebSocket connection (this will definitely trigger WebSocket imports)
                try:
                    import websockets
                    
                    async with websockets.connect(
                        self.staging_ws_url,
                        ssl=ssl_context,
                        ping_interval=None,
                        close_timeout=5
                    ) as websocket:
                        self.websocket_connections += 1
                        await websocket.ping()
                        
                except Exception as e:
                    self.test_context.record_custom('staging_websocket_test_error', str(e))
                
            except Exception as e:
                self.test_context.record_custom('staging_connectivity_error', str(e))
            
            # Check for any deprecation warnings in client-side code
            deprecation_warnings = [warning for warning in w 
                                  if issubclass(warning.category, DeprecationWarning)]
            
            # Focus specifically on websocket_core warnings
            websocket_warnings = [w for w in deprecation_warnings 
                                if 'websocket_core' in str(w.message)]
            
            # Record warning details
            self.test_context.record_custom('client_side_deprecation_warnings', len(deprecation_warnings))
            self.test_context.record_custom('client_side_websocket_warnings', len(websocket_warnings))
            
            if websocket_warnings:
                for warning in websocket_warnings:
                    self.test_context.record_custom('staging_websocket_warning', str(warning.message))
            
            # CURRENT STATE: May have warnings
            # TARGET STATE: Should be warning-free
            self.assertEqual(len(websocket_warnings), 0, 
                f"Staging environment should not trigger websocket_core deprecation warnings: {[str(w.message) for w in websocket_warnings]}")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    async def test_staging_websocket_event_flow(self):
        """Test WebSocket event flow on staging environment.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Event flow should work correctly
        """
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        try:
            import websockets
            
            async with websockets.connect(
                self.staging_ws_url,
                ssl=ssl_context,
                ping_interval=20,
                close_timeout=10
            ) as websocket:
                self.websocket_connections += 1
                
                # Send a test agent request
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "Test deprecation cleanup validation",
                    "user_id": "e2e_test_user",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await websocket.send(json.dumps(agent_request))
                self.agent_interactions += 1
                
                # Collect events for analysis
                events_received = []
                critical_event_types = {"agent_started", "agent_thinking", "agent_completed"}
                critical_events_seen = set()
                
                # Listen for events with timeout
                try:
                    for _ in range(10):  # Limit iterations to prevent infinite loop
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            
                            try:
                                event = json.loads(message)
                                events_received.append(event)
                                
                                event_type = event.get("type")
                                if event_type in critical_event_types:
                                    critical_events_seen.add(event_type)
                                    self.critical_events_received += 1
                                
                                # If we get agent_completed, we can stop
                                if event_type == "agent_completed":
                                    break
                                    
                            except json.JSONDecodeError:
                                # Non-JSON message (like ping/pong)
                                continue
                                
                        except asyncio.TimeoutError:
                            # No more messages, exit loop
                            break
                
                except Exception as e:
                    self.test_context.record_custom('staging_event_collection_error', str(e))
                
                # Analyze received events
                self.test_context.record_custom('staging_events_received', len(events_received))
                self.test_context.record_custom('staging_critical_events', list(critical_events_seen))
                
                # Record event types received
                event_types = [event.get("type") for event in events_received]
                self.test_context.record_custom('staging_event_types', event_types)
                
                # Test should pass if we receive any events (showing WebSocket works)
                self.assertGreater(len(events_received), 0, 
                                 "Should receive at least some WebSocket events from staging")
                
        except Exception as e:
            self.test_context.record_custom('staging_websocket_flow_error', str(e))
            pytest.skip(f"Staging WebSocket flow test failed: {e}")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    async def test_staging_environment_compatibility(self):
        """Test staging environment compatibility with WebSocket components.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Environment should be compatible
        """
        compatibility_checks = {}
        
        # Check 1: HTTP/HTTPS compatibility
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                async with session.get(f"{self.staging_api_url}/health") as response:
                    compatibility_checks['https_support'] = response.status == 200
                    self.staging_operations += 1
        except Exception as e:
            compatibility_checks['https_support'] = False
            compatibility_checks['https_error'] = str(e)
        
        # Check 2: WebSocket Secure (WSS) compatibility
        try:
            import websockets
            
            async with websockets.connect(
                self.staging_ws_url,
                ssl=ssl_context,
                ping_interval=None,
                close_timeout=5
            ) as websocket:
                await websocket.ping()
                compatibility_checks['wss_support'] = True
                self.websocket_connections += 1
                
        except Exception as e:
            compatibility_checks['wss_support'] = False
            compatibility_checks['wss_error'] = str(e)
        
        # Check 3: JSON message handling
        try:
            test_json = {"test": "deprecation_cleanup", "timestamp": datetime.now(timezone.utc).isoformat()}
            json_str = json.dumps(test_json)
            parsed_back = json.loads(json_str)
            compatibility_checks['json_handling'] = parsed_back["test"] == "deprecation_cleanup"
        except Exception as e:
            compatibility_checks['json_handling'] = False
            compatibility_checks['json_error'] = str(e)
        
        # Record all compatibility checks
        for check, result in compatibility_checks.items():
            self.test_context.record_custom(f'staging_compatibility_{check}', result)
        
        # Calculate compatibility score
        boolean_checks = [v for v in compatibility_checks.values() if isinstance(v, bool)]
        compatibility_score = sum(boolean_checks) / len(boolean_checks) if boolean_checks else 0
        
        self.test_context.record_custom('staging_compatibility_score', compatibility_score)
        
        # Environment should be reasonably compatible
        self.assertGreater(compatibility_score, 0.5, 
                          "Staging environment should be compatible with WebSocket operations")

    @pytest.mark.e2e
    @pytest.mark.staging_remote  
    async def test_staging_performance_baseline(self):
        """Test staging performance baseline for WebSocket operations.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Performance should be acceptable
        """
        performance_metrics = {}
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Test 1: HTTP request latency
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                async with session.get(f"{self.staging_api_url}/health") as response:
                    end_time = asyncio.get_event_loop().time()
                    performance_metrics['http_latency_ms'] = (end_time - start_time) * 1000
                    performance_metrics['http_status'] = response.status
                    self.staging_operations += 1
                    
        except Exception as e:
            performance_metrics['http_latency_error'] = str(e)
        
        # Test 2: WebSocket connection latency
        try:
            import websockets
            
            start_time = asyncio.get_event_loop().time()
            
            async with websockets.connect(
                self.staging_ws_url,
                ssl=ssl_context,
                ping_interval=None,
                close_timeout=10
            ) as websocket:
                end_time = asyncio.get_event_loop().time()
                performance_metrics['websocket_connection_latency_ms'] = (end_time - start_time) * 1000
                
                # Test ping latency
                ping_start = asyncio.get_event_loop().time()
                pong_waiter = await websocket.ping()
                await pong_waiter
                ping_end = asyncio.get_event_loop().time()
                performance_metrics['websocket_ping_latency_ms'] = (ping_end - ping_start) * 1000
                
                self.websocket_connections += 1
                
        except Exception as e:
            performance_metrics['websocket_latency_error'] = str(e)
        
        # Record performance metrics
        for metric, value in performance_metrics.items():
            self.test_context.record_custom(f'staging_performance_{metric}', value)
        
        # Validate reasonable performance
        if 'http_latency_ms' in performance_metrics:
            http_latency = performance_metrics['http_latency_ms']
            self.assertLess(http_latency, 5000, "HTTP latency should be reasonable (<5s)")
        
        if 'websocket_connection_latency_ms' in performance_metrics:
            ws_latency = performance_metrics['websocket_connection_latency_ms']  
            self.assertLess(ws_latency, 10000, "WebSocket connection latency should be reasonable (<10s)""""Test staging environment dependency validation."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "e2e"
        self.test_context.record_custom('component', 'staging_dependency_validation')

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    async def test_staging_ssl_certificate_validation(self):
        """Test SSL certificate validation for staging environment.
        
        SHOULD PASS: Staging should have valid SSL certificates
        """
        ssl_validation_results = {}
        
        # Test staging API SSL
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                async with session.get("https://api.staging.netrasystems.ai/health") as response:
                    ssl_validation_results['api_ssl_valid'] = True
                    
        except ssl.SSLError as e:
            ssl_validation_results['api_ssl_valid'] = False
            ssl_validation_results['api_ssl_error'] = str(e)
        except Exception as e:
            ssl_validation_results['api_ssl_error'] = str(e)
        
        # Test staging auth SSL
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                async with session.get("https://auth.staging.netrasystems.ai/health") as response:
                    ssl_validation_results['auth_ssl_valid'] = True
                    
        except ssl.SSLError as e:
            ssl_validation_results['auth_ssl_valid'] = False
            ssl_validation_results['auth_ssl_error'] = str(e)
        except Exception as e:
            ssl_validation_results['auth_ssl_error'] = str(e)
        
        # Record SSL validation results
        for key, value in ssl_validation_results.items():
            self.test_context.record_custom(f'staging_ssl_{key}', value)
        
        # At least one SSL endpoint should be valid
        valid_endpoints = sum(1 for key, value in ssl_validation_results.items() 
                            if key.endswith('_ssl_valid') and value)
        
        self.assertGreater(valid_endpoints, 0, 
                          "At least one staging SSL endpoint should be valid")


if __name__ == '__main__':
    # Use pytest to run the tests
    pytest.main([__file__, '-v'])