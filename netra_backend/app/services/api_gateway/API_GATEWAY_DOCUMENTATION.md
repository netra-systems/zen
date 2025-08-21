# API Gateway Service Documentation

## Overview

The Netra Apex API Gateway service provides a comprehensive solution for managing API traffic, implementing enterprise-grade features including request routing, rate limiting, caching, circuit breaking, and data transformation. This modular gateway architecture ensures high availability, performance optimization, and resilience for AI workload optimization.

## Architecture

### Core Components

The API Gateway consists of five primary components, each designed with single responsibility and high cohesion:

1. **Router** (`router.py`) - Request routing and load balancing
2. **Rate Limiter** (`rate_limiter.py`) - Traffic control and quota management
3. **Cache Manager** (`cache_manager.py`) - Response caching and optimization
4. **Circuit Breaker** (`circuit_breaker.py`) - Fault tolerance and resilience
5. **Transformation Engine** (`transformation_engine.py`) - Request/response data transformation

### Component Interaction Flow

```
Client Request
    ↓
[Rate Limiter] → Check rate limits
    ↓ (if allowed)
[Router] → Determine target endpoint
    ↓
[Cache Manager] → Check for cached response
    ↓ (if cache miss)
[Circuit Breaker] → Check service health
    ↓ (if circuit closed)
[Transformation Engine] → Transform request
    ↓
Backend Service
    ↓
[Transformation Engine] → Transform response
    ↓
[Cache Manager] → Store in cache
    ↓
Client Response
```

## Component Details

### 1. API Gateway Router

**Purpose**: Manages request routing and load balancing across multiple backend services.

**Key Features**:
- Dynamic route configuration
- Weighted load balancing
- Route enable/disable capability
- Health status monitoring

**Classes**:
- `Route`: Data class representing route configuration
- `LoadBalancer`: Distributes requests across targets
- `RouteManager`: Manages routing rules and lookups
- `ApiGatewayRouter`: Main router orchestration

**Usage Example**:
```python
from netra_backend.app.services.api_gateway.router import ApiGatewayRouter

# Initialize router
router = ApiGatewayRouter()

# Add routes
router.add_route(
    path="/api/v1/agents",
    method="GET",
    target="http://agent-service:8001",
    weight=100
)

# Route request
target = router.route_request("/api/v1/agents", "GET")
# Returns: "http://agent-service:8001"

# Check health
health = router.get_health_status()
# Returns: {'enabled': True, 'routes_count': 1, 'targets_count': 1}
```

### 2. API Gateway Rate Limiter

**Purpose**: Controls API traffic to prevent abuse and ensure fair resource allocation.

**Key Features**:
- Per-client rate limiting
- Configurable time windows (minute/hour)
- Burst protection
- Client-specific configurations
- Real-time statistics

**Classes**:
- `RateLimitConfig`: Configuration for rate limits
- `RateLimitState`: Tracks client request state
- `ApiGatewayManager`: Gateway configuration management
- `ApiGatewayRateLimiter`: Main rate limiting logic

**Usage Example**:
```python
from netra_backend.app.services.api_gateway.rate_limiter import (
    ApiGatewayRateLimiter,
    RateLimitConfig
)

# Initialize rate limiter
rate_limiter = ApiGatewayRateLimiter()

# Set custom client config
enterprise_config = RateLimitConfig(
    requests_per_minute=100,
    requests_per_hour=5000,
    burst_size=20
)
rate_limiter.set_client_config("enterprise_client_123", enterprise_config)

# Check if request allowed
if rate_limiter.is_allowed("client_123", "/api/v1/agents"):
    # Process request
    pass
else:
    # Return 429 Too Many Requests
    pass

# Get client statistics
stats = rate_limiter.get_client_stats("client_123")
# Returns: {'requests_this_minute': 5, 'requests_this_hour': 100, 'burst_tokens': 8}
```

### 3. API Cache Manager

**Purpose**: Caches API responses to reduce backend load and improve response times.

**Key Features**:
- Configurable caching strategies
- TTL-based expiration
- LRU eviction policy
- Cache invalidation patterns
- Hit rate statistics

**Classes**:
- `CacheEntry`: Individual cache entry with metadata
- `CacheStrategy`: Abstract base for caching strategies
- `DefaultCacheStrategy`: Default caching implementation
- `ApiCacheManager`: Main cache management

