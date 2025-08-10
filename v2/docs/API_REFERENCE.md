# Netra API Reference

Complete API documentation for the Netra AI Optimization Platform v2.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.netrasystems.ai`

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <token>
```

## REST API Endpoints

### Authentication Endpoints

#### POST /api/auth/login
Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Status Codes:**
- `200`: Successful login
- `401`: Invalid credentials
- `422`: Validation error

---

#### POST /api/auth/logout
Logout the current user.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

**Status Codes:**
- `200`: Successful logout
- `401`: Unauthorized

---

#### GET /api/auth/me
Get current authenticated user information.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

#### GET /api/auth/google/authorize
Initialize OAuth 2.0 flow with Google.

**Query Parameters:**
- `redirect_uri` (optional): Custom redirect URI after authentication

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=..."
}
```

**Status Codes:**
- `200`: Success
- `500`: OAuth configuration error

---

#### GET /api/auth/google/callback
Handle OAuth 2.0 callback from Google.

**Query Parameters:**
- `code`: Authorization code from Google
- `state`: State parameter for CSRF protection

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "John Doe",
    "picture": "https://..."
  }
}
```

**Status Codes:**
- `200`: Successful authentication
- `400`: Invalid authorization code
- `500`: OAuth processing error

---

### Agent Endpoints

