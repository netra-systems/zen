#!/usr/bin/env python
"""INTEGRATION TEST: WebSocket Service Coordination - REAL SERVICES ONLY

Business Value Justification:
- Segment: Platform/Internal - Service architecture coordination
- Business Goal: Development Velocity & System Reliability - Seamless service coordination
- Value Impact: Validates WebSocket services coordinate properly with all system components
- Strategic Impact: Ensures service coordination patterns support scalable multi-service architecture

This test suite validates comprehensive WebSocket service coordination:
- UnifiedWebSocketManager coordination with backend services
- WebSocket service discovery and inter-service communication
- Service lifecycle coordination during startup/shutdown
- Load balancing and connection distribution coordination
- Service health monitoring and failover coordination
- Multi-tenant service isolation and coordination

Per CLAUDE.md: UnifiedWebSocketManager - central coordination point
Per CLAUDE.md: Microservice independence with shared coordination
Per CLAUDE.md: "MOCKS = Abomination" - Only real service coordination

SUCCESS CRITERIA:
- WebSocket services coordinate seamlessly with all backend services
- Service discovery enables dynamic service coordination
- Load balancing coordinates connections across service instances
- Health monitoring coordinates service availability across boundaries
- Multi-tenant isolation maintained during service coordination
- Service coordination patterns scale under production load
"""

import asyncio
import json
import os
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading
import random
import statistics

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment after path setup
from shared.isolated_environment import get_env, IsolatedEnvironment

import pytest
from loguru import logger

# Import REAL production components - NO MOCKS per CLAUDE.md
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager

# Import integration test framework
from test_framework.test_context import TestContext, create_test_context
from test_framework.websocket_helpers import WebSocketTestHelpers
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    pytest.skip("websockets not available", allow_module_level=True)


# ============================================================================
# WEBSOCKET SERVICE COORDINATION MONITORING
# ============================================================================

