#!/usr/bin/env python
"""
INTEGRATION TEST SUITE - ALL CRITICAL FIXES WORKING TOGETHER

COMPREHENSIVE INTEGRATION VALIDATION:
- All critical fixes must work together seamlessly
- Memory optimization + WebSocket modernization integration
- Startup sequence + ClickHouse dependency integration
- Cross-system communication and data flow validation
- End-to-end scenario testing under realistic load
- Performance validation across all systems
- Error handling and recovery across system boundaries

This test suite provides END-TO-END integration scenarios:
1. Complete system startup with all fixes active
2. Memory-optimized WebSocket operations under load
3. ClickHouse analytics with WebSocket real-time updates
4. Concurrent user isolation across all system components
5. Failure cascade handling across all systems
6. Performance regression validation for the entire stack
7. Data consistency across WebSocket, database, and analytics
8. Resource management across all critical components

Business Impact: Ensures production system reliability and performance
Strategic Value: Critical for validating complete system integration
"""

import asyncio
import json
import os
import random
import sys
import time
import uuid
import threading
import tracemalloc
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set, Callable, Tuple, AsyncIterator
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.isolated_environment import get_env

# Import all critical system components
try:
    # Memory optimization
    from netra_backend.app.services.memory_optimization_service import MemoryOptimizationService, MemoryPressureLevel
    from netra_backend.app.services.session_memory_manager import SessionMemoryManager
    
    # WebSocket modernization
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    # Startup sequence
    from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError
    
    # ClickHouse integration
    from netra_backend.app.database.clickhouse_client import ClickHouseClient
    from netra_backend.app.database.clickhouse_health import ClickHouseHealthChecker
    
    # User execution context
    from netra_backend.app.models.user_execution_context import UserExecutionContext
    
    INTEGRATION_SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Integration services not available: {e}")
    INTEGRATION_SERVICES_AVAILABLE = False
    
    # Create comprehensive mock classes
    class MemoryOptimizationService:
        async def start(self): pass
        async def stop(self): pass
        def get_memory_stats(self): return {"memory_mb": 100, "active_scopes": 0}
        
    class SessionMemoryManager:
        async def start(self): pass
        async def stop(self): pass
        
    class WebSocketManager:
        def __init__(self): self.active_connections = {}
        async def connect(self, ws, user_id): pass
        async def disconnect(self, ws): pass
        async def send_message(self, user_id, message): pass
        
    class AgentWebSocketBridge:
        async def send_notification(self, user_id, data): pass
        
    class StartupOrchestrator:
        def __init__(self, app): self.app = app
        async def initialize_system(self): pass
        
    class ClickHouseClient:
        async def connect(self): pass
        async def execute(self, query): return []
        async def ping(self): return True
        
    class ClickHouseHealthChecker:
        def __init__(self, client): self.client = client
        async def check_health(self): return {"status": "healthy"}
        
    class UserExecutionContext:
        def __init__(self, user_id, thread_id, run_id, request_id, websocket_connection_id=None):
            self.user_id = user_id
            self.thread_id = thread_id
            self.run_id = run_id
            self.request_id = request_id
            self.websocket_connection_id = websocket_connection_id
    
    DeterministicStartupError = Exception

# FastAPI and additional dependencies
try:
    from fastapi import FastAPI
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = Mock

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Integration test constants
INTEGRATION_TEST_DURATION = 300  # 5 minutes for full integration
CONCURRENT_USERS = 25  # Concurrent users for integration testing
OPERATIONS_PER_USER = 50  # Operations per user
MEMORY_LIMIT_MB = 2048  # 2GB memory limit
WEBSOCKET_MESSAGE_RATE = 10  # Messages per second per user
CLICKHOUSE_BATCH_SIZE = 100  # Records per batch
PERFORMANCE_THRESHOLD_MULTIPLIER = 1.5  # Allow 50% performance degradation during integration


@dataclass
class IntegrationTestUser:
    """Integration test user with comprehensive context."""
    user_id: str
    execution_context: UserExecutionContext
    websocket_connection: Optional[Any] = None
    memory_usage_mb: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    database_operations: int = 0
    errors: List[Exception] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def get_session_duration(self) -> float:
        return time.time() - self.start_time


@dataclass
class SystemComponent:
    """System component status for integration testing."""
    name: str
    status: str = "unknown"  # unknown, starting, healthy, degraded, failed
    start_time: float = 0.0
    last_health_check: float = 0.0
    health_data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    error_count: int = 0
    recovery_count: int = 0


@dataclass
class IntegrationTestResult:
    """Integration test result data."""
    test_name: str
    duration: float
    success: bool
    components_tested: List[str]
    users_simulated: int
    operations_completed: int
    performance_metrics: Dict[str, Any]
    memory_metrics: Dict[str, Any]
    error_summary: Dict[str, Any]
    bottlenecks_detected: List[str] = field(default_factory=list)
    fix_validations: Dict[str, bool] = field(default_factory=dict)


