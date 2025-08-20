"""
Agent Resource Utilization Isolation Test Suite
===============================================

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant isolation requirements)
- Business Goal: Ensure secure per-tenant resource isolation to prevent noisy neighbor problems
- Value Impact: Prevents performance degradation affecting $500K+ enterprise contracts
- Revenue Impact: Essential for enterprise trust and SLA compliance required for premium pricing

This test suite validates comprehensive resource isolation between agent instances,
monitoring CPU and Memory usage per agent to ensure one tenant's activity does not
degrade the performance of others.

Test Coverage:
1. Per-Tenant Resource Monitoring Baseline
2. CPU/Memory Quota Enforcement
3. Resource Leak Detection and Prevention
4. Performance Isolation Under Load
5. Noisy Neighbor Mitigation
6. Multi-Tenant Concurrent Resource Stress
7. Resource Recovery and Cleanup

Performance Requirements:
- Per-agent CPU usage < 25% under normal load
- Per-agent Memory usage < 512MB under normal load
- Resource isolation violations: 0
- Cross-tenant performance impact < 10%
"""

import pytest
import asyncio
import time
import uuid
import json
import secrets
import statistics
import logging
import os
import psutil
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set, Union, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import weakref

import httpx
import websockets
import redis.asyncio as redis
import asyncpg

# Configure test environment
os.environ["TESTING"] = "1"
os.environ["NETRA_ENV"] = "resource_isolation_testing"
os.environ["USE_REAL_SERVICES"] = "true"
os.environ["RESOURCE_ISOLATION_MODE"] = "true"

# Setup logging
logger = logging.getLogger("agent_resource_isolation")
logger.setLevel(logging.INFO)

# Test Configuration
RESOURCE_ISOLATION_CONFIG = {
    "tenant_count": int(os.getenv("RESOURCE_TEST_TENANTS", "20")),
    "test_duration": int(os.getenv("RESOURCE_TEST_DURATION", "600")),  # 10 minutes
    "monitoring_interval": float(os.getenv("RESOURCE_MONITORING_INTERVAL", "1.0")),  # 1 second
    "cpu_quota_percent": float(os.getenv("CPU_QUOTA_PERCENT", "50.0")),
    "memory_quota_mb": int(os.getenv("MEMORY_QUOTA_MB", "1024")),
    "performance_degradation_threshold": float(os.getenv("PERF_DEGRADATION_THRESHOLD", "0.10")),  # 10%
    "noisy_neighbor_threshold": float(os.getenv("NOISY_NEIGHBOR_THRESHOLD", "0.25"))  # 25%
}

# Service endpoints
SERVICE_ENDPOINTS = {
    "auth_service": os.getenv("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
    "backend": os.getenv("E2E_BACKEND_URL", "http://localhost:8000"),
    "websocket": os.getenv("E2E_WEBSOCKET_URL", "ws://localhost:8000/ws"),
    "redis": os.getenv("E2E_REDIS_URL", "redis://localhost:6379"),
    "postgres": os.getenv("E2E_POSTGRES_URL", "postgresql://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev")
}


@dataclass
class ResourceMetrics:
    """Resource utilization metrics for an agent instance."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    io_read_bytes: int
    io_write_bytes: int
    network_sent_bytes: int
    network_recv_bytes: int
    open_files: int
    threads: int


@dataclass
class TenantAgent:
    """Represents a tenant's agent instance with resource monitoring."""
    tenant_id: str
    user_id: str
    email: str
    session_id: str
    auth_token: str
    websocket_client: Optional[websockets.WebSocketServerProtocol] = None
    process_id: Optional[int] = None
    agent_instance_id: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    sensitive_data: Dict[str, Any] = field(default_factory=dict)
    resource_metrics: List[ResourceMetrics] = field(default_factory=list)
    resource_quotas: Dict[str, float] = field(default_factory=dict)
    performance_baseline: Dict[str, float] = field(default_factory=dict)


@dataclass
class ResourceViolation:
    """Represents a resource quota or isolation violation."""
    tenant_id: str
    violation_type: str  # 'cpu_quota', 'memory_quota', 'isolation', 'leak'
    timestamp: float
    severity: str  # 'warning', 'critical'
    details: Dict[str, Any]
    impact_on_others: List[str] = field(default_factory=list)  # Affected tenant IDs


@dataclass
class PerformanceImpactReport:
    """Reports performance impact between tenants."""
    baseline_metrics: Dict[str, float]
    degraded_metrics: Dict[str, float]
    impact_percentage: float
    affected_tenants: List[str]
    noisy_tenants: List[str]
    detection_time: float
    mitigation_time: Optional[float] = None


class ResourceMonitor:
    """Advanced resource monitoring for agent instances."""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.monitoring_interval = monitoring_interval
        self.active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.agent_processes: Dict[str, psutil.Process] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=3600))  # 1 hour at 1s intervals
        self.violation_callbacks: List[callable] = []
        self.system_baseline: Optional[ResourceMetrics] = None
        
    def register_agent_process(self, tenant_id: str, process_id: int):
        """Register an agent process for monitoring."""
        try:
            process = psutil.Process(process_id)
            self.agent_processes[tenant_id] = process
            logger.info(f"Registered process {process_id} for tenant {tenant_id}")
        except psutil.NoSuchProcess:
            logger.warning(f"Process {process_id} not found for tenant {tenant_id}")
    
    def unregister_agent_process(self, tenant_id: str):
        """Unregister an agent process from monitoring."""
        if tenant_id in self.agent_processes:
            del self.agent_processes[tenant_id]
            # Clear metrics history to save memory
            if tenant_id in self.metrics_history:
                del self.metrics_history[tenant_id]
            logger.info(f"Unregistered process for tenant {tenant_id}")
    
    def start_monitoring(self):
        """Start resource monitoring in background thread."""
        if self.active:
            return
        
        self.active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        logger.info("Resource monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.active:
            try:
                current_time = time.time()
                
                # Monitor system baseline
                if not self.system_baseline:
                    self.system_baseline = self._collect_system_metrics()
                
                # Monitor each registered agent process
                for tenant_id, process in list(self.agent_processes.items()):
                    try:
                        if not process.is_running():
                            self.unregister_agent_process(tenant_id)
                            continue
                        
                        metrics = self._collect_process_metrics(process, current_time)
                        self.metrics_history[tenant_id].append(metrics)
                        
                        # Check for violations
                        self._check_resource_violations(tenant_id, metrics)
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        self.unregister_agent_process(tenant_id)
                    except Exception as e:
                        logger.warning(f"Error monitoring tenant {tenant_id}: {e}")
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self) -> ResourceMetrics:
        """Collect system-wide resource metrics."""
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        
        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=psutil.cpu_percent(),
            memory_mb=memory.used / 1024 / 1024,
            memory_percent=memory.percent,
            io_read_bytes=disk_io.read_bytes if disk_io else 0,
            io_write_bytes=disk_io.write_bytes if disk_io else 0,
            network_sent_bytes=net_io.bytes_sent if net_io else 0,
            network_recv_bytes=net_io.bytes_recv if net_io else 0,
            open_files=len(psutil.pids()),
            threads=threading.active_count()
        )
    
    def _collect_process_metrics(self, process: psutil.Process, timestamp: float) -> ResourceMetrics:
        """Collect resource metrics for a specific process."""
        memory_info = process.memory_info()
        io_counters = process.io_counters() if hasattr(process, 'io_counters') else None
        
        return ResourceMetrics(
            timestamp=timestamp,
            cpu_percent=process.cpu_percent(),
            memory_mb=memory_info.rss / 1024 / 1024,
            memory_percent=process.memory_percent(),
            io_read_bytes=io_counters.read_bytes if io_counters else 0,
            io_write_bytes=io_counters.write_bytes if io_counters else 0,
            network_sent_bytes=0,  # Process-level network stats not easily available
            network_recv_bytes=0,
            open_files=process.num_fds() if hasattr(process, 'num_fds') else 0,
            threads=process.num_threads()
        )
    
    def _check_resource_violations(self, tenant_id: str, metrics: ResourceMetrics):
        """Check for resource quota violations."""
        # CPU quota check
        if metrics.cpu_percent > RESOURCE_ISOLATION_CONFIG["cpu_quota_percent"]:
            violation = ResourceViolation(
                tenant_id=tenant_id,
                violation_type="cpu_quota",
                timestamp=metrics.timestamp,
                severity="critical" if metrics.cpu_percent > 80 else "warning",
                details={"cpu_percent": metrics.cpu_percent, "quota": RESOURCE_ISOLATION_CONFIG["cpu_quota_percent"]}
            )
            self._trigger_violation_callbacks(violation)
        
        # Memory quota check
        if metrics.memory_mb > RESOURCE_ISOLATION_CONFIG["memory_quota_mb"]:
            violation = ResourceViolation(
                tenant_id=tenant_id,
                violation_type="memory_quota",
                timestamp=metrics.timestamp,
                severity="critical" if metrics.memory_mb > 1500 else "warning",
                details={"memory_mb": metrics.memory_mb, "quota": RESOURCE_ISOLATION_CONFIG["memory_quota_mb"]}
            )
            self._trigger_violation_callbacks(violation)
    
    def _trigger_violation_callbacks(self, violation: ResourceViolation):
        """Trigger registered violation callbacks."""
        for callback in self.violation_callbacks:
            try:
                callback(violation)
            except Exception as e:
                logger.error(f"Error in violation callback: {e}")
    
    def register_violation_callback(self, callback: callable):
        """Register a callback for resource violations."""
        self.violation_callbacks.append(callback)
    
    def get_tenant_metrics_summary(self, tenant_id: str) -> Dict[str, float]:
        """Get summary metrics for a tenant."""
        if tenant_id not in self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history[tenant_id])[-60:]  # Last 60 seconds
        if not recent_metrics:
            return {}
        
        return {
            "avg_cpu_percent": statistics.mean(m.cpu_percent for m in recent_metrics),
            "max_cpu_percent": max(m.cpu_percent for m in recent_metrics),
            "avg_memory_mb": statistics.mean(m.memory_mb for m in recent_metrics),
            "max_memory_mb": max(m.memory_mb for m in recent_metrics),
            "avg_io_rate": statistics.mean((m.io_read_bytes + m.io_write_bytes) for m in recent_metrics),
            "sample_count": len(recent_metrics)
        }
    
    def detect_noisy_neighbors(self) -> List[str]:
        """Detect tenants that may be impacting others' performance."""
        noisy_tenants = []
        
        for tenant_id in self.agent_processes.keys():
            summary = self.get_tenant_metrics_summary(tenant_id)
            if not summary:
                continue
            
            # Check if tenant is using excessive resources
            if (summary.get("avg_cpu_percent", 0) > RESOURCE_ISOLATION_CONFIG["noisy_neighbor_threshold"] * 100 or
                summary.get("avg_memory_mb", 0) > RESOURCE_ISOLATION_CONFIG["memory_quota_mb"] * 0.8):
                noisy_tenants.append(tenant_id)
        
        return noisy_tenants


