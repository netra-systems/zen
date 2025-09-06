#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment Concurrent Users

Tests multiple concurrent user flows, isolation, and resource management:
    1. Concurrent user registration and login
2. Simultaneous thread creation and management
3. Parallel agent interactions
4. Resource isolation between users
5. Memory and connection management
6. Performance under concurrent load
7. Data consistency across users
8. Rate limiting and fair resource allocation

BVJ:
    - Segment: Early, Mid, Enterprise
- Business Goal: Scalability, Platform Stability
- Value Impact: Platform capability to serve multiple users simultaneously
- Strategic Impact: Foundation for enterprise adoption and revenue scaling
""""

# Test framework import - using pytest fixtures instead

import asyncio
import concurrent.futures
import json
import os
import random
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import psutil
import pytest
import websockets

# Service URLs
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"

# Concurrent test configurations
CONCURRENT_USER_COUNT = 10
CONCURRENT_THREAD_COUNT = 5
CONCURRENT_MESSAGE_COUNT = 3

# Test user template
USER_TEMPLATE = {
    "password": "SecurePass123!",
    "name_template": "Concurrent User {}",
    "tiers": ["free", "early", "mid", "enterprise"]
}

CONCURRENT_SCENARIOS = [
    {
        "name": "simultaneous_registration",
        "description": "Test simultaneous user registration",
        "user_count": 5,
        "operations": ["register"]
    },
    {
        "name": "concurrent_login",
        "description": "Test concurrent user login",
        "user_count": 8,
        "operations": ["login"]
    },
    {
        "name": "parallel_thread_creation",
        "description": "Test parallel thread creation across users",
        "user_count": 6,
        "operations": ["create_thread"]
    },
    {
        "name": "simultaneous_messaging",
        "description": "Test simultaneous messaging from multiple users",
        "user_count": 10,
        "operations": ["send_message"]
    },
    {
        "name": "mixed_operations",
        "description": "Test mixed operations from multiple users",
        "user_count": 8,
        "operations": ["login", "create_thread", "send_message", "get_profile"]
    }
]

class ConcurrentUserTester:
    """Test concurrent user functionality and isolation."""
    
    def __init__(self):
        self.sessions: Dict[str, aiohttp.ClientSession] = {]
        self.user_tokens: Dict[str, str] = {]
        self.websocket_connections: Dict[str, Any] = {]
        self.user_threads: Dict[str, List[str]] = {]
        self.test_results: Dict[str, Any] = {]
        self.performance_metrics: Dict[str, List[float]] = {
            "registration_times": [],
            "login_times": [],
            "thread_creation_times": [],
            "message_send_times": [],
            "concurrent_operation_times": []
        }
        self.resource_metrics: Dict[str, List[float]] = {
            "memory_usage": [],
            "cpu_usage": [],
            "connection_counts": []
        }
        self.test_logs: List[str] = []
        self.isolation_violations: List[Dict[str, Any]] = []
        
    async def __aenter__(self):
        """Setup test environment."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        # Close all WebSocket connections
        for email, ws in self.websocket_connections.items():
            try:
                if ws and not ws.closed:
                    await ws.close()
            except:
                pass
                
        # Close all HTTP sessions
        for email, session in self.sessions.items():
            try:
                await session.close()
            except:
                pass
    
    def log_event(self, user: str, event: str, details: str = ""):
        """Log test events for analysis."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp]] [{user]] {event]"
        if details:
            log_entry += f" - {details}"
        self.test_logs.append(log_entry)
        print(log_entry)
    
    def generate_test_users(self, count: int) -> List[Dict[str, Any]]:
        """Generate test users for concurrent testing."""
        users = []
        for i in range(count):
            user = {
                "email": f"concurrent_test_{i+1}@example.com",
                "password": USER_TEMPLATE["password"],
                "name": USER_TEMPLATE["name_template"].format(i+1),
                "tier": random.choice(USER_TEMPLATE["tiers"]),
                "user_id": i+1
            }
            users.append(user)
        return users
    
    def capture_resource_metrics(self):
        """Capture current system resource usage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            self.resource_metrics["memory_usage"].append(memory_info.rss / 1024 / 1024)  # MB
            self.resource_metrics["cpu_usage"].append(cpu_percent)
            self.resource_metrics["connection_counts"].append(len(self.websocket_connections))
            
        except Exception as e:
            self.log_event("SYSTEM", "RESOURCE_CAPTURE_ERROR", str(e))
    
    async def register_user_concurrent(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a single user with performance tracking."""
        email = user_data["email"]
        result = {
            "success": False,
            "registration_time": 0,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            # Create dedicated session for this user
            timeout = aiohttp.ClientTimeout(total=30)
            session = aiohttp.ClientSession(timeout=timeout)
            self.sessions[email] = session
            
            register_payload = {
                "email": email,
                "password": user_data["password"],
                "name": user_data["name"],
                "tier": user_data.get("tier", "free")
            }
            
            async with session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_payload
            ) as response:
                if response.status in [200, 201, 409]:  # Include 409 for existing users
                    result["success"] = True
                    self.log_event(email, "REGISTRATION_SUCCESS", f"Status: {response.status}")
                else:
                    result["error"] = f"Status: {response.status]"
                    self.log_event(email, "REGISTRATION_FAILED", result["error"])
                    
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "REGISTRATION_ERROR", str(e))
            
        result["registration_time"] = time.time() - start_time
        self.performance_metrics["registration_times"].append(result["registration_time"])
        
        return result
    
    async def login_user_concurrent(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Login a single user with performance tracking."""
        email = user_data["email"]
        result = {
            "success": False,
            "login_time": 0,
            "token": None,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            session = self.sessions.get(email)
            if not session:
                result["error"] = "No session available"
                return result
                
            login_payload = {
                "email": email,
                "password": user_data["password"]
            }
            
            async with session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["success"] = True
                    result["token"] = data.get("access_token")
                    self.user_tokens[email] = result["token"]
                    self.log_event(email, "LOGIN_SUCCESS", "Token obtained")
                else:
                    result["error"] = f"Status: {response.status]"
                    self.log_event(email, "LOGIN_FAILED", result["error"])
                    
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "LOGIN_ERROR", str(e))
            
        result["login_time"] = time.time() - start_time
        self.performance_metrics["login_times"].append(result["login_time"])
        
        return result
    
    async def establish_websocket_concurrent(self, email: str) -> Dict[str, Any]:
        """Establish WebSocket connection with performance tracking."""
        result = {
            "success": False,
            "connection_time": 0,
            "session_id": None,
            "error": None
        }
        
        if email not in self.user_tokens:
            result["error"] = "No auth token"
            return result
            
        start_time = time.time()
        
        try:
            headers = {"Authorization": f"Bearer {self.user_tokens[email]]"]
            
            ws = await websockets.connect(
                WEBSOCKET_URL,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Send auth message
            auth_message = {
                "type": "auth",
                "token": self.user_tokens[email],
                "user_agent": f"ConcurrentTest_{email}"
            }
            await ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("type") == "auth_success":
                result["success"] = True
                result["session_id"] = data.get("session_id")
                self.websocket_connections[email] = ws
                self.user_threads[email] = []
                self.log_event(email, "WS_CONNECT_SUCCESS", f"Session: {result['session_id']]")
            else:
                result["error"] = str(data)
                await ws.close()
                
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "WS_CONNECT_ERROR", str(e))
            
        result["connection_time"] = time.time() - start_time
        return result
    
    async def create_thread_concurrent(self, email: str, thread_index: int) -> Dict[str, Any]:
        """Create a thread for a user with performance tracking."""
        result = {
            "success": False,
            "thread_id": None,
            "creation_time": 0,
            "error": None
        }
        
        ws = self.websocket_connections.get(email)
        if not ws:
            result["error"] = "No WebSocket connection"
            return result
            
        start_time = time.time()
        
        try:
            create_message = {
                "type": "thread_create",
                "data": {
                    "title": f"Concurrent Thread {thread_index} for {email}",
                    "description": f"Testing concurrent thread creation #{thread_index}",
                    "initial_message": f"This is concurrent thread #{thread_index}",
                    "metadata": {
                        "concurrent_test": True,
                        "thread_index": thread_index,
                        "user": email,
                        "created_at": datetime.now().isoformat()
                    }
                }
            }
            
            await ws.send(json.dumps(create_message))
            response = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(response)
            
            if data.get("type") == "thread_created":
                result["success"] = True
                result["thread_id"] = data.get("thread_id")
                self.user_threads[email].append(result["thread_id"])
                self.log_event(email, "THREAD_CREATED", f"ID: {result['thread_id']]")
            else:
                result["error"] = str(data)
                
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "THREAD_CREATE_ERROR", str(e))
            
        result["creation_time"] = time.time() - start_time
        self.performance_metrics["thread_creation_times"].append(result["creation_time"])
        
        return result
    
    async def send_message_concurrent(self, email: str, thread_id: str, message_index: int) -> Dict[str, Any]:
        """Send a message with performance tracking."""
        result = {
            "success": False,
            "message_time": 0,
            "response_received": False,
            "error": None
        }
        
        ws = self.websocket_connections.get(email)
        if not ws or not thread_id:
            result["error"] = "No WebSocket connection or thread"
            return result
            
        start_time = time.time()
        
        try:
            message_payload = {
                "type": "send_message",
                "thread_id": thread_id,
                "message": {
                    "content": f"Concurrent message #{message_index} from {email}: What is the current time?",
                    "type": "user",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "concurrent_test": True,
                        "message_index": message_index,
                        "user": email
                    }
                }
            }
            
            await ws.send(json.dumps(message_payload))
            
            # Wait for agent response (with timeout)
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=20)
                data = json.loads(response)
                
                if data.get("type") in ["agent_response", "agent_response_complete"]:
                    result["response_received"] = True
                    result["success"] = True
                    self.log_event(email, "MESSAGE_RESPONSE", f"Message {message_index} responded")
                    
            except asyncio.TimeoutError:
                self.log_event(email, "MESSAGE_TIMEOUT", f"Message {message_index} timeout")
                
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "MESSAGE_ERROR", str(e))
            
        result["message_time"] = time.time() - start_time
        self.performance_metrics["message_send_times"].append(result["message_time"])
        
        return result
    
    async def get_user_profile_concurrent(self, email: str) -> Dict[str, Any]:
        """Get user profile with performance tracking."""
        result = {
            "success": False,
            "response_time": 0,
            "profile_data": None,
            "error": None
        }
        
        session = self.sessions.get(email)
        token = self.user_tokens.get(email)
        if not session or not token:
            result["error"] = "No session or token"
            return result
            
        start_time = time.time()
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            async with session.get(
                f"{BACKEND_URL}/api/user/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["success"] = True
                    result["profile_data"] = data
                    self.log_event(email, "PROFILE_SUCCESS", "Profile retrieved")
                else:
                    result["error"] = f"Status: {response.status]"
                    
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "PROFILE_ERROR", str(e))
            
        result["response_time"] = time.time() - start_time
        return result
    
    @pytest.mark.asyncio
    async def test_user_isolation(self, users: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test that users are properly isolated from each other."""
        result = {
            "isolation_violations": 0,
            "cross_user_access_attempts": 0,
            "data_leakage_detected": False,
            "isolation_score": 1.0
        }
        
        self.log_event("SYSTEM", "ISOLATION_TEST", f"Testing isolation for {len(users)} users")
        
        try:
            # Test 1: Try to access other users' threads
            for i, user1 in enumerate(users):
                email1 = user1["email"]
                session1 = self.sessions.get(email1)
                token1 = self.user_tokens.get(email1)
                
                if not session1 or not token1:
                    continue
                    
                for j, user2 in enumerate(users):
                    if i == j:
                        continue
                        
                    email2 = user2["email"]
                    user2_threads = self.user_threads.get(email2, [])
                    
                    for thread_id in user2_threads:
                        # Try to access user2's thread from user1's session
                        result["cross_user_access_attempts"] += 1
                        
                        try:
                            headers = {"Authorization": f"Bearer {token1}"}
                            async with session1.get(
                                f"{BACKEND_URL}/api/threads/{thread_id}",
                                headers=headers
                            ) as response:
                                if response.status == 200:
                                    # This is a violation - user1 accessed user2's thread
                                    violation = {
                                        "type": "cross_user_thread_access",
                                        "accessor": email1,
                                        "target": email2,
                                        "thread_id": thread_id,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    self.isolation_violations.append(violation)
                                    result["isolation_violations"] += 1
                                    result["data_leakage_detected"] = True
                                    
                                    self.log_event("ISOLATION", "VIOLATION_DETECTED", 
                                                 f"{email1} accessed {email2}'s thread {thread_id}")
                                    
                        except Exception:
                            # Expected behavior - access should be denied
                            pass
            
            # Test 2: Check WebSocket message isolation
            await self._test_websocket_isolation(users, result)
            
            # Calculate isolation score
            if result["cross_user_access_attempts"] > 0:
                result["isolation_score"] = 1.0 - (result["isolation_violations"] / result["cross_user_access_attempts"])
            
        except Exception as e:
            self.log_event("ISOLATION", "TEST_ERROR", str(e))
            
        return result
    
    async def _test_websocket_isolation(self, users: List[Dict[str, Any]], result: Dict[str, Any]):
        """Test WebSocket message isolation between users."""
        # Send messages and ensure they don't cross users
        for user in users:
            email = user["email"]
            ws = self.websocket_connections.get(email)
            threads = self.user_threads.get(email, [])
            
            if not ws or not threads:
                continue
                
            # Send a message with user-specific content
            unique_content = f"ISOLATION_TEST_{email}_{uuid.uuid4()}"
            
            try:
                message = {
                    "type": "send_message",
                    "thread_id": threads[0],
                    "message": {
                        "content": unique_content,
                        "type": "user",
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await ws.send(json.dumps(message))
                
                # Check if other users receive this message (they shouldn't)
                for other_user in users:
                    if other_user["email"] == email:
                        continue
                        
                    other_ws = self.websocket_connections.get(other_user["email"])
                    if not other_ws:
                        continue
                        
                    try:
                        # Check for unexpected messages (with short timeout)
                        response = await asyncio.wait_for(other_ws.recv(), timeout=1)
                        data = json.loads(response)
                        
                        # Check if the response contains content from another user
                        response_content = str(data)
                        if unique_content in response_content:
                            violation = {
                                "type": "websocket_message_leakage",
                                "sender": email,
                                "receiver": other_user["email"],
                                "content": unique_content,
                                "timestamp": datetime.now().isoformat()
                            }
                            self.isolation_violations.append(violation)
                            result["isolation_violations"] += 1
                            result["data_leakage_detected"] = True
                            
                    except asyncio.TimeoutError:
                        # Expected - no message should be received
                        pass
                        
            except Exception as e:
                self.log_event(email, "ISOLATION_MESSAGE_ERROR", str(e))
    
    @pytest.mark.asyncio
    async def test_concurrent_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test a specific concurrent scenario."""
        scenario_name = scenario["name"]
        user_count = scenario["user_count"]
        operations = scenario["operations"]
        
        result = {
            "scenario_name": scenario_name,
            "users_processed": 0,
            "operations_completed": 0,
            "total_operations": 0,
            "success_rate": 0,
            "avg_operation_time": 0,
            "concurrent_time": 0,
            "operation_results": {}
        }
        
        self.log_event("SCENARIO", f"START_{scenario_name.upper()}", f"Testing {user_count} users")
        
        # Generate users for this scenario
        users = self.generate_test_users(user_count)
        start_time = time.time()
        
        try:
            # Capture initial resource metrics
            self.capture_resource_metrics()
            
            # Phase 1: Setup users (registration)
            if "register" in operations:
                registration_tasks = [self.register_user_concurrent(user) for user in users]
                registration_results = await asyncio.gather(*registration_tasks)
                
                successful_registrations = sum(1 for r in registration_results if r["success"])
                result["operation_results"]["registration"] = {
                    "attempted": len(users),
                    "successful": successful_registrations,
                    "success_rate": successful_registrations / len(users) * 100
                }
            
            # Phase 2: Login users
            if "login" in operations:
                login_tasks = [self.login_user_concurrent(user) for user in users]
                login_results = await asyncio.gather(*login_tasks)
                
                successful_logins = sum(1 for r in login_results if r["success"])
                result["operation_results"]["login"] = {
                    "attempted": len(users),
                    "successful": successful_logins,
                    "success_rate": successful_logins / len(users) * 100
                }
                result["users_processed"] = successful_logins
            
            # Phase 3: Establish WebSocket connections
            websocket_tasks = [self.establish_websocket_concurrent(user["email"]) for user in users]
            websocket_results = await asyncio.gather(*websocket_tasks)
            
            successful_connections = sum(1 for r in websocket_results if r["success"])
            
            # Phase 4: Execute scenario-specific operations
            if "create_thread" in operations:
                thread_tasks = []
                for user in users:
                    email = user["email"]
                    if email in self.websocket_connections:
                        for i in range(CONCURRENT_THREAD_COUNT):
                            task = self.create_thread_concurrent(email, i)
                            thread_tasks.append(task)
                
                thread_results = await asyncio.gather(*thread_tasks)
                successful_threads = sum(1 for r in thread_results if r["success"])
                
                result["operation_results"]["thread_creation"] = {
                    "attempted": len(thread_tasks),
                    "successful": successful_threads,
                    "success_rate": successful_threads / len(thread_tasks) * 100 if thread_tasks else 0
                }
                result["operations_completed"] += successful_threads
                result["total_operations"] += len(thread_tasks)
            
            if "send_message" in operations:
                message_tasks = []
                for user in users:
                    email = user["email"]
                    threads = self.user_threads.get(email, [])
                    for thread_id in threads[:1]:  # Use first thread only
                        for i in range(CONCURRENT_MESSAGE_COUNT):
                            task = self.send_message_concurrent(email, thread_id, i)
                            message_tasks.append(task)
                
                message_results = await asyncio.gather(*message_tasks)
                successful_messages = sum(1 for r in message_results if r["success"])
                
                result["operation_results"]["messaging"] = {
                    "attempted": len(message_tasks),
                    "successful": successful_messages,
                    "success_rate": successful_messages / len(message_tasks) * 100 if message_tasks else 0
                }
                result["operations_completed"] += successful_messages
                result["total_operations"] += len(message_tasks)
            
            if "get_profile" in operations:
                profile_tasks = [self.get_user_profile_concurrent(user["email"]) for user in users]
                profile_results = await asyncio.gather(*profile_tasks)
                
                successful_profiles = sum(1 for r in profile_results if r["success"])
                
                result["operation_results"]["profile_access"] = {
                    "attempted": len(profile_tasks),
                    "successful": successful_profiles,
                    "success_rate": successful_profiles / len(profile_tasks) * 100
                }
                result["operations_completed"] += successful_profiles
                result["total_operations"] += len(profile_tasks)
            
            # Test user isolation
            isolation_result = await self.test_user_isolation(users)
            result["isolation_result"] = isolation_result
            
            # Capture final resource metrics
            self.capture_resource_metrics()
            
        except Exception as e:
            self.log_event("SCENARIO", f"ERROR_{scenario_name.upper()}", str(e))
            
        result["concurrent_time"] = time.time() - start_time
        
        # Calculate overall success rate
        if result["total_operations"] > 0:
            result["success_rate"] = result["operations_completed"] / result["total_operations"] * 100
            
        self.log_event("SCENARIO", f"COMPLETE_{scenario_name.upper()}", 
                     f"Success: {result['success_rate']:.1f]%, Time: {result['concurrent_time']:.2f]s")
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all concurrent user tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "scenarios_tested": len(CONCURRENT_SCENARIOS),
            "scenario_results": {},
            "performance_metrics": {},
            "resource_metrics": {},
            "isolation_violations": [],
            "test_logs": [],
            "summary": {}
        }
        
        print("\n" + "="*60)
        print("CONCURRENT USER TESTING")
        print("="*60)
        
        # Run each concurrent scenario
        for scenario in CONCURRENT_SCENARIOS:
            print(f"\n{'-'*40}")
            print(f"Running scenario: {scenario['name']]")
            print(f"Description: {scenario['description']]")
            print(f"{'-'*40}")
            
            scenario_result = await self.test_concurrent_scenario(scenario)
            all_results["scenario_results"][scenario["name"]] = scenario_result
            
            # Brief pause between scenarios
            await asyncio.sleep(2)
        
        # Calculate performance metrics
        all_results["performance_metrics"] = {
            "avg_registration_time": (
                sum(self.performance_metrics["registration_times"]) / 
                len(self.performance_metrics["registration_times"])
                if self.performance_metrics["registration_times"] else 0
            ),
            "avg_login_time": (
                sum(self.performance_metrics["login_times"]) / 
                len(self.performance_metrics["login_times"])
                if self.performance_metrics["login_times"] else 0
            ),
            "avg_thread_creation_time": (
                sum(self.performance_metrics["thread_creation_times"]) / 
                len(self.performance_metrics["thread_creation_times"])
                if self.performance_metrics["thread_creation_times"] else 0
            ),
            "avg_message_time": (
                sum(self.performance_metrics["message_send_times"]) / 
                len(self.performance_metrics["message_send_times"])
                if self.performance_metrics["message_send_times"] else 0
            ),
            "total_operations": sum(len(times) for times in self.performance_metrics.values())
        }
        
        # Calculate resource metrics
        all_results["resource_metrics"] = {
            "peak_memory_mb": max(self.resource_metrics["memory_usage"]) if self.resource_metrics["memory_usage"] else 0,
            "avg_memory_mb": (
                sum(self.resource_metrics["memory_usage"]) / 
                len(self.resource_metrics["memory_usage"])
                if self.resource_metrics["memory_usage"] else 0
            ),
            "peak_cpu_percent": max(self.resource_metrics["cpu_usage"]) if self.resource_metrics["cpu_usage"] else 0,
            "max_connections": max(self.resource_metrics["connection_counts"]) if self.resource_metrics["connection_counts"] else 0
        }
        
        # Add isolation violations
        all_results["isolation_violations"] = self.isolation_violations
        
        # Add logs
        all_results["test_logs"] = self.test_logs
        
        # Generate summary
        total_scenarios = len(CONCURRENT_SCENARIOS)
        successful_scenarios = sum(
            1 for result in all_results["scenario_results"].values()
            if result.get("success_rate", 0) >= 70
        )
        
        total_isolation_violations = len(self.isolation_violations)
        
        all_results["summary"] = {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "scenario_success_rate": (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0,
            "total_operations": all_results["performance_metrics"]["total_operations"],
            "isolation_violations": total_isolation_violations,
            "isolation_score": 1.0 - (total_isolation_violations / max(100, all_results["performance_metrics"]["total_operations"])),
            "resource_efficiency": "good" if all_results["resource_metrics"]["peak_memory_mb"] < 1000 else "concerning"
        }
        
        return all_results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
@pytest.mark.asyncio
async def test_dev_environment_concurrent_users():
    """Test comprehensive concurrent user functionality."""
    async with ConcurrentUserTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("CONCURRENT USER TEST RESULTS")
        print("="*60)
        
        for scenario_name, scenario_result in results["scenario_results"].items():
            print(f"\nScenario: {scenario_name}")
            print("-" * 40)
            print(f"  Users Processed: {scenario_result.get('users_processed', 0)}")
            print(f"  Operations Completed: {scenario_result.get('operations_completed', 0)}")
            print(f"  Success Rate: {scenario_result.get('success_rate', 0):.1f}%")
            print(f"  Concurrent Time: {scenario_result.get('concurrent_time', 0):.2f}s")
            
            # Show operation-specific results
            for op_name, op_result in scenario_result.get("operation_results", {}).items():
                success_rate = op_result.get("success_rate", 0)
                attempted = op_result.get("attempted", 0)
                successful = op_result.get("successful", 0)
                print(f"    {op_name}: {successful}/{attempted} ({success_rate:.1f}%)")
            
            # Show isolation results
            isolation = scenario_result.get("isolation_result", {})
            violations = isolation.get("isolation_violations", 0)
            score = isolation.get("isolation_score", 1.0)
            print(f"    Isolation: {score:.2f} score ({violations} violations)")
        
        # Performance metrics
        perf = results["performance_metrics"]
        print("\n" + "="*60)
        print("PERFORMANCE METRICS")
        print("="*60)
        print(f"Avg Registration Time: {perf['avg_registration_time']:.2f]s")
        print(f"Avg Login Time: {perf['avg_login_time']:.2f]s")
        print(f"Avg Thread Creation: {perf['avg_thread_creation_time']:.2f]s")
        print(f"Avg Message Time: {perf['avg_message_time']:.2f]s")
        print(f"Total Operations: {perf['total_operations']]")
        
        # Resource metrics
        resources = results["resource_metrics"]
        print("\n" + "="*60)
        print("RESOURCE METRICS")
        print("="*60)
        print(f"Peak Memory: {resources['peak_memory_mb']:.1f] MB")
        print(f"Avg Memory: {resources['avg_memory_mb']:.1f] MB")
        print(f"Peak CPU: {resources['peak_cpu_percent']:.1f]%")
        print(f"Max Connections: {resources['max_connections']]")
        
        # Summary
        summary = results["summary"]
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Scenarios: {summary['successful_scenarios']]/{summary['total_scenarios']]")
        print(f"Scenario Success Rate: {summary['scenario_success_rate']:.1f]%")
        print(f"Total Operations: {summary['total_operations']]")
        print(f"Isolation Violations: {summary['isolation_violations']]")
        print(f"Isolation Score: {summary['isolation_score']:.2f]")
        print(f"Resource Efficiency: {summary['resource_efficiency']]")
        
        # Assert critical conditions
        assert summary["scenario_success_rate"] >= 70, f"Scenario success rate too low: {summary['scenario_success_rate']:.1f]%"
        assert summary["isolation_score"] >= 0.9, f"Isolation score too low: {summary['isolation_score']:.2f]"
        assert resources["peak_memory_mb"] < 2000, f"Memory usage too high: {resources['peak_memory_mb']:.1f] MB"
        assert perf["avg_login_time"] < 5, "Login time too slow under concurrent load"
        
        print("\n[SUCCESS] Concurrent user tests completed!")

async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT CONCURRENT USERS TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with ConcurrentUserTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        results_file = project_root / "test_results" / "concurrent_users_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\nResults saved to: {results_file}")
        
        # Return exit code
        if results["summary"]["scenario_success_rate"] >= 70:
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)