**Usage Example**:
```python
from netra_backend.app.services.api_gateway.cache_manager import ApiCacheManager

# Initialize cache manager
cache = ApiCacheManager(max_size=1000)

# Cache a response
cache.set(
    request_path="/api/v1/agents",
    params={"status": "active"},
    value={"agents": [...]},
    metadata={"cache_time": 300}
)

# Retrieve cached response
cached_value = cache.get("/api/v1/agents", {"status": "active"})

# Invalidate cache entries
cache.invalidate(pattern="/api/v1/agents")

# Get cache statistics
stats = cache.get_stats()
# Returns: {'hits': 150, 'misses': 50, 'hit_rate': 0.75, 'size': 42}
```

### 4. API Circuit Breaker

**Purpose**: Provides fault tolerance by preventing cascading failures when backend services are unavailable.

**Key Features**:
- Three states: CLOSED, OPEN, HALF_OPEN
- Automatic state transitions
- Configurable thresholds
- Fallback responses
- Per-endpoint circuit breakers

**Classes**:
- `CircuitState`: Enumeration of circuit states
- `CircuitBreakerConfig`: Configuration parameters
- `CircuitBreakerStats`: Statistics tracking
- `ApiFallbackService`: Fallback response management
- `CircuitBreakerManager`: Multi-endpoint management
- `ApiCircuitBreaker`: Main circuit breaker logic

**Usage Example**:
```python
from netra_backend.app.services.api_gateway.circuit_breaker import (
    CircuitBreakerManager,
    CircuitBreakerConfig
)

# Initialize circuit breaker manager
cb_manager = CircuitBreakerManager()

# Get circuit breaker for endpoint
config = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=3
)
circuit_breaker = cb_manager.get_circuit_breaker("/api/v1/agents", config)

# Execute with circuit breaker protection
try:
    result = circuit_breaker.call(backend_service_call, endpoint_params)
except CircuitBreakerOpenError:
    # Return fallback response
    result = cb_manager.fallback_service.get_fallback("/api/v1/agents")

# Get circuit breaker stats
stats = circuit_breaker.get_stats()
# Returns: {'state': 'closed', 'failure_count': 2, 'success_count': 98}
```

### 5. Transformation Engine

**Purpose**: Transforms request and response data between different API schemas and formats.

**Key Features**:
- Schema mapping
- Data type conversion
- Custom transformation rules
- Field-level transformations
- Bidirectional transformation

**Classes**:
- `TransformationRule`: Individual transformation rule
- `SchemaMapper`: Maps between API schemas
- `DataConverter`: Type and format conversion
- `TransformationEngine`: Main transformation orchestration

**Usage Example**:
```python
from netra_backend.app.services.api_gateway.transformation_engine import (
    TransformationEngine,
    TransformationRule
)

# Initialize transformation engine
transformer = TransformationEngine()

# Add schema mapping
transformer.schema_mapper.add_mapping(
    source_schema="v1",
    target_schema="v2",
    field_mappings={
        "agent_id": "id",
        "agent_name": "name",
        "agent_status": "status"
    }
)

# Add custom transformation rule
rule = TransformationRule(
    name="uppercase_status",
    source_field="status",
    target_field="status",
    transformer=lambda x: x.upper()
)
transformer.add_transformation(rule)

# Transform request
request_data = {"agent_id": "123", "agent_name": "GPT", "agent_status": "active"}
transformed = transformer.transform_request(request_data, "v1", "v2")
# Returns: {"id": "123", "name": "GPT", "status": "ACTIVE"}
```

## Configuration

### Environment Variables

```bash
# Rate Limiting
API_GATEWAY_RATE_LIMIT_PER_MINUTE=60
API_GATEWAY_RATE_LIMIT_PER_HOUR=1000
API_GATEWAY_BURST_SIZE=10

# Caching
API_GATEWAY_CACHE_TTL=300
API_GATEWAY_CACHE_MAX_SIZE=1000

# Circuit Breaker
API_GATEWAY_CB_FAILURE_THRESHOLD=5
API_GATEWAY_CB_RECOVERY_TIMEOUT=60
API_GATEWAY_CB_SUCCESS_THRESHOLD=3

# General
API_GATEWAY_ENABLED=true
```

### Configuration File Example

```yaml
# api_gateway_config.yaml
router:
  routes:
    - path: "/api/v1/agents"
      method: "GET"
      target: "http://agent-service:8001"
      weight: 100
    - path: "/api/v1/threads"
      method: "POST"
      target: "http://thread-service:8002"
      weight: 100

rate_limiter:
  default:
    requests_per_minute: 60
    requests_per_hour: 1000
  clients:
    enterprise_tier:
      requests_per_minute: 200
      requests_per_hour: 10000

cache:
  strategy: "default"
  ttl: 300
  max_size: 1000

circuit_breaker:
  default:
    failure_threshold: 5
    recovery_timeout: 60
    success_threshold: 3
```

