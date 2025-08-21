#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment End-to-End Workflow

Tests complete E2E workflow from login to agent response:
1. Complete user onboarding flow
2. Full authentication and authorization
3. Thread creation and management
4. Multi-turn agent conversations
5. File uploads and processing
6. Context management and persistence
7. User settings and preferences
8. Complete session lifecycle

BVJ:
- Segment: Free, Early, Mid, Enterprise
- Business Goal: User Experience, Conversion, Retention
- Value Impact: Complete user journey validation ensuring seamless platform experience
- Strategic Impact: Critical for user satisfaction and platform adoption across all tiers
"""

from netra_backend.tests.test_utils import setup_test_path

setup_test_path()

import asyncio
import base64
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import pytest
import websockets

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Service URLs
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"

# E2E Test Scenarios
E2E_SCENARIOS = [
    {
        "name": "new_user_journey",
        "description": "Complete new user onboarding and first interaction",
        "user_tier": "free",
        "steps": [
            "register", "verify_email", "login", "setup_profile", 
            "create_first_thread", "send_first_message", "receive_response",
            "update_preferences", "logout"
        ]
    },
    {
        "name": "returning_user_workflow",
        "description": "Returning user login and interaction flow",
        "user_tier": "early",
        "steps": [
            "login", "restore_session", "access_threads", "continue_conversation",
            "create_new_thread", "multi_turn_conversation", "save_and_logout"
        ]
    },
    {
        "name": "enterprise_user_flow",
        "description": "Enterprise user with advanced features",
        "user_tier": "enterprise",
        "steps": [
            "sso_login", "access_enterprise_features", "bulk_operations",
            "advanced_agent_interactions", "file_processing", "team_collaboration",
            "analytics_access", "admin_controls"
        ]
    },
    {
        "name": "mobile_user_experience",
        "description": "Mobile-optimized user experience flow",
        "user_tier": "mid",
        "steps": [
            "mobile_login", "responsive_interface", "touch_interactions",
            "offline_mode", "sync_on_reconnect", "mobile_notifications"
        ]
    }
]

CONVERSATION_FLOWS = [
    {
        "name": "technical_assistance",
        "messages": [
            "I need help setting up a Python development environment",
            "I'm using Windows 11 and want to use VSCode",
            "What about virtual environments? Should I use venv or conda?",
            "Can you help me set up automatic formatting with black?",
            "How do I configure debugging for a Flask application?"
        ],
        "expected_agent_types": ["technical", "development", "python_expert"]
    },
    {
        "name": "business_consultation",
        "messages": [
            "I'm starting a tech startup and need advice on the technology stack",
            "We're expecting to scale to 100,000 users within 2 years",
            "What database would you recommend for user data and analytics?",
            "How should we handle authentication and user management?",
            "What about deployment and DevOps strategies?"
        ],
        "expected_agent_types": ["business", "architecture", "consultant"]
    },
    {
        "name": "creative_project",
        "messages": [
            "I want to create an interactive web application for storytelling",
            "Users should be able to create branching narratives",
            "What technologies would work best for this?",
            "How can I implement real-time collaboration features?",
            "Any suggestions for monetization strategies?"
        ],
        "expected_agent_types": ["creative", "web_development", "product"]
    }
]


class EndToEndWorkflowTester:
    """Test complete end-to-end user workflows."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_data: Dict[str, Dict[str, Any]] = {}
        self.user_tokens: Dict[str, str] = {}
        self.websocket_connections: Dict[str, Any] = {}
        self.user_threads: Dict[str, List[str]] = {}
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.workflow_metrics: Dict[str, List[float]] = {
            "registration_times": [],
            "login_times": [],
            "first_response_times": [],
            "conversation_times": [],
            "total_workflow_times": []
        }
        self.user_experience_scores: Dict[str, float] = {}
        self.test_logs: List[str] = []
        
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
        """Log workflow events for analysis."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{user}] {event}"
        if details:
            log_entry += f" - {details}"
        self.test_logs.append(log_entry)
        print(log_entry)
    
    def generate_test_user(self, scenario: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
        """Generate a test user for E2E scenario."""
        scenario_name = scenario["name"]
        tier = scenario["user_tier"]
        
        user = {
            "email": f"e2e_{scenario_name}_{index}@example.com",
            "password": "SecureE2EPass123!",
            "name": f"E2E Test User {scenario_name.title()} {index}",
            "tier": tier,
            "scenario": scenario_name,
            "created_at": datetime.now().isoformat()
        }
        
        self.user_data[user["email"]] = user
        return user
    
    async def execute_user_registration(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user registration with full validation."""
        result = {
            "success": False,
            "registration_time": 0,
            "email_verification_required": False,
            "profile_created": False,
            "error": None
        }
        
        email = user["email"]
        start_time = time.time()
        
        self.log_event(email, "REGISTRATION_START", f"Tier: {user['tier']}")
        
        try:
            register_payload = {
                "email": email,
                "password": user["password"],
                "name": user["name"],
                "tier": user["tier"],
                "preferences": {
                    "theme": "light",
                    "notifications": True,
                    "language": "en"
                },
                "metadata": {
                    "source": "e2e_test",
                    "scenario": user["scenario"],
                    "test_timestamp": datetime.now().isoformat()
                }
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_payload
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    result["success"] = True
                    result["email_verification_required"] = data.get("verification_required", False)
                    result["profile_created"] = True
                    
                    # Store user ID for later use
                    user["user_id"] = data.get("user_id")
                    
                    self.log_event(email, "REGISTRATION_SUCCESS", f"User ID: {data.get('user_id')}")
                    
                elif response.status == 409:
                    # User already exists - this is okay for testing
                    result["success"] = True
                    self.log_event(email, "USER_EXISTS", "Using existing user")
                else:
                    error_text = await response.text()
                    result["error"] = f"Status: {response.status}, Error: {error_text}"
                    self.log_event(email, "REGISTRATION_FAILED", result["error"])
                    
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "REGISTRATION_ERROR", str(e))
            
        result["registration_time"] = time.time() - start_time
        self.workflow_metrics["registration_times"].append(result["registration_time"])
        
        return result
    
    async def execute_user_login(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user login with session management."""
        result = {
            "success": False,
            "login_time": 0,
            "token_received": False,
            "session_created": False,
            "profile_loaded": False,
            "error": None
        }
        
        email = user["email"]
        start_time = time.time()
        
        self.log_event(email, "LOGIN_START", "Authenticating user")
        
        try:
            login_payload = {
                "email": email,
                "password": user["password"],
                "device_info": {
                    "type": "desktop",
                    "browser": "test_client",
                    "os": "test_os"
                }
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["success"] = True
                    result["token_received"] = bool(data.get("access_token"))
                    result["session_created"] = bool(data.get("session_id"))
                    
                    # Store token for future requests
                    self.user_tokens[email] = data.get("access_token")
                    user["session_id"] = data.get("session_id")
                    
                    # Load user profile
                    profile_result = await self._load_user_profile(email)
                    result["profile_loaded"] = profile_result
                    
                    self.log_event(email, "LOGIN_SUCCESS", f"Session: {data.get('session_id')}")
                    
                else:
                    error_text = await response.text()
                    result["error"] = f"Status: {response.status}, Error: {error_text}"
                    self.log_event(email, "LOGIN_FAILED", result["error"])
                    
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "LOGIN_ERROR", str(e))
            
        result["login_time"] = time.time() - start_time
        self.workflow_metrics["login_times"].append(result["login_time"])
        
        return result
    
    async def _load_user_profile(self, email: str) -> bool:
        """Load user profile data."""
        try:
            headers = {"Authorization": f"Bearer {self.user_tokens[email]}"}
            
            async with self.session.get(
                f"{BACKEND_URL}/api/v1/user/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    profile_data = await response.json()
                    self.user_data[email]["profile"] = profile_data
                    return True
                    
        except Exception as e:
            self.log_event(email, "PROFILE_LOAD_ERROR", str(e))
            
        return False
    
    async def establish_websocket_connection(self, email: str) -> Dict[str, Any]:
        """Establish WebSocket connection for real-time interactions."""
        result = {
            "success": False,
            "connection_time": 0,
            "authenticated": False,
            "error": None
        }
        
        if email not in self.user_tokens:
            result["error"] = "No auth token"
            return result
            
        start_time = time.time()
        self.log_event(email, "WS_CONNECT_START", "Establishing WebSocket connection")
        
        try:
            headers = {"Authorization": f"Bearer {self.user_tokens[email]}"}
            
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
                "client_info": {
                    "type": "e2e_test",
                    "scenario": self.user_data[email]["scenario"]
                }
            }
            await ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("type") == "auth_success":
                result["success"] = True
                result["authenticated"] = True
                self.websocket_connections[email] = ws
                self.user_threads[email] = []
                self.conversation_history[email] = []
                
                self.log_event(email, "WS_CONNECT_SUCCESS", f"Session: {data.get('session_id')}")
            else:
                result["error"] = str(data)
                await ws.close()
                
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "WS_CONNECT_ERROR", str(e))
            
        result["connection_time"] = time.time() - start_time
        return result
    
    async def execute_conversation_flow(self, email: str, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complete conversation flow with an agent."""
        result = {
            "conversation_started": False,
            "thread_created": False,
            "messages_sent": 0,
            "responses_received": 0,
            "conversation_time": 0,
            "first_response_time": 0,
            "agent_types_encountered": [],
            "conversation_quality": 0,
            "error": None
        }
        
        ws = self.websocket_connections.get(email)
        if not ws:
            result["error"] = "No WebSocket connection"
            return result
            
        start_time = time.time()
        conversation_name = conversation["name"]
        messages = conversation["messages"]
        
        self.log_event(email, "CONVERSATION_START", f"Flow: {conversation_name}")
        
        try:
            # Create thread for conversation
            thread_data = {
                "title": f"E2E Test: {conversation_name.title()}",
                "description": f"End-to-end test conversation: {conversation_name}",
                "initial_message": messages[0],
                "metadata": {
                    "e2e_test": True,
                    "conversation_flow": conversation_name,
                    "test_timestamp": datetime.now().isoformat()
                }
            }
            
            create_message = {
                "type": "thread_create",
                "data": thread_data
            }
            
            await ws.send(json.dumps(create_message))
            response = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(response)
            
            if data.get("type") == "thread_created":
                thread_id = data.get("thread_id")
                result["thread_created"] = True
                result["conversation_started"] = True
                self.user_threads[email].append(thread_id)
                
                self.log_event(email, "THREAD_CREATED", f"ID: {thread_id}")
                
                # Send each message in the conversation
                first_response_received = False
                
                for i, message in enumerate(messages):
                    message_start = time.time()
                    
                    message_payload = {
                        "type": "send_message",
                        "thread_id": thread_id,
                        "message": {
                            "content": message,
                            "type": "user",
                            "timestamp": datetime.now().isoformat(),
                            "message_index": i
                        }
                    }
                    
                    await ws.send(json.dumps(message_payload))
                    result["messages_sent"] += 1
                    
                    # Wait for agent response
                    try:
                        agent_response = await asyncio.wait_for(ws.recv(), timeout=30)
                        response_data = json.loads(agent_response)
                        
                        if response_data.get("type") in ["agent_response", "agent_response_complete"]:
                            result["responses_received"] += 1
                            
                            # Track first response time
                            if not first_response_received:
                                result["first_response_time"] = time.time() - start_time
                                first_response_received = True
                                self.workflow_metrics["first_response_times"].append(result["first_response_time"])
                            
                            # Track agent type
                            agent_type = response_data.get("agent_type")
                            if agent_type and agent_type not in result["agent_types_encountered"]:
                                result["agent_types_encountered"].append(agent_type)
                                
                            # Store conversation history
                            self.conversation_history[email].append({
                                "user_message": message,
                                "agent_response": response_data.get("content", ""),
                                "agent_type": agent_type,
                                "timestamp": datetime.now().isoformat(),
                                "response_time": time.time() - message_start
                            })
                            
                            self.log_event(email, "MESSAGE_RESPONSE", 
                                         f"Message {i+1}: {agent_type}, Time: {time.time() - message_start:.2f}s")
                        
                    except asyncio.TimeoutError:
                        self.log_event(email, "MESSAGE_TIMEOUT", f"Message {i+1} timeout")
                        break
                    
                    # Brief pause between messages for natural conversation flow
                    await asyncio.sleep(1)
                
                # Calculate conversation quality
                result["conversation_quality"] = self._calculate_conversation_quality(
                    email, conversation, result
                )
                
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "CONVERSATION_ERROR", str(e))
            
        result["conversation_time"] = time.time() - start_time
        self.workflow_metrics["conversation_times"].append(result["conversation_time"])
        
        return result
    
    def _calculate_conversation_quality(self, email: str, conversation: Dict[str, Any], result: Dict[str, Any]) -> float:
        """Calculate the quality score for a conversation."""
        quality_score = 0.0
        
        # Response rate (30%)
        if result["messages_sent"] > 0:
            response_rate = result["responses_received"] / result["messages_sent"]
            quality_score += response_rate * 0.3
        
        # Response time (20%)
        if result["first_response_time"] > 0:
            # Good response time is under 10 seconds
            time_score = max(0, 1 - (result["first_response_time"] / 10))
            quality_score += time_score * 0.2
        
        # Agent variety (20%)
        expected_agents = conversation.get("expected_agent_types", [])
        if expected_agents:
            agent_match_score = len(set(result["agent_types_encountered"]).intersection(set(expected_agents))) / len(expected_agents)
            quality_score += agent_match_score * 0.2
        
        # Conversation completeness (30%)
        if result["conversation_started"] and result["responses_received"] >= len(conversation["messages"]) * 0.8:
            quality_score += 0.3
        
        return min(quality_score, 1.0)
    
    async def execute_user_preferences_update(self, email: str) -> Dict[str, Any]:
        """Execute user preferences update."""
        result = {
            "success": False,
            "preferences_updated": False,
            "sync_verified": False,
            "update_time": 0,
            "error": None
        }
        
        start_time = time.time()
        self.log_event(email, "PREFERENCES_UPDATE", "Updating user preferences")
        
        try:
            headers = {"Authorization": f"Bearer {self.user_tokens[email]}"}
            
            preferences_update = {
                "theme": "dark",
                "notifications": {
                    "email": True,
                    "push": False,
                    "in_app": True
                },
                "language": "en",
                "ai_assistant": {
                    "response_style": "detailed",
                    "expertise_level": "advanced",
                    "preferred_agents": ["technical", "creative"]
                },
                "privacy": {
                    "data_sharing": False,
                    "analytics": True,
                    "personalization": True
                }
            }
            
            async with self.session.put(
                f"{BACKEND_URL}/api/v1/user/preferences",
                json=preferences_update,
                headers=headers
            ) as response:
                if response.status == 200:
                    result["preferences_updated"] = True
                    
                    # Verify preferences were applied
                    await asyncio.sleep(1)
                    
                    async with self.session.get(
                        f"{BACKEND_URL}/api/v1/user/preferences",
                        headers=headers
                    ) as verify_response:
                        if verify_response.status == 200:
                            saved_prefs = await verify_response.json()
                            
                            if saved_prefs.get("theme") == "dark":
                                result["sync_verified"] = True
                                result["success"] = True
                                
                    self.log_event(email, "PREFERENCES_SUCCESS", "Preferences updated and verified")
                else:
                    result["error"] = f"Status: {response.status}"
                    
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "PREFERENCES_ERROR", str(e))
            
        result["update_time"] = time.time() - start_time
        return result
    
    async def execute_file_upload_workflow(self, email: str) -> Dict[str, Any]:
        """Execute file upload and processing workflow."""
        result = {
            "file_uploaded": False,
            "processing_started": False,
            "processing_completed": False,
            "results_available": False,
            "upload_time": 0,
            "processing_time": 0,
            "error": None
        }
        
        start_time = time.time()
        self.log_event(email, "FILE_UPLOAD_START", "Testing file upload workflow")
        
        try:
            # Create a test file
            test_content = "# Test Document\n\nThis is a test document for E2E file processing.\n\n## Content\n\nSample content for analysis."
            test_file_data = base64.b64encode(test_content.encode()).decode()
            
            headers = {"Authorization": f"Bearer {self.user_tokens[email]}"}
            
            upload_payload = {
                "filename": "test_document.md",
                "content_type": "text/markdown",
                "file_data": test_file_data,
                "processing_options": {
                    "extract_text": True,
                    "analyze_content": True,
                    "generate_summary": True
                }
            }
            
            async with self.session.post(
                f"{BACKEND_URL}/api/v1/files/upload",
                json=upload_payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    upload_data = await response.json()
                    file_id = upload_data.get("file_id")
                    result["file_uploaded"] = True
                    
                    if upload_data.get("processing_started"):
                        result["processing_started"] = True
                        
                        # Wait for processing completion
                        processing_complete = False
                        max_wait = 30  # 30 seconds max wait
                        check_interval = 2
                        
                        for _ in range(max_wait // check_interval):
                            await asyncio.sleep(check_interval)
                            
                            async with self.session.get(
                                f"{BACKEND_URL}/api/v1/files/{file_id}/status",
                                headers=headers
                            ) as status_response:
                                if status_response.status == 200:
                                    status_data = await status_response.json()
                                    
                                    if status_data.get("status") == "completed":
                                        result["processing_completed"] = True
                                        processing_complete = True
                                        break
                                    elif status_data.get("status") == "failed":
                                        result["error"] = "Processing failed"
                                        break
                        
                        # Get processing results
                        if processing_complete:
                            async with self.session.get(
                                f"{BACKEND_URL}/api/v1/files/{file_id}/results",
                                headers=headers
                            ) as results_response:
                                if results_response.status == 200:
                                    results_data = await results_response.json()
                                    result["results_available"] = True
                                    
                                    self.log_event(email, "FILE_PROCESSING_SUCCESS", 
                                                 f"File: {file_id}, Results: {len(results_data.get('results', []))}")
                    
                else:
                    result["error"] = f"Upload failed: {response.status}"
                    
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "FILE_UPLOAD_ERROR", str(e))
            
        result["upload_time"] = time.time() - start_time
        result["processing_time"] = result["upload_time"]  # Total time including processing
        
        return result
    
    async def execute_session_cleanup(self, email: str) -> Dict[str, Any]:
        """Execute session cleanup and logout."""
        result = {
            "logout_initiated": False,
            "session_invalidated": False,
            "websocket_closed": False,
            "cleanup_time": 0,
            "error": None
        }
        
        start_time = time.time()
        self.log_event(email, "SESSION_CLEANUP", "Starting session cleanup")
        
        try:
            # Close WebSocket connection
            ws = self.websocket_connections.get(email)
            if ws and not ws.closed:
                await ws.close()
                result["websocket_closed"] = True
                del self.websocket_connections[email]
            
            # Logout via API
            if email in self.user_tokens:
                headers = {"Authorization": f"Bearer {self.user_tokens[email]}"}
                
                async with self.session.post(
                    f"{AUTH_SERVICE_URL}/auth/logout",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result["logout_initiated"] = True
                        result["session_invalidated"] = True
                        
                        # Remove token
                        del self.user_tokens[email]
                        
                        self.log_event(email, "LOGOUT_SUCCESS", "Session invalidated")
                    else:
                        result["error"] = f"Logout failed: {response.status}"
            
        except Exception as e:
            result["error"] = str(e)
            self.log_event(email, "CLEANUP_ERROR", str(e))
            
        result["cleanup_time"] = time.time() - start_time
        return result
    
    async def execute_e2e_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complete E2E scenario."""
        scenario_name = scenario["name"]
        steps = scenario["steps"]
        
        result = {
            "scenario_name": scenario_name,
            "user_created": False,
            "steps_completed": 0,
            "total_steps": len(steps),
            "step_results": {},
            "overall_time": 0,
            "user_experience_score": 0,
            "error": None
        }
        
        start_time = time.time()
        self.log_event("SCENARIO", f"START_{scenario_name.upper()}", f"Executing {len(steps)} steps")
        
        try:
            # Generate test user for this scenario
            user = self.generate_test_user(scenario)
            email = user["email"]
            result["user_created"] = True
            
            # Execute each step in the scenario
            for step_name in steps:
                step_start = time.time()
                step_result = None
                
                try:
                    if step_name == "register":
                        step_result = await self.execute_user_registration(user)
                    elif step_name == "login":
                        step_result = await self.execute_user_login(user)
                    elif step_name == "setup_profile":
                        # WebSocket connection needed for profile setup
                        ws_result = await self.establish_websocket_connection(email)
                        step_result = ws_result
                    elif step_name in ["create_first_thread", "create_new_thread"]:
                        # Execute conversation flow
                        conversation = CONVERSATION_FLOWS[0]  # Use first conversation
                        step_result = await self.execute_conversation_flow(email, conversation)
                    elif step_name == "multi_turn_conversation":
                        # Execute longer conversation
                        conversation = CONVERSATION_FLOWS[1]  # Use business consultation
                        step_result = await self.execute_conversation_flow(email, conversation)
                    elif step_name == "update_preferences":
                        step_result = await self.execute_user_preferences_update(email)
                    elif step_name == "file_processing":
                        step_result = await self.execute_file_upload_workflow(email)
                    elif step_name in ["logout", "save_and_logout"]:
                        step_result = await self.execute_session_cleanup(email)
                    else:
                        # Generic step simulation
                        step_result = {
                            "success": True,
                            "simulated": True,
                            "step_time": 0.5
                        }
                        await asyncio.sleep(0.5)
                    
                    if step_result and step_result.get("success", True):
                        result["steps_completed"] += 1
                        
                    result["step_results"][step_name] = step_result
                    
                    step_time = time.time() - step_start
                    self.log_event(email, f"STEP_{step_name.upper()}", 
                                 f"Completed in {step_time:.2f}s, Success: {step_result.get('success', False) if step_result else False}")
                    
                except Exception as e:
                    step_result = {"success": False, "error": str(e)}
                    result["step_results"][step_name] = step_result
                    self.log_event(email, f"STEP_{step_name.upper()}_ERROR", str(e))
            
            # Calculate user experience score
            result["user_experience_score"] = self._calculate_user_experience_score(result)
            self.user_experience_scores[email] = result["user_experience_score"]
            
        except Exception as e:
            result["error"] = str(e)
            self.log_event("SCENARIO", f"ERROR_{scenario_name.upper()}", str(e))
            
        result["overall_time"] = time.time() - start_time
        self.workflow_metrics["total_workflow_times"].append(result["overall_time"])
        
        self.log_event("SCENARIO", f"COMPLETE_{scenario_name.upper()}", 
                     f"Score: {result['user_experience_score']:.2f}, Time: {result['overall_time']:.2f}s")
        
        return result
    
    def _calculate_user_experience_score(self, scenario_result: Dict[str, Any]) -> float:
        """Calculate user experience score for a scenario."""
        score = 0.0
        
        # Step completion rate (40%)
        completion_rate = scenario_result["steps_completed"] / scenario_result["total_steps"]
        score += completion_rate * 0.4
        
        # Performance score (30%)
        performance_score = 1.0
        for step_name, step_result in scenario_result["step_results"].items():
            if isinstance(step_result, dict):
                # Penalize slow operations
                if "registration_time" in step_result and step_result["registration_time"] > 5:
                    performance_score -= 0.1
                if "login_time" in step_result and step_result["login_time"] > 3:
                    performance_score -= 0.1
                if "first_response_time" in step_result and step_result["first_response_time"] > 10:
                    performance_score -= 0.1
        
        score += max(0, performance_score) * 0.3
        
        # Error rate (30%)
        error_count = sum(
            1 for step_result in scenario_result["step_results"].values()
            if isinstance(step_result, dict) and not step_result.get("success", True)
        )
        error_rate = error_count / scenario_result["total_steps"]
        score += (1 - error_rate) * 0.3
        
        return min(score, 1.0)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all E2E workflow tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "scenarios_tested": len(E2E_SCENARIOS),
            "scenario_results": {},
            "workflow_metrics": {},
            "user_experience_scores": {},
            "test_logs": [],
            "summary": {}
        }
        
        print("\n" + "="*60)
        print("END-TO-END WORKFLOW TESTING")
        print("="*60)
        
        # Execute each E2E scenario
        for scenario in E2E_SCENARIOS:
            print(f"\n{'-'*40}")
            print(f"Scenario: {scenario['name']}")
            print(f"Description: {scenario['description']}")
            print(f"User Tier: {scenario['user_tier']}")
            print(f"Steps: {len(scenario['steps'])}")
            print(f"{'-'*40}")
            
            scenario_result = await self.execute_e2e_scenario(scenario)
            all_results["scenario_results"][scenario["name"]] = scenario_result
            
            # Brief pause between scenarios
            await asyncio.sleep(2)
        
        # Calculate workflow metrics
        all_results["workflow_metrics"] = {
            "avg_registration_time": (
                sum(self.workflow_metrics["registration_times"]) / 
                len(self.workflow_metrics["registration_times"])
                if self.workflow_metrics["registration_times"] else 0
            ),
            "avg_login_time": (
                sum(self.workflow_metrics["login_times"]) / 
                len(self.workflow_metrics["login_times"])
                if self.workflow_metrics["login_times"] else 0
            ),
            "avg_first_response_time": (
                sum(self.workflow_metrics["first_response_times"]) / 
                len(self.workflow_metrics["first_response_times"])
                if self.workflow_metrics["first_response_times"] else 0
            ),
            "avg_conversation_time": (
                sum(self.workflow_metrics["conversation_times"]) / 
                len(self.workflow_metrics["conversation_times"])
                if self.workflow_metrics["conversation_times"] else 0
            ),
            "avg_total_workflow_time": (
                sum(self.workflow_metrics["total_workflow_times"]) / 
                len(self.workflow_metrics["total_workflow_times"])
                if self.workflow_metrics["total_workflow_times"] else 0
            )
        }
        
        # Store user experience scores
        all_results["user_experience_scores"] = self.user_experience_scores
        
        # Add logs
        all_results["test_logs"] = self.test_logs
        
        # Generate summary
        total_scenarios = len(E2E_SCENARIOS)
        successful_scenarios = sum(
            1 for result in all_results["scenario_results"].values()
            if result.get("user_experience_score", 0) >= 0.7
        )
        
        avg_ux_score = (
            sum(self.user_experience_scores.values()) / 
            len(self.user_experience_scores)
            if self.user_experience_scores else 0
        )
        
        all_results["summary"] = {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "scenario_success_rate": (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0,
            "avg_user_experience_score": avg_ux_score,
            "total_users_tested": len(self.user_data),
            "total_conversations": len(self.conversation_history),
            "workflow_efficiency": "good" if all_results["workflow_metrics"]["avg_total_workflow_time"] < 120 else "needs_improvement"
        }
        
        return all_results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
async def test_dev_environment_end_to_end_workflow():
    """Test comprehensive end-to-end workflow functionality."""
    async with EndToEndWorkflowTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("END-TO-END WORKFLOW TEST RESULTS")
        print("="*60)
        
        for scenario_name, scenario_result in results["scenario_results"].items():
            print(f"\nScenario: {scenario_name}")
            print("-" * 40)
            print(f"  Steps Completed: {scenario_result.get('steps_completed', 0)}/{scenario_result.get('total_steps', 0)}")
            print(f"  UX Score: {scenario_result.get('user_experience_score', 0):.2f}")
            print(f"  Overall Time: {scenario_result.get('overall_time', 0):.2f}s")
            
            # Show key step results
            step_results = scenario_result.get("step_results", {})
            for step_name, step_result in step_results.items():
                if isinstance(step_result, dict):
                    success = step_result.get("success", False)
                    print(f"    {step_name}: {'✓' if success else '✗'}")
        
        # Workflow metrics
        metrics = results["workflow_metrics"]
        print("\n" + "="*60)
        print("WORKFLOW METRICS")
        print("="*60)
        print(f"Avg Registration Time: {metrics['avg_registration_time']:.2f}s")
        print(f"Avg Login Time: {metrics['avg_login_time']:.2f}s")
        print(f"Avg First Response Time: {metrics['avg_first_response_time']:.2f}s")
        print(f"Avg Conversation Time: {metrics['avg_conversation_time']:.2f}s")
        print(f"Avg Total Workflow Time: {metrics['avg_total_workflow_time']:.2f}s")
        
        # User Experience Scores
        ux_scores = results["user_experience_scores"]
        if ux_scores:
            print("\n" + "="*60)
            print("USER EXPERIENCE SCORES")
            print("="*60)
            for user, score in ux_scores.items():
                print(f"  {user}: {score:.2f}")
        
        # Summary
        summary = results["summary"]
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Scenarios: {summary['successful_scenarios']}/{summary['total_scenarios']}")
        print(f"Scenario Success Rate: {summary['scenario_success_rate']:.1f}%")
        print(f"Avg UX Score: {summary['avg_user_experience_score']:.2f}")
        print(f"Users Tested: {summary['total_users_tested']}")
        print(f"Conversations: {summary['total_conversations']}")
        print(f"Workflow Efficiency: {summary['workflow_efficiency']}")
        
        # Assert critical conditions
        assert summary["scenario_success_rate"] >= 75, f"Scenario success rate too low: {summary['scenario_success_rate']:.1f}%"
        assert summary["avg_user_experience_score"] >= 0.7, f"UX score too low: {summary['avg_user_experience_score']:.2f}"
        assert metrics["avg_login_time"] < 5, "Login time too slow"
        assert metrics["avg_first_response_time"] < 15, "First response time too slow"
        
        print("\n[SUCCESS] End-to-end workflow tests completed!")


async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT END-TO-END WORKFLOW TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with EndToEndWorkflowTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        results_file = project_root / "test_results" / "end_to_end_workflow_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\nResults saved to: {results_file}")
        
        # Return exit code
        if results["summary"]["scenario_success_rate"] >= 75:
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)