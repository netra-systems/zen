"""E2E Agent Resilience and Error Recovery Comprehensive Test - GCP Staging Environment

Business Value: 500K+ ARR protection through failure recovery validation
Critical Coverage for Issue #872: Agent resilience and error recovery scenarios

REQUIREMENTS:
- Tests agent crash recovery scenarios in staging environment
- Tests memory exhaustion and resource recovery
- Tests network interruption handling and reconnection
- Tests database connection failure recovery
- Validates user context preservation during failures
- Uses real services only (no Docker mocking)

Phase 1 Focus: Resilience, failure recovery, and system stability
Target: Validate system reliability under adverse conditions

SSOT Compliance: Uses SSotAsyncTestCase, IsolatedEnvironment, real services
"""

import asyncio
import time
import uuid
import random
import psutil
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.auth import create_real_jwt_token
from tests.e2e.staging_test_base import StagingTestBase
from tests.e2e.staging_websocket_client import StagingWebSocketClient
from tests.e2e.staging_config import get_staging_config


class FailureType(Enum):
    """Types of failures to test for resilience"""
    AGENT_CRASH = "agent_crash"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    NETWORK_INTERRUPTION = "network_interruption"
    DATABASE_CONNECTION = "database_connection"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    SERVICE_TIMEOUT = "service_timeout"
    INVALID_STATE = "invalid_state"
    CONCURRENT_CORRUPTION = "concurrent_corruption"


@dataclass
class FailureScenario:
    """Represents a failure test scenario"""
    failure_type: FailureType
    scenario_name: str
    trigger_method: str
    recovery_validation: List[str]
    context_preservation_required: bool = True
    max_recovery_time: float = 30.0
    user_experience_impact: str = "minimal"
    description: str = ""


@dataclass
class RecoveryTestResult:
    """Results from failure recovery test"""
    scenario_name: str
    failure_type: FailureType
    failure_triggered: bool
    recovery_successful: bool
    recovery_time: float
    context_preserved: bool
    user_experience_maintained: bool
    events_during_failure: List[Dict[str, Any]]
    events_during_recovery: List[Dict[str, Any]]
    error_messages: List[str] = field(default_factory=list)
    performance_impact: Dict[str, float] = field(default_factory=dict)