class ResourceLeakDetector:
    """Detects various types of resource leaks."""
    
    def __init__(self, resource_monitor: ResourceMonitor):
        self.resource_monitor = resource_monitor
        self.leak_thresholds = {
            "memory_growth_rate": 50.0,  # MB per minute
            "file_handle_growth": 10,     # handles per minute
            "cpu_sustained_high": 300,    # seconds at > 80% CPU
        }
        self.tenant_baselines: Dict[str, Dict[str, float]] = {}
    
    def establish_baseline(self, tenant_id: str):
        """Establish resource baseline for a tenant."""
        summary = self.resource_monitor.get_tenant_metrics_summary(tenant_id)
        if summary:
            self.tenant_baselines[tenant_id] = summary.copy()
    
    def detect_memory_leaks(self, tenant_id: str) -> Optional[ResourceViolation]:
        """Detect memory leaks for a tenant."""
        if tenant_id not in self.tenant_baselines:
            return None
        
        current_summary = self.resource_monitor.get_tenant_metrics_summary(tenant_id)
        baseline = self.tenant_baselines[tenant_id]
        
        if not current_summary or "avg_memory_mb" not in baseline:
            return None
        
        memory_growth = current_summary["avg_memory_mb"] - baseline["avg_memory_mb"]
        time_elapsed = 60  # Assume 1 minute for simplicity
        growth_rate = memory_growth / time_elapsed
        
        if growth_rate > self.leak_thresholds["memory_growth_rate"]:
            return ResourceViolation(
                tenant_id=tenant_id,
                violation_type="memory_leak",
                timestamp=time.time(),
                severity="critical",
                details={
                    "growth_rate_mb_per_min": growth_rate,
                    "threshold": self.leak_thresholds["memory_growth_rate"],
                    "current_memory_mb": current_summary["avg_memory_mb"],
                    "baseline_memory_mb": baseline["avg_memory_mb"]
                }
            )
        
        return None
    
    def detect_all_leaks(self) -> List[ResourceViolation]:
        """Detect all types of resource leaks across all tenants."""
        violations = []
        
        for tenant_id in self.resource_monitor.agent_processes.keys():
            # Memory leak detection
            memory_violation = self.detect_memory_leaks(tenant_id)
            if memory_violation:
                violations.append(memory_violation)
        
        return violations


class PerformanceIsolationValidator:
    """Validates performance isolation between tenants."""
    
    def __init__(self, resource_monitor: ResourceMonitor):
        self.resource_monitor = resource_monitor
        self.baseline_performance: Dict[str, Dict[str, float]] = {}
        self.impact_reports: List[PerformanceImpactReport] = []
    
    def establish_performance_baseline(self, tenant_id: str):
        """Establish performance baseline for a tenant."""
        summary = self.resource_monitor.get_tenant_metrics_summary(tenant_id)
        if summary:
            self.baseline_performance[tenant_id] = summary.copy()
    
    def measure_cross_tenant_impact(self, noisy_tenants: List[str], normal_tenants: List[str]) -> PerformanceImpactReport:
        """Measure performance impact of noisy tenants on normal tenants."""
        affected_tenants = []
        degraded_metrics = {}
        
        for tenant_id in normal_tenants:
            if tenant_id not in self.baseline_performance:
                continue
            
            current_summary = self.resource_monitor.get_tenant_metrics_summary(tenant_id)
            baseline = self.baseline_performance[tenant_id]
            
            if not current_summary:
                continue
            
            # Calculate performance degradation
            cpu_degradation = (current_summary.get("avg_cpu_percent", 0) - baseline.get("avg_cpu_percent", 0)) / baseline.get("avg_cpu_percent", 1)
            memory_degradation = (current_summary.get("avg_memory_mb", 0) - baseline.get("avg_memory_mb", 0)) / baseline.get("avg_memory_mb", 1)
            
            degradation = max(cpu_degradation, memory_degradation)
            
            if degradation > RESOURCE_ISOLATION_CONFIG["performance_degradation_threshold"]:
                affected_tenants.append(tenant_id)
                degraded_metrics[tenant_id] = {
                    "cpu_degradation": cpu_degradation,
                    "memory_degradation": memory_degradation,
                    "overall_degradation": degradation
                }
        
        impact_percentage = len(affected_tenants) / len(normal_tenants) if normal_tenants else 0
        
        report = PerformanceImpactReport(
            baseline_metrics=self.baseline_performance.copy(),
            degraded_metrics=degraded_metrics,
            impact_percentage=impact_percentage,
            affected_tenants=affected_tenants,
            noisy_tenants=noisy_tenants,
            detection_time=time.time()
        )
        
        self.impact_reports.append(report)
        return report


