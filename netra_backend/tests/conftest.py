"""
Backend-specific test configuration.
Depends on root /tests/conftest.py for common fixtures and environment setup.

# Setup Python path for imports
import sys
from pathlib import Path

# Add project root to Python path for netra_backend imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

"""

import os

# Import constants at module level only if not in collection mode  
if not os.environ.get("TEST_COLLECTION_MODE"):
    from netra_backend.app.core.network_constants import (
        DatabaseConstants,
        HostConstants,
        ServicePorts,
    )

# Set test environment variables BEFORE importing any app modules
# Use isolated values if TEST_ISOLATION is enabled

# CRITICAL: Set test collection mode to skip heavy initialization during pytest collection
os.environ["TEST_COLLECTION_MODE"] = "1"

if os.environ.get("TEST_ISOLATION") == "1":
    # When using test isolation, environment is already configured
    # Just ensure critical test flags are set

    os.environ.setdefault("TESTING", "1")

    os.environ.setdefault("ENVIRONMENT", "testing")

    os.environ.setdefault("LOG_LEVEL", "ERROR")

    os.environ.setdefault("DEV_MODE_DISABLE_CLICKHOUSE", "true")

    os.environ.setdefault("CLICKHOUSE_ENABLED", "false")
    
    # Ensure SERVICE_SECRET is set for test isolation mode
    os.environ.setdefault("SERVICE_SECRET", "test-service-secret-for-cross-service-auth-32-chars-minimum-length")

else:
    # Standard test environment setup

    os.environ["TESTING"] = "1"
    # Import network constants lazily only if not in collection mode
    if not os.environ.get("TEST_COLLECTION_MODE"):
        from netra_backend.app.core.network_constants import (
            DatabaseConstants,
            HostConstants, 
            ServicePorts,
        )
    
    # Use PostgreSQL URL format even for tests to satisfy validator
    if not os.environ.get("TEST_COLLECTION_MODE"):
        os.environ["DATABASE_URL"] = DatabaseConstants.build_postgres_url(
            user="test", password="test", 
            port=ServicePorts.POSTGRES_DEFAULT,
            database="netra_test"
        )

        os.environ["REDIS_URL"] = DatabaseConstants.build_redis_url(
            database=DatabaseConstants.REDIS_TEST_DB
        )

        os.environ["REDIS_HOST"] = HostConstants.LOCALHOST

        os.environ["REDIS_PORT"] = str(ServicePorts.REDIS_DEFAULT)
    else:
        # Use simple defaults during collection mode
        os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/netra_test"
        os.environ["REDIS_URL"] = "redis://localhost:6379/1"
        os.environ["REDIS_HOST"] = "localhost"
        os.environ["REDIS_PORT"] = "6379"

    os.environ["REDIS_USERNAME"] = ""

    os.environ["REDIS_PASSWORD"] = ""

    os.environ["TEST_DISABLE_REDIS"] = "true"

    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only-must-be-32-chars"

    os.environ["SERVICE_SECRET"] = "test-service-secret-for-cross-service-auth-32-chars-minimum-length"

    os.environ["FERNET_KEY"] = "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw="

    os.environ["ENVIRONMENT"] = "testing"

    os.environ["LOG_LEVEL"] = "ERROR"
    # Disable ClickHouse for tests

    os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"

    os.environ["CLICKHOUSE_ENABLED"] = "false"
    
    # Handle real LLM testing configuration

    if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
        # When real LLM testing is enabled, use actual API keys
        # These should be passed from the test runner
        # Ensure GOOGLE_API_KEY mirrors GEMINI_API_KEY for compatibility

        if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):

            os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
        
        # Validate that at least Gemini key is available for real LLM testing
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not gemini_key or gemini_key.startswith("test-"):
            import warnings
            warnings.warn(
                "ENABLE_REAL_LLM_TESTING=true but no valid Gemini API key found. "
                "Real LLM tests will fail. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.",
                stacklevel=2
            )

    else:
        # Use mock keys for regular testing

        os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

        os.environ.setdefault("GOOGLE_API_KEY", "test-gemini-api-key")  # Same as GEMINI

        os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")

        os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-api-key")