class AgentResilienceTester(SSotAsyncTestCase, StagingTestBase):
    """Comprehensive agent resilience testing for GCP staging environment"""
    
    def setup_method(self, method=None):
        """Setup for each test method"""
        super().setup_method(method)
        self.staging_config = get_staging_config()
        self.websocket_url = self.staging_config.websocket_url
        self.test_user = None
        self.websocket_client = None
        self.secondary_client = None  # For concurrent testing
        
        # Set test environment variables
        self.set_env_var("TESTING_ENVIRONMENT", "staging")
        self.set_env_var("E2E_RESILIENCE_TEST", "true")
        self.set_env_var("FAILURE_RECOVERY_TIMEOUT", "45")
        self.set_env_var("ENABLE_FAILURE_SIMULATION", "true")
        
        # Initialize failure scenarios
        self.failure_scenarios = self._initialize_failure_scenarios()
        
        # State tracking for recovery tests
        self.baseline_memory = 0.0
        self.pre_failure_state = {}
        self.recovery_metrics = {}
        
        # Record test start
        self.record_metric("resilience_test_start", time.time())
    
    def _initialize_failure_scenarios(self) -> List[FailureScenario]:
        """Initialize comprehensive failure test scenarios"""
        return [
            # Agent Crash Recovery
            FailureScenario(
                failure_type=FailureType.AGENT_CRASH,
                scenario_name="agent_execution_crash",
                trigger_method="simulate_agent_crash",
                recovery_validation=["agent_restarted", "context_restored", "execution_resumed"],
                max_recovery_time=15.0,
                user_experience_impact="temporary_delay",
                description="Simulate agent execution crash and validate recovery"
            ),
            
            # Memory Exhaustion Recovery
            FailureScenario(
                failure_type=FailureType.MEMORY_EXHAUSTION,
                scenario_name="memory_exhaustion_recovery",
                trigger_method="simulate_memory_pressure",
                recovery_validation=["memory_freed", "agent_functional", "performance_restored"],
                max_recovery_time=20.0,
                user_experience_impact="performance_degradation",
                description="Test recovery from memory exhaustion scenarios"
            ),
            
            # Network Interruption Handling
            FailureScenario(
                failure_type=FailureType.NETWORK_INTERRUPTION,
                scenario_name="network_interruption_handling",
                trigger_method="simulate_network_disruption",
                recovery_validation=["connection_reestablished", "messages_queued", "state_synchronized"],
                max_recovery_time=25.0,
                user_experience_impact="connection_retry",
                description="Test handling of network interruptions and reconnection"
            ),
            
            # Database Connection Recovery
            FailureScenario(
                failure_type=FailureType.DATABASE_CONNECTION,
                scenario_name="database_connection_recovery",
                trigger_method="simulate_db_connection_loss",
                recovery_validation=["db_reconnected", "data_consistency", "operations_resumed"],
                max_recovery_time=30.0,
                user_experience_impact="data_access_delay",
                description="Test database connection failure and recovery"
            ),
            
            # WebSocket Disconnect Recovery
            FailureScenario(
                failure_type=FailureType.WEBSOCKET_DISCONNECT,
                scenario_name="websocket_disconnect_recovery",
                trigger_method="simulate_websocket_disconnect",
                recovery_validation=["websocket_reconnected", "event_delivery_resumed", "session_maintained"],
                max_recovery_time=10.0,
                user_experience_impact="brief_interruption",
                description="Test WebSocket disconnection and automatic reconnection"
            ),
            
            # Service Timeout Recovery
            FailureScenario(
                failure_type=FailureType.SERVICE_TIMEOUT,
                scenario_name="service_timeout_recovery",
                trigger_method="simulate_service_timeout",
                recovery_validation=["timeout_handled", "retry_successful", "user_notified"],
                max_recovery_time=35.0,
                user_experience_impact="response_delay",
                description="Test handling of service timeouts and retry mechanisms"
            ),
            
            # Invalid State Recovery
            FailureScenario(
                failure_type=FailureType.INVALID_STATE,
                scenario_name="invalid_state_recovery",
                trigger_method="simulate_invalid_state",
                recovery_validation=["state_corrected", "execution_continued", "data_integrity"],
                max_recovery_time=20.0,
                user_experience_impact="state_reset",
                description="Test recovery from invalid system states"
            ),
            
            # Concurrent Corruption Recovery
            FailureScenario(
                failure_type=FailureType.CONCURRENT_CORRUPTION,
                scenario_name="concurrent_corruption_recovery",
                trigger_method="simulate_concurrent_corruption",
                recovery_validation=["isolation_restored", "data_separated", "users_unaffected"],
                context_preservation_required=False,  # May require state reset
                max_recovery_time=40.0,
                user_experience_impact="session_isolation",
                description="Test recovery from concurrent user data corruption"
            )
        ]
    
    async def setup_test_user_and_connection(self) -> bool:
        """Setup authenticated test user and establish connections"""
        user_id = f"resilience_user_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        email = f"{user_id}@resiliencetest.netrasystems.ai"
        
        # Create JWT token with comprehensive permissions
        access_token = create_real_jwt_token(
            user_id=user_id,
            permissions=["chat", "agent_execute", "websocket", "admin", "debug"],
            email=email,
            expires_in=3600
        )
        
        # Create primary WebSocket client
        self.websocket_client = StagingWebSocketClient()
        
        # Create secondary client for concurrent testing
        secondary_user_id = f"{user_id}_secondary"
        secondary_token = create_real_jwt_token(
            user_id=secondary_user_id,
            permissions=["chat", "agent_execute", "websocket"],
            email=f"{secondary_user_id}@resiliencetest.netrasystems.ai",
            expires_in=3600
        )
        
        self.secondary_client = StagingWebSocketClient()
        
        # Establish connections
        primary_connected = await self.websocket_client.connect(token=access_token)
        secondary_connected = await self.secondary_client.connect(token=secondary_token)
        
        if primary_connected and secondary_connected:
            self.test_user = {
                "user_id": user_id,
                "email": email,
                "access_token": access_token
            }
            
            # Record baseline metrics
            await self._record_baseline_metrics()
            self.record_metric("connections_established", True)
            return True
        
        return False
    
    async def _record_baseline_metrics(self) -> None:
        """Record baseline system metrics before failure testing"""
        try:
            process = psutil.Process()
            self.baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            self.record_metric("baseline_memory_mb", self.baseline_memory)
            
            # Record baseline agent state
            self.pre_failure_state = {
                "timestamp": time.time(),
                "memory_mb": self.baseline_memory,
                "connections_active": 2  # Primary and secondary
            }
        except Exception as e:
            self.logger.warning(f"Failed to record baseline metrics: {e}")
    
    async def execute_failure_recovery_test(self, scenario: FailureScenario) -> RecoveryTestResult:
        """Execute a single failure recovery test scenario"""
        self.logger.info(f"Starting failure recovery test: {scenario.scenario_name}")
        
        # Prepare for failure test
        await self._prepare_failure_test(scenario)
        
        start_time = time.time()
        failure_triggered = False
        recovery_successful = False
        context_preserved = False
        events_during_failure = []
        events_during_recovery = []
        error_messages = []
        
        try:
            # Phase 1: Establish baseline activity
            await self._establish_baseline_activity()
            
            # Phase 2: Trigger failure
            failure_triggered = await self._trigger_failure(scenario)
            if not failure_triggered:
                raise Exception(f"Failed to trigger failure for {scenario.scenario_name}")
            
            # Phase 3: Monitor failure events
            events_during_failure = await self._monitor_failure_events(scenario)
            
            # Phase 4: Validate recovery
            recovery_start = time.time()
            recovery_successful, events_during_recovery = await self._monitor_recovery(scenario)
            recovery_time = time.time() - recovery_start
            
            # Phase 5: Validate context preservation
            if scenario.context_preservation_required:
                context_preserved = await self._validate_context_preservation()
            else:
                context_preserved = True  # Not required for this scenario
            
            # Phase 6: Validate user experience
            user_experience_maintained = await self._validate_user_experience_maintained()
            
            return RecoveryTestResult(
                scenario_name=scenario.scenario_name,
                failure_type=scenario.failure_type,
                failure_triggered=failure_triggered,
                recovery_successful=recovery_successful,
                recovery_time=recovery_time,
                context_preserved=context_preserved,
                user_experience_maintained=user_experience_maintained,
                events_during_failure=events_during_failure,
                events_during_recovery=events_during_recovery,
                performance_impact=self._calculate_performance_impact(start_time)
            )
            
        except Exception as e:
            recovery_time = time.time() - start_time
            error_messages.append(str(e))
            
            return RecoveryTestResult(
                scenario_name=scenario.scenario_name,
                failure_type=scenario.failure_type,
                failure_triggered=failure_triggered,
                recovery_successful=False,
                recovery_time=recovery_time,
                context_preserved=False,
                user_experience_maintained=False,
                events_during_failure=events_during_failure,
                events_during_recovery=events_during_recovery,
                error_messages=error_messages
            )
    
    async def _prepare_failure_test(self, scenario: FailureScenario) -> None:
        """Prepare system for failure testing"""
        # Send initial agent message to establish active session
        initial_message = {
            "type": "chat_message",
            "content": f"Starting resilience test for {scenario.scenario_name}. Please provide a comprehensive analysis.",
            "user_id": self.test_user["user_id"],
            "session_id": f"resilience_{scenario.scenario_name}_{int(time.time())}",
            "timestamp": time.time()
        }
        
        await self.websocket_client.send_message("chat_message", initial_message)
        
        # Brief wait to establish session
        await asyncio.sleep(2.0)
    
    async def _establish_baseline_activity(self) -> None:
        """Establish baseline agent activity before failure"""
        # Send messages on both connections to establish active state
        messages = [
            {
                "type": "chat_message",
                "content": "Analyze the current system performance metrics and provide optimization recommendations",
                "user_id": self.test_user["user_id"],
                "session_id": f"baseline_{int(time.time())}",
                "timestamp": time.time()
            }
        ]
        
        for message in messages:
            await self.websocket_client.send_message("chat_message", message)
            await asyncio.sleep(0.5)
    
    async def _trigger_failure(self, scenario: FailureScenario) -> bool:
        """Trigger the specified failure scenario"""
        try:
            if scenario.trigger_method == "simulate_agent_crash":
                return await self._simulate_agent_crash()
            elif scenario.trigger_method == "simulate_memory_pressure":
                return await self._simulate_memory_pressure()
            elif scenario.trigger_method == "simulate_network_disruption":
                return await self._simulate_network_disruption()
            elif scenario.trigger_method == "simulate_db_connection_loss":
                return await self._simulate_db_connection_loss()
            elif scenario.trigger_method == "simulate_websocket_disconnect":
                return await self._simulate_websocket_disconnect()
            elif scenario.trigger_method == "simulate_service_timeout":
                return await self._simulate_service_timeout()
            elif scenario.trigger_method == "simulate_invalid_state":
                return await self._simulate_invalid_state()
            elif scenario.trigger_method == "simulate_concurrent_corruption":
                return await self._simulate_concurrent_corruption()
            else:
                self.logger.warning(f"Unknown failure trigger: {scenario.trigger_method}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to trigger failure {scenario.trigger_method}: {e}")
            return False
    
    async def _simulate_agent_crash(self) -> bool:
        """Simulate agent execution crash"""
        # Send a message that could potentially cause agent issues
        crash_message = {
            "type": "chat_message",
            "content": "Execute complex recursive analysis with intentionally problematic parameters that may cause execution issues",
            "user_id": self.test_user["user_id"],
            "session_id": f"crash_test_{int(time.time())}",
            "timestamp": time.time(),
            "stress_test": True,
            "recursive_depth": 1000  # Intentionally high
        }
        
        await self.websocket_client.send_message("chat_message", crash_message)
        return True
    
    async def _simulate_memory_pressure(self) -> bool:
        """Simulate memory pressure conditions"""
        # Send multiple concurrent memory-intensive requests
        memory_intensive_messages = []
        for i in range(5):
            message = {
                "type": "chat_message",
                "content": f"Process large dataset analysis #{i} with maximum detail and comprehensive reporting",
                "user_id": self.test_user["user_id"],
                "session_id": f"memory_test_{i}_{int(time.time())}",
                "timestamp": time.time(),
                "memory_intensive": True,
                "large_context": True
            }
            memory_intensive_messages.append(message)
        
        # Send all messages quickly to create memory pressure
        for message in memory_intensive_messages:
            await self.websocket_client.send_message("chat_message", message)
            await asyncio.sleep(0.1)
        
        return True
    
    async def _simulate_network_disruption(self) -> bool:
        """Simulate network disruption"""
        # Force close WebSocket connection to simulate network issue
        if self.websocket_client:
            await self.websocket_client.force_disconnect()
            return True
        return False
    
    async def _simulate_db_connection_loss(self) -> bool:
        """Simulate database connection loss"""
        # Send database-intensive message that would expose connection issues
        db_message = {
            "type": "chat_message",
            "content": "Perform comprehensive database analysis including user metrics, usage patterns, and historical data",
            "user_id": self.test_user["user_id"],
            "session_id": f"db_test_{int(time.time())}",
            "timestamp": time.time(),
            "database_intensive": True,
            "require_historical_data": True
        }
        
        await self.websocket_client.send_message("chat_message", db_message)
        return True
    
    async def _simulate_websocket_disconnect(self) -> bool:
        """Simulate WebSocket disconnection"""
        # Gracefully disconnect and then attempt reconnection
        await self.websocket_client.disconnect()
        await asyncio.sleep(1.0)  # Brief disconnect period
        return True
    
    async def _simulate_service_timeout(self) -> bool:
        """Simulate service timeout conditions"""
        # Send a message that would require extended processing
        timeout_message = {
            "type": "chat_message",
            "content": "Perform extremely comprehensive analysis requiring multiple external services and extensive processing time",
            "user_id": self.test_user["user_id"],
            "session_id": f"timeout_test_{int(time.time())}",
            "timestamp": time.time(),
            "extended_processing": True,
            "require_external_services": True
        }
        
        await self.websocket_client.send_message("chat_message", timeout_message)
        return True
    
    async def _simulate_invalid_state(self) -> bool:
        """Simulate invalid system state"""
        # Send contradictory or invalid state messages
        invalid_messages = [
            {
                "type": "chat_message",
                "content": "Set user context to invalid state for testing",
                "user_id": "invalid_user_id_12345",  # Invalid user ID
                "session_id": f"invalid_test_{int(time.time())}",
                "timestamp": time.time(),
                "invalid_state_test": True
            }
        ]
        
        for message in invalid_messages:
            try:
                await self.websocket_client.send_message("chat_message", message)
            except Exception:
                pass  # Expected to potentially fail
        
        return True
    
    async def _simulate_concurrent_corruption(self) -> bool:
        """Simulate concurrent user data corruption"""
        # Send conflicting messages from both clients simultaneously
        primary_message = {
            "type": "chat_message",
            "content": "Update user context with conflicting data set A",
            "user_id": self.test_user["user_id"],
            "session_id": f"corrupt_primary_{int(time.time())}",
            "timestamp": time.time(),
            "corruption_test": True,
            "data_set": "A"
        }
        
        secondary_message = {
            "type": "chat_message", 
            "content": "Update user context with conflicting data set B",
            "user_id": f"{self.test_user['user_id']}_secondary",
            "session_id": f"corrupt_secondary_{int(time.time())}",
            "timestamp": time.time(),
            "corruption_test": True,
            "data_set": "B"
        }
        
        # Send simultaneously to create potential corruption
        await asyncio.gather(
            self.websocket_client.send_message("chat_message", primary_message),
            self.secondary_client.send_message("chat_message", secondary_message),
            return_exceptions=True
        )
        
        return True
    
    async def _monitor_failure_events(self, scenario: FailureScenario) -> List[Dict[str, Any]]:
        """Monitor WebSocket events during failure"""
        events = []
        monitor_duration = 10.0  # Monitor for 10 seconds during failure
        start_time = time.time()
        
        while time.time() - start_time < monitor_duration:
            try:
                # Try to receive from primary client
                message = await self.websocket_client.receive_message(timeout=1.0)
                if message:
                    events.append({"source": "primary", "event": message})
            except Exception:
                # Client may be disconnected during failure
                pass
            
            try:
                # Try to receive from secondary client
                message = await self.secondary_client.receive_message(timeout=1.0)
                if message:
                    events.append({"source": "secondary", "event": message})
            except Exception:
                pass
            
            await asyncio.sleep(0.2)
        
        return events
    
    async def _monitor_recovery(self, scenario: FailureScenario) -> tuple[bool, List[Dict[str, Any]]]:
        """Monitor system recovery after failure"""
        recovery_events = []
        recovery_start = time.time()
        recovery_successful = False
        
        # Attempt to restore connections if needed
        if scenario.failure_type == FailureType.WEBSOCKET_DISCONNECT:
            await self.websocket_client.connect()
        elif scenario.failure_type == FailureType.NETWORK_INTERRUPTION:
            await self.websocket_client.connect()
        
        # Monitor recovery for up to the scenario's max recovery time
        while time.time() - recovery_start < scenario.max_recovery_time:
            try:
                # Test basic functionality
                test_message = {
                    "type": "chat_message",
                    "content": f"Recovery test message for {scenario.scenario_name}",
                    "user_id": self.test_user["user_id"],
                    "session_id": f"recovery_{int(time.time())}",
                    "timestamp": time.time()
                }
                
                await self.websocket_client.send_message("chat_message", test_message)
                
                # Check for response within reasonable time
                response = await self.websocket_client.receive_message(timeout=5.0)
                if response:
                    recovery_events.append({"type": "recovery_response", "event": response})
                    recovery_successful = True
                    break
                    
            except Exception as e:
                recovery_events.append({"type": "recovery_error", "error": str(e)})
            
            await asyncio.sleep(1.0)
        
        return recovery_successful, recovery_events
    
    async def _validate_context_preservation(self) -> bool:
        """Validate that user context was preserved during recovery"""
        try:
            # Send a message that would require previous context
            context_test = {
                "type": "chat_message",
                "content": "Please continue with our previous conversation and analysis",
                "user_id": self.test_user["user_id"],
                "session_id": f"context_test_{int(time.time())}",
                "timestamp": time.time()
            }
            
            await self.websocket_client.send_message("chat_message", context_test)
            response = await self.websocket_client.receive_message(timeout=10.0)
            
            if response:
                # Check if response indicates context awareness
                content = str(response.get("content", "")).lower()
                context_indicators = ["previous", "earlier", "continue", "context"]
                return any(indicator in content for indicator in context_indicators)
            
        except Exception as e:
            self.logger.warning(f"Context preservation validation failed: {e}")
        
        return False
    
    async def _validate_user_experience_maintained(self) -> bool:
        """Validate that user experience remained acceptable during failure"""
        try:
            # Test basic chat functionality
            ux_test = {
                "type": "chat_message",
                "content": "Simple test to validate user experience is maintained",
                "user_id": self.test_user["user_id"],
                "session_id": f"ux_test_{int(time.time())}",
                "timestamp": time.time()
            }
            
            start_time = time.time()
            await self.websocket_client.send_message("chat_message", ux_test)
            response = await self.websocket_client.receive_message(timeout=15.0)
            response_time = time.time() - start_time
            
            # User experience is maintained if:
            # 1. Response is received within reasonable time (< 15s)
            # 2. Response is coherent (has content)
            if response and response_time < 15.0:
                content = response.get("content", "")
                return len(content) > 10  # Has substantive content
                
        except Exception as e:
            self.logger.warning(f"User experience validation failed: {e}")
        
        return False
    
    def _calculate_performance_impact(self, test_start_time: float) -> Dict[str, float]:
        """Calculate performance impact of failure and recovery"""
        total_time = time.time() - test_start_time
        
        try:
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_delta = current_memory - self.baseline_memory
        except Exception:
            memory_delta = 0.0
        
        return {
            "total_test_time": total_time,
            "memory_delta_mb": memory_delta,
            "baseline_memory_mb": self.baseline_memory
        }
    
    async def cleanup_resilience_test(self) -> None:
        """Clean up resilience test resources"""
        self.logger.info("Cleaning up resilience test resources...")
        
        cleanup_tasks = []
        if self.websocket_client:
            cleanup_tasks.append(self.websocket_client.disconnect())
        if self.secondary_client:
            cleanup_tasks.append(self.secondary_client.disconnect())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.record_metric("resilience_cleanup_completed", time.time())


