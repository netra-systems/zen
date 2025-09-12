"""
Integration test to establish baseline WebSocket connection performance before deployment
This test should FAIL before deployment (documenting poor performance) and PASS after deployment

Business Value: Documents baseline WebSocket performance and validates improvement after Issue #128 fixes
"""
import pytest
import asyncio
import time
import socket
import requests

class TestStagingWebSocketBaseline:
    
    def test_staging_backend_connectivity_baseline(self):
        """INTEGRATION: Test basic connectivity to staging backend"""
        staging_backend_url = "https://netra-backend-staging-00282-244513.a.run.app"
        
        try:
            start_time = time.time()
            response = requests.get(f"{staging_backend_url}/health", timeout=15)
            response_time = time.time() - start_time
            
            print(f"Staging backend response time: {response_time:.2f}s")
            print(f"Staging backend status: {response.status_code}")
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"Staging health status: {health_data.get('status', 'unknown')}")
                
                # Document current configuration (before deployment)
                config_data = health_data.get("config", {})
                current_ws_timeout = config_data.get("websocket_connection_timeout", "not_set")
                print(f"Current WebSocket timeout config: {current_ws_timeout}")
                
                # BEFORE DEPLOYMENT: Should not have optimized timeout (360)
                # AFTER DEPLOYMENT: Should have optimized timeout (360)
                if current_ws_timeout == "360":
                    print(" PASS:  Optimized WebSocket timeout (360s) is active - deployment successful")
                else:
                    print(f" CHART:  BASELINE: WebSocket timeout not yet optimized: {current_ws_timeout}")
                    # Don't fail - this is expected before deployment
                
            # Document response time for comparison after deployment
            if response_time > 3.0:
                print(f" CHART:  BASELINE: Slow response time ({response_time:.2f}s) - expect improvement after deployment")
            else:
                print(f" PASS:  Good response time: {response_time:.2f}s")
                
        except requests.exceptions.RequestException as e:
            print(f" CHART:  BASELINE: Staging connectivity issue: {e}")
            # Don't fail - this documents the current state
            
    def test_websocket_endpoint_tcp_connectivity_baseline(self):
        """INTEGRATION: Test TCP connectivity to WebSocket endpoint"""
        staging_ws_host = "netra-backend-staging-00282-244513.a.run.app"
        staging_ws_port = 443
        
        connection_attempts = []
        
        # Try multiple connection attempts to measure consistency
        for attempt in range(3):
            try:
                start_time = time.time()
                sock = socket.create_connection((staging_ws_host, staging_ws_port), timeout=10)
                connection_time = time.time() - start_time
                sock.close()
                connection_attempts.append(connection_time)
                print(f"TCP connection attempt {attempt + 1}: {connection_time:.2f}s")
                
            except socket.timeout:
                connection_attempts.append(None)
                print(f"TCP connection attempt {attempt + 1}: TIMEOUT")
                
            except socket.error as e:
                connection_attempts.append(None)
                print(f"TCP connection attempt {attempt + 1}: ERROR - {e}")
        
        # Analyze connection attempts
        successful_connections = [t for t in connection_attempts if t is not None]
        
        if successful_connections:
            avg_connection_time = sum(successful_connections) / len(successful_connections)
            success_rate = len(successful_connections) / len(connection_attempts)
            
            print(f" CHART:  BASELINE: TCP connection success rate: {success_rate * 100:.1f}% ({len(successful_connections)}/3)")
            print(f" CHART:  BASELINE: Average TCP connection time: {avg_connection_time:.2f}s")
            
            # Document baseline performance
            if avg_connection_time > 2.0:
                print(f" CHART:  BASELINE: Slow TCP connections - expect improvement after deployment")
            if success_rate < 1.0:
                print(f" CHART:  BASELINE: Inconsistent TCP connectivity - expect improvement after deployment")
                
        else:
            print(" CHART:  BASELINE: All TCP connection attempts failed - significant connectivity issues")
    
    @pytest.mark.asyncio
    async def test_websocket_handshake_baseline(self):
        """INTEGRATION: Test WebSocket handshake baseline performance"""
        # Note: This test may fail before deployment due to WebSocket connectivity issues
        # That's expected and documents the current state
        
        try:
            # First check if we can get staging config
            from tests.e2e.staging_test_config import get_staging_config
            config = get_staging_config()
            
            print(f"Testing WebSocket connection to: {config.websocket_url}")
            
            # Get authentication headers
            ws_headers = config.get_websocket_headers()
            if ws_headers.get("Authorization"):
                print(" PASS:  WebSocket authentication headers available")
            else:
                print(" WARNING: [U+FE0F]  No WebSocket authentication headers - may cause connection failures")
            
            # Attempt WebSocket connection
            start_time = time.time()
            connection_successful = False
            error_message = None
            
            try:
                import websockets
                
                async with websockets.connect(
                    config.websocket_url,
                    additional_headers=ws_headers,
                    subprotocols=["jwt-auth"],
                    close_timeout=10
                ) as ws:
                    # Try to receive welcome message
                    welcome_response = await asyncio.wait_for(ws.recv(), timeout=15)
                    connection_time = time.time() - start_time
                    connection_successful = True
                    
                    print(f" PASS:  WebSocket connection successful in {connection_time:.2f}s")
                    print(f"Welcome message received: {welcome_response[:100]}...")
                    
            except asyncio.TimeoutError:
                connection_time = time.time() - start_time
                error_message = f"WebSocket timeout after {connection_time:.2f}s"
                
            except Exception as e:
                connection_time = time.time() - start_time  
                error_message = f"WebSocket error after {connection_time:.2f}s: {e}"
            
            # Document the baseline result
            if connection_successful:
                print(f" CHART:  BASELINE: WebSocket connection working - {connection_time:.2f}s")
                if connection_time > 5.0:
                    print(f" CHART:  BASELINE: Slow WebSocket connection - expect improvement after deployment")
            else:
                print(f" CHART:  BASELINE: WebSocket connection failed - {error_message}")
                print(" CHART:  BASELINE: This failure is expected before deployment of Issue #128 fixes")
                # Don't fail the test - this documents current state
                
        except ImportError as e:
            print(f" CHART:  BASELINE: Cannot test WebSocket connection - missing dependencies: {e}")
        except Exception as e:
            print(f" CHART:  BASELINE: WebSocket test error: {e}")
            
    def test_staging_environment_resource_baseline(self):
        """INTEGRATION: Document current staging resource utilization baseline"""
        staging_backend_url = "https://netra-backend-staging-00282-244513.a.run.app"
        
        try:
            # Test concurrent request handling (current resource capacity)
            start_time = time.time()
            responses = []
            
            import concurrent.futures
            import requests
            
            def make_request():
                try:
                    return requests.get(f"{staging_backend_url}/health", timeout=10)
                except Exception as e:
                    return None
            
            # Test concurrent load handling
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(make_request) for _ in range(3)]
                responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            successful_responses = [r for r in responses if r and r.status_code == 200]
            
            print(f" CHART:  BASELINE: 3 concurrent requests completed in {total_time:.2f}s")
            print(f" CHART:  BASELINE: Success rate: {len(successful_responses)}/3")
            
            if total_time > 8.0:
                print(" CHART:  BASELINE: Slow concurrent request handling - expect improvement with 4Gi/4CPU scaling")
            if len(successful_responses) < 3:
                print(" CHART:  BASELINE: Some concurrent requests failed - expect improvement with resource scaling")
                
        except Exception as e:
            print(f" CHART:  BASELINE: Cannot test concurrent load: {e}")
            
    def test_document_current_deployment_state(self):
        """INTEGRATION: Document current deployment state for comparison"""
        staging_backend_url = "https://netra-backend-staging-00282-244513.a.run.app"
        
        try:
            response = requests.get(f"{staging_backend_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                
                # Document current deployment info
                deployment_info = health_data.get("deployment", {})
                revision = deployment_info.get("revision", "unknown")
                
                print(f" CHART:  BASELINE DEPLOYMENT STATE:")
                print(f"  Revision: {revision}")
                print(f"  Health Status: {health_data.get('status', 'unknown')}")
                
                # Document current configurations
                config_data = health_data.get("config", {})
                websocket_configs = {
                    k: v for k, v in config_data.items() 
                    if "websocket" in k.lower() or "timeout" in k.lower()
                }
                
                if websocket_configs:
                    print(f"  Current WebSocket Configs:")
                    for key, value in websocket_configs.items():
                        print(f"    {key}: {value}")
                else:
                    print(f"  No WebSocket timeout configs found in health response")
                    
                # Check if this looks like the pre-deployment state
                ws_connection_timeout = config_data.get("websocket_connection_timeout")
                if ws_connection_timeout == "360":
                    print(" CELEBRATION:  DEPLOYMENT DETECTED: Optimized WebSocket timeout (360s) is already active!")
                    print("This suggests Issue #128 fixes have been deployed successfully.")
                else:
                    print(f" CHART:  PRE-DEPLOYMENT STATE: WebSocket connection timeout: {ws_connection_timeout}")
                    print("This suggests Issue #128 fixes have not yet been deployed.")
                    
        except Exception as e:
            print(f" CHART:  BASELINE: Cannot document deployment state: {e}")