import pytest
import asyncio
from typing import Optional

# Always import logger - this is lightweight
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

# Only import heavy modules if not in collection mode
if not os.environ.get("TEST_COLLECTION_MODE"):
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    # Configuration imports moved to fixtures to avoid slow startup during test collection
    from netra_backend.app.core.configuration.base import get_unified_config

    # Database imports moved to fixtures to avoid slow startup during test collection
    from netra_backend.app.db.session import get_db_session
    from netra_backend.tests.conftest_helpers import (
        _create_mock_tool_dispatcher,
        _create_real_tool_dispatcher,
        _import_agent_classes,
        _instantiate_agents,
        _setup_basic_llm_mocks,
        _setup_performance_llm_mocks,
        _setup_websocket_interface_compatibility,
        _setup_websocket_test_mocks,
    )

# NOTE: Import main app lazily in fixtures to avoid slow startup during test collection
# The app will be imported when actually needed in fixtures, not during conftest loading

# Configure pytest with custom markers

def pytest_configure(config):

    """Configure pytest with custom markers"""

    config.addinivalue_line(

        "markers", "clickhouse: mark test as requiring ClickHouse"

    )

    config.addinivalue_line(

        "markers", "slow: mark test as slow running"

    )

    config.addinivalue_line(

        "markers", "integration: mark test as integration test"

    )

    config.addinivalue_line(

        "markers", 

        "performance: mark test as performance test"

    )

    config.addinivalue_line(

        "markers",

        "benchmark: mark test as benchmark test"

    )

    config.addinivalue_line(

        "markers", "e2e: mark test as end-to-end test"

    )

    config.addinivalue_line(

        "markers", "real_services: mark test as requiring real services"

    )

    config.addinivalue_line(

        "markers", "critical: mark test as critical business path"

    )

    config.addinivalue_line(

        "markers", "throughput: mark test as throughput test"

    )

# Database initialization moved to fixtures - no longer done at module level
# This avoids slow startup during test collection

# Event loop fixture is provided by root conftest.py

@pytest.fixture(scope="function")
def ensure_db_initialized():
    """Ensure database is initialized for tests that need it."""
    # Skip this fixture during collection mode
    if os.environ.get("TEST_COLLECTION_MODE"):
        return None
        
    from netra_backend.app.db.postgres import async_session_factory, initialize_postgres
    
    if async_session_factory is None:
        try:
            session_factory = initialize_postgres()
            if session_factory is None:
                pytest.skip("Database initialization returned None - database may not be available")
        except Exception as e:
            pytest.skip(f"Cannot initialize database for test: {e}")
    
    # Return the session factory for convenience
    return async_session_factory

@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    # Skip this fixture during collection mode
    if os.environ.get("TEST_COLLECTION_MODE"):
        yield None
        return
        
    # Import modules lazily to avoid slow startup during test collection
    from netra_backend.app.db.base import Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

    # Use in-memory SQLite for tests to avoid requiring real database
    # This ensures tests are isolated and fast
    test_database_url = "sqlite+aiosqlite:///:memory:"
    
    engine = create_async_engine(
        test_database_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        }
    )

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine
    finally:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception as e:
            logger.warning(f"Failed to drop test tables: {e}")
        finally:
            await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_engine):
    # Skip this fixture during collection mode
    if os.environ.get("TEST_COLLECTION_MODE"):
        yield None
        return
        
    # Skip if test_engine is None (happens during collection mode)
    if test_engine is None:
        yield None
        return
        
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@pytest.fixture(scope="function")
def client(db_session):
    """Create FastAPI test client with database session override."""
    # Skip this fixture during collection mode
    if os.environ.get("TEST_COLLECTION_MODE"):
        return None
        
    # Skip if db_session is None (happens during collection mode or engine issues)
    if db_session is None:
        return None
        
    # Import modules lazily to avoid startup during test collection
    from netra_backend.app.main import app
    from netra_backend.app.db.session import get_db_session
    from fastapi.testclient import TestClient

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    try:
        with TestClient(app) as c:
            yield c
    finally:
        # Clean up override
        if get_db_session in app.dependency_overrides:
            del app.dependency_overrides[get_db_session]