#### POST /api/agent/execute
Execute an agent workflow for optimization.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "message": "Optimize my AI workload for cost efficiency",
  "context": {
    "workload_id": "wl-123",
    "parameters": {
      "priority": "cost",
      "constraints": ["gpu_memory", "latency"]
    }
  },
  "thread_id": "thread-456" // Optional
}
```

**Response:**
```json
{
  "run_id": "run-789",
  "thread_id": "thread-456",
  "status": "processing",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200`: Execution started
- `400`: Invalid request
- `401`: Unauthorized
- `500`: Internal server error

---

#### GET /api/agent/status/{run_id}
Get the status of an agent execution run.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `run_id`: The ID of the execution run

**Response:**
```json
{
  "run_id": "run-789",
  "status": "completed",
  "result": {
    "recommendations": [...],
    "metrics": {...},
    "actions": [...]
  },
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:00Z"
}
```

**Status Codes:**
- `200`: Success
- `404`: Run not found
- `401`: Unauthorized

---

#### GET /api/agent/history
Get execution history for the authenticated user.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (optional, default: 20): Number of results to return
- `offset` (optional, default: 0): Pagination offset
- `thread_id` (optional): Filter by thread ID

**Response:**
```json
{
  "runs": [
    {
      "run_id": "run-789",
      "thread_id": "thread-456",
      "status": "completed",
      "message": "Optimize my AI workload",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 50,
  "limit": 20,
  "offset": 0
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

### Thread Endpoints

#### GET /api/threads
Get all threads for the authenticated user.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (optional, default: 20): Number of results
- `offset` (optional, default: 0): Pagination offset

**Response:**
```json
{
  "threads": [
    {
      "id": "thread-456",
      "title": "Cost Optimization Session",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:05:00Z",
      "message_count": 10
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

---

#### GET /api/threads/{thread_id}
Get a specific thread with messages.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `thread_id`: Thread identifier

**Response:**
```json
{
  "id": "thread-456",
  "title": "Cost Optimization Session",
  "messages": [
    {
      "id": "msg-123",
      "role": "user",
      "content": "Optimize my workload",
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": "msg-124",
      "role": "assistant",
      "content": "I'll help you optimize...",
      "created_at": "2024-01-01T00:00:05Z"
    }
  ],
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

#### DELETE /api/threads/{thread_id}
Delete a thread and all its messages.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `thread_id`: Thread identifier

**Response:**
```json
{
  "message": "Thread deleted successfully"
}
```

**Status Codes:**
- `200`: Success
- `404`: Thread not found
- `401`: Unauthorized

---

### Health & Monitoring Endpoints

#### GET /health
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "2.0.0"
}
```

**Status Codes:**
- `200`: Service is healthy
- `503`: Service unavailable

---

#### GET /health/ready
Readiness probe for deployment orchestration.

**Response:**
```json
{
  "ready": true,
  "checks": {
    "database": "connected",
    "redis": "connected",
    "clickhouse": "connected"
  }
}
```

**Status Codes:**
- `200`: Service is ready
- `503`: Service not ready

---

#### GET /health/dependencies
Check status of all service dependencies.

**Response:**
```json
{
  "dependencies": {
    "postgresql": {
      "status": "healthy",
      "latency_ms": 5
    },
    "clickhouse": {
      "status": "healthy",
      "latency_ms": 10
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 2
    },
    "openai_api": {
      "status": "healthy",
      "latency_ms": 150
    }
  },
  "overall_status": "healthy"
}
```

---

### Configuration Endpoints

#### GET /api/config
Get application configuration (public settings only).

**Response:**
```json
{
  "environment": "production",
  "features": {
    "oauth_enabled": true,
    "websocket_enabled": true,
    "analytics_enabled": true
  },
  "limits": {
    "max_message_length": 10000,
    "max_thread_messages": 1000,
    "rate_limit_requests": 100
  }
}
```

---

## WebSocket API

### Connection

Connect to the WebSocket endpoint with JWT authentication:

```
ws://localhost:8000/ws?token=<jwt_token>
```

or in production:

```
wss://api.netrasystems.ai/ws?token=<jwt_token>
```

### Message Format

All WebSocket messages use JSON format:

```typescript
interface WebSocketMessage {
  type: string;
  data: any;
  timestamp?: string;
  id?: string;
}
```

### Message Types

#### Client to Server Messages

##### optimization_request
Request optimization analysis:
```json
{
  "type": "optimization_request",
  "data": {
    "message": "Optimize my GPU workload",
    "workload_id": "wl-123",
    "parameters": {
      "priority": "performance",
      "budget": 10000
    }
  }
}
```

##### stop_processing
Stop current agent processing:
```json
{
  "type": "stop_processing",
  "data": {
    "run_id": "run-789"
  }
}
```

##### ping
Keep connection alive:
```json
{
  "type": "ping"
}
```

#### Server to Client Messages

##### agent_update
Real-time agent status updates:
```json
{
  "type": "agent_update",
  "data": {
    "agent": "TriageSubAgent",
    "status": "processing",
    "message": "Analyzing request requirements...",
    "progress": 25
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

##### agent_result
Final agent execution result:
```json
{
  "type": "agent_result",
  "data": {
    "run_id": "run-789",
    "success": true,
    "result": {
      "recommendations": [
        {
          "action": "Switch to A100 GPUs",
          "impact": "30% performance improvement",
          "cost_change": "+15%"
        }
      ],
      "supply_config": {...},
      "metrics": {...}
    }
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

##### error
Error notifications:
```json
{
  "type": "error",
  "data": {
    "code": "PROCESSING_ERROR",
    "message": "Failed to analyze workload",
    "details": "Invalid workload configuration"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

##### status
Connection and system status:
```json
{
  "type": "status",
  "data": {
    "connected": true,
    "authenticated": true,
    "user_id": 1
  }
}
```

##### pong
Response to ping:
```json
{
  "type": "pong",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### WebSocket Error Codes

| Code | Description |
|------|-------------|
| 1000 | Normal closure |
| 1001 | Going away |
| 1002 | Protocol error |
| 1003 | Unsupported data |
| 1006 | Abnormal closure |
| 1007 | Invalid frame payload |
| 1008 | Policy violation |
| 1009 | Message too big |
| 1011 | Internal server error |
| 4000 | Authentication failed |
| 4001 | Token expired |
| 4002 | Invalid message format |
| 4003 | Rate limit exceeded |

### WebSocket Connection Lifecycle

1. **Connection**: Client connects with JWT token
2. **Authentication**: Server validates token
3. **Status Message**: Server sends initial status
4. **Communication**: Bidirectional message exchange
5. **Heartbeat**: Periodic ping/pong to maintain connection
6. **Closure**: Clean disconnect or error

### Example WebSocket Client

```javascript
// JavaScript/TypeScript example
const token = localStorage.getItem('jwt_token');
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

ws.onopen = () => {
  console.log('Connected to Netra WebSocket');
  
  // Send optimization request
  ws.send(JSON.stringify({
    type: 'optimization_request',
    data: {
      message: 'Optimize my workload',
      parameters: { priority: 'cost' }
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch(message.type) {
    case 'agent_update':
      console.log(`Agent ${message.data.agent}: ${message.data.message}`);
      break;
    case 'agent_result':
      console.log('Optimization complete:', message.data.result);
      break;
    case 'error':
      console.error('Error:', message.data.message);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  console.log(`Connection closed: ${event.code} - ${event.reason}`);
};
```

## Rate Limiting

API endpoints are rate-limited to ensure service stability:

| Endpoint Type | Limit | Window |
|--------------|-------|---------|
| Authentication | 5 requests | 1 minute |
| Agent Execution | 10 requests | 1 minute |
| General API | 100 requests | 1 minute |
| WebSocket Messages | 30 messages | 1 minute |

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: UTC timestamp when limit resets

## Error Responses

Standard error response format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context"
    }
  },
  "request_id": "req-123456"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| UNAUTHORIZED | 401 | Authentication required |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 422 | Invalid request data |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily down |

## Pagination

List endpoints support pagination using `limit` and `offset`:

```
GET /api/threads?limit=20&offset=40
```

Paginated responses include metadata:

```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "limit": 20,
    "offset": 40,
    "has_more": true
  }
}
```

## Versioning

The API uses URL versioning. The current version is v2:

```
https://api.netrasystems.ai/v2/...
```

Version information is also available in response headers:
- `X-API-Version: 2.0.0`

## SDK Support

Official SDKs are available for:

- Python: `pip install netra-sdk`
- JavaScript/TypeScript: `npm install @netra/sdk`
- Go: `go get github.com/netrasystems/netra-go`

## Support

For API support and questions:
- Documentation: [https://docs.netrasystems.ai](https://docs.netrasystems.ai)
- API Status: [https://status.netrasystems.ai](https://status.netrasystems.ai)
- Support Email: [api-support@netrasystems.ai](mailto:api-support@netrasystems.ai)