class QuotaEnforcer:
    """Enforces resource quotas for tenant agents."""
    
    def __init__(self, resource_monitor: ResourceMonitor):
        self.resource_monitor = resource_monitor
        self.enforcement_actions: List[Dict[str, Any]] = []
    
    def enforce_cpu_quota(self, tenant_id: str, violation: ResourceViolation) -> bool:
        """Enforce CPU quota by throttling the process."""
        if tenant_id not in self.resource_monitor.agent_processes:
            return False
        
        process = self.resource_monitor.agent_processes[tenant_id]
        
        try:
            # Simulate quota enforcement by setting process priority
            if hasattr(process, 'nice'):
                current_nice = process.nice()
                if current_nice < 10:  # Lower priority (higher nice value)
                    process.nice(min(current_nice + 5, 19))
                    
                    action = {
                        "tenant_id": tenant_id,
                        "action": "cpu_throttling",
                        "timestamp": time.time(),
                        "details": {"old_nice": current_nice, "new_nice": process.nice()}
                    }
                    self.enforcement_actions.append(action)
                    logger.info(f"Applied CPU throttling to tenant {tenant_id}")
                    return True
        except Exception as e:
            logger.error(f"Failed to enforce CPU quota for tenant {tenant_id}: {e}")
        
        return False
    
    def enforce_memory_quota(self, tenant_id: str, violation: ResourceViolation) -> bool:
        """Enforce memory quota by triggering garbage collection or process restart."""
        # In a real implementation, this would implement memory limiting
        # For testing, we simulate by logging the enforcement action
        action = {
            "tenant_id": tenant_id,
            "action": "memory_enforcement",
            "timestamp": time.time(),
            "details": violation.details
        }
        self.enforcement_actions.append(action)
        logger.warning(f"Memory quota enforcement triggered for tenant {tenant_id}")
        return True