# Real LLM Testing Fixtures

@pytest.fixture(scope="function")
def real_llm_manager():
    """Create real LLM manager when ENABLE_REAL_LLM_TESTING=true, otherwise proper mock."""
    # Skip during collection mode
    if os.environ.get("TEST_COLLECTION_MODE"):
        return None
        
    if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
        # Use unified configuration system
        from netra_backend.app.config import get_unified_config as get_config
        from netra_backend.app.llm.llm_manager import LLMManager

        config = get_config()
        return LLMManager(config)
    else:
        return _create_mock_llm_manager()

def _create_mock_llm_manager():
    """Create properly configured async mock LLM manager."""
    from unittest.mock import AsyncMock, MagicMock

    # Use AsyncMock for async methods, regular Mock for sync methods
    mock_manager = AsyncMock()

    # Import helpers only if not in collection mode
    if not os.environ.get("TEST_COLLECTION_MODE"):
        from netra_backend.tests.conftest_helpers import _setup_basic_llm_mocks, _setup_performance_llm_mocks
        _setup_basic_llm_mocks(mock_manager)
        _setup_performance_llm_mocks(mock_manager)

    return mock_manager

@pytest.fixture(scope="function") 
def real_websocket_manager():
    """Create real WebSocket manager for E2E tests with interface compatibility."""
    # Skip during collection mode
    if os.environ.get("TEST_COLLECTION_MODE"):
        return None
        
    from netra_backend.app.websocket_core import UnifiedWebSocketManager as WebSocketManager

    manager = WebSocketManager()

    # Import helpers only if not in collection mode
    if not os.environ.get("TEST_COLLECTION_MODE"):
        from netra_backend.tests.conftest_helpers import _setup_websocket_interface_compatibility, _setup_websocket_test_mocks
        _setup_websocket_interface_compatibility(manager)
        _setup_websocket_test_mocks(manager)

    return manager

@pytest.fixture(scope="function")
def real_tool_dispatcher():
    """Create real tool dispatcher when needed, otherwise proper mock."""
    # Skip during collection mode
    if os.environ.get("TEST_COLLECTION_MODE"):
        return None
        
    # Import helpers only if not in collection mode
    if not os.environ.get("TEST_COLLECTION_MODE"):
        from netra_backend.tests.conftest_helpers import _create_real_tool_dispatcher, _create_mock_tool_dispatcher
        
        if os.environ.get("ENABLE_REAL_LLM_TESTING") == "true":
            return _create_real_tool_dispatcher()

        return _create_mock_tool_dispatcher()
    
    return None

@pytest.fixture(scope="function")

def real_agent_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):

    """Create real agent setup for E2E testing."""

    agents = _create_real_agents(real_llm_manager, real_tool_dispatcher)

    return _build_real_setup_dict(agents, real_llm_manager, real_websocket_manager, real_tool_dispatcher)

def _create_real_agents(llm_manager, tool_dispatcher):

    """Create real agent instances with proper dependencies."""

    agent_classes = _import_agent_classes()

    return _instantiate_agents(agent_classes, llm_manager, tool_dispatcher)

def _build_real_setup_dict(agents, llm_manager, websocket_manager, tool_dispatcher):
    """Build real setup dictionary for E2E tests."""
    import uuid

    return {
        'agents': agents, 'llm': llm_manager, 'websocket': websocket_manager,
        'dispatcher': tool_dispatcher, 'run_id': str(uuid.uuid4()), 'user_id': 'test-user-e2e'
    }

# Import database repository fixtures to make them available
# Use try-except to handle missing modules gracefully
try:
    pytest_plugins = ["netra_backend.tests.helpers.database_repository_fixtures"]