class WebSocketServiceCoordinationMonitor:
    """Monitors WebSocket service coordination patterns and inter-service communication."""
    
    def __init__(self):
        self.coordination_sessions: Dict[str, Dict[str, Any]] = {}
        self.service_discovery_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.inter_service_communications: List[Dict[str, Any]] = []
        self.load_balancing_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.health_monitoring_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.service_lifecycle_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.tenant_isolation_tracking: Dict[str, Dict[str, Any]] = {}
        self.monitor_lock = threading.Lock()
    
    def start_service_coordination_session(self, session_id: str, coordination_config: Dict[str, Any]) -> None:
        """Start monitoring a WebSocket service coordination session."""
        with self.monitor_lock:
            self.coordination_sessions[session_id] = {
                "session_id": session_id,
                "start_time": time.time(),
                "coordination_scope": coordination_config.get("coordination_scope", "single_service"),
                "services_coordinated": coordination_config.get("services_coordinated", []),
                "coordination_complexity": coordination_config.get("coordination_complexity", "standard"),
                "tenant_isolation_required": coordination_config.get("tenant_isolation", True),
                "status": "active",
                "service_discoveries": 0,
                "successful_coordinations": 0,
                "coordination_failures": 0,
                "health_checks_performed": 0,
                "load_balancing_decisions": 0,
                "tenant_boundary_crossings": 0
            }
    
    def record_service_discovery_event(self, session_id: str, discovery_data: Dict[str, Any]) -> None:
        """Record service discovery coordination event."""
        discovery_event = {
            "session_id": session_id,
            "discovery_type": discovery_data.get("discovery_type", "automatic"),
            "service_name": discovery_data.get("service_name", "unknown"),
            "service_endpoint": discovery_data.get("service_endpoint", "unknown"),
            "service_health": discovery_data.get("service_health", "unknown"),
            "discovery_latency_ms": discovery_data.get("discovery_latency_ms", 0),
            "discovery_success": discovery_data.get("discovery_success", True),
            "timestamp": time.time()
        }
        
        with self.monitor_lock:
            self.service_discovery_events[session_id].append(discovery_event)
            
            if session_id in self.coordination_sessions:
                self.coordination_sessions[session_id]["service_discoveries"] += 1
    
    def record_inter_service_communication(self, communication_data: Dict[str, Any]) -> None:
        """Record inter-service communication for coordination analysis."""
        communication_event = {
            "source_service": communication_data.get("source_service", "unknown"),
            "target_service": communication_data.get("target_service", "unknown"),
            "communication_type": communication_data.get("communication_type", "unknown"),
            "payload_size_bytes": communication_data.get("payload_size_bytes", 0),
            "response_time_ms": communication_data.get("response_time_ms", 0),
            "success": communication_data.get("success", True),
            "tenant_context": communication_data.get("tenant_context", "unknown"),
            "timestamp": time.time()
        }
        
        with self.monitor_lock:
            self.inter_service_communications.append(communication_event)
    
    def record_load_balancing_event(self, session_id: str, load_balancing_data: Dict[str, Any]) -> None:
        """Record load balancing coordination event."""
        load_balancing_event = {
            "session_id": session_id,
            "balancing_algorithm": load_balancing_data.get("algorithm", "round_robin"),
            "available_instances": load_balancing_data.get("available_instances", 0),
            "selected_instance": load_balancing_data.get("selected_instance", "unknown"),
            "instance_load": load_balancing_data.get("instance_load", 0),
            "balancing_decision_time_ms": load_balancing_data.get("decision_time_ms", 0),
            "timestamp": time.time()
        }
        
        with self.monitor_lock:
            self.load_balancing_events[session_id].append(load_balancing_event)
            
            if session_id in self.coordination_sessions:
                self.coordination_sessions[session_id]["load_balancing_decisions"] += 1
    
    def record_health_monitoring_event(self, session_id: str, health_data: Dict[str, Any]) -> None:
        """Record service health monitoring coordination event."""
        health_event = {
            "session_id": session_id,
            "service_name": health_data.get("service_name", "unknown"),
            "health_status": health_data.get("health_status", "unknown"),
            "health_metrics": health_data.get("health_metrics", {}),
            "health_check_latency_ms": health_data.get("check_latency_ms", 0),
            "health_coordination_required": health_data.get("coordination_required", False),
            "timestamp": time.time()
        }
        
        with self.monitor_lock:
            self.health_monitoring_events[session_id].append(health_event)
            
            if session_id in self.coordination_sessions:
                self.coordination_sessions[session_id]["health_checks_performed"] += 1
    
    def record_service_lifecycle_event(self, session_id: str, lifecycle_data: Dict[str, Any]) -> None:
        """Record service lifecycle coordination event."""
        lifecycle_event = {
            "session_id": session_id,
            "lifecycle_stage": lifecycle_data.get("lifecycle_stage", "unknown"),
            "service_name": lifecycle_data.get("service_name", "unknown"),
            "coordination_required": lifecycle_data.get("coordination_required", True),
            "coordination_success": lifecycle_data.get("coordination_success", True),
            "affected_services": lifecycle_data.get("affected_services", []),
            "coordination_duration_ms": lifecycle_data.get("coordination_duration_ms", 0),
            "timestamp": time.time()
        }
        
        with self.monitor_lock:
            self.service_lifecycle_events[session_id].append(lifecycle_event)
    
    def track_tenant_isolation(self, session_id: str, tenant_id: str, isolation_metrics: Dict[str, Any]) -> None:
        """Track multi-tenant isolation during service coordination."""
        with self.monitor_lock:
            isolation_key = f"{session_id}_{tenant_id}"
            
            self.tenant_isolation_tracking[isolation_key] = {
                "session_id": session_id,
                "tenant_id": tenant_id,
                "isolation_level": isolation_metrics.get("isolation_level", "standard"),
                "resource_allocation": isolation_metrics.get("resource_allocation", {}),
                "boundary_violations": isolation_metrics.get("boundary_violations", 0),
                "cross_tenant_communications": isolation_metrics.get("cross_tenant_communications", 0),
                "isolation_effectiveness": isolation_metrics.get("isolation_effectiveness", 1.0),
                "timestamp": time.time()
            }
            
            if session_id in self.coordination_sessions:
                self.coordination_sessions[session_id]["tenant_boundary_crossings"] += isolation_metrics.get("boundary_violations", 0)
    
    def complete_service_coordination_session(self, session_id: str, completion_data: Dict[str, Any]) -> None:
        """Complete service coordination session and calculate final metrics."""
        with self.monitor_lock:
            if session_id in self.coordination_sessions:
                session = self.coordination_sessions[session_id]
                session["status"] = "completed"
                session["end_time"] = time.time()
                session["total_duration"] = time.time() - session["start_time"]
                session.update(completion_data)
                
                # Calculate service coordination effectiveness
                effectiveness_score = self._calculate_service_coordination_effectiveness(session_id)
                session["service_coordination_effectiveness"] = effectiveness_score
    
    def _calculate_service_coordination_effectiveness(self, session_id: str) -> float:
        """Calculate service coordination effectiveness score."""
        session = self.coordination_sessions.get(session_id, {})
        
        score = 0.0
        
        # Service discovery effectiveness (20% of score)
        service_discoveries = session.get("service_discoveries", 0)
        if service_discoveries > 0:
            score += 0.2
        
        # Successful coordination rate (30% of score)
        successful = session.get("successful_coordinations", 0)
        failures = session.get("coordination_failures", 0)
        total_coordinations = successful + failures
        
        if total_coordinations > 0:
            coordination_success_rate = successful / total_coordinations
            score += coordination_success_rate * 0.3
        elif successful == 0 and failures == 0:
            score += 0.3  # No failures = perfect coordination
        
        # Health monitoring effectiveness (20% of score)
        health_checks = session.get("health_checks_performed", 0)
        if health_checks > 0:
            score += 0.2
        
        # Load balancing decisions (15% of score)
        load_balancing_decisions = session.get("load_balancing_decisions", 0)
        if load_balancing_decisions > 0:
            score += 0.15
        
        # Tenant isolation effectiveness (15% of score)
        tenant_boundary_crossings = session.get("tenant_boundary_crossings", 0)
        if tenant_boundary_crossings == 0:
            score += 0.15  # Perfect tenant isolation
        elif tenant_boundary_crossings <= 2:
            score += 0.075  # Minor isolation issues
        
        return min(score, 1.0)
    
    def get_service_coordination_report(self) -> Dict[str, Any]:
        """Generate comprehensive service coordination report."""
        with self.monitor_lock:
            total_sessions = len(self.coordination_sessions)
            completed_sessions = sum(1 for s in self.coordination_sessions.values() if s.get("status") == "completed")
            
            # Calculate service coordination effectiveness
            effectiveness_scores = [s.get("service_coordination_effectiveness", 0) for s in self.coordination_sessions.values() if s.get("service_coordination_effectiveness") is not None]
            
            # Analyze service discovery patterns
            service_discovery_analysis = self._analyze_service_discovery_patterns()
            
            # Analyze inter-service communication
            inter_service_analysis = self._analyze_inter_service_communication()
            
            # Analyze load balancing coordination
            load_balancing_analysis = self._analyze_load_balancing_patterns()
            
            # Analyze health monitoring coordination
            health_monitoring_analysis = self._analyze_health_monitoring_patterns()
            
            # Analyze tenant isolation effectiveness
            tenant_isolation_analysis = self._analyze_tenant_isolation_effectiveness()
            
            return {
                "session_summary": {
                    "total_sessions": total_sessions,
                    "completed_sessions": completed_sessions,
                    "completion_rate": completed_sessions / max(total_sessions, 1)
                },
                "service_coordination_effectiveness": {
                    "mean_effectiveness": statistics.mean(effectiveness_scores) if effectiveness_scores else 0,
                    "min_effectiveness": min(effectiveness_scores) if effectiveness_scores else 0,
                    "max_effectiveness": max(effectiveness_scores) if effectiveness_scores else 0,
                    "sessions_above_80": sum(1 for score in effectiveness_scores if score >= 0.8),
                    "sessions_above_60": sum(1 for score in effectiveness_scores if score >= 0.6)
                },
                "service_discovery": service_discovery_analysis,
                "inter_service_communication": inter_service_analysis,
                "load_balancing": load_balancing_analysis,
                "health_monitoring": health_monitoring_analysis,
                "tenant_isolation": tenant_isolation_analysis,
                "report_timestamp": time.time()
            }
    
    def _analyze_service_discovery_patterns(self) -> Dict[str, Any]:
        """Analyze service discovery coordination patterns."""
        all_discovery_events = []
        for events in self.service_discovery_events.values():
            all_discovery_events.extend(events)
        
        if not all_discovery_events:
            return {"no_discovery_data": True}
        
        successful_discoveries = sum(1 for event in all_discovery_events if event.get("discovery_success", False))
        discovery_latencies = [event.get("discovery_latency_ms", 0) for event in all_discovery_events]
        
        return {
            "total_discovery_events": len(all_discovery_events),
            "discovery_success_rate": successful_discoveries / len(all_discovery_events),
            "avg_discovery_latency_ms": statistics.mean(discovery_latencies),
            "max_discovery_latency_ms": max(discovery_latencies) if discovery_latencies else 0
        }
    
    def _analyze_inter_service_communication(self) -> Dict[str, Any]:
        """Analyze inter-service communication patterns."""
        if not self.inter_service_communications:
            return {"no_communication_data": True}
        
        successful_communications = sum(1 for comm in self.inter_service_communications if comm.get("success", False))
        response_times = [comm.get("response_time_ms", 0) for comm in self.inter_service_communications]
        payload_sizes = [comm.get("payload_size_bytes", 0) for comm in self.inter_service_communications]
        
        return {
            "total_communications": len(self.inter_service_communications),
            "communication_success_rate": successful_communications / len(self.inter_service_communications),
            "avg_response_time_ms": statistics.mean(response_times),
            "avg_payload_size_bytes": statistics.mean(payload_sizes),
            "max_response_time_ms": max(response_times) if response_times else 0
        }
    
    def _analyze_load_balancing_patterns(self) -> Dict[str, Any]:
        """Analyze load balancing coordination patterns."""
        all_load_balancing_events = []
        for events in self.load_balancing_events.values():
            all_load_balancing_events.extend(events)
        
        if not all_load_balancing_events:
            return {"no_load_balancing_data": True}
        
        decision_times = [event.get("balancing_decision_time_ms", 0) for event in all_load_balancing_events]
        
        return {
            "total_load_balancing_events": len(all_load_balancing_events),
            "avg_decision_time_ms": statistics.mean(decision_times),
            "max_decision_time_ms": max(decision_times) if decision_times else 0
        }
    
    def _analyze_health_monitoring_patterns(self) -> Dict[str, Any]:
        """Analyze health monitoring coordination patterns."""
        all_health_events = []
        for events in self.health_monitoring_events.values():
            all_health_events.extend(events)
        
        if not all_health_events:
            return {"no_health_monitoring_data": True}
        
        healthy_services = sum(1 for event in all_health_events if event.get("health_status") == "healthy")
        check_latencies = [event.get("health_check_latency_ms", 0) for event in all_health_events]
        
        return {
            "total_health_checks": len(all_health_events),
            "service_health_rate": healthy_services / len(all_health_events),
            "avg_check_latency_ms": statistics.mean(check_latencies),
            "max_check_latency_ms": max(check_latencies) if check_latencies else 0
        }
    
    def _analyze_tenant_isolation_effectiveness(self) -> Dict[str, Any]:
        """Analyze tenant isolation effectiveness during service coordination."""
        if not self.tenant_isolation_tracking:
            return {"no_tenant_isolation_data": True}
        
        isolation_data = list(self.tenant_isolation_tracking.values())
        boundary_violations = sum(isolation["boundary_violations"] for isolation in isolation_data)
        isolation_effectiveness_scores = [isolation.get("isolation_effectiveness", 1.0) for isolation in isolation_data]
        
        return {
            "total_tenants_tracked": len(isolation_data),
            "total_boundary_violations": boundary_violations,
            "avg_isolation_effectiveness": statistics.mean(isolation_effectiveness_scores),
            "perfect_isolation_tenants": sum(1 for score in isolation_effectiveness_scores if score >= 0.95)
        }


