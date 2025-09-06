#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment Chat Thread Initialization

Tests comprehensive chat thread creation and initialization flow:
    1. Thread creation with proper metadata
2. Context loading and agent assignment
3. Thread state persistence
4. Thread validation and constraints
5. Multi-thread management
6. Thread archival and cleanup
7. Performance under load
8. Error handling and recovery

BVJ:
    - Segment: Free, Early, Mid, Enterprise
- Business Goal: Conversion, Retention
- Value Impact: Core chat functionality enabling AI agent interactions
- Strategic Impact: Foundation for all user-agent conversations and value delivery
""""

# Test framework import - using pytest fixtures instead

import asyncio
import concurrent.futures
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import aiohttp
import pytest
import websockets

# Service URLs
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"

# Test configurations
TEST_USERS = [
    {
        "email": "chat_test_1@example.com",
        "password": "SecurePass123!",
        "name": "Chat Test User 1",
        "tier": "free"
    },
    {
        "email": "chat_test_2@example.com",
        "password": "SecurePass456!",
        "name": "Chat Test User 2",
        "tier": "early"
    },
    {
        "email": "chat_test_3@example.com",
        "password": "SecurePass789!",
        "name": "Chat Test User 3",
        "tier": "enterprise"
    }
]

THREAD_TEST_CASES = [
    {
        "title": "Simple Query Thread",
        "description": "Basic question-answer thread",
        "initial_message": "What is Python?",
        "expected_agent_type": "general",
        "context_requirements": ["basic"]
    },
    {
        "title": "Code Analysis Thread",
        "description": "Code review and analysis",
        "initial_message": "Review this Python function for optimization",
        "expected_agent_type": "code_reviewer",
        "context_requirements": ["code", "analysis"]
    },
    {
        "title": "Long Context Thread",
        "description": "Thread with extensive context requirements",
        "initial_message": "Analyze the entire codebase architecture",
        "expected_agent_type": "architect",
        "context_requirements": ["full_codebase", "documentation", "specs"]
    },
    {
        "title": "Multi-Modal Thread",
        "description": "Thread requiring multiple agent types",
        "initial_message": "Create a full-stack feature with frontend and backend",
        "expected_agent_type": "coordinator",
        "context_requirements": ["frontend", "backend", "database"]
    }
]

class ChatInitializationTester:
    """Test comprehensive chat thread initialization flows."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_tokens: Dict[str, str] = {]
        self.websocket_connections: Dict[str, Any] = {]
        self.created_threads: List[Dict[str, Any]] = []
        self.test_logs: List[str] = []
        self.performance_metrics: Dict[str, List[float]] = {
            "thread_creation_times": [],
            "context_loading_times": [],
            "agent_assignment_times": []
        }
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
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
                
        if self.session:
            await self.session.close()
    
    def log_event(self, user: str, event: str, details: str = ""):
        """Log test events for analysis."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp]] [{user]] {event]"
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
            
            # Login user
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
                    self.user_tokens[email] = data.get("access_token")
                    self.log_event(email, "LOGIN_SUCCESS", "Token obtained")
                    return True
                else:
                    self.log_event(email, "LOGIN_FAILED", f"Status: {response.status}")
                    return False
                    
        except Exception as e:
            self.log_event(email, "SETUP_ERROR", str(e))
            return False
    
    async def establish_websocket_connection(self, email: str) -> bool:
        """Establish authenticated WebSocket connection."""
        if email not in self.user_tokens:
            self.log_event(email, "WS_CONNECT_SKIP", "No auth token")
            return False
            
        self.log_event(email, "WS_CONNECT_START", "Establishing WebSocket connection")
        
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
                "token": self.user_tokens[email]
            }
            await ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("type") == "auth_success":
                self.websocket_connections[email] = ws
                self.log_event(email, "WS_CONNECT_SUCCESS", f"Session: {data.get('session_id', 'unknown')}")
                return True
            else:
                self.log_event(email, "WS_AUTH_FAILED", str(data))
                await ws.close()
                return False
                
        except Exception as e:
            self.log_event(email, "WS_CONNECT_ERROR", str(e))
            return False
    
    @pytest.mark.asyncio
    async def test_basic_thread_creation(self, email: str, thread_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test basic thread creation functionality."""
        result = {
            "thread_created": False,
            "thread_id": None,
            "creation_time": 0,
            "metadata_valid": False,
            "agent_assigned": False,
            "context_loaded": False
        }
        
        ws = self.websocket_connections.get(email)
        if not ws:
            self.log_event(email, "THREAD_CREATE_SKIP", "No WebSocket connection")
            return result
            
        start_time = time.time()
        
        self.log_event(email, "THREAD_CREATE_START", f"Creating: {thread_case['title']]")
        
        try:
            # Create thread
            create_message = {
                "type": "thread_create",
                "data": {
                    "title": thread_case["title"],
                    "description": thread_case["description"],
                    "initial_message": thread_case["initial_message"],
                    "context_requirements": thread_case.get("context_requirements", []),
                    "agent_preferences": {
                        "type": thread_case.get("expected_agent_type", "general"),
                        "capabilities": thread_case.get("required_capabilities", [])
                    },
                    "metadata": {
                        "test_case": True,
                        "test_timestamp": datetime.now().isoformat(),
                        "test_user": email
                    }
                }
            }
            
            await ws.send(json.dumps(create_message))
            
            # Wait for thread creation response
            response = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(response)
            
            creation_time = time.time() - start_time
            result["creation_time"] = creation_time
            self.performance_metrics["thread_creation_times"].append(creation_time)
            
            if data.get("type") == "thread_created":
                result["thread_created"] = True
                result["thread_id"] = data.get("thread_id")
                
                # Validate metadata
                thread_data = data.get("thread", {})
                if (thread_data.get("title") == thread_case["title"] and
                    thread_data.get("description") == thread_case["description"]):
                        result["metadata_valid"] = True
                
                # Check agent assignment
                if thread_data.get("assigned_agent"):
                    result["agent_assigned"] = True
                    
                # Check context loading
                if thread_data.get("context_status") in ["loaded", "loading"]:
                    result["context_loaded"] = True
                
                # Store for cleanup
                self.created_threads.append({
                    "thread_id": result["thread_id"],
                    "user": email,
                    "created_at": datetime.now()
                })
                
                self.log_event(email, "THREAD_CREATE_SUCCESS", 
                             f"ID: {result['thread_id']], Time: {creation_time:.2f]s")
                
            elif data.get("type") == "error":
                self.log_event(email, "THREAD_CREATE_ERROR", data.get("message", "Unknown error"))
                
        except asyncio.TimeoutError:
            self.log_event(email, "THREAD_CREATE_TIMEOUT", f"After {time.time() - start_time:.2f}s")
        except Exception as e:
            self.log_event(email, "THREAD_CREATE_EXCEPTION", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_context_loading(self, email: str, thread_id: str, context_requirements: List[str]) -> Dict[str, Any]:
        """Test context loading for a thread."""
        result = {
            "context_loading_started": False,
            "context_loaded": False,
            "loading_time": 0,
            "context_size": 0,
            "context_types": []
        }
        
        ws = self.websocket_connections.get(email)
        if not ws or not thread_id:
            return result
            
        start_time = time.time()
        
        self.log_event(email, "CONTEXT_LOAD_START", f"Thread: {thread_id}, Requirements: {context_requirements}")
        
        try:
            # Request context loading
            context_message = {
                "type": "load_context",
                "thread_id": thread_id,
                "context_requirements": context_requirements,
                "priority": "high"
            }
            
            await ws.send(json.dumps(context_message))
            
            # Wait for context loading response
            timeout = 30  # Longer timeout for context loading
            response = await asyncio.wait_for(ws.recv(), timeout=timeout)
            data = json.loads(response)
            
            loading_time = time.time() - start_time
            result["loading_time"] = loading_time
            self.performance_metrics["context_loading_times"].append(loading_time)
            
            if data.get("type") == "context_loaded":
                result["context_loading_started"] = True
                result["context_loaded"] = True
                
                context_data = data.get("context", {})
                result["context_size"] = context_data.get("size", 0)
                result["context_types"] = context_data.get("types", [])
                
                self.log_event(email, "CONTEXT_LOAD_SUCCESS", 
                             f"Size: {result['context_size']], Time: {loading_time:.2f]s")
                
            elif data.get("type") == "context_loading":
                result["context_loading_started"] = True
                self.log_event(email, "CONTEXT_LOADING", "Context loading in progress")
                
                # Wait for completion
                while True:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=20)
                        data = json.loads(response)
                        
                        if data.get("type") == "context_loaded":
                            result["context_loaded"] = True
                            context_data = data.get("context", {})
                            result["context_size"] = context_data.get("size", 0)
                            result["context_types"] = context_data.get("types", [])
                            break
                        elif data.get("type") == "context_error":
                            self.log_event(email, "CONTEXT_LOAD_ERROR", data.get("message"))
                            break
                            
                    except asyncio.TimeoutError:
                        self.log_event(email, "CONTEXT_LOAD_TIMEOUT", "Context loading timeout")
                        break
                        
        except Exception as e:
            self.log_event(email, "CONTEXT_LOAD_EXCEPTION", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_agent_assignment(self, email: str, thread_id: str, expected_agent_type: str) -> Dict[str, Any]:
        """Test agent assignment to thread."""
        result = {
            "agent_assigned": False,
            "agent_type": None,
            "agent_id": None,
            "assignment_time": 0,
            "agent_capabilities": []
        }
        
        ws = self.websocket_connections.get(email)
        if not ws or not thread_id:
            return result
            
        start_time = time.time()
        
        self.log_event(email, "AGENT_ASSIGN_START", f"Thread: {thread_id}, Expected: {expected_agent_type}")
        
        try:
            # Request agent assignment
            assign_message = {
                "type": "assign_agent",
                "thread_id": thread_id,
                "agent_preferences": {
                    "type": expected_agent_type,
                    "priority": "high"
                }
            }
            
            await ws.send(json.dumps(assign_message))
            
            # Wait for agent assignment response
            response = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(response)
            
            assignment_time = time.time() - start_time
            result["assignment_time"] = assignment_time
            self.performance_metrics["agent_assignment_times"].append(assignment_time)
            
            if data.get("type") == "agent_assigned":
                result["agent_assigned"] = True
                
                agent_data = data.get("agent", {})
                result["agent_type"] = agent_data.get("type")
                result["agent_id"] = agent_data.get("id")
                result["agent_capabilities"] = agent_data.get("capabilities", [])
                
                self.log_event(email, "AGENT_ASSIGN_SUCCESS", 
                             f"Type: {result['agent_type']], ID: {result['agent_id']], Time: {assignment_time:.2f]s")
                
            elif data.get("type") == "agent_assignment_failed":
                self.log_event(email, "AGENT_ASSIGN_FAILED", data.get("reason", "Unknown reason"))
                
        except Exception as e:
            self.log_event(email, "AGENT_ASSIGN_EXCEPTION", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_thread_state_persistence(self, email: str, thread_id: str) -> Dict[str, Any]:
        """Test thread state persistence across reconnections."""
        result = {
            "state_persisted": False,
            "reconnection_successful": False,
            "thread_recovered": False,
            "state_consistency": False
        }
        
        if not thread_id:
            return result
            
        self.log_event(email, "STATE_PERSIST_START", f"Thread: {thread_id}")
        
        try:
            # Get current thread state
            ws = self.websocket_connections.get(email)
            if not ws:
                return result
                
            # Get thread state
            state_message = {
                "type": "get_thread_state",
                "thread_id": thread_id
            }
            
            await ws.send(json.dumps(state_message))
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            initial_state = json.loads(response)
            
            # Close connection
            await ws.close()
            del self.websocket_connections[email]
            
            self.log_event(email, "CONNECTION_CLOSED", "Testing reconnection")
            
            # Wait a moment
            await asyncio.sleep(2)
            
            # Reconnect
            reconnect_success = await self.establish_websocket_connection(email)
            if not reconnect_success:
                return result
                
            result["reconnection_successful"] = True
            
            # Get thread state again
            ws = self.websocket_connections.get(email)
            await ws.send(json.dumps(state_message))
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            recovered_state = json.loads(response)
            
            if recovered_state.get("type") == "thread_state":
                result["thread_recovered"] = True
                
                # Compare states
                if (initial_state.get("thread", {}).get("id") == 
                    recovered_state.get("thread", {}).get("id")):
                        result["state_consistency"] = True
                    result["state_persisted"] = True
                    
                self.log_event(email, "STATE_PERSIST_SUCCESS", "Thread state recovered")
                
        except Exception as e:
            self.log_event(email, "STATE_PERSIST_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_concurrent_thread_creation(self, email: str) -> Dict[str, Any]:
        """Test concurrent thread creation for a single user."""
        result = {
            "concurrent_threads_created": 0,
            "creation_times": [],
            "all_successful": False,
            "thread_ids": []
        }
        
        ws = self.websocket_connections.get(email)
        if not ws:
            return result
            
        self.log_event(email, "CONCURRENT_TEST_START", "Testing concurrent thread creation")
        
        try:
            # Create multiple threads concurrently
            concurrent_count = 3
            tasks = []
            
            for i in range(concurrent_count):
                thread_case = {
                    "title": f"Concurrent Thread {i+1}",
                    "description": f"Thread created concurrently #{i+1}",
                    "initial_message": f"This is concurrent message #{i+1}",
                    "expected_agent_type": "general"
                }
                
                task = self.test_basic_thread_creation(email, thread_case)
                tasks.append(task)
            
            # Wait for all threads to be created
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_creations = 0
            for i, res in enumerate(results):
                if isinstance(res, dict) and res.get("thread_created"):
                    successful_creations += 1
                    result["creation_times"].append(res.get("creation_time", 0))
                    result["thread_ids"].append(res.get("thread_id"))
                    
            result["concurrent_threads_created"] = successful_creations
            result["all_successful"] = successful_creations == concurrent_count
            
            self.log_event(email, "CONCURRENT_TEST_COMPLETE", 
                         f"Created: {successful_creations}/{concurrent_count}")
                         
        except Exception as e:
            self.log_event(email, "CONCURRENT_TEST_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_thread_cleanup(self, email: str) -> Dict[str, Any]:
        """Test thread cleanup and archival."""
        result = {
            "threads_cleaned": 0,
            "cleanup_successful": False,
            "archive_created": False
        }
        
        user_threads = [t for t in self.created_threads if t["user"] == email]
        if not user_threads:
            return result
            
        ws = self.websocket_connections.get(email)
        if not ws:
            return result
            
        self.log_event(email, "CLEANUP_START", f"Cleaning {len(user_threads)} threads")
        
        try:
            cleaned_count = 0
            
            for thread_info in user_threads:
                cleanup_message = {
                    "type": "archive_thread",
                    "thread_id": thread_info["thread_id"],
                    "reason": "Test cleanup"
                }
                
                await ws.send(json.dumps(cleanup_message))
                
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(response)
                    
                    if data.get("type") == "thread_archived":
                        cleaned_count += 1
                        
                except asyncio.TimeoutError:
                    continue
                    
            result["threads_cleaned"] = cleaned_count
            result["cleanup_successful"] = cleaned_count > 0
            result["archive_created"] = cleaned_count == len(user_threads)
            
            self.log_event(email, "CLEANUP_COMPLETE", f"Archived: {cleaned_count}/{len(user_threads)}")
            
        except Exception as e:
            self.log_event(email, "CLEANUP_ERROR", str(e))
            
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all chat initialization tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "users_tested": len(TEST_USERS),
            "thread_cases_tested": len(THREAD_TEST_CASES),
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
            if success:
                await self.establish_websocket_connection(email)
        
        # Run tests for each user
        for user_data in TEST_USERS:
            email = user_data["email"]
            
            if email not in self.websocket_connections:
                self.log_event(email, "SKIP_USER", "No WebSocket connection")
                continue
                
            print(f"\n{'='*60}")
            print(f"Testing chat initialization for: {email}")
            print('='*60)
            
            user_results = {}
            
            # Test each thread case
            for thread_case in THREAD_TEST_CASES:
                case_name = thread_case["title"].replace(" ", "_").lower()
                
                # Test basic thread creation
                creation_result = await self.test_basic_thread_creation(email, thread_case)
                user_results[f"{case_name]_creation"] = creation_result
                
                thread_id = creation_result.get("thread_id")
                if thread_id:
                    # Test context loading
                    context_result = await self.test_context_loading(
                        email, thread_id, thread_case.get("context_requirements", [])
                    )
                    user_results[f"{case_name]_context"] = context_result
                    
                    # Test agent assignment
                    agent_result = await self.test_agent_assignment(
                        email, thread_id, thread_case.get("expected_agent_type", "general")
                    )
                    user_results[f"{case_name]_agent"] = agent_result
                    
                    # Test state persistence (only for first thread)
                    if case_name == "simple_query_thread":
                        persistence_result = await self.test_thread_state_persistence(email, thread_id)
                        user_results["state_persistence"] = persistence_result
            
            # Test concurrent thread creation
            concurrent_result = await self.test_concurrent_thread_creation(email)
            user_results["concurrent_creation"] = concurrent_result
            
            # Test cleanup
            cleanup_result = await self.test_thread_cleanup(email)
            user_results["cleanup"] = cleanup_result
            
            all_results["user_results"][email] = user_results
        
        # Add performance metrics
        all_results["performance_metrics"] = {
            "avg_thread_creation_time": (
                sum(self.performance_metrics["thread_creation_times"]) / 
                len(self.performance_metrics["thread_creation_times"])
                if self.performance_metrics["thread_creation_times"] else 0
            ),
            "avg_context_loading_time": (
                sum(self.performance_metrics["context_loading_times"]) / 
                len(self.performance_metrics["context_loading_times"])
                if self.performance_metrics["context_loading_times"] else 0
            ),
            "avg_agent_assignment_time": (
                sum(self.performance_metrics["agent_assignment_times"]) / 
                len(self.performance_metrics["agent_assignment_times"])
                if self.performance_metrics["agent_assignment_times"] else 0
            ),
            "total_threads_created": len(self.created_threads)
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
                    # Determine if test passed based on its primary success criteria
                    if "creation" in test_name and test_result.get("thread_created"):
                        passed_tests += 1
                    elif "context" in test_name and test_result.get("context_loaded"):
                        passed_tests += 1
                    elif "agent" in test_name and test_result.get("agent_assigned"):
                        passed_tests += 1
                    elif "persistence" in test_name and test_result.get("state_persisted"):
                        passed_tests += 1
                    elif "concurrent" in test_name and test_result.get("all_successful"):
                        passed_tests += 1
                    elif "cleanup" in test_name and test_result.get("cleanup_successful"):
                        passed_tests += 1
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_threads_created": len(self.created_threads),
            "active_connections": len(self.websocket_connections)
        }
        
        return all_results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
@pytest.mark.asyncio
async def test_dev_environment_chat_initialization():
    """Test comprehensive chat thread initialization functionality."""
    async with ChatInitializationTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("CHAT INITIALIZATION TEST RESULTS")
        print("="*60)
        
        for email, user_results in results["user_results"].items():
            print(f"\nUser: {email}")
            print("-" * 40)
            
            for test_name, test_result in user_results.items():
                if isinstance(test_result, dict):
                    success = False
                    if "creation" in test_name:
                        success = test_result.get("thread_created", False)
                        time_taken = test_result.get("creation_time", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} ({time_taken:.2f}s)")
                    elif "context" in test_name:
                        success = test_result.get("context_loaded", False)
                        size = test_result.get("context_size", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} (size: {size})")
                    elif "agent" in test_name:
                        success = test_result.get("agent_assigned", False)
                        agent_type = test_result.get("agent_type", "none")
                        print(f"  {test_name}: {'✓' if success else '✗'} (type: {agent_type})")
                    elif "persistence" in test_name:
                        success = test_result.get("state_persisted", False)
                        print(f"  {test_name}: {'✓' if success else '✗'}")
                    elif "concurrent" in test_name:
                        success = test_result.get("all_successful", False)
                        created = test_result.get("concurrent_threads_created", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} (created: {created})")
                    elif "cleanup" in test_name:
                        success = test_result.get("cleanup_successful", False)
                        cleaned = test_result.get("threads_cleaned", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} (cleaned: {cleaned})")
        
        # Performance metrics
        perf = results["performance_metrics"]
        print("\n" + "="*60)
        print("PERFORMANCE METRICS")
        print("="*60)
        print(f"Avg Thread Creation: {perf['avg_thread_creation_time']:.2f]s")
        print(f"Avg Context Loading: {perf['avg_context_loading_time']:.2f]s")
        print(f"Avg Agent Assignment: {perf['avg_agent_assignment_time']:.2f]s")
        print(f"Total Threads Created: {perf['total_threads_created']]")
        
        # Summary
        summary = results["summary"]
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']]")
        print(f"Passed Tests: {summary['passed_tests']]")
        print(f"Success Rate: {summary['success_rate']:.1f]%")
        print(f"Threads Created: {summary['total_threads_created']]")
        print(f"Active Connections: {summary['active_connections']]")
        
        # Assert critical conditions
        assert summary["success_rate"] >= 70, f"Success rate too low: {summary['success_rate']:.1f]%"
        assert summary["total_threads_created"] >= 5, "Not enough threads created"
        assert perf["avg_thread_creation_time"] < 10, "Thread creation too slow"
        
        print("\n[SUCCESS] Chat initialization tests completed!")

async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT CHAT INITIALIZATION TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with ChatInitializationTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        results_file = project_root / "test_results" / "chat_initialization_results.json"
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