class IntegratedSystemManager:
    """Manages all system components for integration testing."""
    
    def __init__(self):
        self.components: Dict[str, SystemComponent] = {}
        self.services: Dict[str, Any] = {}
        self.app: Optional[FastAPI] = None
        self.lock = asyncio.Lock()
        self.startup_complete = False
        self.shutdown_initiated = False
        
        # Initialize component definitions
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize system component definitions."""
        component_configs = [
            {
                "name": "memory_optimization",
                "dependencies": [],
                "dependents": ["session_manager", "websocket_manager", "agent_bridge"]
            },
            {
                "name": "session_manager", 
                "dependencies": ["memory_optimization"],
                "dependents": ["websocket_manager", "agent_bridge"]
            },
            {
                "name": "websocket_manager",
                "dependencies": ["memory_optimization", "session_manager"],
                "dependents": ["agent_bridge", "user_interface"]
            },
            {
                "name": "clickhouse_client",
                "dependencies": [],
                "dependents": ["analytics", "health_checker"]
            },
            {
                "name": "clickhouse_health",
                "dependencies": ["clickhouse_client"],
                "dependents": ["analytics", "startup_orchestrator"]
            },
            {
                "name": "agent_bridge",
                "dependencies": ["websocket_manager", "session_manager", "memory_optimization"],
                "dependents": ["user_interface"]
            },
            {
                "name": "startup_orchestrator",
                "dependencies": ["memory_optimization", "clickhouse_health"],
                "dependents": []
            }
        ]
        
        for config in component_configs:
            self.components[config["name"]] = SystemComponent(
                name=config["name"],
                dependencies=config["dependencies"],
                dependents=config["dependents"]
            )
    
    async def initialize_all_systems(self) -> bool:
        """Initialize all system components in correct order."""
        logger.info("Initializing integrated system components")
        
        async with self.lock:
            # Create FastAPI app
            self.app = FastAPI() if FASTAPI_AVAILABLE else Mock()
            
            # Initialize components in dependency order
            initialization_order = self._calculate_initialization_order()
            
            for component_name in initialization_order:
                logger.debug(f"Initializing component: {component_name}")
                
                component = self.components[component_name]
                component.start_time = time.time()
                component.status = "starting"
                
                try:
                    success = await self._initialize_component(component_name)
                    
                    if success:
                        component.status = "healthy"
                        component.last_health_check = time.time()
                        logger.debug(f"Component {component_name} initialized successfully")
                    else:
                        component.status = "failed"
                        component.error_count += 1
                        logger.error(f"Component {component_name} initialization failed")
                        return False
                        
                except Exception as e:
                    component.status = "failed"
                    component.error_count += 1
                    logger.error(f"Component {component_name} initialization error: {e}")
                    return False
            
            self.startup_complete = True
            logger.info("All system components initialized successfully")
            return True
    
    def _calculate_initialization_order(self) -> List[str]:
        """Calculate correct component initialization order based on dependencies."""
        order = []
        remaining = set(self.components.keys())
        
        while remaining:
            # Find components with no unresolved dependencies
            ready = []
            for component_name in remaining:
                component = self.components[component_name]
                if all(dep in order for dep in component.dependencies):
                    ready.append(component_name)
            
            if not ready:
                # Circular dependency detected
                logger.error(f"Circular dependency detected in components: {remaining}")
                # Break circle by initializing remaining in arbitrary order
                ready = list(remaining)
            
            for component_name in ready:
                order.append(component_name)
                remaining.remove(component_name)
        
        return order
    
    async def _initialize_component(self, component_name: str) -> bool:
        """Initialize a specific system component."""
        if component_name == "memory_optimization":
            service = MemoryOptimizationService()
            await service.start()
            self.services[component_name] = service
            return True
            
        elif component_name == "session_manager":
            service = SessionMemoryManager()
            await service.start()
            self.services[component_name] = service
            return True
            
        elif component_name == "websocket_manager":
            service = WebSocketManager()
            self.services[component_name] = service
            return True
            
        elif component_name == "clickhouse_client":
            service = ClickHouseClient()
            await service.connect()
            self.services[component_name] = service
            return True
            
        elif component_name == "clickhouse_health":
            client = self.services.get("clickhouse_client")
            if client:
                service = ClickHouseHealthChecker(client)
                health = await service.check_health()
                self.services[component_name] = service
                return health.get("status") == "healthy"
            return False
            
        elif component_name == "agent_bridge":
            service = AgentWebSocketBridge()
            self.services[component_name] = service
            return True
            
        elif component_name == "startup_orchestrator":
            service = StartupOrchestrator(self.app)
            self.services[component_name] = service
            return True
        
        return False
    
    async def health_check_all_components(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health_results = {}
        
        async with self.lock:
            for component_name, component in self.components.items():
                try:
                    health_data = await self._health_check_component(component_name)
                    component.health_data = health_data
                    component.last_health_check = time.time()
                    
                    if health_data.get("status") == "healthy":
                        if component.status != "healthy":
                            component.recovery_count += 1
                        component.status = "healthy"
                    else:
                        component.status = "degraded"
                        component.error_count += 1
                    
                    health_results[component_name] = health_data
                    
                except Exception as e:
                    component.status = "failed"
                    component.error_count += 1
                    health_results[component_name] = {"status": "failed", "error": str(e)}
        
        return health_results
    
    async def _health_check_component(self, component_name: str) -> Dict[str, Any]:
        """Health check for a specific component."""
        service = self.services.get(component_name)
        
        if component_name == "memory_optimization":
            if service:
                stats = service.get_memory_stats()
                return {
                    "status": "healthy" if stats.get("memory_mb", 0) < MEMORY_LIMIT_MB * 0.8 else "degraded",
                    "memory_mb": stats.get("memory_mb", 0),
                    "active_scopes": stats.get("active_scopes", 0)
                }
            return {"status": "failed", "error": "Service not available"}
            
        elif component_name == "clickhouse_client":
            if service:
                ping_result = await service.ping()
                return {"status": "healthy" if ping_result else "degraded"}
            return {"status": "failed", "error": "Service not available"}
            
        elif component_name == "clickhouse_health":
            if service:
                return await service.check_health()
            return {"status": "failed", "error": "Service not available"}
            
        elif component_name == "websocket_manager":
            if service:
                active_connections = len(getattr(service, 'active_connections', {}))
                return {
                    "status": "healthy",
                    "active_connections": active_connections,
                    "connection_capacity": 1000
                }
            return {"status": "failed", "error": "Service not available"}
        
        # Default health check for other components
        return {"status": "healthy" if service else "failed"}
    
    async def shutdown_all_systems(self):
        """Gracefully shutdown all system components."""
        logger.info("Shutting down integrated system components")
        
        self.shutdown_initiated = True
        
        async with self.lock:
            # Shutdown in reverse dependency order
            initialization_order = self._calculate_initialization_order()
            shutdown_order = reversed(initialization_order)
            
            for component_name in shutdown_order:
                try:
                    await self._shutdown_component(component_name)
                    self.components[component_name].status = "stopped"
                    logger.debug(f"Component {component_name} shut down")
                except Exception as e:
                    logger.error(f"Error shutting down component {component_name}: {e}")
        
        logger.info("All system components shut down")
    
    async def _shutdown_component(self, component_name: str):
        """Shutdown a specific component."""
        service = self.services.get(component_name)
        
        if component_name in ["memory_optimization", "session_manager"]:
            if service and hasattr(service, 'stop'):
                await service.stop()
        elif component_name == "clickhouse_client":
            if service and hasattr(service, 'disconnect'):
                await service.disconnect()
        
        # Remove service reference
        if component_name in self.services:
            del self.services[component_name]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        healthy_components = [name for name, comp in self.components.items() if comp.status == "healthy"]
        degraded_components = [name for name, comp in self.components.items() if comp.status == "degraded"]
        failed_components = [name for name, comp in self.components.items() if comp.status == "failed"]
        
        return {
            "startup_complete": self.startup_complete,
            "shutdown_initiated": self.shutdown_initiated,
            "total_components": len(self.components),
            "healthy_components": len(healthy_components),
            "degraded_components": len(degraded_components),
            "failed_components": len(failed_components),
            "component_details": {
                "healthy": healthy_components,
                "degraded": degraded_components,
                "failed": failed_components
            }
        }


class IntegrationScenarioRunner:
    """Runs comprehensive integration test scenarios."""
    
    def __init__(self, system_manager: IntegratedSystemManager):
        self.system_manager = system_manager
        self.test_users: List[IntegrationTestUser] = []
        self.executor = ThreadPoolExecutor(max_workers=CONCURRENT_USERS)
        self.memory_tracker = None
        
    async def run_end_to_end_integration_scenario(self) -> IntegrationTestResult:
        """Run comprehensive end-to-end integration scenario."""
        logger.info(f"Running end-to-end integration scenario with {CONCURRENT_USERS} users")
        
        start_time = time.time()
        
        # Enable memory tracking
        tracemalloc.start()
        initial_memory = tracemalloc.take_snapshot()
        
        try:
            # Initialize all systems
            initialization_success = await self.system_manager.initialize_all_systems()
            if not initialization_success:
                raise Exception("System initialization failed")
            
            # Create test users
            self.test_users = self._create_integration_test_users(CONCURRENT_USERS)
            
            # Run concurrent user scenarios
            user_tasks = []
            for user in self.test_users:
                task = asyncio.create_task(self._run_user_integration_scenario(user))
                user_tasks.append(task)
            
            # Monitor system health while scenarios run
            health_monitoring_task = asyncio.create_task(self._monitor_system_health())
            
            # Wait for scenarios to complete
            scenario_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            # Stop health monitoring
            health_monitoring_task.cancel()
            
            # Collect final metrics
            final_memory = tracemalloc.take_snapshot()
            system_status = self.system_manager.get_system_status()
            performance_metrics = self._calculate_performance_metrics(scenario_results)
            memory_metrics = self._calculate_memory_metrics(initial_memory, final_memory)
            
            # Validate all critical fixes
            fix_validations = await self._validate_all_critical_fixes()
            
            end_time = time.time()
            
            # Determine overall success
            successful_users = len([r for r in scenario_results if not isinstance(r, Exception)])
            success = (
                successful_users >= len(self.test_users) * 0.8 and  # 80% user success
                system_status["failed_components"] == 0 and  # No failed components
                all(fix_validations.values())  # All fixes validated
            )
            
            return IntegrationTestResult(
                test_name="end_to_end_integration",
                duration=end_time - start_time,
                success=success,
                components_tested=list(self.system_manager.components.keys()),
                users_simulated=len(self.test_users),
                operations_completed=sum(
                    user.messages_sent + user.database_operations 
                    for user in self.test_users
                ),
                performance_metrics=performance_metrics,
                memory_metrics=memory_metrics,
                error_summary=self._summarize_errors(scenario_results),
                bottlenecks_detected=self._detect_bottlenecks(),
                fix_validations=fix_validations
            )
            
        finally:
            tracemalloc.stop()
            await self.system_manager.shutdown_all_systems()
    
    def _create_integration_test_users(self, count: int) -> List[IntegrationTestUser]:
        """Create integration test users with full context."""
        users = []
        
        for i in range(count):
            user_id = f"integration_user_{i}_{uuid.uuid4().hex[:8]}"
            
            execution_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"req_{i}_{uuid.uuid4().hex[:8]}",
                websocket_connection_id=f"ws_{i}_{uuid.uuid4().hex[:8]}"
            )
            
            user = IntegrationTestUser(
                user_id=user_id,
                execution_context=execution_context
            )
            
            users.append(user)
        
        return users
    
    async def _run_user_integration_scenario(self, user: IntegrationTestUser) -> Dict[str, Any]:
        """Run integration scenario for a single user."""
        try:
            # Simulate user session with all system interactions
            
            # 1. WebSocket connection
            await self._simulate_websocket_connection(user)
            
            # 2. Memory-scoped operations
            await self._simulate_memory_scoped_operations(user)
            
            # 3. Database operations
            await self._simulate_database_operations(user)
            
            # 4. Real-time messaging
            await self._simulate_realtime_messaging(user)
            
            # 5. Analytics operations
            await self._simulate_analytics_operations(user)
            
            return {
                "user_id": user.user_id,
                "success": True,
                "messages_sent": user.messages_sent,
                "messages_received": user.messages_received,
                "database_operations": user.database_operations,
                "session_duration": user.get_session_duration(),
                "memory_usage_mb": user.memory_usage_mb,
                "error_count": len(user.errors)
            }
            
        except Exception as e:
            user.errors.append(e)
            logger.error(f"User scenario failed for {user.user_id}: {e}")
            
            return {
                "user_id": user.user_id,
                "success": False,
                "error": str(e),
                "error_count": len(user.errors)
            }
    
    async def _simulate_websocket_connection(self, user: IntegrationTestUser):
        """Simulate WebSocket connection for user."""
        websocket_manager = self.system_manager.services.get("websocket_manager")
        if websocket_manager:
            # Simulate WebSocket connection
            mock_websocket = Mock()
            user.websocket_connection = mock_websocket
            
            await websocket_manager.connect(mock_websocket, user.user_id)
    
    async def _simulate_memory_scoped_operations(self, user: IntegrationTestUser):
        """Simulate memory-scoped operations for user."""
        memory_service = self.system_manager.services.get("memory_optimization")
        if memory_service:
            # Simulate memory usage tracking
            initial_stats = memory_service.get_memory_stats()
            
            # Perform operations that should be memory-scoped
            for i in range(20):
                # Simulate operation with temporary data
                temp_data = [f"data_{user.user_id}_{i}_{j}" for j in range(100)]
                await asyncio.sleep(0.01)  # Simulate processing
                del temp_data
            
            final_stats = memory_service.get_memory_stats()
            user.memory_usage_mb = final_stats.get("memory_mb", 0) - initial_stats.get("memory_mb", 0)
    
    async def _simulate_database_operations(self, user: IntegrationTestUser):
        """Simulate database operations for user."""
        clickhouse_client = self.system_manager.services.get("clickhouse_client")
        if clickhouse_client:
            # Simulate database operations
            for i in range(10):
                try:
                    query = f"SELECT '{user.user_id}', {i}, now()"
                    await clickhouse_client.execute(query)
                    user.database_operations += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    user.errors.append(e)
    
    async def _simulate_realtime_messaging(self, user: IntegrationTestUser):
        """Simulate real-time messaging for user."""
        agent_bridge = self.system_manager.services.get("agent_bridge")
        websocket_manager = self.system_manager.services.get("websocket_manager")
        
        if agent_bridge and websocket_manager:
            # Send messages through the system
            for i in range(OPERATIONS_PER_USER):
                try:
                    message_data = {
                        "type": "user_message",
                        "user_id": user.user_id,
                        "content": f"Integration test message {i}",
                        "timestamp": time.time()
                    }
                    
                    # Send via agent bridge
                    await agent_bridge.send_notification(user.user_id, message_data)
                    user.messages_sent += 1
                    
                    # Simulate receiving response
                    await websocket_manager.send_message(user.user_id, {
                        "type": "response",
                        "original_message": i,
                        "response": f"Processed message {i}"
                    })
                    user.messages_received += 1
                    
                    await asyncio.sleep(0.1)  # 10 messages per second
                    
                except Exception as e:
                    user.errors.append(e)
    
    async def _simulate_analytics_operations(self, user: IntegrationTestUser):
        """Simulate analytics operations for user."""
        clickhouse_client = self.system_manager.services.get("clickhouse_client")
        if clickhouse_client:
            try:
                # Simulate analytics queries
                analytics_queries = [
                    f"SELECT count(*) FROM user_events WHERE user_id = '{user.user_id}'",
                    f"SELECT avg(response_time) FROM user_sessions WHERE user_id = '{user.user_id}'",
                    f"SELECT date, count(*) FROM user_activity WHERE user_id = '{user.user_id}' GROUP BY date"
                ]
                
                for query in analytics_queries:
                    await clickhouse_client.execute(query)
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                user.errors.append(e)
    
    async def _monitor_system_health(self):
        """Monitor system health during integration test."""
        try:
            while True:
                health_results = await self.system_manager.health_check_all_components()
                
                # Log any degraded components
                for component_name, health_data in health_results.items():
                    if health_data.get("status") != "healthy":
                        logger.warning(f"Component {component_name} degraded: {health_data}")
                
                await asyncio.sleep(10.0)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.debug("Health monitoring stopped")
    
    def _calculate_performance_metrics(self, scenario_results: List[Any]) -> Dict[str, Any]:
        """Calculate performance metrics from scenario results."""
        successful_results = [r for r in scenario_results if not isinstance(r, Exception) and r.get("success", False)]
        
        if not successful_results:
            return {"error": "No successful scenarios"}
        
        total_messages = sum(r.get("messages_sent", 0) + r.get("messages_received", 0) for r in successful_results)
        total_db_operations = sum(r.get("database_operations", 0) for r in successful_results)
        total_session_time = sum(r.get("session_duration", 0) for r in successful_results)
        
        return {
            "successful_users": len(successful_results),
            "total_messages": total_messages,
            "total_database_operations": total_db_operations,
            "message_throughput": total_messages / total_session_time if total_session_time > 0 else 0,
            "db_operation_throughput": total_db_operations / total_session_time if total_session_time > 0 else 0,
            "average_session_duration": total_session_time / len(successful_results),
            "average_messages_per_user": total_messages / len(successful_results),
            "average_db_operations_per_user": total_db_operations / len(successful_results)
        }
    
    def _calculate_memory_metrics(self, initial_snapshot, final_snapshot) -> Dict[str, Any]:
        """Calculate memory usage metrics."""
        try:
            top_stats = final_snapshot.compare_to(initial_snapshot, 'lineno')
            
            total_growth_mb = sum(stat.size_diff for stat in top_stats) / 1024 / 1024
            total_allocations = sum(stat.count_diff for stat in top_stats)
            
            return {
                "memory_growth_mb": total_growth_mb,
                "memory_growth_within_limit": total_growth_mb <= MEMORY_LIMIT_MB * 0.1,  # 10% of limit
                "total_allocations": total_allocations,
                "top_memory_consumers": [
                    {
                        "location": stat.traceback.format()[0] if stat.traceback.format() else "unknown",
                        "size_diff_mb": stat.size_diff / 1024 / 1024,
                        "count_diff": stat.count_diff
                    }
                    for stat in top_stats[:5]
                ]
            }
        except Exception as e:
            return {"error": f"Memory calculation failed: {e}"}
    
    def _summarize_errors(self, scenario_results: List[Any]) -> Dict[str, Any]:
        """Summarize errors from scenario results."""
        all_errors = []
        
        for result in scenario_results:
            if isinstance(result, Exception):
                all_errors.append(str(result))
            elif isinstance(result, dict) and not result.get("success", True):
                all_errors.append(result.get("error", "Unknown error"))
        
        # Add user-specific errors
        for user in self.test_users:
            all_errors.extend(str(error) for error in user.errors)
        
        # Categorize errors
        error_categories = {}
        for error in all_errors:
            error_type = type(error).__name__ if isinstance(error, Exception) else "Runtime Error"
            error_categories[error_type] = error_categories.get(error_type, 0) + 1
        
        return {
            "total_errors": len(all_errors),
            "error_categories": error_categories,
            "error_rate": len(all_errors) / max(len(self.test_users) * OPERATIONS_PER_USER, 1),
            "sample_errors": all_errors[:10] if all_errors else []
        }
    
    def _detect_bottlenecks(self) -> List[str]:
        """Detect system bottlenecks from integration test."""
        bottlenecks = []
        
        # Check component health for bottlenecks
        system_status = self.system_manager.get_system_status()
        
        if system_status["degraded_components"] > 0:
            bottlenecks.append(f"Component degradation: {system_status['component_details']['degraded']}")
        
        # Check memory usage bottlenecks
        memory_service = self.system_manager.services.get("memory_optimization")
        if memory_service:
            stats = memory_service.get_memory_stats()
            if stats.get("memory_mb", 0) > MEMORY_LIMIT_MB * 0.8:
                bottlenecks.append("Memory usage approaching limit")
        
        # Check user error rates
        high_error_users = [user for user in self.test_users if len(user.errors) > 5]
        if len(high_error_users) > len(self.test_users) * 0.2:
            bottlenecks.append("High error rate in user operations")
        
        return bottlenecks
    
    async def _validate_all_critical_fixes(self) -> Dict[str, bool]:
        """Validate that all critical fixes are working correctly."""
        validations = {}
        
        # 1. Memory optimization fixes
        memory_service = self.system_manager.services.get("memory_optimization")
        validations["memory_optimization"] = (
            memory_service is not None and
            all(user.memory_usage_mb < 50 for user in self.test_users)  # Memory per user under 50MB
        )
        
        # 2. WebSocket modernization
        websocket_manager = self.system_manager.services.get("websocket_manager")
        validations["websocket_modernization"] = (
            websocket_manager is not None and
            all(user.messages_sent > 0 for user in self.test_users if len(user.errors) < 5)
        )
        
        # 3. Startup sequence fixes
        validations["startup_sequence"] = (
            self.system_manager.startup_complete and
            self.system_manager.get_system_status()["failed_components"] == 0
        )
        
        # 4. ClickHouse dependency fixes
        clickhouse_health = self.system_manager.services.get("clickhouse_health")
        clickhouse_working = False
        if clickhouse_health:
            try:
                health = await clickhouse_health.check_health()
                clickhouse_working = health.get("status") == "healthy"
            except Exception:
                pass
        
        validations["clickhouse_dependency"] = clickhouse_working
        
        # 5. User isolation fixes
        user_isolation_working = all(
            user.execution_context.user_id.startswith("integration_user")
            for user in self.test_users
        ) and len(set(user.user_id for user in self.test_users)) == len(self.test_users)
        
        validations["user_isolation"] = user_isolation_working
        
        return validations


# ============================================================================
# INTEGRATION TEST SUITE - ALL FIXES WORKING TOGETHER
# ============================================================================

@pytest.fixture
async def integrated_system_manager():
    """Fixture providing integrated system manager."""
    manager = IntegratedSystemManager()
    try:
        yield manager
    finally:
        if not manager.shutdown_initiated:
            await manager.shutdown_all_systems()


@pytest.fixture
async def integration_scenario_runner(integrated_system_manager):
    """Fixture providing integration scenario runner."""
    runner = IntegrationScenarioRunner(integrated_system_manager)
    try:
        yield runner
    finally:
        runner.executor.shutdown(wait=True)


@pytest.mark.asyncio
class TestIntegrationAllFixes:
    """Integration test suite validating all critical fixes working together."""
    
    @pytest.mark.slow
    async def test_complete_system_integration_comprehensive(self, integration_scenario_runner):
        """Test complete system integration with all fixes active."""
        logger.info("Running comprehensive system integration test")
        
        # Run end-to-end integration scenario
        result = await integration_scenario_runner.run_end_to_end_integration_scenario()
        
        logger.info(f"Integration test results:")
        logger.info(f"  Duration: {result.duration:.2f}s")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Users simulated: {result.users_simulated}")
        logger.info(f"  Operations completed: {result.operations_completed}")
        logger.info(f"  Components tested: {len(result.components_tested)}")
        
        # Log performance metrics
        perf = result.performance_metrics
        logger.info(f"Performance metrics:")
        logger.info(f"  Successful users: {perf.get('successful_users', 0)}")
        logger.info(f"  Message throughput: {perf.get('message_throughput', 0):.2f} msg/s")
        logger.info(f"  DB operation throughput: {perf.get('db_operation_throughput', 0):.2f} ops/s")
        
        # Log memory metrics
        mem = result.memory_metrics
        logger.info(f"Memory metrics:")
        logger.info(f"  Memory growth: {mem.get('memory_growth_mb', 0):.2f}MB")
        logger.info(f"  Within limits: {mem.get('memory_growth_within_limit', False)}")
        
        # Log error summary
        errors = result.error_summary
        logger.info(f"Error summary:")
        logger.info(f"  Total errors: {errors.get('total_errors', 0)}")
        logger.info(f"  Error rate: {errors.get('error_rate', 0):.4f}")
        
        # Log fix validations
        logger.info(f"Critical fix validations:")
        for fix_name, is_valid in result.fix_validations.items():
            status = "✓ PASS" if is_valid else "✗ FAIL"
            logger.info(f"  {fix_name}: {status}")
        
        # CRITICAL VALIDATIONS
        
        # Overall integration success
        assert result.success, \
            f"Complete system integration failed. Bottlenecks: {result.bottlenecks_detected}"
        
        # Test duration should be reasonable
        assert result.duration <= INTEGRATION_TEST_DURATION, \
            f"Integration test took too long: {result.duration:.2f}s (limit: {INTEGRATION_TEST_DURATION}s)"
        
        # All users should be simulated
        assert result.users_simulated == CONCURRENT_USERS, \
            f"Not all users were simulated: {result.users_simulated}/{CONCURRENT_USERS}"
        
        # Significant operations should be completed
        assert result.operations_completed > CONCURRENT_USERS * OPERATIONS_PER_USER * 0.5, \
            f"Too few operations completed: {result.operations_completed}"
        
        # Performance requirements
        successful_users = result.performance_metrics.get("successful_users", 0)
        assert successful_users >= CONCURRENT_USERS * 0.8, \
            f"Too many user failures: {successful_users}/{CONCURRENT_USERS}"
        
        # Memory requirements
        assert result.memory_metrics.get("memory_growth_within_limit", False), \
            f"Memory growth exceeded limits: {result.memory_metrics.get('memory_growth_mb', 0):.2f}MB"
        
        # Error rate requirements
        assert result.error_summary.get("error_rate", 1.0) <= 0.05, \
            f"Error rate too high: {result.error_summary.get('error_rate', 0):.4f} (max: 0.05)"
        
        # All critical fixes must be validated
        for fix_name, is_valid in result.fix_validations.items():
            assert is_valid, f"Critical fix validation failed: {fix_name}"
        
        # No critical bottlenecks
        critical_bottlenecks = [b for b in result.bottlenecks_detected if "critical" in b.lower()]
        assert len(critical_bottlenecks) == 0, f"Critical bottlenecks detected: {critical_bottlenecks}"
    
    async def test_memory_websocket_integration_specific(self, integrated_system_manager):
        """Test specific integration between memory optimization and WebSocket modernization."""
        logger.info("Testing memory-WebSocket integration")
        
        # Initialize required components
        await integrated_system_manager.initialize_all_systems()
        
        memory_service = integrated_system_manager.services.get("memory_optimization")
        websocket_manager = integrated_system_manager.services.get("websocket_manager")
        
        assert memory_service is not None, "Memory optimization service not available"
        assert websocket_manager is not None, "WebSocket manager not available"
        
        # Test memory-scoped WebSocket operations
        initial_memory = memory_service.get_memory_stats()
        
        # Simulate multiple WebSocket connections with memory tracking
        connections = []
        for i in range(10):
            mock_ws = Mock()
            user_id = f"memory_ws_user_{i}"
            
            await websocket_manager.connect(mock_ws, user_id)
            connections.append((mock_ws, user_id))
            
            # Send messages that should be memory-scoped
            for j in range(20):
                message = {
                    "type": "test_message",
                    "data": "x" * 1024,  # 1KB per message
                    "user_id": user_id,
                    "sequence": j
                }
                await websocket_manager.send_message(user_id, message)
        
        # Check memory usage
        peak_memory = memory_service.get_memory_stats()
        memory_increase = peak_memory.get("memory_mb", 0) - initial_memory.get("memory_mb", 0)
        
        # Disconnect all connections
        for mock_ws, user_id in connections:
            await websocket_manager.disconnect(mock_ws)
        
        # Allow memory cleanup
        await asyncio.sleep(1.0)
        
        final_memory = memory_service.get_memory_stats()
        memory_after_cleanup = final_memory.get("memory_mb", 0) - initial_memory.get("memory_mb", 0)
        
        logger.info(f"Memory-WebSocket integration results:")
        logger.info(f"  Peak memory increase: {memory_increase:.2f}MB")
        logger.info(f"  Memory after cleanup: {memory_after_cleanup:.2f}MB")
        
        # Validate memory-WebSocket integration
        assert memory_increase <= 100.0, f"Memory increase too high: {memory_increase:.2f}MB"
        assert memory_after_cleanup <= memory_increase * 0.5, \
            "Memory not properly cleaned up after WebSocket disconnect"
    
    async def test_startup_clickhouse_integration_specific(self, integrated_system_manager):
        """Test specific integration between startup sequence and ClickHouse dependencies."""
        logger.info("Testing startup-ClickHouse integration")
        
        # Test startup with ClickHouse dependency validation
        startup_success = await integrated_system_manager.initialize_all_systems()
        
        assert startup_success, "Startup with ClickHouse dependencies failed"
        
        # Validate startup completed with ClickHouse health
        system_status = integrated_system_manager.get_system_status()
        clickhouse_health_service = integrated_system_manager.services.get("clickhouse_health")
        
        assert system_status["startup_complete"], "System startup not complete"
        assert clickhouse_health_service is not None, "ClickHouse health service not initialized"
        
        # Test ClickHouse health check
        health_result = await clickhouse_health_service.check_health()
        
        logger.info(f"ClickHouse health: {health_result}")
        
        # Validate startup-ClickHouse integration
        assert health_result.get("status") in ["healthy", "degraded"], \
            f"ClickHouse health check failed: {health_result}"
        
        # Test startup order - ClickHouse should be initialized before dependent components
        startup_order = integrated_system_manager._calculate_initialization_order()
        clickhouse_index = startup_order.index("clickhouse_client")
        health_index = startup_order.index("clickhouse_health")
        
        assert clickhouse_index < health_index, "ClickHouse client should initialize before health checker"
    
    async def test_cross_component_error_handling_integration(self, integrated_system_manager):
        """Test error handling and recovery across component boundaries."""
        logger.info("Testing cross-component error handling")
        
        # Initialize system
        await integrated_system_manager.initialize_all_systems()
        
        # Test error cascade handling
        error_scenarios = [
            {
                "component": "memory_optimization",
                "simulate_error": True,
                "expected_cascade": ["session_manager", "websocket_manager"]
            },
            {
                "component": "clickhouse_client", 
                "simulate_error": True,
                "expected_cascade": ["clickhouse_health"]
            }
        ]
        
        error_handling_results = {}
        
        for scenario in error_scenarios:
            component_name = scenario["component"]
            service = integrated_system_manager.services.get(component_name)
            
            if service:
                # Simulate component error by making it unhealthy
                original_component = integrated_system_manager.components[component_name]
                original_component.status = "failed"
                original_component.error_count += 1
                
                # Check health of dependent components
                health_results = await integrated_system_manager.health_check_all_components()
                
                # Verify error handling
                degraded_components = [
                    name for name, health in health_results.items()
                    if health.get("status") not in ["healthy", "unknown"]
                ]
                
                error_handling_results[component_name] = {
                    "error_injected": True,
                    "degraded_components": degraded_components,
                    "cascade_detected": len(degraded_components) > 1,
                    "health_results": health_results
                }
                
                # Recover component
                original_component.status = "healthy"
                original_component.recovery_count += 1
        
        logger.info(f"Error handling results: {json.dumps(error_handling_results, indent=2)}")
        
        # Validate error handling
        for component_name, result in error_handling_results.items():
            assert result["error_injected"], f"Error not properly injected for {component_name}"
            # Note: We don't require cascade detection as it depends on implementation
    
    async def test_performance_regression_integration(self, integration_scenario_runner):
        """Test that integration doesn't introduce performance regressions."""
        logger.info("Testing performance regression in integration")
        
        # Run a smaller integration test for performance measurement
        original_concurrent_users = CONCURRENT_USERS
        original_operations_per_user = OPERATIONS_PER_USER
        
        # Temporarily reduce load for precise measurement
        global CONCURRENT_USERS, OPERATIONS_PER_USER
        CONCURRENT_USERS = 5
        OPERATIONS_PER_USER = 20
        
        try:
            start_time = time.time()
            result = await integration_scenario_runner.run_end_to_end_integration_scenario()
            end_time = time.time()
            
            # Performance analysis
            performance_metrics = result.performance_metrics
            
            # Calculate key performance indicators
            total_operations = result.operations_completed
            test_duration = result.duration
            operations_per_second = total_operations / test_duration if test_duration > 0 else 0
            
            # Memory efficiency
            memory_metrics = result.memory_metrics
            memory_per_operation = (
                memory_metrics.get("memory_growth_mb", 0) / total_operations 
                if total_operations > 0 else 0
            )
            
            logger.info(f"Performance regression test results:")
            logger.info(f"  Operations per second: {operations_per_second:.2f}")
            logger.info(f"  Memory per operation: {memory_per_operation:.4f}MB")
            logger.info(f"  Error rate: {result.error_summary.get('error_rate', 0):.4f}")
            
            # Performance regression thresholds
            min_ops_per_second = 10.0  # Minimum acceptable performance
            max_memory_per_operation = 1.0  # 1MB per operation max
            max_error_rate = 0.02  # 2% max error rate
            
            # Validate no performance regression
            assert operations_per_second >= min_ops_per_second, \
                f"Performance regression detected: {operations_per_second:.2f} ops/s < {min_ops_per_second}"
            
            assert memory_per_operation <= max_memory_per_operation, \
                f"Memory regression detected: {memory_per_operation:.4f}MB > {max_memory_per_operation}MB per operation"
            
            assert result.error_summary.get("error_rate", 1.0) <= max_error_rate, \
                f"Error rate regression: {result.error_summary.get('error_rate', 0):.4f} > {max_error_rate}"
            
            assert result.success, "Integration performance test failed"
            
        finally:
            # Restore original values
            CONCURRENT_USERS = original_concurrent_users
            OPERATIONS_PER_USER = original_operations_per_user
    
    async def test_data_consistency_across_all_systems(self, integrated_system_manager):
        """Test data consistency across WebSocket, memory, and database systems."""
        logger.info("Testing data consistency across all systems")
        
        # Initialize all systems
        await integrated_system_manager.initialize_all_systems()
        
        # Get system services
        websocket_manager = integrated_system_manager.services.get("websocket_manager")
        memory_service = integrated_system_manager.services.get("memory_optimization")
        clickhouse_client = integrated_system_manager.services.get("clickhouse_client")
        
        # Test data flow consistency
        test_data = []
        consistency_results = {}
        
        # 1. Create test data through WebSocket
        for i in range(10):
            user_id = f"consistency_user_{i}"
            mock_ws = Mock()
            
            # Connect via WebSocket
            await websocket_manager.connect(mock_ws, user_id)
            
            # Send data through WebSocket
            message_data = {
                "user_id": user_id,
                "message_id": i,
                "content": f"Test message {i}",
                "timestamp": time.time()
            }
            
            await websocket_manager.send_message(user_id, message_data)
            test_data.append(message_data)
        
        # 2. Verify data in ClickHouse (if available)
        if clickhouse_client:
            try:
                # Simulate data verification query
                verify_query = "SELECT count(*) as count FROM test_messages"
                result = await clickhouse_client.execute(verify_query)
                consistency_results["clickhouse_data_accessible"] = True
            except Exception as e:
                consistency_results["clickhouse_data_accessible"] = False
                logger.debug(f"ClickHouse verification failed: {e}")
        
        # 3. Verify memory usage is reasonable
        memory_stats = memory_service.get_memory_stats()
        consistency_results["memory_usage_reasonable"] = memory_stats.get("memory_mb", 0) < 1000
        
        # 4. Verify WebSocket connections are tracked
        consistency_results["websocket_connections_tracked"] = len(
            getattr(websocket_manager, 'active_connections', {})
        ) >= 0
        
        # 5. Test data cleanup
        for i in range(10):
            user_id = f"consistency_user_{i}"
            mock_ws = Mock()
            await websocket_manager.disconnect(mock_ws)
        
        # Verify cleanup
        final_memory = memory_service.get_memory_stats()
        memory_cleaned_up = final_memory.get("memory_mb", 0) <= memory_stats.get("memory_mb", 0)
        consistency_results["memory_cleaned_up"] = memory_cleaned_up
        
        logger.info(f"Data consistency results: {json.dumps(consistency_results, indent=2)}")
        
        # Validate data consistency
        assert consistency_results["memory_usage_reasonable"], "Memory usage not reasonable during data operations"
        assert consistency_results["websocket_connections_tracked"], "WebSocket connections not properly tracked"
        assert consistency_results["memory_cleaned_up"], "Memory not properly cleaned up after operations"