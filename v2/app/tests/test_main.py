import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet

# Mock all settings using environment variables
@pytest.fixture(scope="module", autouse=True)
def mock_settings():
    with patch.dict('os.environ', {
        'environment': 'testing',
        'SECRET_KEY': 'test_secret',
        'POSTGRES_USER': 'testuser',
        'POSTGRES_PASSWORD': 'testpassword',
        'POSTGRES_DB': 'testdb',
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432',
        'CLICKHOUSE_HOST': 'localhost',
        'CLICKHOUSE_PORT': '9000',
        'CLICKHOUSE_USER': 'default',
        'CLICKHOUSE_PASSWORD': '',
        'CLICKHOUSE_DATABASE': 'testdb',
        'OPENAI_API_KEY': 'test_key',
        'GOOGLE_API_KEY': 'test_key',
        'ANTHROPIC_API_KEY': 'test_key',
        'GOOGLE_CLIENT_ID': 'test_id',
        'GOOGLE_CLIENT_SECRET': 'test_secret',
        'GOOGLE_REDIRECT_URI': 'http://localhost/auth/google/callback',
    }, clear=True):
        yield

# Module-scoped mock for the database session
@pytest.fixture(scope="module")
def mock_db_session_module():
    return AsyncMock(spec=AsyncSession)

# This fixture creates the test client and handles dependency overrides
@pytest.fixture(scope="module")
def client(mock_db_session_module):
    # Create a mock KeyManager that can be used by the SecurityService
    mock_key_manager = MagicMock()
    mock_key_manager.fernet_key = Fernet.generate_key()

    # Patch services that are initialized during app startup (lifespan)
    # The patches must target where the objects are looked up (i.e., in 'app.main')
    with patch('app.main.KeyManager.load_from_settings', return_value=mock_key_manager), \
         patch('app.main.LLMManager', autospec=True), \
         patch('app.logging_config.central_logger.clickhouse_db', autospec=True), \
         patch('app.main.NetraOptimizerAgentSupervisor', autospec=True), \
         patch('app.main.StreamingAgentSupervisor', autospec=True), \
         patch('app.main.AgentService', autospec=True):

        # Import the app *after* the patches have been applied
        from app.main import app
        from app.db.postgres import get_async_db

        # Setup dependency override for the database
        async def override_get_db():
            yield mock_db_session_module

        app.dependency_overrides[get_async_db] = override_get_db
        
        with TestClient(app) as c:
            yield c
    
        # Clean up the override after tests are done
        app.dependency_overrides.clear()

# This fixture runs before each test to reset the state of the mock
@pytest.fixture(autouse=True)
def reset_db_mock(mock_db_session_module):
    mock_db_session_module.reset_mock()
    mock_db_session_module.execute.reset_mock()
    mock_db_session_module.execute.side_effect = None

def test_read_root(client):
    """Tests the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Netra API v2"}

def test_live_probe(client):
    """Tests the liveness probe."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready_probe_success(client, mock_db_session_module):
    """Tests the readiness probe when all services are healthy."""
    with patch('app.logging_config.central_logger.clickhouse_db.ping', return_value=True) as mock_ping:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_db_session_module.execute.assert_awaited_once()
        mock_ping.assert_called_once()

def test_ready_probe_postgres_failure(client, mock_db_session_module):
    """Tests the readiness probe when the Postgres database connection fails."""
    mock_db_session_module.execute.side_effect = Exception("Postgres connection failed")
    
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Service Unavailable"}
    mock_db_session_module.execute.assert_awaited_once()

def test_ready_probe_clickhouse_failure(client, mock_db_session_module):
    """Tests the readiness probe when the ClickHouse database connection fails."""
    with patch('app.logging_config.central_logger.clickhouse_db.ping', return_value=False) as mock_ping:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"detail": "Service Unavailable"}
        mock_db_session_module.execute.assert_awaited_once()
        mock_ping.assert_called_once()