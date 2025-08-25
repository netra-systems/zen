# Netra API Reference

Complete API documentation for the Netra AI Optimization Platform apex-v1.

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

#### GET /api/auth/config
Get authentication configuration.

**Response:**
```json
{
  "development_mode": false,
  "google_client_id": "your-google-client-id",
  "endpoints": {
    "login": "/api/auth/login",
    "logout": "/api/auth/logout",
    "callback": "/api/auth/callback",
    "token": "/api/auth/token",
    "user": "/api/users/me",
    "dev_login": "/api/auth/dev_login"
  },
  "authorized_javascript_origins": [...],
  "authorized_redirect_uris": [...]
}
```

**Status Codes:**
- `200`: Success
- `500`: Configuration error

---

#### GET /api/auth/login
Initialize OAuth 2.0 flow with Google.

Redirects to Google OAuth authorization URL.

**Status Codes:**
- `302`: Redirect to Google OAuth
- `500`: OAuth configuration error

---

#### GET /api/auth/callback
Handle OAuth 2.0 callback from Google.

**Query Parameters:**
- `code`: Authorization code from Google
- `state`: State parameter for CSRF protection

Redirects to frontend with token or error.

**Status Codes:**
- `302`: Redirect to frontend with token
- `400`: Invalid authorization code
- `500`: OAuth processing error

---

#### POST /api/auth/logout
Logout the current user.

**Response:**
```json
{
  "message": "Successfully logged out",
  "success": true
}
```

**Status Codes:**
- `200`: Successful logout

---

#### POST /api/auth/dev_login
Development-only login endpoint.

**Request Body:**
```json
{
  "email": "dev@example.com"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Status Codes:**
- `200`: Successful login
- `403`: Not available in production

---

#### POST /api/auth/token
Token endpoint for OAuth2 password flow.

**Request Body (form-data):**
- `username`: Email address
- `password`: User password

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Status Codes:**
- `200`: Successful authentication
- `401`: Invalid credentials

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

### Agent Endpoints

**Note:** Agent execution is primarily handled via WebSocket connections. REST endpoints are available for stateless operations and streaming.

#### POST /api/agent/stream
Stream agent responses using Server-Sent Events (SSE).

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "Your question or request",
  "id": "optional-thread-id",
  "user_request": "optional-user-context"
}
```

**Response:**
Server-Sent Events stream with structured chunks:
```
data: {"id":"uuid","type":"stream_start","data":{"stream_id":"uuid"},"metadata":{"protocol":"sse"},"timestamp":"2025-08-14T10:00:00.000Z"}

data: {"id":"uuid","type":"data","data":"Response text chunk","metadata":{"stream_id":"uuid","chunk_index":0},"timestamp":"2025-08-14T10:00:00.100Z"}

data: {"id":"uuid","type":"stream_end","data":{"stream_id":"uuid"},"metadata":{"total_chunks":10,"duration_ms":1500},"timestamp":"2025-08-14T10:00:01.500Z"}
```

**Response Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no` (Disables nginx buffering)

**Status Codes:**
- `200`: Streaming started successfully
- `401`: Unauthorized
- `500`: Internal server error

---

#### POST /api/agent/message
Process a message through the agent system (non-streaming).

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "message": "Your question or request",
  "thread_id": "optional-thread-id"
}
```

**Response:**
```json
{
  "response": "Agent's response to your message",
  "agent": "supervisor",
  "status": "success"
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized
- `500`: Internal server error

---

#### POST /api/agent/run_agent
Legacy endpoint - starts the agent to analyze a user's request.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "Optimize my AI workload for cost efficiency",
  "id": "run-789"
}
```

**Response:**
```json
{
  "run_id": "run-789",
  "status": "started"
}
```

**Status Codes:**
- `200`: Execution started
- `400`: Invalid request
- `401`: Unauthorized
- `500`: Internal server error

---

