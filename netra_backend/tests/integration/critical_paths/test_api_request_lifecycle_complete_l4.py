"""
L4 Integration Test: API Request Lifecycle Complete
Tests complete API request lifecycle from ingress to response
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.config import get_config

# Add project root to path
from netra_backend.app.services.api_gateway import APIGateway
from netra_backend.app.services.middleware_chain import MiddlewareChain
from netra_backend.app.services.rate_limiter import RateLimiter
from netra_backend.app.services.request_validator import RequestValidator

# Add project root to path


class TestAPIRequestLifecycleCompleteL4:
    """Complete API request lifecycle testing"""
    
    @pytest.fixture
    async def api_infrastructure(self):
        """API infrastructure setup"""
        return {
            'gateway': APIGateway(),
            'rate_limiter': RateLimiter(),
            'validator': RequestValidator(),
            'middleware': MiddlewareChain(),
            'request_log': [],
            'metrics': {
                'total_requests': 0,
                'successful': 0,
                'failed': 0,
                'rate_limited': 0
            }
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_validation_pipeline(self, api_infrastructure):
        """Test complete request validation pipeline"""
        
        # Test various request types
        test_requests = [
            # Valid request
            {
                'method': 'POST',
                'path': '/api/v1/users',
                'headers': {'Content-Type': 'application/json', 'Authorization': 'Bearer token123'},
                'body': {'email': 'user@test.com', 'password': 'Test123!'}
            },
            # Missing required header
            {
                'method': 'POST',
                'path': '/api/v1/users',
                'headers': {'Content-Type': 'application/json'},
                'body': {'email': 'user@test.com', 'password': 'Test123!'}
            },
            # Invalid body schema
            {
                'method': 'POST',
                'path': '/api/v1/users',
                'headers': {'Content-Type': 'application/json', 'Authorization': 'Bearer token123'},
                'body': {'email': 'invalid-email', 'password': '123'}
            },
            # SQL injection attempt
            {
                'method': 'GET',
                'path': '/api/v1/users',
                'query': "id=1' OR '1'='1",
                'headers': {'Authorization': 'Bearer token123'}
            },
            # XSS attempt
            {
                'method': 'POST',
                'path': '/api/v1/comments',
                'headers': {'Content-Type': 'application/json', 'Authorization': 'Bearer token123'},
                'body': {'text': '<script>alert("xss")</script>'}
            }
        ]
        
        validation_results = []
        
        for request in test_requests:
            result = await api_infrastructure['validator'].validate_request(request)
            validation_results.append(result)
        
        # First request should pass
        assert validation_results[0]['valid']
        
        # Missing auth should fail
        assert not validation_results[1]['valid']
        assert 'authorization' in validation_results[1]['errors'][0].lower()
        
        # Invalid schema should fail
        assert not validation_results[2]['valid']
        
        # SQL injection should be detected
        assert not validation_results[3]['valid']
        assert 'injection' in validation_results[3]['errors'][0].lower()
        
        # XSS should be sanitized or rejected
        assert not validation_results[4]['valid'] or validation_results[4].get('sanitized')
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_middleware_chain_execution(self, api_infrastructure):
        """Test middleware chain execution order and error handling"""
        
        execution_order = []
        
        # Define middleware functions
        async def auth_middleware(request, next_handler):
            execution_order.append('auth_start')
            if 'Authorization' not in request.get('headers', {}):
                return {'error': 'Unauthorized', 'status': 401}
            response = await next_handler(request)
            execution_order.append('auth_end')
            return response
        
        async def logging_middleware(request, next_handler):
            execution_order.append('logging_start')
            start_time = time.time()
            response = await next_handler(request)
            duration = time.time() - start_time
            execution_order.append(f'logging_end_{duration:.3f}')
            return response
        
        async def cors_middleware(request, next_handler):
            execution_order.append('cors_start')
            response = await next_handler(request)
            response['headers'] = response.get('headers', {})
            response['headers']['Access-Control-Allow-Origin'] = '*'
            execution_order.append('cors_end')
            return response
        
        # Configure middleware chain
        api_infrastructure['middleware'].add(logging_middleware)
        api_infrastructure['middleware'].add(auth_middleware)
        api_infrastructure['middleware'].add(cors_middleware)
        
        # Test request through middleware
        request = {
            'method': 'GET',
            'path': '/api/v1/data',
            'headers': {'Authorization': 'Bearer token123'}
        }
        
        async def final_handler(req):
            execution_order.append('handler')
            return {'data': 'response', 'status': 200}
        
        response = await api_infrastructure['middleware'].execute(request, final_handler)
        
        # Verify execution order (onion model)
        assert execution_order[0] == 'logging_start'
        assert execution_order[1] == 'auth_start'
        assert execution_order[2] == 'cors_start'
        assert execution_order[3] == 'handler'
        assert execution_order[4] == 'cors_end'
        assert execution_order[5] == 'auth_end'
        assert 'logging_end' in execution_order[6]
        
        # Verify CORS header added
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_rate_limiting_per_endpoint(self, api_infrastructure):
        """Test rate limiting per endpoint and per user"""
        
        # Configure different limits
        limits = {
            '/api/v1/expensive': {'requests': 5, 'window': 60},
            '/api/v1/normal': {'requests': 30, 'window': 60},
            '/api/v1/public': {'requests': 100, 'window': 60}
        }
        
        api_infrastructure['rate_limiter'].configure_limits(limits)
        
        # Test expensive endpoint
        user_id = "user_123"
        expensive_results = []
        
        for i in range(10):
            result = await api_infrastructure['rate_limiter'].check_limit(
                user_id=user_id,
                endpoint='/api/v1/expensive'
            )
            expensive_results.append(result)
        
        # First 5 should pass, rest should be limited
        assert sum(1 for r in expensive_results[:5] if r['allowed']) == 5
        assert sum(1 for r in expensive_results[5:] if not r['allowed']) == 5
        
        # Test normal endpoint (different limit)
        normal_results = []
        
        for i in range(35):
            result = await api_infrastructure['rate_limiter'].check_limit(
                user_id=user_id,
                endpoint='/api/v1/normal'
            )
            normal_results.append(result)
        
        # First 30 should pass
        assert sum(1 for r in normal_results[:30] if r['allowed']) == 30
        assert sum(1 for r in normal_results[30:] if not r['allowed']) == 5
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_timeout_handling(self, api_infrastructure):
        """Test request timeout and cancellation"""
        
        timeout_config = {
            'default': 5,
            'endpoints': {
                '/api/v1/quick': 1,
                '/api/v1/slow': 30
            }
        }
        
        api_infrastructure['gateway'].configure_timeouts(timeout_config)
        
        # Test quick endpoint timeout
        async def slow_handler():
            await asyncio.sleep(2)  # Exceeds 1 second timeout
            return {'data': 'should_not_return'}
        
        quick_request = {'path': '/api/v1/quick'}
        
        with pytest.raises(asyncio.TimeoutError):
            await api_infrastructure['gateway'].handle_request(
                request=quick_request,
                handler=slow_handler,
                timeout=timeout_config['endpoints']['/api/v1/quick']
            )
        
        # Test slow endpoint (should not timeout)
        async def medium_handler():
            await asyncio.sleep(2)
            return {'data': 'success'}
        
        slow_request = {'path': '/api/v1/slow'}
        
        result = await api_infrastructure['gateway'].handle_request(
            request=slow_request,
            handler=medium_handler,
            timeout=timeout_config['endpoints']['/api/v1/slow']
        )
        
        assert result['data'] == 'success'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_retry_with_backoff(self, api_infrastructure):
        """Test request retry logic with exponential backoff"""
        
        attempt_count = 0
        attempt_times = []
        
        async def flaky_handler():
            nonlocal attempt_count
            attempt_count += 1
            attempt_times.append(time.time())
            
            if attempt_count < 3:
                raise Exception("Temporary failure")
            
            return {'data': 'success', 'attempts': attempt_count}
        
        retry_config = {
            'max_attempts': 5,
            'initial_delay': 0.1,
            'max_delay': 2,
            'exponential_base': 2
        }
        
        result = await api_infrastructure['gateway'].execute_with_retry(
            handler=flaky_handler,
            retry_config=retry_config
        )
        
        assert result['data'] == 'success'
        assert result['attempts'] == 3
        
        # Verify exponential backoff
        if len(attempt_times) > 1:
            delays = [attempt_times[i] - attempt_times[i-1] for i in range(1, len(attempt_times))]
            # Each delay should be roughly double the previous
            assert delays[1] > delays[0] * 1.5  # Allow some variance
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_body_size_limits(self, api_infrastructure):
        """Test request body size limit enforcement"""
        
        size_limits = {
            'default': 1024 * 1024,  # 1MB
            'endpoints': {
                '/api/v1/upload': 10 * 1024 * 1024,  # 10MB
                '/api/v1/webhook': 64 * 1024  # 64KB
            }
        }
        
        api_infrastructure['validator'].configure_size_limits(size_limits)
        
        # Test small request (should pass)
        small_request = {
            'path': '/api/v1/data',
            'body': 'x' * 1000  # 1KB
        }
        
        result = await api_infrastructure['validator'].check_size(small_request)
        assert result['allowed']
        
        # Test large request on default endpoint (should fail)
        large_request = {
            'path': '/api/v1/data',
            'body': 'x' * (2 * 1024 * 1024)  # 2MB
        }
        
        result = await api_infrastructure['validator'].check_size(large_request)
        assert not result['allowed']
        assert 'size limit' in result['reason'].lower()
        
        # Test large request on upload endpoint (should pass)
        upload_request = {
            'path': '/api/v1/upload',
            'body': 'x' * (5 * 1024 * 1024)  # 5MB
        }
        
        result = await api_infrastructure['validator'].check_size(upload_request)
        assert result['allowed']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_deduplication(self, api_infrastructure):
        """Test request deduplication for idempotency"""
        
        # Enable deduplication
        api_infrastructure['gateway'].enable_deduplication(window=5)
        
        request_id = "unique_request_123"
        execution_count = 0
        
        async def handler():
            nonlocal execution_count
            execution_count += 1
            await asyncio.sleep(0.5)  # Simulate processing
            return {'result': 'processed', 'count': execution_count}
        
        # Send same request multiple times concurrently
        tasks = []
        for _ in range(5):
            request = {
                'path': '/api/v1/process',
                'headers': {'X-Request-ID': request_id},
                'body': {'data': 'test'}
            }
            
            task = asyncio.create_task(
                api_infrastructure['gateway'].handle_request(request, handler)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Handler should only execute once
        assert execution_count == 1
        
        # All results should be identical
        for result in results:
            assert result['count'] == 1
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_circuit_breaker_per_service(self, api_infrastructure):
        """Test circuit breaker per backend service"""
        
        circuit_breakers = {
            'user_service': {'threshold': 3, 'timeout': 2, 'reset': 5},
            'payment_service': {'threshold': 2, 'timeout': 3, 'reset': 10}
        }
        
        api_infrastructure['gateway'].configure_circuit_breakers(circuit_breakers)
        
        # Simulate user service failures
        user_service_calls = []
        
        for i in range(10):
            try:
                if i < 5:
                    # Force failures
                    raise Exception("Service unavailable")
                else:
                    # Service recovered
                    user_service_calls.append({'success': True})
            except Exception as e:
                user_service_calls.append({'success': False, 'error': str(e)})
            
            # Check circuit state
            if i == 3:  # After threshold
                state = api_infrastructure['gateway'].get_circuit_state('user_service')
                assert state == 'open'
        
        # Circuit should trip after threshold
        failures = [c for c in user_service_calls if not c['success']]
        assert len(failures) >= 3
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_response_caching_strategy(self, api_infrastructure):
        """Test response caching with cache invalidation"""
        
        cache_config = {
            'enabled': True,
            'ttl': 60,
            'endpoints': {
                '/api/v1/static': {'ttl': 3600},
                '/api/v1/dynamic': {'ttl': 5},
                '/api/v1/realtime': {'cache': False}
            }
        }
        
        api_infrastructure['gateway'].configure_cache(cache_config)
        
        execution_count = 0
        
        async def data_handler():
            nonlocal execution_count
            execution_count += 1
            return {'data': f'response_{execution_count}', 'timestamp': time.time()}
        
        # First request - cache miss
        request1 = {'path': '/api/v1/static', 'method': 'GET'}
        response1 = await api_infrastructure['gateway'].handle_request(request1, data_handler)
        
        # Second request - cache hit
        request2 = {'path': '/api/v1/static', 'method': 'GET'}
        response2 = await api_infrastructure['gateway'].handle_request(request2, data_handler)
        
        # Should return cached response
        assert response1['data'] == response2['data']
        assert execution_count == 1  # Handler called only once
        
        # Test cache invalidation
        await api_infrastructure['gateway'].invalidate_cache('/api/v1/static')
        
        # Third request - cache miss after invalidation
        request3 = {'path': '/api/v1/static', 'method': 'GET'}
        response3 = await api_infrastructure['gateway'].handle_request(request3, data_handler)
        
        assert response3['data'] != response1['data']
        assert execution_count == 2
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_request_tracing_and_correlation(self, api_infrastructure):
        """Test distributed tracing and request correlation"""
        
        # Enable tracing
        api_infrastructure['gateway'].enable_tracing()
        
        parent_request = {
            'path': '/api/v1/aggregate',
            'headers': {'X-Trace-ID': 'trace_123', 'X-Span-ID': 'span_456'}
        }
        
        # Track spans
        spans = []
        
        async def service_a_handler(trace_context):
            span = {
                'service': 'service_a',
                'trace_id': trace_context['trace_id'],
                'parent_span': trace_context['span_id'],
                'span_id': f"span_a_{time.time()}",
                'start': time.time()
            }
            spans.append(span)
            await asyncio.sleep(0.1)
            span['end'] = time.time()
            return {'service_a': 'data'}
        
        async def service_b_handler(trace_context):
            span = {
                'service': 'service_b',
                'trace_id': trace_context['trace_id'],
                'parent_span': trace_context['span_id'],
                'span_id': f"span_b_{time.time()}",
                'start': time.time()
            }
            spans.append(span)
            await asyncio.sleep(0.15)
            span['end'] = time.time()
            return {'service_b': 'data'}
        
        # Aggregate handler calls multiple services
        async def aggregate_handler(request):
            trace_context = {
                'trace_id': request['headers'].get('X-Trace-ID'),
                'span_id': request['headers'].get('X-Span-ID')
            }
            
            # Call services in parallel
            results = await asyncio.gather(
                service_a_handler(trace_context),
                service_b_handler(trace_context)
            )
            
            return {'aggregated': results}
        
        response = await api_infrastructure['gateway'].handle_request(
            parent_request,
            aggregate_handler
        )
        
        # Verify trace propagation
        assert all(span['trace_id'] == 'trace_123' for span in spans)
        assert all(span['parent_span'] == 'span_456' for span in spans)
        
        # Verify timing information captured
        for span in spans:
            assert 'start' in span
            assert 'end' in span
            assert span['end'] > span['start']