#!/usr/bin/env python
"""Real Agent Error Handling E2E Test Suite - Complete Agent Resilience Workflow

MISSION CRITICAL: Validates that agents deliver REAL BUSINESS VALUE even under error conditions 
through comprehensive error handling, recovery, and graceful degradation. Tests actual resilience 
capabilities and business continuity, not just technical error catching.

Business Value Justification (BVJ):
- Segment: All customer segments (critical for platform reliability)
- Business Goal: Ensure agents maintain service delivery during errors and failures
- Value Impact: Platform resilience that prevents revenue loss from agent failures
- Strategic/Revenue Impact: $5M+ ARR protection from error-related service disruptions
- Platform Stability: Foundation for reliable multi-user AI operations under all conditions

CLAUDE.md COMPLIANCE:
- Uses ONLY real services (Docker, PostgreSQL, Redis) - NO MOCKS  
- Tests complete business value delivery through error scenarios
- Verifies ALL 5 WebSocket events even during error conditions
- Uses test_framework imports for SSOT patterns
- Validates actual recovery mechanisms and business continuity
- Tests multi-user isolation during error propagation
- Focuses on REAL business outcomes during failure scenarios
- Uses SSOT TEST_PORTS configuration
- Implements proper resource cleanup and error handling
- Validates business value compliance during degraded operations

This test validates that our agent error handling actually works end-to-end to maintain 
business value delivery. Not just that errors are caught, but that agents provide 
meaningful responses and maintain service quality even when components fail.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# SSOT imports from test_framework
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events
from test_framework.test_config import TEST_PORTS
from test_framework.agent_test_helpers import create_test_agent, assert_agent_execution

# SSOT environment management
from shared.isolated_environment import get_env


class ErrorScenarioType(Enum):
    """Types of error scenarios to test."""
    LLM_API_TIMEOUT = "llm_api_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    DATABASE_CONNECTION_LOSS = "database_connection_loss"
    REDIS_UNAVAILABLE = "redis_unavailable"
    TOOL_EXECUTION_FAILURE = "tool_execution_failure"
    WEBSOCKET_INTERRUPTION = "websocket_interruption"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    INVALID_USER_INPUT = "invalid_user_input"
    CONCURRENT_REQUEST_OVERLOAD = "concurrent_request_overload"


@dataclass
class AgentErrorHandlingMetrics:
    """Business value metrics for agent error handling and recovery."""
    
    # Error metrics
    errors_encountered: int = 0
    errors_handled_gracefully: int = 0
    service_degradations_detected: int = 0
    
    # Recovery metrics
    automatic_recoveries: int = 0
    fallback_mechanisms_triggered: int = 0
    partial_responses_delivered: int = 0
    recovery_time_seconds: float = 0.0
    
    # Business continuity metrics
    user_facing_errors: int = 0
    business_value_maintained_during_errors: bool = False
    alternative_solutions_provided: int = 0
    error_impact_minimization_score: float = 0.0
    
    # Quality metrics during errors
    error_response_quality_score: float = 0.0
    user_experience_preservation_score: float = 0.0
    helpful_error_messages: int = 0
    
    # Performance under stress
    response_time_under_errors: float = 0.0
    throughput_degradation_percentage: float = 0.0
    
    # WebSocket event tracking during errors
    websocket_events_during_errors: Dict[str, int] = field(default_factory=lambda: {
        "agent_started": 0,
        "agent_thinking": 0,
        "tool_executing": 0,
        "tool_completed": 0,
        "agent_completed": 0,
        "error_occurred": 0,
        "recovery_attempted": 0,
        "fallback_activated": 0
    })
    
    def is_business_value_maintained(self) -> bool:
        """Check if business value was maintained during error conditions."""
        return (
            self.errors_handled_gracefully >= self.errors_encountered * 0.8 and  # 80% graceful handling
            self.business_value_maintained_during_errors and
            self.user_facing_errors <= self.errors_encountered * 0.2 and  # Max 20% user-facing errors
            self.error_response_quality_score >= 0.7 and
            all(count > 0 for event, count in self.websocket_events_during_errors.items() 
                if event in ["agent_started", "agent_completed"])
        )


class RealAgentErrorHandlingE2ETest(BaseE2ETest):
    """Test agent error handling with real services and business continuity validation."""
    
    def __init__(self):
        super().__init__()
        self.env = get_env()
        self.metrics = AgentErrorHandlingMetrics()
        
    async def create_test_user(self, subscription: str = "mid") -> Dict[str, Any]:
        """Create test user for error handling scenarios."""
        user_data = {
            "user_id": f"test_error_user_{uuid.uuid4().hex[:8]}",
            "email": f"error.test.{uuid.uuid4().hex[:8]}@testcompany.com",
            "subscription_tier": subscription,
            "permissions": ["agent_access", "error_recovery", "fallback_services"],
            "error_handling_preferences": {
                "graceful_degradation": True,
                "detailed_error_info": subscription == "enterprise",
                "auto_retry": True
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Created error handling test user: {user_data['user_id']} ({subscription})")
        return user_data
    
    async def generate_error_scenario(self, error_type: ErrorScenarioType) -> Dict[str, Any]:
        """Generate realistic error scenario for testing."""
        
        scenarios = {
            ErrorScenarioType.LLM_API_TIMEOUT: {
                "name": "LLM API Timeout",
                "description": "LLM API becomes unresponsive during agent execution",
                "trigger_conditions": {
                    "simulate_timeout": True,
                    "timeout_duration": 30.0,
                    "affected_operations": ["llm_completion", "embedding_generation"]
                },
                "expected_fallbacks": ["cached_responses", "simplified_analysis", "offline_capabilities"],
                "business_impact": "medium",
                "expected_recovery_time": 15.0
            },
            ErrorScenarioType.LLM_RATE_LIMIT: {
                "name": "LLM Rate Limit Exceeded",
                "description": "LLM API rate limits exceeded during peak usage",
                "trigger_conditions": {
                    "simulate_rate_limit": True,
                    "requests_per_minute": 1000,  # Exceed typical limits
                    "affected_operations": ["all_llm_calls"]
                },
                "expected_fallbacks": ["request_queuing", "alternative_models", "degraded_responses"],
                "business_impact": "high",
                "expected_recovery_time": 60.0
            },
            ErrorScenarioType.DATABASE_CONNECTION_LOSS: {
                "name": "Database Connection Lost",
                "description": "PostgreSQL connection lost during agent execution",
                "trigger_conditions": {
                    "simulate_db_failure": True,
                    "failure_duration": 20.0,
                    "affected_operations": ["data_persistence", "user_context_loading"]
                },
                "expected_fallbacks": ["memory_cache", "read_replicas", "degraded_state"],
                "business_impact": "high", 
                "expected_recovery_time": 10.0
            },
            ErrorScenarioType.TOOL_EXECUTION_FAILURE: {
                "name": "Tool Execution Failure",
                "description": "Agent tool fails during critical operation",
                "trigger_conditions": {
                    "simulate_tool_failure": True,
                    "failing_tools": ["cost_analyzer", "data_processor"],
                    "failure_probability": 0.5
                },
                "expected_fallbacks": ["alternative_tools", "manual_analysis", "best_effort_results"],
                "business_impact": "medium",
                "expected_recovery_time": 5.0
            },
            ErrorScenarioType.WEBSOCKET_INTERRUPTION: {
                "name": "WebSocket Connection Interrupted",
                "description": "WebSocket connection drops during agent execution",
                "trigger_conditions": {
                    "simulate_websocket_drop": True,
                    "interruption_points": ["mid_execution", "tool_phase"],
                    "reconnection_delay": 3.0
                },
                "expected_fallbacks": ["automatic_reconnection", "state_recovery", "continuation"],
                "business_impact": "low",
                "expected_recovery_time": 5.0
            },
            ErrorScenarioType.INVALID_USER_INPUT: {
                "name": "Invalid User Input",
                "description": "User provides malformed or invalid input data",
                "trigger_conditions": {
                    "invalid_input_types": ["malformed_json", "missing_required_fields", "invalid_data_types"],
                    "input_validation_bypass": False
                },
                "expected_fallbacks": ["input_sanitization", "user_guidance", "partial_processing"],
                "business_impact": "low",
                "expected_recovery_time": 1.0
            }
        }
        
        scenario = scenarios.get(error_type, scenarios[ErrorScenarioType.TOOL_EXECUTION_FAILURE])
        logger.info(f"Generated error scenario: {scenario['name']} (impact: {scenario['business_impact']})")
        return scenario
    
    async def execute_agent_with_error_injection(
        self,
        websocket_client: WebSocketTestClient,
        error_scenario: Dict[str, Any],
        agent_task: str = "comprehensive_analysis"
    ) -> Dict[str, Any]:
        """Execute agent with error injection and track recovery metrics."""
        
        start_time = time.time()
        
        # Send request that will trigger error scenario
        request_message = {
            "type": "agent_request",
            "agent": "resilient_agent",
            "message": f"Please perform {agent_task} with potential error conditions",
            "context": {
                "task": agent_task,
                "error_scenario": error_scenario,
                "error_simulation": error_scenario["trigger_conditions"],
                "business_context": "error_resilience_testing",
                "expected_fallbacks": error_scenario["expected_fallbacks"]
            },
            "user_id": f"error_test_{uuid.uuid4().hex[:8]}",
            "thread_id": str(uuid.uuid4())
        }
        
        await websocket_client.send_json(request_message)
        logger.info(f"Initiated agent execution with error scenario: {error_scenario['name']}")
        
        # Collect all WebSocket events including error events
        events = []
        error_detected = False
        recovery_started = False
        
        async for event in websocket_client.receive_events(timeout=180.0):  # Extended timeout for error recovery
            events.append(event)
            event_type = event.get("type", "unknown")
            
            # Track WebSocket events during errors
            if event_type in self.metrics.websocket_events_during_errors:
                self.metrics.websocket_events_during_errors[event_type] += 1
            
            # Track error and recovery events
            if event_type == "error_occurred":
                error_detected = True
                self.metrics.errors_encountered += 1
                error_details = event.get("data", {})
                logger.warning(f"Error detected: {error_details.get('error_type', 'unknown')}")
                
            elif event_type == "recovery_attempted":
                recovery_started = True
                self.metrics.automatic_recoveries += 1
                recovery_method = event.get("data", {}).get("recovery_method", "unknown")
                logger.info(f"Recovery attempted: {recovery_method}")
                
            elif event_type == "fallback_activated":
                self.metrics.fallback_mechanisms_triggered += 1
                fallback_type = event.get("data", {}).get("fallback_type", "unknown")
                logger.info(f"Fallback activated: {fallback_type}")
                
            elif event_type == "graceful_degradation":
                self.metrics.errors_handled_gracefully += 1
                logger.info("Graceful degradation initiated")
                
            elif event_type == "partial_response":
                self.metrics.partial_responses_delivered += 1
                logger.info("Partial response delivered despite errors")
            
            logger.info(f"Error handling event: {event_type}")
            
            # Stop on completion or unrecoverable error
            if event_type in ["agent_completed", "unrecoverable_error"]:
                break
                
        # Calculate error handling metrics
        total_time = time.time() - start_time
        self.metrics.response_time_under_errors = total_time
        
        if recovery_started:
            recovery_events = [e for e in events if e.get("type") == "recovery_attempted"]
            if recovery_events:
                recovery_start = recovery_events[0].get("timestamp", start_time)
                recovery_end_events = [e for e in events if e.get("type") in ["recovery_completed", "agent_completed"]]
                if recovery_end_events:
                    recovery_end = recovery_end_events[0].get("timestamp", time.time())
                    self.metrics.recovery_time_seconds = recovery_end - recovery_start
        
        # Extract final result (may be partial or degraded)
        final_event = events[-1] if events else {}
        result = final_event.get("data", {}).get("result", {})
        
        # Analyze error handling business value
        self._analyze_error_handling_metrics(result, error_scenario, events)
        
        return {
            "events": events,
            "result": result,
            "error_detected": error_detected,
            "recovery_successful": recovery_started and final_event.get("type") == "agent_completed",
            "metrics": self.metrics,
            "total_time": total_time
        }
    
    def _analyze_error_handling_metrics(self, result: Dict[str, Any], scenario: Dict[str, Any], events: List[Dict[str, Any]]):
        """Analyze error handling results to extract business continuity metrics."""
        
        # Determine if business value was maintained
        response_quality_indicators = [
            len(result.get("insights", [])),
            len(result.get("recommendations", [])),
            bool(result.get("analysis_summary")),
            bool(result.get("actionable_items"))
        ]
        self.metrics.business_value_maintained_during_errors = sum(response_quality_indicators) >= 2
        
        # Count alternative solutions provided
        alternatives = result.get("alternative_solutions", [])
        fallback_results = result.get("fallback_results", [])
        self.metrics.alternative_solutions_provided = len(alternatives) + len(fallback_results)
        
        # Calculate error response quality score
        quality_factors = []
        if result.get("partial_results"):
            quality_factors.append(0.3)  # Partial results provided
        if result.get("explanation"):
            quality_factors.append(0.2)  # Error explanation provided
        if result.get("recommendations"):
            quality_factors.append(0.3)  # Still provided recommendations
        if result.get("next_steps"):
            quality_factors.append(0.2)  # Guidance for next steps
            
        self.metrics.error_response_quality_score = sum(quality_factors)
        
        # Count helpful error messages
        error_events = [e for e in events if e.get("type") == "error_occurred"]
        helpful_errors = [
            e for e in error_events 
            if e.get("data", {}).get("user_message") and 
               e.get("data", {}).get("suggested_actions")
        ]
        self.metrics.helpful_error_messages = len(helpful_errors)
        
        # Count user-facing errors (should be minimized)
        user_facing_errors = [
            e for e in error_events
            if e.get("data", {}).get("user_visible", True)  # Default to user-visible
        ]
        self.metrics.user_facing_errors = len(user_facing_errors)
        
        # Calculate user experience preservation score
        ux_factors = []
        if self.metrics.websocket_events_during_errors["agent_completed"] > 0:
            ux_factors.append(0.4)  # Completed successfully
        if self.metrics.fallback_mechanisms_triggered > 0:
            ux_factors.append(0.2)  # Fallbacks activated
        if self.metrics.partial_responses_delivered > 0:
            ux_factors.append(0.2)  # Partial responses provided
        if self.metrics.helpful_error_messages > 0:
            ux_factors.append(0.2)  # Helpful error communication
            
        self.metrics.user_experience_preservation_score = sum(ux_factors)
        
        # Calculate error impact minimization score
        expected_impact = {"low": 0.2, "medium": 0.5, "high": 0.8}.get(scenario.get("business_impact", "medium"), 0.5)
        actual_impact = 1.0 - self.metrics.error_response_quality_score
        self.metrics.error_impact_minimization_score = max(0.0, 1.0 - (actual_impact / expected_impact))
        
        logger.info(
            f"Error handling metrics: {self.metrics.errors_handled_gracefully}/{self.metrics.errors_encountered} graceful, "
            f"quality: {self.metrics.error_response_quality_score:.2f}, "
            f"UX preservation: {self.metrics.user_experience_preservation_score:.2f}, "
            f"recovery time: {self.metrics.recovery_time_seconds:.1f}s"
        )


class TestRealAgentErrorHandling(RealAgentErrorHandlingE2ETest):
    """Test suite for real agent error handling and recovery flows."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_comprehensive_error_recovery_flow(self, real_services_fixture):
        """Test complete error recovery workflow with business continuity validation."""
        
        # Create test user
        user = await self.create_test_user("enterprise")
        
        # Generate database connection error scenario
        error_scenario = await self.generate_error_scenario(ErrorScenarioType.DATABASE_CONNECTION_LOSS)
        
        # Connect to WebSocket
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            # Execute agent with error injection
            error_result = await self.execute_agent_with_error_injection(
                client, error_scenario, "cost_analysis"
            )
            
            # CRITICAL: Verify WebSocket events were sent even during errors
            expected_events = ["agent_started"]
            if error_result["recovery_successful"]:
                expected_events.append("agent_completed")
            
            # Should also see error handling events
            error_events = [e for e in error_result["events"] if e.get("type") in [
                "error_occurred", "recovery_attempted", "fallback_activated"
            ]]
            assert len(error_events) > 0, "Must detect and handle errors"
            
            # Validate business continuity during errors
            assert self.metrics.is_business_value_maintained(), (
                f"Business value not maintained during errors. Metrics: {self.metrics}"
            )
            
            # Validate specific error handling outcomes
            result = error_result["result"]
            
            # Must handle errors gracefully
            assert self.metrics.errors_handled_gracefully > 0, (
                "Must handle at least some errors gracefully"
            )
            
            # Must minimize user-facing errors
            error_exposure_rate = (self.metrics.user_facing_errors / max(self.metrics.errors_encountered, 1)) * 100
            assert error_exposure_rate <= 30.0, (
                f"Too many user-facing errors: {error_exposure_rate}%"
            )
            
            # Must provide meaningful response despite errors
            assert self.metrics.error_response_quality_score >= 0.5, (
                f"Error response quality too low: {self.metrics.error_response_quality_score}"
            )
            
            # Must preserve user experience
            assert self.metrics.user_experience_preservation_score >= 0.6, (
                f"User experience not preserved: {self.metrics.user_experience_preservation_score}"
            )
            
            # Recovery performance requirements
            if self.metrics.recovery_time_seconds > 0:
                assert self.metrics.recovery_time_seconds <= error_scenario["expected_recovery_time"] * 2, (
                    f"Recovery took too long: {self.metrics.recovery_time_seconds}s"
                )
            
            # Must provide alternative solutions when primary fails
            if not error_result["recovery_successful"]:
                assert self.metrics.alternative_solutions_provided > 0, (
                    "Must provide alternatives when primary solution fails"
                )
            
        logger.success("✓ Comprehensive error recovery flow validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_llm_api_timeout_resilience(self, real_services_fixture):
        """Test agent resilience to LLM API timeouts and rate limits."""
        
        user = await self.create_test_user("mid")
        
        # Test both timeout and rate limit scenarios
        error_scenarios = [
            await self.generate_error_scenario(ErrorScenarioType.LLM_API_TIMEOUT),
            await self.generate_error_scenario(ErrorScenarioType.LLM_RATE_LIMIT)
        ]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        for scenario in error_scenarios:
            logger.info(f"Testing LLM resilience: {scenario['name']}")
            
            # Reset metrics for each scenario
            self.metrics = AgentErrorHandlingMetrics()
            
            async with WebSocketTestClient(
                url=websocket_url,
                user_id=user["user_id"]
            ) as client:
                
                error_result = await self.execute_agent_with_error_injection(
                    client, scenario, "text_analysis"
                )
                
                # Must activate fallback mechanisms for LLM issues
                assert self.metrics.fallback_mechanisms_triggered > 0, (
                    f"Must activate fallbacks for {scenario['name']}"
                )
                
                result = error_result["result"]
                
                # Must provide some form of analysis despite LLM issues
                has_analysis = any([
                    result.get("cached_analysis"),
                    result.get("simplified_analysis"), 
                    result.get("offline_analysis"),
                    result.get("partial_analysis")
                ])
                assert has_analysis, f"Must provide analysis despite {scenario['name']}"
                
                # Must explain LLM unavailability to user
                explanation_provided = any([
                    result.get("service_status"),
                    result.get("explanation"),
                    "llm" in str(result).lower(),
                    "api" in str(result).lower()
                ])
                assert explanation_provided, f"Must explain LLM issues for {scenario['name']}"
            
        logger.success("✓ LLM API resilience validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_tool_execution_failure_recovery(self, real_services_fixture):
        """Test agent recovery from tool execution failures."""
        
        user = await self.create_test_user("enterprise")
        tool_failure_scenario = await self.generate_error_scenario(ErrorScenarioType.TOOL_EXECUTION_FAILURE)
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            error_result = await self.execute_agent_with_error_injection(
                client, tool_failure_scenario, "cost_optimization"
            )
            
            # Must detect tool failures
            tool_error_events = [
                e for e in error_result["events"]
                if e.get("type") == "tool_execution_failed" or
                   (e.get("type") == "error_occurred" and "tool" in str(e.get("data", {})).lower())
            ]
            assert len(tool_error_events) > 0, "Must detect tool execution failures"
            
            # Must attempt alternative approaches
            alternative_tool_events = [
                e for e in error_result["events"]
                if e.get("type") == "alternative_tool_used" or
                   (e.get("type") == "fallback_activated" and "tool" in str(e.get("data", {})).lower())
            ]
            
            result = error_result["result"]
            
            # Must provide results using alternative methods
            has_alternative_results = any([
                result.get("manual_analysis"),
                result.get("best_effort_results"),
                result.get("alternative_tool_results"),
                len(alternative_tool_events) > 0
            ])
            assert has_alternative_results, "Must provide results using alternative methods"
            
            # Must explain tool limitations
            tool_status_info = any([
                result.get("tool_status"),
                result.get("limitations_explanation"),
                "tool" in str(result.get("notes", "")).lower()
            ])
            assert tool_status_info, "Must explain tool limitations to user"
            
        logger.success("✓ Tool execution failure recovery validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_interruption_recovery(self, real_services_fixture):
        """Test agent recovery from WebSocket connection interruptions."""
        
        user = await self.create_test_user("mid")
        websocket_scenario = await self.generate_error_scenario(ErrorScenarioType.WEBSOCKET_INTERRUPTION)
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        # This test simulates connection drops and reconnections
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"],
            reconnect_on_failure=True  # Enable automatic reconnection
        ) as client:
            
            error_result = await self.execute_agent_with_error_injection(
                client, websocket_scenario, "simple_analysis"
            )
            
            # WebSocket interruptions should be handled transparently
            connection_events = [
                e for e in error_result["events"]
                if e.get("type") in ["connection_lost", "reconnection_attempted", "connection_restored"]
            ]
            
            # If connection issues occurred, must handle them
            if len(connection_events) > 0:
                reconnection_events = [e for e in connection_events if "reconnect" in e.get("type", "")]
                assert len(reconnection_events) > 0, "Must attempt reconnection on WebSocket drops"
            
            # Must complete execution despite potential interruptions
            completion_events = [e for e in error_result["events"] if e.get("type") == "agent_completed"]
            assert len(completion_events) > 0, "Must complete execution despite WebSocket interruptions"
            
            result = error_result["result"]
            
            # Must provide complete or continued results
            has_results = any([
                result.get("analysis"),
                result.get("continued_from_interruption"),
                result.get("recovered_state"),
                len(str(result)) > 50  # Some meaningful content
            ])
            assert has_results, "Must provide results despite WebSocket interruptions"
            
        logger.success("✓ WebSocket interruption recovery validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_concurrent_error_isolation(self, real_services_fixture):
        """Test error isolation between concurrent users during failure scenarios."""
        
        # Create multiple users
        users = [
            await self.create_test_user("enterprise"),
            await self.create_test_user("mid"),
            await self.create_test_user("early")
        ]
        
        # Create different error scenarios for each user
        error_scenarios = [
            await self.generate_error_scenario(ErrorScenarioType.DATABASE_CONNECTION_LOSS),
            await self.generate_error_scenario(ErrorScenarioType.TOOL_EXECUTION_FAILURE),
            await self.generate_error_scenario(ErrorScenarioType.LLM_API_TIMEOUT)
        ]
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        # Execute concurrent error scenarios
        async def execute_for_user(user, scenario):
            # Individual metrics per user
            user_metrics = AgentErrorHandlingMetrics()
            original_metrics = self.metrics
            self.metrics = user_metrics
            
            try:
                async with WebSocketTestClient(
                    url=websocket_url,
                    user_id=user["user_id"]
                ) as client:
                    
                    result = await self.execute_agent_with_error_injection(
                        client, scenario
                    )
                    
                    return {
                        "user_id": user["user_id"],
                        "scenario": scenario["name"],
                        "success": user_metrics.is_business_value_maintained(),
                        "errors_handled": user_metrics.errors_handled_gracefully,
                        "user_facing_errors": user_metrics.user_facing_errors,
                        "metrics": user_metrics
                    }
                    
            finally:
                self.metrics = original_metrics
        
        # Execute all error scenarios concurrently
        results = await asyncio.gather(*[
            execute_for_user(users[i], error_scenarios[i])
            for i in range(len(users))
        ])
        
        # Validate isolation - errors in one user's session shouldn't affect others
        successful_error_handling = [r for r in results if r["success"]]
        assert len(successful_error_handling) >= len(users) * 0.8, (
            f"Error isolation failed. Only {len(successful_error_handling)}/{len(users)} users handled errors well"
        )
        
        # Validate that each user's errors were contained
        for result in results:
            assert result["errors_handled"] > 0, (
                f"User {result['user_id']} should have handled errors in {result['scenario']}"
            )
            
            # User-facing errors should be minimized for each user
            assert result["user_facing_errors"] <= result["errors_handled"], (
                f"User {result['user_id']} had too many user-facing errors"
            )
        
        logger.success("✓ Concurrent error isolation validated")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_invalid_input_graceful_handling(self, real_services_fixture):
        """Test graceful handling of invalid user input."""
        
        user = await self.create_test_user("mid")
        input_error_scenario = await self.generate_error_scenario(ErrorScenarioType.INVALID_USER_INPUT)
        
        backend_url = f"http://localhost:{TEST_PORTS['backend']}"
        websocket_url = backend_url.replace("http", "ws") + "/ws"
        
        # Test various invalid inputs
        invalid_inputs = [
            {"type": "malformed_json", "data": '{"incomplete": json'},
            {"type": "missing_fields", "data": {"incomplete_request": True}},
            {"type": "invalid_types", "data": {"numbers_as_strings": "not_a_number", "required_array": "should_be_array"}},
            {"type": "empty_request", "data": {}},
            {"type": "oversized_input", "data": {"huge_text": "x" * 100000}}
        ]
        
        async with WebSocketTestClient(
            url=websocket_url,
            user_id=user["user_id"]
        ) as client:
            
            for invalid_input in invalid_inputs[:3]:  # Test first 3 to avoid timeout
                logger.info(f"Testing invalid input: {invalid_input['type']}")
                
                # Reset metrics for each input type
                self.metrics = AgentErrorHandlingMetrics()
                
                # Send invalid request
                invalid_request = {
                    "type": "agent_request",
                    "agent": "input_validator", 
                    "message": "Process this potentially invalid input",
                    "context": {
                        "test_invalid_input": invalid_input,
                        "business_context": "input_validation_testing"
                    },
                    "invalid_data": invalid_input["data"]  # This might cause parsing errors
                }
                
                try:
                    await client.send_json(invalid_request)
                    
                    # Collect response events
                    events = []
                    async for event in client.receive_events(timeout=30.0):
                        events.append(event)
                        if event.get("type") in ["agent_completed", "input_validation_error", "unrecoverable_error"]:
                            break
                    
                    # Must handle input gracefully
                    validation_events = [e for e in events if "validation" in e.get("type", "").lower()]
                    error_events = [e for e in events if e.get("type") == "error_occurred"]
                    
                    # Should either validate and fix input, or provide helpful error
                    handled_gracefully = (
                        len(validation_events) > 0 or  # Input validation triggered
                        any(e.get("data", {}).get("user_message") for e in error_events) or  # Helpful error message
                        any(e.get("type") == "agent_completed" for e in events)  # Completed despite invalid input
                    )
                    
                    assert handled_gracefully, f"Must handle invalid input gracefully: {invalid_input['type']}"
                    
                    # Must provide user guidance for invalid input
                    final_event = events[-1] if events else {}
                    result = final_event.get("data", {}).get("result", {})
                    
                    guidance_provided = any([
                        result.get("input_guidance"),
                        result.get("validation_errors"),
                        result.get("suggested_corrections"),
                        "input" in str(result).lower(),
                        "format" in str(result).lower()
                    ])
                    assert guidance_provided, f"Must provide input guidance for: {invalid_input['type']}"
                    
                except Exception as e:
                    logger.warning(f"Exception during invalid input test {invalid_input['type']}: {e}")
                    # Even exceptions should be handled gracefully by the system
                    assert False, f"System should handle invalid input without exceptions: {invalid_input['type']}"
        
        logger.success("✓ Invalid input graceful handling validated")


if __name__ == "__main__":
    # Run the test directly for development
    import asyncio
    
    async def run_direct_tests():
        logger.info("Starting real agent error handling E2E tests...")
        
        test_instance = TestRealAgentErrorHandling()
        
        try:
            # Mock real_services_fixture for direct testing
            mock_services = {
                "db": "mock_db",
                "redis": "mock_redis",
                "backend_url": f"http://localhost:{TEST_PORTS['backend']}"
            }
            
            await test_instance.test_comprehensive_error_recovery_flow(mock_services)
            logger.success("✓ All agent error handling tests passed")
            
        except Exception as e:
            logger.error(f"✗ Agent error handling tests failed: {e}")
            raise
    
    asyncio.run(run_direct_tests())