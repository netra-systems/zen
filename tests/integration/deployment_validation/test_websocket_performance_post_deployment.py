"""
Integration test to validate WebSocket connection performance after deployment
This test should FAIL before deployment and PASS after deployment

Business Value: Validates that Issue #128 WebSocket performance improvements are active in staging
"""
import pytest
import asyncio
import time
import httpx

class TestWebSocketPerformancePostDeployment:
    
    @pytest.mark.asyncio
    async def test_websocket_timeout_configs_active_in_staging(self):
        """INTEGRATION: Validate optimized timeout configs are active in staging"""
        staging_backend_url = "https://netra-backend-staging-00282-244513.a.run.app"
        
        try:
            # Check if optimized timeout configs are now active
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{staging_backend_url}/health")
                
                if response.status_code != 200:
                    pytest.fail(f"Cannot reach staging health endpoint: {response.status_code}")
                
                health_data = response.json()
                
                # These should now be active after deployment
                config_data = health_data.get("config", {})
                
                # Validate Issue #128 timeout optimizations are active
                expected_timeouts = {
                    "websocket_connection_timeout": "360",      # 6 minutes
                    "websocket_heartbeat_interval": "15",       # 15 seconds  
                    "websocket_heartbeat_timeout": "45"         # 45 seconds
                }
                
                missing_configs = []
                for config_key, expected_value in expected_timeouts.items():
                    actual_value = config_data.get(config_key)
                    if actual_value != expected_value:
                        missing_configs.append(f"{config_key}={actual_value} (expected={expected_value})")
                
                if missing_configs:
                    # BEFORE DEPLOYMENT: This will fail
                    # AFTER DEPLOYMENT: This should pass
                    pytest.fail(f"DEPLOYMENT GAP: Timeout configs not yet active in staging: {missing_configs}")
                
                print("✅ All Issue #128 timeout optimizations are active in staging")
                
        except httpx.RequestError as e:
            pytest.fail(f"DEPLOYMENT GAP: Cannot connect to staging: {e}")
        except (KeyError, AttributeError) as e:
            pytest.fail(f"DEPLOYMENT GAP: Config structure not updated in staging: {e}")
    
    def test_staging_websocket_endpoint_availability(self):
        """INTEGRATION: Validate staging WebSocket endpoint is available with better performance"""
        import requests
        
        staging_backend_url = "https://netra-backend-staging-00282-244513.a.run.app"
        
        try:
            # Test that the health endpoint responds quickly (infrastructure improvement)
            start_time = time.time()
            response = requests.get(f"{staging_backend_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code != 200:
                pytest.fail(f"DEPLOYMENT GAP: Staging backend not responding properly: {response.status_code}")
            
            # After deployment with 4Gi memory and 4 CPU cores, response should be faster
            if response_time > 5.0:
                pytest.fail(f"DEPLOYMENT GAP: Staging response too slow ({response_time:.2f}s), deployment may not be active")
            
            health_data = response.json()
            status = health_data.get("status")
            
            if status != "healthy":
                pytest.fail(f"DEPLOYMENT GAP: Staging not healthy: {status}")
            
            print(f"✅ Staging backend responding in {response_time:.2f}s with healthy status")
            
            # Check for deployment indicators in health response
            deployment_info = health_data.get("deployment", {})
            revision = deployment_info.get("revision", "unknown")
            
            print(f"Staging revision: {revision}")
            
            # Look for signs that the new deployment is active
            if "netra-backend-staging" not in str(revision):
                print(f"⚠️  Warning: Deployment revision may not reflect recent changes: {revision}")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"DEPLOYMENT GAP: Cannot connect to staging backend: {e}")
    
    def test_websocket_connection_environment_readiness(self):
        """INTEGRATION: Test that staging environment is ready for WebSocket connections"""
        import socket
        
        # Parse WebSocket URL to test connectivity
        staging_ws_host = "netra-backend-staging-00282-244513.a.run.app"
        staging_ws_port = 443  # HTTPS/WSS port
        
        try:
            # Test TCP connectivity to WebSocket endpoint
            start_time = time.time()
            sock = socket.create_connection((staging_ws_host, staging_ws_port), timeout=10)
            connection_time = time.time() - start_time
            sock.close()
            
            # After deployment with resource scaling, connection should be faster
            if connection_time > 3.0:
                pytest.fail(f"DEPLOYMENT GAP: TCP connection too slow ({connection_time:.2f}s), may indicate deployment not active")
            
            print(f"✅ TCP connection to staging WebSocket endpoint: {connection_time:.2f}s")
            
        except socket.timeout:
            pytest.fail("DEPLOYMENT GAP: TCP connection timeout to staging WebSocket endpoint")
        except socket.error as e:
            pytest.fail(f"DEPLOYMENT GAP: TCP connection error to staging WebSocket endpoint: {e}")
    
    @pytest.mark.asyncio
    async def test_staging_resource_scaling_indicators(self):
        """INTEGRATION: Validate that staging shows signs of resource scaling deployment"""
        staging_backend_url = "https://netra-backend-staging-00282-244513.a.run.app"
        
        try:
            # Multiple rapid requests to test if 4Gi memory / 4 CPU cores are active
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=30) as client:
                # Concurrent requests to test resource capacity
                tasks = []
                for i in range(5):
                    task = client.get(f"{staging_backend_url}/health")
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks)
                
            total_time = time.time() - start_time
            
            # All requests should succeed
            for i, response in enumerate(responses):
                if response.status_code != 200:
                    pytest.fail(f"DEPLOYMENT GAP: Request {i+1} failed: {response.status_code}")
            
            # With 4Gi/4CPU scaling, concurrent requests should be handled efficiently
            avg_time_per_request = total_time / len(responses)
            
            if total_time > 10.0:
                pytest.fail(f"DEPLOYMENT GAP: Concurrent requests too slow ({total_time:.2f}s total), resource scaling may not be active")
            
            print(f"✅ 5 concurrent requests completed in {total_time:.2f}s (avg: {avg_time_per_request:.2f}s each)")
            
            # Check for any resource-related indicators in responses
            for response in responses:
                health_data = response.json()
                if health_data.get("status") != "healthy":
                    pytest.fail(f"DEPLOYMENT GAP: Staging health degraded under concurrent load")
                    
        except httpx.RequestError as e:
            pytest.fail(f"DEPLOYMENT GAP: Cannot test concurrent requests against staging: {e}")
        except asyncio.TimeoutError:
            pytest.fail("DEPLOYMENT GAP: Concurrent requests timed out - resource scaling may not be active")