except ImportError:
    pytest_plugins = []

# =============================================================================
# AGENT TESTING FIXTURES
# Consolidated from netra_backend/tests/agents/conftest.py
# =============================================================================

def _setup_database_mock():

    """Create mock database session with standard async methods."""
    from unittest.mock import AsyncMock
    from sqlalchemy.ext.asyncio import AsyncSession

    db_session = AsyncMock(spec=AsyncSession)

    db_session.commit = AsyncMock()

    db_session.rollback = AsyncMock()

    db_session.close = AsyncMock()

    return db_session

async def _mock_call_llm(*args, **kwargs):

    """Mock LLM call returning optimization response."""

    return {

        "content": "Based on analysis, reduce costs by switching to efficient models.",

        "tool_calls": []

    }

async def _mock_ask_llm(*args, **kwargs):

    """Mock LLM ask returning structured JSON response."""
    import json

    return json.dumps({

        "category": "optimization",

        "analysis": "Cost optimization required",

        "recommendations": ["Switch to GPT-3.5 for low-complexity tasks", "Implement caching"]

    })

async def _mock_ask_structured_llm(prompt, llm_config_name, schema, **kwargs):

    """Mock structured LLM call with TriageResult support."""
    from unittest.mock import Mock
    from netra_backend.app.agents.triage_sub_agent.models import TriageResult

    if schema == TriageResult or hasattr(schema, '__name__') and 'TriageResult' in schema.__name__:

        return TriageResult(

            category="optimization", severity="medium",

            analysis="Cost optimization analysis for provided prompt",

            requirements=["cost reduction", "performance maintenance"],

            next_steps=["analyze_costs", "identify_optimization_opportunities"],

            data_needed=["current_costs", "usage_patterns"],

            suggested_tools=["cost_analyzer", "performance_monitor"]

        )

    try:

        return schema()

    except:

        return Mock()

def _setup_agent_llm_manager():

    """Create LLM manager mock with realistic response methods."""
    from unittest.mock import AsyncMock, Mock
    from netra_backend.app.llm.llm_manager import LLMManager

    llm_manager = Mock(spec=LLMManager)

    llm_manager.call_llm = AsyncMock(side_effect=_mock_call_llm)

    llm_manager.ask_llm = AsyncMock(side_effect=_mock_ask_llm)

    llm_manager.ask_structured_llm = AsyncMock(side_effect=_mock_ask_structured_llm)

    llm_manager.get = Mock(return_value=Mock())

    return llm_manager

def _setup_websocket_tool_dispatcher():

    """Create websocket manager and tool dispatcher mock."""
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.websocket_core import WebSocketManager

    websocket_manager = WebSocketManager()

    tool_dispatcher = Mock(spec=ToolDispatcher)

    tool_dispatcher.dispatch_tool = AsyncMock(return_value={

        "status": "success", "result": "Tool executed successfully"

    })

    tool_dispatcher.has_tool = Mock(return_value=True)

    return websocket_manager, tool_dispatcher

def _setup_core_services():

    """Create core business services."""
    from netra_backend.app.services.synthetic_data_service import SyntheticDataService
    from netra_backend.app.services.quality_gate_service import QualityGateService
    from netra_backend.app.services.corpus_service import CorpusService

    synthetic_service = SyntheticDataService()

    quality_service = QualityGateService()

    corpus_service = CorpusService()

    return synthetic_service, quality_service, corpus_service

def _setup_mock_services():

    """Create mock state persistence and apex tool selector services."""

    state_service = Mock()

    state_service.save_state = AsyncMock()

    state_service.load_state = AsyncMock(return_value=None)

    apex_selector = Mock()

    apex_selector.select_tools = AsyncMock(return_value=[])

    apex_selector.dispatch_tool = AsyncMock(return_value={"status": "success"})

    return state_service, apex_selector

def _setup_agents(db_session, llm_manager, websocket_manager, tool_dispatcher):

    """Create supervisor and agent service with proper configuration."""
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
    from netra_backend.app.services.agent_service import AgentService

    import uuid
    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())

    agent_service = AgentService(supervisor)

    agent_service.websocket_manager = websocket_manager

    return supervisor, agent_service

