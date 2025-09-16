from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'\nComprehensive test suite for dev launcher critical path.\n\nTests are designed to FAIL initially to expose real issues.\nThese tests use REAL services with MINIMAL mocking.\n\nCritical Path Coverage:\n1. Startups clear without errors (real errors fixed, not silenced)\n2. Inter-service connections work\n3. Dev login and OAuth work (clearing CORS, port issues, etc.)\n4. Users can login and send tokens back\n5. WebSockets automatically connect\n6. Chat and UI/UX load properly\n7. Users can send sample prompts\n8. Model processes run and return responses\n9. Users see messages during processing\n\nRunning:\n    python -m pytest tests/e2e/integration/test_dev_launcher_critical_path.py -v\n    python -m pytest tests/e2e/integration/test_dev_launcher_critical_path.py -v -m critical\n    python -m pytest tests/e2e/integration/test_dev_launcher_critical_path.py -v -m performance\n'
import pytest
import asyncio
import subprocess
import httpx
import websockets
import json
import time
import psutil
import os
import sys
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import platform
STARTUP_TIME_LIMIT = 30
MEMORY_LIMIT_MB = 500
CPU_SETTLE_TIME = 10
CPU_IDLE_THRESHOLD = 10
BACKEND_PORT = 8000
FRONTEND_PORT = 3000
AUTH_PORT = 8081
BACKEND_URL = f'http://localhost:{BACKEND_PORT}'
FRONTEND_URL = f'http://localhost:{FRONTEND_PORT}'
AUTH_URL = f'http://localhost:{AUTH_PORT}'
WS_URL = f'ws://localhost:{BACKEND_PORT}/ws'

