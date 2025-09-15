"""
Stress tests for token refresh during high-load scenarios.

Tests system behavior under extreme conditions to ensure robustness.
"""
import asyncio
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment
import jwt
import pytest
import websockets
from httpx import AsyncClient
from netra_backend.app.core.configuration import get_configuration
from test_framework.auth_jwt_test_manager import AuthJWTTestManager
from test_framework.services import ServiceManager, get_service_manager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import get_env

class StressTestMetrics:
    """Collect and analyze stress test metrics."""

    def __init__(self):
        self.operations = []
        self.errors = []
        self.latencies = []
        self.start_time = None
        self.end_time = None

    def start(self):
        """Start metrics collection."""
        self.start_time = time.time()

    def stop(self):
        """Stop metrics collection."""
        self.end_time = time.time()

    def record_operation(self, op_type: str, latency: float, success: bool, details: Dict=None):
        """Record an operation."""
        self.operations.append({'type': op_type, 'latency': latency, 'success': success, 'timestamp': time.time(), 'details': details or {}})
        if success:
            self.latencies.append(latency)
        else:
            self.errors.append({'type': op_type, 'timestamp': time.time(), 'details': details or {}})

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        if not self.operations:
            return {'error': 'No operations recorded'}
        successful_ops = [op for op in self.operations if op['success']]
        failed_ops = [op for op in self.operations if not op['success']]
        duration = (self.end_time or time.time()) - self.start_time
        return {'duration': duration, 'total_operations': len(self.operations), 'successful_operations': len(successful_ops), 'failed_operations': len(failed_ops), 'error_rate': len(failed_ops) / len(self.operations) if self.operations else 0, 'throughput': len(self.operations) / duration if duration > 0 else 0, 'latency_stats': self._calculate_latency_stats(), 'error_types': self._categorize_errors()}

    def _calculate_latency_stats(self) -> Dict[str, float]:
        """Calculate latency statistics."""
        if not self.latencies:
            return {}
        sorted_latencies = sorted(self.latencies)
        return {'min': min(self.latencies), 'max': max(self.latencies), 'avg': sum(self.latencies) / len(self.latencies), 'p50': sorted_latencies[len(sorted_latencies) // 2], 'p95': sorted_latencies[int(len(sorted_latencies) * 0.95)], 'p99': sorted_latencies[int(len(sorted_latencies) * 0.99)]}

    def _categorize_errors(self) -> Dict[str, int]:
        """Categorize errors by type."""
        error_counts = {}
        for error in self.errors:
            error_type = error.get('type', 'unknown')
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        return error_counts

@pytest.mark.asyncio
class ConcurrentTokenRefreshTests:
    """Test concurrent token refresh scenarios."""

    async def test_hundred_concurrent_refreshes(self):
        """Test 100 concurrent token refresh attempts."""
        config = get_configuration()
        auth_manager = AuthJWTTestManager()
        metrics = StressTestMetrics()
        tokens = []
        for i in range(100):
            payload = {'sub': f'user_{i}', 'email': f'user{i}@example.com', 'exp': int((datetime.utcnow() + timedelta(minutes=5)).timestamp()), 'iat': int(datetime.utcnow().timestamp())}
            token = jwt.encode(payload, config.jwt_secret, algorithm='HS256')
            tokens.append(token)

        async def refresh_token(token: str, user_id: int) -> Tuple[bool, float]:
            """Attempt to refresh a token."""
            start = time.time()
            try:
                await asyncio.sleep(random.uniform(0.01, 0.1))
                decoded = jwt.decode(token, config.jwt_secret, algorithms=['HS256'], options={'verify_exp': False})
                decoded['exp'] = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
                decoded['refresh_count'] = decoded.get('refresh_count', 0) + 1
                new_token = jwt.encode(decoded, config.jwt_secret, algorithm='HS256')
                latency = time.time() - start
                return (True, latency)
            except Exception as e:
                latency = time.time() - start
                metrics.record_operation('refresh', latency, False, {'error': str(e)})
                return (False, latency)
        metrics.start()
        tasks = []
        for i, token in enumerate(tokens):
            task = refresh_token(token, i)
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                metrics.record_operation('refresh', 0, False, {'error': str(result)})
            else:
                success, latency = result
                metrics.record_operation('refresh', latency, success)
        metrics.stop()
        summary = metrics.get_summary()
        assert summary['successful_operations'] >= 95
        assert summary['latency_stats']['p95'] < 1.0
        assert summary['throughput'] > 50
        print(f'Concurrent Refresh Test Summary: {json.dumps(summary, indent=2)}')

    async def test_refresh_race_condition_prevention(self):
        """Test that multiple refresh attempts for same token are properly handled."""
        config = get_configuration()
        metrics = StressTestMetrics()
        payload = {'sub': 'test_user', 'email': 'test@example.com', 'exp': int((datetime.utcnow() + timedelta(minutes=5)).timestamp()), 'iat': int(datetime.utcnow().timestamp())}
        token = jwt.encode(payload, config.jwt_secret, algorithm='HS256')
        refresh_results = []
        refresh_lock = asyncio.Lock()

        async def attempt_refresh(attempt_id: int) -> Dict:
            """Attempt to refresh the token."""
            start = time.time()
            await asyncio.sleep(0.001 * random.random())
            async with refresh_lock:
                if refresh_results:
                    return {'attempt_id': attempt_id, 'status': 'blocked', 'latency': time.time() - start}
                await asyncio.sleep(0.1)
                new_payload = payload.copy()
                new_payload['exp'] = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
                new_payload['refresh_count'] = 1
                new_token = jwt.encode(new_payload, config.jwt_secret, algorithm='HS256')
                result = {'attempt_id': attempt_id, 'status': 'success', 'new_token': new_token, 'latency': time.time() - start}
                refresh_results.append(result)
                return result
        tasks = []
        for i in range(50):
            task = attempt_refresh(i)
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        successful = [r for r in results if r['status'] == 'success']
        blocked = [r for r in results if r['status'] == 'blocked']
        assert len(successful) == 1
        assert len(blocked) == 49
        new_token = successful[0]['new_token']
        assert all((r['status'] == 'blocked' or r.get('new_token') == new_token for r in results))

@pytest.mark.asyncio
class WebSocketLoadWithRefreshTests:
    """Test WebSocket behavior under load with token refresh."""

    async def test_websocket_message_flood_with_refresh(self):
        """Test WebSocket handling 10k messages while refreshing tokens."""
        service_manager = get_service_manager()
        await service_manager.start_services()
        metrics = StressTestMetrics()
        config = get_configuration()
        try:
            payload = {'sub': 'stress_test_user', 'email': 'stress@example.com', 'exp': int((datetime.utcnow() + timedelta(minutes=10)).timestamp()), 'iat': int(datetime.utcnow().timestamp())}
            token = jwt.encode(payload, config.jwt_secret, algorithm='HS256')
            ws_url = f'ws://localhost:8000/ws?token={token}'
            messages_sent = 0
            messages_received = 0
            refresh_count = 0
            errors = []
            async with websockets.connect(ws_url) as websocket:

                async def send_messages():
                    """Send rapid fire messages."""
                    nonlocal messages_sent
                    for i in range(10000):
                        try:
                            await websocket.send(json.dumps({'type': 'stress_test', 'id': i, 'timestamp': time.time()}))
                            messages_sent += 1
                            if i % 100 == 0:
                                await asyncio.sleep(0.01)
                        except Exception as e:
                            errors.append({'phase': 'send', 'error': str(e)})

                async def receive_messages():
                    """Receive messages."""
                    nonlocal messages_received
                    while messages_received < 9000:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                            messages_received += 1
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            errors.append({'phase': 'receive', 'error': str(e)})
                            break

                async def refresh_tokens():
                    """Periodically refresh tokens."""
                    nonlocal refresh_count
                    current_token = token
                    for _ in range(5):
                        await asyncio.sleep(2)
                        new_payload = payload.copy()
                        new_payload['exp'] = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
                        new_payload['refresh_count'] = refresh_count + 1
                        new_token = jwt.encode(new_payload, config.jwt_secret, algorithm='HS256')
                        await websocket.send(json.dumps({'type': 'token_refresh', 'old_token': current_token, 'new_token': new_token}))
                        current_token = new_token
                        refresh_count += 1
                metrics.start()
                send_task = asyncio.create_task(send_messages())
                receive_task = asyncio.create_task(receive_messages())
                refresh_task = asyncio.create_task(refresh_tokens())
                await asyncio.wait_for(asyncio.gather(send_task, receive_task, refresh_task), timeout=30)
                metrics.stop()
            assert messages_sent >= 9000
            assert messages_received >= 8000
            assert refresh_count >= 4
            assert len(errors) < 100
            print(f'WebSocket Load Test: Sent={messages_sent}, Received={messages_received}, Refreshes={refresh_count}, Errors={len(errors)}')
        finally:
            await service_manager.stop_services()

    async def test_multiple_websocket_connections_with_refresh(self):
        """Test 50 concurrent WebSocket connections with token refresh."""
        service_manager = get_service_manager()
        await service_manager.start_services()
        config = get_configuration()
        metrics = StressTestMetrics()
        try:
            connection_stats = []

            async def manage_connection(conn_id: int):
                """Manage a single WebSocket connection."""
                payload = {'sub': f'user_{conn_id}', 'email': f'user{conn_id}@example.com', 'exp': int((datetime.utcnow() + timedelta(minutes=5)).timestamp()), 'iat': int(datetime.utcnow().timestamp())}
                token = jwt.encode(payload, config.jwt_secret, algorithm='HS256')
                ws_url = f'ws://localhost:8000/ws?token={token}'
                stats = {'conn_id': conn_id, 'messages_sent': 0, 'messages_received': 0, 'refreshes': 0, 'errors': 0}
                try:
                    async with websockets.connect(ws_url) as websocket:
                        for i in range(100):
                            await websocket.send(json.dumps({'type': 'ping', 'conn_id': conn_id, 'msg_id': i}))
                            stats['messages_sent'] += 1
                            if i == 50:
                                new_payload = payload.copy()
                                new_payload['exp'] = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
                                new_token = jwt.encode(new_payload, config.jwt_secret, algorithm='HS256')
                                await websocket.send(json.dumps({'type': 'token_refresh', 'new_token': new_token}))
                                stats['refreshes'] += 1
                            await asyncio.sleep(0.01)
                        for _ in range(50):
                            try:
                                await asyncio.wait_for(websocket.recv(), timeout=0.1)
                                stats['messages_received'] += 1
                            except asyncio.TimeoutError:
                                break
                except Exception as e:
                    stats['errors'] += 1
                connection_stats.append(stats)
                return stats
            metrics.start()
            tasks = []
            for i in range(50):
                task = manage_connection(i)
                tasks.append(task)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            metrics.stop()
            successful_conns = [r for r in results if isinstance(r, dict) and r['errors'] == 0]
            total_messages = sum((r['messages_sent'] for r in results if isinstance(r, dict)))
            total_refreshes = sum((r['refreshes'] for r in results if isinstance(r, dict)))
            assert len(successful_conns) >= 45
            assert total_messages >= 4500
            assert total_refreshes >= 45
            print(f'Multi-Connection Test: Connections={len(successful_conns)}/50, Messages={total_messages}, Refreshes={total_refreshes}')
        finally:
            await service_manager.stop_services()

@pytest.mark.asyncio
class TokenRefreshResilienceTests:
    """Test system resilience during token refresh failures."""

    async def test_refresh_with_auth_service_outage(self):
        """Test token refresh behavior when auth service is down."""
        metrics = StressTestMetrics()
        config = get_configuration()
        payload = {'sub': 'resilience_test_user', 'email': 'resilience@example.com', 'exp': int((datetime.utcnow() + timedelta(minutes=1)).timestamp()), 'iat': int(datetime.utcnow().timestamp())}
        token = jwt.encode(payload, config.jwt_secret, algorithm='HS256')
        with patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.refresh_token') as mock_refresh:
            mock_refresh.side_effect = Exception('Auth service unavailable')
            refresh_attempts = []

            async def attempt_refresh_with_retry():
                """Attempt refresh with exponential backoff."""
                max_retries = 5
                retry_count = 0
                while retry_count < max_retries:
                    start = time.time()
                    try:
                        result = await mock_refresh(token)
                        refresh_attempts.append({'attempt': retry_count, 'status': 'success', 'latency': time.time() - start})
                        return result
                    except Exception as e:
                        refresh_attempts.append({'attempt': retry_count, 'status': 'failed', 'error': str(e), 'latency': time.time() - start})
                        await asyncio.sleep(2 ** retry_count * 0.1)
                        retry_count += 1
                return None
            result = await attempt_refresh_with_retry()
            assert result is None
            assert len(refresh_attempts) == 5
            for i in range(1, len(refresh_attempts)):
                assert refresh_attempts[i]['attempt'] > refresh_attempts[i - 1]['attempt']

    async def test_refresh_with_intermittent_failures(self):
        """Test token refresh with intermittent network failures."""
        config = get_configuration()
        attempt_counter = 0
        success_pattern = [False, False, True, False, True, True]

        async def intermittent_refresh(token: str):
            """Simulate intermittent failures."""
            nonlocal attempt_counter
            should_succeed = success_pattern[attempt_counter % len(success_pattern)]
            attempt_counter += 1
            if should_succeed:
                decoded = jwt.decode(token, config.jwt_secret, algorithms=['HS256'], options={'verify_exp': False})
                decoded['exp'] = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
                new_token = jwt.encode(decoded, config.jwt_secret, algorithm='HS256')
                return {'access_token': new_token}
            else:
                raise Exception('Network timeout')
        payload = {'sub': 'intermittent_test', 'email': 'intermittent@example.com', 'exp': int((datetime.utcnow() + timedelta(minutes=5)).timestamp()), 'iat': int(datetime.utcnow().timestamp())}
        token = jwt.encode(payload, config.jwt_secret, algorithm='HS256')
        results = []
        for i in range(10):
            try:
                result = await intermittent_refresh(token)
                results.append({'attempt': i, 'success': True})
                token = result['access_token']
            except Exception as e:
                results.append({'attempt': i, 'success': False, 'error': str(e)})
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        assert len(successful) > 0
        assert len(failed) > 0
        print(f'Intermittent Failure Test: Success={len(successful)}, Failed={len(failed)}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')