@pytest.fixture

def mock_dependencies():

    """Create mock dependencies for DataSubAgent and other tests"""

    llm_manager = _setup_agent_llm_manager()

    websocket_manager, tool_dispatcher = _setup_websocket_tool_dispatcher()

    return llm_manager, tool_dispatcher

@pytest.fixture

def agent(mock_dependencies):

    """Create DataSubAgent instance with mocked dependencies for test compatibility"""
    from unittest.mock import patch, Mock, AsyncMock
    from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
    
    llm_manager, tool_dispatcher = mock_dependencies

    with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager') as mock_redis_class:
        # Setup proper async mocks for redis operations

        mock_redis_instance = Mock()

        mock_redis_instance.get = AsyncMock()

        mock_redis_instance.set = AsyncMock()

        mock_redis_instance.delete = AsyncMock()

        mock_redis_instance.exists = AsyncMock()

        mock_redis_class.return_value = mock_redis_instance
        
        agent = DataSubAgent(llm_manager, tool_dispatcher)
        # Ensure redis_manager is properly mocked

        if hasattr(agent, 'redis_manager') and agent.redis_manager:

            agent.redis_manager.get = AsyncMock()

            agent.redis_manager.set = AsyncMock()

    return agent

@pytest.fixture

def service(agent):

    """Alias agent as service for integration test compatibility"""

    return agent

@pytest.fixture

def sample_performance_data():

    """Sample performance metrics data for testing"""

    return [

        {

            'time_bucket': '2024-01-01T12:00:00',

            'event_count': 100,

            'latency_p50': 50.0,

            'latency_p95': 95.0,

            'latency_p99': 99.0,

            'avg_throughput': 1000.0,

            'peak_throughput': 2000.0,

            'error_rate': 0.5,

            'total_cost': 10.0,

            'unique_workloads': 5

        }

    ]

@pytest.fixture

def sample_anomaly_data():

    """Sample anomaly detection data for testing"""

    return [

        {

            'timestamp': '2024-01-01T12:00:00',

            'value': 50.0,

            'avg_value': 50.0,

            'std_value': 10.0,

            'z_score': 0.0

        },

        {

            'timestamp': '2024-01-01T12:01:00',

            'value': 100.0,

            'avg_value': 50.0,

            'std_value': 10.0,

            'z_score': 5.0

        }

    ]

@pytest.fixture

def sample_usage_patterns():

    """Sample usage pattern data for testing"""

    return [

        {'day_of_week': 1, 'hour': 9, 'total_events': 1000, 'avg_latency': 50.0},

        {'day_of_week': 1, 'hour': 10, 'total_events': 1500, 'avg_latency': 45.0},

        {'day_of_week': 1, 'hour': 11, 'total_events': 2000, 'avg_latency': 55.0}

    ]

@pytest.fixture

def setup_real_infrastructure():

    """Setup infrastructure for real LLM tests."""
    # Use unified configuration system
    from netra_backend.app.config import get_unified_config as get_config

    config = get_config()

    db_session = _setup_database_mock()

    llm_manager = _setup_agent_llm_manager()

    websocket_manager, tool_dispatcher = _setup_websocket_tool_dispatcher()

    synthetic_service, quality_service, corpus_service = _setup_core_services()

    state_persistence_service, apex_tool_selector = _setup_mock_services()

    supervisor, agent_service = _setup_agents(db_session, llm_manager, websocket_manager, tool_dispatcher)

    return {

        "supervisor": supervisor, "agent_service": agent_service, "db_session": db_session, 

        "llm_manager": llm_manager, "websocket_manager": websocket_manager, 

        "tool_dispatcher": tool_dispatcher, "synthetic_service": synthetic_service, 

        "quality_service": quality_service, "quality_gate_service": quality_service, 

        "corpus_service": corpus_service, "state_persistence_service": state_persistence_service, 

        "apex_tool_selector": apex_tool_selector, "config": config

    }