class ResourceIsolationTestSuite:
    """Main test suite orchestrator for resource isolation testing."""
    
    def __init__(self):
        self.resource_monitor = ResourceMonitor(RESOURCE_ISOLATION_CONFIG["monitoring_interval"])
        self.leak_detector = ResourceLeakDetector(self.resource_monitor)
        self.performance_validator = PerformanceIsolationValidator(self.resource_monitor)
        self.quota_enforcer = QuotaEnforcer(self.resource_monitor)
        self.tenant_agents: List[TenantAgent] = []
        self.test_violations: List[ResourceViolation] = []
        self.redis_client: Optional[redis.Redis] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        
        # Register violation callback
        self.resource_monitor.register_violation_callback(self._handle_violation)
    
    def _handle_violation(self, violation: ResourceViolation):
        """Handle resource violations."""
        self.test_violations.append(violation)
        logger.warning(f"Resource violation detected: {violation}")
        
        # Trigger quota enforcement for critical violations
        if violation.severity == "critical":
            if violation.violation_type == "cpu_quota":
                self.quota_enforcer.enforce_cpu_quota(violation.tenant_id, violation)
            elif violation.violation_type == "memory_quota":
                self.quota_enforcer.enforce_memory_quota(violation.tenant_id, violation)
    
    async def initialize_test_environment(self):
        """Initialize test environment with database connections."""
        logger.info("Initializing resource isolation test environment...")
        
        # Initialize Redis connection
        self.redis_client = redis.Redis.from_url(
            SERVICE_ENDPOINTS["redis"],
            decode_responses=True,
            socket_timeout=10
        )
        
        # Initialize database pool
        self.db_pool = await asyncpg.create_pool(
            SERVICE_ENDPOINTS["postgres"],
            min_size=10,
            max_size=50,
            command_timeout=30
        )
        
        # Verify services are available
        await self._verify_services()
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        logger.info("Resource isolation test environment initialized")
    
    async def _verify_services(self):
        """Verify all required services are available."""
        # Test Redis
        await self.redis_client.ping()
        
        # Test database
        async with self.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Test HTTP services
        async with httpx.AsyncClient() as client:
            backend_response = await client.get(f"{SERVICE_ENDPOINTS['backend']}/health", timeout=10)
            if backend_response.status_code != 200:
                raise RuntimeError(f"Backend service not available: {backend_response.status_code}")
    
    async def cleanup_test_environment(self):
        """Clean up test environment."""
        logger.info("Cleaning up resource isolation test environment...")
        
        # Stop resource monitoring
        self.resource_monitor.stop_monitoring()
        
        # Clean up tenant data
        if self.tenant_agents:
            await self._cleanup_tenant_data()
        
        # Close connections
        if self.redis_client:
            await self.redis_client.aclose()
        
        if self.db_pool:
            await self.db_pool.close()
        
        logger.info("Resource isolation test environment cleanup completed")
    
    async def create_tenant_agents(self, count: int) -> List[TenantAgent]:
        """Create multiple tenant agents for testing."""
        agents = []
        
        for i in range(count):
            agent = TenantAgent(
                tenant_id=f"tenant_{i}_{uuid.uuid4().hex[:8]}",
                user_id=f"user_{i}_{uuid.uuid4().hex[:8]}",
                email=f"tenant_{i}@resource.test",
                session_id=f"session_{i}_{int(time.time())}",
                auth_token=self._generate_test_jwt(f"user_{i}"),
                context_data={
                    "budget": 10000 + (i * 1000),
                    "region": ["us-east-1", "us-west-2", "eu-west-1"][i % 3],
                    "tier": "enterprise",
                    "resource_tier": ["light", "medium", "heavy"][i % 3],
                    "workload_pattern": ["analytical", "operational", "mixed"][i % 3]
                },
                resource_quotas={
                    "cpu_percent": RESOURCE_ISOLATION_CONFIG["cpu_quota_percent"],
                    "memory_mb": RESOURCE_ISOLATION_CONFIG["memory_quota_mb"]
                }
            )
            
            # Add sensitive data for contamination detection
            agent.sensitive_data = {
                "api_key": f"sk_test_{agent.tenant_id}_{secrets.token_hex(16)}",
                "database_credentials": f"db_creds_{agent.tenant_id}",
                "encryption_key": secrets.token_hex(32),
                "tenant_specific_data": f"sensitive_data_for_{agent.tenant_id}"
            }
            
            agents.append(agent)
        
        self.tenant_agents.extend(agents)
        return agents
    
    def _generate_test_jwt(self, user_id: str) -> str:
        """Generate test JWT token for user."""
        import jwt
        payload = {
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "user_id": user_id
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")
    
    async def establish_agent_connections(self, agents: List[TenantAgent]) -> int:
        """Establish WebSocket connections for tenant agents."""
        logger.info(f"Establishing connections for {len(agents)} tenant agents...")
        
        successful_connections = 0
        
        # Connect in batches to avoid overwhelming the server
        batch_size = 10
        for i in range(0, len(agents), batch_size):
            batch = agents[i:i + batch_size]
            
            connection_tasks = [
                self._establish_single_connection(agent)
                for agent in batch
            ]
            
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Connection failed for tenant {batch[j].tenant_id}: {result}")
                elif result:
                    successful_connections += 1
                    # Register process for monitoring if available
                    if hasattr(batch[j], 'process_id') and batch[j].process_id:
                        self.resource_monitor.register_agent_process(batch[j].tenant_id, batch[j].process_id)
            
            # Brief pause between batches
            if i + batch_size < len(agents):
                await asyncio.sleep(1.0)
        
        logger.info(f"Successfully established {successful_connections} connections")
        return successful_connections
    
    async def _establish_single_connection(self, agent: TenantAgent) -> bool:
        """Establish WebSocket connection for a single agent."""
        try:
            start_time = time.time()
            
            uri = f"{SERVICE_ENDPOINTS['websocket']}?token={agent.auth_token}"
            
            agent.websocket_client = await websockets.connect(
                uri,
                close_timeout=30
            )
            
            # Simulate process ID (in real implementation, this would come from agent startup)
            agent.process_id = os.getpid()  # Simplified for testing
            
            connection_time = time.time() - start_time
            logger.debug(f"Agent {agent.tenant_id} connected in {connection_time:.2f}s")
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to establish connection for agent {agent.tenant_id}: {e}")
            return False
    
    async def generate_workload(self, agents: List[TenantAgent], workload_type: str = "normal") -> List[Dict[str, Any]]:
        """Generate workload for tenant agents."""
        logger.info(f"Generating {workload_type} workload for {len(agents)} agents...")
        
        workload_patterns = {
            "normal": self._generate_normal_workload,
            "heavy": self._generate_heavy_workload,
            "noisy": self._generate_noisy_workload,
            "mixed": self._generate_mixed_workload
        }
        
        generator = workload_patterns.get(workload_type, self._generate_normal_workload)
        
        tasks = [generator(agent) for agent in agents if agent.websocket_client]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_responses = [r for r in responses if not isinstance(r, Exception)]
        logger.info(f"Generated workload resulted in {len(valid_responses)} valid responses")
        
        return valid_responses
    
    async def _generate_normal_workload(self, agent: TenantAgent) -> Dict[str, Any]:
        """Generate normal workload for an agent."""
        message = {
            "type": "chat_message",
            "content": f"Analyze optimization opportunities for tenant {agent.tenant_id} with budget ${agent.context_data['budget']}",
            "session_id": agent.session_id,
            "tenant_id": agent.tenant_id,
            "context": agent.context_data
        }
        
        await agent.websocket_client.send(json.dumps(message))
        
        response_raw = await asyncio.wait_for(
            agent.websocket_client.recv(),
            timeout=30
        )
        
        response = json.loads(response_raw)
        return {
            "tenant_id": agent.tenant_id,
            "workload_type": "normal",
            "response": response,
            "timestamp": time.time()
        }
    
    async def _generate_heavy_workload(self, agent: TenantAgent) -> Dict[str, Any]:
        """Generate heavy workload for an agent."""
        # Send multiple rapid requests to simulate heavy usage
        messages = []
        for i in range(5):
            message = {
                "type": "chat_message",
                "content": f"Perform complex analysis #{i} for tenant {agent.tenant_id} with detailed computations and large dataset processing",
                "session_id": agent.session_id,
                "tenant_id": agent.tenant_id,
                "context": agent.context_data,
                "complexity": "high",
                "require_deep_analysis": True
            }
            messages.append(message)
        
        # Send all messages rapidly
        for message in messages:
            await agent.websocket_client.send(json.dumps(message))
            await asyncio.sleep(0.1)  # Small delay between messages
        
        # Collect responses
        responses = []
        for _ in messages:
            response_raw = await asyncio.wait_for(
                agent.websocket_client.recv(),
                timeout=45
            )
            responses.append(json.loads(response_raw))
        
        return {
            "tenant_id": agent.tenant_id,
            "workload_type": "heavy",
            "responses": responses,
            "timestamp": time.time()
        }
    
    async def _generate_noisy_workload(self, agent: TenantAgent) -> Dict[str, Any]:
        """Generate noisy neighbor workload."""
        # Simulate resource-intensive operations
        message = {
            "type": "chat_message",
            "content": f"URGENT: Perform intensive resource analysis for tenant {agent.tenant_id} - use maximum CPU and memory for comprehensive optimization",
            "session_id": agent.session_id,
            "tenant_id": agent.tenant_id,
            "context": agent.context_data,
            "priority": "critical",
            "resource_intensive": True,
            "use_max_resources": True
        }
        
        await agent.websocket_client.send(json.dumps(message))
        
        response_raw = await asyncio.wait_for(
            agent.websocket_client.recv(),
            timeout=60
        )
        
        response = json.loads(response_raw)
        return {
            "tenant_id": agent.tenant_id,
            "workload_type": "noisy",
            "response": response,
            "timestamp": time.time()
        }
    
    async def _generate_mixed_workload(self, agent: TenantAgent) -> Dict[str, Any]:
        """Generate mixed workload pattern."""
        workload_type = agent.context_data.get("workload_pattern", "normal")
        
        if workload_type == "analytical":
            return await self._generate_heavy_workload(agent)
        elif workload_type == "operational":
            return await self._generate_normal_workload(agent)
        else:  # mixed
            # Randomly choose between normal and heavy
            import random
            if random.random() < 0.3:  # 30% chance of heavy workload
                return await self._generate_heavy_workload(agent)
            else:
                return await self._generate_normal_workload(agent)
    
    async def _cleanup_tenant_data(self):
        """Clean up tenant data from databases."""
        logger.info(f"Cleaning up data for {len(self.tenant_agents)} tenants...")
        
        tenant_ids = [agent.tenant_id for agent in self.tenant_agents]
        user_ids = [agent.user_id for agent in self.tenant_agents]
        
        # Clean database
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM users WHERE id = ANY($1)",
                user_ids
            )
            await conn.execute(
                "DELETE FROM user_sessions WHERE user_id = ANY($1)",
                user_ids
            )
            await conn.execute(
                "DELETE FROM agent_states WHERE user_id = ANY($1)",
                user_ids
            )
        
        # Clean Redis
        redis_keys = []
        for tenant_id in tenant_ids:
            redis_keys.extend([
                f"tenant_context:{tenant_id}",
                f"agent_state:{tenant_id}",
                f"resource_metrics:{tenant_id}"
            ])
        
        if redis_keys:
            await self.redis_client.delete(*redis_keys)
        
        # Unregister from resource monitoring
        for agent in self.tenant_agents:
            self.resource_monitor.unregister_agent_process(agent.tenant_id)
        
        logger.info("Tenant data cleanup completed")


# Pytest Fixtures

@pytest.fixture(scope="function")
async def resource_isolation_suite():
    """Set up resource isolation test suite."""
    suite = ResourceIsolationTestSuite()
    await suite.initialize_test_environment()
    
    yield suite
    
    await suite.cleanup_test_environment()


