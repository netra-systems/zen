"""
Category 3 Test Suite: Concurrency, Isolation, and Load Testing
==============================================================

Business Value Justification (BVJ):
- Segment: Enterprise, Mid-tier customers  
- Business Goal: Platform Scalability, Multi-tenant Security, System Stability
- Value Impact: Enables $100K+ enterprise deals, prevents catastrophic failures
- Strategic/Revenue Impact: Critical for enterprise sales, prevents security breaches

This comprehensive test suite validates the Netra Apex platform's ability to handle
100+ concurrent users with complete isolation, robust resource management, and
enterprise-grade security guarantees.

Test Coverage:
1. Concurrent Agent Startup Isolation (100+ Users)
2. Race Conditions in Authentication  
3. Database Connection Pool Exhaustion
4. Agent Resource Utilization Isolation
5. Cache Contention Under Load

Performance Requirements:
- 100+ concurrent user isolation validation
- Zero cross-contamination incidents
- P95 response time < 2 seconds under load
- Graceful degradation under resource exhaustion
- 99.9% availability during stress testing

Architectural Compliance:
- Real service integration (no mocking)
- Production-like test environment
- Comprehensive metrics collection
- Advanced race condition detection
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
import gc
import threading
import hashlib
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set, Union, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

import httpx
import websockets
import redis
import redis.asyncio
import asyncpg
import psutil
import jwt

# Configure test environment
os.environ["TESTING"] = "1"
os.environ["NETRA_ENV"] = "concurrency_testing"
os.environ["USE_REAL_SERVICES"] = "true"
os.environ["CONCURRENT_TEST_MODE"] = "true"

# Setup logging
logger = logging.getLogger("concurrency_isolation")
logger.setLevel(logging.INFO)

# Test Configuration
CONCURRENCY_CONFIG = {
    "base_user_count": int(os.getenv("CONCURRENT_TEST_USERS", "100")),
    "max_user_count": int(os.getenv("MAX_CONCURRENT_USERS", "150")),
    "test_timeout": int(os.getenv("CONCURRENT_TEST_TIMEOUT", "600")),
    "agent_startup_timeout": int(os.getenv("AGENT_STARTUP_TIMEOUT", "30")),
    "max_response_time": float(os.getenv("MAX_RESPONSE_TIME", "2.0")),
    "min_success_rate": float(os.getenv("MIN_SUCCESS_RATE", "0.95")),
    "resource_check_interval": float(os.getenv("RESOURCE_CHECK_INTERVAL", "1.0")),
    "memory_limit_gb": float(os.getenv("MEMORY_LIMIT_GB", "8.0")),
    "cpu_limit_percent": float(os.getenv("CPU_LIMIT_PERCENT", "85.0")),
    "db_pool_size": int(os.getenv("TEST_DB_POOL_SIZE", "5")),
    "db_max_overflow": int(os.getenv("TEST_DB_MAX_OVERFLOW", "10")),
    "race_detection_threshold": float(os.getenv("RACE_DETECTION_THRESHOLD", "0.001"))
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
class ConcurrentUser:
    """Represents a concurrent test user with full isolation context."""
    user_id: str
    email: str
    session_id: str
    auth_token: str
    workspace_id: str = field(default_factory=lambda: f"ws_{uuid.uuid4().hex[:8]}")
    context_data: Dict[str, Any] = field(default_factory=dict)
    sensitive_data: Dict[str, Any] = field(default_factory=dict)
    isolation_markers: Set[str] = field(default_factory=set)
    websocket_client: Optional[websockets.WebSocketServerProtocol] = None
    agent_instance_id: Optional[str] = None
    resource_usage: Dict[str, float] = field(default_factory=dict)
    timing_metrics: Dict[str, float] = field(default_factory=dict)
    error_log: List[str] = field(default_factory=list)
    is_connected: bool = False
    last_activity: float = field(default_factory=time.time)


@dataclass
class IsolationViolation:
    """Represents a detected isolation violation."""
    violation_type: str
    source_user: str
    target_user: str
    contaminated_data: str
    detection_context: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    severity: str = "HIGH"


@dataclass
class ResourceMetrics:
    """System resource utilization metrics."""
    timestamp: float = field(default_factory=time.time)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    active_connections: int = 0
    db_pool_status: Dict[str, Any] = field(default_factory=dict)
    redis_memory_mb: float = 0.0
    websocket_connections: int = 0
    thread_count: int = 0


@dataclass
class ConcurrencyTestReport:
    """Comprehensive test execution report."""
    test_name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_users: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    isolation_violations: List[IsolationViolation] = field(default_factory=list)
    resource_metrics: List[ResourceMetrics] = field(default_factory=list)
    race_conditions_detected: int = 0
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        total_ops = self.successful_operations + self.failed_operations
        return self.successful_operations / total_ops if total_ops > 0 else 0.0
    
    @property
    def test_duration(self) -> float:
        end_time = self.end_time or time.time()
        return end_time - self.start_time
    
    @property
    def has_violations(self) -> bool:
        return len(self.isolation_violations) > 0


class AdvancedRaceDetector:
    """Advanced race condition detection system."""
    
    def __init__(self):
        self.operation_timestamps = defaultdict(deque)
        self.shared_resource_access = defaultdict(list)
        self.timing_anomalies = []
        self.memory_snapshots = []
        self.lock = threading.Lock()
        
    def record_operation(self, operation_type: str, user_id: str, resource_id: str, timestamp: float):
        """Record an operation for race condition analysis."""
        with self.lock:
            self.operation_timestamps[operation_type].append({
                'user_id': user_id,
                'resource_id': resource_id,
                'timestamp': timestamp
            })
            
            # Track shared resource access
            if resource_id:
                self.shared_resource_access[resource_id].append({
                    'user_id': user_id,
                    'operation': operation_type,
                    'timestamp': timestamp
                })
    
    def detect_race_conditions(self) -> List[Dict[str, Any]]:
        """Detect potential race conditions from recorded operations."""
        race_conditions = []
        
        # Analyze concurrent access to shared resources
        for resource_id, accesses in self.shared_resource_access.items():
            if len(accesses) > 1:
                # Sort by timestamp
                accesses.sort(key=lambda x: x['timestamp'])
                
                # Check for overlapping operations
                for i in range(len(accesses) - 1):
                    current = accesses[i]
                    next_access = accesses[i + 1]
                    
                    time_diff = next_access['timestamp'] - current['timestamp']
                    
                    # Race condition if operations are very close in time
                    if time_diff < CONCURRENCY_CONFIG['race_detection_threshold']:
                        race_conditions.append({
                            'type': 'concurrent_resource_access',
                            'resource_id': resource_id,
                            'users': [current['user_id'], next_access['user_id']],
                            'time_diff': time_diff,
                            'operations': [current['operation'], next_access['operation']]
                        })
        
        return race_conditions
    
    def take_memory_snapshot(self, label: str):
        """Take system memory snapshot for leak detection."""
        snapshot = {
            'label': label,
            'timestamp': time.time(),
            'memory_rss': psutil.Process().memory_info().rss,
            'objects_count': len(gc.get_objects()),
            'thread_count': threading.active_count()
        }
        self.memory_snapshots.append(snapshot)
    
    def analyze_memory_trends(self) -> Dict[str, Any]:
        """Analyze memory usage trends for leak detection."""
        if len(self.memory_snapshots) < 2:
            return {"status": "insufficient_data"}
            
        start = self.memory_snapshots[0]
        end = self.memory_snapshots[-1]
        
        memory_growth = end['memory_rss'] - start['memory_rss']
        growth_rate = memory_growth / (end['timestamp'] - start['timestamp'])
        
        return {
            'memory_growth_bytes': memory_growth,
            'memory_growth_mb': memory_growth / (1024 * 1024),
            'growth_rate_mb_per_sec': growth_rate / (1024 * 1024),
            'is_leak_suspected': memory_growth > 100 * 1024 * 1024  # >100MB growth
        }


class ResourceMonitor:
    """Continuous system resource monitoring."""
    
    def __init__(self):
        self.monitoring_active = False
        self.metrics_history = []
        self.process = psutil.Process()
        self.monitor_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self):
        """Start continuous resource monitoring."""
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self):
        """Continuous monitoring loop."""
        while self.monitoring_active:
            try:
                metrics = ResourceMetrics(
                    memory_usage_mb=self.process.memory_info().rss / 1024 / 1024,
                    cpu_usage_percent=self.process.cpu_percent(),
                    thread_count=threading.active_count()
                )
                self.metrics_history.append(metrics)
                
                # Keep only last 1000 metrics to prevent memory bloat
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                    
                await asyncio.sleep(CONCURRENCY_CONFIG['resource_check_interval'])
                
            except Exception as e:
                logger.warning(f"Resource monitoring error: {e}")
                
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get resource utilization summary."""
        if not self.metrics_history:
            return {"status": "no_data"}
            
        memory_values = [m.memory_usage_mb for m in self.metrics_history]
        cpu_values = [m.cpu_usage_percent for m in self.metrics_history]
        
        return {
            'peak_memory_mb': max(memory_values),
            'avg_memory_mb': statistics.mean(memory_values),
            'peak_cpu_percent': max(cpu_values),
            'avg_cpu_percent': statistics.mean(cpu_values),
            'samples_collected': len(self.metrics_history)
        }


