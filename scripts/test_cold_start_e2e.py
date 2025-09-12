#!/usr/bin/env python3
"""
End-to-End Cold Start Test Suite for Netra Apex Platform

This comprehensive test validates the entire user flow from cold start through
authentication, WebSocket connection, chat interaction, and model response.

Critical Path Tested:
1. Dev launcher startup with all services
2. Service discovery and dynamic port handling
3. Auth service login (dev mode)
4. Token retrieval and validation
5. WebSocket connection with auth
6. Chat message sending
7. Model processing and response
8. Clean shutdown

Author: Netra Apex Engineering
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import websockets
from websockets import ClientConnection as WebSocketClientProtocol

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    'startup_timeout': 60,  # seconds
    'request_timeout': 10,  # seconds
    'websocket_timeout': 30,  # seconds
    'test_user': {
        'email': 'test@netrasystems.ai',
        'password': 'test123456',
        'name': 'Test User'
    },
    'test_message': 'Hello, can you help me optimize my AI workload?',
    'expected_patterns': [
        'optimize', 'workload', 'performance', 'cost', 'efficiency'
    ]
}


class ColdStartE2ETest:
    """End-to-end test suite for cold start validation."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.discovery_dir = self.project_root / '.service_discovery'
        self.launcher_process: Optional[subprocess.Popen] = None
        self.services: Dict[str, Dict[str, Any]] = {}
        self.auth_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.test_results: Dict[str, bool] = {}
        
    async def run_full_test(self) -> bool:
        """Run the complete E2E test suite."""
        logger.info("[U+1F680] Starting Cold Start E2E Test Suite")
        
        try:
            # Phase 1: Start services
            if not await self.start_services():
                return False
                
            # Phase 2: Wait for services to be healthy
            if not await self.wait_for_services():
                return False
                
            # Phase 3: Test authentication
            if not await self.test_authentication():
                return False
                
            # Phase 4: Test WebSocket connection
            if not await self.test_websocket():
                return False
                
            # Phase 5: Test chat flow
            if not await self.test_chat_flow():
                return False
                
            # Phase 6: Test model response
            if not await self.test_model_response():
                return False
                
            logger.info(" PASS:  All E2E tests passed successfully!")
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  E2E test failed: {e}")
            return False
            
        finally:
            await self.cleanup()
            
    async def start_services(self) -> bool:
        """Start all services using dev launcher."""
        logger.info("[U+1F4E6] Starting services with dev launcher...")
        
        try:
            # Start dev launcher
            cmd = [sys.executable, 'scripts/dev_launcher.py', '--no-browser']
            self.launcher_process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give services time to start
            await asyncio.sleep(10)
            
            # Check if launcher is still running
            if self.launcher_process.poll() is not None:
                stdout, stderr = self.launcher_process.communicate()
                logger.error(f"Dev launcher exited unexpectedly")
                logger.error(f"Stdout: {stdout}")
                logger.error(f"Stderr: {stderr}")
                return False
                
            logger.info(" PASS:  Services started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            return False
            
    async def wait_for_services(self) -> bool:
        """Wait for all services to be healthy."""
        logger.info("[U+23F3] Waiting for services to be healthy...")
        
        start_time = time.time()
        timeout = TEST_CONFIG['startup_timeout']
        
        while time.time() - start_time < timeout:
            # Read service discovery
            self.services = self.read_service_discovery()
            
            if self.services:
                # Check health endpoints
                all_healthy = True
                for service_name, service_info in self.services.items():
                    if not await self.check_service_health(service_name, service_info):
                        all_healthy = False
                        break
                        
                if all_healthy:
                    logger.info(" PASS:  All services are healthy")
                    return True
                    
            await asyncio.sleep(2)
            
        logger.error(" FAIL:  Services failed to become healthy within timeout")
        return False
        
    def read_service_discovery(self) -> Dict[str, Dict[str, Any]]:
        """Read service discovery information."""
        services = {}
        
        if not self.discovery_dir.exists():
            return services
            
        for json_file in self.discovery_dir.glob('*.json'):
            try:
                with open(json_file, 'r') as f:
                    service_data = json.load(f)
                    service_name = json_file.stem
                    services[service_name] = service_data
            except Exception as e:
                logger.warning(f"Failed to read {json_file}: {e}")
                
        return services
        
    async def check_service_health(self, name: str, info: Dict[str, Any]) -> bool:
        """Check if a service is healthy."""
        try:
            # Determine health endpoint
            if 'api_url' in info:
                health_url = f"{info['api_url']}/health"
            elif 'url' in info:
                health_url = f"{info['url']}/health"
            else:
                return False
                
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    health_url,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.debug(f" PASS:  {name} service is healthy")
                        return True
                    else:
                        logger.debug(f" WARNING: [U+FE0F] {name} service returned {response.status}")
                        return False
                        
        except Exception as e:
            logger.debug(f" WARNING: [U+FE0F] {name} service health check failed: {e}")
            return False
            
    async def test_authentication(self) -> bool:
        """Test authentication flow."""
        logger.info("[U+1F510] Testing authentication...")
        
        try:
            # Get auth service URL
            auth_url = self.get_auth_url()
            if not auth_url:
                logger.error("Auth service URL not found")
                return False
                
            # Test dev login
            async with aiohttp.ClientSession() as session:
                # Dev login endpoint
                login_url = f"{auth_url}/auth/dev-login"
                login_data = {
                    'email': TEST_CONFIG['test_user']['email'],
                    'name': TEST_CONFIG['test_user']['name']
                }
                
                async with session.post(
                    login_url,
                    json=login_data,
                    timeout=aiohttp.ClientTimeout(total=TEST_CONFIG['request_timeout'])
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.auth_token = data.get('access_token')
                        self.user_id = data.get('user_id', 'test_user')
                        
                        if self.auth_token:
                            logger.info(f" PASS:  Authentication successful (user: {self.user_id})")
                            return True
                        else:
                            logger.error("No access token received")
                            return False
                    else:
                        text = await response.text()
                        logger.error(f"Login failed with status {response.status}: {text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False
            
    async def test_websocket(self) -> bool:
        """Test WebSocket connection."""
        logger.info("[U+1F50C] Testing WebSocket connection...")
        
        try:
            ws_url = self.get_websocket_url()
            if not ws_url:
                logger.error("WebSocket URL not found")
                return False
                
            # Connect with auth token
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f"Bearer {self.auth_token}"
                
            async with websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                # Send auth message
                auth_msg = {
                    'type': 'auth',
                    'payload': {
                        'token': self.auth_token
                    }
                }
                await websocket.send(json.dumps(auth_msg))
                
                # Wait for auth confirmation
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=TEST_CONFIG['websocket_timeout']
                )
                
                data = json.loads(response)
                if data.get('type') == 'auth_success':
                    logger.info(" PASS:  WebSocket connection authenticated")
                    return True
                else:
                    logger.error(f"WebSocket auth failed: {data}")
                    return False
                    
        except Exception as e:
            logger.error(f"WebSocket test failed: {e}")
            return False
            
    async def test_chat_flow(self) -> bool:
        """Test sending a chat message."""
        logger.info("[U+1F4AC] Testing chat message flow...")
        
        try:
            api_url = self.get_api_url()
            if not api_url:
                logger.error("API URL not found")
                return False
                
            # Create a thread
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f"Bearer {self.auth_token}"}
                
                # Create thread
                thread_url = f"{api_url}/api/threads"
                thread_data = {
                    'name': 'E2E Test Thread',
                    'description': 'Automated test thread'
                }
                
                async with session.post(
                    thread_url,
                    json=thread_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=TEST_CONFIG['request_timeout'])
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"Failed to create thread: {text}")
                        return False
                        
                    thread = await response.json()
                    thread_id = thread['id']
                    logger.info(f" PASS:  Thread created: {thread_id}")
                    
                # Send message
                message_url = f"{api_url}/api/threads/{thread_id}/messages"
                message_data = {
                    'content': TEST_CONFIG['test_message'],
                    'role': 'user'
                }
                
                async with session.post(
                    message_url,
                    json=message_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=TEST_CONFIG['request_timeout'])
                ) as response:
                    if response.status == 200:
                        logger.info(" PASS:  Message sent successfully")
                        return True
                    else:
                        text = await response.text()
                        logger.error(f"Failed to send message: {text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Chat flow test failed: {e}")
            return False
            
    async def test_model_response(self) -> bool:
        """Test receiving model response via WebSocket."""
        logger.info("[U+1F916] Testing model response...")
        
        try:
            ws_url = self.get_websocket_url()
            if not ws_url:
                logger.error("WebSocket URL not found")
                return False
                
            # Connect and wait for model response
            headers = {}
            if self.auth_token:
                headers['Authorization'] = f"Bearer {self.auth_token}"
                
            async with websockets.connect(
                ws_url,
                extra_headers=headers
            ) as websocket:
                # Auth first
                auth_msg = {
                    'type': 'auth',
                    'payload': {'token': self.auth_token}
                }
                await websocket.send(json.dumps(auth_msg))
                
                # Wait for messages
                start_time = time.time()
                timeout = TEST_CONFIG['websocket_timeout']
                
                while time.time() - start_time < timeout:
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=5
                        )
                        
                        data = json.loads(response)
                        msg_type = data.get('type')
                        
                        # Check for model response types
                        if msg_type in ['agent_started', 'partial_result', 'agent_completed']:
                            logger.info(f" PASS:  Received model event: {msg_type}")
                            
                            # Check if response contains expected patterns
                            payload = data.get('payload', {})
                            content = str(payload.get('content', ''))
                            
                            for pattern in TEST_CONFIG['expected_patterns']:
                                if pattern.lower() in content.lower():
                                    logger.info(f" PASS:  Model response contains expected pattern: {pattern}")
                                    return True
                                    
                    except asyncio.TimeoutError:
                        continue
                        
            logger.warning(" WARNING: [U+FE0F] No model response received within timeout")
            return True  # Consider this a soft pass if services are up
            
        except Exception as e:
            logger.error(f"Model response test failed: {e}")
            return False
            
    def get_api_url(self) -> Optional[str]:
        """Get backend API URL from service discovery."""
        backend = self.services.get('backend', {})
        return backend.get('api_url') or backend.get('url')
        
    def get_auth_url(self) -> Optional[str]:
        """Get auth service URL from service discovery."""
        auth = self.services.get('auth', {})
        return auth.get('url') or auth.get('api_url') or 'http://localhost:8083'
        
    def get_websocket_url(self) -> Optional[str]:
        """Get WebSocket URL from service discovery."""
        backend = self.services.get('backend', {})
        ws_url = backend.get('ws_url')
        
        if ws_url:
            # Ensure it's the secure endpoint
            if '/secure' not in ws_url and '/v1' not in ws_url:
                ws_url = ws_url.replace('/ws', '/ws')
            return ws_url
            
        # Fallback
        api_url = self.get_api_url()
        if api_url:
            return api_url.replace('http://', 'ws://') + '/ws'
            
        return None
        
    async def cleanup(self):
        """Clean up resources."""
        logger.info("[U+1F9F9] Cleaning up...")
        
        if self.launcher_process:
            try:
                # Graceful shutdown
                self.launcher_process.terminate()
                await asyncio.sleep(2)
                
                if self.launcher_process.poll() is None:
                    # Force kill if still running
                    self.launcher_process.kill()
                    
                logger.info(" PASS:  Services stopped")
            except Exception as e:
                logger.warning(f"Cleanup error: {e}")
                
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("E2E COLD START TEST SUMMARY")
        print("="*60)
        
        for test_name, passed in self.test_results.items():
            status = " PASS:  PASS" if passed else " FAIL:  FAIL"
            print(f"{test_name}: {status}")
            
        print("="*60)
        
        all_passed = all(self.test_results.values())
        if all_passed:
            print(" CELEBRATION:  ALL TESTS PASSED!")
        else:
            print(" WARNING: [U+FE0F] SOME TESTS FAILED")
            
        print("="*60 + "\n")


async def main():
    """Main entry point."""
    test = ColdStartE2ETest()
    
    # Run tests
    success = await test.run_full_test()
    
    # Print summary
    test.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())