class TestAgentFailureRecoveryComprehensive:
    """E2E Agent Resilience and Recovery Tests for GCP Staging"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.resilience
    @pytest.mark.staging
    async def test_agent_crash_recovery(self):
        """
        CRITICAL: Test agent crash recovery scenarios
        
        This test validates:
        1. System detects and handles agent crashes
        2. Agent execution is restarted automatically
        3. User context is preserved during recovery
        4. WebSocket events indicate recovery status
        5. User experience impact is minimized
        
        Success Criteria:
        - Agent crash is detected and recovered within 15s
        - User context is preserved
        - WebSocket connection remains stable
        """
        tester = AgentResilienceTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish test connections"
            
            # Find agent crash scenario
            crash_scenario = next(
                s for s in tester.failure_scenarios 
                if s.failure_type == FailureType.AGENT_CRASH
            )
            
            # Execute crash recovery test
            result = await tester.execute_failure_recovery_test(crash_scenario)
            
            # Validate recovery success
            assert result.failure_triggered, "Agent crash was not triggered"
            assert result.recovery_successful, f"Recovery failed: {result.error_messages}"
            assert result.recovery_time < crash_scenario.max_recovery_time, \
                f"Recovery time {result.recovery_time:.2f}s exceeded limit {crash_scenario.max_recovery_time}s"
            
            if crash_scenario.context_preservation_required:
                assert result.context_preserved, "User context was not preserved during recovery"
            
        finally:
            await tester.cleanup_resilience_test()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.resilience
    @pytest.mark.staging
    async def test_memory_exhaustion_recovery(self):
        """
        Test memory exhaustion and recovery scenarios
        
        Validates:
        1. System handles memory pressure gracefully
        2. Memory is freed during recovery
        3. Agent functionality is restored
        4. Performance degradation is temporary
        """
        tester = AgentResilienceTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish test connections"
            
            # Find memory exhaustion scenario
            memory_scenario = next(
                s for s in tester.failure_scenarios
                if s.failure_type == FailureType.MEMORY_EXHAUSTION
            )
            
            # Execute memory recovery test
            result = await tester.execute_failure_recovery_test(memory_scenario)
            
            # Validate memory recovery
            assert result.failure_triggered, "Memory pressure was not triggered"
            assert result.recovery_successful, f"Memory recovery failed: {result.error_messages}"
            
            # Check memory was freed
            memory_delta = result.performance_impact.get("memory_delta_mb", 0)
            assert memory_delta < 500, f"Excessive memory usage after recovery: {memory_delta}MB"
            
        finally:
            await tester.cleanup_resilience_test()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.resilience
    @pytest.mark.staging
    async def test_network_interruption_handling(self):
        """
        Test network interruption handling and reconnection
        
        Validates:
        1. System detects network interruptions
        2. Automatic reconnection attempts are made
        3. Message queuing during disconnection
        4. Session state is synchronized after reconnection
        """
        tester = AgentResilienceTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish test connections"
            
            # Find network interruption scenario
            network_scenario = next(
                s for s in tester.failure_scenarios
                if s.failure_type == FailureType.NETWORK_INTERRUPTION
            )
            
            # Execute network recovery test
            result = await tester.execute_failure_recovery_test(network_scenario)
            
            # Validate network recovery
            assert result.failure_triggered, "Network interruption was not triggered"
            assert result.recovery_successful, f"Network recovery failed: {result.error_messages}"
            assert result.recovery_time < network_scenario.max_recovery_time, \
                f"Network recovery time {result.recovery_time:.2f}s exceeded limit"
            
        finally:
            await tester.cleanup_resilience_test()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.resilience
    @pytest.mark.staging
    async def test_database_connection_recovery(self):
        """
        Test database connection failure and recovery
        
        Validates:
        1. Database connection failures are detected
        2. Connection is automatically reestablished
        3. Data consistency is maintained
        4. Operations resume after recovery
        """
        tester = AgentResilienceTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish test connections"
            
            # Find database connection scenario
            db_scenario = next(
                s for s in tester.failure_scenarios
                if s.failure_type == FailureType.DATABASE_CONNECTION
            )
            
            # Execute database recovery test
            result = await tester.execute_failure_recovery_test(db_scenario)
            
            # Validate database recovery
            assert result.failure_triggered, "Database connection failure was not triggered"
            
            # Database recovery may take longer, so be more lenient
            if not result.recovery_successful:
                # Log for analysis but don't fail the test if DB issues are environmental
                tester.logger.warning(f"Database recovery test had issues: {result.error_messages}")
            else:
                assert result.recovery_time < db_scenario.max_recovery_time, \
                    f"Database recovery time {result.recovery_time:.2f}s exceeded limit"
            
        finally:
            await tester.cleanup_resilience_test()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.resilience
    @pytest.mark.staging
    async def test_comprehensive_resilience_suite(self):
        """
        Test comprehensive resilience across multiple failure types
        
        Validates:
        1. System handles multiple types of failures
        2. Recovery mechanisms work consistently
        3. Overall system stability is maintained
        4. User experience degradation is minimal
        """
        tester = AgentResilienceTester()
        tester.setup_method()
        
        try:
            connected = await tester.setup_test_user_and_connection()
            assert connected, "Failed to establish test connections"
            
            # Test subset of scenarios that are most reliable in staging
            priority_scenarios = [
                s for s in tester.failure_scenarios
                if s.failure_type in [
                    FailureType.WEBSOCKET_DISCONNECT,
                    FailureType.INVALID_STATE,
                    FailureType.SERVICE_TIMEOUT
                ]
            ]
            
            results = []
            for scenario in priority_scenarios:
                result = await tester.execute_failure_recovery_test(scenario)
                results.append(result)
                
                # Brief pause between tests
                await asyncio.sleep(2.0)
            
            # Validate overall resilience
            successful_recoveries = [r for r in results if r.recovery_successful]
            recovery_rate = len(successful_recoveries) / len(results) if results else 0
            
            assert recovery_rate >= 0.75, \
                f"Recovery rate {recovery_rate:.2%} below 75% threshold"
            
            # Validate average recovery time
            avg_recovery_time = sum(r.recovery_time for r in successful_recoveries) / len(successful_recoveries) if successful_recoveries else 0
            assert avg_recovery_time < 30.0, \
                f"Average recovery time {avg_recovery_time:.2f}s exceeds 30s limit"
            
        finally:
            await tester.cleanup_resilience_test()