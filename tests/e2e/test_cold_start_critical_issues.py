from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Critical Cold Start Integration Tests
Tests the most common and difficult initialization issues that occur during system startup.
Tests real services with dev launcher (local DB, Redis, ClickHouse).
"""

import asyncio
import os
import sys
import time
import pytest
import psycopg2
import httpx
from httpx import ASGITransport
import websockets
import json
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import subprocess
import signal
from typing import Dict, Any, Optional, List
from pathlib import Path
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.e2e.integration.service_orchestrator import E2EServiceOrchestrator
from tests.e2e.integration.unified_e2e_harness import UnifiedE2ETestHarness
from netra_backend.app.db.database_manager import DatabaseManager
from auth_service.auth_core.core.session_manager import SessionManager
from netra_backend.app.db.postgres import Database
from netra_backend.app.redis_manager import RedisManager
from database_scripts.create_postgres_tables import create_all_tables


@pytest.mark.e2e
class TestColdStartCriticalIssues:
    """Test suite for critical cold start initialization issues."""

    @pytest.fixture(autouse=True)
    async def setup_method(self):
        """Set up test environment."""
        self.orchestrator = E2EServiceOrchestrator()
        self.harness = UnifiedE2ETestHarness()
        self.base_url = "http://localhost:8000"
        self.auth_url = "http://localhost:8083"
        self.frontend_url = "http://localhost:3000"
        
    async def cleanup(self):
        """Clean up test resources."""
        if hasattr(self, 'orchestrator'):
            await self.orchestrator.cleanup()

    # Journey 1: Cold Start Development Environment Initialization

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_table_missing_on_fresh_installation(self):
        """Test 1.1: Database hangs indefinitely when tables don't exist."""
        # Drop all tables to simulate fresh installation
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="netra_test",
                user="postgres",
                password="postgres",
                connect_timeout=5
            )
        except psycopg2.OperationalError as e:
            # CLAUDE.md: TESTS MUST RAISE ERRORS - No skipping for critical system functionality
            raise AssertionError(f"Test database must be available for E2E cold start validation: {e}") from e
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.commit()
        conn.close()
        
        # Attempt to start backend without tables
        start_time = time.time()
        timeout_occurred = False
        
        try:
            # This should hang without proper table creation
            process = subprocess.Popen(
                ["python", "-m", "netra_backend.main"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for 30 seconds to detect hanging
            process.wait(timeout=30)
            
        except subprocess.TimeoutExpired:
            timeout_occurred = True
            process.kill()
            
        assert timeout_occurred, "Backend should hang without database tables"
        assert time.time() - start_time > 25, "Should timeout after significant wait"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_environment_variable_mapping_mismatch(self):
        """Test 1.2: Critical services fail due to env var name conflicts."""
        # Set environment variable
        
        # Attempt ClickHouse connection with mismatched passwords
        from netra_backend.app.db.clickhouse import ClickHouseService
        
        with pytest.raises(Exception) as exc_info:
            ch_service = ClickHouseService()
            await ch_service.test_connection()
            
        assert "missing secrets" in str(exc_info.value).lower() or \
               "authentication" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_service_port_conflicts_during_startup(self):
        """Test 1.3: Hard-coded port assignments cause service startup failures."""
        # Pre-bind ports to cause conflicts
        import socket
        
        sockets = []
        ports = [8080, 8081, 8082]
        
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('localhost', port))
            s.listen(1)
            sockets.append(s)
            
        try:
            # Attempt to start dev launcher
            from dev_launcher.__main__ import DevLauncher
            launcher = DevLauncher()
            
            with pytest.raises(Exception) as exc_info:
                await launcher.start_services()
                
            assert "port already in use" in str(exc_info.value).lower()
            
        finally:
            for s in sockets:
                s.close()

    # Journey 2: Google OAuth First-Time User Registration

    @pytest.mark.asyncio  
    @pytest.mark.e2e
    async def test_oauth_state_parameter_validation_race_condition(self):
        """Test 2.1: Concurrent OAuth flows cause state validation failures."""
        async def initiate_oauth_flow():
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{self.auth_url}/auth/login")
                return response.json()
                
        # Initiate 5 concurrent OAuth flows
        tasks = [initiate_oauth_flow() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for state validation failures
        failures = [r for r in results if isinstance(r, Exception) or 
                    (isinstance(r, dict) and "state" in str(r).lower())]
        
        assert len(failures) > 0, "Concurrent OAuth flows should cause state conflicts"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_jwt_secret_environment_variable_mismatch(self):
        """Test 2.2: Auth service and backend use different JWT secret variables."""
        # Set different JWT secrets
        
        # Generate token with auth service secret
        session_mgr = SessionManager()
        token = session_mgr.create_session({
            "user_id": "test_user",
            "email": "test@example.com"
        })
        
        # Try to validate with backend secret
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        jwt_handler = JWTHandler()
        
        with pytest.raises(Exception) as exc_info:
            jwt_handler.verify_token(token)
            
        assert "signature" in str(exc_info.value).lower() or \
               "invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_user_creation_transaction_rollback(self):
        """Test 2.3: User creation partially completes then fails."""
        db_manager = DatabaseManager()
        
        # Simulate connection loss mid-transaction
        async def interrupt_transaction():
            await asyncio.sleep(0.1)
            # Force close database connection
            if hasattr(db_manager, 'connection'):
                await db_manager.connection.close()
                
        # Start user creation and interrupt
        create_task = asyncio.create_task(
            db_manager.create_user({
                "email": "partial@example.com",
                "name": "Partial User",
                "google_id": "google_123"
            })
        )
        interrupt_task = asyncio.create_task(interrupt_transaction())
        
        results = await asyncio.gather(create_task, interrupt_task, 
                                      return_exceptions=True)
        
        # Check for partial user state
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="netra_test",
            user="postgres", 
            password="postgres"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = 'partial@example.com'")
        partial_user = cursor.fetchone()
        conn.close()
        
        assert partial_user is not None, "Partial user record should exist"
        assert isinstance(results[0], Exception), "User creation should have failed"

    # Journey 3: Authenticated WebSocket Connection Setup

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_routes_not_registered(self):
        """Test 3.1: WebSocket endpoints return 404 errors."""
        # Start backend without WebSocket routes registered
        with patch('netra_backend.app.app_factory_route_imports.register_websocket_routes'):
            from netra_backend.main import app
            
            async with httpx.AsyncClient(transport=ASGITransport(app=app)) as client:
                # Attempt WebSocket connection
                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    response = await client.get("/ws")
                    
                assert exc_info.value.response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_blocking_websocket_upgrade_requests(self):
        """Test 3.2: CORS policies prevent WebSocket handshake completion."""
        # Configure strict CORS without WebSocket support
        
        # Attempt WebSocket from different origin
        headers = {
            "Origin": "http://localhost:3000",
            "Host": "localhost:8000"
        }
        
        with pytest.raises(websockets.exceptions.InvalidStatus) as exc_info:
            async with websockets.connect(
                "ws://localhost:8000/ws",
                extra_headers=headers
            ) as ws:
                # CLAUDE.md: E2E tests must attempt real operations, not just pass
                # This should fail due to 403 auth error - connection attempt validates the error occurs
                await ws.send(json.dumps({"type": "test", "data": "unauthorized_attempt"}))
                
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_authentication_context_missing_during_websocket(self):
        """Test 3.3: WebSocket connections fail due to missing user context."""
        # Create valid JWT but don't create user in database
        session_mgr = SessionManager()
        token = session_mgr.create_session({
            "user_id": "nonexistent_user",
            "email": "ghost@example.com"
        })
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        with pytest.raises(websockets.exceptions.InvalidStatus) as exc_info:
            async with websockets.connect(
                "ws://localhost:8000/ws",
                extra_headers=headers
            ) as ws:
                # CLAUDE.md: E2E tests must attempt real operations, not just pass
                # This should fail due to 403 auth error - connection attempt validates the error occurs
                await ws.send(json.dumps({"type": "test", "data": "unauthorized_attempt"}))
                
        assert exc_info.value.status_code == 403

    # Journey 4: Next.js Frontend Cold Start Compilation and Load

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_environment_configuration_mismatch(self):
        """Test 4.1: Frontend pointing to wrong service ports/URLs."""
        # Set frontend to use static ports
        env_path = Path("frontend/.env.local")
        env_path.write_text("""
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AUTH_URL=http://localhost:8083
        """)
        
        # Start backend on different dynamic port
        
        # Try frontend API call
        async with httpx.AsyncClient(follow_redirects=True) as client:
            with pytest.raises(httpx.ConnectError):
                await client.get("http://localhost:3000/api/health")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_provider_context_initialization_failure(self):
        """Test 4.2: React context providers fail to initialize with auth service."""
        # Stop auth service
        subprocess.run(["pkill", "-f", "auth_service"], capture_output=True)
        
        # Start frontend and check for errors
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd="frontend",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        await asyncio.sleep(5)
        stderr_output = process.stderr.read().decode()
        process.terminate()
        
        assert "AuthProvider" in stderr_output or "auth" in stderr_output.lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_typescript_compilation_errors_missing_types(self):
        """Test 4.3: Missing type definitions prevent compilation."""
        # Remove a critical @types package
        subprocess.run(
            ["npm", "uninstall", "@types/react"],
            cwd="frontend",
            capture_output=True
        )
        
        # Attempt to build frontend
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd="frontend",
            capture_output=True
        )
        
        assert result.returncode != 0
        assert "type" in result.stderr.decode().lower()

    # Journey 5: Development Mode Quick Authentication

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_dev_mode_user_creation_without_database_setup(self):
        """Test 5.1: Create dev user fails when database tables don't exist."""
        # Drop user tables
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="netra_test",
            user="postgres",
            password="postgres"
        )
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS users CASCADE")
        conn.commit()
        conn.close()
        
        # Attempt dev mode login
        async with httpx.AsyncClient(follow_redirects=True) as client:
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                response = await client.post(
                    f"{self.auth_url}/auth/dev/login",
                    json={"email": "dev@example.com"}
                )
                
            assert "sql" in str(exc_info.value).lower() or \
                   "table" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_jwt_token_generation_missing_required_claims(self):
        """Test 5.2: Generated tokens lack required 'iss' claim."""
        # Patch JWT generation to skip issuer
        # Mock: Session state isolation for predictable testing
        with patch('auth_service.auth_core.core.session_manager.SessionManager.create_session') as mock_create:
            mock_create.return_value = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIn0.test"
            
            session_mgr = SessionManager()
            token = session_mgr.create_session({"user_id": "123"})
            
            # Validate token
            jwt_handler = JWTHandler()
            
            with pytest.raises(Exception) as exc_info:
                jwt_handler.verify_token(token)
                
            assert "iss" in str(exc_info.value) or "issuer" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_session_storage_redis_connection_failure(self):
        """Test 5.3: Authentication succeeds but session storage fails."""
        # Stop Redis
        subprocess.run(["pkill", "-f", "redis-server"], capture_output=True)
        
        # Attempt login
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                f"{self.auth_url}/auth/dev/login",
                json={"email": "dev@example.com"}
            )
            
            # Login appears successful
            assert response.status_code == 200
            token = response.json()["token"]
            
            # But subsequent requests fail
            with pytest.raises(httpx.HTTPStatusError):
                await client.get(
                    f"{self.base_url}/api/user",
                    headers={"Authorization": f"Bearer {token}"}
                )

    # Journey 6: PostgreSQL and ClickHouse Database Initialization

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_clickhouse_port_configuration_wrong_protocol(self):
        """Test 6.1: HTTPS port 8443 used instead of HTTP port 8123."""
        
        ch_conn = ClickHouseConnection()
        
        with pytest.raises(Exception) as exc_info:
            await ch_conn.connect()
            
        assert "https" in str(exc_info.value).lower() or \
               "connection" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_postgresql_connection_pool_exhaustion(self):
        """Test 6.2: Connection pool depleted during startup health checks."""
        # Set very small connection pool
        
        db = Database()
        
        # Create multiple concurrent connections
        async def get_connection():
            return await db.get_connection()
            
        tasks = [get_connection() for _ in range(5)]
        
        with pytest.raises(Exception) as exc_info:
            await asyncio.gather(*tasks)
            
        assert "pool" in str(exc_info.value).lower() or \
               "exhausted" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_migration_version_mismatch(self):
        """Test 6.3: Code expects newer database schema than exists."""
        # Simulate older schema by removing a column
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="netra_test",
            user="postgres",
            password="postgres"
        )
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE threads DROP COLUMN IF EXISTS created_at")
        conn.commit()
        conn.close()
        
        # Try to query with new schema expectations
        from netra_backend.app.services.database.thread_repository import ThreadRepository
        repo = ThreadRepository()
        
        with pytest.raises(Exception) as exc_info:
            await repo.get_thread("test_thread")
            
        assert "column" in str(exc_info.value).lower() or \
               "created_at" in str(exc_info.value).lower()

    # Journey 7: End-to-End Message Processing with AI Agent

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_llm_api_key_missing_or_invalid(self):
        """Test 7.1: Agent execution fails due to missing GEMINI_API_KEY."""
        # Remove API key
            
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.config import get_config
        
        # CLAUDE.md: E2E tests MUST use real services - No mocks/fakes allowed
        # Create real service dependencies for E2E testing
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        from netra_backend.app.tools.dispatcher import ToolDispatcher
        
        config = get_config()
        database_manager = DatabaseManager(config)
        db_session = await database_manager.get_session()
        llm_manager = LLMManager(config)
        websocket_manager = WebSocketManagerFactory.create_manager()
        tool_dispatcher = ToolDispatcher(config)
        
        agent = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        from netra_backend.app.agents.state import DeepAgentState
        
        # Create proper state object
        state = DeepAgentState(
            thread_id="test",
            user_id="user123",
            message="Hello"
        )
        
        with pytest.raises(Exception) as exc_info:
            await agent.execute(state, run_id="test_run", stream_updates=False)
            
        assert "api" in str(exc_info.value).lower() and \
               "key" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_agent_state_persistence_database_failure(self):
        """Test 7.2: Agent state cannot be saved due to database issues."""
        # Simulate intermittent database failures
        original_execute = Database.execute
        
        call_count = [0]
        async def failing_execute(self, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 0:  # Fail every 3rd call
                raise Exception("Database connection lost")
            return await original_execute(self, *args, **kwargs)
            
        Database.execute = failing_execute
        
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.config import get_config
        
        # CLAUDE.md: E2E tests MUST use real services - No mocks/fakes allowed
        # Create real service dependencies for E2E testing
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        from netra_backend.app.tools.dispatcher import ToolDispatcher
        
        config = get_config()
        database_manager = DatabaseManager(config)
        db_session = await database_manager.get_session()
        llm_manager = LLMManager(config)
        websocket_manager = WebSocketManagerFactory.create_manager()
        tool_dispatcher = ToolDispatcher(config)
        
        agent = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
        
        from netra_backend.app.agents.state import DeepAgentState
        
        # Create proper state object
        state = DeepAgentState(
            thread_id="test",
            user_id="user123",
            message="Test message"
        )
        
        with pytest.raises(Exception) as exc_info:
            await agent.execute(state, run_id="test_run", stream_updates=False)
            
        assert "database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_background_task_timeout_causing_crash(self):
        """Test 7.3: Background index optimization hangs causing 4-minute crash."""
        # Start backend and monitor for crash
        process = subprocess.Popen(
            ["python", "-m", "netra_backend.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait 5 minutes
        await asyncio.sleep(300)
        
        # Check if process crashed
        return_code = process.poll()
        
        if return_code is None:
            process.terminate()
            assert False, "Process should have crashed within 4-5 minutes"
        else:
            assert return_code == 1, "Backend should exit with code 1"

    # Journey 8: New Chat Thread Creation and State Management

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_thread_id_generation_race_condition(self):
        """Test 8.1: Concurrent thread creation generates duplicate IDs."""
        async def create_thread():
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.post(
                    f"{self.base_url}/api/threads",
                    json={"name": "Test Thread"},
                    headers={"Authorization": "Bearer test_token"}
                )
                return response.json()["thread_id"]
                
        # Create 10 threads simultaneously
        tasks = [create_thread() for _ in range(10)]
        thread_ids = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for duplicates
        valid_ids = [tid for tid in thread_ids if not isinstance(tid, Exception)]
        assert len(valid_ids) != len(set(valid_ids)), "Should have duplicate thread IDs"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_connection_state_not_synchronized(self):
        """Test 8.2: Thread created in database but WebSocket not notified."""
        # Connect WebSocket client
        ws_messages = []
        
        async def ws_listener():
            async with websockets.connect("ws://localhost:8000/ws") as ws:
                while True:
                    msg = await ws.recv()
                    ws_messages.append(json.loads(msg))
                    
        listener_task = asyncio.create_task(ws_listener())
        await asyncio.sleep(1)
        
        # Create thread via API
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                f"{self.base_url}/api/threads",
                json={"name": "Test Thread"}
            )
            thread_id = response.json()["thread_id"]
            
        await asyncio.sleep(2)
        listener_task.cancel()
        
        # Check if WebSocket received update
        thread_updates = [m for m in ws_messages if m.get("thread_id") == thread_id]
        assert len(thread_updates) == 0, "WebSocket should not receive thread updates"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_memory_management_large_thread_history(self):
        """Test 8.3: Large thread history causes memory exhaustion."""
        import psutil
        
        # Monitor initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create thread with 1000+ messages
        repo = ThreadRepository()
        
        thread_id = await repo.create_thread({
            "user_id": "test_user",
            "name": "Large Thread"
        })
        
        # Add many messages
        for i in range(1000):
            await repo.add_message(thread_id, {
                "content": f"Message {i}" * 100,  # Large message
                "role": "user"
            })
            
        # Check memory growth
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        assert memory_growth > 500, "Should consume significant memory without pruning"

    # Journey 9: System Health Validation Across All Services

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_health_check_cascade_failures(self):
        """Test 9.1: Single service failure causes all health checks to fail."""
        # Stop auth service
        subprocess.run(["pkill", "-f", "auth_service"], capture_output=True)
        await asyncio.sleep(2)
        
        # Check health of other services
        async with httpx.AsyncClient(follow_redirects=True) as client:
            backend_health = await client.get(f"{self.base_url}/health")
            
        # Backend should report unhealthy due to auth dependency
        health_data = backend_health.json()
        assert health_data["status"] == "unhealthy"
        assert "auth" in str(health_data).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_health_check_database_query_timeout(self):
        """Test 9.2: Health checks hang on database queries without timeout."""
        # Simulate slow database
        # Mock: Database access isolation for fast, reliable unit testing
        with patch('netra_backend.app.db.postgres.Database.execute') as mock_execute:
            async def slow_query(*args, **kwargs):
                await asyncio.sleep(30)  # 30 second delay
                
            mock_execute.side_effect = slow_query
            
            start_time = time.time()
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                with pytest.raises(httpx.TimeoutException):
                    await client.get(
                        f"{self.base_url}/health",
                        timeout=15.0
                    )
                    
            elapsed = time.time() - start_time
            assert elapsed > 10, "Health check should timeout"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_startup_check_failure_in_staging(self):
        """Test 9.3: Non-critical failures treated as critical in staging."""
        # Set staging environment
        
        # Start backend
        process = subprocess.Popen(
            ["python", "-m", "netra_backend.main"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup
        await asyncio.sleep(5)
        
        # Check if process crashed
        return_code = process.poll()
        
        if return_code is None:
            process.terminate()
            assert False, "Should continue running despite minor failure"
        else:
            assert return_code != 0, "Should crash immediately in staging"

    # Journey 10: Redis Cache Initialization and Session Storage

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_redis_remote_connection_no_local_fallback(self):
        """Test 10.1: Attempts to connect to remote Redis with no fallback."""
        # Set remote Redis URL
        
        redis_mgr = RedisManager()
        
        with pytest.raises(Exception) as exc_info:
            await redis_mgr.connect()
            
        assert "connection" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_redis_memory_eviction_during_session_storage(self):
        """Test 10.2: Active sessions evicted due to Redis memory limits."""
        # Connect to Redis
        r = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6379)
        
        # Fill Redis memory with data
        for i in range(10000):
            r.set(f"dummy_key_{i}", "x" * 1000)
            
        # Create session
        session_mgr = SessionManager()
        session_token = session_mgr.create_session({
            "user_id": "test_user",
            "email": "test@example.com"
        })
        
        # Add more data to trigger eviction
        for i in range(10000, 20000):
            r.set(f"dummy_key_{i}", "x" * 1000)
            
        # Try to validate session
        session_data = session_mgr.get_session(session_token)
        assert session_data is None, "Session should be evicted"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_redis_cluster_configuration_mismatch(self):
        """Test 10.3: Single Redis client used with cluster configuration."""
        # Configure Redis as cluster but use single-node client
        
        redis_mgr = RedisManager()
        
        # Try operations that would fail with cluster
        with pytest.raises(Exception) as exc_info:
            await redis_mgr.set("test_key", "value")
            await redis_mgr.get("test_key")
            
        assert "moved" in str(exc_info.value).lower() or \
               "ask" in str(exc_info.value).lower()