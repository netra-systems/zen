#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment Agent Response Flow

Tests comprehensive agent message processing and response generation:
1. Message routing to appropriate agents
2. Agent processing and analysis
3. Response generation and streaming
4. Response completion and validation
5. Multi-turn conversation handling
6. Agent handoff and escalation
7. Response quality and consistency
8. Performance under various loads

BVJ:
- Segment: Free, Early, Mid, Enterprise
- Business Goal: Conversion, Retention, Expansion
- Value Impact: Core AI interaction quality determining user satisfaction
- Strategic Impact: Direct revenue impact through AI value delivery and user engagement
"""

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
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
        "email": "agent_test_1@example.com",
        "password": "SecurePass123!",
        "name": "Agent Test User 1",
        "tier": "free"
    },
    {
        "email": "agent_test_2@example.com", 
        "password": "SecurePass456!",
        "name": "Agent Test User 2",
        "tier": "early"
    },
    {
        "email": "agent_test_3@example.com",
        "password": "SecurePass789!",
        "name": "Agent Test User 3", 
        "tier": "enterprise"
    }
]

MESSAGE_TEST_CASES = [
    {
        "name": "simple_question",
        "message": "What is Python programming?",
        "expected_agent_type": "general",
        "expected_response_type": "informational",
        "min_response_length": 50,
        "max_response_time": 10,
        "should_stream": True
    },
    {
        "name": "code_review",
        "message": "Please review this Python function:\n\ndef factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)",
        "expected_agent_type": "code_reviewer",
        "expected_response_type": "analysis",
        "min_response_length": 100,
        "max_response_time": 15,
        "should_stream": True
    },
    {
        "name": "complex_analysis",
        "message": "Analyze the architecture of a microservices-based AI platform and provide optimization recommendations",
        "expected_agent_type": "architect",
        "expected_response_type": "detailed_analysis",
        "min_response_length": 200,
        "max_response_time": 25,
        "should_stream": True
    },
    {
        "name": "follow_up_question",
        "message": "Can you elaborate on the previous point?",
        "expected_agent_type": "context_aware",
        "expected_response_type": "contextual",
        "min_response_length": 30,
        "max_response_time": 8,
        "should_stream": True
    },
    {
        "name": "multi_part_request",
        "message": "I need help with: 1) Setting up a database, 2) Creating an API, 3) Implementing authentication",
        "expected_agent_type": "coordinator",
        "expected_response_type": "structured",
        "min_response_length": 150,
        "max_response_time": 20,
        "should_stream": True
    }
]

CONVERSATION_SCENARIOS = [
    {
        "name": "technical_discussion",
        "messages": [
            "What are the benefits of microservices architecture?",
            "How does it compare to monolithic architecture?",
            "What are the main challenges in implementing microservices?",
            "Can you provide specific examples of companies using this approach?"
        ]
    },
    {
        "name": "code_improvement_session",
        "messages": [
            "I have a slow Python script that processes large datasets",
            "It currently takes 10 minutes to process 1GB of data",
            "Can you suggest optimization strategies?",
            "Show me how to implement parallel processing for this use case"
        ]
    }
]

class AgentResponseFlowTester:
    """Test comprehensive agent response flows."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_tokens: Dict[str, str] = {}
        self.websocket_connections: Dict[str, Any] = {}
        self.active_threads: Dict[str, List[Dict[str, Any]]] = {}
        self.response_metrics: Dict[str, List[float]] = {
            "response_times": [],
            "first_token_times": [],
            "streaming_rates": [],
            "response_lengths": []
        }
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
                "token": self.user_tokens[email]
            }
            await ws.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("type") == "auth_success":
                self.websocket_connections[email] = ws
                self.active_threads[email] = []
                self.log_event(email, "WS_CONNECT_SUCCESS", f"Session: {data.get('session_id', 'unknown')}")
                return True
            else:
                self.log_event(email, "WS_AUTH_FAILED", str(data))
                await ws.close()
                return False
                
        except Exception as e:
            self.log_event(email, "WS_CONNECT_ERROR", str(e))
            return False
    
    async def create_test_thread(self, email: str, purpose: str = "agent_response_test") -> Optional[str]:
        """Create a test thread for agent response testing."""
        ws = self.websocket_connections.get(email)
        if not ws:
            return None
            
        try:
            create_message = {
                "type": "thread_create",
                "data": {
                    "title": f"Agent Response Test - {purpose}",
                    "description": f"Testing agent responses for {purpose}",
                    "initial_message": "Testing agent response capabilities",
                    "metadata": {
                        "test_purpose": purpose,
                        "test_timestamp": datetime.now().isoformat()
                    }
                }
            }
            
            await ws.send(json.dumps(create_message))
            response = await asyncio.wait_for(ws.recv(), timeout=15)
            data = json.loads(response)
            
            if data.get("type") == "thread_created":
                thread_id = data.get("thread_id")
                self.active_threads[email].append({
                    "thread_id": thread_id,
                    "purpose": purpose,
                    "created_at": datetime.now()
                })
                self.log_event(email, "THREAD_CREATED", f"ID: {thread_id}, Purpose: {purpose}")
                return thread_id
                
        except Exception as e:
            self.log_event(email, "THREAD_CREATE_ERROR", str(e))
            
        return None
    
    @pytest.mark.asyncio
    async def test_message_processing(self, email: str, thread_id: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test agent message processing and response generation."""
        result = {
            "message_sent": False,
            "agent_responded": False,
            "response_time": 0,
            "first_token_time": 0,
            "streaming_started": False,
            "streaming_completed": False,
            "response_content": "",
            "response_length": 0,
            "agent_type": None,
            "response_quality_score": 0,
            "meets_requirements": False
        }
        
        ws = self.websocket_connections.get(email)
        if not ws or not thread_id:
            return result
            
        message = test_case["message"]
        start_time = time.time()
        
        self.log_event(email, "MESSAGE_SEND", f"Thread: {thread_id}, Case: {test_case['name']}")
        
        try:
            # Send message to agent
            message_payload = {
                "type": "send_message",
                "thread_id": thread_id,
                "message": {
                    "content": message,
                    "type": "user",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "test_case": test_case["name"],
                        "expected_agent": test_case.get("expected_agent_type"),
                        "test_id": str(uuid.uuid4())
                    }
                }
            }
            
            await ws.send(json.dumps(message_payload))
            result["message_sent"] = True
            
            # Track response streaming
            response_chunks = []
            first_token_received = False
            streaming_complete = False
            
            # Wait for agent response(s)
            timeout = test_case.get("max_response_time", 30)
            end_time = start_time + timeout
            
            while time.time() < end_time and not streaming_complete:
                try:
                    response = await asyncio.wait_for(
                        ws.recv(), 
                        timeout=min(5, end_time - time.time())
                    )
                    data = json.loads(response)
                    
                    # Track first token time
                    if not first_token_received and data.get("type") in ["agent_response_chunk", "agent_response"]:
                        result["first_token_time"] = time.time() - start_time
                        first_token_received = True
                        result["streaming_started"] = True
                        
                    # Handle different response types
                    if data.get("type") == "agent_response_chunk":
                        chunk_content = data.get("content", "")
                        response_chunks.append(chunk_content)
                        
                        # Update agent type if provided
                        if data.get("agent_type"):
                            result["agent_type"] = data.get("agent_type")
                            
                    elif data.get("type") == "agent_response_complete":
                        result["agent_responded"] = True
                        result["streaming_completed"] = True
                        streaming_complete = True
                        
                        # Get final response content
                        if response_chunks:
                            result["response_content"] = "".join(response_chunks)
                        else:
                            result["response_content"] = data.get("content", "")
                            
                        result["response_length"] = len(result["response_content"])
                        result["agent_type"] = data.get("agent_type", result["agent_type"])
                        
                        self.log_event(email, "RESPONSE_COMPLETE", 
                                     f"Agent: {result['agent_type']}, Length: {result['response_length']}")
                        
                    elif data.get("type") == "agent_response":
                        # Non-streaming response
                        result["agent_responded"] = True
                        result["response_content"] = data.get("content", "")
                        result["response_length"] = len(result["response_content"])
                        result["agent_type"] = data.get("agent_type")
                        streaming_complete = True
                        
                    elif data.get("type") == "error":
                        self.log_event(email, "RESPONSE_ERROR", data.get("message", "Unknown error"))
                        break
                        
                except asyncio.TimeoutError:
                    if not first_token_received:
                        self.log_event(email, "RESPONSE_TIMEOUT", "No response received")
                        break
                    # Continue waiting for completion if we've started receiving
                    continue
                    
            result["response_time"] = time.time() - start_time
            
            # Evaluate response quality
            result["response_quality_score"] = self._evaluate_response_quality(
                result["response_content"], test_case
            )
            
            # Check if requirements are met
            result["meets_requirements"] = self._check_requirements(result, test_case)
            
            # Store metrics
            if result["response_time"] > 0:
                self.response_metrics["response_times"].append(result["response_time"])
            if result["first_token_time"] > 0:
                self.response_metrics["first_token_times"].append(result["first_token_time"])
            if result["response_length"] > 0:
                self.response_metrics["response_lengths"].append(result["response_length"])
                
        except Exception as e:
            self.log_event(email, "MESSAGE_PROCESS_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_conversation_flow(self, email: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test multi-turn conversation flow."""
        result = {
            "conversation_started": False,
            "messages_processed": 0,
            "total_messages": len(scenario["messages"]),
            "conversation_quality": 0,
            "context_maintained": False,
            "response_consistency": 0,
            "total_time": 0
        }
        
        thread_id = await self.create_test_thread(email, f"conversation_{scenario['name']}")
        if not thread_id:
            return result
            
        start_time = time.time()
        self.log_event(email, "CONVERSATION_START", f"Scenario: {scenario['name']}")
        
        result["conversation_started"] = True
        previous_responses = []
        
        try:
            for i, message in enumerate(scenario["messages"]):
                test_case = {
                    "name": f"{scenario['name']}_message_{i+1}",
                    "message": message,
                    "expected_agent_type": "conversational",
                    "max_response_time": 15,
                    "min_response_length": 20
                }
                
                response_result = await self.test_message_processing(email, thread_id, test_case)
                
                if response_result["agent_responded"]:
                    result["messages_processed"] += 1
                    previous_responses.append(response_result["response_content"])
                    
                    self.log_event(email, "CONVERSATION_MESSAGE", 
                                 f"Message {i+1}/{len(scenario['messages'])} processed")
                else:
                    self.log_event(email, "CONVERSATION_FAILED", f"Message {i+1} failed")
                    break
                    
                # Brief pause between messages
                await asyncio.sleep(1)
            
            # Evaluate conversation quality
            if previous_responses:
                result["context_maintained"] = self._check_context_continuity(previous_responses)
                result["response_consistency"] = self._evaluate_response_consistency(previous_responses)
                result["conversation_quality"] = (
                    result["messages_processed"] / result["total_messages"] * 0.4 +
                    (1 if result["context_maintained"] else 0) * 0.3 +
                    result["response_consistency"] * 0.3
                )
                
        except Exception as e:
            self.log_event(email, "CONVERSATION_ERROR", str(e))
            
        result["total_time"] = time.time() - start_time
        
        self.log_event(email, "CONVERSATION_COMPLETE", 
                     f"Processed: {result['messages_processed']}/{result['total_messages']}")
        
        return result
    
    @pytest.mark.asyncio
    async def test_agent_handoff(self, email: str) -> Dict[str, Any]:
        """Test agent handoff and escalation scenarios."""
        result = {
            "handoff_triggered": False,
            "handoff_successful": False,
            "original_agent": None,
            "target_agent": None,
            "handoff_time": 0,
            "context_preserved": False
        }
        
        thread_id = await self.create_test_thread(email, "agent_handoff")
        if not thread_id:
            return result
            
        start_time = time.time()
        self.log_event(email, "HANDOFF_TEST_START", f"Thread: {thread_id}")
        
        try:
            # Send a message that should trigger handoff
            handoff_message = {
                "name": "complex_technical_query",
                "message": "I need detailed help with both frontend React components and backend Python API optimization. This requires expertise in both areas.",
                "expected_agent_type": "specialist",
                "max_response_time": 20
            }
            
            initial_result = await self.test_message_processing(email, thread_id, handoff_message)
            result["original_agent"] = initial_result.get("agent_type")
            
            # Look for handoff indicators in response
            if self._detect_handoff_pattern(initial_result.get("response_content", "")):
                result["handoff_triggered"] = True
                
                # Send follow-up that requires the specialized agent
                followup_message = {
                    "name": "handoff_followup",
                    "message": "Please focus specifically on the React optimization techniques.",
                    "expected_agent_type": "frontend_specialist",
                    "max_response_time": 15
                }
                
                followup_result = await self.test_message_processing(email, thread_id, followup_message)
                result["target_agent"] = followup_result.get("agent_type")
                
                # Check if handoff was successful
                if (result["target_agent"] and 
                    result["target_agent"] != result["original_agent"]):
                    result["handoff_successful"] = True
                    result["context_preserved"] = self._check_context_preservation(
                        initial_result.get("response_content", ""),
                        followup_result.get("response_content", "")
                    )
                    
        except Exception as e:
            self.log_event(email, "HANDOFF_ERROR", str(e))
            
        result["handoff_time"] = time.time() - start_time
        
        self.log_event(email, "HANDOFF_TEST_COMPLETE", 
                     f"Success: {result['handoff_successful']}, Time: {result['handoff_time']:.2f}s")
        
        return result
    
    @pytest.mark.asyncio
    async def test_concurrent_responses(self, email: str) -> Dict[str, Any]:
        """Test handling of concurrent message processing."""
        result = {
            "concurrent_messages_sent": 0,
            "responses_received": 0,
            "all_responses_valid": False,
            "avg_response_time": 0,
            "no_interference": True
        }
        
        thread_id = await self.create_test_thread(email, "concurrent_responses")
        if not thread_id:
            return result
            
        self.log_event(email, "CONCURRENT_TEST_START", f"Thread: {thread_id}")
        
        try:
            # Prepare concurrent messages
            concurrent_messages = [
                {
                    "name": "concurrent_1",
                    "message": "What is machine learning?",
                    "expected_agent_type": "general",
                    "max_response_time": 10
                },
                {
                    "name": "concurrent_2", 
                    "message": "Explain Python decorators",
                    "expected_agent_type": "technical",
                    "max_response_time": 10
                },
                {
                    "name": "concurrent_3",
                    "message": "How to optimize database queries?",
                    "expected_agent_type": "database",
                    "max_response_time": 10
                }
            ]
            
            # Send messages concurrently
            tasks = []
            for msg in concurrent_messages:
                task = self.test_message_processing(email, thread_id, msg)
                tasks.append(task)
                result["concurrent_messages_sent"] += 1
                
            # Wait for all responses
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_results = []
            total_response_time = 0
            
            for i, res in enumerate(results):
                if isinstance(res, dict) and res.get("agent_responded"):
                    result["responses_received"] += 1
                    valid_results.append(res)
                    total_response_time += res.get("response_time", 0)
                    
                    # Check for interference (responses mixed up)
                    expected_content = concurrent_messages[i]["message"]
                    actual_response = res.get("response_content", "")
                    if not self._response_matches_query(expected_content, actual_response):
                        result["no_interference"] = False
                        
            result["all_responses_valid"] = (
                result["responses_received"] == result["concurrent_messages_sent"]
            )
            
            if valid_results:
                result["avg_response_time"] = total_response_time / len(valid_results)
                
        except Exception as e:
            self.log_event(email, "CONCURRENT_ERROR", str(e))
            
        self.log_event(email, "CONCURRENT_TEST_COMPLETE", 
                     f"Received: {result['responses_received']}/{result['concurrent_messages_sent']}")
        
        return result
    
    def _evaluate_response_quality(self, response: str, test_case: Dict[str, Any]) -> float:
        """Evaluate the quality of an agent response."""
        if not response:
            return 0.0
            
        score = 0.0
        
        # Length check
        min_length = test_case.get("min_response_length", 10)
        if len(response) >= min_length:
            score += 0.3
            
        # Relevance check (basic keyword matching)
        message = test_case["message"].lower()
        response_lower = response.lower()
        
        # Extract key terms from the message
        key_terms = re.findall(r'\b\w{4,}\b', message)
        relevance_score = sum(1 for term in key_terms if term in response_lower)
        if key_terms:
            score += (relevance_score / len(key_terms)) * 0.4
            
        # Structure check (for detailed responses)
        if test_case.get("expected_response_type") == "detailed_analysis":
            if any(marker in response for marker in ["1.", "•", "-", "First", "Second"]):
                score += 0.2
        elif test_case.get("expected_response_type") == "analysis":
            if any(word in response_lower for word in ["analysis", "review", "recommendation"]):
                score += 0.2
                
        # Completeness check
        if not response.endswith(("...", "incomplete", "error")):
            score += 0.1
            
        return min(score, 1.0)
    
    def _check_requirements(self, result: Dict[str, Any], test_case: Dict[str, Any]) -> bool:
        """Check if response meets test case requirements."""
        # Basic response received
        if not result.get("agent_responded"):
            return False
            
        # Response time check
        max_time = test_case.get("max_response_time", 30)
        if result.get("response_time", 0) > max_time:
            return False
            
        # Minimum length check
        min_length = test_case.get("min_response_length", 10)
        if result.get("response_length", 0) < min_length:
            return False
            
        # Streaming check
        if test_case.get("should_stream", False) and not result.get("streaming_started"):
            return False
            
        return True
    
    def _check_context_continuity(self, responses: List[str]) -> bool:
        """Check if context is maintained across conversation turns."""
        if len(responses) < 2:
            return True
            
        # Look for references to previous responses
        for i in range(1, len(responses)):
            current = responses[i].lower()
            # Simple heuristic: look for continuity indicators
            if any(phrase in current for phrase in [
                "as mentioned", "previously", "earlier", "above", "that", "this"
            ]):
                return True
                
        return False
    
    def _evaluate_response_consistency(self, responses: List[str]) -> float:
        """Evaluate consistency across conversation responses."""
        if len(responses) < 2:
            return 1.0
            
        # Simple consistency check: similar writing style/length
        lengths = [len(resp) for resp in responses]
        avg_length = sum(lengths) / len(lengths)
        
        # Calculate variance in response lengths
        variance = sum((length - avg_length) ** 2 for length in lengths) / len(lengths)
        consistency_score = max(0, 1 - (variance / (avg_length ** 2)))
        
        return min(consistency_score, 1.0)
    
    def _detect_handoff_pattern(self, response: str) -> bool:
        """Detect if response indicates agent handoff."""
        handoff_indicators = [
            "specialist", "expert", "transfer", "handoff", "escalate",
            "specialized", "specific expertise", "refer you to"
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in handoff_indicators)
    
    def _check_context_preservation(self, initial_response: str, followup_response: str) -> bool:
        """Check if context is preserved during handoff."""
        # Look for references to the initial context in the followup
        initial_terms = set(re.findall(r'\b\w{4,}\b', initial_response.lower()))
        followup_terms = set(re.findall(r'\b\w{4,}\b', followup_response.lower()))
        
        # Calculate overlap
        overlap = len(initial_terms.intersection(followup_terms))
        return overlap >= min(3, len(initial_terms) * 0.2)
    
    def _response_matches_query(self, query: str, response: str) -> bool:
        """Check if response is relevant to the query."""
        query_terms = set(re.findall(r'\b\w{4,}\b', query.lower()))
        response_terms = set(re.findall(r'\b\w{4,}\b', response.lower()))
        
        overlap = len(query_terms.intersection(response_terms))
        return overlap >= min(2, len(query_terms) * 0.3)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all agent response flow tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "users_tested": len(TEST_USERS),
            "message_cases_tested": len(MESSAGE_TEST_CASES),
            "conversation_scenarios_tested": len(CONVERSATION_SCENARIOS),
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
            print(f"Testing agent response flow for: {email}")
            print('='*60)
            
            user_results = {}
            
            # Test individual message cases
            for test_case in MESSAGE_TEST_CASES:
                thread_id = await self.create_test_thread(email, test_case["name"])
                if thread_id:
                    result = await self.test_message_processing(email, thread_id, test_case)
                    user_results[f"message_{test_case['name']}"] = result
            
            # Test conversation scenarios
            for scenario in CONVERSATION_SCENARIOS:
                result = await self.test_conversation_flow(email, scenario)
                user_results[f"conversation_{scenario['name']}"] = result
            
            # Test agent handoff
            handoff_result = await self.test_agent_handoff(email)
            user_results["agent_handoff"] = handoff_result
            
            # Test concurrent responses
            concurrent_result = await self.test_concurrent_responses(email)
            user_results["concurrent_responses"] = concurrent_result
            
            all_results["user_results"][email] = user_results
        
        # Calculate performance metrics
        all_results["performance_metrics"] = {
            "avg_response_time": (
                sum(self.response_metrics["response_times"]) / 
                len(self.response_metrics["response_times"])
                if self.response_metrics["response_times"] else 0
            ),
            "avg_first_token_time": (
                sum(self.response_metrics["first_token_times"]) / 
                len(self.response_metrics["first_token_times"])
                if self.response_metrics["first_token_times"] else 0
            ),
            "avg_response_length": (
                sum(self.response_metrics["response_lengths"]) / 
                len(self.response_metrics["response_lengths"])
                if self.response_metrics["response_lengths"] else 0
            ),
            "total_responses_tested": len(self.response_metrics["response_times"])
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
                    if "message_" in test_name and test_result.get("meets_requirements"):
                        passed_tests += 1
                    elif "conversation_" in test_name and test_result.get("conversation_quality", 0) >= 0.7:
                        passed_tests += 1
                    elif "handoff" in test_name and test_result.get("handoff_successful"):
                        passed_tests += 1
                    elif "concurrent" in test_name and test_result.get("all_responses_valid"):
                        passed_tests += 1
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_responses": len(self.response_metrics["response_times"]),
            "avg_quality_score": sum(
                result.get("response_quality_score", 0) 
                for user_results in all_results["user_results"].values()
                for result in user_results.values()
                if isinstance(result, dict) and "response_quality_score" in result
            ) / max(1, len([
                result for user_results in all_results["user_results"].values()
                for result in user_results.values()
                if isinstance(result, dict) and "response_quality_score" in result
            ]))
        }
        
        return all_results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
@pytest.mark.asyncio
async def test_dev_environment_agent_response_flow():
    """Test comprehensive agent response flow functionality."""
    async with AgentResponseFlowTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("AGENT RESPONSE FLOW TEST RESULTS")
        print("="*60)
        
        for email, user_results in results["user_results"].items():
            print(f"\nUser: {email}")
            print("-" * 40)
            
            for test_name, test_result in user_results.items():
                if isinstance(test_result, dict):
                    if "message_" in test_name:
                        success = test_result.get("meets_requirements", False)
                        quality = test_result.get("response_quality_score", 0)
                        time_taken = test_result.get("response_time", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} (quality: {quality:.2f}, time: {time_taken:.2f}s)")
                    elif "conversation_" in test_name:
                        quality = test_result.get("conversation_quality", 0)
                        messages = test_result.get("messages_processed", 0)
                        total = test_result.get("total_messages", 0)
                        print(f"  {test_name}: {quality:.2f} quality ({messages}/{total} messages)")
                    elif "handoff" in test_name:
                        success = test_result.get("handoff_successful", False)
                        context = test_result.get("context_preserved", False)
                        print(f"  {test_name}: {'✓' if success else '✗'} (context: {'✓' if context else '✗'})")
                    elif "concurrent" in test_name:
                        success = test_result.get("all_responses_valid", False)
                        received = test_result.get("responses_received", 0)
                        sent = test_result.get("concurrent_messages_sent", 0)
                        print(f"  {test_name}: {'✓' if success else '✗'} ({received}/{sent} responses)")
        
        # Performance metrics
        perf = results["performance_metrics"]
        print("\n" + "="*60)
        print("PERFORMANCE METRICS")
        print("="*60)
        print(f"Avg Response Time: {perf['avg_response_time']:.2f}s")
        print(f"Avg First Token Time: {perf['avg_first_token_time']:.2f}s")
        print(f"Avg Response Length: {perf['avg_response_length']:.0f} chars")
        print(f"Total Responses: {perf['total_responses_tested']}")
        
        # Summary
        summary = results["summary"]
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed Tests: {summary['passed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Avg Quality Score: {summary['avg_quality_score']:.2f}")
        print(f"Total Responses: {summary['total_responses']}")
        
        # Assert critical conditions
        assert summary["success_rate"] >= 70, f"Success rate too low: {summary['success_rate']:.1f}%"
        assert summary["total_responses"] >= 10, "Not enough responses tested"
        assert perf["avg_response_time"] < 20, "Average response time too slow"
        assert summary["avg_quality_score"] >= 0.5, "Average quality score too low"
        
        print("\n[SUCCESS] Agent response flow tests completed!")

async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT AGENT RESPONSE FLOW TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with AgentResponseFlowTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        results_file = project_root / "test_results" / "agent_response_flow_results.json"
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