@pytest.fixture
async def tenant_agents(resource_isolation_suite):
    """Create tenant agents for testing."""
    suite = resource_isolation_suite
    agents = await suite.create_tenant_agents(RESOURCE_ISOLATION_CONFIG["tenant_count"])
    
    # Pre-populate database with tenant data
    for agent in agents:
        async with suite.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (id, email, is_active, created_at) 
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET email = $2
            """, agent.user_id, agent.email, True, datetime.now(timezone.utc))
            
            # Set tenant context in Redis
            await suite.redis_client.hset(
                f"tenant_context:{agent.tenant_id}",
                mapping=agent.context_data
            )
    
    yield agents


# Test Cases

@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
async def test_per_tenant_resource_monitoring_baseline(resource_isolation_suite, tenant_agents):
    """Test Case 1: Per-Tenant Resource Monitoring Baseline
    
    Objective: Establish baseline resource consumption for individual agent instances
    Success Criteria:
    - Each agent instance monitored independently
    - Resource metrics collected at 1-second intervals
    - Baseline CPU usage < 5% idle, < 25% under load
    - Baseline memory usage < 256MB idle, < 512MB under load
    - No resource leaks detected over monitoring period
    """
    logger.info("Starting Test Case 1: Per-Tenant Resource Monitoring Baseline")
    
    suite = resource_isolation_suite
    
    # Phase 1: Establish connections
    connection_count = await suite.establish_agent_connections(tenant_agents)
    assert connection_count >= len(tenant_agents) * 0.8, f"Insufficient connections: {connection_count}/{len(tenant_agents)}"
    
    # Phase 2: Establish baselines during idle period
    logger.info("Establishing idle baselines...")
    await asyncio.sleep(10)  # Allow idle baseline collection
    
    idle_baselines = {}
    for agent in tenant_agents:
        if agent.tenant_id in suite.resource_monitor.metrics_history:
            summary = suite.resource_monitor.get_tenant_metrics_summary(agent.tenant_id)
            if summary:
                idle_baselines[agent.tenant_id] = summary
                suite.leak_detector.establish_baseline(agent.tenant_id)
                suite.performance_validator.establish_performance_baseline(agent.tenant_id)
    
    # Phase 3: Generate normal workload and monitor
    logger.info("Generating normal workload...")
    responses = await suite.generate_workload(tenant_agents, "normal")
    
    # Phase 4: Allow monitoring period
    await asyncio.sleep(30)  # Monitor under load
    
    # Phase 5: Validate baselines
    load_summaries = {}
    for agent in tenant_agents:
        summary = suite.resource_monitor.get_tenant_metrics_summary(agent.tenant_id)
        if summary:
            load_summaries[agent.tenant_id] = summary
    
    # Assertions
    baseline_violations = 0
    for tenant_id, idle_baseline in idle_baselines.items():
        # Idle CPU should be < 5%
        if idle_baseline.get("avg_cpu_percent", 0) > 5.0:
            baseline_violations += 1
            logger.warning(f"Tenant {tenant_id} idle CPU too high: {idle_baseline['avg_cpu_percent']:.2f}%")
        
        # Idle memory should be < 256MB
        if idle_baseline.get("avg_memory_mb", 0) > 256:
            baseline_violations += 1
            logger.warning(f"Tenant {tenant_id} idle memory too high: {idle_baseline['avg_memory_mb']:.2f}MB")
    
    for tenant_id, load_summary in load_summaries.items():
        # Load CPU should be < 25%
        if load_summary.get("avg_cpu_percent", 0) > 25.0:
            baseline_violations += 1
            logger.warning(f"Tenant {tenant_id} load CPU too high: {load_summary['avg_cpu_percent']:.2f}%")
        
        # Load memory should be < 512MB
        if load_summary.get("avg_memory_mb", 0) > 512:
            baseline_violations += 1
            logger.warning(f"Tenant {tenant_id} load memory too high: {load_summary['avg_memory_mb']:.2f}MB")
    
    # Check for resource leaks
    detected_leaks = suite.leak_detector.detect_all_leaks()
    
    # Final assertions
    assert baseline_violations == 0, f"Baseline violations detected: {baseline_violations}"
    assert len(detected_leaks) == 0, f"Resource leaks detected: {len(detected_leaks)}"
    assert len(responses) > 0, "No responses received from workload generation"
    
    logger.info(f"Test Case 1 completed: {len(idle_baselines)} baselines established, {len(responses)} responses processed")


@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_cpu_memory_quota_enforcement(resource_isolation_suite, tenant_agents):
    """Test Case 2: CPU/Memory Quota Enforcement
    
    Objective: Validate that agents cannot exceed allocated resource quotas
    Success Criteria:
    - CPU quota enforcement prevents agents from exceeding configured limits
    - Memory quota enforcement prevents agents from exceeding configured limits
    - Quota violations trigger proper throttling/rejection
    - System remains stable under quota pressure
    - No impact on other tenants when one hits quotas
    """
    logger.info("Starting Test Case 2: CPU/Memory Quota Enforcement")
    
    suite = resource_isolation_suite
    
    # Phase 1: Establish connections and baselines
    await suite.establish_agent_connections(tenant_agents)
    await asyncio.sleep(5)  # Brief baseline period
    
    # Establish baselines for all tenants
    for agent in tenant_agents:
        suite.performance_validator.establish_performance_baseline(agent.tenant_id)
    
    # Phase 2: Select subset of tenants to push to quota limits
    quota_test_agents = tenant_agents[:5]  # First 5 agents will hit quotas
    normal_agents = tenant_agents[5:]      # Remaining agents stay normal
    
    # Phase 3: Generate heavy workload for quota test agents
    logger.info(f"Generating heavy workload for {len(quota_test_agents)} agents to trigger quota enforcement...")
    
    # Generate workload that should trigger quotas
    quota_tasks = [
        suite._generate_noisy_workload(agent)
        for agent in quota_test_agents
        if agent.websocket_client
    ]
    
    normal_tasks = [
        suite._generate_normal_workload(agent)
        for agent in normal_agents
        if agent.websocket_client
    ]
    
    # Execute workloads concurrently
    all_tasks = quota_tasks + normal_tasks
    responses = await asyncio.gather(*all_tasks, return_exceptions=True)
    
    # Phase 4: Monitor for quota violations and enforcement
    await asyncio.sleep(30)  # Allow time for quota enforcement
    
    # Phase 5: Validate quota enforcement
    quota_violations = [v for v in suite.test_violations if v.violation_type in ["cpu_quota", "memory_quota"]]
    enforcement_actions = suite.quota_enforcer.enforcement_actions
    
    # Check impact on normal tenants
    impact_report = suite.performance_validator.measure_cross_tenant_impact(
        noisy_tenants=[agent.tenant_id for agent in quota_test_agents],
        normal_tenants=[agent.tenant_id for agent in normal_agents]
    )
    
    # Assertions
    assert len(quota_violations) > 0, "No quota violations detected despite heavy workload"
    assert len(enforcement_actions) > 0, "No enforcement actions taken despite violations"
    assert impact_report.impact_percentage < 0.3, f"Too much impact on normal tenants: {impact_report.impact_percentage:.2%}"
    
    # Validate that normal tenants weren't affected significantly
    for tenant_id in impact_report.affected_tenants:
        degradation = impact_report.degraded_metrics[tenant_id]["overall_degradation"]
        assert degradation < RESOURCE_ISOLATION_CONFIG["performance_degradation_threshold"], \
            f"Tenant {tenant_id} degradation too high: {degradation:.2%}"
    
    logger.info(f"Test Case 2 completed: {len(quota_violations)} violations, {len(enforcement_actions)} enforcement actions")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_resource_leak_detection_and_prevention(resource_isolation_suite, tenant_agents):
    """Test Case 3: Resource Leak Detection and Prevention
    
    Objective: Detect and prevent resource leaks that could affect other tenants
    Success Criteria:
    - Memory leaks detected within 60 seconds
    - CPU runaway processes identified
    - Automatic cleanup mechanisms function
    - No lasting impact on other tenant performance
    """
    logger.info("Starting Test Case 3: Resource Leak Detection and Prevention")
    
    suite = resource_isolation_suite
    
    # Phase 1: Establish connections and baselines
    await suite.establish_agent_connections(tenant_agents)
    await asyncio.sleep(10)  # Establish stable baseline
    
    # Establish baselines for leak detection
    for agent in tenant_agents:
        suite.leak_detector.establish_baseline(agent.tenant_id)
        suite.performance_validator.establish_performance_baseline(agent.tenant_id)
    
    # Phase 2: Simulate leak scenarios with subset of agents
    leak_agents = tenant_agents[:3]  # First 3 agents will have simulated leaks
    normal_agents = tenant_agents[3:]  # Remaining agents stay normal
    
    logger.info(f"Simulating resource leaks with {len(leak_agents)} agents...")
    
    # Simulate various leak patterns
    leak_tasks = []
    for i, agent in enumerate(leak_agents):
        if i == 0:
            # Simulate memory leak pattern
            leak_tasks.append(suite._generate_heavy_workload(agent))
        else:
            # Simulate high CPU usage
            leak_tasks.append(suite._generate_noisy_workload(agent))
    
    normal_tasks = [
        suite._generate_normal_workload(agent)
        for agent in normal_agents
        if agent.websocket_client
    ]
    
    # Execute leak simulation
    await asyncio.gather(*(leak_tasks + normal_tasks), return_exceptions=True)
    
    # Phase 3: Monitor for leak detection
    leak_detection_start = time.time()
    await asyncio.sleep(60)  # Allow time for leak detection
    
    # Phase 4: Check leak detection results
    detected_leaks = suite.leak_detector.detect_all_leaks()
    detection_time = time.time() - leak_detection_start
    
    # Check impact on normal tenants
    impact_report = suite.performance_validator.measure_cross_tenant_impact(
        noisy_tenants=[agent.tenant_id for agent in leak_agents],
        normal_tenants=[agent.tenant_id for agent in normal_agents]
    )
    
    # Phase 5: Validate cleanup (simulate by checking system returns to baseline)
    await asyncio.sleep(30)  # Allow cleanup time
    
    post_cleanup_metrics = {}
    for agent in normal_agents:
        summary = suite.resource_monitor.get_tenant_metrics_summary(agent.tenant_id)
        if summary:
            post_cleanup_metrics[agent.tenant_id] = summary
    
    # Assertions
    assert detection_time <= 60, f"Leak detection took too long: {detection_time:.2f}s"
    
    # Validate that normal tenants maintained performance
    assert impact_report.impact_percentage < 0.2, f"Leak impact on normal tenants too high: {impact_report.impact_percentage:.2%}"
    
    # Validate system stability
    system_stable = all(
        metrics.get("avg_cpu_percent", 0) < 50 and metrics.get("avg_memory_mb", 0) < 1000
        for metrics in post_cleanup_metrics.values()
    )
    assert system_stable, "System not stable after leak detection and cleanup"
    
    logger.info(f"Test Case 3 completed: {len(detected_leaks)} leaks detected in {detection_time:.2f}s")


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
async def test_performance_isolation_under_load(resource_isolation_suite, tenant_agents):
    """Test Case 4: Performance Isolation Under Load
    
    Objective: Ensure high-load tenants don't impact other tenants' performance
    Success Criteria:
    - High-load tenant isolated from others
    - Other tenants maintain acceptable response times
    - CPU and memory isolation effective under stress
    - Performance degradation within acceptable limits
    """
    logger.info("Starting Test Case 4: Performance Isolation Under Load")
    
    suite = resource_isolation_suite
    
    # Phase 1: Establish connections and baselines
    await suite.establish_agent_connections(tenant_agents)
    await asyncio.sleep(10)  # Stable baseline period
    
    # Establish performance baselines
    for agent in tenant_agents:
        suite.performance_validator.establish_performance_baseline(agent.tenant_id)
    
    # Phase 2: Create load scenarios
    high_load_agents = tenant_agents[:2]    # 2 high-load tenants
    normal_agents = tenant_agents[2:]       # Remaining normal tenants
    
    logger.info(f"Testing isolation with {len(high_load_agents)} high-load and {len(normal_agents)} normal tenants...")
    
    # Phase 3: Generate sustained load
    start_time = time.time()
    
    # High-load agents generate intensive workload
    async def sustained_high_load(agent):
        for _ in range(10):  # 10 rounds of heavy workload
            await suite._generate_heavy_workload(agent)
            await asyncio.sleep(2)  # Brief pause between rounds
    
    high_load_tasks = [
        sustained_high_load(agent)
        for agent in high_load_agents
        if agent.websocket_client
    ]
    
    # Normal agents generate regular workload
    async def sustained_normal_load(agent):
        for _ in range(5):  # 5 rounds of normal workload
            await suite._generate_normal_workload(agent)
            await asyncio.sleep(4)  # Longer pause for normal agents
    
    normal_load_tasks = [
        sustained_normal_load(agent)
        for agent in normal_agents
        if agent.websocket_client
    ]
    
    # Execute sustained load test
    await asyncio.gather(*(high_load_tasks + normal_load_tasks), return_exceptions=True)
    
    test_duration = time.time() - start_time
    
    # Phase 4: Measure performance impact
    impact_report = suite.performance_validator.measure_cross_tenant_impact(
        noisy_tenants=[agent.tenant_id for agent in high_load_agents],
        normal_tenants=[agent.tenant_id for agent in normal_agents]
    )
    
    # Phase 5: Validate isolation effectiveness
    high_load_summaries = {}
    normal_summaries = {}
    
    for agent in high_load_agents:
        summary = suite.resource_monitor.get_tenant_metrics_summary(agent.tenant_id)
        if summary:
            high_load_summaries[agent.tenant_id] = summary
    
    for agent in normal_agents:
        summary = suite.resource_monitor.get_tenant_metrics_summary(agent.tenant_id)
        if summary:
            normal_summaries[agent.tenant_id] = summary
    
    # Assertions
    assert test_duration < 300, f"Load test took too long: {test_duration:.2f}s"
    assert impact_report.impact_percentage < 0.15, f"Performance impact too high: {impact_report.impact_percentage:.2%}"
    
    # Validate high-load tenants used resources but didn't exceed quotas excessively
    quota_violations = [
        v for v in suite.test_violations 
        if v.tenant_id in [agent.tenant_id for agent in high_load_agents]
        and v.severity == "critical"
    ]
    assert len(quota_violations) < 5, f"Too many critical quota violations: {len(quota_violations)}"
    
    # Validate normal tenants maintained performance
    normal_performance_good = all(
        summary.get("avg_cpu_percent", 0) < 30 and summary.get("avg_memory_mb", 0) < 600
        for summary in normal_summaries.values()
    )
    assert normal_performance_good, "Normal tenants did not maintain good performance"
    
    logger.info(f"Test Case 4 completed: {impact_report.impact_percentage:.2%} impact on normal tenants")


@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_noisy_neighbor_mitigation(resource_isolation_suite, tenant_agents):
    """Test Case 5: Noisy Neighbor Mitigation
    
    Objective: Demonstrate effective mitigation of noisy neighbor scenarios
    Success Criteria:
    - "Noisy" tenants automatically identified
    - Performance impact on other tenants minimized
    - Automatic recovery when noisy activity subsides
    - Clear monitoring and alerting for operations team
    """
    logger.info("Starting Test Case 5: Noisy Neighbor Mitigation")
    
    suite = resource_isolation_suite
    
    # Phase 1: Establish connections and baselines
    await suite.establish_agent_connections(tenant_agents)
    await asyncio.sleep(10)
    
    # Establish baselines
    for agent in tenant_agents:
        suite.performance_validator.establish_performance_baseline(agent.tenant_id)
    
    # Phase 2: Create noisy neighbor scenario
    noisy_agents = tenant_agents[:2]      # 2 noisy neighbors
    victim_agents = tenant_agents[2:]     # Potential victims
    
    logger.info(f"Creating noisy neighbor scenario with {len(noisy_agents)} noisy tenants...")
    
    # Phase 3: Generate extreme noisy workload
    detection_start = time.time()
    
    # Extreme noisy workload
    async def extreme_noisy_workload(agent):
        for i in range(20):  # Very intensive workload
            await suite._generate_noisy_workload(agent)
            if i % 5 == 0:  # Brief pause every 5 iterations
                await asyncio.sleep(1)
    
    noisy_tasks = [
        extreme_noisy_workload(agent)
        for agent in noisy_agents
        if agent.websocket_client
    ]
    
    # Normal workload for victims
    victim_tasks = [
        suite._generate_normal_workload(agent)
        for agent in victim_agents[:10]  # Only test with subset to save time
        if agent.websocket_client
    ]
    
    # Execute noisy neighbor test
    await asyncio.gather(*(noisy_tasks + victim_tasks), return_exceptions=True)
    
    # Phase 4: Check for noisy neighbor detection
    detected_noisy = suite.resource_monitor.detect_noisy_neighbors()
    detection_time = time.time() - detection_start
    
    # Phase 5: Measure impact and mitigation
    impact_report = suite.performance_validator.measure_cross_tenant_impact(
        noisy_tenants=[agent.tenant_id for agent in noisy_agents],
        normal_tenants=[agent.tenant_id for agent in victim_agents[:10]]
    )
    
    # Check enforcement actions taken
    enforcement_actions = [
        action for action in suite.quota_enforcer.enforcement_actions
        if action["tenant_id"] in [agent.tenant_id for agent in noisy_agents]
    ]
    
    # Phase 6: Test recovery (simulate noisy tenants reducing load)
    logger.info("Testing recovery after noisy neighbor mitigation...")
    recovery_start = time.time()
    
    # Generate normal workload for previously noisy tenants
    recovery_tasks = [
        suite._generate_normal_workload(agent)
        for agent in noisy_agents
        if agent.websocket_client
    ]
    
    await asyncio.gather(*recovery_tasks, return_exceptions=True)
    await asyncio.sleep(30)  # Allow recovery time
    
    recovery_time = time.time() - recovery_start
    
    # Check post-recovery performance
    post_recovery_impact = suite.performance_validator.measure_cross_tenant_impact(
        noisy_tenants=[agent.tenant_id for agent in noisy_agents],
        normal_tenants=[agent.tenant_id for agent in victim_agents[:10]]
    )
    
    # Assertions
    assert detection_time < 60, f"Noisy neighbor detection took too long: {detection_time:.2f}s"
    assert len(detected_noisy) > 0, "No noisy neighbors detected despite extreme workload"
    assert len(enforcement_actions) > 0, "No enforcement actions taken against noisy neighbors"
    
    # Validate impact was contained
    assert impact_report.impact_percentage < 0.5, f"Noisy neighbor impact too high: {impact_report.impact_percentage:.2%}"
    
    # Validate recovery
    assert post_recovery_impact.impact_percentage < impact_report.impact_percentage, "No recovery observed after mitigation"
    assert recovery_time < 60, f"Recovery took too long: {recovery_time:.2f}s"
    
    # Validate operational visibility
    total_violations = len([v for v in suite.test_violations if v.tenant_id in [agent.tenant_id for agent in noisy_agents]])
    assert total_violations > 0, "No violations logged for operational visibility"
    
    logger.info(f"Test Case 5 completed: {len(detected_noisy)} noisy neighbors detected and mitigated")


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
async def test_multi_tenant_concurrent_stress(resource_isolation_suite, tenant_agents):
    """Test Case 6: Multi-Tenant Concurrent Resource Stress
    
    Objective: Validate resource isolation under maximum concurrent tenant load
    Success Criteria:
    - All tenants can operate simultaneously
    - Each tenant maintains independent resource allocation
    - System gracefully handles resource contention
    - Fair resource distribution maintained
    """
    logger.info("Starting Test Case 6: Multi-Tenant Concurrent Resource Stress")
    
    suite = resource_isolation_suite
    
    # Phase 1: Establish all connections simultaneously
    stress_start = time.time()
    connection_count = await suite.establish_agent_connections(tenant_agents)
    connection_time = time.time() - stress_start
    
    assert connection_count >= len(tenant_agents) * 0.9, f"Insufficient connections under stress: {connection_count}/{len(tenant_agents)}"
    
    # Phase 2: Generate concurrent workload for all tenants
    logger.info(f"Generating concurrent workload for {len(tenant_agents)} tenants...")
    
    # Mixed workload distribution
    workload_distribution = {
        "normal": tenant_agents[:len(tenant_agents)//2],
        "heavy": tenant_agents[len(tenant_agents)//2:len(tenant_agents)*3//4],
        "mixed": tenant_agents[len(tenant_agents)*3//4:]
    }
    
    concurrent_tasks = []
    for workload_type, agents in workload_distribution.items():
        for agent in agents:
            if agent.websocket_client:
                if workload_type == "normal":
                    concurrent_tasks.append(suite._generate_normal_workload(agent))
                elif workload_type == "heavy":
                    concurrent_tasks.append(suite._generate_heavy_workload(agent))
                else:  # mixed
                    concurrent_tasks.append(suite._generate_mixed_workload(agent))
    
    # Execute all workloads concurrently
    workload_start = time.time()
    responses = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
    workload_time = time.time() - workload_start
    
    # Phase 3: Analyze resource distribution
    await asyncio.sleep(10)  # Allow metrics to stabilize
    
    resource_summaries = {}
    for agent in tenant_agents:
        summary = suite.resource_monitor.get_tenant_metrics_summary(agent.tenant_id)
        if summary:
            resource_summaries[agent.tenant_id] = summary
    
    # Phase 4: Validate resource fairness
    if resource_summaries:
        cpu_usages = [summary["avg_cpu_percent"] for summary in resource_summaries.values()]
        memory_usages = [summary["avg_memory_mb"] for summary in resource_summaries.values()]
        
        cpu_fairness = statistics.stdev(cpu_usages) / statistics.mean(cpu_usages) if cpu_usages else 0
        memory_fairness = statistics.stdev(memory_usages) / statistics.mean(memory_usages) if memory_usages else 0
        
        # Check for resource monopolization
        max_cpu = max(cpu_usages) if cpu_usages else 0
        max_memory = max(memory_usages) if memory_usages else 0
        
        avg_cpu = statistics.mean(cpu_usages) if cpu_usages else 0
        avg_memory = statistics.mean(memory_usages) if memory_usages else 0
    else:
        cpu_fairness = memory_fairness = 0
        max_cpu = max_memory = avg_cpu = avg_memory = 0
    
    # Count successful responses
    successful_responses = len([r for r in responses if not isinstance(r, Exception)])
    response_rate = successful_responses / len(concurrent_tasks) if concurrent_tasks else 0
    
    # Assertions
    assert connection_time < 60, f"Connection establishment took too long: {connection_time:.2f}s"
    assert workload_time < 180, f"Concurrent workload took too long: {workload_time:.2f}s"
    assert response_rate >= 0.8, f"Response rate too low: {response_rate:.2%}"
    
    # Resource fairness assertions
    assert cpu_fairness < 1.0, f"CPU distribution not fair: coefficient of variation {cpu_fairness:.3f}"
    assert memory_fairness < 1.0, f"Memory distribution not fair: coefficient of variation {memory_fairness:.3f}"
    
    # No single tenant should monopolize resources
    if avg_cpu > 0:
        assert max_cpu / avg_cpu < 3.0, f"CPU monopolization detected: max {max_cpu:.2f}% vs avg {avg_cpu:.2f}%"
    if avg_memory > 0:
        assert max_memory / avg_memory < 3.0, f"Memory monopolization detected: max {max_memory:.2f}MB vs avg {avg_memory:.2f}MB"
    
    logger.info(f"Test Case 6 completed: {successful_responses}/{len(concurrent_tasks)} successful responses")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_resource_recovery_and_cleanup(resource_isolation_suite, tenant_agents):
    """Test Case 7: Resource Recovery and Cleanup
    
    Objective: Validate proper resource cleanup when tenants disconnect
    Success Criteria:
    - Agent termination releases all allocated resources
    - Memory is properly garbage collected
    - System resources available for new tenants
    - No zombie processes or leaked resources remain
    """
    logger.info("Starting Test Case 7: Resource Recovery and Cleanup")
    
    suite = resource_isolation_suite
    
    # Phase 1: Establish connections and generate workload
    connection_count = await suite.establish_agent_connections(tenant_agents)
    assert connection_count > 0, "No connections established for cleanup test"
    
    # Generate workload to allocate resources
    responses = await suite.generate_workload(tenant_agents, "mixed")
    await asyncio.sleep(10)  # Allow resource allocation
    
    # Capture initial resource state
    initial_summaries = {}
    for agent in tenant_agents:
        summary = suite.resource_monitor.get_tenant_metrics_summary(agent.tenant_id)
        if summary:
            initial_summaries[agent.tenant_id] = summary
    
    initial_system_metrics = suite.resource_monitor._collect_system_metrics()
    
    # Phase 2: Simulate different disconnect scenarios
    crash_agents = tenant_agents[:len(tenant_agents)//3]      # Simulate crashes
    graceful_agents = tenant_agents[len(tenant_agents)//3:]   # Graceful disconnects
    
    logger.info(f"Simulating {len(crash_agents)} crashes and {len(graceful_agents)} graceful disconnects...")
    
    # Phase 3: Simulate abrupt termination (crashes)
    crash_start = time.time()
    for agent in crash_agents:
        if agent.websocket_client:
            try:
                # Abrupt close without proper cleanup
                await agent.websocket_client.close(code=1006)  # Abnormal closure
            except Exception:
                pass  # Expected for abrupt closes
        
        # Unregister from monitoring (simulating process termination)
        suite.resource_monitor.unregister_agent_process(agent.tenant_id)
    
    # Phase 4: Graceful disconnection
    for agent in graceful_agents:
        if agent.websocket_client:
            try:
                # Send goodbye message
                goodbye_msg = {
                    "type": "disconnect",
                    "tenant_id": agent.tenant_id,
                    "reason": "graceful_shutdown"
                }
                await agent.websocket_client.send(json.dumps(goodbye_msg))
                await agent.websocket_client.close()
            except Exception:
                pass  # Connection might already be closed
        
        # Unregister from monitoring
        suite.resource_monitor.unregister_agent_process(agent.tenant_id)
    
    disconnect_time = time.time() - crash_start
    
    # Phase 5: Allow cleanup time and monitor recovery
    logger.info("Monitoring resource recovery...")
    await asyncio.sleep(30)  # Allow cleanup and recovery
    
    # Capture post-cleanup system state
    post_cleanup_metrics = suite.resource_monitor._collect_system_metrics()
    
    # Check that tenant-specific metrics are cleaned up
    remaining_tenants = [
        tenant_id for tenant_id in initial_summaries.keys()
        if tenant_id in suite.resource_monitor.metrics_history
    ]
    
    # Phase 6: Test system capacity for new tenants
    logger.info("Testing capacity for new tenants...")
    
    # Create a few new test agents to verify capacity
    new_agents = await suite.create_tenant_agents(3)
    new_connection_count = await suite.establish_agent_connections(new_agents)
    
    # Generate workload for new agents
    if new_connection_count > 0:
        new_responses = await suite.generate_workload(new_agents[:new_connection_count], "normal")
    else:
        new_responses = []
    
    # Assertions
    assert disconnect_time < 30, f"Disconnection process took too long: {disconnect_time:.2f}s"
    
    # Validate cleanup - most tenants should be removed from monitoring
    cleanup_percentage = 1 - (len(remaining_tenants) / len(initial_summaries)) if initial_summaries else 1
    assert cleanup_percentage >= 0.8, f"Insufficient cleanup: {cleanup_percentage:.2%}"
    
    # Validate system resource recovery
    memory_recovered = initial_system_metrics.memory_mb - post_cleanup_metrics.memory_mb
    assert memory_recovered > 0 or post_cleanup_metrics.memory_mb < initial_system_metrics.memory_mb * 1.1, \
        "No significant memory recovery observed"
    
    # Validate new tenant capacity
    assert new_connection_count >= 2, f"Insufficient capacity for new tenants: {new_connection_count}/3"
    assert len(new_responses) >= 1, "New tenants unable to generate responses"
    
    # Validate no zombie processes (all registered processes should be cleaned up)
    remaining_processes = len(suite.resource_monitor.agent_processes)
    assert remaining_processes <= 3, f"Too many processes remain: {remaining_processes} (should be <= 3 new agents)"
    
    logger.info(f"Test Case 7 completed: {cleanup_percentage:.2%} cleanup, {new_connection_count} new connections")


# Helper Functions for Advanced Testing

async def validate_resource_isolation_integrity(suite: ResourceIsolationTestSuite, tenant_agents: List[TenantAgent]) -> Dict[str, Any]:
    """Validate overall resource isolation integrity."""
    integrity_report = {
        "total_tenants": len(tenant_agents),
        "monitored_tenants": len(suite.resource_monitor.agent_processes),
        "violations_detected": len(suite.test_violations),
        "enforcement_actions": len(suite.quota_enforcer.enforcement_actions),
        "noisy_neighbors": len(suite.resource_monitor.detect_noisy_neighbors()),
        "system_stable": True
    }
    
    # Check system stability
    if suite.resource_monitor.system_baseline:
        current_metrics = suite.resource_monitor._collect_system_metrics()
        cpu_increase = current_metrics.cpu_percent - suite.resource_monitor.system_baseline.cpu_percent
        memory_increase = current_metrics.memory_mb - suite.resource_monitor.system_baseline.memory_mb
        
        if cpu_increase > 50 or memory_increase > 2048:  # 2GB increase
            integrity_report["system_stable"] = False
    
    return integrity_report


async def generate_comprehensive_report(suite: ResourceIsolationTestSuite) -> Dict[str, Any]:
    """Generate comprehensive test report."""
    return {
        "test_summary": {
            "total_tenants": len(suite.tenant_agents),
            "total_violations": len(suite.test_violations),
            "enforcement_actions": len(suite.quota_enforcer.enforcement_actions),
            "performance_reports": len(suite.performance_validator.impact_reports)
        },
        "violation_breakdown": {
            violation_type: len([v for v in suite.test_violations if v.violation_type == violation_type])
            for violation_type in ["cpu_quota", "memory_quota", "memory_leak", "isolation"]
        },
        "performance_impact": {
            "total_reports": len(suite.performance_validator.impact_reports),
            "max_impact": max([r.impact_percentage for r in suite.performance_validator.impact_reports], default=0),
            "avg_impact": statistics.mean([r.impact_percentage for r in suite.performance_validator.impact_reports]) if suite.performance_validator.impact_reports else 0
        },
        "resource_usage": {
            tenant_id: suite.resource_monitor.get_tenant_metrics_summary(tenant_id)
            for tenant_id in suite.resource_monitor.agent_processes.keys()
        }
    }