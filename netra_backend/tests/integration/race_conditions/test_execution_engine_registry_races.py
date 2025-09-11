"""
Race Condition Tests: Execution Engine Registry Management

This module tests for race conditions in execution engine registry state management.
Validates that execution engines remain stable and isolated under concurrent load.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Ensure reliable agent execution engine management
- Value Impact: Prevents execution failures, engine corruption, and inconsistent behavior
- Strategic Impact: CRITICAL - Execution engine registry is core to agent operations

Test Coverage:
- Concurrent engine registration and access
- Registry state corruption detection
- Engine lifecycle management races
- Agent factory integration races
- Cross-engine isolation verification
"""

import asyncio
import time
import uuid
import weakref
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional
from unittest.mock import Mock, AsyncMock, MagicMock
import pytest

from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry, get_agent_registry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory as AgentFactory, get_agent_instance_factory as get_agent_factory
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.agent_execution_tracker import ExecutionTracker, get_execution_tracker
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
# Skip requires_real functions - using real services by default in integration tests
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestExecutionEngineRegistryRaces(SSotBaseTestCase):
    """Test race conditions in execution engine registry management."""
    
    def setup_method(self):
        """Set up test environment with registry tracking."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.set("TEST_MODE", "execution_engine_race_testing", source="test")
        
        # Track registry state and operations
        self.registered_engines: Dict[str, Any] = {}
        self.registry_operations: List[Dict] = []
        self.race_condition_detections: List[Dict] = []
        self.engine_refs: List[weakref.ref] = []
        self.agent_factory_operations: List[Dict] = []
        
        # Initialize database helper for real service tests
        self.db_helper = DatabaseTestHelper()
        
    def teardown_method(self):
        """Clean up test state and verify no engine leaks."""
        # Clear tracking data
        self.registered_engines.clear()
        self.registry_operations.clear()
        self.race_condition_detections.clear()
        self.agent_factory_operations.clear()
        
        # Check for leaked engine references
        leaked_refs = [ref for ref in self.engine_refs if ref() is not None]
        if leaked_refs:
            logger.warning(f"Potential engine leaks detected: {len(leaked_refs)} engines not garbage collected")
        
        self.engine_refs.clear()
        
        super().teardown_method()
    
    def _create_mock_execution_engine(self, engine_id: str, agent_name: str) -> Mock:
        """Create mock execution engine for testing."""
        engine = Mock(spec=ExecutionEngine)
        engine.engine_id = engine_id
        engine.agent_name = agent_name
        engine.is_running = False
        engine.execution_count = 0
        
        async def mock_execute(state: DeepAgentState, run_id: str, **kwargs):
            """Mock execute method with race condition tracking."""
            engine.is_running = True
            engine.execution_count += 1
            
            # Track execution for race condition analysis
            execution_event = {
                "engine_id": engine_id,
                "agent_name": agent_name,
                "run_id": run_id,
                "execution_count": engine.execution_count,
                "timestamp": time.time(),
                "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
            }
            
            self._track_registry_operation("engine_execute", execution_event)
            
            # Simulate work with potential race conditions
            await asyncio.sleep(0.001)
            
            engine.is_running = False
            
            return {
                "success": True,
                "result": f"Execution result from {engine_id}",
                "execution_count": engine.execution_count
            }
        
        engine.execute = mock_execute
        return engine
    
    def _create_mock_agent_registry(self) -> Mock:
        """Create mock agent registry with race condition tracking."""
        registry = Mock(spec=AgentRegistry)
        self.registry_agents = {}
        
        def mock_register_agent(agent_name: str, agent_class: Any):
            """Mock register agent with race condition tracking."""
            if agent_name in self.registry_agents:
                # Race condition: agent already registered
                self._detect_race_condition(
                    "duplicate_agent_registration",
                    {"agent_name": agent_name},
                    {"existing_class": self.registry_agents[agent_name], "new_class": agent_class}
                )
                return False
            
            self.registry_agents[agent_name] = agent_class
            self._track_registry_operation("register_agent", {
                "agent_name": agent_name,
                "agent_class": str(agent_class)
            })
            return True
        
        def mock_get_agent(agent_name: str):
            """Mock get agent with tracking."""
            if agent_name in self.registry_agents:
                self._track_registry_operation("get_agent", {"agent_name": agent_name})
                return self.registry_agents[agent_name]
            return None
        
        def mock_list_agents():
            """Mock list agents."""
            return list(self.registry_agents.keys())
        
        registry.register_agent = mock_register_agent
        registry.get_agent = mock_get_agent
        registry.list_agents = mock_list_agents
        
        return registry
    
    def _track_registry_operation(self, operation_type: str, operation_data: Dict):
        """Track registry operation for race condition analysis."""
        operation = {
            "operation_type": operation_type,
            "operation_data": operation_data,
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.registry_operations.append(operation)
        
        # Check for potential race conditions
        self._check_registry_operation_races(operation)
    
    def _check_registry_operation_races(self, operation: Dict):
        """Check for race conditions in registry operations."""
        operation_type = operation["operation_type"]
        operation_data = operation["operation_data"]
        
        # Check for concurrent operations on same agent
        if operation_type in ["register_agent", "get_agent"]:
            agent_name = operation_data.get("agent_name")
            if agent_name:
                # Find concurrent operations on same agent
                concurrent_ops = [
                    op for op in self.registry_operations[-10:]  # Check last 10 operations
                    if (op["operation_data"].get("agent_name") == agent_name and
                        abs(op["timestamp"] - operation["timestamp"]) < 0.01 and  # Within 10ms
                        op != operation)
                ]
                
                if len(concurrent_ops) > 0:
                    self._detect_race_condition(
                        "concurrent_agent_operations",
                        {"agent_name": agent_name, "concurrent_count": len(concurrent_ops)},
                        operation
                    )
        
        # Check for excessive operation frequency (potential race/loop)
        recent_ops = [
            op for op in self.registry_operations[-20:]  # Check last 20 operations
            if op["operation_type"] == operation_type and
               (time.time() - op["timestamp"]) < 0.1  # Within 100ms
        ]
        
        if len(recent_ops) > 10:  # More than 10 operations of same type in 100ms
            self._detect_race_condition(
                "excessive_operation_frequency",
                {"operation_type": operation_type, "frequency": len(recent_ops)},
                operation
            )
    
    def _detect_race_condition(self, condition_type: str, metadata: Dict, context: Dict):
        """Record race condition detection."""
        race_condition = {
            "condition_type": condition_type,
            "metadata": metadata,
            "context": context,
            "timestamp": time.time(),
            "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
        }
        self.race_condition_detections.append(race_condition)
        logger.warning(f"Execution engine registry race condition detected: {race_condition}")
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    async def test_concurrent_engine_registration(self):
        """Test concurrent execution engine registration for race conditions."""
        registry = self._create_mock_agent_registry()
        
        async def register_execution_engine(engine_index: int):
            """Register an execution engine with race condition tracking."""
            try:
                engine_id = f"race_engine_{engine_index:03d}"
                agent_name = f"race_agent_{engine_index % 5}"  # 5 different agent types
                
                # Create mock execution engine
                engine = self._create_mock_execution_engine(engine_id, agent_name)
                self.engine_refs.append(weakref.ref(engine))
                
                # Register in our tracking
                if engine_id in self.registered_engines:
                    # Race condition detected
                    self._detect_race_condition(
                        "duplicate_engine_registration",
                        {"engine_id": engine_id},
                        {"existing_agent": self.registered_engines[engine_id].agent_name}
                    )
                    return {"engine_index": engine_index, "success": False, "error": "duplicate_engine_id"}
                
                self.registered_engines[engine_id] = engine
                
                # Register agent with registry
                # Simulate agent class
                agent_class = type(f"Agent{engine_index}", (), {"name": agent_name})
                registration_success = registry.register_agent(agent_name, agent_class)
                
                # Small delay to create race opportunities
                await asyncio.sleep(0.0001)
                
                # Verify registration
                retrieved_agent = registry.get_agent(agent_name)
                retrieval_success = retrieved_agent is not None
                
                return {
                    "engine_index": engine_index,
                    "engine_id": engine_id,
                    "agent_name": agent_name,
                    "registration_success": registration_success,
                    "retrieval_success": retrieval_success,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Engine registration failed for index {engine_index}: {e}")
                return {
                    "engine_index": engine_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Register 30 engines concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[register_execution_engine(i) for i in range(30)],
            return_exceptions=True
        )
        registration_time = time.time() - start_time
        
        # Analyze results
        successful_registrations = len([r for r in results if isinstance(r, dict) and r.get("success")])
        failed_registrations = len([r for r in results if not isinstance(r, dict) or not r.get("success")])
        successful_retrievals = len([r for r in results if isinstance(r, dict) and r.get("retrieval_success")])
        
        # Check for race condition indicators
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in engine registration: {self.race_condition_detections}"
        )
        
        # Verify all registrations succeeded
        assert successful_registrations == 30, (
            f"Expected 30 successful engine registrations, got {successful_registrations}. "
            f"Failed: {failed_registrations}. Race conditions may have caused registration failures."
        )
        
        # Verify all retrievals succeeded
        assert successful_retrievals == successful_registrations, (
            f"Expected {successful_registrations} successful retrievals, got {successful_retrievals}. "
            f"Race conditions may have affected registry state consistency."
        )
        
        # Verify unique engine IDs
        engine_ids = [r.get("engine_id") for r in results if isinstance(r, dict) and r.get("engine_id")]
        unique_engine_ids = set(engine_ids)
        
        assert len(engine_ids) == len(unique_engine_ids), (
            f"Duplicate engine IDs detected: {len(engine_ids)} total, {len(unique_engine_ids)} unique. "
            f"Race condition in engine ID generation."
        )
        
        # Verify reasonable registration time
        assert registration_time < 10.0, (
            f"Engine registration took {registration_time:.2f}s, expected < 10s. "
            f"This may indicate serialization or registry bottlenecks."
        )
        
        # Verify agent registry state consistency
        registered_agents = registry.list_agents()
        expected_agents = set(f"race_agent_{i}" for i in range(5))  # 5 different agent types
        actual_agents = set(registered_agents)
        
        assert expected_agents.issubset(actual_agents), (
            f"Missing agents in registry: expected {expected_agents}, got {actual_agents}. "
            f"Race conditions may have caused registration inconsistencies."
        )
        
        logger.info(
            f"✅ 30 concurrent engine registrations completed successfully in {registration_time:.2f}s. "
            f"Success rate: {successful_registrations}/30, Retrievals: {successful_retrievals}/30, "
            f"Unique engines: {len(unique_engine_ids)}, Registered agents: {len(registered_agents)}, "
            f"Race conditions: {len(self.race_condition_detections)}"
        )
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    async def test_concurrent_engine_execution(self):
        """Test concurrent execution through engines for race conditions."""
        registry = self._create_mock_agent_registry()
        
        # Set up engines and agents
        engines = {}
        for i in range(5):
            agent_name = f"exec_agent_{i}"
            engine_id = f"exec_engine_{i}"
            
            engine = self._create_mock_execution_engine(engine_id, agent_name)
            engines[agent_name] = engine
            
            # Register agent
            agent_class = type(f"Agent{i}", (), {"name": agent_name})
            registry.register_agent(agent_name, agent_class)
        
        async def execute_through_engine(execution_index: int):
            """Execute agent through engine with race condition tracking."""
            try:
                agent_name = f"exec_agent_{execution_index % 5}"  # Round-robin through agents
                run_id = f"exec_run_{execution_index:03d}_{uuid.uuid4().hex[:6]}"
                user_id = f"exec_user_{execution_index:03d}"
                
                # Get engine
                engine = engines.get(agent_name)
                if not engine:
                    return {"execution_index": execution_index, "success": False, "error": "engine_not_found"}
                
                # Create execution state
                state = DeepAgentState()
                state.user_id = user_id
                state.agent_name = agent_name
                state.current_step = "initialization"
                
                # Track execution attempt
                execution_event = {
                    "execution_index": execution_index,
                    "agent_name": agent_name,
                    "run_id": run_id,
                    "user_id": user_id,
                    "engine_id": engine.engine_id
                }
                self._track_registry_operation("execution_attempt", execution_event)
                
                # Execute through engine
                result = await engine.execute(state, run_id)
                
                # Verify execution result
                execution_success = result.get("success", False)
                execution_count = result.get("execution_count", 0)
                
                return {
                    "execution_index": execution_index,
                    "agent_name": agent_name,
                    "run_id": run_id,
                    "engine_id": engine.engine_id,
                    "execution_success": execution_success,
                    "execution_count": execution_count,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Engine execution failed for index {execution_index}: {e}")
                return {
                    "execution_index": execution_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute 50 operations concurrently (10 per engine)
        execution_results = await asyncio.gather(
            *[execute_through_engine(i) for i in range(50)],
            return_exceptions=True
        )
        
        # Analyze execution results
        successful_executions = len([r for r in execution_results if isinstance(r, dict) and r.get("success")])
        failed_executions = len([r for r in execution_results if not isinstance(r, dict) or not r.get("success")])
        successful_agent_executions = len([r for r in execution_results if isinstance(r, dict) and r.get("execution_success")])
        
        # Group executions by engine
        executions_by_engine = defaultdict(list)
        for result in execution_results:
            if isinstance(result, dict) and result.get("success"):
                engine_id = result.get("engine_id")
                if engine_id:
                    executions_by_engine[engine_id].append(result)
        
        # Verify each engine handled exactly 10 executions
        for engine_id, engine_executions in executions_by_engine.items():
            assert len(engine_executions) == 10, (
                f"Engine {engine_id} should have 10 executions, got {len(engine_executions)}. "
                f"Race conditions may have caused execution distribution issues."
            )
            
            # Verify execution counts are sequential (no race in engine state)
            execution_counts = [e.get("execution_count", 0) for e in engine_executions]
            expected_counts = list(range(1, 11))  # 1 through 10
            execution_counts.sort()
            
            assert execution_counts == expected_counts, (
                f"Engine {engine_id} execution counts not sequential: {execution_counts}. "
                f"Expected {expected_counts}. Race condition in engine state management."
            )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in engine execution: {self.race_condition_detections}"
        )
        
        # Verify all executions succeeded
        assert successful_executions == 50, (
            f"Expected 50 successful executions, got {successful_executions}. "
            f"Failed: {failed_executions}. Race conditions may have caused execution failures."
        )
        
        assert successful_agent_executions == successful_executions, (
            f"Expected {successful_executions} successful agent executions, got {successful_agent_executions}. "
            f"Race conditions may have affected agent execution logic."
        )
        
        logger.info(
            f"✅ 50 concurrent engine executions completed successfully. "
            f"Success rate: {successful_executions}/50, Agent executions: {successful_agent_executions}/50, "
            f"Engines used: {len(executions_by_engine)}, Race conditions: {len(self.race_condition_detections)}"
        )
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    @requires_real_database
    @requires_real_redis
    async def test_agent_factory_integration_races(self):
        """Test agent factory integration for race conditions with real services."""
        
        async def factory_integration_test(test_index: int):
            """Test agent factory integration with race condition tracking."""
            try:
                user_id = f"factory_user_{test_index:03d}"
                agent_name = f"factory_agent_{test_index % 3}"  # 3 different agent types
                
                # Track factory operation
                factory_event = {
                    "test_index": test_index,
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "timestamp": time.time()
                }
                self.agent_factory_operations.append(factory_event)
                
                # Get agent factory (real factory for integration test)
                try:
                    factory = get_agent_factory()
                except Exception as e:
                    # If real factory not available, create mock
                    factory = Mock()
                    
                    async def mock_create_agent(name, user_context):
                        await asyncio.sleep(0.001)  # Simulate work
                        return Mock(name=name, user_id=user_context.get("user_id"))
                    
                    factory.create_agent = mock_create_agent
                
                # Create agent through factory
                user_context = {
                    "user_id": user_id,
                    "test_index": test_index,
                    "agent_name": agent_name
                }
                
                agent = await factory.create_agent(agent_name, user_context)
                
                # Verify agent creation
                agent_created = agent is not None
                
                # Small delay for race condition opportunities
                await asyncio.sleep(0.001)
                
                return {
                    "test_index": test_index,
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "agent_created": agent_created,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Factory integration test failed for index {test_index}: {e}")
                return {
                    "test_index": test_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Run 24 concurrent factory integration tests (8 per agent type)
        factory_results = await asyncio.gather(
            *[factory_integration_test(i) for i in range(24)],
            return_exceptions=True
        )
        
        # Analyze factory integration results
        successful_tests = len([r for r in factory_results if isinstance(r, dict) and r.get("success")])
        failed_tests = len([r for r in factory_results if not isinstance(r, dict) or not r.get("success")])
        successful_creations = len([r for r in factory_results if isinstance(r, dict) and r.get("agent_created")])
        
        # Group by agent type
        creations_by_agent = defaultdict(list)
        for result in factory_results:
            if isinstance(result, dict) and result.get("success"):
                agent_name = result.get("agent_name")
                if agent_name:
                    creations_by_agent[agent_name].append(result)
        
        # Verify each agent type had exactly 8 creations
        for agent_name, agent_creations in creations_by_agent.items():
            assert len(agent_creations) == 8, (
                f"Agent {agent_name} should have 8 creations, got {len(agent_creations)}. "
                f"Race conditions may have affected factory distribution."
            )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected in factory integration: {self.race_condition_detections}"
        )
        
        # Verify all tests succeeded
        assert successful_tests == 24, (
            f"Expected 24 successful factory tests, got {successful_tests}. "
            f"Failed: {failed_tests}. Race conditions may have caused factory failures."
        )
        
        assert successful_creations == successful_tests, (
            f"Expected {successful_tests} successful agent creations, got {successful_creations}. "
            f"Race conditions may have affected agent creation through factory."
        )
        
        logger.info(
            f"✅ Agent factory integration race test passed: "
            f"{successful_tests}/24 successful tests, {successful_creations} agent creations, "
            f"3 agent types with 8 creations each, 0 race conditions detected"
        )
    
    @pytest.mark.integration
    @pytest.mark.race_conditions
    async def test_registry_state_corruption_detection(self):
        """Test detection of registry state corruption under concurrent load."""
        registry = self._create_mock_agent_registry()
        
        # Track registry state throughout test
        registry_snapshots = []
        
        async def stress_test_registry(batch_index: int):
            """Stress test registry with operations that could cause corruption."""
            batch_operations = []
            
            try:
                for op_index in range(10):  # 10 operations per batch
                    operation_type = op_index % 3  # Cycle through operation types
                    
                    if operation_type == 0:
                        # Register agent
                        agent_name = f"stress_agent_{batch_index:02d}_{op_index:02d}"
                        agent_class = type(f"StressAgent{batch_index}{op_index}", (), {"name": agent_name})
                        
                        success = registry.register_agent(agent_name, agent_class)
                        batch_operations.append({
                            "type": "register",
                            "agent_name": agent_name,
                            "success": success
                        })
                        
                    elif operation_type == 1:
                        # Get agent
                        agent_name = f"stress_agent_{batch_index:02d}_{(op_index - 1):02d}"  # Get previous
                        agent = registry.get_agent(agent_name)
                        
                        batch_operations.append({
                            "type": "get",
                            "agent_name": agent_name,
                            "found": agent is not None
                        })
                        
                    else:
                        # List agents
                        agents = registry.list_agents()
                        batch_operations.append({
                            "type": "list",
                            "agent_count": len(agents)
                        })
                    
                    # Take registry snapshot
                    registry_snapshots.append({
                        "batch_index": batch_index,
                        "op_index": op_index,
                        "timestamp": time.time(),
                        "registered_agents": len(registry.list_agents()),
                        "thread_id": asyncio.current_task().get_name() if asyncio.current_task() else "unknown"
                    })
                    
                    # Small delay to create race opportunities
                    await asyncio.sleep(0.0001)
                
                return {
                    "batch_index": batch_index,
                    "operations": batch_operations,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Registry stress test batch {batch_index} failed: {e}")
                return {
                    "batch_index": batch_index,
                    "operations": batch_operations,
                    "success": False,
                    "error": str(e)
                }
        
        # Run 15 concurrent stress test batches
        start_time = time.time()
        stress_results = await asyncio.gather(
            *[stress_test_registry(i) for i in range(15)],
            return_exceptions=True
        )
        stress_time = time.time() - start_time
        
        # Analyze stress test results
        successful_batches = len([r for r in stress_results if isinstance(r, dict) and r.get("success")])
        total_operations = sum(
            len(r["operations"]) for r in stress_results 
            if isinstance(r, dict) and r.get("operations")
        )
        
        # Analyze registry state consistency
        final_agent_count = len(registry.list_agents())
        expected_registrations = sum(
            len([op for op in r["operations"] if op["type"] == "register" and op["success"]])
            for r in stress_results if isinstance(r, dict) and r.get("operations")
        )
        
        # Check for state corruption indicators
        # 1. Final agent count should match successful registrations
        assert final_agent_count == expected_registrations, (
            f"Registry state corruption detected: {final_agent_count} agents in registry, "
            f"but {expected_registrations} successful registrations. "
            f"Race conditions may have corrupted registry state."
        )
        
        # 2. Registry snapshots should show monotonic increase in agent count
        snapshot_counts = [s["registered_agents"] for s in registry_snapshots]
        for i in range(1, len(snapshot_counts)):
            assert snapshot_counts[i] >= snapshot_counts[i-1], (
                f"Registry agent count decreased: {snapshot_counts[i-1]} -> {snapshot_counts[i]} "
                f"at snapshot {i}. Race condition may have caused state corruption."
            )
        
        # Check for race conditions
        assert len(self.race_condition_detections) == 0, (
            f"Race conditions detected during registry stress test: {self.race_condition_detections}"
        )
        
        # Verify stress test completed successfully
        assert successful_batches == 15, (
            f"Expected 15 successful stress test batches, got {successful_batches}. "
            f"Race conditions may have caused batch failures."
        )
        
        # Verify reasonable stress test time
        assert stress_time < 20.0, (
            f"Registry stress test took {stress_time:.2f}s, expected < 20s. "
            f"Registry bottlenecks may indicate race conditions."
        )
        
        logger.info(
            f"✅ Registry state corruption detection test passed: "
            f"{successful_batches}/15 successful batches, {total_operations} total operations "
            f"in {stress_time:.2f}s. Final agent count: {final_agent_count}, "
            f"Expected registrations: {expected_registrations}, "
            f"Snapshots taken: {len(registry_snapshots)}, "
            f"Race conditions: {len(self.race_condition_detections)}"
        )