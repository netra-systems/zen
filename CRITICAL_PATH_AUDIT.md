# Netra Platform - Critical Path Audit Report

## Executive Summary
This audit traces the primary paths through the Netra platform for basic WebSocket connections, user authentication, and chat functionality. The system consists of three microservices (Frontend, Backend, Auth Service) with well-defined integration points.

---

## 1. WEBSOCKET CONNECTION FLOW

### Primary Path: Client → Backend WebSocket
**Entry Point:** Frontend WebSocket Connection
- **Frontend Initiation:** `frontend/providers/WebSocketProvider.tsx:88-113`
  - Creates secure WebSocket connection with JWT token
  - Handles token refresh via unified auth service
  - Manages connection lifecycle and message handling

**Backend WebSocket Endpoint:** `netra_backend/app/routes/websocket.py:69-206`
- **Main Endpoint:** `/ws` - Authenticated WebSocket endpoint
- **Authentication:** JWT via Authorization header or Sec-WebSocket-Protocol
- **Message Routing:** Routes messages through `MessageRouter` to appropriate handlers
- **Heartbeat:** Maintains connection with 45-second heartbeat interval
- **Security:** Rate limiting (30 msg/min), max connections (3/user), message size limit (8KB)

**WebSocket Core Infrastructure:** `netra_backend/app/websocket_core/`
- `WebSocketManager`: Connection management and user tracking
- `MessageRouter`: Routes messages to handlers based on type
- `WebSocketAuthenticator`: JWT validation for WebSocket connections
- `ConnectionSecurityManager`: Security validation and violation tracking

### Test Endpoints (Development Only)
- `/ws/test` (`websocket.py:492-598`) - Unauthenticated test endpoint
- `/websocket` (`websocket.py:479-489`) - Legacy compatibility endpoint

---

## 2. AUTHENTICATION FLOW

### Primary Path: OAuth → Auth Service → Backend Integration

**Auth Service Entry:** `auth_service/auth_core/routes/auth_routes.py`
- **OAuth Providers:** `/oauth/providers` (lines 113-150)
  - Google OAuth configuration check
  - GitHub OAuth configuration check
  - Returns available providers based on environment

**Backend Auth Integration:** `netra_backend/app/auth_integration/auth.py:46-99`
- **CRITICAL:** Backend ONLY integrates with auth service, never implements auth logic
- `get_current_user()`: Validates JWT token via auth service client
- Creates development users automatically in dev mode
- All auth operations proxied through `AuthServiceClient`

**Auth Service Client:** `netra_backend/app/clients/auth_client_core.py`
- HTTP client for auth service communication
- Token validation endpoint calls
- User synchronization between services

### Authentication Flow Sequence:
1. User initiates OAuth login via Frontend
2. Auth Service handles OAuth provider interaction
3. Auth Service generates JWT token
4. Frontend receives token and stores in context
5. Backend validates token via Auth Service for API calls
6. WebSocket uses token for secure connection establishment

---

## 3. CHAT/CONVERSATION FLOW

### Primary Path: Frontend → API → Thread Service → Database

**Frontend Thread Management:** `frontend/services/threadService.ts:22-69`
- `listThreads()`: GET `/api/threads` - Fetch user's threads
- `createThread()`: POST `/api/threads` - Create new conversation
- `getThreadMessages()`: GET `/api/threads/{id}/messages` - Fetch messages

**Backend Thread Routes:** `netra_backend/app/routes/threads_route.py:54-100`
- **List Threads:** `/api/threads/` (lines 54-61)
- **Create Thread:** POST `/api/threads/` (lines 63-70)
- **Get Thread:** `/api/threads/{thread_id}` (lines 72-79)
- **Get Messages:** `/api/threads/{thread_id}/messages` (line 99+)

**Thread Service Layer:** `netra_backend/app/services/thread_service.py:38-100`
- `ThreadService`: Core business logic for threads
- Uses Unit of Work pattern for database transactions
- Sends WebSocket events on thread creation
- Repository pattern for data access