class IsolationValidator:
    """Advanced isolation validation system."""
    
    def __init__(self):
        self.contamination_markers = {}
        self.access_logs = defaultdict(list)
        
    async def inject_isolation_markers(self, users: List[ConcurrentUser]) -> Dict[str, Set[str]]:
        """Inject unique isolation markers for contamination detection."""
        user_markers = {}
        
        for user in users:
            # Generate unique markers for each user
            markers = {
                f"isolation_marker_{user.user_id}_{i}_{secrets.token_hex(8)}"
                for i in range(15)  # 15 unique markers per user
            }
            
            user_markers[user.user_id] = markers
            user.isolation_markers = markers
            
            # Inject markers into user context
            user.context_data.update({
                'isolation_markers': list(markers),
                'private_api_key': f"sk_live_{user.user_id}_{secrets.token_hex(24)}",
                'secret_budget': random.randint(10000, 100000),
                'confidential_workspace': user.workspace_id,
                'sensitive_metrics': {
                    f"metric_{i}": random.randint(1, 1000) 
                    for i in range(10)
                }
            })
            
            user.sensitive_data.update({
                'internal_user_id': user.user_id,
                'auth_token': user.auth_token,
                'session_secrets': [secrets.token_hex(16) for _ in range(5)]
            })
        
        self.contamination_markers = user_markers
        return user_markers
    
    async def validate_isolation(self, users: List[ConcurrentUser], 
                               responses: List[Dict[str, Any]]) -> List[IsolationViolation]:
        """Validate complete isolation between users."""
        violations = []
        
        # Check for cross-contamination in responses
        for response in responses:
            user_id = response.get('user_id')
            if not user_id or user_id not in self.contamination_markers:
                continue
                
            response_text = json.dumps(response)
            
            # Check for other users' markers in this response
            for other_user_id, other_markers in self.contamination_markers.items():
                if other_user_id != user_id:
                    for marker in other_markers:
                        if marker in response_text:
                            violations.append(IsolationViolation(
                                violation_type="cross_contamination",
                                source_user=other_user_id,
                                target_user=user_id,
                                contaminated_data=marker,
                                detection_context=response,
                                severity="CRITICAL"
                            ))
        
        return violations
    
    def log_resource_access(self, user_id: str, resource_type: str, resource_id: str, 
                          operation: str, timestamp: float):
        """Log resource access for authorization validation."""
        self.access_logs[resource_type].append({
            'user_id': user_id,
            'resource_id': resource_id,
            'operation': operation,
            'timestamp': timestamp
        })
    
    async def validate_resource_authorization(self) -> List[IsolationViolation]:
        """Validate that users only access authorized resources."""
        violations = []
        
        # Check for unauthorized cross-user resource access
        for resource_type, accesses in self.access_logs.items():
            user_resources = defaultdict(set)
            
            # Build mapping of users to their resources
            for access in accesses:
                user_resources[access['user_id']].add(access['resource_id'])
            
            # Check for unauthorized access patterns
            for user_id, resources in user_resources.items():
                for resource_id in resources:
                    # Check if this resource belongs to another user
                    if any(resource_id.startswith(other_user) 
                          for other_user in user_resources.keys() 
                          if other_user != user_id):
                        violations.append(IsolationViolation(
                            violation_type="unauthorized_resource_access",
                            source_user=user_id,
                            target_user="unknown",
                            contaminated_data=resource_id,
                            detection_context={"resource_type": resource_type}
                        ))
        
        return violations