# =============================================================================
# CLICKHOUSE TESTING FIXTURES
# Consolidated from netra_backend/tests/clickhouse/conftest.py
# =============================================================================

@pytest.fixture

def mock_clickhouse_client():

    """Mock ClickHouse client for testing"""

    client = AsyncMock()

    client.execute = AsyncMock(return_value=[])

    client.execute_query = AsyncMock(return_value=[])

    client.command = AsyncMock(return_value=None)

    client.insert_data = AsyncMock(return_value=None)

    client.test_connection = AsyncMock(return_value=True)

    client.disconnect = AsyncMock()

    return client

@pytest.fixture

def mock_db_session():

    """Mock database session"""
    from unittest.mock import MagicMock

    session = MagicMock()

    session.add = MagicMock()

    session.commit = MagicMock()

    session.refresh = MagicMock()

    session.delete = MagicMock()

    session.query = MagicMock()

    return session

@pytest.fixture

def sample_corpus_data():

    """Sample corpus data for testing"""

    return {

        "simple_chat": [

            ("Hello, how are you?", "I'm doing well, thank you!"),

            ("What's the weather?", "I don't have access to weather data.")

        ],

        "rag_pipeline": [

            ("Find information about Python", "Python is a high-level programming language..."),

            ("Search for ML algorithms", "Machine learning algorithms include...")

        ],

        "tool_use": [

            ("Calculate 2+2", "The result is 4"),

            ("Get current time", "The current time is 12:00 PM")

        ]

    }

@pytest.fixture

def sample_corpus_records():

    """Sample corpus records for validation testing"""

    return [

        {

            "workload_type": "simple_chat",

            "prompt": "Test prompt",

            "response": "Test response",

            "metadata": {"test": True}

        },

        {

            "workload_type": "rag_pipeline",

            "prompt": "Another prompt",

            "response": "Another response",

            "metadata": {"index": 1}

        }

    ]

# NOTE: mock_redis_manager is now provided by root conftest.py to avoid duplication

@pytest.fixture(autouse=True)

def setup_backend_test_environment(monkeypatch):

    """Set up backend-specific test environment variables"""
    # Backend-specific database configs (root conftest handles common env vars)

    monkeypatch.setenv("CLICKHOUSE_URL", "clickhouse://test:test@localhost:9000/test")

@pytest.fixture

def performance_metrics_data():

    """Sample performance metrics data"""

    return {

        "user_id": 123,

        "workload_id": "wl_test",

        "metrics": {

            "latency_ms": [100, 150, 200, 250, 300],

            "throughput": [1000, 1200, 800, 900, 1100],

            "cost_cents": [10, 12, 8, 9, 11]

        },

        "timestamps": [

            "2025-01-01T10:00:00",

            "2025-01-01T10:01:00",

            "2025-01-01T10:02:00",

            "2025-01-01T10:03:00",

            "2025-01-01T10:04:00"

        ]

    }

@pytest.fixture

def anomaly_detection_data():

    """Sample data for anomaly detection testing"""

    return {

        "baseline_values": [100, 102, 98, 101, 99, 103, 97, 100, 102, 98],

        "anomaly_values": [100, 102, 500, 101, 99],  # 500 is anomaly

        "metric_name": "latency_ms",

        "z_score_threshold": 2.0

    }

# =============================================================================
# PERFORMANCE TESTING FIXTURES  
# Consolidated from netra_backend/tests/performance/conftest.py
# =============================================================================

@pytest.fixture

def mock_settings():

    """Mock settings for performance tests"""

    mock_config = MagicMock()

    mock_config.clickhouse_https.host = "test-host"

    mock_config.clickhouse_https.port = 8443

    mock_config.clickhouse_https.user = "test-user"

    mock_config.clickhouse_https.password = "test-pass"

    mock_config.clickhouse_https.database = "test-db"

    mock_config.llm_configs = {'default': MagicMock(api_key="test-key")}

    return mock_config

