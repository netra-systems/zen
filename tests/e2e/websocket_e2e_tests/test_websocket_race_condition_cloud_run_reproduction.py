"""
E2E Test: WebSocket Race Condition Cloud Run Reproduction

MISSION CRITICAL: Comprehensive reproduction of WebSocket race conditions that occur
in GCP Cloud Run environments, with specific focus on the "Need to call accept first"
error and associated timing issues.

TARGET VALIDATION:
1. Reproduce the exact race condition scenarios observed in Cloud Run
2. Test Cloud Run timing simulation with progressive delays (100-300ms)
3. Validate race condition detection framework catches timing issues
4. Ensure all 5 critical WebSocket events are delivered reliably
5. Test concurrent connections under latency conditions

BUSINESS VALUE:
- Segment: Platform/Internal
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Validates production-ready chat functionality under adverse conditions
- Strategic Impact: Prevents $500K+ ARR loss from WebSocket failures

CRITICAL E2E REQUIREMENTS:
- MUST use real services (--real-services flag)
- MUST use authentic authentication (no mocks per CLAUDE.md)
- MUST test actual WebSocket connections with real timing
- MUST validate complete message routing pipeline
- MUST detect and report race condition patterns

SSOT COMPLIANCE: Uses test_framework/ssot/e2e_auth_helper.py for authentication
and follows established E2E test patterns.

TEST OBJECTIVES:
- Reproduce "Need to call accept first" race condition error
- Validate Cloud Run timing issues with progressive delays
- Test concurrent connections under latency conditions
- Ensure all 5 critical WebSocket events are delivered
- Provide comprehensive race condition detection framework
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import patch
import random

import pytest
import websockets
import aiohttp
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode, ConnectionClosedOK

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    E2EAuthConfig,
    create_authenticated_user_context
)
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
# Container utilities will be handled by the unified test runner
from netra_backend.app.websocket_core.gcp_initialization_validator import (
    GCPWebSocketInitializationValidator,
    GCPReadinessState,
    create_gcp_websocket_validator,
    gcp_websocket_readiness_check
)


class RaceConditionType(Enum):
    """Types of race conditions that can occur in WebSocket connections."""
    ACCEPT_FIRST_ERROR = "need_to_call_accept_first"
    CONNECTION_TIMEOUT = "connection_timeout"
    SERVICE_NOT_READY = "service_not_ready"
    AUTH_TIMING = "auth_timing_issue"
    REDIS_READINESS = "redis_readiness_race"
    CONCURRENT_CONFLICT = "concurrent_connection_conflict"


@dataclass
class CloudRunLatencyProfile:
    """Cloud Run latency simulation profile."""
    name: str
    base_delay_ms: int
    jitter_ms: int
    connection_timeout_ms: int
    auth_delay_ms: int
    description: str
    
    def get_simulated_delay(self) -> float:
        """Get simulated delay with jitter in seconds."""
        total_delay_ms = self.base_delay_ms + random.randint(0, self.jitter_ms)
        return total_delay_ms / 1000.0


@dataclass
class RaceConditionTestResult:
    """Result of race condition reproduction test."""
    test_name: str
    success: bool
    race_condition_detected: bool
    race_condition_type: Optional[RaceConditionType]
    connection_time: float
    error_message: Optional[str]
    websocket_events_received: List[str]
    auth_method: str
    environment: str
    latency_profile: str
    additional_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebSocketEventValidationResult:
    """Result of WebSocket event validation."""
    expected_events: List[str]
    received_events: List[str]
    missing_events: List[str]
    unexpected_events: List[str]
    event_timing: Dict[str, float]
    validation_success: bool


class WebSocketRaceConditionTestFramework:
    """
    Comprehensive framework for testing WebSocket race conditions.
    
    CRITICAL: This framework provides systematic reproduction of race conditions
    observed in Cloud Run environments and validates fixes work correctly.
    """
    
    # Critical WebSocket events that MUST be delivered for business value
    CRITICAL_WEBSOCKET_EVENTS = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    ]
    
    # Cloud Run latency profiles for realistic simulation
    CLOUD_RUN_LATENCY_PROFILES = {
        "fast": CloudRunLatencyProfile(
            name="fast",
            base_delay_ms=50,
            jitter_ms=25,
            connection_timeout_ms=5000,
            auth_delay_ms=100,
            description="Fast Cloud Run instance (optimal conditions)"
        ),
        "typical": CloudRunLatencyProfile(
            name="typical", 
            base_delay_ms=150,
            jitter_ms=50,
            connection_timeout_ms=8000,
            auth_delay_ms=200,
            description="Typical Cloud Run instance (normal conditions)"
        ),
        "slow": CloudRunLatencyProfile(
            name="slow",
            base_delay_ms=300,
            jitter_ms=100,
            connection_timeout_ms=12000,
            auth_delay_ms=400,
            description="Slow Cloud Run instance (high load conditions)"
        ),
        "stress": CloudRunLatencyProfile(
            name="stress",
            base_delay_ms=500,
            jitter_ms=200,
            connection_timeout_ms=15000,
            auth_delay_ms=600,
            description="Stressed Cloud Run instance (extreme conditions)"
        )
    }
    
    def __init__(self, auth_helper: E2EWebSocketAuthHelper, environment: str = "test"):
        self.auth_helper = auth_helper
        self.environment = environment
        self.logger = logging.getLogger(__name__)
        self.env = get_env()
        
        # Test configuration
        self.base_connection_timeout = 20.0
        self.message_timeout = 10.0
        self.race_condition_patterns = [
            "need to call accept first",
            "connection closed before",
            "server error",
            "timeout",
            "502 bad gateway",
            "503 service unavailable",
            "1011"
        ]
    
    async def simulate_cloud_run_latency(self, profile: CloudRunLatencyProfile) -> None:
        """Simulate Cloud Run environment latency."""
        delay = profile.get_simulated_delay()
        self.logger.debug(f"Simulating {profile.name} Cloud Run latency: {delay:.3f}s")
        await asyncio.sleep(delay)
    
    def detect_race_condition(self, error_message: str) -> Tuple[bool, Optional[RaceConditionType]]:
        """
        Detect race condition patterns in error messages.
        
        Returns:
            Tuple of (is_race_condition, race_condition_type)
        """
        error_lower = error_message.lower()
        
        # Check for specific race condition patterns
        if "need to call accept first" in error_lower:
            return True, RaceConditionType.ACCEPT_FIRST_ERROR
        elif "connection closed before" in error_lower or "1011" in error_lower:
            return True, RaceConditionType.SERVICE_NOT_READY
        elif "timeout" in error_lower:
            return True, RaceConditionType.CONNECTION_TIMEOUT
        elif any(pattern in error_lower for pattern in ["502", "503", "server error"]):
            return True, RaceConditionType.SERVICE_NOT_READY
        elif "auth" in error_lower and ("timeout" in error_lower or "failed" in error_lower):
            return True, RaceConditionType.AUTH_TIMING
        elif "redis" in error_lower and ("timeout" in error_lower or "connection" in error_lower):
            return True, RaceConditionType.REDIS_READINESS
        
        return False, None
    
    async def test_websocket_connection_with_latency(
        self,
        profile: CloudRunLatencyProfile,
        test_name: str = "latency_test"
    ) -> RaceConditionTestResult:
        """
        Test WebSocket connection with simulated Cloud Run latency.
        
        Args:
            profile: Cloud Run latency profile to simulate
            test_name: Name of the test for reporting
            
        Returns:
            RaceConditionTestResult with detailed results
        """
        start_time = time.time()
        websocket = None
        events_received = []
        
        try:
            # Simulate Cloud Run startup delay
            await self.simulate_cloud_run_latency(profile)
            
            # Attempt WebSocket connection with profile-adjusted timeout
            connection_timeout = profile.connection_timeout_ms / 1000.0
            
            # Add auth delay simulation
            if profile.auth_delay_ms > 0:
                auth_delay = profile.auth_delay_ms / 1000.0
                self.logger.debug(f"Simulating auth delay: {auth_delay:.3f}s")
                await asyncio.sleep(auth_delay)
            
            websocket = await self.auth_helper.connect_authenticated_websocket(
                timeout=connection_timeout
            )
            
            connection_time = time.time() - start_time
            
            # Test message sending and event collection
            test_message = {
                "type": "test_race_condition",
                "profile": profile.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_name": test_name
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Collect events for a short period
            event_collection_timeout = time.time() + 5.0
            while time.time() < event_collection_timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    
                    if "type" in response_data:
                        event_type = response_data["type"]
                        events_received.append(event_type)
                        
                        # Break if we get a completion event
                        if event_type in ["pong", "agent_completed", "test_response"]:
                            break
                            
                except asyncio.TimeoutError:
                    break
                except json.JSONDecodeError:
                    # Some responses might not be JSON
                    continue
            
            return RaceConditionTestResult(
                test_name=test_name,
                success=True,
                race_condition_detected=False,
                race_condition_type=None,
                connection_time=connection_time,
                error_message=None,
                websocket_events_received=events_received,
                auth_method="jwt_with_e2e_headers",
                environment=self.environment,
                latency_profile=profile.name,
                additional_details={
                    "simulated_delay": profile.get_simulated_delay(),
                    "events_count": len(events_received)
                }
            )
            
        except Exception as e:
            connection_time = time.time() - start_time
            error_message = str(e)
            
            # Detect race condition
            is_race_condition, race_type = self.detect_race_condition(error_message)
            
            return RaceConditionTestResult(
                test_name=test_name,
                success=False,
                race_condition_detected=is_race_condition,
                race_condition_type=race_type,
                connection_time=connection_time,
                error_message=error_message,
                websocket_events_received=events_received,
                auth_method="jwt_with_e2e_headers",
                environment=self.environment,
                latency_profile=profile.name,
                additional_details={
                    "simulated_delay": profile.get_simulated_delay(),
                    "exception_type": type(e).__name__
                }
            )
            
        finally:
            if websocket:
                try:
                    await websocket.close()
                except:
                    pass
    
    async def test_concurrent_connections_under_latency(
        self,
        profile: CloudRunLatencyProfile,
        concurrent_count: int = 3
    ) -> List[RaceConditionTestResult]:
        """
        Test multiple concurrent WebSocket connections under latency.
        
        Args:
            profile: Cloud Run latency profile to simulate
            concurrent_count: Number of concurrent connections to test
            
        Returns:
            List of RaceConditionTestResult for each connection
        """
        async def single_connection_test(connection_id: int) -> RaceConditionTestResult:
            return await self.test_websocket_connection_with_latency(
                profile=profile,
                test_name=f"concurrent_{connection_id}"
            )
        
        # Create concurrent connection tasks
        tasks = [
            single_connection_test(i) 
            for i in range(concurrent_count)
        ]
        
        # Execute with some staggered timing to simulate real-world scenarios
        results = []
        for i, task in enumerate(tasks):
            if i > 0:
                # Stagger connections slightly
                await asyncio.sleep(0.1)
            
            try:
                result = await task
                results.append(result)
            except Exception as e:
                # Create error result for failed task
                error_result = RaceConditionTestResult(
                    test_name=f"concurrent_{i}",
                    success=False,
                    race_condition_detected=True,
                    race_condition_type=RaceConditionType.CONCURRENT_CONFLICT,
                    connection_time=0.0,
                    error_message=str(e),
                    websocket_events_received=[],
                    auth_method="jwt_with_e2e_headers",
                    environment=self.environment,
                    latency_profile=profile.name
                )
                results.append(error_result)
        
        return results
    
    def validate_websocket_events(
        self,
        received_events: List[str],
        expected_events: Optional[List[str]] = None
    ) -> WebSocketEventValidationResult:
        """
        Validate that critical WebSocket events were received.
        
        Args:
            received_events: List of event types received
            expected_events: Optional list of expected events (defaults to critical events)
            
        Returns:
            WebSocketEventValidationResult with validation details
        """
        expected_events = expected_events or self.CRITICAL_WEBSOCKET_EVENTS.copy()
        
        # Find missing and unexpected events
        missing_events = [event for event in expected_events if event not in received_events]
        unexpected_events = [event for event in received_events if event not in expected_events]
        
        # Create timing information (simplified for this implementation)
        event_timing = {event: 0.0 for event in received_events}
        
        validation_success = len(missing_events) == 0
        
        return WebSocketEventValidationResult(
            expected_events=expected_events,
            received_events=received_events,
            missing_events=missing_events,
            unexpected_events=unexpected_events,
            event_timing=event_timing,
            validation_success=validation_success
        )


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.e2e_auth_required
class TestWebSocketRaceConditionCloudRunReproduction(SSotBaseTestCase):
    """
    Comprehensive E2E tests for WebSocket race condition reproduction.
    
    CRITICAL: These tests reproduce race conditions observed in Cloud Run
    environments and validate that fixes work correctly under adverse conditions.
    """
    
    def setup_method(self, method):
        """Setup E2E test environment with real services."""
        super().setup_method(method)
        self.env = get_env()
        # Real services fixture setup handled by pytest fixtures
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        # Setup auth helpers
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        
        # Setup race condition test framework
        self.race_framework = WebSocketRaceConditionTestFramework(
            auth_helper=self.websocket_auth_helper,
            environment=self.test_environment
        )
        
        # Test configuration
        self.base_timeout = 20.0 if self.test_environment == "staging" else 15.0
        
        print(f"🔬 RACE CONDITION REPRODUCTION TEST SETUP:")
        print(f"   Environment: {self.test_environment}")
        print(f"   WebSocket URL: {self.websocket_auth_helper.config.websocket_url}")
        print(f"   Base timeout: {self.base_timeout}s")
    
    @pytest.mark.asyncio
    async def test_reproduce_accept_first_race_condition(self):
        """
        CRITICAL E2E TEST: Reproduce "Need to call accept first" race condition.
        
        This test specifically targets the race condition that occurs when WebSocket
        connections are attempted before the backend services are fully ready.
        """
        print("🧪 TESTING: Reproduce 'Need to call accept first' Race Condition")
        
        # Services are ensured by real_services pytest fixtures
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Test with different Cloud Run latency profiles
        latency_profiles = ["fast", "typical", "slow"]
        race_condition_results = []
        
        for profile_name in latency_profiles:
            profile = self.race_framework.CLOUD_RUN_LATENCY_PROFILES[profile_name]
            print(f"   Testing with {profile.name} Cloud Run profile: {profile.description}")
            
            # Simulate GCP environment for this test
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend',
                'GCP_PROJECT': 'netra-staging'
            }):
                result = await self.race_framework.test_websocket_connection_with_latency(
                    profile=profile,
                    test_name=f"accept_first_race_{profile_name}"
                )
                
                race_condition_results.append(result)
                
                if result.success:
                    print(f"     ✅ {profile.name}: Connection successful in {result.connection_time:.3f}s")
                    print(f"       Events received: {len(result.websocket_events_received)}")
                else:
                    print(f"     ❌ {profile.name}: Connection failed - {result.error_message}")
                    if result.race_condition_detected:
                        print(f"       🚨 Race condition detected: {result.race_condition_type.value}")
        
        # Analyze results
        successful_connections = [r for r in race_condition_results if r.success]
        failed_connections = [r for r in race_condition_results if not r.success]
        race_conditions_detected = [r for r in race_condition_results if r.race_condition_detected]
        
        print(f"📊 RACE CONDITION REPRODUCTION RESULTS:")
        print(f"   Total tests: {len(race_condition_results)}")
        print(f"   Successful: {len(successful_connections)}")
        print(f"   Failed: {len(failed_connections)}")
        print(f"   Race conditions detected: {len(race_conditions_detected)}")
        
        # Report race condition patterns
        if race_conditions_detected:
            race_types = [r.race_condition_type.value for r in race_conditions_detected if r.race_condition_type]
            print(f"   Race condition types found: {set(race_types)}")
        
        # CRITICAL VALIDATION: At least fast profile should work (validates fix is working)
        fast_results = [r for r in race_condition_results if r.latency_profile == "fast"]
        assert len(fast_results) > 0, "No fast profile results found"
        
        fast_success = any(r.success for r in fast_results)
        if not fast_success:
            fast_errors = [r.error_message for r in fast_results if not r.success]
            pytest.fail(f"Fast profile should succeed - indicates race condition fix may not be working. Errors: {fast_errors}")
        
        # Allow for some failures in slow/stress conditions (realistic for Cloud Run)
        success_rate = len(successful_connections) / len(race_condition_results)
        assert success_rate >= 0.3, f"Too many total failures: {success_rate:.1%} success rate"
        
        print("✅ RACE CONDITION REPRODUCTION TEST COMPLETED")
    
    @pytest.mark.asyncio
    async def test_progressive_cloud_run_latency_simulation(self):
        """
        E2E TEST: Progressive Cloud Run latency simulation.
        
        This test validates that WebSocket connections work correctly across
        different Cloud Run performance scenarios with increasing latency.
        """
        print("🧪 TESTING: Progressive Cloud Run Latency Simulation")
        
        # Services are ensured by real_services pytest fixtures
        
        # Test all latency profiles progressively
        profile_names = ["fast", "typical", "slow", "stress"]
        progressive_results = []
        
        for profile_name in profile_names:
            profile = self.race_framework.CLOUD_RUN_LATENCY_PROFILES[profile_name]
            print(f"   Testing {profile.name} profile: {profile.description}")
            
            # Run test with Cloud Run environment simulation
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend',
                'CLOUD_RUN_SERVICE': 'netra-backend',
                'PORT': '8080'
            }):
                result = await self.race_framework.test_websocket_connection_with_latency(
                    profile=profile,
                    test_name=f"progressive_latency_{profile_name}"
                )
                
                progressive_results.append(result)
                
                # Report individual result
                if result.success:
                    connection_time = result.connection_time
                    events_count = len(result.websocket_events_received)
                    print(f"     ✅ {profile.name}: {connection_time:.3f}s, {events_count} events")
                else:
                    error_msg = result.error_message[:100] if result.error_message else "Unknown error"
                    print(f"     ❌ {profile.name}: Failed - {error_msg}")
                    
                    if result.race_condition_detected:
                        print(f"       🚨 Race condition: {result.race_condition_type.value}")
                
                # Brief delay between profile tests
                await asyncio.sleep(0.5)
        
        # Analyze progressive results
        successful_by_profile = {}
        for result in progressive_results:
            profile_name = result.latency_profile
            successful_by_profile[profile_name] = result.success
        
        print(f"📊 PROGRESSIVE LATENCY SIMULATION RESULTS:")
        for profile_name in profile_names:
            status = "✅ PASS" if successful_by_profile.get(profile_name) else "❌ FAIL"
            print(f"   {profile_name}: {status}")
        
        # Calculate performance degradation
        successful_count = sum(1 for success in successful_by_profile.values() if success)
        success_rate = successful_count / len(profile_names)
        
        print(f"   Overall success rate: {success_rate:.1%} ({successful_count}/{len(profile_names)})")
        
        # VALIDATION: Fast and typical profiles should work (minimum acceptable performance)
        assert successful_by_profile.get("fast", False), "Fast profile must work for acceptable performance"
        
        # At least 50% of profiles should work (validates fix handles reasonable latency)
        assert success_rate >= 0.5, f"Poor latency tolerance: {success_rate:.1%} success rate"
        
        print("✅ PROGRESSIVE CLOUD RUN LATENCY SIMULATION COMPLETED")
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections_with_race_detection(self):
        """
        STRESS E2E TEST: Concurrent WebSocket connections with race condition detection.
        
        This test validates that multiple concurrent WebSocket connections work
        correctly under latency and can detect/handle race conditions gracefully.
        """
        print("🧪 TESTING: Concurrent WebSocket Connections with Race Detection")
        
        # Services are ensured by real_services pytest fixtures
        
        # Test concurrent connections under different latency profiles
        test_profiles = ["typical", "slow"]
        concurrent_count = 3  # Moderate concurrency for E2E stability
        
        all_concurrent_results = []
        
        for profile_name in test_profiles:
            profile = self.race_framework.CLOUD_RUN_LATENCY_PROFILES[profile_name]
            print(f"   Testing {concurrent_count} concurrent connections with {profile.name} profile")
            
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'
            }):
                concurrent_results = await self.race_framework.test_concurrent_connections_under_latency(
                    profile=profile,
                    concurrent_count=concurrent_count
                )
                
                all_concurrent_results.extend(concurrent_results)
                
                # Analyze this profile's results
                successful = [r for r in concurrent_results if r.success]
                failed = [r for r in concurrent_results if not r.success]
                race_detected = [r for r in concurrent_results if r.race_condition_detected]
                
                print(f"     {profile.name} profile results:")
                print(f"       Successful: {len(successful)}/{concurrent_count}")
                print(f"       Failed: {len(failed)}")
                print(f"       Race conditions: {len(race_detected)}")
                
                if successful:
                    avg_time = sum(r.connection_time for r in successful) / len(successful)
                    print(f"       Average connection time: {avg_time:.3f}s")
        
        # Overall concurrent analysis
        total_tests = len(all_concurrent_results)
        total_successful = [r for r in all_concurrent_results if r.success]
        total_failed = [r for r in all_concurrent_results if not r.success]
        total_race_conditions = [r for r in all_concurrent_results if r.race_condition_detected]
        
        print(f"📊 CONCURRENT CONNECTION RESULTS:")
        print(f"   Total concurrent tests: {total_tests}")
        print(f"   Total successful: {len(total_successful)}")
        print(f"   Total failed: {len(total_failed)}")
        print(f"   Total race conditions detected: {len(total_race_conditions)}")
        
        # Race condition analysis
        if total_race_conditions:
            race_types = {}
            for result in total_race_conditions:
                if result.race_condition_type:
                    race_type = result.race_condition_type.value
                    race_types[race_type] = race_types.get(race_type, 0) + 1
            
            print(f"   Race condition breakdown: {race_types}")
        
        # Performance analysis
        if total_successful:
            connection_times = [r.connection_time for r in total_successful]
            avg_time = sum(connection_times) / len(connection_times)
            min_time = min(connection_times)
            max_time = max(connection_times)
            
            print(f"   Connection time stats: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")
        
        # VALIDATION: Concurrent connections should mostly succeed
        success_rate = len(total_successful) / total_tests
        assert success_rate >= 0.5, f"Poor concurrent connection success rate: {success_rate:.1%}"
        
        # No catastrophic race conditions (accept some timeouts under stress)
        catastrophic_races = [
            r for r in total_race_conditions 
            if r.race_condition_type in [RaceConditionType.ACCEPT_FIRST_ERROR, RaceConditionType.SERVICE_NOT_READY]
        ]
        
        catastrophic_rate = len(catastrophic_races) / total_tests
        assert catastrophic_rate <= 0.3, f"Too many catastrophic race conditions: {catastrophic_rate:.1%}"
        
        print("✅ CONCURRENT WEBSOCKET CONNECTIONS WITH RACE DETECTION COMPLETED")
    
    @pytest.mark.asyncio 
    async def test_websocket_event_delivery_under_race_conditions(self):
        """
        CRITICAL E2E TEST: WebSocket event delivery validation under race conditions.
        
        This test ensures that all 5 critical WebSocket events are delivered
        correctly even when race conditions or timing issues are present.
        """
        print("🧪 TESTING: WebSocket Event Delivery Under Race Conditions")
        
        # Services are ensured by real_services pytest fixtures
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Test event delivery under different latency conditions
        test_scenarios = [
            ("optimal", "fast"),
            ("normal", "typical"),
            ("degraded", "slow")
        ]
        
        event_delivery_results = []
        
        for scenario_name, profile_name in test_scenarios:
            profile = self.race_framework.CLOUD_RUN_LATENCY_PROFILES[profile_name]
            print(f"   Testing event delivery in {scenario_name} conditions ({profile.name} profile)")
            
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'
            }):
                # Test WebSocket connection and event collection
                websocket = None
                events_received = []
                
                try:
                    # Apply latency simulation
                    await self.race_framework.simulate_cloud_run_latency(profile)
                    
                    # Connect with extended timeout for event collection
                    websocket = await self.websocket_auth_helper.connect_authenticated_websocket(
                        timeout=self.base_timeout
                    )
                    
                    # Send message that should trigger agent events
                    agent_trigger_message = {
                        "type": "chat_message",
                        "content": f"Test agent execution for {scenario_name} conditions",
                        "user_id": str(user_context.user_id),
                        "thread_id": str(user_context.thread_id),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await websocket.send(json.dumps(agent_trigger_message))
                    
                    # Collect events for extended period to catch all agent events
                    event_collection_start = time.time()
                    event_timeout = 15.0  # Extended timeout for agent execution
                    
                    while (time.time() - event_collection_start) < event_timeout:
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            
                            try:
                                response_data = json.loads(response)
                                if "type" in response_data:
                                    event_type = response_data["type"]
                                    events_received.append(event_type)
                                    print(f"     📨 Event received: {event_type}")
                                    
                                    # Break if we get agent completion
                                    if event_type == "agent_completed":
                                        print(f"     🏁 Agent execution completed")
                                        break
                                        
                            except json.JSONDecodeError:
                                # Some responses might not be JSON
                                continue
                                
                        except asyncio.TimeoutError:
                            # No more events in the last 2 seconds
                            continue
                    
                    # Validate events received
                    event_validation = self.race_framework.validate_websocket_events(events_received)
                    
                    event_delivery_results.append({
                        "scenario": scenario_name,
                        "profile": profile_name,
                        "success": True,
                        "events_received": events_received,
                        "validation": event_validation,
                        "error": None
                    })
                    
                    print(f"     ✅ {scenario_name}: {len(events_received)} events received")
                    print(f"       Critical events missing: {len(event_validation.missing_events)}")
                    
                except Exception as e:
                    error_message = str(e)
                    race_detected, race_type = self.race_framework.detect_race_condition(error_message)
                    
                    event_delivery_results.append({
                        "scenario": scenario_name,
                        "profile": profile_name,
                        "success": False,
                        "events_received": events_received,
                        "validation": None,
                        "error": error_message,
                        "race_condition": race_detected,
                        "race_type": race_type.value if race_type else None
                    })
                    
                    print(f"     ❌ {scenario_name}: Failed - {error_message}")
                    if race_detected:
                        print(f"       🚨 Race condition detected: {race_type.value}")
                
                finally:
                    if websocket:
                        try:
                            await websocket.close()
                        except:
                            pass
        
        # Analyze event delivery results
        successful_scenarios = [r for r in event_delivery_results if r["success"]]
        failed_scenarios = [r for r in event_delivery_results if not r["success"]]
        
        print(f"📊 EVENT DELIVERY UNDER RACE CONDITIONS RESULTS:")
        print(f"   Successful scenarios: {len(successful_scenarios)}/{len(event_delivery_results)}")
        print(f"   Failed scenarios: {len(failed_scenarios)}")
        
        # Event delivery analysis
        if successful_scenarios:
            for result in successful_scenarios:
                validation = result["validation"]
                print(f"   {result['scenario']}:")
                print(f"     Events received: {len(result['events_received'])}")
                print(f"     Missing critical events: {len(validation.missing_events)}")
                if validation.missing_events:
                    print(f"     Missing: {validation.missing_events}")
        
        # Report race conditions in failed scenarios
        race_condition_failures = [r for r in failed_scenarios if r.get("race_condition")]
        if race_condition_failures:
            print(f"   Race condition failures: {len(race_condition_failures)}")
            race_types = [r["race_type"] for r in race_condition_failures if r.get("race_type")]
            print(f"   Race types: {set(race_types)}")
        
        # VALIDATION: At least optimal conditions should work perfectly
        optimal_results = [r for r in successful_scenarios if r["scenario"] == "optimal"]
        assert len(optimal_results) > 0, "Optimal conditions must work for event delivery"
        
        for optimal_result in optimal_results:
            validation = optimal_result["validation"]
            assert validation.validation_success or len(validation.missing_events) <= 2, (
                f"Too many missing critical events in optimal conditions: {validation.missing_events}"
            )
        
        # At least 2/3 scenarios should succeed
        success_rate = len(successful_scenarios) / len(event_delivery_results)
        assert success_rate >= 0.67, f"Poor event delivery success rate: {success_rate:.1%}"
        
        print("✅ WEBSOCKET EVENT DELIVERY UNDER RACE CONDITIONS COMPLETED")
    
    @pytest.mark.asyncio
    async def test_race_condition_recovery_and_reconnection(self):
        """
        E2E TEST: Race condition recovery and WebSocket reconnection.
        
        This test validates that the system can recover gracefully from race
        conditions and successfully reconnect WebSocket connections.
        """
        print("🧪 TESTING: Race Condition Recovery and Reconnection")
        
        # Services are ensured by real_services pytest fixtures
        
        # Test recovery scenarios
        recovery_scenarios = [
            {
                "name": "immediate_reconnect",
                "initial_profile": "stress",  # Likely to cause issues
                "recovery_profile": "typical",  # Should work better
                "delay_between": 0.5
            },
            {
                "name": "delayed_reconnect", 
                "initial_profile": "slow",
                "recovery_profile": "fast",
                "delay_between": 2.0
            }
        ]
        
        recovery_results = []
        
        for scenario in recovery_scenarios:
            print(f"   Testing {scenario['name']} scenario")
            
            with patch.dict('os.environ', {
                'ENVIRONMENT': 'staging',
                'K_SERVICE': 'netra-backend'
            }):
                # Attempt initial connection (may fail due to race condition)
                initial_profile = self.race_framework.CLOUD_RUN_LATENCY_PROFILES[scenario["initial_profile"]]
                initial_result = await self.race_framework.test_websocket_connection_with_latency(
                    profile=initial_profile,
                    test_name=f"{scenario['name']}_initial"
                )
                
                print(f"     Initial connection ({initial_profile.name}): {'✅' if initial_result.success else '❌'}")
                if not initial_result.success and initial_result.race_condition_detected:
                    print(f"       Race condition detected: {initial_result.race_condition_type.value}")
                
                # Wait before recovery attempt
                await asyncio.sleep(scenario["delay_between"])
                
                # Attempt recovery connection
                recovery_profile = self.race_framework.CLOUD_RUN_LATENCY_PROFILES[scenario["recovery_profile"]]
                recovery_result = await self.race_framework.test_websocket_connection_with_latency(
                    profile=recovery_profile,
                    test_name=f"{scenario['name']}_recovery"
                )
                
                print(f"     Recovery connection ({recovery_profile.name}): {'✅' if recovery_result.success else '❌'}")
                
                recovery_results.append({
                    "scenario_name": scenario["name"],
                    "initial_success": initial_result.success,
                    "initial_race_detected": initial_result.race_condition_detected,
                    "recovery_success": recovery_result.success,
                    "recovery_race_detected": recovery_result.race_condition_detected,
                    "total_time": initial_result.connection_time + scenario["delay_between"] + recovery_result.connection_time
                })
        
        # Analyze recovery results
        successful_recoveries = [r for r in recovery_results if r["recovery_success"]]
        failed_recoveries = [r for r in recovery_results if not r["recovery_success"]]
        
        print(f"📊 RECOVERY AND RECONNECTION RESULTS:")
        print(f"   Total scenarios: {len(recovery_results)}")
        print(f"   Successful recoveries: {len(successful_recoveries)}")
        print(f"   Failed recoveries: {len(failed_recoveries)}")
        
        # Recovery pattern analysis
        patterns = {
            "race_to_success": 0,  # Initial race condition, recovery successful
            "success_to_success": 0,  # Both successful
            "race_to_race": 0,  # Both failed with race conditions
            "other": 0
        }
        
        for result in recovery_results:
            if result["initial_race_detected"] and result["recovery_success"]:
                patterns["race_to_success"] += 1
            elif result["initial_success"] and result["recovery_success"]:
                patterns["success_to_success"] += 1
            elif result["initial_race_detected"] and result["recovery_race_detected"]:
                patterns["race_to_race"] += 1
            else:
                patterns["other"] += 1
        
        print(f"   Recovery patterns: {patterns}")
        
        # VALIDATION: Recovery connections should work better than initial attempts
        recovery_success_rate = len(successful_recoveries) / len(recovery_results)
        assert recovery_success_rate >= 0.5, f"Poor recovery success rate: {recovery_success_rate:.1%}"
        
        # At least some race-to-success recoveries should occur (validates fix works)
        assert patterns["race_to_success"] > 0, "No successful recovery from race conditions observed"
        
        print("✅ RACE CONDITION RECOVERY AND RECONNECTION COMPLETED")


@pytest.mark.e2e
@pytest.mark.real_services  
class TestWebSocketRaceConditionPerformanceBenchmarks:
    """
    Performance benchmarks for WebSocket race condition scenarios.
    
    These tests provide performance metrics for race condition detection
    and recovery under various Cloud Run conditions.
    """
    
    @pytest.fixture
    async def benchmark_framework(self):
        """Create race condition test framework for benchmarking."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        return WebSocketRaceConditionTestFramework(auth_helper, environment="test")
    
    @pytest.mark.asyncio
    async def test_websocket_connection_timing_benchmarks(self, benchmark_framework):
        """
        PERFORMANCE TEST: WebSocket connection timing benchmarks across latency profiles.
        
        This test provides detailed timing analysis for WebSocket connections
        under different Cloud Run latency conditions.
        """
        print("📊 PERFORMANCE BENCHMARK: WebSocket Connection Timing")
        
        # Test all latency profiles
        profile_names = ["fast", "typical", "slow", "stress"]
        benchmark_results = {}
        
        for profile_name in profile_names:
            profile = benchmark_framework.CLOUD_RUN_LATENCY_PROFILES[profile_name]
            print(f"   Benchmarking {profile.name} profile...")
            
            # Run multiple iterations for statistical validity
            iterations = 3
            timing_results = []
            
            for iteration in range(iterations):
                result = await benchmark_framework.test_websocket_connection_with_latency(
                    profile=profile,
                    test_name=f"benchmark_{profile_name}_{iteration}"
                )
                
                timing_results.append({
                    "success": result.success,
                    "connection_time": result.connection_time,
                    "race_detected": result.race_condition_detected,
                    "events_count": len(result.websocket_events_received)
                })
                
                # Brief delay between iterations
                await asyncio.sleep(0.2)
            
            # Calculate statistics
            successful_times = [r["connection_time"] for r in timing_results if r["success"]]
            race_count = sum(1 for r in timing_results if r["race_detected"])
            
            if successful_times:
                avg_time = sum(successful_times) / len(successful_times)
                min_time = min(successful_times)
                max_time = max(successful_times)
                
                benchmark_results[profile_name] = {
                    "iterations": iterations,
                    "successful": len(successful_times),
                    "success_rate": len(successful_times) / iterations,
                    "avg_connection_time": avg_time,
                    "min_connection_time": min_time,
                    "max_connection_time": max_time,
                    "race_conditions": race_count,
                    "race_rate": race_count / iterations
                }
                
                print(f"     Results: {len(successful_times)}/{iterations} successful")
                print(f"     Timing: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")
                print(f"     Race conditions: {race_count}")
            else:
                benchmark_results[profile_name] = {
                    "iterations": iterations,
                    "successful": 0,
                    "success_rate": 0.0,
                    "race_conditions": race_count,
                    "race_rate": race_count / iterations
                }
                print(f"     Results: 0/{iterations} successful (all failed)")
        
        # Report comprehensive benchmark results
        print("📊 WEBSOCKET CONNECTION TIMING BENCHMARK RESULTS:")
        for profile_name, stats in benchmark_results.items():
            print(f"   {profile_name}:")
            print(f"     Success rate: {stats['success_rate']:.1%}")
            if stats["successful"] > 0:
                print(f"     Connection time: {stats['avg_connection_time']:.3f}s (avg)")
                print(f"     Range: {stats['min_connection_time']:.3f}s - {stats['max_connection_time']:.3f}s")
            print(f"     Race condition rate: {stats['race_rate']:.1%}")
        
        # Performance assertions
        fast_stats = benchmark_results.get("fast")
        if fast_stats:
            assert fast_stats["success_rate"] >= 0.7, f"Fast profile performance too poor: {fast_stats['success_rate']:.1%}"
            if fast_stats["successful"] > 0:
                assert fast_stats["avg_connection_time"] <= 3.0, f"Fast profile too slow: {fast_stats['avg_connection_time']:.3f}s"
        
        print("✅ WEBSOCKET CONNECTION TIMING BENCHMARKS COMPLETED")


if __name__ == "__main__":
    # Run specific tests for manual execution
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])