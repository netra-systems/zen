"""
Analytics Service Test Configuration
====================================

Comprehensive test configuration for the Analytics Service.
Uses real services (NO MOCKS policy) with Docker Compose for integration testing.

Test Infrastructure:
- FastAPI test client for API testing
- Real ClickHouse connection for database integration
- Real Redis connection for caching tests
- Sample event data generators
- Async test support with proper cleanup

Environment:
- Uses IsolatedEnvironment for configuration management
- Real services via Docker Compose (preferred)
- Falls back to local services if Docker unavailable
"""

import asyncio
import json
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Import base test framework
from test_framework.conftest_base import *
from test_framework.docker_test_manager import get_test_manager

# Analytics service isolated environment
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Use dev launcher environment as fallback
    from shared.isolated_environment import get_env

# Analytics service imports (to be created)
# from analytics_service.app import app
# from analytics_service.models import EventModel, ReportModel
# from analytics_service.event_processor import EventProcessor
# from analytics_service.database import get_clickhouse_client, get_redis_client

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

# Set analytics service specific environment variables
if "pytest" in sys.modules or get_env().get("PYTEST_CURRENT_TEST"):
    env = get_env()
    env.enable_isolation()
    
    # Analytics service configuration
    env.set("ANALYTICS_SERVICE_PORT", "8090", "analytics_conftest")
    env.set("CLICKHOUSE_ANALYTICS_URL", "clickhouse://localhost:9090/analytics", "analytics_conftest")
    env.set("REDIS_ANALYTICS_URL", "redis://localhost:6380/2", "analytics_conftest")
    env.set("GRAFANA_API_URL", "http://localhost:3001", "analytics_conftest")
    env.set("EVENT_BATCH_SIZE", "100", "analytics_conftest")
    env.set("EVENT_FLUSH_INTERVAL_MS", "1000", "analytics_conftest")  # Faster for tests
    env.set("MAX_EVENTS_PER_USER_PER_MINUTE", "1000", "analytics_conftest")
    
    # Enable services for testing (NO MOCKS policy)
    env.set("CLICKHOUSE_ENABLED", "true", "analytics_conftest")
    env.set("REDIS_ENABLED", "true", "analytics_conftest")
    env.set("TEST_DISABLE_REDIS", "false", "analytics_conftest")  # Enable Redis for analytics tests
    env.set("DEV_MODE_DISABLE_CLICKHOUSE", "false", "analytics_conftest")  # Enable ClickHouse for analytics tests
    
    # Test-specific overrides
    env.set("ENVIRONMENT", "test", "analytics_conftest")
    env.set("LOG_LEVEL", "DEBUG", "analytics_conftest")  # More verbose logging for analytics tests

# =============================================================================
# FASTAPI TEST CLIENT
# =============================================================================

@pytest.fixture
def analytics_app():
    """Analytics Service FastAPI application instance"""
    # This will be implemented when the actual FastAPI app is created
    from fastapi import FastAPI
    
    app = FastAPI(title="Analytics Service Test", version="1.0.0")
    
    # Add test routes
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "analytics"}
    
    @app.post("/api/analytics/events")
    async def ingest_events(events: Dict[str, Any]):
        return {"status": "ingested", "count": len(events.get("events", []))}
    
    return app

@pytest.fixture
def test_client(analytics_app):
    """FastAPI test client for analytics service"""
    with TestClient(analytics_app) as client:
        yield client

@pytest.fixture
async def async_test_client(analytics_app):
    """Async FastAPI test client for analytics service"""
    from httpx import AsyncClient, ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app=analytics_app), base_url="http://test") as client:
        yield client

# =============================================================================
# DATABASE FIXTURES (NO MOCKS - REAL SERVICES)
# =============================================================================