@pytest.fixture

def mock_performance_websocket_manager():

    """Mock WebSocket manager for performance tests (renamed to avoid conflict)"""

    manager = AsyncMock()

    manager.broadcast = AsyncMock()

    return manager

@pytest.fixture

def performance_test_data():

    """Test data for performance benchmarks"""

    return {

        'small_corpus': {

            'simple_chat': [('prompt1', 'response1'), ('prompt2', 'response2')],

            'analysis': [('analysis1', 'result1')]

        },

        'medium_corpus': {

            'simple_chat': [(f'prompt_{i}', f'response_{i}') for i in range(100)],

            'analysis': [(f'analysis_{i}', f'result_{i}') for i in range(100)]

        }

    }

@pytest.fixture(autouse=True)

def setup_performance_environment(tmp_path, monkeypatch):

    """Set up environment for performance tests"""
    import os
    # Create temporary directories

    test_dir = tmp_path / "performance_test"

    test_dir.mkdir()
    
    corpus_dir = test_dir / "content_corpuses"

    corpus_dir.mkdir()
    
    # Set environment variables

    monkeypatch.setenv("CORPUS_TEST_DIR", str(corpus_dir))
    
    yield test_dir

@pytest.fixture

def cleanup_performance_files():

    """Clean up performance test files"""

    files_to_cleanup = []
    
    def register_cleanup(filepath: str):

        """Register file for cleanup"""

        files_to_cleanup.append(filepath)
    
    yield register_cleanup
    
    # Cleanup

    for filepath in files_to_cleanup:

        if os.path.exists(filepath):

            os.remove(filepath)

# =============================================================================
# AUTH TOKEN FIXTURES
# =============================================================================

@pytest.fixture
def test_auth_token():
    """Generate a test authentication token for E2E tests."""
    import jwt
    import time
    
    payload = {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "exp": int(time.time()) + 3600,  # 1 hour expiry
        "iat": int(time.time())
    }
    
    # Use a test secret key
    secret_key = "test_secret_key_for_e2e_testing"
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    
    return token

# =============================================================================
# WEBSOCKET MANAGER TESTING FIXTURES
# Consolidated from netra_backend/tests/ws_manager/conftest.py
# =============================================================================

class MockWebSocket:

    """Enhanced mock WebSocket for comprehensive testing"""

    def __init__(self, state=None):
        from starlette.websockets import WebSocketState
        from unittest.mock import AsyncMock

        self.client_state = state or WebSocketState.CONNECTED

        self.send_json = AsyncMock()

        self.close = AsyncMock()

        self.send_calls = []

        self.close_calls = []
    
    async def mock_send_json(self, data):

        self.send_calls.append(data)
    
    async def mock_close(self, code=1000, reason=""):

        self.close_calls.append({"code": code, "reason": reason})

        self.client_state = WebSocketState.DISCONNECTED

@pytest.fixture

def fresh_manager():

    """Create a fresh WebSocketManager instance for each test"""
    from netra_backend.app.websocket_core import WebSocketManager
    
    # Reset singleton

    WebSocketManager._instance = None

    WebSocketManager._initialized = False
    
    manager = WebSocketManager()

    yield manager
    
    # Clean up

    WebSocketManager._instance = None

@pytest.fixture

def mock_websocket():

    """Create a mock WebSocket"""

    return MockWebSocket()

@pytest.fixture

def connected_websocket():

    """Create a connected mock WebSocket"""
    from starlette.websockets import WebSocketState

    ws = MockWebSocket(WebSocketState.CONNECTED)

    ws.client_state = WebSocketState.CONNECTED

    return ws

@pytest.fixture

def disconnected_websocket():

    """Create a disconnected mock WebSocket"""

    ws = MockWebSocket(WebSocketState.DISCONNECTED)

    ws.client_state = WebSocketState.DISCONNECTED

    return ws

# =============================================================================
# REDIS CONNECTION FIXTURES
# =============================================================================