## Integration Patterns

### 1. FastAPI Integration

```python
from fastapi import FastAPI, Request, HTTPException
from netra_backend.app.services.api_gateway.router import ApiGatewayRouter
from netra_backend.app.services.api_gateway.rate_limiter import ApiGatewayRateLimiter
from netra_backend.app.services.api_gateway.cache_manager import ApiCacheManager

app = FastAPI()
router = ApiGatewayRouter()
rate_limiter = ApiGatewayRateLimiter()
cache_manager = ApiCacheManager()

@app.middleware("http")
async def api_gateway_middleware(request: Request, call_next):
    # Extract client ID
    client_id = request.headers.get("X-Client-ID", "anonymous")
    
    # Check rate limit
    if not rate_limiter.is_allowed(client_id, request.url.path):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Check cache
    cache_key_params = dict(request.query_params)
    cached_response = cache_manager.get(request.url.path, cache_key_params)
    if cached_response:
        return cached_response
    
    # Process request
    response = await call_next(request)
    
    # Cache response if successful
    if response.status_code == 200:
        cache_manager.set(request.url.path, cache_key_params, response)
    
    return response
```

### 2. Async Request Handling

```python
import asyncio
from netra_backend.app.services.api_gateway.circuit_breaker import ApiCircuitBreaker

async def process_with_gateway(endpoint: str, params: dict):
    """Process request through API Gateway components."""
    
    # Rate limiting check
    if not rate_limiter.is_allowed(client_id, endpoint):
        return {"error": "Rate limit exceeded"}, 429
    
    # Cache check
    cached = cache_manager.get(endpoint, params)
    if cached:
        return cached, 200
    
    # Circuit breaker protected call
    circuit_breaker = cb_manager.get_circuit_breaker(endpoint)
    
    try:
        result = await circuit_breaker.call(
            async_backend_call,
            endpoint,
            params
        )
        
        # Cache successful response
        cache_manager.set(endpoint, params, result)
        return result, 200
        
    except CircuitBreakerOpenError:
        return {"error": "Service unavailable"}, 503
```

### 3. Multi-Service Orchestration

```python
class ApiGatewayOrchestrator:
    """Orchestrates multiple API Gateway components."""
    
    def __init__(self):
        self.router = ApiGatewayRouter()
        self.rate_limiter = ApiGatewayRateLimiter()
        self.cache_manager = ApiCacheManager()
        self.circuit_breaker_manager = CircuitBreakerManager()
        self.transformer = TransformationEngine()
    
    async def handle_request(
        self,
        client_id: str,
        path: str,
        method: str,
        data: dict,
        schema_version: str = "v1"
    ):
        # Rate limiting
        if not self.rate_limiter.is_allowed(client_id, path):
            return {"error": "Rate limit exceeded"}, 429
        
        # Routing
        target = self.router.route_request(path, method)
        if not target:
            return {"error": "Route not found"}, 404
        
        # Cache check
        cached = self.cache_manager.get(path, data)
        if cached:
            return cached, 200
        
        # Transform request
        transformed_data = self.transformer.transform_request(
            data, schema_version, "internal"
        )
        
        # Circuit breaker protected call
        cb = self.circuit_breaker_manager.get_circuit_breaker(path)
        try:
            result = await cb.call(
                self._backend_call,
                target,
                transformed_data
            )
        except CircuitBreakerOpenError:
            fallback = self.circuit_breaker_manager.fallback_service.get_fallback(path)
            return fallback, 503
        
        # Transform response
        response = self.transformer.transform_response(
            result, "internal", schema_version
        )
        
        # Cache response
        self.cache_manager.set(path, data, response)
        
        return response, 200
```

## Best Practices

### 1. Rate Limiting
- Set reasonable defaults for different client tiers
- Monitor rate limit violations to adjust thresholds
- Implement gradual backoff for clients approaching limits
- Use burst tokens for handling traffic spikes

### 2. Caching
- Cache only idempotent GET requests
- Set appropriate TTLs based on data volatility
- Implement cache warming for critical endpoints
- Monitor cache hit rates to optimize configuration
- Use cache invalidation patterns for data updates

### 3. Circuit Breaking
- Configure thresholds based on service SLAs
- Implement meaningful fallback responses
- Monitor circuit state transitions
- Use half-open state for gradual recovery
- Set appropriate recovery timeouts

### 4. Request Transformation
- Version API schemas explicitly
- Document all transformation rules
- Validate transformed data
- Handle transformation errors gracefully
- Maintain backward compatibility