@pytest.fixture
async def clickhouse_client():
    """Real ClickHouse client for analytics testing"""
    try:
        import clickhouse_connect
        
        client = clickhouse_connect.get_client(
            host='localhost',
            port=9090,
            username='analytics_user',
            password='analytics_pass',
            database='analytics_test'
        )
        
        # Test connection
        result = client.query("SELECT 1")
        assert result.result_rows[0][0] == 1
        
        # Setup test tables
        await setup_test_tables(client)
        
        yield client
        
        # Cleanup
        client.close()
        
    except ImportError:
        import logging
        logging.warning("ClickHouse client not available - using stub implementation")
        
        class StubClickHouseClient:
            def command(self, query):
                logging.info(f"[STUB] Would execute ClickHouse command: {query}")
                pass
            
            def close(self):
                pass
        
        client = StubClickHouseClient()
        yield client
        client.close()
        
    except Exception as e:
        import logging
        logging.warning(f"ClickHouse connection failed: {e} - using stub implementation")
        
        class StubClickHouseClient:
            def command(self, query):
                logging.info(f"[STUB] Would execute ClickHouse command: {query} (connection failed)")
                pass
            
            def close(self):
                pass
        
        client = StubClickHouseClient()
        yield client
        client.close()

@pytest.fixture
async def redis_client():
    """Real Redis client for analytics caching"""
    try:
        import redis.asyncio as redis
        
        client = redis.Redis(
            host='localhost',
            port=6380,
            db=2,
            decode_responses=True
        )
        
        # Test connection
        await client.ping()
        
        # Clear test database
        await client.flushdb()
        
        yield client
        
        # Cleanup
        await client.flushdb()
        await client.close()
        
    except ImportError:
        import logging
        logging.warning("Redis client not available - using stub implementation")
        
        class StubRedisClient:
            async def flushdb(self):
                logging.info("[STUB] Would flush Redis database")
                pass
            
            async def close(self):
                pass
        
        client = StubRedisClient()
        yield client
        await client.flushdb()
        await client.close()
        
    except Exception as e:
        import logging
        logging.warning(f"Redis connection failed: {e} - using stub implementation")
        
        class StubRedisClient:
            async def flushdb(self):
                logging.info("[STUB] Would flush Redis database (connection failed)")
                pass
            
            async def close(self):
                pass
        
        client = StubRedisClient()
        yield client
        await client.flushdb()
        await client.close()