### Message Flow Sequence:
1. User sends message via Frontend MessageInput component
2. Message sent through WebSocket connection
3. Backend MessageRouter routes to AgentMessageHandler
4. Message stored in database via ThreadService
5. Agent processes message and generates response
6. Response sent back via WebSocket to Frontend
7. Frontend updates UI with new message

---

## 4. SERVICE INTEGRATION POINTS

### Critical Integration Points:

**1. Frontend ↔ Backend API**
- REST API: `http://localhost:8000/api/*`
- WebSocket: `ws://localhost:8000/ws`
- Authentication: JWT Bearer tokens

**2. Backend ↔ Auth Service**
- Auth Service URL: `http://localhost:8001`
- Token Validation: `/auth/validate`
- User Sync: Shared PostgreSQL database

**3. Shared Infrastructure**
- **PostgreSQL:** Shared user/auth database
- **Redis:** Session management, caching
- **ClickHouse:** Analytics and metrics

### Configuration Management:
- **Unified Config:** `netra_backend/app/core/configuration/`
- **Environment Management:** `dev_launcher/isolated_environment.py`
- **CORS Configuration:** `shared/cors_config.py`

---

## 5. STARTUP SEQUENCE

### Application Initialization Order:

**1. Backend Startup** (`netra_backend/app/main.py:102-131`)
- Load environment configuration
- Create FastAPI app via `app_factory.py`
- Setup middleware stack (CORS, Auth, Security)
- Register routes and WebSocket endpoints
- Initialize lifespan manager

**2. App Factory** (`netra_backend/app/core/app_factory.py:161-188`)
- Create FastAPI instance with lifespan
- Configure error handlers
- Setup security middleware (IP blocking, path traversal)
- Setup request middleware (CORS, auth, logging)
- Register API routes
- Apply WebSocket CORS wrapper

**3. WebSocket Initialization**
- WebSocket core services initialized as singletons
- Message handlers registered with router
- Agent handlers connected to supervisor

---

## 6. IDENTIFIED ISSUES & RISKS

### Critical Issues:

**1. WebSocket Authentication Complexity**
- Multiple authentication methods (header vs subprotocol)
- Token refresh mechanism needs careful coordination
- Test endpoints bypass authentication (security risk if deployed)

**2. Service Dependency**
- Backend critically depends on Auth Service availability
- No fallback mechanism if Auth Service is down
- Shared database creates tight coupling

**3. Configuration Management**
- Multiple environment files (.env, .env.development, .env.development.local)
- Complex precedence rules for configuration loading
- Different behavior in staging/production vs development

### Recommendations:

1. **Implement Circuit Breaker** for Auth Service communication
2. **Add Health Checks** for service dependencies
3. **Standardize WebSocket Auth** to single method
4. **Remove Test Endpoints** from production builds
5. **Implement Graceful Degradation** for service failures
6. **Add Request Tracing** for debugging distributed calls

---

## 7. PRIMARY USER JOURNEY

### Complete Flow: User Login → Chat Interaction

1. **User Visits App** → Frontend loads at `http://localhost:3000`
2. **OAuth Login** → Redirected to Auth Service OAuth flow
3. **Token Generation** → Auth Service creates JWT after successful OAuth
4. **Frontend Auth** → Token stored in AuthContext
5. **WebSocket Connection** → Secure connection established with JWT
6. **Thread Creation** → POST `/api/threads` creates conversation
7. **Send Message** → Message sent via WebSocket
8. **Agent Processing** → Backend routes to agent for response
9. **Response Delivery** → Response sent back via WebSocket
10. **UI Update** → Frontend renders new message

### Key File Locations:
- **Entry Point:** `netra_backend/app/main.py`
- **WebSocket:** `netra_backend/app/routes/websocket.py`
- **Auth Integration:** `netra_backend/app/auth_integration/auth.py`
- **Thread Service:** `netra_backend/app/services/thread_service.py`
- **Frontend WS:** `frontend/providers/WebSocketProvider.tsx`
- **Auth Routes:** `auth_service/auth_core/routes/auth_routes.py`

---

## Audit Completed
**Date:** 2025-08-27
**Auditor:** System Analysis
**Status:** Primary paths verified and documented