### 5. Monitoring and Observability
- Track key metrics:
  - Request rate and latency
  - Cache hit/miss ratio
  - Circuit breaker state changes
  - Rate limit violations
  - Transformation errors
- Set up alerts for:
  - Circuit breaker opens
  - High rate limit violations
  - Low cache hit rates
  - Transformation failures

## Testing

### Unit Testing Example

```python
import pytest
from netra_backend.app.services.api_gateway.rate_limiter import ApiGatewayRateLimiter

def test_rate_limiter():
    limiter = ApiGatewayRateLimiter()
    client_id = "test_client"
    
    # Should allow initial requests
    for _ in range(60):
        assert limiter.is_allowed(client_id, "/api/test")
    
    # Should block after limit
    assert not limiter.is_allowed(client_id, "/api/test")
    
    # Reset and verify
    limiter.reset_client(client_id)
    assert limiter.is_allowed(client_id, "/api/test")
```

### Integration Testing

```python
async def test_api_gateway_integration():
    orchestrator = ApiGatewayOrchestrator()
    
    # Configure components
    orchestrator.router.add_route("/api/test", "GET", "http://backend:8000")
    
    # Test successful request
    response, status = await orchestrator.handle_request(
        client_id="test",
        path="/api/test",
        method="GET",
        data={},
        schema_version="v1"
    )
    assert status == 200
    
    # Test rate limiting
    for _ in range(100):
        await orchestrator.handle_request("test", "/api/test", "GET", {})
    
    response, status = await orchestrator.handle_request(
        "test", "/api/test", "GET", {}
    )
    assert status == 429
```

## Troubleshooting

### Common Issues and Solutions

1. **High cache miss rate**
   - Review cache key generation logic
   - Increase cache size if evictions are frequent
   - Adjust TTL values based on data patterns

2. **Circuit breaker frequently opening**
   - Review failure threshold settings
   - Check backend service health
   - Implement retry logic with exponential backoff

3. **Rate limit violations for legitimate traffic**
   - Review and adjust rate limit configurations
   - Implement client tier differentiation
   - Consider implementing sliding window rate limiting

4. **Transformation errors**
   - Validate input data before transformation
   - Add comprehensive error handling
   - Log transformation failures for debugging

## Performance Considerations

### Optimization Tips

1. **Caching Strategy**
   - Use Redis for distributed caching in production
   - Implement cache preloading for frequently accessed data
   - Use compression for large cached values

2. **Rate Limiting**
   - Use Redis for distributed rate limiting
   - Implement sliding window algorithm for smoother rate limiting
   - Consider using token bucket algorithm for burst handling

3. **Circuit Breaker**
   - Tune thresholds based on actual service performance
   - Implement gradual recovery with increasing success thresholds
   - Use distributed state storage for multi-instance deployments

4. **Request Routing**
   - Implement health checks for backend services
   - Use weighted round-robin for load distribution
   - Consider implementing sticky sessions where appropriate

## Security Considerations

1. **Authentication & Authorization**
   - Validate API keys/tokens before processing
   - Implement role-based access control
   - Use secure headers for client identification

2. **Input Validation**
   - Validate all input data before transformation
   - Implement request size limits
   - Sanitize data to prevent injection attacks

3. **Rate Limiting**
   - Implement IP-based rate limiting for anonymous clients
   - Use progressive rate limiting for suspected abuse
   - Log and monitor rate limit violations

4. **Monitoring**
   - Log all gateway decisions for audit trails
   - Monitor for unusual traffic patterns
   - Implement alerting for security events

## Future Enhancements

1. **Advanced Load Balancing**
   - Implement least connections algorithm
   - Add health-check based routing
   - Support for sticky sessions

2. **Enhanced Caching**
   - Implement distributed caching with Redis
   - Add cache warming strategies
   - Support for partial response caching

3. **Advanced Circuit Breaking**
   - Implement adaptive thresholds
   - Add predictive circuit breaking
   - Support for cascading circuit breakers

4. **Request/Response Transformation**
   - Add GraphQL to REST transformation
   - Implement protocol translation (HTTP to gRPC)
   - Support for response aggregation

5. **Observability**
   - Integrate with OpenTelemetry
   - Add distributed tracing
   - Implement SLI/SLO monitoring

## Conclusion

The Netra Apex API Gateway provides a robust, scalable solution for managing API traffic with enterprise-grade features. Its modular architecture ensures maintainability and extensibility while providing essential capabilities for modern microservices architectures. By following the best practices and integration patterns outlined in this documentation, teams can effectively implement and operate the API Gateway to ensure optimal performance, reliability, and security for their AI workload optimization platform.