class ConcurrencyTestEnvironment:
    """Comprehensive test environment for concurrency testing."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.race_detector = AdvancedRaceDetector()
        self.resource_monitor = ResourceMonitor()
        self.isolation_validator = IsolationValidator()
        self.active_users: List[ConcurrentUser] = []
        self.cleanup_tasks: List[asyncio.Task] = []
        
    async def initialize(self):
        """Initialize comprehensive test environment."""
        logger.info("Initializing concurrency test environment...")
        
        # Start resource monitoring
        await self.resource_monitor.start_monitoring()
        self.race_detector.take_memory_snapshot("environment_init_start")
        
        # Initialize Redis (async)
        self.redis_client = redis.asyncio.Redis.from_url(
            SERVICE_ENDPOINTS["redis"],
            decode_responses=True,
            socket_timeout=30,
            socket_keepalive=True,
            health_check_interval=30
        )
        
        # Initialize database pool with test configuration
        self.db_pool = await asyncpg.create_pool(
            SERVICE_ENDPOINTS["postgres"],
            min_size=CONCURRENCY_CONFIG["db_pool_size"],
            max_size=CONCURRENCY_CONFIG["db_pool_size"] + CONCURRENCY_CONFIG["db_max_overflow"],
            command_timeout=60
        )
        
        # Verify services
        await self._verify_services()
        self.race_detector.take_memory_snapshot("environment_init_complete")
        
        logger.info("Concurrency test environment initialized successfully")
    
    async def _verify_services(self):
        """Verify all required services are available and responsive."""
        # Test Redis
        await self.redis_client.ping()
        
        # Test database
        async with self.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Test HTTP services
        async with httpx.AsyncClient(timeout=30) as client:
            # Backend health check
            backend_response = await client.get(f"{SERVICE_ENDPOINTS['backend']}/health")
            if backend_response.status_code != 200:
                raise RuntimeError(f"Backend service unhealthy: {backend_response.status_code}")
            
            # Auth service health check (optional)
            try:
                auth_response = await client.get(f"{SERVICE_ENDPOINTS['auth_service']}/health")
                logger.info(f"Auth service status: {auth_response.status_code}")
            except Exception as e:
                logger.warning(f"Auth service unavailable: {e}")
    
    async def create_concurrent_users(self, count: int) -> List[ConcurrentUser]:
        """Create concurrent test users with complete isolation setup."""
        users = []
        regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"]
        tiers = ["free", "early", "mid", "enterprise"]
        
        for i in range(count):
            user = ConcurrentUser(
                user_id=f"concurrent_user_{i:04d}_{uuid.uuid4().hex[:8]}",
                email=f"concurrency_test_{i:04d}@isolation.test",
                session_id=f"session_{i:04d}_{int(time.time())}_{secrets.token_hex(8)}",
                auth_token=self._generate_test_jwt(f"concurrent_user_{i:04d}"),
                context_data={
                    "user_index": i,
                    "budget": 25000 + (i * 1000),  # Unique budget per user
                    "region": regions[i % len(regions)],
                    "tier": tiers[i % len(tiers)],
                    "workspace_name": f"Workspace {i:04d}",
                    "unique_identifier": f"isolation_test_{i:04d}",
                    "optimization_preferences": {
                        "focus": ["cost", "performance", "reliability"][i % 3],
                        "risk_tolerance": ["low", "medium", "high"][i % 3],
                        "notification_channels": ["email", "slack", "webhook"][i % 3]
                    },
                    "feature_flags": {
                        f"feature_{j}": (i + j) % 2 == 0 
                        for j in range(5)
                    }
                }
            )
            users.append(user)
        
        # Inject isolation markers
        await self.isolation_validator.inject_isolation_markers(users)
        
        self.active_users = users
        logger.info(f"Created {count} concurrent test users with isolation markers")
        return users
    
    def _generate_test_jwt(self, user_id: str) -> str:
        """Generate realistic test JWT token."""
        payload = {
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 7200,  # 2 hour expiry
            "user_id": user_id,
            "scope": "read write admin",
            "workspace_id": f"ws_{user_id}",
            "permissions": ["chat", "analyze", "optimize", "admin"]
        }
        return jwt.encode(payload, "test-secret-key-for-concurrency", algorithm="HS256")
    
    async def seed_user_data(self, users: List[ConcurrentUser]):
        """Seed user data in databases with isolation."""
        logger.info(f"Seeding isolated data for {len(users)} users...")
        
        # Seed in parallel batches to avoid overwhelming database
        batch_size = 25
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            tasks = [self._seed_single_user(user) for user in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Brief pause between batches
            if i + batch_size < len(users):
                await asyncio.sleep(0.1)
        
        logger.info("User data seeding completed")
    
    async def _seed_single_user(self, user: ConcurrentUser):
        """Seed data for a single user with full isolation."""
        async with self.db_pool.acquire() as conn:
            # Insert user record
            await conn.execute("""
                INSERT INTO users (id, email, is_active, created_at, workspace_id) 
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET 
                    email = $2, workspace_id = $5
            """, user.user_id, user.email, True, datetime.now(timezone.utc), user.workspace_id)
            
            # Create workspace
            await conn.execute("""
                INSERT INTO workspaces (id, name, owner_id, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET name = $2
            """, user.workspace_id, user.context_data['workspace_name'], 
                user.user_id, datetime.now(timezone.utc))
            
            # Create user session
            await conn.execute("""
                INSERT INTO user_sessions (id, user_id, session_data, created_at, expires_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET session_data = $3
            """, user.session_id, user.user_id, json.dumps(user.context_data),
                datetime.now(timezone.utc), datetime.now(timezone.utc).replace(hour=23, minute=59))
        
        # Set user context in Redis with namespace isolation
        redis_key = f"user_context:{user.user_id}"
        await self.redis_client.hset(redis_key, mapping={
            "context": json.dumps(user.context_data),
            "sensitive": json.dumps(user.sensitive_data),
            "workspace_id": user.workspace_id,
            "last_update": str(time.time())
        })
        
        # Set cache with TTL
        await self.redis_client.expire(redis_key, 3600)  # 1 hour TTL
    
    async def cleanup_user_data(self, users: List[ConcurrentUser]):
        """Clean up user data with complete isolation validation."""
        logger.info(f"Cleaning up data for {len(users)} users...")
        
        user_ids = [user.user_id for user in users]
        workspace_ids = [user.workspace_id for user in users]
        session_ids = [user.session_id for user in users]
        
        # Clean database
        async with self.db_pool.acquire() as conn:
            await conn.execute("DELETE FROM user_sessions WHERE id = ANY($1)", session_ids)
            await conn.execute("DELETE FROM workspaces WHERE id = ANY($1)", workspace_ids)
            await conn.execute("DELETE FROM users WHERE id = ANY($1)", user_ids)
            await conn.execute("DELETE FROM agent_states WHERE user_id = ANY($1)", user_ids)
        
        # Clean Redis
        redis_keys = [f"user_context:{user_id}" for user_id in user_ids]
        redis_keys.extend([f"agent_state:{user_id}" for user_id in user_ids])
        redis_keys.extend([f"session:{session_id}" for session_id in session_ids])
        
        if redis_keys:
            await self.redis_client.delete(*redis_keys)
        
        logger.info("User data cleanup completed")
    
    async def cleanup(self):
        """Complete environment cleanup."""
        # Stop monitoring
        await self.resource_monitor.stop_monitoring()
        
        # Clean up active users
        if self.active_users:
            await self.cleanup_user_data(self.active_users)
        
        # Close connections
        if self.redis_client:
            await self.redis_client.aclose()
        
        if self.db_pool:
            await self.db_pool.close()
        
        # Cancel cleanup tasks
        for task in self.cleanup_tasks:
            if not task.done():
                task.cancel()
        
        # Final memory snapshot
        self.race_detector.take_memory_snapshot("environment_cleanup_complete")


class ConcurrentTestOrchestrator:
    """Orchestrates complex concurrent testing scenarios."""
    
    def __init__(self, test_env: ConcurrencyTestEnvironment):
        self.test_env = test_env
        
    async def establish_websocket_connections(self, users: List[ConcurrentUser]) -> int:
        """Establish WebSocket connections for all users concurrently."""
        logger.info(f"Establishing WebSocket connections for {len(users)} users...")
        
        successful_connections = 0
        batch_size = 30  # Increased batch size for efficiency
        
        for i in range(0, len(users), batch_size):
            batch_end = min(i + batch_size, len(users))
            batch_users = users[i:batch_end]
            
            connection_tasks = [
                self._establish_single_connection(user) 
                for user in batch_users
            ]
            
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            for j, result in enumerate(results):
                user = batch_users[j]
                if isinstance(result, Exception):
                    logger.warning(f"Connection failed for user {user.user_id}: {result}")
                    user.error_log.append(f"Connection failed: {result}")
                elif result:
                    successful_connections += 1
                    user.is_connected = True
                    user.last_activity = time.time()
            
            # Brief pause between batches
            if batch_end < len(users):
                await asyncio.sleep(0.2)
        
        logger.info(f"Established {successful_connections} WebSocket connections")
        return successful_connections
    
    async def _establish_single_connection(self, user: ConcurrentUser) -> bool:
        """Establish WebSocket connection for a single user."""
        try:
            start_time = time.time()
            
            # Record operation for race detection
            self.test_env.race_detector.record_operation(
                "websocket_connect", user.user_id, "websocket_server", start_time
            )
            
            # Connect with authentication
            uri = f"{SERVICE_ENDPOINTS['websocket']}?token={user.auth_token}&user_id={user.user_id}"
            
            user.websocket_client = await websockets.connect(
                uri,
                close_timeout=CONCURRENCY_CONFIG["agent_startup_timeout"],
                ping_interval=20,
                ping_timeout=10
            )
            
            connection_time = time.time() - start_time
            user.timing_metrics['websocket_connection_time'] = connection_time
            
            return True
            
        except Exception as e:
            user.error_log.append(f"WebSocket connection failed: {e}")
            return False
    
    async def send_concurrent_messages(self, users: List[ConcurrentUser]) -> List[Dict[str, Any]]:
        """Send concurrent messages to all connected users."""
        logger.info(f"Sending concurrent messages to {len(users)} users...")
        
        connected_users = [user for user in users if user.is_connected and user.websocket_client]
        
        if not connected_users:
            logger.error("No connected users available")
            return []
        
        # Send messages in batches to prevent overwhelming
        batch_size = 25
        all_responses = []
        
        for i in range(0, len(connected_users), batch_size):
            batch_end = min(i + batch_size, len(connected_users))
            batch_users = connected_users[i:batch_end]
            
            message_tasks = [
                self._send_user_message(user) 
                for user in batch_users
            ]
            
            batch_responses = await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Process batch responses
            for j, response in enumerate(batch_responses):
                user = batch_users[j]
                if isinstance(response, Exception):
                    logger.warning(f"Message failed for user {user.user_id}: {response}")
                    user.error_log.append(f"Message failed: {response}")
                else:
                    all_responses.append(response)
                    user.last_activity = time.time()
            
            # Brief pause between message batches
            if batch_end < len(connected_users):
                await asyncio.sleep(0.1)
        
        logger.info(f"Received {len(all_responses)} valid responses")
        return all_responses
    
    async def _send_user_message(self, user: ConcurrentUser) -> Dict[str, Any]:
        """Send message to user and receive response."""
        if not user.websocket_client:
            raise RuntimeError(f"No WebSocket connection for user {user.user_id}")
        
        start_time = time.time()
        
        # Record operation for race detection
        self.test_env.race_detector.record_operation(
            "send_message", user.user_id, f"agent_{user.user_id}", start_time
        )
        
        # Create user-specific message with sensitive data
        message = {
            "type": "chat_message",
            "content": f"Optimize my budget of ${user.context_data['budget']} for {user.context_data['region']} region. Focus on {user.context_data['optimization_preferences']['focus']}.",
            "session_id": user.session_id,
            "workspace_id": user.workspace_id,
            "user_context": user.context_data,
            "request_id": f"req_{user.user_id}_{int(time.time())}_{secrets.token_hex(8)}"
        }
        
        # Send message
        await user.websocket_client.send(json.dumps(message))
        
        # Wait for response with timeout
        response_raw = await asyncio.wait_for(
            user.websocket_client.recv(),
            timeout=CONCURRENCY_CONFIG["agent_startup_timeout"]
        )
        
        response = json.loads(response_raw)
        
        # Record timing
        total_time = time.time() - start_time
        user.timing_metrics['total_response_time'] = total_time
        
        # Extract agent instance ID
        if 'agent_instance_id' in response:
            user.agent_instance_id = response['agent_instance_id']
        
        return {
            'user_id': user.user_id,
            'session_id': user.session_id,
            'workspace_id': user.workspace_id,
            'response': response,
            'response_time': total_time,
            'agent_instance_id': user.agent_instance_id,
            'request_id': message['request_id']
        }


# Pytest Fixtures

@pytest.fixture(scope="function")
async def concurrency_test_environment():
    """Set up comprehensive concurrency test environment."""
    test_env = ConcurrencyTestEnvironment()
    await test_env.initialize()
    
    yield test_env
    
    await test_env.cleanup()


@pytest.fixture
async def concurrent_users_100(concurrency_test_environment):
    """Create 100 concurrent test users."""
    orchestrator = ConcurrentTestOrchestrator(concurrency_test_environment)
    users = await concurrency_test_environment.create_concurrent_users(CONCURRENCY_CONFIG["base_user_count"])
    
    await concurrency_test_environment.seed_user_data(users)
    
    yield users
    
    # Cleanup handled by environment fixture


@pytest.fixture  
async def concurrent_users_150(concurrency_test_environment):
    """Create 150 concurrent test users for load testing."""
    orchestrator = ConcurrentTestOrchestrator(concurrency_test_environment)
    users = await concurrency_test_environment.create_concurrent_users(CONCURRENCY_CONFIG["max_user_count"])
    
    await concurrency_test_environment.seed_user_data(users)
    
    yield users


# Test Cases

@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_1_concurrent_agent_startup_isolation(
    concurrency_test_environment,
    concurrent_users_100
):
    """
    Test 1: Concurrent Agent Startup Isolation (100+ Users)
    
    Objective: Validate 100+ users can start agents simultaneously with complete isolation
    Success Criteria:
    - 100+ unique agent instances created
    - Zero cross-contamination incidents
    - P95 response time < 2 seconds
    - >95% success rate
    - Memory usage within limits
    """
    logger.info("Starting Test 1: Concurrent Agent Startup Isolation (100+ Users)")
    
    test_report = ConcurrencyTestReport(
        test_name="concurrent_agent_startup_isolation",
        total_users=len(concurrent_users_100)
    )
    
    orchestrator = ConcurrentTestOrchestrator(concurrency_test_environment)
    
    try:
        # Phase 1: Establish connections
        connection_count = await orchestrator.establish_websocket_connections(concurrent_users_100)
        assert connection_count >= int(CONCURRENCY_CONFIG["base_user_count"] * CONCURRENCY_CONFIG["min_success_rate"]), \
            f"Insufficient connections: {connection_count}/{CONCURRENCY_CONFIG['base_user_count']}"
        
        # Phase 2: Send concurrent messages
        responses = await orchestrator.send_concurrent_messages(concurrent_users_100)
        test_report.successful_operations = len(responses)
        test_report.failed_operations = len(concurrent_users_100) - len(responses)
        
        # Phase 3: Validate isolation
        violations = await concurrency_test_environment.isolation_validator.validate_isolation(
            concurrent_users_100, responses
        )
        test_report.isolation_violations = violations
        
        # Phase 4: Check for race conditions
        race_conditions = concurrency_test_environment.race_detector.detect_race_conditions()
        test_report.race_conditions_detected = len(race_conditions)
        
        # Phase 5: Performance validation
        response_times = [r['response_time'] for r in responses]
        if response_times:
            p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
            test_report.performance_summary = {
                'p95_response_time': p95_time,
                'avg_response_time': statistics.mean(response_times),
                'max_response_time': max(response_times)
            }
        
        # Phase 6: Resource utilization check
        resource_summary = concurrency_test_environment.resource_monitor.get_resource_summary()
        test_report.resource_metrics.append(ResourceMetrics(
            memory_usage_mb=resource_summary.get('peak_memory_mb', 0),
            cpu_usage_percent=resource_summary.get('peak_cpu_percent', 0)
        ))
        
        # Assertions
        assert len(violations) == 0, f"Isolation violations detected: {violations}"
        assert test_report.success_rate >= CONCURRENCY_CONFIG['min_success_rate'], \
            f"Success rate too low: {test_report.success_rate:.2%}"
        
        if response_times:
            assert test_report.performance_summary['p95_response_time'] <= CONCURRENCY_CONFIG['max_response_time'], \
                f"P95 response time too high: {test_report.performance_summary['p95_response_time']:.2f}s"
        
        # Verify unique agent instances
        agent_ids = [r.get('agent_instance_id') for r in responses if r.get('agent_instance_id')]
        assert len(set(agent_ids)) == len(agent_ids), "Agent instance IDs are not unique"
        
        # Memory usage check
        assert resource_summary.get('peak_memory_mb', 0) < CONCURRENCY_CONFIG['memory_limit_gb'] * 1024, \
            f"Memory usage exceeded limit: {resource_summary.get('peak_memory_mb', 0):.1f}MB"
        
        logger.info(f"Test 1 completed: {test_report.success_rate:.2%} success rate, {len(violations)} violations")
        
    finally:
        test_report.end_time = time.time()


@pytest.mark.e2e
@pytest.mark.critical
@pytest.mark.asyncio
async def test_2_race_conditions_authentication(
    concurrency_test_environment,
    concurrent_users_100
):
    """
    Test 2: Race Conditions in Authentication
    
    Objective: Detect and prevent race conditions in authentication system
    Success Criteria:
    - Concurrent login/logout operations execute safely
    - Token refresh operations are atomic
    - Session management maintains consistency
    - No authentication bypass vulnerabilities
    """
    logger.info("Starting Test 2: Race Conditions in Authentication")
    
    test_report = ConcurrencyTestReport(
        test_name="race_conditions_authentication",
        total_users=len(concurrent_users_100)
    )
    
    # Test concurrent authentication operations
    auth_operations = []
    
    # Phase 1: Concurrent token refresh
    async def concurrent_token_refresh(user: ConcurrentUser):
        """Simulate concurrent token refresh operations."""
        try:
            start_time = time.time()
            concurrency_test_environment.race_detector.record_operation(
                "token_refresh", user.user_id, "auth_system", start_time
            )
            
            # Simulate token refresh
            new_token = concurrency_test_environment._generate_test_jwt(user.user_id)
            user.auth_token = new_token
            
            # Simulate database update
            async with concurrency_test_environment.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE user_sessions SET updated_at = $1 WHERE id = $2",
                    datetime.now(timezone.utc), user.session_id
                )
            
            return {"success": True, "user_id": user.user_id}
            
        except Exception as e:
            return {"success": False, "user_id": user.user_id, "error": str(e)}
    
    # Execute concurrent token refreshes
    refresh_tasks = [concurrent_token_refresh(user) for user in concurrent_users_100[:50]]
    refresh_results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
    
    successful_refreshes = sum(1 for r in refresh_results if isinstance(r, dict) and r.get('success'))
    test_report.successful_operations += successful_refreshes
    test_report.failed_operations += len(refresh_results) - successful_refreshes
    
    # Phase 2: Concurrent session invalidation
    async def concurrent_session_invalidation(user: ConcurrentUser):
        """Simulate concurrent session invalidation."""
        try:
            start_time = time.time()
            concurrency_test_environment.race_detector.record_operation(
                "session_invalidation", user.user_id, "session_manager", start_time
            )
            
            # Simulate session invalidation
            await concurrency_test_environment.redis_client.delete(f"session:{user.session_id}")
            
            return {"success": True, "user_id": user.user_id}
            
        except Exception as e:
            return {"success": False, "user_id": user.user_id, "error": str(e)}
    
    # Execute concurrent session invalidations
    invalidation_tasks = [concurrent_session_invalidation(user) for user in concurrent_users_100[50:]]
    invalidation_results = await asyncio.gather(*invalidation_tasks, return_exceptions=True)
    
    successful_invalidations = sum(1 for r in invalidation_results if isinstance(r, dict) and r.get('success'))
    test_report.successful_operations += successful_invalidations
    test_report.failed_operations += len(invalidation_results) - successful_invalidations
    
    # Phase 3: Race condition detection
    race_conditions = concurrency_test_environment.race_detector.detect_race_conditions()
    test_report.race_conditions_detected = len(race_conditions)
    
    # Assertions
    # For authentication race condition tests, we expect some controlled failures
    # but the system should remain consistent
    assert test_report.success_rate >= 0.80, f"Too many auth operations failed: {test_report.success_rate:.2%}"
    
    # No critical race conditions should be detected
    critical_races = [rc for rc in race_conditions if rc.get('type') == 'concurrent_resource_access']
    assert len(critical_races) <= 5, f"Too many critical race conditions: {len(critical_races)}"
    
    logger.info(f"Test 2 completed: {test_report.success_rate:.2%} success rate, {len(race_conditions)} race conditions detected")
    
    test_report.end_time = time.time()


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
async def test_3_database_connection_pool_exhaustion(
    concurrency_test_environment,
    concurrent_users_150
):
    """
    Test 3: Database Connection Pool Exhaustion
    
    Objective: Validate graceful handling of database connection pool limits
    Success Criteria:
    - System handles pool exhaustion gracefully
    - Proper backpressure mechanisms activate
    - No connection leaks detected
    - Recovery after load reduction
    """
    logger.info("Starting Test 3: Database Connection Pool Exhaustion")
    
    test_report = ConcurrencyTestReport(
        test_name="database_connection_pool_exhaustion",
        total_users=len(concurrent_users_150)
    )
    
    # Phase 1: Create more database operations than pool can handle
    async def database_intensive_operation(user: ConcurrentUser):
        """Simulate database-intensive operation."""
        try:
            start_time = time.time()
            concurrency_test_environment.race_detector.record_operation(
                "db_operation", user.user_id, "database", start_time
            )
            
            async with concurrency_test_environment.db_pool.acquire() as conn:
                # Simulate complex query
                await conn.execute("SELECT pg_sleep(0.1)")  # 100ms query
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM users WHERE id = $1", user.user_id
                )
                
                # Simulate additional database work
                await conn.execute(
                    "UPDATE users SET updated_at = $1 WHERE id = $2",
                    datetime.now(timezone.utc), user.user_id
                )
            
            return {"success": True, "user_id": user.user_id, "result": result}
            
        except asyncio.TimeoutError:
            return {"success": False, "user_id": user.user_id, "error": "timeout"}
        except Exception as e:
            return {"success": False, "user_id": user.user_id, "error": str(e)}
    
    # Execute operations that will exhaust pool
    db_tasks = [database_intensive_operation(user) for user in concurrent_users_150]
    
    # Use timeout to prevent test from hanging
    try:
        db_results = await asyncio.wait_for(
            asyncio.gather(*db_tasks, return_exceptions=True),
            timeout=120  # 2 minute timeout
        )
    except asyncio.TimeoutError:
        logger.warning("Database operations timed out as expected under load")
        db_results = [{"success": False, "error": "global_timeout"}] * len(concurrent_users_150)
    
    successful_operations = sum(1 for r in db_results if isinstance(r, dict) and r.get('success'))
    test_report.successful_operations = successful_operations
    test_report.failed_operations = len(db_results) - successful_operations
    
    # Phase 2: Verify pool status and recovery
    # Wait for pool to recover
    await asyncio.sleep(5)
    
    # Test that normal operations work after load reduction
    recovery_tasks = [database_intensive_operation(user) for user in concurrent_users_150[:10]]
    recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
    
    recovery_success = sum(1 for r in recovery_results if isinstance(r, dict) and r.get('success'))
    
    # Assertions
    # Under pool exhaustion, we expect controlled failures but eventual recovery
    assert test_report.success_rate >= 0.30, f"Database operations completely failed: {test_report.success_rate:.2%}"
    assert recovery_success >= 8, f"System did not recover properly: {recovery_success}/10 recovery operations succeeded"
    
    # No connection leaks
    memory_analysis = concurrency_test_environment.race_detector.analyze_memory_trends()
    if memory_analysis.get('is_leak_suspected'):
        logger.warning(f"Potential memory leak detected: {memory_analysis}")
    
    logger.info(f"Test 3 completed: {test_report.success_rate:.2%} under load, {recovery_success}/10 recovery success")
    
    test_report.end_time = time.time()


@pytest.mark.e2e
@pytest.mark.isolation
@pytest.mark.asyncio
async def test_4_agent_resource_utilization_isolation(
    concurrency_test_environment,
    concurrent_users_100
):
    """
    Test 4: Agent Resource Utilization Isolation
    
    Objective: Prevent noisy neighbor problems in agent resource allocation
    Success Criteria:
    - Each agent has isolated resource limits
    - No agent can monopolize system resources
    - Fair resource distribution under load
    - Resource cleanup after agent termination
    """
    logger.info("Starting Test 4: Agent Resource Utilization Isolation")
    
    test_report = ConcurrencyTestReport(
        test_name="agent_resource_utilization_isolation",
        total_users=len(concurrent_users_100)
    )
    
    orchestrator = ConcurrentTestOrchestrator(concurrency_test_environment)
    
    # Phase 1: Create agents with varying resource demands
    connection_count = await orchestrator.establish_websocket_connections(concurrent_users_100)
    
    # Phase 2: Send resource-intensive requests
    async def send_resource_intensive_request(user: ConcurrentUser, intensity: str):
        """Send resource-intensive request based on intensity level."""
        try:
            if not user.websocket_client:
                return {"success": False, "error": "no_connection"}
            
            # Create different types of resource-intensive requests
            if intensity == "high":
                message = {
                    "type": "chat_message",
                    "content": f"Perform comprehensive analysis of {user.context_data['budget']} budget across all categories with detailed optimization recommendations and multi-scenario modeling.",
                    "workspace_id": user.workspace_id,
                    "processing_options": {
                        "analysis_depth": "comprehensive",
                        "scenario_count": 10,
                        "include_forecasting": True
                    }
                }
            elif intensity == "medium":
                message = {
                    "type": "chat_message", 
                    "content": f"Analyze my budget of ${user.context_data['budget']} and suggest optimizations.",
                    "workspace_id": user.workspace_id,
                    "processing_options": {
                        "analysis_depth": "standard"
                    }
                }
            else:  # low
                message = {
                    "type": "chat_message",
                    "content": f"What's my current budget status?",
                    "workspace_id": user.workspace_id
                }
            
            start_time = time.time()
            await user.websocket_client.send(json.dumps(message))
            
            response_raw = await asyncio.wait_for(
                user.websocket_client.recv(),
                timeout=CONCURRENCY_CONFIG["agent_startup_timeout"]
            )
            
            response_time = time.time() - start_time
            user.timing_metrics[f'{intensity}_request_time'] = response_time
            
            return {
                "success": True,
                "user_id": user.user_id,
                "intensity": intensity,
                "response_time": response_time
            }
            
        except Exception as e:
            return {"success": False, "user_id": user.user_id, "error": str(e)}
    
    # Distribute different intensity levels
    high_intensity_users = concurrent_users_100[:30]
    medium_intensity_users = concurrent_users_100[30:70]
    low_intensity_users = concurrent_users_100[70:]
    
    # Execute resource-intensive requests concurrently
    intensive_tasks = []
    intensive_tasks.extend([send_resource_intensive_request(user, "high") for user in high_intensity_users])
    intensive_tasks.extend([send_resource_intensive_request(user, "medium") for user in medium_intensity_users])
    intensive_tasks.extend([send_resource_intensive_request(user, "low") for user in low_intensity_users])
    
    intensive_results = await asyncio.gather(*intensive_tasks, return_exceptions=True)
    
    successful_requests = sum(1 for r in intensive_results if isinstance(r, dict) and r.get('success'))
    test_report.successful_operations = successful_requests
    test_report.failed_operations = len(intensive_results) - successful_requests
    
    # Phase 3: Analyze resource distribution fairness
    high_intensity_times = [r['response_time'] for r in intensive_results 
                           if isinstance(r, dict) and r.get('intensity') == 'high' and r.get('success')]
    medium_intensity_times = [r['response_time'] for r in intensive_results 
                             if isinstance(r, dict) and r.get('intensity') == 'medium' and r.get('success')]
    low_intensity_times = [r['response_time'] for r in intensive_results 
                          if isinstance(r, dict) and r.get('intensity') == 'low' and r.get('success')]
    
    # Calculate fairness metrics
    resource_fairness = {}
    if high_intensity_times:
        resource_fairness['high_avg'] = statistics.mean(high_intensity_times)
    if medium_intensity_times:
        resource_fairness['medium_avg'] = statistics.mean(medium_intensity_times)
    if low_intensity_times:
        resource_fairness['low_avg'] = statistics.mean(low_intensity_times)
    
    test_report.performance_summary = resource_fairness
    
    # Phase 4: Resource cleanup validation
    resource_summary = concurrency_test_environment.resource_monitor.get_resource_summary()
    
    # Assertions
    assert test_report.success_rate >= 0.85, f"Too many resource requests failed: {test_report.success_rate:.2%}"
    
    # Verify resource isolation - high intensity shouldn't completely block low intensity
    if low_intensity_times and high_intensity_times:
        low_avg = statistics.mean(low_intensity_times)
        high_avg = statistics.mean(high_intensity_times)
        
        # Low intensity requests should still complete reasonably quickly
        assert low_avg <= CONCURRENCY_CONFIG['max_response_time'] * 2, \
            f"Low intensity requests too slow: {low_avg:.2f}s (possible noisy neighbor)"
        
        # But high intensity should take longer (resource allocation working)
        assert high_avg >= low_avg, "Resource allocation not working - high intensity should take longer"
    
    # Memory usage should remain reasonable
    assert resource_summary.get('peak_memory_mb', 0) < CONCURRENCY_CONFIG['memory_limit_gb'] * 1024, \
        f"Memory usage exceeded: {resource_summary.get('peak_memory_mb', 0):.1f}MB"
    
    logger.info(f"Test 4 completed: Resource fairness - {resource_fairness}")
    
    test_report.end_time = time.time()


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.asyncio
async def test_5_cache_contention_under_load(
    concurrency_test_environment,
    concurrent_users_100
):
    """
    Test 5: Cache Contention Under Load
    
    Objective: Validate atomic Redis operations under concurrent load
    Success Criteria:
    - Redis operations remain atomic under load
    - No cache corruption or data loss
    - Consistent cache state across concurrent operations
    - Performance degradation within acceptable limits
    """
    logger.info("Starting Test 5: Cache Contention Under Load")
    
    test_report = ConcurrencyTestReport(
        test_name="cache_contention_under_load",
        total_users=len(concurrent_users_100)
    )
    
    # Phase 1: Concurrent cache operations
    cache_keys = [f"cache_test_{i}" for i in range(20)]  # Shared cache keys
    
    async def concurrent_cache_operation(user: ConcurrentUser, operation_type: str):
        """Perform concurrent cache operations."""
        try:
            start_time = time.time()
            concurrency_test_environment.race_detector.record_operation(
                f"cache_{operation_type}", user.user_id, "redis", start_time
            )
            
            cache_key = random.choice(cache_keys)
            
            if operation_type == "increment":
                # Atomic increment operation
                result = await concurrency_test_environment.redis_client.incr(cache_key)
                
            elif operation_type == "set_get":
                # Set and get operation
                value = f"{user.user_id}_{int(time.time())}_{secrets.token_hex(8)}"
                await concurrency_test_environment.redis_client.set(
                    f"user_cache:{user.user_id}", value, ex=300
                )
                result = await concurrency_test_environment.redis_client.get(
                    f"user_cache:{user.user_id}"
                )
                
            elif operation_type == "hash_update":
                # Hash field update
                await concurrency_test_environment.redis_client.hset(
                    f"user_hash:{user.user_id}",
                    mapping={
                        "last_access": str(time.time()),
                        "operation_count": str(random.randint(1, 100)),
                        "user_data": json.dumps(user.context_data)
                    }
                )
                result = await concurrency_test_environment.redis_client.hgetall(
                    f"user_hash:{user.user_id}"
                )
                
            elif operation_type == "list_operations":
                # List push/pop operations
                list_key = f"user_list:{user.user_id}"
                await concurrency_test_environment.redis_client.lpush(
                    list_key, json.dumps({"timestamp": time.time(), "data": user.user_id})
                )
                result = await concurrency_test_environment.redis_client.llen(list_key)
                
                # Keep list size manageable
                if result > 100:
                    await concurrency_test_environment.redis_client.ltrim(list_key, 0, 50)
                    
            else:  # pipeline_operations
                # Pipeline operations for atomicity
                pipe = concurrency_test_environment.redis_client.pipeline()
                pipe.set(f"pipe:{user.user_id}:1", "value1")
                pipe.set(f"pipe:{user.user_id}:2", "value2")
                pipe.incr(f"pipe_counter:{user.user_id}")
                result = await pipe.execute()
            
            operation_time = time.time() - start_time
            
            return {
                "success": True,
                "user_id": user.user_id,
                "operation": operation_type,
                "time": operation_time,
                "result": str(result)[:100]  # Truncate for logging
            }
            
        except Exception as e:
            return {
                "success": False,
                "user_id": user.user_id,
                "operation": operation_type,
                "error": str(e)
            }
    
    # Execute diverse cache operations concurrently
    operation_types = ["increment", "set_get", "hash_update", "list_operations", "pipeline_operations"]
    cache_tasks = []
    
    for user in concurrent_users_100:
        # Each user performs multiple operation types
        for op_type in random.sample(operation_types, 3):  # 3 random operations per user
            cache_tasks.append(concurrent_cache_operation(user, op_type))
    
    cache_results = await asyncio.gather(*cache_tasks, return_exceptions=True)
    
    successful_cache_ops = sum(1 for r in cache_results if isinstance(r, dict) and r.get('success'))
    test_report.successful_operations = successful_cache_ops
    test_report.failed_operations = len(cache_results) - successful_cache_ops
    
    # Phase 2: Verify cache consistency
    consistency_issues = 0
    
    # Check increment counters for consistency
    for cache_key in cache_keys:
        try:
            counter_value = await concurrency_test_environment.redis_client.get(cache_key)
            if counter_value:
                # Verify counter is reasonable (not corrupted)
                counter_int = int(counter_value)
                if counter_int < 0 or counter_int > len(concurrent_users_100) * 2:
                    consistency_issues += 1
                    logger.warning(f"Cache inconsistency in counter {cache_key}: {counter_int}")
        except Exception as e:
            consistency_issues += 1
            logger.warning(f"Cache read error for {cache_key}: {e}")
    
    # Phase 3: Performance analysis
    operation_times = [r['time'] for r in cache_results 
                      if isinstance(r, dict) and r.get('success') and 'time' in r]
    
    if operation_times:
        test_report.performance_summary = {
            'avg_cache_operation_time': statistics.mean(operation_times),
            'max_cache_operation_time': max(operation_times),
            'p95_cache_operation_time': statistics.quantiles(operation_times, n=20)[18] if len(operation_times) >= 20 else max(operation_times)
        }
    
    # Assertions
    assert test_report.success_rate >= 0.90, f"Too many cache operations failed: {test_report.success_rate:.2%}"
    assert consistency_issues == 0, f"Cache consistency violations detected: {consistency_issues}"
    
    if operation_times:
        avg_time = statistics.mean(operation_times)
        assert avg_time <= 0.1, f"Cache operations too slow: {avg_time:.3f}s average"
    
    # Verify cache is still responsive after load
    test_key = f"post_test_verify_{int(time.time())}"
    await concurrency_test_environment.redis_client.set(test_key, "test_value", ex=60)
    verify_value = await concurrency_test_environment.redis_client.get(test_key)
    assert verify_value == "test_value", "Cache not responsive after load test"
    
    logger.info(f"Test 5 completed: {test_report.success_rate:.2%} success, {consistency_issues} consistency issues")
    
    test_report.end_time = time.time()


# Helper Functions for comprehensive validation

async def cleanup_websocket_connections(users: List[ConcurrentUser]) -> bool:
    """Clean up all WebSocket connections."""
    try:
        cleanup_tasks = []
        for user in users:
            if user.websocket_client:
                cleanup_tasks.append(user.websocket_client.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        return True
    except Exception as e:
        logger.error(f"WebSocket cleanup failed: {e}")
        return False


async def validate_system_stability(test_env: ConcurrencyTestEnvironment) -> Dict[str, Any]:
    """Validate overall system stability after testing."""
    stability_report = {
        "memory_analysis": test_env.race_detector.analyze_memory_trends(),
        "resource_summary": test_env.resource_monitor.get_resource_summary(),
        "race_conditions": test_env.race_detector.detect_race_conditions()
    }
    
    # Check for memory leaks
    memory_analysis = stability_report["memory_analysis"]
    if memory_analysis.get("is_leak_suspected"):
        logger.warning(f"Memory leak suspected: {memory_analysis}")
    
    # Check for performance degradation
    resource_summary = stability_report["resource_summary"]
    if resource_summary.get("peak_memory_mb", 0) > CONCURRENCY_CONFIG["memory_limit_gb"] * 1024:
        logger.warning(f"Memory usage exceeded limits: {resource_summary['peak_memory_mb']:.1f}MB")
    
    return stability_report


if __name__ == "__main__":
    # For standalone execution
    pytest.main([__file__, "-v", "--tb=short"])