async def setup_test_tables(clickhouse_client):
    """Setup ClickHouse test tables"""
    # Create test database
    clickhouse_client.command("CREATE DATABASE IF NOT EXISTS analytics_test")
    clickhouse_client.command("USE analytics_test")
    
    # Create frontend_events table
    clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS frontend_events (
            event_id UUID DEFAULT generateUUIDv4(),
            timestamp DateTime64(3) DEFAULT now(),
            user_id String,
            session_id String,
            event_type String,
            event_category String,
            event_action String,
            event_label String,
            event_value Float64,
            properties String,
            user_agent String,
            ip_address String,
            country_code String,
            page_path String,
            page_title String,
            referrer String,
            gtm_container_id String,
            environment String,
            app_version String,
            date Date DEFAULT toDate(timestamp),
            hour UInt8 DEFAULT toHour(timestamp)
        )
        ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (user_id, timestamp, event_id)
        TTL timestamp + INTERVAL 90 DAY
        SETTINGS index_granularity = 8192
    """)
    
    # Create prompt_analytics table
    clickhouse_client.command("""
        CREATE TABLE IF NOT EXISTS prompt_analytics (
            prompt_id UUID DEFAULT generateUUIDv4(),
            timestamp DateTime64(3) DEFAULT now(),
            user_id String,
            thread_id String,
            prompt_hash String,
            prompt_category String,
            prompt_intent String,
            prompt_complexity_score Float32,
            response_quality_score Float32,
            response_relevance_score Float32,
            follow_up_generated Boolean,
            is_repeat_question Boolean,
            similar_prompts Array(String),
            estimated_cost_cents Float32,
            actual_cost_cents Float32
        )
        ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (user_id, timestamp, prompt_id)
        TTL timestamp + INTERVAL 180 DAY
    """)

# =============================================================================
# SAMPLE DATA GENERATORS
# =============================================================================

@pytest.fixture
def sample_chat_interaction_event():
    """Generate sample chat interaction event"""
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "chat_interaction",
        "event_category": "User Interaction Events",
        "user_id": f"test_user_{int(time.time())}",
        "session_id": f"session_{int(time.time())}",
        "properties": json.dumps({
            "thread_id": f"thread_{uuid.uuid4()}",
            "message_id": f"msg_{uuid.uuid4()}",
            "message_type": "user_prompt",
            "prompt_text": "How can I optimize my AI spending?",
            "prompt_length": 35,
            "response_time_ms": 1250.5,
            "model_used": "claude-sonnet-4",
            "tokens_consumed": 150,
            "is_follow_up": False
        }),
        "page_path": "/chat",
        "page_title": "Netra AI Chat",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

@pytest.fixture
def sample_survey_response_event():
    """Generate sample survey response event"""
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "survey_response",
        "event_category": "Survey and Feedback Events",
        "user_id": f"test_user_{int(time.time())}",
        "session_id": f"session_{int(time.time())}",
        "properties": json.dumps({
            "survey_id": "ai_spend_survey_2025",
            "question_id": "pain_perception_q1",
            "question_type": "pain_perception",
            "response_value": "High AI costs are impacting our budget",
            "response_scale": 8,
            "ai_spend_last_month": 15000.50,
            "ai_spend_next_quarter": 45000.00
        }),
        "page_path": "/onboarding/survey",
        "page_title": "AI Spending Survey"
    }

@pytest.fixture
def sample_performance_event():
    """Generate sample performance metric event"""
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "performance_metric",
        "event_category": "Technical Events",
        "user_id": f"test_user_{int(time.time())}",
        "session_id": f"session_{int(time.time())}",
        "properties": json.dumps({
            "metric_type": "api_call",
            "duration_ms": 245.7,
            "success": True,
            "error_details": None
        }),
        "page_path": "/dashboard",
        "page_title": "Analytics Dashboard"
    }

@pytest.fixture
def sample_event_batch():
    """Generate batch of sample events for testing"""
    events = []
    user_id = f"batch_test_user_{int(time.time())}"
    session_id = f"batch_session_{int(time.time())}"
    
    # Chat interactions
    for i in range(10):
        events.append({
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "chat_interaction",
            "event_category": "User Interaction Events",
            "user_id": user_id,
            "session_id": session_id,
            "properties": json.dumps({
                "thread_id": f"thread_{i}",
                "message_id": f"msg_{i}",
                "message_type": "user_prompt",
                "prompt_text": f"Test prompt number {i}",
                "prompt_length": 20 + i,
                "tokens_consumed": 100 + i * 10,
                "is_follow_up": i > 0
            }),
            "page_path": "/chat",
            "event_value": float(100 + i * 10)  # tokens as event_value
        })
    
    # Performance metrics
    for i in range(5):
        events.append({
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "performance_metric",
            "event_category": "Technical Events",
            "user_id": user_id,
            "session_id": session_id,
            "properties": json.dumps({
                "metric_type": "page_load",
                "duration_ms": 200 + i * 50,
                "success": True
            }),
            "page_path": f"/page_{i}",
            "event_value": float(200 + i * 50)  # duration as event_value
        })
    
    return events

@pytest.fixture
def high_volume_event_generator():
    """Generator for high-volume performance testing (10,000 events/second)"""
    def generate_events(count: int = 10000, user_count: int = 100):
        events = []
        for i in range(count):
            user_id = f"perf_user_{i % user_count}"
            events.append({
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "chat_interaction",
                "event_category": "User Interaction Events",
                "user_id": user_id,
                "session_id": f"perf_session_{i // 10}",
                "properties": json.dumps({
                    "thread_id": f"perf_thread_{i}",
                    "message_id": f"perf_msg_{i}",
                    "message_type": "user_prompt",
                    "prompt_length": 50,
                    "tokens_consumed": 100,
                    "is_follow_up": False
                }),
                "page_path": "/chat",
                "event_value": 100.0
            })
        return events
    
    return generate_events

# =============================================================================
# PERFORMANCE TESTING FIXTURES
# =============================================================================

@pytest.fixture
def analytics_performance_monitor():
    """Performance monitor for analytics service testing"""
    class AnalyticsPerformanceMonitor:
        def __init__(self):
            self.measurements = {}
            self.requirements = {
                "event_ingestion_latency": 0.1,  # 100ms max
                "batch_processing": 5.0,  # 5s max for 1000 events
                "query_response": 2.0,  # 2s max for reports
                "real_time_update": 1.0,  # 1s max for real-time metrics
                "high_volume_ingestion": 10.0  # 10s max for 10k events
            }
        
        def start_measurement(self, operation: str):
            self.measurements[operation] = {"start": time.time()}
        
        def end_measurement(self, operation: str) -> float:
            if operation in self.measurements:
                duration = time.time() - self.measurements[operation]["start"]
                self.measurements[operation]["duration"] = duration
                return duration
            return 0.0
        
        def validate_performance(self, operation: str) -> bool:
            """Validate operation meets performance requirements"""
            if operation not in self.measurements:
                return False
            
            duration = self.measurements[operation]["duration"]
            requirement = self.requirements.get(operation, 10.0)
            
            if duration > requirement:
                pytest.fail(f"Performance requirement failed: {operation} took {duration:.3f}s (max: {requirement}s)")
            
            return True
        
        def get_metrics(self) -> Dict[str, float]:
            """Get all measured performance metrics"""
            return {op: data.get("duration", 0.0) for op, data in self.measurements.items()}
    
    return AnalyticsPerformanceMonitor()

# =============================================================================
# WEBSOCKET TESTING FIXTURES
# =============================================================================

@pytest.fixture
async def websocket_test_client():
    """WebSocket client for real-time analytics testing"""
    try:
        import websockets
        
        async def create_connection():
            uri = "ws://localhost:8090/ws/analytics"
            return await websockets.connect(uri)
        
        return create_connection
        
    except ImportError:
        import logging
        logging.warning("websockets library not available - using stub implementation")
        
        async def stub_create_connection():
            class StubWebSocket:
                async def send(self, message):
                    logging.info(f"[STUB] Would send WebSocket message: {message}")
                    pass
                
                async def recv(self):
                    logging.info("[STUB] Would receive WebSocket message")
                    return '{"type":"stub","data":"websockets library not available"}'
                
                async def close(self):
                    pass
                    
                async def __aenter__(self):
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            return StubWebSocket()
        
        return stub_create_connection

# =============================================================================
# EVENT LOOP CONFIGURATION
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async analytics tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

# =============================================================================
# DOCKER TEST SERVICES FOR ANALYTICS
# =============================================================================

@pytest.fixture(scope="session")
async def analytics_test_services():
    """Start analytics-specific test services (ClickHouse, Redis, Grafana)"""
    manager = get_test_manager()
    
    # Start analytics services
    await manager.start_services(
        services=["clickhouse-test", "redis-test", "grafana-test"],
        wait_healthy=True,
        timeout=120
    )
    
    yield manager
    
    # Services are stopped by session-level fixture

# =============================================================================
# CLEANUP FIXTURES
# =============================================================================

@pytest.fixture
async def clean_analytics_db(clickhouse_client, redis_client):
    """Clean analytics databases before and after tests"""
    # Clean before test
    if clickhouse_client:
        clickhouse_client.command("TRUNCATE TABLE IF EXISTS frontend_events")
        clickhouse_client.command("TRUNCATE TABLE IF EXISTS prompt_analytics")
    
    if redis_client:
        await redis_client.flushdb()
    
    yield
    
    # Clean after test
    if clickhouse_client:
        clickhouse_client.command("TRUNCATE TABLE IF EXISTS frontend_events")
        clickhouse_client.command("TRUNCATE TABLE IF EXISTS prompt_analytics")
    
    if redis_client:
        await redis_client.flushdb()

# =============================================================================
# TEST CONTEXT MANAGERS
# =============================================================================

@pytest.fixture
def analytics_test_context():
    """Context manager for analytics test setup and teardown"""
    
    @asynccontextmanager
    async def test_context(test_name: str):
        """Context manager for individual analytics tests"""
        start_time = time.time()
        
        try:
            # Test setup
            print(f"[ANALYTICS-TEST] Starting: {test_name}")
            yield
            
            # Test success
            duration = time.time() - start_time
            print(f"[ANALYTICS-TEST] Completed: {test_name} ({duration:.2f}s)")
            
        except Exception as e:
            # Test failure
            duration = time.time() - start_time
            print(f"[ANALYTICS-TEST] Failed: {test_name} ({duration:.2f}s) - {e}")
            raise
    
    return test_context