#### GET /api/agent/{run_id}/status
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
  "current_step": 5,
  "total_steps": 5
}
```

**Status Codes:**
- `200`: Success
- `404`: Run not found
- `401`: Unauthorized

---

#### GET /api/agent/{run_id}/state
Get the full agent state for a run.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `run_id`: The ID of the execution run

**Response:**
```json
{
  "run_id": "run-789",
  "state": {
    "status": "completed",
    "current_sub_agent": "ReportingSubAgent",
    "context": {...},
    "results": {...}
  }
}
```

**Status Codes:**
- `200`: Success
- `404`: State not found
- `401`: Unauthorized

---

#### GET /api/agent/thread/{thread_id}/runs
Get all runs for a thread.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `thread_id`: The ID of the thread

**Query Parameters:**
- `limit` (optional, default: 10): Number of runs to return

**Response:**
```json
{
  "thread_id": "thread-456",
  "runs": [
    {
      "run_id": "run-789",
      "status": "completed",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `404`: Thread not found
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
[
  {
    "id": "thread-456",
    "object": "thread",
    "title": "Cost Optimization Session",
    "created_at": 1640995200,
    "updated_at": 1640998800,
    "metadata": {
      "title": "Cost Optimization Session",
      "status": "active"
    },
    "message_count": 10
  }
]
```

---

#### POST /api/threads/
Create a new thread.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "My Optimization Session",
  "metadata": {
    "description": "Custom metadata"
  }
}
```

**Response:**
```json
{
  "id": "thread_abc123",
  "object": "thread",
  "title": "My Optimization Session",
  "created_at": 1640995200,
  "metadata": {
    "title": "My Optimization Session",
    "status": "active"
  },
  "message_count": 0
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized
- `500`: Creation failed

---

#### GET /api/threads/{thread_id}
Get a specific thread.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `thread_id`: Thread identifier

**Response:**
```json
{
  "id": "thread-456",
  "object": "thread",
  "title": "Cost Optimization Session",
  "created_at": 1640995200,
  "updated_at": 1640998800,
  "metadata": {
    "title": "Cost Optimization Session",
    "status": "active"
  },
  "message_count": 5
}
```

---

#### PUT /api/threads/{thread_id}
Update a thread.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `thread_id`: Thread identifier

**Request Body:**
```json
{
  "title": "Updated Title",
  "metadata": {
    "updated_field": "value"
  }
}
```

**Response:**
```json
{
  "id": "thread-456",
  "object": "thread",
  "title": "Updated Title",
  "created_at": 1640995200,
  "updated_at": 1640998800,
  "metadata": {
    "title": "Updated Title",
    "updated_field": "value"
  },
  "message_count": 5
}
```

**Status Codes:**
- `200`: Success
- `404`: Thread not found
- `401`: Unauthorized
- `403`: Access denied

---

#### DELETE /api/threads/{thread_id}
Archive a thread.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `thread_id`: Thread identifier

**Response:**
```json
{
  "message": "Thread archived successfully"
}
```

**Status Codes:**
- `200`: Success
- `404`: Thread not found
- `401`: Unauthorized
- `403`: Access denied

---

#### GET /api/threads/{thread_id}/messages
Get messages for a specific thread.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `thread_id`: Thread identifier

**Query Parameters:**
- `limit` (optional, default: 50): Number of messages to return
- `offset` (optional, default: 0): Pagination offset

**Response:**
```json
{
  "thread_id": "thread-456",
  "messages": [
    {
      "id": "msg-123",
      "role": "user",
      "content": "Optimize my workload",
      "created_at": 1640995200,
      "metadata": {}
    },
    {
      "id": "msg-124",
      "role": "assistant",
      "content": "I'll help you optimize...",
      "created_at": 1640995205,
      "metadata": {
        "type": "agent_response"
      }
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Status Codes:**
- `200`: Success
- `404`: Thread not found
- `401`: Unauthorized
- `403`: Access denied

---

### Supply Catalog Endpoints

#### GET /api/supply-catalog/
Retrieve all supply catalog options.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "id": 1,
    "name": "NVIDIA A100",
    "type": "GPU",
    "specifications": {
      "memory": "40GB",
      "compute_capability": "8.0"
    },
    "pricing": {
      "hourly_rate": 3.20,
      "currency": "USD"
    }
  }
]
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

#### POST /api/supply-catalog/
Create a new supply option.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "NVIDIA H100",
  "type": "GPU",
  "specifications": {
    "memory": "80GB",
    "compute_capability": "9.0"
  },
  "pricing": {
    "hourly_rate": 4.50,
    "currency": "USD"
  }
}
```

**Response:**
```json
{
  "id": 2,
  "name": "NVIDIA H100",
  "type": "GPU",
  "specifications": {
    "memory": "80GB",
    "compute_capability": "9.0"
  },
  "pricing": {
    "hourly_rate": 4.50,
    "currency": "USD"
  }
}
```

**Status Codes:**
- `201`: Created
- `400`: Validation error
- `401`: Unauthorized

---

#### GET /api/supply-catalog/{option_id}
Get a specific supply option.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `option_id`: Supply option ID

**Response:**
```json
{
  "id": 1,
  "name": "NVIDIA A100",
  "type": "GPU",
  "specifications": {...},
  "pricing": {...}
}
```

**Status Codes:**
- `200`: Success
- `404`: Option not found
- `401`: Unauthorized

---

### Content Generation Endpoints

#### POST /api/generation/content
Start content generation job.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "topic": "AI workload optimization",
  "content_type": "documentation",
  "parameters": {
    "length": "detailed",
    "style": "technical"
  }
}
```

**Response:**
```json
{
  "job_id": "gen-123456",
  "message": "Content generation job started."
}
```

**Status Codes:**
- `202`: Job started
- `400`: Invalid parameters
- `401`: Unauthorized

---

#### POST /api/generation/logs
Start synthetic log generation job.

**Request Body:**
```json
{
  "num_logs": 1000,
  "time_range": "24h",
  "log_types": ["performance", "error", "access"]
}
```

**Response:**
```json
{
  "job_id": "log-789012",
  "message": "Synthetic log generation job started."
}
```

**Status Codes:**
- `202`: Job started
- `400`: Invalid parameters
- `401`: Unauthorized

---

#### GET /api/generation/jobs/{job_id}
Get generation job status.

**Path Parameters:**
- `job_id`: Generation job ID

**Response:**
```json
{
  "job_id": "gen-123456",
  "status": "completed",
  "progress": 100,
  "result": {
    "output_path": "/path/to/generated/content",
    "metadata": {...}
  },
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:00Z"
}
```

**Status Codes:**
- `200`: Success
- `404`: Job not found

---

#### GET /api/generation/content
List available content corpuses.

**Response:**
```json
[
  {
    "corpus_id": "content-123",
    "path": "/app/data/generated/content_corpuses/content-123/content_corpus.json"
  }
]
```

**Status Codes:**
- `200`: Success

---

### Corpus Management Endpoints

#### GET /api/corpus/
List all corpus entries.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `skip` (optional, default: 0): Pagination offset
- `limit` (optional, default: 100): Number of entries to return

**Response:**
```json
[
  {
    "id": "corpus-123",
    "name": "AI Optimization Corpus",
    "description": "Training data for AI workload optimization",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

#### POST /api/corpus/
Create a new corpus.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "New Corpus",
  "description": "Description of the corpus",
  "metadata": {
    "domain": "optimization",
    "version": "1.0"
  }
}
```

**Response:**
```json
{
  "id": "corpus-456",
  "name": "New Corpus",
  "description": "Description of the corpus",
  "status": "creating",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Status Codes:**
- `200`: Created
- `400`: Validation error
- `401`: Unauthorized

---

#### GET /api/corpus/tables
List corpus tables in ClickHouse.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
[
  "corpus_ai_optimization_v1",
  "corpus_performance_data_v2"
]
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

### References Endpoints

#### GET /api/references
Get all available reference items.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "references": [
    {
      "id": 1,
      "title": "GPU Optimization Guide",
      "type": "documentation",
      "url": "https://docs.example.com/gpu-optimization",
      "description": "Comprehensive guide for GPU workload optimization"
    }
  ]
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

#### POST /api/references
Create a new reference item.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "title": "New Reference",
  "type": "article",
  "url": "https://example.com/article",
  "description": "Reference description"
}
```

**Response:**
```json
{
  "id": 2,
  "title": "New Reference",
  "type": "article",
  "url": "https://example.com/article",
  "description": "Reference description"
}
```

**Status Codes:**
- `200`: Created
- `400`: Validation error
- `401`: Unauthorized

---

### LLM Cache Endpoints

#### GET /api/llm-cache/stats
Get LLM cache statistics.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `llm_config_name` (optional): Filter by specific LLM config

**Response:**
```json
{
  "cache_enabled": true,
  "default_ttl": 3600,
  "stats": {
    "hits": 150,
    "misses": 25,
    "total": 175,
    "hit_rate": 0.857
  }
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

#### DELETE /api/llm-cache/clear
Clear LLM cache entries.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `llm_config_name` (optional): Clear specific LLM config cache

**Response:**
```json
{
  "success": true,
  "deleted_entries": 47,
  "scope": "all",
  "message": "Successfully cleared 47 cache entries"
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized
- `500`: Clear operation failed

---

#### POST /api/llm-cache/toggle
Enable or disable LLM response caching.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "cache_enabled": true,
  "message": "Cache enabled successfully"
}
```

**Status Codes:**
- `200`: Success
- `401`: Unauthorized

---

### Synthetic Data Generation Endpoints

#### POST /api/synthetic/generate
Generate synthetic AI workload data.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "corpus_id": "corpus-123",
  "domain_focus": "cost_optimization",
  "tool_catalog": [
    {
      "name": "cost_estimator",
      "type": "analysis",
      "latency_ms_range": [100, 300],
      "failure_rate": 0.01
    }
  ],
  "workload_distribution": {
    "inference": 0.7,
    "training": 0.3
  },
  "scale_parameters": {
    "num_traces": 10000,
    "time_window_hours": 24,
    "concurrent_users": 50
  }
}
```

**Response:**
```json
{
  "job_id": "synth-789",
  "status": "started",
  "estimated_duration_seconds": 100,
  "websocket_channel": "user_123_synthetic_data",
  "table_name": "synthetic_workload_data_20240101"
}
```

**Status Codes:**
- `200`: Job started
- `400`: Invalid parameters
- `401`: Unauthorized
- `500`: Generation failed

---

#### GET /api/synthetic/status/{job_id}
Get synthetic data generation job status.

**Headers:**
- `Authorization: Bearer <token>`

**Path Parameters:**
- `job_id`: Generation job ID

**Response:**
```json
{
  "job_id": "synth-789",
  "status": "completed",
  "progress_percentage": 100.0,
  "records_generated": 10000,
  "records_ingested": 10000,
  "errors": [],
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:05:00Z"
}
```

**Status Codes:**
- `200`: Success
- `404`: Job not found
- `401`: Unauthorized
- `403`: Access denied

---

#### GET /api/synthetic/preview
Preview sample synthetic data before generation.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `corpus_id` (optional): Corpus to use for generation
- `workload_type`: Type of workload to generate
- `sample_size` (optional, default: 10): Number of samples

**Response:**
```json
{
  "samples": [
    {
      "workload_id": "wl-123",
      "type": "inference",
      "metrics": {
        "total_latency_ms": 150,
        "tokens_per_second": 25
      },
      "tool_invocations": ["cost_estimator"]
    }
  ],
  "estimated_characteristics": {
    "avg_latency_ms": 145.5,
    "tool_diversity": 3,
    "sample_count": 10
  }
}
```

**Status Codes:**
- `200`: Success
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

### Connection Features

- **Authentication**: JWT token required in query parameters
- **Per-user Connection Tracking**: Multiple concurrent connections per user supported
- **Automatic Heartbeat**: Server sends ping every 30 seconds, 60-second timeout
- **Connection Recovery**: Automatic cleanup of stale connections
- **Message Queuing**: Priority-based message processing system
- **Real-time Updates**: Live agent execution status and tool invocations
- **State Persistence**: Agent state maintained across reconnections

### Message Format

All WebSocket messages use JSON format:

```typescript
interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp?: number;
  system?: boolean;  // For system messages like heartbeat
  displayed_to_user?: boolean;  // Whether message should be shown to user
}
```

### Message Metadata

Messages include contextual information:

```typescript
interface MessageContext {
  thread_id?: string;
  run_id?: string;
  agent_name?: string;
  sub_agent_name?: string;
  connection_id?: string;
  timestamp: number;
}
```

### Message Types

#### Client to Server Messages

##### start_agent
Start agent processing:
```json
{
  "type": "start_agent",
  "payload": {
    "request": {
      "query": "Optimize my GPU workload for cost efficiency",
      "user_request": "Help me reduce costs while maintaining performance"
    }
  }
}
```

##### user_message
Send user message to agent:
```json
{
  "type": "user_message",
  "payload": {
    "text": "What are the current optimization recommendations?",
    "references": ["@cost_analysis", "@performance_metrics"]
  }
}
```

##### stop_agent
Stop current agent processing:
```json
{
  "type": "stop_agent",
  "payload": {
    "run_id": "run-789"
  }
}
```

##### get_thread_history
Get thread message history:
```json
{
  "type": "get_thread_history",
  "payload": {
    "limit": 50
  }
}
```

##### ping
Keep connection alive (handled automatically by client):
```json
{
  "type": "ping",
  "timestamp": 1640995200
}
```

#### Server to Client Messages

##### connection_established
Connection successfully established:
```json
{
  "type": "connection_established",
  "connection_id": "conn_1640995200123",
  "timestamp": 1640995200.123,
  "system": true
}
```

##### agent_started
Agent execution started:
```json
{
  "type": "agent_started",
  "payload": {
    "run_id": "run-789",
    "thread_id": "thread-456",
    "agent_name": "Supervisor",
    "status": "started"
  },
  "timestamp": 1640995200.456
}
```

##### sub_agent_update
Real-time sub-agent status updates:
```json
{
  "type": "sub_agent_update",
  "payload": {
    "run_id": "run-789",
    "agent_name": "TriageSubAgent",
    "status": "processing",
    "message": "Analyzing request requirements...",
    "progress": 25,
    "current_step": "data_analysis"
  },
  "timestamp": 1640995201.789,
  "displayed_to_user": true
}
```

##### tool_call
Tool invocation notification:
```json
{
  "type": "tool_call",
  "payload": {
    "tool_name": "cost_estimator",
    "tool_args": {
      "workload_type": "inference",
      "instance_type": "g5.xlarge"
    },
    "sub_agent_name": "OptimizationCoreSubAgent",
    "timestamp": 1640995202.123
  },
  "displayed_to_user": true
}
```

##### tool_result
Tool execution result:
```json
{
  "type": "tool_result",
  "payload": {
    "tool_name": "cost_estimator",
    "result": {
      "estimated_cost_per_hour": 1.23,
      "cost_breakdown": {
        "compute": 0.85,
        "storage": 0.38
      }
    },
    "sub_agent_name": "OptimizationCoreSubAgent",
    "timestamp": 1640995203.456
  },
  "displayed_to_user": true
}
```

##### agent_completed
Agent execution completed:
```json
{
  "type": "agent_completed",
  "payload": {
    "run_id": "run-789",
    "thread_id": "thread-456",
    "agent_name": "Supervisor",
    "status": "completed",
    "result": {
      "recommendations": [
        {
          "action": "Switch to A100 GPUs",
          "impact": "30% performance improvement",
          "cost_change": "+15%"
        }
      ],
      "supply_config": {},
      "optimization_summary": "Cost reduced by 12% while maintaining performance"
    }
  },
  "timestamp": 1640995210.789
}
```

##### agent_log
Real-time agent logging:
```json
{
  "type": "agent_log",
  "payload": {
    "level": "info",
    "message": "Starting workload analysis...",
    "sub_agent_name": "DataSubAgent",
    "timestamp": 1640995204.123
  },
  "displayed_to_user": true
}
```

##### error
Error notifications:
```json
{
  "type": "error",
  "payload": {
    "error": "Failed to analyze workload: Invalid configuration provided",
    "sub_agent_name": "DataSubAgent"
  },
  "timestamp": 1640995205.456,
  "displayed_to_user": true
}
```

##### heartbeat (ping)
Server heartbeat (sent every 30 seconds):
```json
{
  "type": "ping",
  "timestamp": 1640995200.123,
  "system": true
}
```

##### thread_history
Thread message history response:
```json
{
  "event": "thread_history",
  "thread_id": "thread-456",
  "messages": [
    {
      "id": "msg-123",
      "role": "user",
      "content": "Optimize my workload",
      "created_at": 1640995200
    },
    {
      "id": "msg-124",
      "role": "assistant", 
      "content": "I'll help you optimize your workload...",
      "created_at": 1640995205
    }
  ]
}
```

### WebSocket Error Codes

| Code | Description | Usage |
|------|-------------|-------|
| 1000 | Normal closure | Clean disconnect |
| 1001 | Going away | Server shutdown or connection lost |
| 1002 | Protocol error | WebSocket protocol violation |
| 1003 | Unsupported data | Unsupported message type |
| 1006 | Abnormal closure | Connection dropped |
| 1007 | Invalid frame payload | Malformed message data |
| 1008 | Policy violation | Authentication or authorization failed |
| 1009 | Message too big | Message exceeds size limit |
| 1011 | Internal server error | Server-side error |
| 4000 | Authentication failed | Invalid or missing token |
| 4001 | Token expired | JWT token has expired |
| 4002 | Invalid message format | JSON parsing or schema validation failed |
| 4003 | Rate limit exceeded | Too many messages sent |

### Connection Statistics

The WebSocket manager tracks detailed statistics:

```json
{
  "total_connections": 1250,
  "total_messages_sent": 45230,
  "total_messages_received": 12450,
  "total_errors": 23,
  "connection_failures": 5,
  "active_connections": 12,
  "active_users": 8,
  "connections_by_user": {
    "user123": 2,
    "user456": 1
  }
}
```

### WebSocket Connection Lifecycle

1. **Connection**: Client connects with JWT token via query parameter
2. **Authentication**: Server validates token and user
3. **Connection Established**: Server sends `connection_established` message
4. **Heartbeat Setup**: Server starts heartbeat loop (30s intervals)
5. **Communication**: Bidirectional message exchange with queuing system
6. **Heartbeat Maintenance**: Automatic ping/pong every 30 seconds (60s timeout)
7. **Error Handling**: Automatic reconnection with exponential backoff
8. **Cleanup**: Graceful disconnect or timeout cleanup

### Agent Pipeline Architecture

The Netra platform uses a sophisticated multi-agent pipeline:

1. **Supervisor Agent**: Orchestrates the overall workflow and coordinates sub-agents
2. **Triage Sub-Agent**: Analyzes incoming requests and determines the appropriate processing strategy
3. **Data Sub-Agent**: Fetches and analyzes relevant data from logs, metrics, and configurations
4. **Optimization Core Sub-Agent**: Performs core optimization analysis using 30+ specialized tools
5. **Actions Sub-Agent**: Generates actionable recommendations to meet optimization goals
6. **Reporting Sub-Agent**: Compiles results into comprehensive reports and summaries

### Apex Optimizer Agent Tools

The Optimization Core Sub-Agent has access to specialized tools including:

- **cost_estimator**: Calculates cost implications of different configurations
- **performance_predictor**: Predicts performance metrics for proposed changes
- **supply_catalog_search**: Searches available hardware and service options
- **log_analyzer**: Analyzes system logs for optimization opportunities
- **policy_proposer**: Suggests policy changes for automated optimization
- **multi_objective_optimization**: Balances multiple optimization objectives
- **kv_cache_optimization_audit**: Optimizes key-value cache configurations
- **tool_latency_optimization**: Reduces tool execution latencies
- **advanced_optimization_for_core_function**: Advanced optimization algorithms

### State Persistence and Recovery

The system maintains persistent state across sessions:

- **Thread State**: Conversation history and context preservation
- **Agent State**: Current execution state and intermediate results
- **Run Tracking**: Complete audit trail of all agent executions
- **Auto-Recovery**: Automatic state restoration after disconnections
- **Concurrent Sessions**: Support for multiple concurrent user sessions

### Example WebSocket Client

```javascript
// JavaScript/TypeScript example
const token = localStorage.getItem('jwt_token');
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

ws.onopen = () => {
  console.log('Connected to Netra WebSocket');
  
  // Send start agent request
  ws.send(JSON.stringify({
    type: 'start_agent',
    payload: {
      request: {
        query: 'Optimize my workload for cost efficiency'
      }
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch(message.type) {
    case 'connection_established':
      console.log(`Connected with ID: ${message.connection_id}`);
      break;
    case 'sub_agent_update':
      console.log(`${message.payload.agent_name}: ${message.payload.message}`);
      break;
    case 'agent_completed':
      console.log('Optimization complete:', message.payload.result);
      break;
    case 'tool_call':
      console.log(`Tool called: ${message.payload.tool_name}`);
      break;
    case 'error':
      console.error('Error:', message.payload.error);
      break;
    case 'ping':
      // Respond to heartbeat
      ws.send('pong');
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

Standard error response format based on NetraException:

```json
{
  "error": {
    "code": "AUTH_FAILED",
    "message": "Authentication failed",
    "severity": "high",
    "user_message": "Please check your credentials and try again",
    "timestamp": "2024-01-01T00:00:00Z",
    "trace_id": "trace-123456",
    "details": {
      "field": "email",
      "additional_context": "value"
    },
    "context": {
      "request_path": "/api/auth/login",
      "user_agent": "Mozilla/5.0..."
    }
  }
}
```

### Common Error Codes

#### General Errors (1000-1999)
| Code | HTTP Status | Description |
|------|------------|-------------|
| INTERNAL_ERROR | 500 | Internal server error |
| CONFIGURATION_ERROR | 500 | Configuration issue |
| VALIDATION_ERROR | 422 | Data validation failed |

#### Authentication Errors (2000-2999)
| Code | HTTP Status | Description |
|------|------------|-------------|
| AUTH_FAILED | 401 | Authentication failed |
| AUTH_UNAUTHORIZED | 403 | Access denied |
| AUTH_TOKEN_EXPIRED | 401 | Token has expired |
| AUTH_TOKEN_INVALID | 401 | Invalid token |

#### Database Errors (3000-3999)
| Code | HTTP Status | Description |
|------|------------|-------------|
| DB_CONNECTION_FAILED | 503 | Database connection failed |
| DB_QUERY_FAILED | 500 | Database query failed |
| DB_RECORD_NOT_FOUND | 404 | Record not found |
| DB_RECORD_EXISTS | 409 | Record already exists |

#### Service Errors (4000-4999)
| Code | HTTP Status | Description |
|------|------------|-------------|
| SERVICE_UNAVAILABLE | 503 | Service unavailable |
| SERVICE_TIMEOUT | 504 | Service timeout |
| EXTERNAL_SERVICE_ERROR | 502 | External service error |

#### Agent/LLM Errors (5000-5999)
| Code | HTTP Status | Description |
|------|------------|-------------|
| AGENT_EXECUTION_FAILED | 500 | Agent execution failed |
| LLM_REQUEST_FAILED | 502 | LLM API request failed |
| LLM_RATE_LIMIT_EXCEEDED | 429 | LLM rate limit exceeded |
| AGENT_TIMEOUT | 504 | Agent execution timeout |

#### WebSocket Errors (6000-6999)
| Code | WebSocket Code | Description |
|------|---------------|-------------|
| WS_CONNECTION_FAILED | 4000 | Connection failed |
| WS_MESSAGE_INVALID | 4002 | Invalid message format |
| WS_AUTH_FAILED | 4000 | Authentication failed |

#### File/Data Errors (7000-7999)
| Code | HTTP Status | Description |
|------|------------|-------------|
| FILE_NOT_FOUND | 404 | File not found |
| FILE_ACCESS_DENIED | 403 | File access denied |
| DATA_PARSING_ERROR | 422 | Data parsing failed |
| DATA_VALIDATION_ERROR | 422 | Data validation failed |

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

The API uses URL versioning. The current version is apex-v1:

```
https://api.netrasystems.ai/apex-...
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