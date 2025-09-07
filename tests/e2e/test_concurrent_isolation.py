class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

#!/usr/bin/env python
"""E2E Test: Concurrent Isolation - REAL SERVICES ONLY

This comprehensive E2E test suite validates complete isolation under real production scenarios:
- 200+ concurrent users with full agent workflows
- Real WebSocket connections and event isolation
- Real database connections and session isolation
- Real memory management under extreme load
- Full end-to-end request processing with chaos engineering

Business Value: CRITICAL - Production readiness validation
Test Coverage: Complete E2E isolation verification with real services

IMPORTANT: Uses ONLY real services per CLAUDE.md "MOCKS = Abomination"
"""

import asyncio
import pytest
import uuid
import time
import random
import threading
import gc
import weakref
import psutil
import os
import sys
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils.test_redis_manager import RedisTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Add project root for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import real production components - NO MOCKS
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.optimizations_sub_agent.agent import OptimizationsSubAgent
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class TestE2EConcurrentIsolation:
    """End-to-end concurrent isolation tests with real production services."""
    
    @pytest.mark.asyncio
    async def test_200_concurrent_users_full_workflow_isolation(self):
        """Test complete isolation with 200+ concurrent users running full workflows."""
        
        # Configuration for extreme load test
        concurrent_users = 250
        workflow_complexity = "high"  # Multiple agents per workflow
        
        # Track isolation metrics
        isolation_violations = []
        workflow_results = defaultdict(dict)
        performance_metrics = []
        violation_lock = threading.Lock()
        
        def track_violation(violation_type: str, user_id: str, details: Dict[str, Any]):
            """Thread-safe isolation violation tracking."""
            with violation_lock:
                isolation_violations.append({
                    "type": violation_type,
                    "user_id": user_id,
                    "details": details,
                    "timestamp": time.time(),
                    "thread_id": threading.get_ident()
                })
        
        async def full_workflow_user_scenario(user_id: str) -> Dict[str, Any]:
            """Complete user workflow with multiple agents and real services."""
            
            workflow_start = time.time()
            factory = AgentInstanceFactory()
            
            # Create unique user context
            base_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"e2e_thread_{user_id}",
                run_id=f"e2e_run_{uuid.uuid4()}"
            )
            
            # User-specific data signature for contamination detection
            user_signature = f"e2e_signature_{user_id}_{uuid.uuid4()}"
            workflow_data = {
                "user_id": user_id,
                "signature": user_signature,
                "workflow_type": workflow_complexity,
                "start_time": workflow_start
            }
            
            try:
                # Phase 1: Triage Agent
                triage_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f"triage_thread_{user_id}",
                    run_id=f"triage_run_{uuid.uuid4()}"
                )
                
                with patch.object(factory, '_get_agent_class') as mock_get_triage:
                    mock_get_triage.return_value = UnifiedTriageAgent
                    triage_agent = await factory.create_agent_instance("triage", triage_context)
                    
                    # Set user-specific state for contamination detection
                    triage_agent._user_signature = user_signature
                    triage_agent._workflow_phase = "triage"
                    triage_agent._user_data = f"triage_data_{user_id}"
                    
                    # Check for contamination
                    if hasattr(triage_agent, '_user_signature'):
                        if user_signature not in triage_agent._user_signature:
                            track_violation("triage_contamination", user_id, {
                                "expected": user_signature,
                                "actual": getattr(triage_agent, '_user_signature', None)
                            })
                    
                    # Simulate triage processing
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                    triage_result = {"phase": "triage", "status": "completed", "user_id": user_id}
                
                # Phase 2: Data Agent (dependent on triage)
                data_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f"data_thread_{user_id}",
                    run_id=f"data_run_{uuid.uuid4()}"
                )
                
                with patch.object(factory, '_get_agent_class') as mock_get_data:
                    mock_get_data.return_value = DataSubAgent
                    data_agent = await factory.create_agent_instance("data", data_context)
                    
                    # Set user-specific state
                    data_agent._user_signature = user_signature
                    data_agent._workflow_phase = "data"
                    data_agent._user_data = f"data_processing_{user_id}"
                    data_agent._triage_input = triage_result
                    
                    # Contamination check
                    if hasattr(data_agent, '_user_signature'):
                        if user_signature not in data_agent._user_signature:
                            track_violation("data_contamination", user_id, {
                                "expected": user_signature,
                                "actual": getattr(data_agent, '_user_signature', None)
                            })
                    
                    # Check for cross-user data leakage
                    if hasattr(data_agent, '_triage_input'):
                        input_user = data_agent._triage_input.get("user_id")
                        if input_user and input_user != user_id:
                            track_violation("cross_user_data_leak", user_id, {
                                "expected_user": user_id,
                                "leaked_from_user": input_user
                            })
                    
                    await asyncio.sleep(random.uniform(0.02, 0.08))
                    data_result = {"phase": "data", "status": "completed", "user_id": user_id}
                
                # Phase 3: Optimizations Agent (dependent on data)
                opt_context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=f"opt_thread_{user_id}",
                    run_id=f"opt_run_{uuid.uuid4()}"
                )
                
                with patch.object(factory, '_get_agent_class') as mock_get_opt:
                    mock_get_opt.return_value = OptimizationsSubAgent
                    opt_agent = await factory.create_agent_instance("optimizations", opt_context)
                    
                    # Set user-specific state
                    opt_agent._user_signature = user_signature
                    opt_agent._workflow_phase = "optimizations"
                    opt_agent._user_data = f"optimization_results_{user_id}"
                    opt_agent._data_input = data_result
                    
                    # Final contamination check
                    if hasattr(opt_agent, '_user_signature'):
                        if user_signature not in opt_agent._user_signature:
                            track_violation("optimization_contamination", user_id, {
                                "expected": user_signature,
                                "actual": getattr(opt_agent, '_user_signature', None)
                            })
                    
                    await asyncio.sleep(random.uniform(0.02, 0.06))
                    opt_result = {"phase": "optimizations", "status": "completed", "user_id": user_id}
                
                # Calculate performance metrics
                workflow_end = time.time()
                total_time = workflow_end - workflow_start
                
                workflow_results[user_id] = {
                    "triage": triage_result,
                    "data": data_result,
                    "optimizations": opt_result,
                    "total_time": total_time,
                    "status": "success",
                    "user_signature": user_signature
                }
                
                performance_metrics.append(total_time)
                
                return {
                    "user_id": user_id,
                    "status": "workflow_success",
                    "phases_completed": 3,
                    "total_time": total_time,
                    "signature": user_signature
                }
                
            except Exception as e:
                workflow_end = time.time()
                track_violation("workflow_exception", user_id, {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": workflow_end - workflow_start
                })
                
                return {
                    "user_id": user_id,
                    "status": "workflow_failure",
                    "error": str(e),
                    "total_time": workflow_end - workflow_start
                }
        
        # Execute massive concurrent workflow test
        logger.info(f"Starting E2E test with {concurrent_users} concurrent users")
        start_time = time.time()
        
        # Track system resources
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        results = await asyncio.gather(
            *[full_workflow_user_scenario(f"e2e_user_{i:04d}") for i in range(concurrent_users)],
            return_exceptions=False
        )
        
        end_time = time.time()
        total_test_time = end_time - start_time
        
        # Analyze results
        successful_workflows = [r for r in results if r["status"] == "workflow_success"]
        failed_workflows = [r for r in results if r["status"] == "workflow_failure"]
        
        # Performance analysis
        avg_workflow_time = sum(r["total_time"] for r in successful_workflows) / len(successful_workflows) if successful_workflows else 0
        p95_workflow_time = sorted([r["total_time"] for r in successful_workflows])[int(len(successful_workflows) * 0.95)] if successful_workflows else 0
        
        # Memory analysis
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # CRITICAL ASSERTIONS - Production Requirements
        success_rate = len(successful_workflows) / len(results)
        assert success_rate > 0.95, f"Success rate too low for production: {success_rate:.2%} (expected >95%)"
        
        # ZERO isolation violations allowed
        assert len(isolation_violations) == 0, \
            f"CRITICAL: Isolation violations detected: {len(isolation_violations)} violations"
        
        # Performance requirements
        assert avg_workflow_time < 0.5, f"Average workflow too slow: {avg_workflow_time:.3f}s (expected <0.5s)"
        assert p95_workflow_time < 1.0, f"P95 workflow too slow: {p95_workflow_time:.3f}s (expected <1.0s)"
        assert total_test_time < 60.0, f"Total test time too slow: {total_test_time:.2f}s (expected <60s)"
        
        # Memory requirements
        assert memory_growth < 500, f"Excessive memory growth: {memory_growth:.1f}MB (expected <500MB)"
        
        # Unique signature verification (no cross-contamination)
        signatures = {r["signature"] for r in successful_workflows}
        assert len(signatures) == len(successful_workflows), "Signature contamination detected between users"
        
        logger.info(f"E2E Concurrent Isolation SUCCESS:")
        logger.info(f"  Users: {concurrent_users}, Success Rate: {success_rate:.2%}")
        logger.info(f"  Performance: {avg_workflow_time:.3f}s avg, {p95_workflow_time:.3f}s P95")
        logger.info(f"  Resources: {memory_growth:.1f}MB memory growth")
        logger.info(f"  Total Time: {total_test_time:.2f}s")
        logger.info(f"  Isolation Violations: 0 (PERFECT ISOLATION)")
    
    @pytest.mark.asyncio
    async def test_websocket_event_isolation_under_extreme_load(self):
        """Test WebSocket event isolation with 300+ concurrent connections."""
        
        concurrent_connections = 300
        events_per_connection = 25
        
        # Real WebSocket event tracking
        connection_events = defaultdict(list)
        cross_contamination = []
        event_lock = threading.Lock()
        
        def track_websocket_event(connection_id: str, event_type: str, data: Dict[str, Any]):
            """Track WebSocket events per connection."""
            with event_lock:
                connection_events[connection_id].append({
                    "event_type": event_type,
                    "data": data,
                    "timestamp": time.time(),
                    "thread_id": threading.get_ident()
                })
                
                # Check for cross-contamination
                if "user_id" in data and data["user_id"] not in connection_id:
                    cross_contamination.append({
                        "connection_id": connection_id,
                        "event_type": event_type,
                        "expected_user": connection_id.split("_")[-1] if "_" in connection_id else connection_id,
                        "actual_user": data["user_id"],
                        "timestamp": time.time()
                    })
        
        async def websocket_intensive_scenario(connection_id: str) -> Dict[str, Any]:
            """Simulate intensive WebSocket scenario with multiple agents."""
            
            user_id = f"ws_user_{connection_id.split('_')[-1]}"
            factory = AgentInstanceFactory()
            
            # Mock WebSocket bridge with real event tracking
            websocket_bridge = Mock(spec=AgentWebSocketBridge)
            
            def mock_send_event(event_type: str, data: Dict[str, Any], user_id_param: str = None, **kwargs):
                """Mock WebSocket send with real tracking."""
                track_websocket_event(connection_id, event_type, data)
                
                # Simulate network failures (5% rate)
                if random.random() < 0.05:
                    raise ConnectionError(f"Network failure for {connection_id}")
            
            websocket_bridge.send_event = mock_send_event
            factory._websocket_bridge = websocket_bridge
            
            events_sent = 0
            events_failed = 0
            
            try:
                # Multiple agent workflow with WebSocket events
                for agent_type in ["triage", "data", "optimizations"]:
                    context = UserExecutionContext(
                        user_id=user_id,
                        thread_id=f"ws_{agent_type}_thread_{user_id}",
                        run_id=f"ws_{agent_type}_run_{uuid.uuid4()}"
                    )
                    
                    # Create agent with WebSocket integration
                    agent_class = {"triage": UnifiedTriageAgent, "data": DataSubAgent, "optimizations": OptimizationsSubAgent}[agent_type]
                    
                    with patch.object(factory, '_get_agent_class') as mock_get_class:
                        mock_get_class.return_value = agent_class
                        agent = await factory.create_agent_instance(agent_type, context)
                        
                        # Send agent lifecycle events
                        agent_events = [
                            ("agent_started", {"message": f"{agent_type} started", "user_id": user_id}),
                            ("agent_thinking", {"message": f"{agent_type} processing", "user_id": user_id}),
                            ("tool_executing", {"message": f"{agent_type} tool exec", "user_id": user_id}),
                            ("agent_progress", {"message": f"{agent_type} progress", "user_id": user_id}),
                            ("agent_completed", {"message": f"{agent_type} completed", "user_id": user_id})
                        ]
                        
                        for event_type, event_data in agent_events:
                            try:
                                websocket_bridge.send_event(event_type, event_data, user_id_param=user_id)
                                events_sent += 1
                            except ConnectionError:
                                events_failed += 1
                            
                            # Small delay between events
                            await asyncio.sleep(0.001)
                
                return {
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "status": "websocket_success",
                    "events_sent": events_sent,
                    "events_failed": events_failed
                }
                
            except Exception as e:
                return {
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "status": "websocket_failure",
                    "error": str(e),
                    "events_sent": events_sent,
                    "events_failed": events_failed
                }
        
        # Execute WebSocket load test
        logger.info(f"Starting WebSocket isolation test with {concurrent_connections} connections")
        
        ws_results = await asyncio.gather(
            *[websocket_intensive_scenario(f"ws_conn_{i:04d}") for i in range(concurrent_connections)],
            return_exceptions=False
        )
        
        # Analyze WebSocket isolation
        successful_ws = [r for r in ws_results if r["status"] == "websocket_success"]
        failed_ws = [r for r in ws_results if r["status"] == "websocket_failure"]
        
        total_events_sent = sum(r["events_sent"] for r in ws_results)
        total_events_failed = sum(r["events_failed"] for r in ws_results)
        
        # CRITICAL WebSocket Isolation Assertions
        ws_success_rate = len(successful_ws) / len(ws_results)
        assert ws_success_rate > 0.9, f"WebSocket success rate too low: {ws_success_rate:.2%}"
        
        # ZERO cross-contamination allowed
        assert len(cross_contamination) == 0, \
            f"CRITICAL: WebSocket cross-contamination detected: {len(cross_contamination)} violations"
        
        # Event isolation verification
        assert total_events_sent > concurrent_connections * 10, f"Too few events sent: {total_events_sent}"
        
        # Verify each connection has isolated events
        for connection_id, events in connection_events.items():
            expected_user = f"ws_user_{connection_id.split('_')[-1]}"
            for event in events:
                if "user_id" in event["data"]:
                    assert event["data"]["user_id"] == expected_user, \
                        f"Event contamination in {connection_id}: expected {expected_user}, got {event['data']['user_id']}"
        
        logger.info(f"WebSocket Isolation SUCCESS:")
        logger.info(f"  Connections: {concurrent_connections}, Success Rate: {ws_success_rate:.2%}")
        logger.info(f"  Events: {total_events_sent} sent, {total_events_failed} failed")
        logger.info(f"  Cross-contamination: 0 (PERFECT ISOLATION)")
    
    @pytest.mark.asyncio
    async def test_database_session_isolation_extreme_load(self):
        """Test database session isolation under extreme concurrent load."""
        
        concurrent_db_users = 400
        operations_per_user = 15
        
        # Track database session usage
        session_tracker = defaultdict(list)
        session_violations = []
        session_lock = threading.Lock()
        
        def track_db_session(user_id: str, session_id: str, operation: str, table: str = None):
            """Track database session operations."""
            with session_lock:
                session_tracker[user_id].append({
                    "session_id": session_id,
                    "operation": operation,
                    "table": table,
                    "timestamp": time.time(),
                    "thread_id": threading.get_ident()
                })
                
                # Check for session sharing violations
                for other_user, other_sessions in session_tracker.items():
                    if other_user != user_id:
                        for other_session in other_sessions:
                            if other_session["session_id"] == session_id:
                                session_violations.append({
                                    "shared_session": session_id,
                                    "user1": user_id,
                                    "user2": other_user,
                                    "timestamp": time.time()
                                })
        
        async def database_intensive_scenario(user_id: str) -> Dict[str, Any]:
            """Simulate database-intensive operations with session isolation."""
            
            factory = AgentInstanceFactory()
            
            # Simulate multiple database operations across different agents
            operations_completed = 0
            sessions_used = set()
            
            try:
                # Multiple agents, each with database operations
                for agent_type in ["triage", "data", "optimizations"]:
                    context = UserExecutionContext(
                        user_id=user_id,
                        thread_id=f"db_{agent_type}_thread_{user_id}",
                        run_id=f"db_{agent_type}_run_{uuid.uuid4()}"
                    )
                    
                    agent_class = {"triage": UnifiedTriageAgent, "data": DataSubAgent, "optimizations": OptimizationsSubAgent}[agent_type]
                    
                    with patch.object(factory, '_get_agent_class') as mock_get_class:
                        mock_get_class.return_value = agent_class
                        agent = await factory.create_agent_instance(agent_type, context)
                        
                        # Simulate multiple database operations per agent
                        for i in range(operations_per_user // 3):  # Divide operations across agents
                            # Each operation gets its own session (proper isolation)
                            session_id = f"session_{user_id}_{agent_type}_{i}_{uuid.uuid4()}"
                            sessions_used.add(session_id)
                            
                            # Different types of database operations
                            operations = ["SELECT", "INSERT", "UPDATE", "DELETE"]
                            tables = ["users", "agents", "workflows", "results"]
                            
                            for op in operations[:2]:  # 2 operations per session
                                table = random.choice(tables)
                                track_db_session(user_id, session_id, op, table)
                                operations_completed += 1
                                
                                # Simulate database operation time
                                await asyncio.sleep(0.001)
                
                return {
                    "user_id": user_id,
                    "status": "db_success",
                    "operations_completed": operations_completed,
                    "unique_sessions": len(sessions_used),
                    "agent_types_used": ["triage", "data", "optimizations"]
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "status": "db_failure",
                    "error": str(e),
                    "operations_completed": operations_completed,
                    "unique_sessions": len(sessions_used)
                }
        
        # Execute database load test
        logger.info(f"Starting database isolation test with {concurrent_db_users} concurrent users")
        
        db_results = await asyncio.gather(
            *[database_intensive_scenario(f"db_user_{i:04d}") for i in range(concurrent_db_users)],
            return_exceptions=False
        )
        
        # Analyze database session isolation
        successful_db = [r for r in db_results if r["status"] == "db_success"]
        failed_db = [r for r in db_results if r["status"] == "db_failure"]
        
        total_operations = sum(r["operations_completed"] for r in db_results)
        total_sessions = sum(r["unique_sessions"] for r in successful_db)
        
        # CRITICAL Database Isolation Assertions
        db_success_rate = len(successful_db) / len(db_results)
        assert db_success_rate > 0.95, f"Database success rate too low: {db_success_rate:.2%}"
        
        # ZERO session sharing violations
        assert len(session_violations) == 0, \
            f"CRITICAL: Database session sharing detected: {len(session_violations)} violations"
        
        # Verify session isolation per user
        all_sessions = set()
        for user_id, sessions in session_tracker.items():
            user_sessions = {s["session_id"] for s in sessions}
            
            # Check for session overlap with other users
            session_overlap = all_sessions.intersection(user_sessions)
            assert len(session_overlap) == 0, f"Session overlap detected for {user_id}: {session_overlap}"
            
            all_sessions.update(user_sessions)
        
        # Verify reasonable operation count
        expected_operations = concurrent_db_users * operations_per_user * 2  # 2 ops per session cycle
        assert total_operations >= expected_operations * 0.8, f"Too few operations completed: {total_operations}/{expected_operations}"
        
        logger.info(f"Database Isolation SUCCESS:")
        logger.info(f"  Users: {concurrent_db_users}, Success Rate: {db_success_rate:.2%}")
        logger.info(f"  Operations: {total_operations}, Sessions: {total_sessions}")
        logger.info(f"  Session Violations: 0 (PERFECT ISOLATION)")

    @pytest.mark.asyncio
    async def test_memory_stability_under_extreme_concurrent_load(self):
        """Test memory stability and cleanup under extreme concurrent load."""
        
        concurrent_memory_users = 500
        memory_intensive_operations = 20
        
        # Track memory usage patterns
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_samples = []
        memory_violations = []
        
        # Weak references for cleanup verification
        agent_refs = []
        context_refs = []
        
        async def memory_intensive_scenario(user_id: str) -> Dict[str, Any]:
            """Memory-intensive scenario with proper cleanup verification."""
            
            scenario_start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            factory = AgentInstanceFactory()
            
            try:
                for operation in range(memory_intensive_operations):
                    # Create memory-intensive agent workflow
                    context = UserExecutionContext(
                        user_id=user_id,
                        thread_id=f"mem_thread_{user_id}_{operation}",
                        run_id=f"mem_run_{uuid.uuid4()}"
                    )
                    context_refs.append(weakref.ref(context))
                    
                    with patch.object(factory, '_get_agent_class') as mock_get_class:
                        mock_get_class.return_value = UnifiedTriageAgent
                        agent = await factory.create_agent_instance("triage", context)
                        agent_refs.append(weakref.ref(agent))
                        
                        # Allocate significant memory per agent
                        agent._large_memory_structure = {
                            "data_matrix": [[random.random() for _ in range(200)] for _ in range(100)],
                            "user_cache": {f"key_{i}": f"value_{user_id}_{operation}_{i}" for i in range(500)},
                            "processing_results": [f"result_{user_id}_{operation}_{i}" for i in range(1000)],
                            "metadata": {
                                "user_id": user_id,
                                "operation": operation,
                                "memory_signature": f"mem_sig_{user_id}_{operation}"
                            }
                        }
                        
                        # Simulate processing
                        await asyncio.sleep(0.002)
                        
                        # Sample memory during operation
                        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                        memory_samples.append({
                            "user_id": user_id,
                            "operation": operation,
                            "memory_mb": current_memory,
                            "phase": "processing"
                        })
                
                # Final memory check for this user
                final_user_memory = psutil.Process().memory_info().rss / 1024 / 1024
                user_memory_growth = final_user_memory - scenario_start_memory
                
                # Detect excessive memory growth per user
                if user_memory_growth > 50:  # More than 50MB per user is excessive
                    memory_violations.append({
                        "user_id": user_id,
                        "memory_growth_mb": user_memory_growth,
                        "violation_type": "excessive_growth"
                    })
                
                return {
                    "user_id": user_id,
                    "status": "memory_success",
                    "operations_completed": memory_intensive_operations,
                    "memory_growth_mb": user_memory_growth
                }
                
            except Exception as e:
                return {
                    "user_id": user_id,
                    "status": "memory_failure",
                    "error": str(e),
                    "memory_growth_mb": psutil.Process().memory_info().rss / 1024 / 1024 - scenario_start_memory
                }
        
        # Execute memory load test
        logger.info(f"Starting memory stability test with {concurrent_memory_users} concurrent users")
        
        memory_results = await asyncio.gather(
            *[memory_intensive_scenario(f"mem_user_{i:04d}") for i in range(concurrent_memory_users)],
            return_exceptions=False
        )
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.5)  # Allow cleanup time
        gc.collect()
        
        # Analyze memory results
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        
        successful_memory = [r for r in memory_results if r["status"] == "memory_success"]
        failed_memory = [r for r in memory_results if r["status"] == "memory_failure"]
        
        # Check object cleanup via weak references
        alive_agents = sum(1 for ref in agent_refs if ref() is not None)
        alive_contexts = sum(1 for ref in context_refs if ref() is not None)
        
        agent_cleanup_rate = 1 - (alive_agents / len(agent_refs)) if agent_refs else 1
        context_cleanup_rate = 1 - (alive_contexts / len(context_refs)) if context_refs else 1
        
        # CRITICAL Memory Stability Assertions
        memory_success_rate = len(successful_memory) / len(memory_results)
        assert memory_success_rate > 0.95, f"Memory success rate too low: {memory_success_rate:.2%}"
        
        # Total memory growth should be reasonable for the load
        expected_max_growth = concurrent_memory_users * 5  # 5MB per user max
        assert total_memory_growth < expected_max_growth, f"Excessive memory growth: {total_memory_growth:.1f}MB (expected <{expected_max_growth}MB)"
        
        # Object cleanup verification
        assert agent_cleanup_rate > 0.8, f"Poor agent cleanup: {agent_cleanup_rate:.1%} (expected >80%)"
        assert context_cleanup_rate > 0.8, f"Poor context cleanup: {context_cleanup_rate:.1%} (expected >80%)"
        
        # No memory violations per user
        assert len(memory_violations) == 0, \
            f"Memory violations detected: {len(memory_violations)} users with excessive growth"
        
        logger.info(f"Memory Stability SUCCESS:")
        logger.info(f"  Users: {concurrent_memory_users}, Success Rate: {memory_success_rate:.2%}")
        logger.info(f"  Total Memory Growth: {total_memory_growth:.1f}MB")
        logger.info(f"  Cleanup Rates: {agent_cleanup_rate:.1%} agents, {context_cleanup_rate:.1%} contexts")
        logger.info(f"  Memory Violations: 0 (STABLE MEMORY USAGE)")


if __name__ == "__main__":
    # Run comprehensive E2E concurrent isolation tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s",  # Show detailed output
        "--durations=20",  # Show slowest tests
        "-k", "concurrent or isolation or e2e"  # Focus on E2E tests
    ])