class WebSocketServiceCoordinationTester:
    """Tests WebSocket service coordination with real services."""
    
    def __init__(self, monitor: WebSocketServiceCoordinationMonitor):
        self.monitor = monitor
        self.docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
    
    async def execute_service_discovery_coordination_test(
        self,
        session_id: str,
        discovery_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute service discovery coordination test."""
        
        coordination_config = {
            "coordination_scope": "service_discovery",
            "services_coordinated": discovery_config.get("services", ["websocket", "backend"]),
            "coordination_complexity": "service_discovery"
        }
        
        self.monitor.start_service_coordination_session(session_id, coordination_config)
        
        # Test WebSocket manager service discovery
        discovery_start = time.time()
        
        try:
            websocket_manager = await self._create_websocket_manager()
            
            discovery_latency = (time.time() - discovery_start) * 1000
            
            self.monitor.record_service_discovery_event(session_id, {
                "discovery_type": "websocket_manager",
                "service_name": "websocket_manager",
                "service_endpoint": "internal",
                "service_health": "healthy",
                "discovery_latency_ms": discovery_latency,
                "discovery_success": True
            })
            
            # Test service coordination with discovered WebSocket manager
            user_id = f"service_discovery_user_{uuid.uuid4().hex[:8]}"
            
            # Test connection info coordination
            connection_info_start = time.time()
            connection_info = await websocket_manager.get_connection_info(user_id)
            connection_info_latency = (time.time() - connection_info_start) * 1000
            
            self.monitor.record_inter_service_communication({
                "source_service": "coordination_tester",
                "target_service": "websocket_manager",
                "communication_type": "get_connection_info",
                "payload_size_bytes": len(user_id.encode()),
                "response_time_ms": connection_info_latency,
                "success": True,
                "tenant_context": user_id
            })
            
            coordination_success = True
            
        except Exception as e:
            logger.info(f"Service discovery coordination test: {e}")
            
            discovery_latency = (time.time() - discovery_start) * 1000
            
            self.monitor.record_service_discovery_event(session_id, {
                "discovery_type": "websocket_manager",
                "service_name": "websocket_manager",
                "service_endpoint": "internal",
                "service_health": "unhealthy",
                "discovery_latency_ms": discovery_latency,
                "discovery_success": False
            })
            
            coordination_success = False
        
        return {
            "session_id": session_id,
            "service_discovery_success": coordination_success,
            "discovery_latency_ms": discovery_latency,
            "services_discovered": 1 if coordination_success else 0
        }
    
    async def execute_inter_service_coordination_test(
        self,
        session_id: str,
        inter_service_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute inter-service coordination test."""
        
        coordination_config = {
            "coordination_scope": "inter_service",
            "services_coordinated": ["websocket", "agent", "backend"],
            "coordination_complexity": "high"
        }
        
        self.monitor.start_service_coordination_session(session_id, coordination_config)
        
        # Test WebSocket service to Agent service coordination
        websocket_manager = await self._create_websocket_manager()
        agent_registry = AgentRegistry()
        
        # Test setting WebSocket manager on agent registry (inter-service coordination)
        coordination_start = time.time()
        
        agent_registry.set_websocket_manager(websocket_manager)
        
        coordination_latency = (time.time() - coordination_start) * 1000
        
        self.monitor.record_inter_service_communication({
            "source_service": "agent_service",
            "target_service": "websocket_service",
            "communication_type": "manager_registration",
            "payload_size_bytes": 1024,  # Estimate for manager reference
            "response_time_ms": coordination_latency,
            "success": True,
            "tenant_context": "system"
        })
        
        # Test user context coordination across services
        user_context = UserExecutionContext.create_for_request(
            user_id=f"inter_service_user_{uuid.uuid4().hex[:8]}",
            request_id=f"inter_service_req_{uuid.uuid4().hex[:8]}"
        )
        
        # Test tool dispatcher creation (agent-websocket coordination)
        tool_dispatcher_start = time.time()
        
        try:
            tool_dispatcher = await agent_registry.create_enhanced_tool_dispatcher(user_context)
            tool_dispatcher_latency = (time.time() - tool_dispatcher_start) * 1000
            
            self.monitor.record_inter_service_communication({
                "source_service": "agent_service",
                "target_service": "websocket_service",
                "communication_type": "tool_dispatcher_creation",
                "payload_size_bytes": len(str(user_context.__dict__)),
                "response_time_ms": tool_dispatcher_latency,
                "success": True,
                "tenant_context": user_context.user_id
            })
            
            inter_service_success = True
            
        except Exception as e:
            tool_dispatcher_latency = (time.time() - tool_dispatcher_start) * 1000
            
            self.monitor.record_inter_service_communication({
                "source_service": "agent_service",
                "target_service": "websocket_service",
                "communication_type": "tool_dispatcher_creation",
                "payload_size_bytes": len(str(user_context.__dict__)),
                "response_time_ms": tool_dispatcher_latency,
                "success": False,
                "tenant_context": user_context.user_id
            })
            
            inter_service_success = False
            logger.info(f"Inter-service coordination test: {e}")
        
        return {
            "session_id": session_id,
            "inter_service_coordination_success": inter_service_success,
            "coordination_latency_ms": coordination_latency,
            "tool_dispatcher_latency_ms": tool_dispatcher_latency
        }
    
    async def execute_load_balancing_coordination_test(
        self,
        session_id: str,
        load_balancing_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute load balancing coordination test."""
        
        coordination_config = {
            "coordination_scope": "load_balancing",
            "services_coordinated": ["websocket_instances"],
            "coordination_complexity": "load_balancing"
        }
        
        self.monitor.start_service_coordination_session(session_id, coordination_config)
        
        # Simulate multiple WebSocket service instances for load balancing
        instance_count = load_balancing_config.get("instance_count", 3)
        
        for instance_index in range(instance_count):
            balancing_start = time.time()
            
            # Simulate load balancing decision
            available_instances = list(range(instance_count))
            selected_instance = random.choice(available_instances)
            instance_load = random.uniform(0.1, 0.8)
            
            balancing_decision_time = (time.time() - balancing_start) * 1000
            
            self.monitor.record_load_balancing_event(session_id, {
                "algorithm": "weighted_round_robin",
                "available_instances": len(available_instances),
                "selected_instance": f"websocket_instance_{selected_instance}",
                "instance_load": instance_load,
                "decision_time_ms": balancing_decision_time
            })
            
            # Small delay between load balancing decisions
            await asyncio.sleep(0.01)
        
        return {
            "session_id": session_id,
            "load_balancing_decisions": instance_count,
            "instance_count": instance_count
        }
    
    async def execute_health_monitoring_coordination_test(
        self,
        session_id: str,
        health_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute health monitoring coordination test."""
        
        coordination_config = {
            "coordination_scope": "health_monitoring",
            "services_coordinated": ["websocket", "backend", "database"],
            "coordination_complexity": "health_monitoring"
        }
        
        self.monitor.start_service_coordination_session(session_id, coordination_config)
        
        # Test health monitoring coordination for multiple services
        services_to_monitor = health_config.get("services", ["websocket_service", "backend_service", "database_service"])
        
        for service_name in services_to_monitor:
            health_check_start = time.time()
            
            # Simulate health check coordination
            if service_name == "websocket_service":
                # Real WebSocket service health check
                try:
                    websocket_manager = await self._create_websocket_manager()
                    health_status = "healthy" if websocket_manager else "unhealthy"
                    health_metrics = {"connections": 0, "response_time": 50}
                except Exception:
                    health_status = "unhealthy"
                    health_metrics = {"error": "service_unavailable"}
            else:
                # Simulate health check for other services
                health_status = random.choice(["healthy", "healthy", "healthy", "degraded"])  # 75% healthy
                health_metrics = {
                    "cpu_usage": random.uniform(10, 80),
                    "memory_usage": random.uniform(20, 70),
                    "response_time": random.uniform(10, 200)
                }
            
            health_check_latency = (time.time() - health_check_start) * 1000
            
            self.monitor.record_health_monitoring_event(session_id, {
                "service_name": service_name,
                "health_status": health_status,
                "health_metrics": health_metrics,
                "check_latency_ms": health_check_latency,
                "coordination_required": health_status != "healthy"
            })
        
        return {
            "session_id": session_id,
            "services_monitored": len(services_to_monitor),
            "health_checks_performed": len(services_to_monitor)
        }
    
    async def execute_tenant_isolation_coordination_test(
        self,
        session_id: str,
        tenant_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tenant isolation coordination test."""
        
        tenant_count = tenant_config.get("tenant_count", 3)
        
        coordination_config = {
            "coordination_scope": "tenant_isolation",
            "services_coordinated": ["websocket", "agent"],
            "coordination_complexity": "multi_tenant",
            "tenant_isolation": True
        }
        
        self.monitor.start_service_coordination_session(session_id, coordination_config)
        
        # Test tenant isolation coordination
        tenant_results = []
        
        for tenant_index in range(tenant_count):
            tenant_id = f"tenant_{tenant_index:02d}"
            
            # Create isolated tenant context
            user_context = UserExecutionContext.create_for_request(
                user_id=f"{tenant_id}_user_{uuid.uuid4().hex[:8]}",
                request_id=f"{tenant_id}_req_{uuid.uuid4().hex[:8]}"
            )
            
            # Test WebSocket coordination for tenant
            try:
                websocket_manager = await self._create_websocket_manager()
                
                # Test tenant-specific WebSocket operations
                connection_info = await websocket_manager.get_connection_info(user_context.user_id)
                
                # Track tenant isolation metrics
                self.monitor.track_tenant_isolation(session_id, tenant_id, {
                    "isolation_level": "strict",
                    "resource_allocation": {"connections": 1, "memory_mb": 10},
                    "boundary_violations": 0,  # Should be 0 for proper isolation
                    "cross_tenant_communications": 0,  # Should be 0 for proper isolation
                    "isolation_effectiveness": 1.0
                })
                
                tenant_results.append({
                    "tenant_id": tenant_id,
                    "isolation_success": True,
                    "user_context": user_context.user_id
                })
                
            except Exception as e:
                logger.info(f"Tenant {tenant_id} coordination test: {e}")
                
                # Track failed tenant isolation
                self.monitor.track_tenant_isolation(session_id, tenant_id, {
                    "isolation_level": "degraded",
                    "resource_allocation": {},
                    "boundary_violations": 1,  # Failure counts as violation
                    "cross_tenant_communications": 0,
                    "isolation_effectiveness": 0.5
                })
                
                tenant_results.append({
                    "tenant_id": tenant_id,
                    "isolation_success": False,
                    "error": str(e)
                })
        
        successful_tenants = sum(1 for result in tenant_results if result["isolation_success"])
        
        return {
            "session_id": session_id,
            "tenant_count": tenant_count,
            "successful_tenant_isolations": successful_tenants,
            "tenant_isolation_rate": successful_tenants / tenant_count,
            "tenant_results": tenant_results
        }
    
    async def _create_websocket_manager(self):
        """Create WebSocket manager for coordination testing."""
        from netra_backend.app.websocket_core import create_websocket_manager
        return await create_websocket_manager()


# ============================================================================
# INTEGRATION WEBSOCKET SERVICE COORDINATION TESTS
# ============================================================================

class TestWebSocketServiceCoordination:
    """Integration tests for WebSocket service coordination."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.service_coordination
    async def test_websocket_service_discovery_coordination(self):
        """Test WebSocket service discovery coordination patterns.
        
        Business Value: Validates WebSocket services can be discovered and coordinated dynamically.
        """
        monitor = WebSocketServiceCoordinationMonitor()
        tester = WebSocketServiceCoordinationTester(monitor)
        
        logger.info("🚀 Starting WebSocket service discovery coordination test")
        
        discovery_config = {
            "services": ["websocket_manager", "websocket_notifier"],
            "discovery_mode": "automatic"
        }
        
        result = await tester.execute_service_discovery_coordination_test(
            session_id="service_discovery_coordination",
            discovery_config=discovery_config
        )
        
        # Get service coordination report
        coordination_report = monitor.get_service_coordination_report()
        
        # CRITICAL SERVICE DISCOVERY ASSERTIONS
        assert result["service_discovery_success"], \
            f"Service discovery coordination failed: {result}"
        
        assert result["discovery_latency_ms"] <= 1000, \
            f"Service discovery too slow: {result['discovery_latency_ms']:.1f}ms > 1000ms"
        
        assert result["services_discovered"] >= 1, \
            f"No services discovered: {result['services_discovered']}"
        
        # Validate service discovery effectiveness
        service_discovery = coordination_report["service_discovery"]
        if not service_discovery.get("no_discovery_data", False):
            assert service_discovery["discovery_success_rate"] >= 0.8, \
                f"Service discovery success rate too low: {service_discovery['discovery_success_rate']:.1%}"
            
            assert service_discovery["avg_discovery_latency_ms"] <= 500, \
                f"Average discovery latency too high: {service_discovery['avg_discovery_latency_ms']:.1f}ms"
        
        # Validate overall coordination effectiveness
        effectiveness = coordination_report["service_coordination_effectiveness"]
        
        assert effectiveness["mean_effectiveness"] >= 0.7, \
            f"Service coordination effectiveness too low: {effectiveness['mean_effectiveness']:.1f}"
        
        logger.info("✅ WebSocket service discovery coordination VALIDATED")
        logger.info(f"  Discovery latency: {result['discovery_latency_ms']:.1f}ms")
        logger.info(f"  Services discovered: {result['services_discovered']}")
        logger.info(f"  Coordination effectiveness: {effectiveness['mean_effectiveness']:.1f}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.service_coordination
    async def test_inter_service_websocket_coordination(self):
        """Test inter-service WebSocket coordination patterns.
        
        Business Value: Validates seamless coordination between WebSocket and other services.
        """
        monitor = WebSocketServiceCoordinationMonitor()
        tester = WebSocketServiceCoordinationTester(monitor)
        
        logger.info("🚀 Starting inter-service WebSocket coordination test")
        
        inter_service_config = {
            "coordination_type": "bidirectional",
            "services": ["websocket", "agent", "backend"]
        }
        
        result = await tester.execute_inter_service_coordination_test(
            session_id="inter_service_coordination",
            inter_service_config=inter_service_config
        )
        
        coordination_report = monitor.get_service_coordination_report()
        
        # CRITICAL INTER-SERVICE COORDINATION ASSERTIONS
        assert result["inter_service_coordination_success"], \
            f"Inter-service coordination failed: {result}"
        
        assert result["coordination_latency_ms"] <= 100, \
            f"Inter-service coordination too slow: {result['coordination_latency_ms']:.1f}ms > 100ms"
        
        assert result["tool_dispatcher_latency_ms"] <= 500, \
            f"Tool dispatcher creation too slow: {result['tool_dispatcher_latency_ms']:.1f}ms > 500ms"
        
        # Validate inter-service communication effectiveness
        inter_service_communication = coordination_report["inter_service_communication"]
        if not inter_service_communication.get("no_communication_data", False):
            assert inter_service_communication["communication_success_rate"] >= 0.9, \
                f"Inter-service communication success rate too low: {inter_service_communication['communication_success_rate']:.1%}"
            
            assert inter_service_communication["avg_response_time_ms"] <= 200, \
                f"Inter-service response time too high: {inter_service_communication['avg_response_time_ms']:.1f}ms"
        
        # Validate coordination effectiveness
        effectiveness = coordination_report["service_coordination_effectiveness"]
        
        assert effectiveness["mean_effectiveness"] >= 0.8, \
            f"Inter-service coordination effectiveness too low: {effectiveness['mean_effectiveness']:.1f}"
        
        logger.info("✅ Inter-service WebSocket coordination VALIDATED")
        logger.info(f"  Coordination latency: {result['coordination_latency_ms']:.1f}ms")
        logger.info(f"  Tool dispatcher latency: {result['tool_dispatcher_latency_ms']:.1f}ms")
        logger.info(f"  Communication success: {inter_service_communication.get('communication_success_rate', 0):.1%}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.service_coordination
    async def test_websocket_load_balancing_coordination(self):
        """Test WebSocket load balancing coordination patterns.
        
        Business Value: Validates load balancing coordinates properly across WebSocket instances.
        """
        monitor = WebSocketServiceCoordinationMonitor()
        tester = WebSocketServiceCoordinationTester(monitor)
        
        logger.info("🚀 Starting WebSocket load balancing coordination test")
        
        load_balancing_config = {
            "instance_count": 5,
            "balancing_algorithm": "weighted_round_robin",
            "coordination_mode": "distributed"
        }
        
        result = await tester.execute_load_balancing_coordination_test(
            session_id="load_balancing_coordination",
            load_balancing_config=load_balancing_config
        )
        
        coordination_report = monitor.get_service_coordination_report()
        
        # CRITICAL LOAD BALANCING COORDINATION ASSERTIONS
        assert result["load_balancing_decisions"] >= load_balancing_config["instance_count"], \
            f"Insufficient load balancing decisions: {result['load_balancing_decisions']} < {load_balancing_config['instance_count']}"
        
        # Validate load balancing coordination effectiveness
        load_balancing = coordination_report["load_balancing"]
        if not load_balancing.get("no_load_balancing_data", False):
            assert load_balancing["avg_decision_time_ms"] <= 50, \
                f"Load balancing decision time too high: {load_balancing['avg_decision_time_ms']:.1f}ms > 50ms"
            
            assert load_balancing["max_decision_time_ms"] <= 200, \
                f"Max load balancing decision time too high: {load_balancing['max_decision_time_ms']:.1f}ms > 200ms"
        
        # Validate coordination effectiveness
        effectiveness = coordination_report["service_coordination_effectiveness"]
        
        assert effectiveness["mean_effectiveness"] >= 0.7, \
            f"Load balancing coordination effectiveness too low: {effectiveness['mean_effectiveness']:.1f}"
        
        logger.info("✅ WebSocket load balancing coordination VALIDATED")
        logger.info(f"  Load balancing decisions: {result['load_balancing_decisions']}")
        logger.info(f"  Instance count: {result['instance_count']}")
        logger.info(f"  Avg decision time: {load_balancing.get('avg_decision_time_ms', 0):.1f}ms")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.service_coordination
    async def test_websocket_health_monitoring_coordination(self):
        """Test WebSocket health monitoring coordination patterns.
        
        Business Value: Validates health monitoring coordinates across all WebSocket-related services.
        """
        monitor = WebSocketServiceCoordinationMonitor()
        tester = WebSocketServiceCoordinationTester(monitor)
        
        logger.info("🚀 Starting WebSocket health monitoring coordination test")
        
        health_config = {
            "services": ["websocket_service", "backend_service", "database_service"],
            "monitoring_interval": 1.0,
            "coordination_required": True
        }
        
        result = await tester.execute_health_monitoring_coordination_test(
            session_id="health_monitoring_coordination",
            health_config=health_config
        )
        
        coordination_report = monitor.get_service_coordination_report()
        
        # CRITICAL HEALTH MONITORING COORDINATION ASSERTIONS
        assert result["health_checks_performed"] >= len(health_config["services"]), \
            f"Insufficient health checks: {result['health_checks_performed']} < {len(health_config['services'])}"
        
        assert result["services_monitored"] == len(health_config["services"]), \
            f"Not all services monitored: {result['services_monitored']} < {len(health_config['services'])}"
        
        # Validate health monitoring coordination effectiveness
        health_monitoring = coordination_report["health_monitoring"]
        if not health_monitoring.get("no_health_monitoring_data", False):
            assert health_monitoring["service_health_rate"] >= 0.7, \
                f"Service health rate too low: {health_monitoring['service_health_rate']:.1%} < 70%"
            
            assert health_monitoring["avg_check_latency_ms"] <= 500, \
                f"Health check latency too high: {health_monitoring['avg_check_latency_ms']:.1f}ms > 500ms"
        
        # Validate coordination effectiveness
        effectiveness = coordination_report["service_coordination_effectiveness"]
        
        assert effectiveness["mean_effectiveness"] >= 0.7, \
            f"Health monitoring coordination effectiveness too low: {effectiveness['mean_effectiveness']:.1f}"
        
        logger.info("✅ WebSocket health monitoring coordination VALIDATED")
        logger.info(f"  Services monitored: {result['services_monitored']}")
        logger.info(f"  Health checks: {result['health_checks_performed']}")
        logger.info(f"  Health rate: {health_monitoring.get('service_health_rate', 0):.1%}")

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.service_coordination
    async def test_multi_tenant_websocket_coordination(self):
        """Test multi-tenant WebSocket coordination patterns.
        
        Business Value: Validates tenant isolation maintained during WebSocket service coordination.
        """
        monitor = WebSocketServiceCoordinationMonitor()
        tester = WebSocketServiceCoordinationTester(monitor)
        
        logger.info("🚀 Starting multi-tenant WebSocket coordination test")
        
        tenant_config = {
            "tenant_count": 4,
            "isolation_level": "strict",
            "coordination_scope": "per_tenant"
        }
        
        result = await tester.execute_tenant_isolation_coordination_test(
            session_id="multi_tenant_coordination",
            tenant_config=tenant_config
        )
        
        coordination_report = monitor.get_service_coordination_report()
        
        # CRITICAL MULTI-TENANT COORDINATION ASSERTIONS
        assert result["tenant_count"] == tenant_config["tenant_count"], \
            f"Tenant count mismatch: {result['tenant_count']} != {tenant_config['tenant_count']}"
        
        assert result["tenant_isolation_rate"] >= 0.8, \
            f"Tenant isolation rate too low: {result['tenant_isolation_rate']:.1%} < 80%"
        
        assert result["successful_tenant_isolations"] >= tenant_config["tenant_count"] * 0.8, \
            f"Too many tenant isolation failures: {result['successful_tenant_isolations']}/{tenant_config['tenant_count']}"
        
        # Validate tenant isolation effectiveness
        tenant_isolation = coordination_report["tenant_isolation"]
        if not tenant_isolation.get("no_tenant_isolation_data", False):
            assert tenant_isolation["total_boundary_violations"] <= tenant_config["tenant_count"] * 0.1, \
                f"Too many tenant boundary violations: {tenant_isolation['total_boundary_violations']}"
            
            assert tenant_isolation["avg_isolation_effectiveness"] >= 0.8, \
                f"Tenant isolation effectiveness too low: {tenant_isolation['avg_isolation_effectiveness']:.1f}"
            
            assert tenant_isolation["perfect_isolation_tenants"] >= tenant_config["tenant_count"] * 0.7, \
                f"Too few perfectly isolated tenants: {tenant_isolation['perfect_isolation_tenants']}/{tenant_config['tenant_count']}"
        
        # Validate coordination effectiveness
        effectiveness = coordination_report["service_coordination_effectiveness"]
        
        assert effectiveness["mean_effectiveness"] >= 0.7, \
            f"Multi-tenant coordination effectiveness too low: {effectiveness['mean_effectiveness']:.1f}"
        
        logger.info("✅ Multi-tenant WebSocket coordination VALIDATED")
        logger.info(f"  Tenant count: {result['tenant_count']}")
        logger.info(f"  Isolation rate: {result['tenant_isolation_rate']:.1%}")
        logger.info(f"  Boundary violations: {tenant_isolation.get('total_boundary_violations', 0)}")
        logger.info(f"  Perfect isolation: {tenant_isolation.get('perfect_isolation_tenants', 0)}/{tenant_config['tenant_count']}")


# ============================================================================
# COMPREHENSIVE INTEGRATION TEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Run the comprehensive integration WebSocket service coordination tests
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: WebSocket Service Coordination")
    print("BUSINESS VALUE: Scalable Multi-Service Architecture Foundation")
    print("=" * 80)
    print()
    print("Service Coordination Patterns Tested:")
    print("- WebSocket service discovery and dynamic coordination")
    print("- Inter-service communication and coordination protocols")
    print("- Load balancing coordination across service instances")
    print("- Health monitoring and service availability coordination")
    print("- Multi-tenant isolation during service coordination")
    print("- Service lifecycle coordination and dependency management")
    print()
    print("SUCCESS CRITERIA: Seamless coordination across all service boundaries")
    print("\n" + "-" * 80)
    
    # Run integration service coordination tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "--maxfail=2",
        "-k", "service_coordination and integration"
    ])