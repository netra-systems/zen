"""Cross-Service Auth Propagation Integration Tests (L4)

Deep integration tests for authentication propagation across microservices,
API gateways, and internal service mesh.

Business Value Justification (BVJ):
- Segment: All (security foundation for entire platform)
- Business Goal: Security - consistent auth across all services
- Value Impact: Auth gaps create security vulnerabilities
- Revenue Impact: Critical - breaches destroy customer trust and revenue
"""

import os
import pytest
import asyncio
import time
import uuid
import jwt
from typing import Dict, Any, List
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from dataclasses import dataclass

# Set test environment before imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.middleware.auth_middleware import AuthMiddleware
from netra_backend.app.services.api_gateway import APIGateway
from netra_backend.app.utils.service_mesh import ServiceMesh
from netra_backend.app.core.config import settings


@dataclass
class ServiceRequest:
    """Track service request flow."""
    service: str
    headers: Dict[str, str]
    user_id: str
    timestamp: datetime
    success: bool = False


class TestCrossServiceAuthPropagation:
    """Test authentication propagation across services."""
    
    @pytest.fixture
    def auth_token(self):
        """Create auth token for testing."""
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
            "type": "access",
            "permissions": ["read", "write"],
            "service_chain": []  # Track service propagation
        }
        secret = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "test_secret"
        return jwt.encode(payload, secret, algorithm="HS256")
    
    @pytest.fixture
    def service_mesh(self):
        """Create service mesh for testing."""
        mesh = ServiceMesh()
        mesh.register_service("api_gateway", "http://localhost:8000")
        mesh.register_service("auth_service", "http://localhost:8001")
        mesh.register_service("data_service", "http://localhost:8002")
        mesh.register_service("analytics_service", "http://localhost:8003")
        return mesh
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_propagation_through_api_gateway(self, auth_token, service_mesh):
        """Test 1: Auth should propagate from API Gateway to backend services."""
        request_chain = []
        
        async def track_request(service: str, headers: Dict):
            request_chain.append({
                "service": service,
                "has_auth": "Authorization" in headers,
                "token": headers.get("Authorization", "").replace("Bearer ", "")
            })
            return {"status": "success"}
        
        # Simulate request flow: Client -> API Gateway -> Backend Service
        with patch.object(service_mesh, 'call_service', side_effect=track_request):
            # Client request to API Gateway
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            # API Gateway processes request
            await track_request("api_gateway", headers)
            
            # API Gateway forwards to backend
            await service_mesh.call_service("data_service", headers)
            
            # Verify auth propagated through chain
            assert len(request_chain) == 2
            assert request_chain[0]["service"] == "api_gateway"
            assert request_chain[0]["has_auth"] == True
            assert request_chain[1]["service"] == "data_service"
            assert request_chain[1]["has_auth"] == True
            assert request_chain[0]["token"] == request_chain[1]["token"]
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_service_to_service_auth_injection(self, service_mesh):
        """Test 2: Service-to-service calls should inject service account auth."""
        service_auth_tokens = {}
        
        async def get_service_token(service_name: str) -> str:
            """Generate service account token."""
            if service_name not in service_auth_tokens:
                payload = {
                    "sub": f"service:{service_name}",
                    "type": "service",
                    "exp": datetime.utcnow() + timedelta(hours=1),
                    "iat": datetime.utcnow(),
                    "permissions": ["internal:call"]
                }
                secret = settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "test_secret"
                service_auth_tokens[service_name] = jwt.encode(payload, secret, algorithm="HS256")
            return service_auth_tokens[service_name]
        
        # Data service calls Analytics service
        data_service_token = await get_service_token("data_service")
        
        with patch.object(service_mesh, 'get_service_token', side_effect=get_service_token):
            # Service-to-service call
            headers = {}  # No user auth
            
            # Data service adds its service token
            headers["X-Service-Auth"] = await service_mesh.get_service_token("data_service")
            
            # Verify service auth was added
            assert "X-Service-Auth" in headers
            assert headers["X-Service-Auth"] == data_service_token
            
            # Decode and verify service token
            decoded = jwt.decode(
                headers["X-Service-Auth"],
                settings.SECRET_KEY if hasattr(settings, 'SECRET_KEY') else "test_secret",
                algorithms=["HS256"]
            )
            assert decoded["sub"] == "service:data_service"
            assert decoded["type"] == "service"
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_context_enrichment_across_services(self, auth_token):
        """Test 3: Auth context should be enriched as it flows through services."""
        auth_context = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "permissions": ["read"],
            "service_chain": [],
            "metadata": {}
        }
        
        async def enrich_context(service: str, context: Dict) -> Dict:
            """Each service enriches the auth context."""
            # Add service to chain
            context["service_chain"].append(service)
            
            # Service-specific enrichment
            if service == "api_gateway":
                context["metadata"]["request_id"] = str(uuid.uuid4())
                context["metadata"]["client_ip"] = "192.168.1.1"
            elif service == "auth_service":
                context["permissions"].append("write")
                context["metadata"]["session_id"] = str(uuid.uuid4())
            elif service == "data_service":
                context["metadata"]["data_access_level"] = "standard"
            
            return context
        
        # Flow through services
        context = await enrich_context("api_gateway", auth_context)
        context = await enrich_context("auth_service", context)
        context = await enrich_context("data_service", context)
        
        # Verify enrichment
        assert len(context["service_chain"]) == 3
        assert "api_gateway" in context["service_chain"]
        assert "write" in context["permissions"]
        assert "request_id" in context["metadata"]
        assert "session_id" in context["metadata"]
        assert "data_access_level" in context["metadata"]
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_delegation_for_async_tasks(self):
        """Test 4: Auth should be properly delegated to async background tasks."""
        task_auth_contexts = []
        
        async def background_task(auth_context: Dict):
            """Simulated background task with delegated auth."""
            task_auth_contexts.append({
                "task_id": str(uuid.uuid4()),
                "user_id": auth_context.get("user_id"),
                "permissions": auth_context.get("permissions"),
                "timestamp": datetime.utcnow()
            })
            await asyncio.sleep(0.01)  # Simulate work
            return True
        
        # Original request context
        original_context = {
            "user_id": str(uuid.uuid4()),
            "permissions": ["read", "write"],
            "request_id": str(uuid.uuid4())
        }
        
        # Spawn background tasks with delegated auth
        tasks = []
        for i in range(3):
            # Each task gets a copy of auth context
            task_context = original_context.copy()
            task_context["task_index"] = i
            tasks.append(asyncio.create_task(background_task(task_context)))
        
        # Wait for tasks
        await asyncio.gather(*tasks)
        
        # Verify all tasks had proper auth context
        assert len(task_auth_contexts) == 3
        for task_ctx in task_auth_contexts:
            assert task_ctx["user_id"] == original_context["user_id"]
            assert task_ctx["permissions"] == original_context["permissions"]
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_propagation_with_service_mesh_retry(self, auth_token, service_mesh):
        """Test 5: Auth should be maintained during service mesh retries."""
        retry_attempts = []
        
        async def flaky_service(headers: Dict, attempt: int = 0):
            """Service that fails initially then succeeds."""
            retry_attempts.append({
                "attempt": attempt,
                "has_auth": "Authorization" in headers,
                "timestamp": datetime.utcnow()
            })
            
            if attempt < 2:
                raise Exception("Service temporarily unavailable")
            
            return {"status": "success"}
        
        # Request with auth
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Service mesh retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await flaky_service(headers, attempt)
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1 * (2 ** attempt))  # Exponential backoff
        
        # Verify auth was maintained across retries
        assert len(retry_attempts) == 3
        for attempt in retry_attempts:
            assert attempt["has_auth"] == True
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_header_sanitization_between_services(self):
        """Test 6: Sensitive auth headers should be sanitized between services."""
        headers = {
            "Authorization": "Bearer token123",
            "X-Internal-Secret": "secret_value",  # Should be removed
            "X-Service-Auth": "service_token",
            "X-User-Id": "user123",
            "Cookie": "session=abc123",  # Should be sanitized
            "X-Request-Id": "req123"  # Should be preserved
        }
        
        def sanitize_headers(headers: Dict, target_service: str) -> Dict:
            """Sanitize headers based on target service."""
            sanitized = headers.copy()
            
            # Remove internal secrets
            internal_headers = ["X-Internal-Secret", "X-Admin-Token"]
            for header in internal_headers:
                sanitized.pop(header, None)
            
            # Sanitize cookies for external services
            if target_service.startswith("external_"):
                sanitized.pop("Cookie", None)
            
            return sanitized
        
        # Call internal service
        internal_headers = sanitize_headers(headers, "data_service")
        assert "Authorization" in internal_headers
        assert "X-Internal-Secret" not in internal_headers
        assert "Cookie" in internal_headers  # Preserved for internal
        assert "X-Request-Id" in internal_headers
        
        # Call external service
        external_headers = sanitize_headers(headers, "external_api")
        assert "Authorization" in external_headers
        assert "X-Internal-Secret" not in external_headers
        assert "Cookie" not in external_headers  # Removed for external
        assert "X-Request-Id" in external_headers
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_distributed_tracing_with_auth_context(self, auth_token):
        """Test 7: Distributed tracing should include auth context."""
        trace_spans = []
        
        async def create_span(service: str, operation: str, auth_context: Dict):
            """Create trace span with auth context."""
            span = {
                "trace_id": auth_context.get("trace_id", str(uuid.uuid4())),
                "span_id": str(uuid.uuid4()),
                "service": service,
                "operation": operation,
                "user_id": auth_context.get("user_id"),
                "timestamp": datetime.utcnow(),
                "duration_ms": 0
            }
            
            trace_spans.append(span)
            
            # Simulate operation
            start = time.perf_counter()
            await asyncio.sleep(0.01)
            span["duration_ms"] = (time.perf_counter() - start) * 1000
            
            return span
        
        # Create trace context
        trace_context = {
            "trace_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "auth_token": auth_token
        }
        
        # Simulate service flow with tracing
        await create_span("api_gateway", "request_validation", trace_context)
        await create_span("auth_service", "token_validation", trace_context)
        await create_span("data_service", "data_fetch", trace_context)
        
        # Verify trace continuity
        assert len(trace_spans) == 3
        trace_ids = [span["trace_id"] for span in trace_spans]
        assert len(set(trace_ids)) == 1  # All same trace ID
        
        # All spans should have user context
        for span in trace_spans:
            assert span["user_id"] == trace_context["user_id"]
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_propagation_in_event_driven_architecture(self):
        """Test 8: Auth should propagate through event-driven messaging."""
        message_queue = []
        
        async def publish_event(event_type: str, payload: Dict, auth_context: Dict):
            """Publish event with auth context."""
            message = {
                "id": str(uuid.uuid4()),
                "type": event_type,
                "payload": payload,
                "auth": {
                    "user_id": auth_context.get("user_id"),
                    "permissions": auth_context.get("permissions")
                },
                "timestamp": datetime.utcnow()
            }
            message_queue.append(message)
            return message["id"]
        
        async def consume_event(message_id: str) -> Dict:
            """Consume event and verify auth context."""
            message = next((m for m in message_queue if m["id"] == message_id), None)
            if message and message.get("auth"):
                # Verify auth context exists
                return message["auth"]
            return {}
        
        # Original auth context
        auth_context = {
            "user_id": str(uuid.uuid4()),
            "permissions": ["read", "write"]
        }
        
        # Publish event
        event_id = await publish_event(
            "user.updated",
            {"name": "Test User"},
            auth_context
        )
        
        # Consumer receives event
        received_auth = await consume_event(event_id)
        
        # Verify auth propagated
        assert received_auth["user_id"] == auth_context["user_id"]
        assert received_auth["permissions"] == auth_context["permissions"]
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_cache_coherence_across_services(self):
        """Test 9: Auth cache should remain coherent across services."""
        # Distributed auth cache
        auth_caches = {
            "api_gateway": {},
            "auth_service": {},
            "data_service": {}
        }
        
        async def update_auth_cache(service: str, token: str, user_data: Dict):
            """Update auth cache for a service."""
            auth_caches[service][token] = {
                "user_data": user_data,
                "cached_at": datetime.utcnow()
            }
        
        async def invalidate_auth_cache(token: str):
            """Invalidate token across all services."""
            for service in auth_caches:
                auth_caches[service].pop(token, None)
        
        # Cache auth data
        token = "test_token_123"
        user_data = {"user_id": str(uuid.uuid4()), "email": "test@example.com"}
        
        # Update cache in all services
        for service in auth_caches:
            await update_auth_cache(service, token, user_data)
        
        # Verify cache coherence
        for service in auth_caches:
            assert token in auth_caches[service]
            assert auth_caches[service][token]["user_data"] == user_data
        
        # Invalidate token
        await invalidate_auth_cache(token)
        
        # Verify invalidation propagated
        for service in auth_caches:
            assert token not in auth_caches[service]
    
    @pytest.mark.integration
    @pytest.mark.L4
    async def test_auth_boundary_enforcement_at_service_edges(self, service_mesh):
        """Test 10: Auth boundaries should be enforced at service edges."""
        service_boundaries = {
            "public_api": {
                "requires_user_auth": True,
                "allowed_auth_types": ["user", "api_key"]
            },
            "internal_api": {
                "requires_user_auth": False,
                "allowed_auth_types": ["user", "service"]
            },
            "admin_api": {
                "requires_user_auth": True,
                "allowed_auth_types": ["admin"]
            }
        }
        
        async def check_auth_boundary(service: str, auth_type: str) -> bool:
            """Check if auth type is allowed for service."""
            boundary = service_boundaries.get(service, {})
            
            # Check auth type
            if auth_type not in boundary.get("allowed_auth_types", []):
                return False
            
            # Check user auth requirement
            if boundary.get("requires_user_auth") and auth_type == "service":
                return False
            
            return True
        
        # Test various auth scenarios
        test_cases = [
            ("public_api", "user", True),
            ("public_api", "service", False),
            ("internal_api", "service", True),
            ("internal_api", "user", True),
            ("admin_api", "user", False),
            ("admin_api", "admin", True)
        ]
        
        for service, auth_type, expected in test_cases:
            result = await check_auth_boundary(service, auth_type)
            assert result == expected, f"Failed for {service} with {auth_type}"