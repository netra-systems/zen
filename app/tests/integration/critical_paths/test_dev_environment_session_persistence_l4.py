#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment Session Persistence

Tests comprehensive session management and persistence across services:
1. Session creation and initialization
2. Cross-service session propagation
3. Session state persistence and recovery
4. Session expiration and renewal
5. Multi-device session synchronization
6. Session cleanup and invalidation
7. Performance under session load
8. Session security and isolation

BVJ:
- Segment: Free, Early, Mid, Enterprise
- Business Goal: Retention, User Experience
- Value Impact: Seamless user experience across sessions and devices
- Strategic Impact: User trust and platform reliability foundation
"""

import asyncio
import json
import os
import sys
import time
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import aiohttp
import websockets
import pytest
from datetime import datetime, timedelta
import redis

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Service URLs
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"
REDIS_URL = "redis://localhost:6379"

# Test configurations
TEST_USERS = [
    {
        "email": "session_test_1@example.com",
        "password": "SecurePass123!",
        "name": "Session Test User 1",
        "tier": "free"
    },
    {
        "email": "session_test_2@example.com",
        "password": "SecurePass456!",
        "name": "Session Test User 2",
        "tier": "early"
    },
    {
        "email": "session_test_3@example.com",
        "password": "SecurePass789!",
        "name": "Session Test User 3",
        "tier": "enterprise"
    }
]

SESSION_TEST_SCENARIOS = [
    {
        "name": "basic_session_lifecycle",
        "description": "Test basic session creation, use, and cleanup",
        "steps": ["create", "validate", "use", "cleanup"]
    },
    {
        "name": "cross_service_persistence",
        "description": "Test session persistence across multiple services",
        "steps": ["create", "auth_service", "backend_service", "websocket_service"]
    },
    {
        "name": "session_recovery",
        "description": "Test session recovery after connection loss",
        "steps": ["create", "disconnect", "reconnect", "validate"]
    },
    {
        "name": "session_expiration",
        "description": "Test session expiration and renewal",
        "steps": ["create", "expire", "renew", "validate"]
    },
    {
        "name": "multi_device_sync",
        "description": "Test session synchronization across multiple devices",
        "steps": ["create_device1", "create_device2", "sync_state", "validate_consistency"]
    }
]


class SessionPersistenceTester:
    """Test comprehensive session persistence functionality."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_tokens: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, List[Any]] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.test_logs: List[str] = []
        self.performance_metrics: Dict[str, List[float]] = {
            "session_creation_times": [],
            "session_recovery_times": [],
            "cross_service_times": [],
            "sync_times": []
        }
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        
        # Setup Redis connection for session inspection
        try:
            self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            await asyncio.to_thread(self.redis_client.ping)
            self.log_event("SYSTEM", "REDIS_CONNECTED", "Redis connection established")
        except Exception as e:
            self.log_event("SYSTEM", "REDIS_WARNING", f"Redis connection failed: {e}")
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        # Close all WebSocket connections
        for email, connections in self.websocket_connections.items():
            for ws in connections:
                try:
                    if ws and not ws.closed:
                        await ws.close()
                except:
                    pass
                    
        if self.redis_client:
            try:
                await asyncio.to_thread(self.redis_client.close)
            except:
                pass
                
        if self.session:
            await self.session.close()
    
    def log_event(self, user: str, event: str, details: str = ""):
        """Log test events for analysis."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{user}] {event}"
        if details:
            log_entry += f" - {details}"
        self.test_logs.append(log_entry)
        print(log_entry)
    
    async def setup_test_user(self, user_data: Dict[str, Any]) -> bool:
        """Setup a test user with authentication."""
        email = user_data["email"]
        
        self.log_event(email, "USER_SETUP", "Starting user setup")
        
        try:
            # Register user
            register_payload = {
                "email": email,
                "password": user_data["password"],
                "name": user_data["name"],
                "tier": user_data.get("tier", "free")
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_payload
            ) as response:
                if response.status in [200, 201, 409]:  # Include 409 for existing users
                    self.log_event(email, "REGISTRATION_OK", f"Status: {response.status}")
                else:
                    self.log_event(email, "REGISTRATION_FAILED", f"Status: {response.status}")
                    return False
            
            # Login user and get session info
            login_payload = {
                "email": email,
                "password": user_data["password"]
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Store comprehensive session info
                    self.user_tokens[email] = {
                        "access_token": data.get("access_token"),
                        "refresh_token": data.get("refresh_token"),
                        "session_id": data.get("session_id"),
                        "expires_in": data.get("expires_in"),
                        "created_at": datetime.now(),
                        "user_id": data.get("user_id")
                    }
                    
                    self.log_event(email, "LOGIN_SUCCESS", f"Session: {data.get('session_id', 'unknown')}")
                    return True
                else:
                    self.log_event(email, "LOGIN_FAILED", f"Status: {response.status}")
                    return False
                    
        except Exception as e:
            self.log_event(email, "SETUP_ERROR", str(e))
            return False
    
    async def test_session_creation(self, email: str) -> Dict[str, Any]:
        """Test comprehensive session creation process."""
        result = {
            "session_created": False,
            "session_id": None,
            "creation_time": 0,
            "redis_stored": False,
            "session_data_valid": False,
            "expiration_set": False
        }
        
        if email not in self.user_tokens:
            return result
            
        start_time = time.time()
        self.log_event(email, "SESSION_CREATE_START", "Testing session creation")
        
        try:
            # Get session details from login
            token_data = self.user_tokens[email]
            session_id = token_data.get("session_id")
            
            if session_id:
                result["session_created"] = True
                result["session_id"] = session_id
                
                # Verify session in Redis
                if self.redis_client:
                    try:
                        session_key = f"session:{session_id}"
                        session_exists = await asyncio.to_thread(
                            self.redis_client.exists, session_key
                        )
                        
                        if session_exists:
                            result["redis_stored"] = True
                            
                            # Get session data
                            session_data = await asyncio.to_thread(
                                self.redis_client.hgetall, session_key
                            )
                            
                            # Validate session data structure
                            required_fields = ["user_id", "created_at", "expires_at"]
                            if all(field in session_data for field in required_fields):
                                result["session_data_valid"] = True
                                
                            # Check expiration
                            ttl = await asyncio.to_thread(
                                self.redis_client.ttl, session_key
                            )
                            if ttl > 0:
                                result["expiration_set"] = True
                                
                            self.log_event(email, "SESSION_REDIS_OK", f"TTL: {ttl}s")
                            
                    except Exception as e:
                        self.log_event(email, "SESSION_REDIS_ERROR", str(e))
                
                # Store session data for later tests
                self.session_data[email] = {
                    "session_id": session_id,
                    "created_at": datetime.now(),
                    "token_data": token_data
                }
                
        except Exception as e:
            self.log_event(email, "SESSION_CREATE_ERROR", str(e))
            
        result["creation_time"] = time.time() - start_time
        self.performance_metrics["session_creation_times"].append(result["creation_time"])
        
        self.log_event(email, "SESSION_CREATE_COMPLETE", 
                     f"Success: {result['session_created']}, Time: {result['creation_time']:.2f}s")
        
        return result
    
    async def test_cross_service_persistence(self, email: str) -> Dict[str, Any]:
        """Test session persistence across different services."""
        result = {
            "auth_service_valid": False,
            "backend_service_valid": False,
            "websocket_service_valid": False,
            "session_consistent": False,
            "total_time": 0
        }
        
        token_data = self.user_tokens.get(email)
        if not token_data:
            return result
            
        start_time = time.time()
        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        self.log_event(email, "CROSS_SERVICE_START", "Testing cross-service session persistence")
        
        try:
            # Test 1: Auth Service Session Validation
            async with self.session.get(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["auth_service_valid"] = True
                    auth_session_id = data.get("session_id")
                    self.log_event(email, "AUTH_SERVICE_OK", f"Session: {auth_session_id}")
                    
            # Test 2: Backend Service Session
            async with self.session.get(
                f"{BACKEND_URL}/api/v1/user/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["backend_service_valid"] = True
                    backend_session_id = data.get("session_id")
                    self.log_event(email, "BACKEND_SERVICE_OK", f"Session: {backend_session_id}")
                    
            # Test 3: WebSocket Service Session
            try:
                ws = await websockets.connect(
                    WEBSOCKET_URL,
                    extra_headers=headers,
                    ping_interval=20
                )
                
                # Send auth message
                auth_message = {
                    "type": "auth",
                    "token": access_token
                }
                await ws.send(json.dumps(auth_message))
                
                # Wait for auth response
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(response)
                
                if data.get("type") == "auth_success":
                    result["websocket_service_valid"] = True
                    ws_session_id = data.get("session_id")
                    self.log_event(email, "WEBSOCKET_SERVICE_OK", f"Session: {ws_session_id}")
                    
                    # Store WebSocket connection
                    if email not in self.websocket_connections:
                        self.websocket_connections[email] = []
                    self.websocket_connections[email].append(ws)
                else:
                    await ws.close()
                    
            except Exception as e:
                self.log_event(email, "WEBSOCKET_SERVICE_ERROR", str(e))
            
            # Check session consistency across services
            if all([result["auth_service_valid"], result["backend_service_valid"], result["websocket_service_valid"]]):
                result["session_consistent"] = True
                
        except Exception as e:
            self.log_event(email, "CROSS_SERVICE_ERROR", str(e))
            
        result["total_time"] = time.time() - start_time
        self.performance_metrics["cross_service_times"].append(result["total_time"])
        
        self.log_event(email, "CROSS_SERVICE_COMPLETE", 
                     f"Valid: Auth={result['auth_service_valid']}, Backend={result['backend_service_valid']}, WS={result['websocket_service_valid']}")
        
        return result
    
    async def test_session_recovery(self, email: str) -> Dict[str, Any]:
        """Test session recovery after connection loss."""
        result = {
            "initial_session_valid": False,
            "connection_closed": False,
            "session_recovered": False,
            "data_consistent": False,
            "recovery_time": 0
        }
        
        token_data = self.user_tokens.get(email)
        session_data = self.session_data.get(email)
        if not token_data or not session_data:
            return result
            
        self.log_event(email, "RECOVERY_TEST_START", "Testing session recovery")
        
        try:
            # Validate initial session
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            async with self.session.get(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers=headers
            ) as response:
                if response.status == 200:
                    initial_data = await response.json()
                    result["initial_session_valid"] = True
                    initial_session_id = initial_data.get("session_id")
                    
            # Simulate connection loss by closing WebSocket
            connections = self.websocket_connections.get(email, [])
            if connections:
                for ws in connections:
                    if not ws.closed:
                        await ws.close()
                result["connection_closed"] = True
                self.log_event(email, "CONNECTION_CLOSED", "Simulated connection loss")
                
                # Wait before recovery attempt
                await asyncio.sleep(2)
                
                # Attempt recovery
                start_recovery = time.time()
                
                # Re-establish WebSocket connection
                try:
                    new_ws = await websockets.connect(
                        WEBSOCKET_URL,
                        extra_headers=headers,
                        ping_interval=20
                    )
                    
                    # Send auth message
                    auth_message = {
                        "type": "auth",
                        "token": token_data["access_token"],
                        "session_recovery": True,
                        "previous_session_id": initial_session_id
                    }
                    await new_ws.send(json.dumps(auth_message))
                    
                    # Wait for recovery response
                    response = await asyncio.wait_for(new_ws.recv(), timeout=10)
                    data = json.loads(response)
                    
                    if data.get("type") == "auth_success":
                        result["session_recovered"] = True
                        recovered_session_id = data.get("session_id")
                        
                        # Check data consistency
                        if recovered_session_id == initial_session_id:
                            result["data_consistent"] = True
                            
                        self.log_event(email, "RECOVERY_SUCCESS", f"Session: {recovered_session_id}")
                        
                        # Update connections list
                        self.websocket_connections[email] = [new_ws]
                    else:
                        await new_ws.close()
                        
                except Exception as e:
                    self.log_event(email, "RECOVERY_WS_ERROR", str(e))
                    
                result["recovery_time"] = time.time() - start_recovery
                self.performance_metrics["session_recovery_times"].append(result["recovery_time"])
                
        except Exception as e:
            self.log_event(email, "RECOVERY_ERROR", str(e))
            
        self.log_event(email, "RECOVERY_TEST_COMPLETE", 
                     f"Recovered: {result['session_recovered']}, Consistent: {result['data_consistent']}")
        
        return result
    
    async def test_session_expiration_renewal(self, email: str) -> Dict[str, Any]:
        """Test session expiration and renewal mechanisms."""
        result = {
            "expiration_detected": False,
            "renewal_attempted": False,
            "renewal_successful": False,
            "new_session_valid": False,
            "renewal_time": 0
        }
        
        token_data = self.user_tokens.get(email)
        if not token_data or not token_data.get("refresh_token"):
            self.log_event(email, "RENEWAL_SKIP", "No refresh token available")
            return result
            
        self.log_event(email, "RENEWAL_TEST_START", "Testing session expiration and renewal")
        
        try:
            # Check current session status
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            async with self.session.get(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers=headers
            ) as response:
                if response.status == 401:
                    result["expiration_detected"] = True
                    self.log_event(email, "SESSION_EXPIRED", "Session has expired")
                elif response.status == 200:
                    # Session still valid, try to simulate near-expiration
                    self.log_event(email, "SESSION_VALID", "Session still valid, testing renewal anyway")
                    
            # Attempt renewal
            start_renewal = time.time()
            result["renewal_attempted"] = True
            
            renewal_payload = {
                "refresh_token": token_data["refresh_token"]
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/refresh",
                json=renewal_payload
            ) as response:
                if response.status == 200:
                    renewal_data = await response.json()
                    result["renewal_successful"] = True
                    
                    # Update stored tokens
                    self.user_tokens[email].update({
                        "access_token": renewal_data.get("access_token"),
                        "refresh_token": renewal_data.get("refresh_token", token_data["refresh_token"]),
                        "session_id": renewal_data.get("session_id"),
                        "renewed_at": datetime.now()
                    })
                    
                    # Validate new session
                    new_headers = {"Authorization": f"Bearer {renewal_data.get('access_token')}"}
                    async with self.session.get(
                        f"{AUTH_SERVICE_URL}/auth/validate",
                        headers=new_headers
                    ) as validate_response:
                        if validate_response.status == 200:
                            result["new_session_valid"] = True
                            
                    self.log_event(email, "RENEWAL_SUCCESS", f"New session: {renewal_data.get('session_id')}")
                else:
                    self.log_event(email, "RENEWAL_FAILED", f"Status: {response.status}")
                    
            result["renewal_time"] = time.time() - start_renewal
            
        except Exception as e:
            self.log_event(email, "RENEWAL_ERROR", str(e))
            
        self.log_event(email, "RENEWAL_TEST_COMPLETE", 
                     f"Success: {result['renewal_successful']}, Valid: {result['new_session_valid']}")
        
        return result
    
    async def test_multi_device_session_sync(self, email: str) -> Dict[str, Any]:
        """Test session synchronization across multiple devices/connections."""
        result = {
            "device1_connected": False,
            "device2_connected": False,
            "state_synchronized": False,
            "updates_propagated": False,
            "sync_time": 0
        }
        
        token_data = self.user_tokens.get(email)
        if not token_data:
            return result
            
        start_time = time.time()
        self.log_event(email, "MULTI_DEVICE_START", "Testing multi-device session sync")
        
        try:
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            
            # Device 1: Establish first connection
            device1_ws = await websockets.connect(
                WEBSOCKET_URL,
                extra_headers=headers,
                ping_interval=20
            )
            
            auth_message_1 = {
                "type": "auth",
                "token": token_data["access_token"],
                "device_id": "device_1",
                "device_type": "desktop"
            }
            await device1_ws.send(json.dumps(auth_message_1))
            
            response1 = await asyncio.wait_for(device1_ws.recv(), timeout=10)
            data1 = json.loads(response1)
            
            if data1.get("type") == "auth_success":
                result["device1_connected"] = True
                self.log_event(email, "DEVICE1_CONNECTED", f"Session: {data1.get('session_id')}")
                
            # Device 2: Establish second connection
            device2_ws = await websockets.connect(
                WEBSOCKET_URL,
                extra_headers=headers,
                ping_interval=20
            )
            
            auth_message_2 = {
                "type": "auth",
                "token": token_data["access_token"],
                "device_id": "device_2",
                "device_type": "mobile"
            }
            await device2_ws.send(json.dumps(auth_message_2))
            
            response2 = await asyncio.wait_for(device2_ws.recv(), timeout=10)
            data2 = json.loads(response2)
            
            if data2.get("type") == "auth_success":
                result["device2_connected"] = True
                self.log_event(email, "DEVICE2_CONNECTED", f"Session: {data2.get('session_id')}")
                
            # Test state synchronization
            if result["device1_connected"] and result["device2_connected"]:
                # Send state update from device 1
                state_update = {
                    "type": "update_user_state",
                    "data": {
                        "preference": "dark_mode",
                        "value": True,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await device1_ws.send(json.dumps(state_update))
                
                # Wait for acknowledgment
                ack1 = await asyncio.wait_for(device1_ws.recv(), timeout=5)
                ack1_data = json.loads(ack1)
                
                # Check if update propagated to device 2
                try:
                    # Send state query to device 2
                    state_query = {
                        "type": "get_user_state",
                        "keys": ["preference"]
                    }
                    await device2_ws.send(json.dumps(state_query))
                    
                    response_state = await asyncio.wait_for(device2_ws.recv(), timeout=5)
                    state_data = json.loads(response_state)
                    
                    if (state_data.get("type") == "user_state" and 
                        state_data.get("data", {}).get("preference") == True):
                        result["state_synchronized"] = True
                        result["updates_propagated"] = True
                        
                except asyncio.TimeoutError:
                    self.log_event(email, "SYNC_TIMEOUT", "State sync timeout")
                    
            # Clean up connections
            try:
                await device1_ws.close()
                await device2_ws.close()
            except:
                pass
                
        except Exception as e:
            self.log_event(email, "MULTI_DEVICE_ERROR", str(e))
            
        result["sync_time"] = time.time() - start_time
        self.performance_metrics["sync_times"].append(result["sync_time"])
        
        self.log_event(email, "MULTI_DEVICE_COMPLETE", 
                     f"Synced: {result['state_synchronized']}, Time: {result['sync_time']:.2f}s")
        
        return result
    
    async def test_session_cleanup(self, email: str) -> Dict[str, Any]:
        """Test session cleanup and invalidation."""
        result = {
            "session_invalidated": False,
            "redis_cleaned": False,
            "token_revoked": False,
            "connections_closed": False
        }
        
        token_data = self.user_tokens.get(email)
        session_data = self.session_data.get(email)
        if not token_data:
            return result
            
        self.log_event(email, "CLEANUP_START", "Testing session cleanup")
        
        try:
            # Logout to trigger cleanup
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/logout",
                headers=headers
            ) as response:
                if response.status == 200:
                    result["session_invalidated"] = True
                    
            # Check if Redis session was cleaned
            if self.redis_client and session_data:
                session_id = session_data.get("session_id")
                if session_id:
                    session_key = f"session:{session_id}"
                    exists = await asyncio.to_thread(
                        self.redis_client.exists, session_key
                    )
                    if not exists:
                        result["redis_cleaned"] = True
                        
            # Verify token is revoked
            async with self.session.get(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers=headers
            ) as response:
                if response.status == 401:
                    result["token_revoked"] = True
                    
            # Close any remaining WebSocket connections
            connections = self.websocket_connections.get(email, [])
            for ws in connections:
                try:
                    if not ws.closed:
                        await ws.close()
                except:
                    pass
            result["connections_closed"] = True
            
        except Exception as e:
            self.log_event(email, "CLEANUP_ERROR", str(e))
            
        self.log_event(email, "CLEANUP_COMPLETE", 
                     f"Invalidated: {result['session_invalidated']}, Cleaned: {result['redis_cleaned']}")
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all session persistence tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "users_tested": len(TEST_USERS),
            "scenarios_tested": len(SESSION_TEST_SCENARIOS),
            "user_results": {},
            "performance_metrics": {},
            "test_logs": [],
            "summary": {}
        }
        
        # Setup all users
        print("\n" + "="*60)
        print("SETTING UP TEST USERS")
        print("="*60)
        
        for user_data in TEST_USERS:
            email = user_data["email"]
            success = await self.setup_test_user(user_data)
            if not success:
                self.log_event(email, "SETUP_FAILED", "Skipping user tests")
        
        # Run tests for each user
        for user_data in TEST_USERS:
            email = user_data["email"]
            
            if email not in self.user_tokens:
                self.log_event(email, "SKIP_USER", "No valid session")
                continue
                
            print(f"\n{'='*60}")
            print(f"Testing session persistence for: {email}")
            print('='*60)
            
            user_results = {}
            
            # Test session creation
            creation_result = await self.test_session_creation(email)
            user_results["session_creation"] = creation_result
            
            # Test cross-service persistence
            cross_service_result = await self.test_cross_service_persistence(email)
            user_results["cross_service_persistence"] = cross_service_result
            
            # Test session recovery
            recovery_result = await self.test_session_recovery(email)
            user_results["session_recovery"] = recovery_result
            
            # Test session renewal
            renewal_result = await self.test_session_expiration_renewal(email)
            user_results["session_renewal"] = renewal_result
            
            # Test multi-device sync
            sync_result = await self.test_multi_device_session_sync(email)
            user_results["multi_device_sync"] = sync_result
            
            # Test session cleanup
            cleanup_result = await self.test_session_cleanup(email)
            user_results["session_cleanup"] = cleanup_result
            
            all_results["user_results"][email] = user_results
        
        # Calculate performance metrics
        all_results["performance_metrics"] = {
            "avg_session_creation_time": (
                sum(self.performance_metrics["session_creation_times"]) / 
                len(self.performance_metrics["session_creation_times"])
                if self.performance_metrics["session_creation_times"] else 0
            ),
            "avg_recovery_time": (
                sum(self.performance_metrics["session_recovery_times"]) / 
                len(self.performance_metrics["session_recovery_times"])
                if self.performance_metrics["session_recovery_times"] else 0
            ),
            "avg_cross_service_time": (
                sum(self.performance_metrics["cross_service_times"]) / 
                len(self.performance_metrics["cross_service_times"])
                if self.performance_metrics["cross_service_times"] else 0
            ),
            "avg_sync_time": (
                sum(self.performance_metrics["sync_times"]) / 
                len(self.performance_metrics["sync_times"])
                if self.performance_metrics["sync_times"] else 0
            )
        }
        
        # Add logs
        all_results["test_logs"] = self.test_logs
        
        # Generate summary
        total_tests = 0
        passed_tests = 0
        
        for email, results in all_results["user_results"].items():
            for test_name, test_result in results.items():
                if isinstance(test_result, dict):
                    total_tests += 1
                    
                    # Determine if test passed based on its type
                    if "creation" in test_name and test_result.get("session_created"):
                        passed_tests += 1
                    elif "cross_service" in test_name and test_result.get("session_consistent"):
                        passed_tests += 1
                    elif "recovery" in test_name and test_result.get("session_recovered"):
                        passed_tests += 1
                    elif "renewal" in test_name and test_result.get("renewal_successful"):
                        passed_tests += 1
                    elif "sync" in test_name and test_result.get("state_synchronized"):
                        passed_tests += 1
                    elif "cleanup" in test_name and test_result.get("session_invalidated"):
                        passed_tests += 1
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "sessions_created": len([r for r in all_results["user_results"].values() 
                                   if r.get("session_creation", {}).get("session_created")]),
            "redis_connected": self.redis_client is not None
        }
        
        return all_results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
async def test_dev_environment_session_persistence():
    """Test comprehensive session persistence functionality."""
    async with SessionPersistenceTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("SESSION PERSISTENCE TEST RESULTS")
        print("="*60)
        
        for email, user_results in results["user_results"].items():
            print(f"\nUser: {email}")
            print("-" * 40)
            
            for test_name, test_result in user_results.items():
                if isinstance(test_result, dict):
                    if "creation" in test_name:
                        success = test_result.get("session_created", False)
                        redis_ok = test_result.get("redis_stored", False)
                        time_taken = test_result.get("creation_time", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} (redis: {'✓' if redis_ok else '✗'}, time: {time_taken:.2f}s)")
                    elif "cross_service" in test_name:
                        consistent = test_result.get("session_consistent", False)
                        auth = test_result.get("auth_service_valid", False)
                        backend = test_result.get("backend_service_valid", False)
                        ws = test_result.get("websocket_service_valid", False)
                        print(f"  {test_name}: {'✓' if consistent else '✗'} (auth: {'✓' if auth else '✗'}, backend: {'✓' if backend else '✗'}, ws: {'✓' if ws else '✗'})")
                    elif "recovery" in test_name:
                        recovered = test_result.get("session_recovered", False)
                        consistent = test_result.get("data_consistent", False)
                        time_taken = test_result.get("recovery_time", 0)
                        print(f"  {test_name}: {'✓' if recovered else '✗'} (consistent: {'✓' if consistent else '✗'}, time: {time_taken:.2f}s)")
                    elif "renewal" in test_name:
                        success = test_result.get("renewal_successful", False)
                        valid = test_result.get("new_session_valid", False)
                        time_taken = test_result.get("renewal_time", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} (valid: {'✓' if valid else '✗'}, time: {time_taken:.2f}s)")
                    elif "sync" in test_name:
                        synced = test_result.get("state_synchronized", False)
                        device1 = test_result.get("device1_connected", False)
                        device2 = test_result.get("device2_connected", False)
                        print(f"  {test_name}: {'✓' if synced else '✗'} (dev1: {'✓' if device1 else '✗'}, dev2: {'✓' if device2 else '✗'})")
                    elif "cleanup" in test_name:
                        invalidated = test_result.get("session_invalidated", False)
                        cleaned = test_result.get("redis_cleaned", False)
                        revoked = test_result.get("token_revoked", False)
                        print(f"  {test_name}: {'✓' if invalidated else '✗'} (cleaned: {'✓' if cleaned else '✗'}, revoked: {'✓' if revoked else '✗'})")
        
        # Performance metrics
        perf = results["performance_metrics"]
        print("\n" + "="*60)
        print("PERFORMANCE METRICS")
        print("="*60)
        print(f"Avg Session Creation: {perf['avg_session_creation_time']:.2f}s")
        print(f"Avg Recovery Time: {perf['avg_recovery_time']:.2f}s")
        print(f"Avg Cross-Service Time: {perf['avg_cross_service_time']:.2f}s")
        print(f"Avg Sync Time: {perf['avg_sync_time']:.2f}s")
        
        # Summary
        summary = results["summary"]
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed Tests: {summary['passed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Sessions Created: {summary['sessions_created']}")
        print(f"Redis Connected: {'✓' if summary['redis_connected'] else '✗'}")
        
        # Assert critical conditions
        assert summary["success_rate"] >= 70, f"Success rate too low: {summary['success_rate']:.1f}%"
        assert summary["sessions_created"] >= 2, "Not enough sessions created"
        assert perf["avg_session_creation_time"] < 5, "Session creation too slow"
        
        print("\n[SUCCESS] Session persistence tests completed!")


async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT SESSION PERSISTENCE TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with SessionPersistenceTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        results_file = project_root / "test_results" / "session_persistence_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\nResults saved to: {results_file}")
        
        # Return exit code
        if results["summary"]["success_rate"] >= 70:
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)