@pytest.fixture
async def real_redis_client():
    """
    Create a real Redis client for integration tests.
    
    This fixture properly handles the event loop issue by creating the Redis
    connection within the test's async context, not at module level.
    """
    if os.environ.get("TEST_COLLECTION_MODE"):
        # During test collection, yield a mock to avoid connection attempts
        from unittest.mock import AsyncMock
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=b'PONG')
        mock_client.aclose = AsyncMock()
        yield mock_client
        return
    
    redis_client: Optional['redis.asyncio.Redis'] = None
    
    try:
        # Import within the fixture to avoid module-level issues
        import redis.asyncio as redis
        
        # Get Redis URL from environment
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
        
        # Create Redis client within the async context
        redis_client = redis.from_url(redis_url, decode_responses=True)
        
        # Test the connection
        await redis_client.ping()
        
        logger.info(f"Connected to Redis at {redis_url} for testing")
        yield redis_client
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        # Fall back to mock if Redis is not available
        from unittest.mock import AsyncMock
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=b'PONG')
        mock_client.aclose = AsyncMock()
        
        # Add basic Redis operation mocks
        mock_client.get = AsyncMock(return_value=None)
        mock_client.set = AsyncMock()
        mock_client.setex = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.exists = AsyncMock(return_value=0)
        mock_client.incr = AsyncMock(return_value=1)
        mock_client.expire = AsyncMock()
        
        logger.warning("Using mock Redis client due to connection failure")
        yield mock_client
    
    finally:
        if redis_client and hasattr(redis_client, 'aclose'):
            try:
                await redis_client.aclose()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

@pytest.fixture
async def isolated_redis_client():
    """
    Create an isolated Redis client with a unique database for each test.
    
    This ensures test isolation by using different Redis databases.
    """
    if os.environ.get("TEST_COLLECTION_MODE"):
        # During test collection, yield a mock
        from unittest.mock import AsyncMock
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=b'PONG')
        mock_client.aclose = AsyncMock()
        yield mock_client
        return
    
    redis_client: Optional['redis.asyncio.Redis'] = None
    
    try:
        import redis.asyncio as redis
        import random
        
        # Use a random database number for isolation (Redis supports 0-15 by default)
        db_num = random.randint(2, 15)  # Avoid 0 (default) and 1 (test default)
        base_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        
        # Replace the database number in the URL
        if base_url.endswith(('/0', '/1')):
            redis_url = base_url[:-2] + f'/{db_num}'
        else:
            redis_url = f"{base_url.rstrip('/')}/{db_num}"
        
        redis_client = redis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        
        # Clear any existing data in this database
        await redis_client.flushdb()
        
        logger.info(f"Created isolated Redis client using database {db_num}")
        yield redis_client
        
        # Clean up the test database
        await redis_client.flushdb()
        
    except Exception as e:
        logger.error(f"Failed to create isolated Redis client: {e}")
        # Fall back to mock
        from unittest.mock import AsyncMock
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=b'PONG')
        mock_client.aclose = AsyncMock()
        
        # Add data storage simulation for tests
        mock_data = {}
        
        async def mock_get(key):
            return mock_data.get(key)
        
        async def mock_setex(key, ttl, value):
            mock_data[key] = value
        
        async def mock_delete(key):
            mock_data.pop(key, None)
        
        async def mock_exists(key):
            return 1 if key in mock_data else 0
        
        async def mock_incr(key):
            current_value = int(mock_data.get(key, "0"))
            new_value = current_value + 1
            mock_data[key] = str(new_value)
            return new_value
        
        mock_client.get = mock_get
        mock_client.setex = mock_setex
        mock_client.delete = mock_delete
        mock_client.exists = mock_exists
        mock_client.incr = mock_incr
        mock_client.expire = AsyncMock()
        mock_client.flushdb = AsyncMock()
        
        yield mock_client
    
    finally:
        if redis_client and hasattr(redis_client, 'aclose'):
            try:
                await redis_client.aclose()
            except Exception as e:
                logger.error(f"Error closing isolated Redis connection: {e}")