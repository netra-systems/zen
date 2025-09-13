# Netra Apex API Documentation

## Table of Contents
- [Overview](#overview)
- [Business Metrics APIs](#business-metrics-apis) **← Revenue & Savings Tracking**
- [Authentication](#authentication)
- [REST API Endpoints](#rest-api-endpoints)
- [WebSocket API](#websocket-api)
- [Rate Limiting](#rate-limiting)
- [API Versioning](#api-versioning)

## Overview

The Netra Apex API enables enterprise customers to integrate AI optimization capabilities directly into their workflows. APIs are designed to maximize value capture through real-time cost analysis and optimization recommendations.

**Base URL**: 
- Production: `https://api.netrasystems.ai`
- Staging: `https://staging-api.netrasystems.ai`
- Development: `http://localhost:8000`

### API Tiers by Customer Segment

| Segment | Rate Limits | Features | SLA |
|---------|------------|----------|-----|
| **Free** | 100 req/hr | Basic optimization | Best effort |
| **Early** | 1000 req/hr | Full optimization + analytics | 99.5% |
| **Mid** | 10000 req/hr | + Bulk operations | 99.9% |
| **Enterprise** | Unlimited | + Custom endpoints | 99.99% |

## Authentication

### JWT Authentication

The API uses JWT (JSON Web Tokens) for authentication. Tokens are obtained through the login endpoint and must be included in the Authorization header for protected endpoints.

```http
Authorization: Bearer <your-jwt-token>
```

### OAuth 2.0 (Google)

Google OAuth 2.0 is supported for user authentication:

1. Get configuration from `/auth/config`
2. Redirect user to `/auth/login`
3. Handle callback at `/auth/callback`
4. Frontend receives JWT token via redirect

## REST API Endpoints

### Authentication Endpoints

#### Authentication Configuration
```http
GET /auth/config

Response:
{
  "development_mode": true,
  "google_client_id": "your-google-client-id",
  "endpoints": {
    "login": "http://localhost:8000/auth/login",
    "logout": "http://localhost:8000/auth/logout",
    "callback": "http://localhost:8000/auth/callback",
    "token": "http://localhost:8000/auth/token",
    "user": "http://localhost:8000/api/users/me",
    "dev_login": "http://localhost:8000/auth/dev_login"
  },
  "authorized_javascript_origins": ["http://localhost:3000"],
  "authorized_redirect_uris": ["http://localhost:8000/auth/callback"]
}
```

#### OAuth2 Token Exchange
```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=your-password&grant_type=password

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

#### Google OAuth Login
```http
GET /auth/login
Redirects to Google OAuth consent page or proxy for PR environments

Response:
Redirect to Google OAuth or proxy URL
```

#### OAuth Callback
```http
GET /auth/callback?code=<auth-code>&state=<state>
Handles OAuth callback from Google

Response:
Redirect to frontend with token:
http://localhost:3000/auth/callback?token=<jwt-token>

Error Response:
Redirect to frontend with error:
http://localhost:3000/auth/error?message=<error-message>
```

#### Logout
```http
POST /auth/logout

Response:
{
  "message": "Successfully logged out",
  "success": true
}
```

#### Development Login
```http
POST /auth/dev_login
Content-Type: application/json

{
  "email": "dev@example.com"
}

Response:
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}

Note: Only available in development mode when DEV_LOGIN=true
```

### Thread Management

#### List Threads
```http
GET /api/threads
Authorization: Bearer <token>

Query Parameters:
- limit: Number of threads to return (default: 20, max: 100)
- offset: Pagination offset (default: 0, min: 0)

Response:
[
  {
    "id": "thread-uuid",
    "object": "thread",
    "title": "Thread Title",
    "created_at": 1642262400,
    "updated_at": 1642262400,
    "metadata": {},
    "message_count": 0
  }
]
```

#### Create Thread
```http
POST /api/threads
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "My Optimization Thread",
  "metadata": {
    "project": "AI Workload Optimization"
  }
}

Response:
{
  "id": "thread-uuid",
  "object": "thread",
  "title": "My Optimization Thread",
  "created_at": 1642262400,
  "updated_at": 1642262400,
  "metadata": {
    "project": "AI Workload Optimization"
  },
  "message_count": 0
}
```

#### Get Thread
```http
GET /api/threads/{thread_id}
Authorization: Bearer <token>

Response:
{
  "id": "thread-uuid",
  "object": "thread",
  "title": "Thread Title",
  "created_at": 1642262400,
  "updated_at": 1642262400,
  "metadata": {},
  "message_count": 5
}
```

#### Update Thread
```http
PUT /api/threads/{thread_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Updated Thread Title",
  "metadata": {
    "updated": true
  }
}

Response:
{
  "id": "thread-uuid",
  "object": "thread",
  "title": "Updated Thread Title",
  "created_at": 1642262400,
  "updated_at": 1642262500,
  "metadata": {
    "updated": true
  },
  "message_count": 5
}
```

#### Delete Thread
```http
DELETE /api/threads/{thread_id}
Authorization: Bearer <token>

Response:
{
  "success": true,
  "message": "Thread archived successfully"
}
```

#### Get Thread Messages
```http
GET /api/threads/{thread_id}/messages
Authorization: Bearer <token>

Query Parameters:
- limit: Number of messages to return (default: 50, max: 100)
- offset: Pagination offset (default: 0, min: 0)

Response:
{
  "messages": [
    {
      "id": "message-uuid",
      "role": "user",
      "content": "Optimize my AI workload",
      "created_at": 1642262460
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

#### Auto-rename Thread
```http
POST /api/threads/{thread_id}/auto-rename
Authorization: Bearer <token>

Response:
{
  "id": "thread-uuid",
  "title": "AI Workload Optimization Discussion",
  "success": true
}
```

### Agent Operations

#### Get Agent Status
```http
GET /api/agent/status/{run_id}
Authorization: Bearer <token>

Response:
{
  "run_id": "run-uuid",
  "status": "completed",
  "thread_id": "thread-uuid",
  "created_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:05:00Z",
  "steps": [
    {
      "agent_name": "TriageSubAgent",
      "status": "completed",
      "duration_ms": 1200
    }
  ]
}
```

#### Get Agent History
```http
GET /api/agent/history
Authorization: Bearer <token>

Query Parameters:
- thread_id: Filter by thread (optional)
- limit: Number of runs to return (default: 10)
- offset: Pagination offset (default: 0)

Response:
{
  "runs": [
    {
      "run_id": "run-uuid",
      "thread_id": "thread-uuid",
      "status": "completed",
      "created_at": "2024-01-15T10:00:00Z",
      "duration_ms": 5000
    }
  ],
  "total": 25
}
```

## Business Metrics APIs

### Savings Dashboard
```http
GET /api/metrics/savings
Authorization: Bearer <token>

Query Parameters:
- period: day|week|month|quarter (default: month)
- breakdown: true|false (show by model/provider)

Response:
{
  "total_ai_spend": 125000.00,
  "optimized_spend": 87500.00,
  "total_savings": 37500.00,
  "savings_percentage": 30.0,
  "netra_fee": 7500.00,  // 20% of savings
  "net_savings": 30000.00,
  "optimization_count": 15234,
  "breakdown": {
    "by_model": [
      {
        "model": "gpt-4",
        "original_cost": 50000,
        "optimized_cost": 30000,
        "savings": 20000
      }
    ]
  }
}
```

### ROI Calculator
```http
POST /api/metrics/roi-estimate
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_monthly_spend": 50000,
  "workload_breakdown": {
    "chat": 0.3,
    "analysis": 0.4,
    "generation": 0.3
  },
  "volume_growth_rate": 0.15
}

Response:
{
  "estimated_monthly_savings": 12500,
  "savings_percentage": 25,
  "netra_monthly_fee": 2500,
  "net_monthly_benefit": 10000,
  "annual_roi": 120000,
  "time_to_value_days": 7,
  "confidence_level": 0.85
}
```

### Usage Analytics
```http
GET /api/metrics/usage
Authorization: Bearer <token>

Response:
{
  "period": "2024-01",
  "total_requests": 523421,
  "optimized_requests": 498234,
  "optimization_rate": 0.952,
  "models_used": {
    "gpt-4": 234123,
    "gpt-3.5-turbo": 189234,
    "claude-3": 99877
  },
  "cost_by_model": {...},
  "latency_improvements": {
    "average_ms_saved": 230,
    "p95_ms_saved": 450
  }
}
```

### Supply Catalog

#### Get Optimized Model Recommendations
```http
POST /api/supply/recommend
Authorization: Bearer <token>

{
  "task_type": "text_generation",
  "requirements": {
    "max_latency_ms": 500,
    "quality_threshold": 0.9,
    "max_cost_per_1k_tokens": 0.02
  },
  "context_length": 4000
}

Response:
{
  "recommendations": [
    {
      "model": "gpt-3.5-turbo",
      "provider": "OpenAI",
      "estimated_cost": 0.002,
      "estimated_latency_ms": 230,
      "quality_score": 0.92,
      "savings_vs_default": 0.028,
      "reasoning": "Optimal balance of cost and quality for this task"
    }
  ],
  "total": 150
}
```

### Unified Tools

#### Access Unified Tool Interface
```http
GET /api/unified-tools
Authorization: Bearer <token>

Response:
{
  "available_tools": [
    {
      "id": "cost_analyzer",
      "name": "Cost Analyzer",
      "description": "Analyze AI workload costs",
      "parameters": {...}
    }
  ]
}
```

### Quality Validation

#### Validate Quality
```http
POST /api/quality/validate
Authorization: Bearer <token>
Content-Type: application/json

{
  "data": {...},
  "validation_type": "data_quality",
  "criteria": [...]
}

Response:
{
  "validation_result": "passed",
  "quality_score": 0.95,
  "recommendations": [...]
}
```

#### Estimate Optimization
```http
POST /api/supply/estimate
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_setup": {
    "model": "gpt-4",
    "provider": "openai",
    "monthly_tokens": 1000000
  },
  "optimization_goals": ["cost", "latency"]
}

Response:
{
  "recommendations": [
    {
      "model": "claude-3-sonnet",
      "provider": "anthropic",
      "estimated_savings": 45.5,
      "latency_improvement": 15.2,
      "confidence": 0.92
    }
  ]
}
```

### Content Generation

#### Start Generation
```http
POST /api/generation/start
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt": "Generate optimization report",
  "type": "report",
  "parameters": {
    "format": "markdown",
    "include_charts": true
  }
}

Response:
{
  "job_id": "gen-uuid",
  "status": "processing",
  "estimated_time": 30
}
```

### System Monitoring

#### Get System Metrics
```http
GET /api/monitoring/metrics
Authorization: Bearer <token>

Response:
{
  "system_health": "operational",
  "database_metrics": {...},
  "websocket_connections": 42,
  "agent_executions": {...}
}
```

#### Database Health Monitoring
```http
GET /api/database-monitoring
Authorization: Bearer <token>

Response:
{
  "postgres": {
    "status": "healthy",
    "connections": 8,
    "query_performance": {...}
  },
  "clickhouse": {...},
  "redis": {...}
}
```

#### Check Generation Status
```http
GET /api/generation/status/{job_id}
Authorization: Bearer <token>

Response:
{
  "job_id": "gen-uuid",
  "status": "completed",
  "result": {
    "content": "# Optimization Report\n...",
    "metadata": {
      "word_count": 500,
      "charts": 3
    }
  }
}
```

### LLM Cache Operations

#### Get Cache Stats
```http
GET /api/llm-cache/stats
Authorization: Bearer <token>

Response:
{
  "total_entries": 1250,
  "hit_rate": 0.73,
  "total_size_mb": 45.2,
  "savings_usd": 127.50
}
```

#### Clear Cache
```http
DELETE /api/llm-cache/clear
Authorization: Bearer <token>

Query Parameters:
- context: Specific context to clear (optional)

Response:
{
  "message": "Cache cleared successfully",
  "entries_removed": 250
}
```

### Corpus Management

#### List Corpus Items
```http
GET /api/corpus
Authorization: Bearer <token>

Query Parameters:
- category: Filter by category
- search: Search term
- limit: Results per page
- offset: Pagination offset

Response:
{
  "items": [
    {
      "id": "corpus-uuid",
      "title": "AI Optimization Best Practices",
      "category": "documentation",
      "tags": ["optimization", "best-practices"],
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 500
}
```

#### Synthetic Data Corpus
```http
GET /api/synthetic-data-corpus
Authorization: Bearer <token>

Response:
{
  "synthetic_items": [
    {
      "id": "synthetic-uuid",
      "type": "generated_scenario",
      "content": "...",
      "metadata": {...}
    }
  ]
}
```

#### Add Corpus Item
```http
POST /api/corpus
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "New Best Practice",
  "content": "Content here...",
  "category": "documentation",
  "tags": ["optimization"]
}

Response:
{
  "id": "corpus-uuid",
  "message": "Corpus item added successfully"
}
```

### Health & Monitoring

#### Basic Health Check
```http
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "version": "1.0.0"
}
```

#### Extended Health Monitoring
```http
GET /health/extended

Response:
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "redis": "healthy", 
    "clickhouse": "healthy",
    "circuit_breakers": "operational",
    "system_metrics": {...}
  },
  "detailed_metrics": {...}
}
```

#### Readiness Check
```http
GET /health/ready

Response:
{
  "status": "ready",
  "checks": {
    "database": "healthy",
    "redis": "healthy",
    "clickhouse": "healthy"
  }
}
```

#### Dependency Status
```http
GET /health/dependencies

Response:
{
  "dependencies": {
    "postgresql": {
      "status": "connected",
      "latency_ms": 2.5,
      "version": "14.5"
    },
    "redis": {
      "status": "connected",
      "latency_ms": 0.8,
      "version": "7.0"
    },
    "clickhouse": {
      "status": "connected",
      "latency_ms": 3.2,
      "version": "23.8"
    },
    "llm_providers": {
      "gemini": "available",
      "openai": "available"
    }
  }
}
```

## WebSocket API

### Connection

Connect to the WebSocket endpoint with JWT authentication:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=<jwt-token>');
```

### Message Format

All WebSocket messages follow this structure:

```typescript
interface WebSocketMessage {
  type: string;
  data: any;
  metadata?: {
    thread_id?: string;
    run_id?: string;
    agent_name?: string;
    timestamp: string;
  };
}
```

### Message Types

#### Client to Server

##### Start Agent Execution
```json
{
  "action": "start_agent",
  "data": {
    "message": "Optimize my AI workload for cost",
    "thread_id": "thread-uuid",
    "context": {
      "current_setup": {...}
    }
  }
}
```

##### Send Message
```json
{
  "action": "send_message",
  "data": {
    "content": "What are the optimization options?",
    "thread_id": "thread-uuid"
  }
}
```

##### Heartbeat
```json
{
  "action": "heartbeat"
}
```

#### Server to Client

##### Connection Established
```json
{
  "type": "connection_established",
  "data": {
    "session_id": "session-uuid",
    "user_id": "user-uuid"
  }
}
```

##### Agent Started
```json
{
  "type": "agent_started",
  "data": {
    "run_id": "run-uuid",
    "thread_id": "thread-uuid"
  }
}
```

##### Sub-Agent Update
```json
{
  "type": "sub_agent_update",
  "data": {
    "agent_name": "TriageSubAgent",
    "status": "thinking",
    "message": "Analyzing request..."
  },
  "metadata": {
    "thread_id": "thread-uuid",
    "run_id": "run-uuid",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

##### Tool Call
```json
{
  "type": "tool_call",
  "data": {
    "tool_name": "cost_analyzer",
    "parameters": {
      "model": "gpt-4",
      "usage": 1000000
    }
  }
}
```

##### Tool Result
```json
{
  "type": "tool_result",
  "data": {
    "tool_name": "cost_analyzer",
    "result": {
      "current_cost": 30.00,
      "optimized_cost": 16.50,
      "savings": 45.0
    }
  }
}
```

##### Agent Log
```json
{
  "type": "agent_log",
  "data": {
    "level": "info",
    "message": "Processing optimization request",
    "agent_name": "OptimizationsCoreSubAgent"
  }
}
```

##### Agent Completed
```json
{
  "type": "agent_completed",
  "data": {
    "run_id": "run-uuid",
    "result": {
      "recommendations": [...],
      "summary": "...",
      "savings": 45.5
    }
  }
}
```

##### Error
```json
{
  "type": "error",
  "data": {
    "code": "AGENT_ERROR",
    "message": "Failed to process request",
    "details": {...}
  }
}
```

##### Heartbeat
```json
{
  "type": "heartbeat",
  "data": {
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

## Error Handling

### Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context"
    },
    "trace_id": "trace-uuid"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Error Examples

#### Validation Error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": {
      "email": "Invalid email format",
      "password": "Password must be at least 8 characters"
    },
    "trace_id": "trace-123"
  }
}
```

#### Rate Limit Error
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests",
    "details": {
      "limit": 100,
      "window": "1h",
      "retry_after": 3600
    },
    "trace_id": "trace-456"
  }
}
```

## Rate Limiting

API requests are rate-limited based on plan tier:

| Plan Tier | Requests/Hour | Concurrent WebSocket | Cache Size |
|-----------|---------------|---------------------|------------|
| Free | 100 | 1 | 10 MB |
| Pro | 1,000 | 5 | 100 MB |
| Enterprise | 10,000 | 50 | 1 GB |
| Developer | Unlimited | Unlimited | Unlimited |

Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1705318800
```

## API Versioning

The API uses implicit versioning. Most endpoints are available at the root level:

```http
https://api.netrasystems.ai/api/threads
```

Some specialized endpoints may use versioned paths when needed for backward compatibility.

### Version Support Policy

- Current version: Full support
- Previous version: 6 months deprecation notice
- Older versions: Best effort support

### Breaking Changes

Breaking changes will be introduced in new major versions only. Minor versions may include:
- New endpoints
- New optional parameters
- New response fields
- Performance improvements

## SDK Examples

### Python
```python
import requests
import json

# Authentication
response = requests.post(
    "http://localhost:8000/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = response.json()["access_token"]

# Create thread
headers = {"Authorization": f"Bearer {token}"}
thread_response = requests.post(
    "http://localhost:8000/api/threads",
    headers=headers,
    json={"name": "My Thread"}
)
thread_id = thread_response.json()["id"]

# WebSocket connection
import websocket

ws = websocket.WebSocket()
ws.connect(f"ws://localhost:8000/ws?token={token}")
ws.send(json.dumps({
    "action": "start_agent",
    "data": {
        "message": "Optimize my AI costs",
        "thread_id": thread_id
    }
}))
```

### JavaScript/TypeScript
```typescript
// Authentication
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password'
  })
});
const { access_token } = await loginResponse.json();

// Create thread
const threadResponse = await fetch('http://localhost:8000/api/threads', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ name: 'My Thread' })
});
const { id: threadId } = await threadResponse.json();

// WebSocket connection
const ws = new WebSocket(`ws://localhost:8000/ws?token=${access_token}`);

ws.onopen = () => {
  ws.send(JSON.stringify({
    action: 'start_agent',
    data: {
      message: 'Optimize my AI costs',
      thread_id: threadId
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

## Support

For API support and questions:
- Documentation: https://docs.netrasystems.ai
- GitHub Issues: https://github.com/netrasystems/netra-core/issues
- Email: api-support@netrasystems.ai

---

**Last Updated**: December 2025  
**Document Version**: 2.0  
**API Status**: Production Ready - All Endpoints Operational  
**Business Integration**: $500K+ ARR Revenue Tracking Active  

## Current API Health (2025-12-09)

- **Authentication**: ✅ OAuth 2.0 + JWT fully operational
- **WebSocket API**: ✅ Real-time agent events validated
- **Business Metrics**: ✅ ROI calculator and savings tracking active
- **Agent Operations**: ✅ Multi-agent orchestration stable
- **Rate Limiting**: ✅ Tier-based limits enforced
- **System Monitoring**: ✅ Health endpoints operational