@pytest.mark.e2e
class TestDevLauncherCriticalPath:
    """
    Comprehensive test suite for dev launcher critical path.
    Tests are designed to FAIL initially to expose real issues.
    """

    @pytest.fixture(autouse=True)
    async def setup_and_cleanup(self):
        """Clean environment before and after each test."""
        await self._cleanup_environment()
        self.test_start_time = time.time()
        yield
        await self._cleanup_environment()
        await self._verify_cleanup()

    async def _cleanup_environment(self):
        """Kill existing processes and clear ports."""
        if platform.system() == 'Windows':
            processes_to_kill = ['node.exe', 'python.exe', 'uvicorn', 'next-server']
            for process in processes_to_kill:
                subprocess.run(f'taskkill /F /IM {process}', shell=True, capture_output=True)
            for port in [BACKEND_PORT, FRONTEND_PORT, AUTH_PORT]:
                subprocess.run(f'netstat -ano | findstr :{port}', shell=True, capture_output=True)
        else:
            subprocess.run("pkill -f 'uvicorn|next|node'", shell=True, capture_output=True)
            for port in [BACKEND_PORT, FRONTEND_PORT, AUTH_PORT]:
                subprocess.run(f'lsof -ti:{port} | xargs kill -9', shell=True, capture_output=True)
        await asyncio.sleep(2)

    async def _verify_cleanup(self):
        """Verify that cleanup was successful and ports are free."""
        ports_in_use = []
        for port in [BACKEND_PORT, FRONTEND_PORT, AUTH_PORT]:
            if self._is_port_in_use(port):
                ports_in_use.append(port)
        if ports_in_use:
            pytest.fail(f'Ports still in use after cleanup: {ports_in_use}')

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    @pytest.mark.critical
    @pytest.mark.timeout(60)
    @pytest.mark.e2e
    async def test_cold_start_complete_system(self):
        """
        Test complete system startup from clean state.
        This test MUST FAIL initially to expose real startup issues.
        """
        start_time = time.time()
        project_root = Path(__file__).parent.parent.parent.parent
        launcher_script = project_root / 'scripts' / 'dev_launcher.py'
        env = get_env().as_dict().copy()
        env.update({'NETRA_ENV': 'development', 'DATABASE_URL': 'postgresql://localhost/netra_dev', 'REDIS_URL': 'redis://localhost:6379', 'CLICKHOUSE_URL': 'http://localhost:8123', 'USE_SHARED_LLM': 'true', 'PYTHONPATH': str(project_root)})
        process = subprocess.Popen([sys.executable, str(launcher_script), '--no-browser', '--no-secrets'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            services_ready = await self._wait_for_services_ready(timeout=30)
            startup_time = time.time() - start_time
            assert startup_time < STARTUP_TIME_LIMIT, f'Startup took {startup_time:.2f}s (limit: {STARTUP_TIME_LIMIT}s)'
            assert services_ready, 'Not all services started successfully'
            stdout, stderr = process.communicate(timeout=1)
            assert 'ERROR' not in stdout, f'Errors found in stdout: {stdout}'
            assert 'ERROR' not in stderr, f'Errors found in stderr: {stderr}'
            assert "name 'project_root' is not defined" not in stderr, "Found 'project_root' undefined error"
        finally:
            process.terminate()
            await asyncio.sleep(2)
            if process.poll() is None:
                process.kill()

    async def _wait_for_services_ready(self, timeout: int=30) -> bool:
        """Wait for all services to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            backend_ready = await self._check_service_health(BACKEND_URL + '/health')
            frontend_ready = await self._check_service_health(FRONTEND_URL)
            auth_ready = await self._check_service_health(AUTH_URL + '/health')
            if backend_ready and frontend_ready and auth_ready:
                return True
            await asyncio.sleep(1)
        return False

    async def _check_service_health(self, url: str) -> bool:
        """Check if a service is healthy."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=5)
                return response.status_code in [200, 301, 302]
        except:
            return False

    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_service_health_endpoints(self):
        """Test that all service health endpoints respond correctly."""
        await self._start_dev_launcher()
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f'{BACKEND_URL}/health')
                assert response.status_code == 200, f'Backend health check failed: {response.status_code}'
                health_data = response.json()
                assert health_data.get('status') == 'healthy', f'Backend not healthy: {health_data}'
                assert 'database' in health_data, 'Database status missing from health check'
                assert 'redis' in health_data, 'Redis status missing from health check'
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f'{AUTH_URL}/health')
                assert response.status_code == 200, f'Auth service health check failed: {response.status_code}'
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(FRONTEND_URL)
                assert response.status_code in [200, 301, 302], f'Frontend not serving: {response.status_code}'
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_cors_configuration(self):
        """Test CORS configuration for cross-origin requests."""
        await self._start_dev_launcher()
        try:
            headers = {'Origin': FRONTEND_URL, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type, Authorization'}
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.options(f'{BACKEND_URL}/api/chat', headers=headers)
                assert response.status_code == 200, f'Backend CORS preflight failed: {response.status_code}'
                assert 'Access-Control-Allow-Origin' in response.headers, 'Missing CORS headers in backend'
                response = await client.options(f'{AUTH_URL}/auth/login', headers=headers)
                assert response.status_code == 200, f'Auth service CORS preflight failed: {response.status_code}'
                assert 'Access-Control-Allow-Origin' in response.headers, 'Missing CORS headers in auth service'
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_websocket_connection(self):
        """Test WebSocket connection establishment and basic messaging."""
        await self._start_dev_launcher()
        try:
            token = await self._get_dev_auth_token()
            assert token, 'Failed to get authentication token'
            headers = {'Authorization': f'Bearer {token}'}
            async with websockets.connect(WS_URL, additional_headers=headers) as websocket:
                test_message = {'type': 'chat', 'content': 'Test message', 'timestamp': datetime.now().isoformat()}
                await websocket.send(json.dumps(test_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                assert 'type' in response_data, 'WebSocket response missing type'
                assert response_data['type'] in ['ack', 'response', 'error'], f"Unexpected response type: {response_data['type']}"
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_authentication_flow(self):
        """Test complete authentication flow from login to authenticated API call."""
        await self._start_dev_launcher()
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                login_data = {'username': 'dev@netra.ai', 'password': 'dev123'}
                response = await client.post(f'{AUTH_URL}/auth/login', json=login_data, headers={'Content-Type': 'application/json'})
                assert response.status_code == 200, f'Login failed: {response.status_code} - {response.text}'
                auth_data = response.json()
                assert 'access_token' in auth_data, 'No access token in login response'
                token = auth_data['access_token']
                headers = {'Authorization': f'Bearer {token}'}
                response = await client.get(f'{BACKEND_URL}/api/user/profile', headers=headers)
                assert response.status_code == 200, f'Authenticated API call failed: {response.status_code}'
                user_data = response.json()
                assert 'email' in user_data, 'User profile missing email'
                assert user_data['email'] == 'dev@netra.ai', 'Wrong user returned'
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_database_connections(self):
        """Test that all required databases are accessible."""
        await self._start_dev_launcher()
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f'{BACKEND_URL}/api/system/database-status')
                if response.status_code == 404:
                    response = await client.get(f'{BACKEND_URL}/health')
                    health_data = response.json()
                    assert health_data.get('database', {}).get('status') == 'connected', 'PostgreSQL not connected'
                    assert health_data.get('redis', {}).get('status') == 'connected', 'Redis not connected'
                    if 'clickhouse' in health_data:
                        assert health_data['clickhouse']['status'] == 'connected', 'ClickHouse not connected'
                else:
                    db_status = response.json()
                    assert db_status.get('postgresql') == 'connected', 'PostgreSQL not connected'
                    assert db_status.get('redis') == 'connected', 'Redis not connected'
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_end_to_end_user_journey(self):
        """
        Test complete user journey from login to chat interaction.
        This is the MOST CRITICAL test - must work for users.
        """
        await self._start_dev_launcher()
        try:
            token = await self._get_dev_auth_token()
            assert token, 'Failed to login'
            headers = {'Authorization': f'Bearer {token}'}
            async with websockets.connect(WS_URL, additional_headers=headers) as websocket:
                chat_message = {'type': 'chat', 'content': 'Hello, can you help me with Python?', 'thread_id': 'test-thread-123', 'timestamp': datetime.now().isoformat()}
                await websocket.send(json.dumps(chat_message))
                ack = await asyncio.wait_for(websocket.recv(), timeout=5)
                ack_data = json.loads(ack)
                assert ack_data.get('type') in ['ack', 'processing'], f'No acknowledgment received: {ack_data}'
                response = await asyncio.wait_for(websocket.recv(), timeout=30)
                response_data = json.loads(response)
                assert response_data.get('type') == 'response', f'No AI response received: {response_data}'
                assert 'content' in response_data, 'AI response missing content'
                assert len(response_data['content']) > 0, 'AI response is empty'
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(f'{BACKEND_URL}/api/threads/test-thread-123', headers={'Authorization': f'Bearer {token}'})
                    if response.status_code == 200:
                        thread_data = response.json()
                        assert len(thread_data.get('messages', [])) >= 2, 'Conversation not saved'
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.performance
    @pytest.mark.e2e
    async def test_startup_performance(self):
        """Test that startup meets performance requirements."""
        start_time = time.time()
        await self._start_dev_launcher()
        try:
            services_ready = await self._wait_for_services_ready(timeout=STARTUP_TIME_LIMIT)
            startup_time = time.time() - start_time
            assert services_ready, f'Services not ready within {STARTUP_TIME_LIMIT}s'
            assert startup_time < STARTUP_TIME_LIMIT, f'Startup took {startup_time:.2f}s (limit: {STARTUP_TIME_LIMIT}s)'
            total_memory = 0
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                if any((name in proc.info['name'].lower() for name in ['python', 'node', 'uvicorn'])):
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    total_memory += memory_mb
            assert total_memory < MEMORY_LIMIT_MB * 3, f'Total memory usage {total_memory:.2f}MB exceeds limit'
            await asyncio.sleep(CPU_SETTLE_TIME)
            cpu_percent = psutil.cpu_percent(interval=2)
            assert cpu_percent < CPU_IDLE_THRESHOLD, f'CPU usage {cpu_percent}% exceeds idle threshold'
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.resilience
    @pytest.mark.e2e
    async def test_service_failure_recovery(self):
        """Test that system recovers from individual service failures."""
        await self._start_dev_launcher()
        try:
            initial_health = await self._get_system_health()
            assert initial_health['all_healthy'], 'System not healthy initially'
            if platform.system() == 'Windows':
                subprocess.run('taskkill /F /IM uvicorn', shell=True, capture_output=True)
            else:
                subprocess.run('pkill -f uvicorn', shell=True, capture_output=True)
            await asyncio.sleep(5)
            recovery_start = time.time()
            recovered = False
            while time.time() - recovery_start < 30:
                health = await self._get_system_health()
                if health['all_healthy']:
                    recovered = True
                    break
                await asyncio.sleep(2)
            assert recovered, 'System did not recover from backend failure'
        finally:
            await self._stop_dev_launcher()

    @pytest.mark.resilience
    @pytest.mark.e2e
    async def test_port_conflict_handling(self):
        """Test handling of port conflicts during startup."""
        dummy_server = await self._start_dummy_server(BACKEND_PORT)
        try:
            process = await self._start_dev_launcher_process(extra_args=['--dynamic'])
            await asyncio.sleep(5)
            stdout, stderr = process.communicate(timeout=5)
            if process.returncode != 0:
                assert 'port' in stderr.lower() or 'address already in use' in stderr.lower(), 'No clear port conflict error message'
            else:
                assert 'Using dynamic port' in stdout or 'Port 8000 in use' in stdout, "Dev launcher didn't detect port conflict"
        finally:
            dummy_server.close()
            await dummy_server.wait_closed()

    @pytest.mark.critical
    @pytest.mark.e2e
    async def test_service_independence(self):
        """Test that services are truly independent as per requirements."""
        backend_process = await self._start_service('backend')
        try:
            backend_healthy = await self._check_service_health(f'{BACKEND_URL}/health')
            assert backend_healthy, 'Backend cannot start independently'
            auth_process = await self._start_service('auth')
            auth_healthy = await self._check_service_health(f'{AUTH_URL}/health')
            assert auth_healthy, 'Auth service cannot start independently'
            async with httpx.AsyncClient(follow_redirects=True) as client:
                backend_config = await client.get(f'{BACKEND_URL}/api/config')
                auth_config = await client.get(f'{AUTH_URL}/config')
                if backend_config.status_code == 200 and auth_config.status_code == 200:
                    assert backend_config.json() != auth_config.json(), 'Services appear to share configuration'
        finally:
            if backend_process:
                backend_process.terminate()
            if auth_process:
                auth_process.terminate()

    async def _start_dev_launcher(self):
        """Start the dev launcher and wait for services."""
        self.launcher_process = await self._start_dev_launcher_process()
        ready = await self._wait_for_services_ready()
        if not ready:
            raise RuntimeError('Dev launcher failed to start all services')

    async def _start_dev_launcher_process(self, extra_args: List[str]=None):
        """Start dev launcher process."""
        project_root = Path(__file__).parent.parent.parent.parent
        launcher_script = project_root / 'scripts' / 'dev_launcher.py'
        args = [sys.executable, str(launcher_script), '--no-browser', '--no-secrets']
        if extra_args:
            args.extend(extra_args)
        env = get_env().as_dict().copy()
        env.update({'NETRA_ENV': 'development', 'PYTHONPATH': str(project_root)})
        return subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    async def _stop_dev_launcher(self):
        """Stop the dev launcher gracefully."""
        if hasattr(self, 'launcher_process'):
            self.launcher_process.terminate()
            await asyncio.sleep(2)
            if self.launcher_process.poll() is None:
                self.launcher_process.kill()

    async def _get_dev_auth_token(self) -> Optional[str]:
        """Get development authentication token."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            login_data = {'username': 'dev@netra.ai', 'password': 'dev123'}
            try:
                response = await client.post(f'{AUTH_URL}/auth/login', json=login_data, timeout=10)
                if response.status_code == 200:
                    return response.json().get('access_token')
            except:
                pass
        return None

    async def _get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        health = {'backend': False, 'frontend': False, 'auth': False, 'all_healthy': False}
        health['backend'] = await self._check_service_health(f'{BACKEND_URL}/health')
        health['frontend'] = await self._check_service_health(FRONTEND_URL)
        health['auth'] = await self._check_service_health(f'{AUTH_URL}/health')
        health['all_healthy'] = all([health['backend'], health['frontend'], health['auth']])
        return health

    async def _start_dummy_server(self, port: int):
        """Start a dummy server on specified port for testing conflicts."""

        async def handle_client(reader, writer):
            writer.close()
            await writer.wait_closed()
        server = await asyncio.start_server(handle_client, 'localhost', port)
        return server

    async def _start_service(self, service_name: str):
        """Start an individual service."""
        project_root = Path(__file__).parent.parent.parent.parent
        if service_name == 'backend':
            cmd = [sys.executable, '-m', 'uvicorn', 'netra_backend.app.main:app', '--host', '0.0.0.0', '--port', str(BACKEND_PORT)]
        elif service_name == 'auth':
            cmd = [sys.executable, '-m', 'uvicorn', 'auth_service.main:app', '--host', '0.0.0.0', '--port', str(AUTH_PORT)]
        else:
            raise ValueError(f'Unknown service: {service_name}')
        env = get_env().as_dict().copy()
        env['PYTHONPATH'] = str(project_root)
        return subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')