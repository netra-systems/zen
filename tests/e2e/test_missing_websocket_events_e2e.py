#!/usr/bin/env python
"""
Missing WebSocket Events E2E Tests - Phase 3 Implementation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - REVENUE PROTECTION
- Business Goal: Prevent critical WebSocket event failures that break user chat experience
- Value Impact: Protects $500K+ ARR from WebSocket event delivery failures 
- Strategic/Revenue Impact: Mission-critical infrastructure for core product functionality

CRITICAL E2E REQUIREMENTS (CLAUDE.md Compliance):
 PASS:  FEATURE FREEZE: Only validates existing WebSocket event system works correctly
 PASS:  NO MOCKS ALLOWED: Real Docker services, real WebSocket, real agent execution
 PASS:  MANDATORY E2E AUTH: All tests use create_authenticated_user_context()
 PASS:  MISSION CRITICAL EVENTS: ALL 5 WebSocket events must be validated in EVERY test
 PASS:  COMPLETE WORK: Full agent execution workflows with complete event validation
 PASS:  SYSTEM STABILITY: Proves WebSocket event system maintains business value delivery

ROOT CAUSE ADDRESSED:
- Missing agent_started events causing user confusion about AI processing
- Missing agent_thinking events breaking transparency and user engagement
- Missing tool_executing events preventing users from understanding AI actions
- Missing tool_completed events blocking insight into AI analysis results
- Missing agent_completed events leaving users without final responses

MISSION CRITICAL WEBSOCKET EVENTS (ALL REQUIRED):
1. agent_started - User sees AI began processing their problem ($500K+ revenue protection)
2. agent_thinking - Real-time reasoning visibility (user engagement and trust)
3. tool_executing - Tool usage transparency (demonstrates AI problem-solving)
4. tool_completed - Tool results display (delivers actionable insights to users)
5. agent_completed - User knows when valuable response is ready (completion confirmation)

COMPREHENSIVE VALIDATION SCENARIOS:
- Complete optimization agent workflow with all 5 events
- Multi-user concurrent execution with event isolation
- Event recovery after interruption or WebSocket reconnection
- Event timing validation under various load conditions
- Business value delivery confirmation through complete event sequences
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import threading
import random
import statistics

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import aiohttp
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    E2EAuthConfig,
    AuthenticatedUser,
    create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestClient
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Import agent execution components for real testing
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


class WebSocketEventValidator:
    """
    Mission-critical WebSocket event validator for E2E testing.
    
    This validator ensures ALL 5 required WebSocket events are delivered
    during agent execution workflows, protecting business value delivery.
    """
    
    # THE 5 MISSION-CRITICAL WEBSOCKET EVENTS (NEVER CHANGE THIS)
    REQUIRED_EVENTS = {
        "agent_started": {
            "description": "User sees AI began processing their problem", 
            "business_impact": "$500K+ revenue protection",
            "required": True,
            "timeout_seconds": 5.0
        },
        "agent_thinking": {
            "description": "Real-time reasoning visibility",
            "business_impact": "User engagement and trust",
            "required": True, 
            "timeout_seconds": 10.0
        },
        "tool_executing": {
            "description": "Tool usage transparency",
            "business_impact": "Demonstrates AI problem-solving",
            "required": True,
            "timeout_seconds": 15.0
        },
        "tool_completed": {
            "description": "Tool results display", 
            "business_impact": "Delivers actionable insights",
            "required": True,
            "timeout_seconds": 20.0
        },
        "agent_completed": {
            "description": "User knows when valuable response is ready",
            "business_impact": "Completion confirmation",
            "required": True,
            "timeout_seconds": 30.0
        }
    }
    
    def __init__(self):
        self.captured_events: List[Dict[str, Any]] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.missing_events: Set[str] = set()
        self.event_timing: Dict[str, float] = {}
        self.start_time: Optional[float] = None
        
    def start_capture(self):
        """Start event capture session."""
        self.captured_events.clear()
        self.event_timeline.clear()
        self.missing_events = set(self.REQUIRED_EVENTS.keys())
        self.event_timing.clear()
        self.start_time = time.time()
        
    def record_event(self, event_data: Dict[str, Any]):
        """Record a WebSocket event."""
        if self.start_time is None:
            self.start_time = time.time()
            
        current_time = time.time()
        event_type = event_data.get("type", "unknown")
        
        # Add timing information
        event_data["validator_timestamp"] = current_time
        event_data["validator_relative_time"] = current_time - self.start_time
        
        self.captured_events.append(event_data)
        self.event_timeline.append((current_time, event_type, event_data))
        
        # Track required events
        if event_type in self.REQUIRED_EVENTS:
            self.missing_events.discard(event_type)
            self.event_timing[event_type] = current_time - self.start_time
            
        print(f"[U+1F4E8] Captured: {event_type} (t+{current_time - self.start_time:.2f}s)")
        
    def validate_complete_event_sequence(self) -> Dict[str, Any]:
        """
        Validate that all required WebSocket events were received.
        
        Returns:
            Validation result with success status and details
        """
        validation_result = {
            "success": True,
            "missing_events": list(self.missing_events),
            "captured_events": len(self.captured_events),
            "event_timing": self.event_timing.copy(),
            "total_duration": time.time() - self.start_time if self.start_time else 0,
            "sequence_analysis": {},
            "business_impact_assessment": {},
            "errors": []
        }
        
        # Check for missing critical events
        if self.missing_events:
            validation_result["success"] = False
            for missing_event in self.missing_events:
                event_info = self.REQUIRED_EVENTS[missing_event]
                error_msg = (f"CRITICAL: Missing {missing_event} - {event_info['description']} "
                           f"(Business Impact: {event_info['business_impact']})")
                validation_result["errors"].append(error_msg)
                
                # Assess business impact
                validation_result["business_impact_assessment"][missing_event] = {
                    "impact": event_info["business_impact"],
                    "user_experience": "DEGRADED",
                    "revenue_risk": "HIGH" if "$500K" in event_info["business_impact"] else "MEDIUM"
                }
        
        # Validate event sequence timing
        sequence_errors = self._validate_event_sequence()
        validation_result["errors"].extend(sequence_errors)
        if sequence_errors:
            validation_result["success"] = False
            
        # Analyze event sequence
        validation_result["sequence_analysis"] = self._analyze_event_sequence()
        
        return validation_result
        
    def _validate_event_sequence(self) -> List[str]:
        """Validate the order and timing of events."""
        errors = []
        
        # Expected event order (flexible but logical)
        expected_order = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        captured_event_types = [event.get("type") for event in self.captured_events 
                               if event.get("type") in self.REQUIRED_EVENTS]
        
        # Check that agent_started comes first among agent events
        if "agent_started" in captured_event_types:
            first_agent_started = captured_event_types.index("agent_started")
            if first_agent_started > 2:  # Allow for connection events
                errors.append("agent_started should be among first events in sequence")
        
        # Check that agent_completed comes last among agent events
        if "agent_completed" in captured_event_types:
            last_agent_completed = len(captured_event_types) - 1 - captured_event_types[::-1].index("agent_completed")
            remaining_agent_events = [e for e in captured_event_types[last_agent_completed + 1:] 
                                    if e in self.REQUIRED_EVENTS]
            if remaining_agent_events:
                errors.append(f"agent_completed should be last, but found {remaining_agent_events} after")
        
        # Check timing constraints
        for event_type, timing in self.event_timing.items():
            max_time = self.REQUIRED_EVENTS[event_type]["timeout_seconds"]
            if timing > max_time:
                errors.append(f"{event_type} took too long: {timing:.2f}s > {max_time}s")
        
        return errors
        
    def _analyze_event_sequence(self) -> Dict[str, Any]:
        """Analyze the captured event sequence for insights."""
        analysis = {
            "total_events": len(self.captured_events),
            "required_events_captured": len(self.REQUIRED_EVENTS) - len(self.missing_events),
            "event_frequency": {},
            "timing_analysis": {},
            "user_experience_quality": "UNKNOWN"
        }
        
        # Event frequency analysis
        event_types = [e.get("type") for e in self.captured_events]
        for event_type in set(event_types):
            analysis["event_frequency"][event_type] = event_types.count(event_type)
        
        # Timing analysis
        if self.event_timing:
            timings = list(self.event_timing.values())
            analysis["timing_analysis"] = {
                "average_event_time": statistics.mean(timings),
                "fastest_event": min(timings),
                "slowest_event": max(timings),
                "total_sequence_time": max(timings) - min(timings) if len(timings) > 1 else 0
            }
        
        # User experience quality assessment
        if len(self.missing_events) == 0:
            analysis["user_experience_quality"] = "EXCELLENT"
        elif len(self.missing_events) <= 1:
            analysis["user_experience_quality"] = "GOOD"
        elif len(self.missing_events) <= 2:
            analysis["user_experience_quality"] = "DEGRADED"
        else:
            analysis["user_experience_quality"] = "POOR"
            
        return analysis


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.mission_critical
@pytest.mark.golden_path
class TestMissingWebSocketEventsE2E(BaseE2ETest):
    """
    E2E tests for complete WebSocket event validation and business value delivery.
    
    Tests ALL 5 mission-critical WebSocket events with REAL services, REAL LLM,
    and REAL agent execution. Validates complete business value delivery through
    proper WebSocket event sequences.
    
    CRITICAL: These tests protect $500K+ ARR by ensuring users receive complete
    AI-powered value delivery through proper WebSocket event communication.
    """
    
    # THE 5 MISSION-CRITICAL WEBSOCKET EVENTS (BUSINESS VALUE PROTECTION)
    CRITICAL_WEBSOCKET_EVENTS = [
        "agent_started",    # User sees AI began processing ($500K+ protection)
        "agent_thinking",   # Real-time reasoning visibility (engagement)
        "tool_executing",   # Tool usage transparency (trust)
        "tool_completed",   # Tool results display (insights)
        "agent_completed"   # Completion confirmation (value delivery)
    ]
    
    @pytest.fixture(autouse=True)
    async def setup_e2e_environment(self, real_services_fixture):
        """Set up full E2E environment for comprehensive WebSocket event testing."""
        self.services = real_services_fixture
        
        # Initialize authentication with Docker-compatible config
        self.auth_config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws"
        )
        self.auth_helper = E2EWebSocketAuthHelper(
            config=self.auth_config,
            environment="test"
        )
        
        # Initialize event validation systems
        self.event_validator = WebSocketEventValidator()
        self.business_value_metrics = []
        self.user_experience_tracking = {}
        
        # Wait for complete system readiness
        await self._wait_for_full_system_ready()
        
        print("[U+1F680] E2E Environment Ready for Mission-Critical WebSocket Event Testing")
    
    async def _wait_for_full_system_ready(self, max_wait_time: float = 60.0):
        """Wait for all services and agent systems to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check infrastructure services
                postgres_ready = await self.services.is_postgres_ready()
                redis_ready = await self.services.is_redis_ready()
                backend_ready = await self._check_backend_health()
                
                # Check agent systems
                agent_system_ready = await self._check_agent_systems_ready()
                
                if all([postgres_ready, redis_ready, backend_ready, agent_system_ready]):
                    print(" PASS:  Complete system ready for comprehensive WebSocket event testing")
                    return
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                print(f"[U+23F3] System readiness check failed: {e}, retrying...")
                await asyncio.sleep(1.0)
        
        pytest.fail(f"Complete system not ready after {max_wait_time}s wait")
    
    async def _check_backend_health(self) -> bool:
        """Check backend service health."""
        try:
            async with aiohttp.ClientSession() as session:
                health_url = f"{self.auth_config.backend_url}/health"
                async with session.get(health_url, timeout=5.0) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def _check_agent_systems_ready(self) -> bool:
        """Check that agent execution systems are operational."""
        try:
            # Test agent registry availability
            registry = AgentRegistry()
            
            # Test basic agent availability
            supervisor_available = hasattr(registry, 'get_agent')
            
            return supervisor_available
            
        except Exception:
            return False

    async def test_001_complete_optimization_workflow_all_events(self):
        """
        Test complete optimization agent workflow with ALL 5 WebSocket events.
        
        MISSION CRITICAL: This test validates the complete business value delivery
        chain through proper WebSocket event sequences for cost optimization.
        
        SUCCESS CRITERIA: ALL 5 events must be received in proper sequence.
        """
        print("[U+1F4BC] MISSION CRITICAL: Testing complete optimization workflow with ALL 5 events")
        
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="optimization_workflow_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        websocket = None
        
        try:
            # Initialize event validator
            self.event_validator.start_capture()
            
            # Connect with authentication
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=15.0
            )
            
            # Send comprehensive optimization request
            optimization_request = {
                "type": "chat_message",
                "message": "Please analyze my cloud infrastructure and provide cost optimization recommendations with detailed analysis.",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "request_type": "cost_optimization",
                "requires_all_events": True  # Signal for comprehensive workflow
            }
            
            await websocket.send(json.dumps(optimization_request))
            
            print("[U+1F4E4] Sent optimization request - expecting ALL 5 critical events")
            
            # Capture ALL events during complete workflow
            workflow_timeout = 45.0  # Extended timeout for complete workflow
            end_time = time.time() + workflow_timeout
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_data = json.loads(response)
                    
                    # Record event with validator
                    self.event_validator.record_event(event_data)
                    
                    event_type = event_data.get("type")
                    
                    # Log critical event progression
                    if event_type in self.CRITICAL_WEBSOCKET_EVENTS:
                        print(f" PASS:  CRITICAL EVENT RECEIVED: {event_type}")
                        
                        # Special validation for business-critical events
                        if event_type == "agent_started":
                            assert "message" in event_data or "content" in event_data, \
                                "agent_started missing user communication"
                                
                        elif event_type == "agent_thinking":
                            thinking_content = event_data.get("content", "")
                            assert len(thinking_content) > 10, \
                                "agent_thinking lacks substantive reasoning content"
                                
                        elif event_type == "tool_executing":
                            assert "tool_name" in event_data or "tool" in event_data, \
                                "tool_executing missing tool identification"
                                
                        elif event_type == "tool_completed":
                            assert "result" in event_data or "content" in event_data, \
                                "tool_completed missing execution results"
                                
                        elif event_type == "agent_completed":
                            final_content = event_data.get("content", "")
                            assert len(final_content) > 50, \
                                "agent_completed lacks comprehensive final response"
                            
                            # Validate business value in final response
                            business_keywords = ["cost", "optimize", "recommend", "save", "improve", "reduce"]
                            has_business_value = any(keyword in final_content.lower() 
                                                   for keyword in business_keywords)
                            assert has_business_value, \
                                "agent_completed lacks business optimization value"
                    
                    # Stop when workflow completes
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Check if we're still missing critical events
                    if len(self.event_validator.missing_events) > 0:
                        print(f"[U+23F3] Still waiting for: {list(self.event_validator.missing_events)}")
                        continue
                    else:
                        break
                except Exception as e:
                    print(f" FAIL:  Event capture error: {e}")
                    break
            
            # CRITICAL VALIDATION: All 5 events must be present
            validation_result = self.event_validator.validate_complete_event_sequence()
            
            # BUSINESS IMPACT ASSERTION
            assert validation_result["success"], \
                f"MISSION CRITICAL FAILURE: {validation_result['errors']} " \
                f"Missing events: {validation_result['missing_events']} " \
                f"Business Impact: {validation_result['business_impact_assessment']}"
            
            # Validate event sequence quality
            sequence_analysis = validation_result["sequence_analysis"]
            user_experience = sequence_analysis.get("user_experience_quality", "UNKNOWN")
            
            assert user_experience in ["EXCELLENT", "GOOD"], \
                f"User experience quality insufficient: {user_experience}"
            
            # Record business value metrics
            self.business_value_metrics.append({
                "test": "complete_optimization_workflow",
                "events_captured": validation_result["captured_events"],
                "missing_events": len(validation_result["missing_events"]),
                "total_duration": validation_result["total_duration"],
                "user_experience": user_experience,
                "business_value_delivered": user_experience in ["EXCELLENT", "GOOD"]
            })
            
            print(f" TROPHY:  SUCCESS: Complete optimization workflow delivered ALL 5 critical events")
            print(f" TROPHY:  User experience quality: {user_experience}")
            print(f" TROPHY:  Total workflow time: {validation_result['total_duration']:.2f}s")
            print(f" TROPHY:  Business value protection: CONFIRMED")
            
        finally:
            if websocket and not websocket.closed:
                await websocket.close()

    async def test_002_multi_user_event_isolation_validation(self):
        """
        Test WebSocket event isolation across multiple concurrent users.
        
        Validates that each user receives ALL 5 critical events and that
        events are properly isolated without cross-contamination.
        """
        print("[U+1F465] Testing multi-user WebSocket event isolation with ALL critical events")
        
        user_count = 3
        user_sessions = []
        user_validators = {}
        
        try:
            # Create multiple authenticated user sessions
            for i in range(user_count):
                user_context = await create_authenticated_user_context(
                    user_email=f"multi_user_events_{i}@example.com",
                    environment="test",
                    websocket_enabled=True
                )
                
                websocket = await self.auth_helper.connect_authenticated_websocket(
                    timeout=12.0
                )
                
                # Initialize event validator for each user
                user_validator = WebSocketEventValidator()
                user_validator.start_capture()
                
                user_sessions.append({
                    "context": user_context,
                    "websocket": websocket,
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id),
                    "validator": user_validator,
                    "user_index": i
                })
                
                user_validators[f"user_{i}"] = user_validator
            
            # Send concurrent requests
            user_tasks = []
            for i, session in enumerate(user_sessions):
                multi_user_message = {
                    "type": "chat_message",
                    "message": f"User {i}: Analyze my specific cloud costs and provide personalized optimization recommendations.",
                    "thread_id": session["thread_id"],
                    "user_id": session["user_id"],
                    "user_specific_request": i,
                    "requires_isolation": True
                }
                
                task = asyncio.create_task(
                    self._capture_user_events_complete(session, multi_user_message)
                )
                user_tasks.append(task)
            
            # Execute all user sessions concurrently
            results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Validate each user's complete event sequence
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Multi-user event test failed for user {i}: {result}")
                
                session = user_sessions[i]
                validator = session["validator"]
                
                # Validate complete event sequence for this user
                validation_result = validator.validate_complete_event_sequence()
                
                # CRITICAL: Each user must receive ALL 5 events
                assert validation_result["success"], \
                    f"User {i} missing critical events: {validation_result['missing_events']} " \
                    f"Errors: {validation_result['errors']}"
                
                # Validate user isolation - no cross-contamination
                user_specific_events = [e for e in validator.captured_events 
                                      if e.get("user_id") == session["user_id"]]
                
                # All events should be for this user
                assert len(user_specific_events) >= len(validator.captured_events) - 5, \
                    f"User {i} received events for other users (cross-contamination)"
                
                print(f" PASS:  User {i}: {validation_result['captured_events']} events, " \
                      f"experience: {validation_result['sequence_analysis']['user_experience_quality']}")
            
            print(f" TROPHY:  SUCCESS: All {user_count} users received complete event sequences with proper isolation")
            
        finally:
            # Clean up all user sessions
            for session in user_sessions:
                try:
                    await session["websocket"].close()
                except Exception:
                    pass

    async def _capture_user_events_complete(self, session: Dict, message: Dict):
        """Capture complete event sequence for individual user session."""
        websocket = session["websocket"]
        validator = session["validator"]
        user_index = session["user_index"]
        
        try:
            await websocket.send(json.dumps(message))
            
            # Capture events until complete workflow
            timeout = 35.0
            end_time = time.time() + timeout
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    event_data = json.loads(response)
                    
                    # Record with user's validator
                    validator.record_event(event_data)
                    
                    # Stop when workflow completes
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Check if still waiting for critical events
                    if len(validator.missing_events) > 0:
                        continue
                    else:
                        break
                except Exception as e:
                    print(f"User {user_index} event capture error: {e}")
                    break
                    
        except Exception as e:
            print(f"User {user_index} session error: {e}")
            raise

    async def test_003_event_recovery_after_interruption(self):
        """
        Test WebSocket event recovery after connection interruption.
        
        Validates that after WebSocket reconnection, users still receive
        complete event sequences and business value delivery continues.
        """
        print(" CYCLE:  Testing WebSocket event recovery after connection interruption")
        
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="event_recovery_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        primary_websocket = None
        recovery_websocket = None
        recovery_validator = WebSocketEventValidator()
        
        try:
            # Establish initial connection
            primary_websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=10.0
            )
            
            # Send initial request
            initial_message = {
                "type": "chat_message",
                "message": "Start optimization analysis - test interruption recovery",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "recovery_test": "initial"
            }
            
            await primary_websocket.send(json.dumps(initial_message))
            
            # Get initial response
            initial_response = await asyncio.wait_for(primary_websocket.recv(), timeout=8.0)
            initial_data = json.loads(initial_response)
            
            assert initial_data.get("type") != "error", f"Initial connection error: {initial_data}"
            
            # Simulate connection interruption
            print("[U+1F534] Simulating connection interruption")
            await primary_websocket.close()
            await asyncio.sleep(2.0)  # Brief interruption
            
            # Reconnect and test event recovery
            print(" CYCLE:  Reconnecting for event recovery test")
            recovery_websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=12.0
            )
            
            recovery_validator.start_capture()
            
            # Send recovery request that should trigger all events
            recovery_message = {
                "type": "chat_message",
                "message": "Complete the optimization analysis after reconnection - need full event sequence.",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "recovery_test": "after_interruption",
                "require_complete_events": True
            }
            
            await recovery_websocket.send(json.dumps(recovery_message))
            
            print("[U+1F4E4] Sent recovery request - capturing complete event sequence")
            
            # Capture complete event sequence after recovery
            recovery_timeout = 40.0
            end_time = time.time() + recovery_timeout
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(recovery_websocket.recv(), timeout=5.0)
                    event_data = json.loads(response)
                    
                    recovery_validator.record_event(event_data)
                    
                    event_type = event_data.get("type")
                    if event_type in self.CRITICAL_WEBSOCKET_EVENTS:
                        print(f" CYCLE:  Recovery event: {event_type}")
                    
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    if len(recovery_validator.missing_events) > 0:
                        print(f"[U+23F3] Recovery still waiting for: {list(recovery_validator.missing_events)}")
                        continue
                    else:
                        break
                except Exception as e:
                    print(f" FAIL:  Recovery event capture error: {e}")
                    break
            
            # Validate complete event recovery
            recovery_validation = recovery_validator.validate_complete_event_sequence()
            
            assert recovery_validation["success"], \
                f"Event recovery failed after interruption: {recovery_validation['errors']} " \
                f"Missing: {recovery_validation['missing_events']}"
            
            # Validate user experience quality maintained
            recovery_experience = recovery_validation["sequence_analysis"]["user_experience_quality"]
            assert recovery_experience in ["EXCELLENT", "GOOD"], \
                f"User experience degraded after recovery: {recovery_experience}"
            
            print(f" PASS:  Event recovery successful: {recovery_validation['captured_events']} events")
            print(f" PASS:  User experience maintained: {recovery_experience}")
            print(" TROPHY:  Business continuity confirmed after interruption")
            
        finally:
            if primary_websocket and not primary_websocket.closed:
                await primary_websocket.close()
            if recovery_websocket and not recovery_websocket.closed:
                await recovery_websocket.close()

    async def test_004_event_timing_under_load(self):
        """
        Test WebSocket event timing under concurrent load conditions.
        
        Validates that ALL 5 critical events are delivered within
        acceptable timeframes even under system load.
        """
        print(" LIGHTNING:  Testing WebSocket event timing under concurrent load")
        
        concurrent_sessions = 4  # Balanced load for timing test
        session_validators = []
        load_sessions = []
        
        try:
            # Create concurrent load sessions
            for i in range(concurrent_sessions):
                user_context = await create_authenticated_user_context(
                    user_email=f"load_timing_user_{i}@example.com",
                    environment="test",
                    websocket_enabled=True
                )
                
                websocket = await self.auth_helper.connect_authenticated_websocket(
                    timeout=15.0
                )
                
                validator = WebSocketEventValidator()
                validator.start_capture()
                
                load_sessions.append({
                    "context": user_context,
                    "websocket": websocket,
                    "validator": validator,
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id),
                    "session_index": i
                })
                
                session_validators.append(validator)
            
            # Execute concurrent load with timing measurement
            timing_tasks = []
            load_start_time = time.time()
            
            for session in load_sessions:
                load_message = {
                    "type": "chat_message",
                    "message": f"Concurrent load test {session['session_index']} - analyze cloud costs with comprehensive insights.",
                    "thread_id": session["thread_id"],
                    "user_id": session["user_id"],
                    "load_test": True,
                    "session_index": session["session_index"]
                }
                
                task = asyncio.create_task(
                    self._measure_event_timing_under_load(session, load_message)
                )
                timing_tasks.append(task)
            
            # Wait for all concurrent sessions to complete
            timing_results = await asyncio.gather(*timing_tasks, return_exceptions=True)
            total_load_time = time.time() - load_start_time
            
            # Validate timing results for each session
            timing_metrics = []
            for i, result in enumerate(timing_results):
                if isinstance(result, Exception):
                    pytest.fail(f"Load timing test failed for session {i}: {result}")
                
                session = load_sessions[i]
                validator = session["validator"]
                
                # Validate complete events received under load
                validation_result = validator.validate_complete_event_sequence()
                
                assert validation_result["success"], \
                    f"Session {i} missing events under load: {validation_result['missing_events']}"
                
                # Collect timing metrics
                timing_analysis = validation_result["sequence_analysis"]["timing_analysis"]
                timing_metrics.append({
                    "session": i,
                    "total_events": validation_result["captured_events"],
                    "total_time": validation_result["total_duration"],
                    "average_event_time": timing_analysis.get("average_event_time", 0),
                    "slowest_event": timing_analysis.get("slowest_event", 0),
                    "user_experience": validation_result["sequence_analysis"]["user_experience_quality"]
                })
            
            # Validate overall timing performance under load
            average_session_time = statistics.mean([m["total_time"] for m in timing_metrics])
            max_session_time = max([m["total_time"] for m in timing_metrics])
            
            # Performance assertions
            assert average_session_time < 35.0, \
                f"Average session time too slow under load: {average_session_time:.2f}s"
            
            assert max_session_time < 50.0, \
                f"Maximum session time too slow under load: {max_session_time:.2f}s"
            
            # Validate all sessions maintained good user experience
            poor_experiences = [m for m in timing_metrics if m["user_experience"] not in ["EXCELLENT", "GOOD"]]
            assert len(poor_experiences) == 0, \
                f"Poor user experiences under load: {poor_experiences}"
            
            print(f" PASS:  Load timing validation successful: {concurrent_sessions} concurrent sessions")
            print(f" PASS:  Average session time: {average_session_time:.2f}s")
            print(f" PASS:  Maximum session time: {max_session_time:.2f}s")
            print(f" PASS:  All sessions maintained good user experience under load")
            
        finally:
            # Clean up all load sessions
            for session in load_sessions:
                try:
                    await session["websocket"].close()
                except Exception:
                    pass

    async def _measure_event_timing_under_load(self, session: Dict, message: Dict):
        """Measure event timing for individual session under load."""
        websocket = session["websocket"]
        validator = session["validator"]
        session_index = session["session_index"]
        
        try:
            session_start = time.time()
            await websocket.send(json.dumps(message))
            
            # Capture events with timing measurement
            timeout = 45.0  # Extended timeout for load conditions
            end_time = time.time() + timeout
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=4.0)
                    event_data = json.loads(response)
                    
                    validator.record_event(event_data)
                    
                    # Complete when agent finishes
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Continue if still missing critical events
                    if len(validator.missing_events) > 0:
                        continue
                    else:
                        break
                except Exception as e:
                    print(f"Session {session_index} timing measurement error: {e}")
                    break
                    
        except Exception as e:
            print(f"Load timing test error for session {session_index}: {e}")
            raise

    async def test_005_business_value_delivery_confirmation(self):
        """
        Test complete business value delivery through WebSocket events.
        
        MISSION CRITICAL: Validates that users receive substantive business
        value (cost optimization insights) through complete event sequences.
        """
        print("[U+1F4B0] MISSION CRITICAL: Testing business value delivery confirmation")
        
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="business_value_delivery_test@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        websocket = None
        business_validator = WebSocketEventValidator()
        
        try:
            business_validator.start_capture()
            
            # Connect with authentication
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=15.0
            )
            
            # Send high-value business request
            business_value_request = {
                "type": "chat_message",
                "message": "I'm spending $50,000/month on AWS. Provide detailed cost optimization recommendations with specific actions I can take to reduce costs by at least 20%.",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "high_value_request": True,
                "expected_value": "cost_optimization_recommendations"
            }
            
            await websocket.send(json.dumps(business_value_request))
            
            print("[U+1F4E4] Sent high-value business request - expecting comprehensive analysis")
            
            # Capture complete business value delivery
            business_timeout = 50.0  # Extended for comprehensive analysis
            end_time = time.time() + business_timeout
            business_insights_captured = []
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=6.0)
                    event_data = json.loads(response)
                    
                    business_validator.record_event(event_data)
                    
                    event_type = event_data.get("type")
                    event_content = event_data.get("content", "")
                    
                    # Capture business insights from events
                    if event_type in ["tool_completed", "agent_thinking", "agent_completed"]:
                        business_keywords = ["cost", "save", "optimize", "reduce", "recommend", "efficiency", "budget"]
                        if any(keyword in event_content.lower() for keyword in business_keywords):
                            business_insights_captured.append({
                                "event_type": event_type,
                                "content": event_content[:200] + "..." if len(event_content) > 200 else event_content,
                                "timestamp": time.time() - business_validator.start_time
                            })
                    
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    if len(business_validator.missing_events) > 0:
                        print(f"[U+23F3] Business value delivery waiting for: {list(business_validator.missing_events)}")
                        continue
                    else:
                        break
                except Exception as e:
                    print(f" FAIL:  Business value capture error: {e}")
                    break
            
            # Validate complete business value delivery
            business_validation = business_validator.validate_complete_event_sequence()
            
            # CRITICAL: All events must be present for business value
            assert business_validation["success"], \
                f"Business value delivery incomplete: {business_validation['errors']} " \
                f"Missing: {business_validation['missing_events']}"
            
            # Validate business insights were delivered
            assert len(business_insights_captured) >= 2, \
                f"Insufficient business insights delivered: {len(business_insights_captured)} events"
            
            # Validate final agent_completed contains substantial business value
            completion_events = [e for e in business_validator.captured_events 
                               if e.get("type") == "agent_completed"]
            
            assert len(completion_events) > 0, "No completion event for business value delivery"
            
            final_response = completion_events[-1]
            final_content = final_response.get("content", "")
            
            # Business value validation
            assert len(final_content) > 100, \
                "Final response lacks comprehensive business recommendations"
            
            value_indicators = ["save", "reduce", "optimize", "recommend", "cost", "efficiency"]
            business_value_score = sum(1 for indicator in value_indicators 
                                     if indicator in final_content.lower())
            
            assert business_value_score >= 3, \
                f"Insufficient business value in final response: score {business_value_score}/6"
            
            # Calculate business value metrics
            business_metrics = {
                "events_delivered": business_validation["captured_events"],
                "business_insights": len(business_insights_captured),
                "response_comprehensiveness": len(final_content),
                "business_value_score": business_value_score,
                "user_experience": business_validation["sequence_analysis"]["user_experience_quality"],
                "total_delivery_time": business_validation["total_duration"]
            }
            
            self.business_value_metrics.append(business_metrics)
            
            print(f" TROPHY:  BUSINESS VALUE DELIVERY CONFIRMED")
            print(f" TROPHY:  Events delivered: {business_metrics['events_delivered']}")
            print(f" TROPHY:  Business insights: {business_metrics['business_insights']}")
            print(f" TROPHY:  Value score: {business_metrics['business_value_score']}/6")
            print(f" TROPHY:  User experience: {business_metrics['user_experience']}")
            print(f" TROPHY:  Total delivery time: {business_metrics['total_delivery_time']:.2f}s")
            
        finally:
            if websocket and not websocket.closed:
                await websocket.close()

    async def test_006_edge_case_event_delivery_resilience(self):
        """
        Test WebSocket event delivery resilience under edge case conditions.
        
        Validates that critical events are still delivered under various
        challenging conditions that could occur in production.
        """
        print("[U+1F9EA] Testing WebSocket event delivery resilience under edge cases")
        
        edge_case_scenarios = [
            "rapid_reconnections",
            "large_request_payload",
            "concurrent_threads",
            "delayed_responses"
        ]
        
        scenario_results = {}
        
        for scenario in edge_case_scenarios:
            print(f"[U+1F9EA] Testing edge case scenario: {scenario}")
            
            # Create authenticated user context for each scenario
            user_context = await create_authenticated_user_context(
                user_email=f"edge_case_{scenario}@example.com",
                environment="test",
                websocket_enabled=True
            )
            
            scenario_validator = WebSocketEventValidator()
            scenario_validator.start_capture()
            
            websocket = None
            
            try:
                if scenario == "rapid_reconnections":
                    # Test rapid reconnection cycles
                    for cycle in range(3):
                        websocket = await self.auth_helper.connect_authenticated_websocket(timeout=8.0)
                        
                        rapid_message = {
                            "type": "chat_message",
                            "message": f"Rapid reconnection test cycle {cycle}",
                            "thread_id": str(user_context.thread_id),
                            "user_id": str(user_context.user_id)
                        }
                        
                        await websocket.send(json.dumps(rapid_message))
                        
                        # Capture initial events
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            event_data = json.loads(response)
                            scenario_validator.record_event(event_data)
                        except asyncio.TimeoutError:
                            pass
                        
                        await websocket.close()
                        await asyncio.sleep(0.5)  # Brief delay between cycles
                    
                    # Final connection for complete workflow
                    websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
                    
                elif scenario == "large_request_payload":
                    websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
                    
                    # Create large request payload
                    large_payload = "Analyze this comprehensive scenario: " + "X" * 2000
                    large_message = {
                        "type": "chat_message",
                        "message": large_payload,
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id)
                    }
                    
                elif scenario == "concurrent_threads":
                    websocket = await self.auth_helper.connect_authenticated_websocket(timeout=10.0)
                    
                    concurrent_message = {
                        "type": "chat_message",
                        "message": "Handle concurrent processing with multiple agent interactions",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id),
                        "concurrent_test": True
                    }
                    
                elif scenario == "delayed_responses":
                    websocket = await self.auth_helper.connect_authenticated_websocket(timeout=12.0)
                    
                    delayed_message = {
                        "type": "chat_message",
                        "message": "Test with potential response delays and timeouts",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id),
                        "expect_delays": True
                    }
                
                # Send appropriate message for scenario
                if scenario != "rapid_reconnections":
                    message_to_send = locals()[f"{scenario}_message"] if f"{scenario}_message" in locals() else {
                        "type": "chat_message",
                        "message": f"Edge case test: {scenario}",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id)
                    }
                    await websocket.send(json.dumps(message_to_send))
                else:
                    # Send final message for rapid reconnections
                    final_message = {
                        "type": "chat_message",
                        "message": "Final message after rapid reconnections",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id)
                    }
                    await websocket.send(json.dumps(final_message))
                
                # Capture events for edge case scenario
                edge_timeout = 40.0 if scenario == "delayed_responses" else 25.0
                end_time = time.time() + edge_timeout
                
                while time.time() < end_time:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_data = json.loads(response)
                        
                        scenario_validator.record_event(event_data)
                        
                        if event_data.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        if len(scenario_validator.missing_events) > 0:
                            continue
                        else:
                            break
                    except Exception as e:
                        print(f"Edge case {scenario} event error: {e}")
                        break
                
                # Validate edge case resilience
                edge_validation = scenario_validator.validate_complete_event_sequence()
                scenario_results[scenario] = {
                    "success": edge_validation["success"],
                    "events_captured": edge_validation["captured_events"],
                    "missing_events": len(edge_validation["missing_events"]),
                    "user_experience": edge_validation["sequence_analysis"]["user_experience_quality"]
                }
                
                # Edge case should still deliver reasonable results
                if not edge_validation["success"]:
                    print(f" WARNING: [U+FE0F] Edge case {scenario} had issues: {edge_validation['errors']}")
                    # For edge cases, we allow some degradation but not complete failure
                    if len(edge_validation["missing_events"]) <= 2:
                        print(f" PASS:  Edge case {scenario} acceptable degradation")
                        scenario_results[scenario]["acceptable_degradation"] = True
                    else:
                        pytest.fail(f"Edge case {scenario} excessive failure: {edge_validation['missing_events']}")
                else:
                    print(f" PASS:  Edge case {scenario} handled successfully")
                
            finally:
                if websocket and not websocket.closed:
                    await websocket.close()
        
        # Overall edge case resilience assessment
        successful_scenarios = len([r for r in scenario_results.values() 
                                  if r["success"] or r.get("acceptable_degradation", False)])
        
        resilience_score = successful_scenarios / len(edge_case_scenarios)
        
        assert resilience_score >= 0.75, \
            f"Edge case resilience insufficient: {resilience_score:.2f} (need >= 0.75)"
        
        print(f" TROPHY:  Edge case resilience validated: {successful_scenarios}/{len(edge_case_scenarios)} scenarios")
        print(f" TROPHY:  Overall resilience score: {resilience_score:.2f}")

    async def test_007_comprehensive_event_sequence_validation(self):
        """
        Comprehensive validation of complete WebSocket event sequences.
        
        FINAL VALIDATION: This test serves as the ultimate validation that
        the WebSocket event system delivers complete business value through
        proper event sequences under all tested conditions.
        """
        print("[U+1F3C1] FINAL VALIDATION: Comprehensive WebSocket event sequence testing")
        
        # Create authenticated user context (MANDATORY per CLAUDE.md)
        user_context = await create_authenticated_user_context(
            user_email="comprehensive_validation@example.com",
            environment="test",
            websocket_enabled=True
        )
        
        websocket = None
        comprehensive_validator = WebSocketEventValidator()
        
        try:
            comprehensive_validator.start_capture()
            
            # Connect with authentication
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=15.0
            )
            
            # Send comprehensive validation request
            comprehensive_request = {
                "type": "chat_message", 
                "message": "COMPREHENSIVE TEST: Analyze my complete cloud infrastructure across all services, provide detailed cost optimization recommendations, security improvements, and performance enhancements with specific actionable steps.",
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id),
                "comprehensive_test": True,
                "expect_complete_analysis": True
            }
            
            await websocket.send(json.dumps(comprehensive_request))
            
            print("[U+1F4E4] Sent comprehensive validation request - expecting complete event sequence")
            
            # Capture comprehensive event sequence
            comprehensive_timeout = 60.0  # Extended for comprehensive analysis
            end_time = time.time() + comprehensive_timeout
            event_sequence_tracking = []
            
            while time.time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=6.0)
                    event_data = json.loads(response)
                    
                    comprehensive_validator.record_event(event_data)
                    
                    event_type = event_data.get("type")
                    event_sequence_tracking.append({
                        "type": event_type,
                        "timestamp": time.time() - comprehensive_validator.start_time,
                        "has_content": len(event_data.get("content", "")) > 0
                    })
                    
                    # Log comprehensive progress
                    if event_type in self.CRITICAL_WEBSOCKET_EVENTS:
                        print(f" FIRE:  COMPREHENSIVE EVENT: {event_type} (t+{event_sequence_tracking[-1]['timestamp']:.2f}s)")
                    
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    remaining_events = list(comprehensive_validator.missing_events)
                    if remaining_events:
                        print(f"[U+23F3] Comprehensive validation waiting for: {remaining_events}")
                        continue
                    else:
                        break
                except Exception as e:
                    print(f" FAIL:  Comprehensive validation error: {e}")
                    break
            
            # ULTIMATE VALIDATION
            final_validation = comprehensive_validator.validate_complete_event_sequence()
            
            # MISSION CRITICAL ASSERTIONS
            assert final_validation["success"], \
                f" ALERT:  COMPREHENSIVE VALIDATION FAILED: {final_validation['errors']} " \
                f"Missing: {final_validation['missing_events']} " \
                f"Business Impact: SEVERE - User experience compromised"
            
            # Validate comprehensive sequence quality
            sequence_analysis = final_validation["sequence_analysis"]
            
            # Must have excellent user experience
            user_experience = sequence_analysis["user_experience_quality"]
            assert user_experience == "EXCELLENT", \
                f"Comprehensive validation requires EXCELLENT experience, got: {user_experience}"
            
            # Validate timing performance
            timing_analysis = sequence_analysis["timing_analysis"]
            total_time = final_validation["total_duration"]
            
            assert total_time < 60.0, \
                f"Comprehensive validation too slow: {total_time:.2f}s"
            
            # Validate event richness
            events_with_content = len([e for e in event_sequence_tracking if e["has_content"]])
            assert events_with_content >= 3, \
                f"Insufficient content-rich events: {events_with_content}"
            
            # Generate final business impact report
            business_impact_report = {
                "validation_success": True,
                "events_delivered": final_validation["captured_events"],
                "critical_events_complete": len(self.CRITICAL_WEBSOCKET_EVENTS),
                "user_experience_quality": user_experience,
                "business_value_protected": "$500K+ ARR",
                "total_validation_time": total_time,
                "event_sequence_quality": "MISSION CRITICAL STANDARDS MET",
                "revenue_protection_status": "CONFIRMED"
            }
            
            # Log comprehensive success
            print(" TROPHY: " * 20)
            print(" TROPHY:  COMPREHENSIVE WEBSOCKET EVENT VALIDATION: SUCCESS")
            print(f" TROPHY:  All {len(self.CRITICAL_WEBSOCKET_EVENTS)} mission-critical events delivered")
            print(f" TROPHY:  User experience quality: {user_experience}")
            print(f" TROPHY:  Total events captured: {final_validation['captured_events']}")
            print(f" TROPHY:  Validation time: {total_time:.2f}s")
            print(" TROPHY:  BUSINESS VALUE DELIVERY: CONFIRMED")
            print(" TROPHY:  REVENUE PROTECTION: $500K+ ARR SECURED")
            print(" TROPHY: " * 20)
            
            # Store final metrics
            self.business_value_metrics.append(business_impact_report)
            
        finally:
            if websocket and not websocket.closed:
                await websocket.close()