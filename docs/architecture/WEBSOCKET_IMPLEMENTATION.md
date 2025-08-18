# WebSocket Implementation Documentation

Comprehensive documentation for the Netra platform's real-time WebSocket communication system.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Connection Management](#connection-management)
- [Message Protocol](#message-protocol)
- [Event Types](#event-types)
- [Backend Implementation](#backend-implementation)
- [Frontend Implementation](#frontend-implementation)
- [Error Handling](#error-handling)
- [Security](#security)
- [Performance & Scaling](#performance--scaling)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

The Netra platform uses WebSockets to provide real-time, bidirectional communication between the frontend and backend. This enables live updates during agent processing, instant notifications, and interactive chat experiences.

### Key Features

- **Real-time Updates**: Live agent status and progress updates
- **Bidirectional Communication**: Both client and server can initiate messages
- **Authentication**: JWT-based secure connections
- **Auto-reconnection**: Resilient connection management
- **Message Queuing**: Handles messages during disconnections
- **Type Safety**: Strongly typed message contracts

## Architecture

### WebSocket Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend Client                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │          WebSocket Provider (React)             │    │
│  │  • Connection management                        │    │
│  │  • Auto-reconnection                           │    │
│  │  • Message queuing                             │    │
│  └────────────────┬────────────────────────────────┘    │
└───────────────────┼──────────────────────────────────────┘
                    │ WSS://
┌───────────────────▼──────────────────────────────────────┐
│                  Load Balancer                           │
│  • SSL termination                                       │
│  • Sticky sessions                                       │
│  • Health checks                                         │
└───────────────────┬──────────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────────┐
│                Backend WebSocket Server                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │           WebSocket Manager (FastAPI)           │    │
│  │  • Connection pool                              │    │
│  │  • Authentication                               │    │
│  │  • Message routing                              │    │
│  └────────────────┬────────────────────────────────┘    │
└───────────────────┼──────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐     ┌────────▼────────┐
│  Agent System  │     │  Event Bus      │
│                │     │  (Redis Pub/Sub)│
└────────────────┘     └─────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **WebSocket Provider** | Client-side connection management, message handling |
| **Load Balancer** | SSL termination, routing, session affinity |
| **WebSocket Manager** | Server-side connection pool, authentication, routing |
| **Agent System** | Process optimization requests, send status updates |
| **Event Bus** | Distribute events across multiple server instances |

## Connection Management

### Backend Connection Handler

```python
# app/routes/websockets.py
from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from app.services.websocket_manager import WebSocketManager
from app.auth.dependencies import verify_websocket_token

class WebSocketEndpoint:
    def __init__(self):
        self.manager = WebSocketManager()
    
    async def websocket_endpoint(
        self,
        websocket: WebSocket,
        token: str = Query(...),
        client_id: Optional[str] = Query(None)
    ):
        """Main WebSocket endpoint"""
        try:
            # Authenticate connection
            user = await verify_websocket_token(token)
            if not user:
                await websocket.close(code=4000, reason="Authentication failed")
                return
            
            # Accept connection
            await websocket.accept()
            
            # Register connection
            connection_id = await self.manager.connect(
                websocket=websocket,
                user_id=user.id,
                client_id=client_id
            )
            
            # Send initial status
            await self.send_connection_status(websocket, connection_id, user)
            
            # Handle messages
            await self.handle_messages(websocket, connection_id, user)
            
        except WebSocketDisconnect:
            await self.manager.disconnect(connection_id)
        except Exception as e:
            await self.handle_error(websocket, e)
            await self.manager.disconnect(connection_id)
    
    async def handle_messages(
        self,
        websocket: WebSocket,
        connection_id: str,
        user: User
    ):
        """Handle incoming WebSocket messages"""
        while True:
            try:
                # Receive message
                data = await websocket.receive_json()
                
                # Validate message
                message = WebSocketMessage(**data)
                
                # Route message
                await self.route_message(message, connection_id, user)
                
            except WebSocketDisconnect:
                break
            except ValidationError as e:
                await self.send_error(websocket, "Invalid message format", e)
            except Exception as e:
                await self.send_error(websocket, "Processing error", e)
```

### WebSocket Manager

```python
# app/services/websocket_manager.py
from typing import Dict, Set
import asyncio

class WebSocketManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[int, Set[str]] = defaultdict(set)
        self.lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        client_id: Optional[str] = None
    ) -> str:
        """Register new connection"""
        async with self.lock:
            connection_id = str(uuid.uuid4())
            
            connection = WebSocketConnection(
                id=connection_id,
                websocket=websocket,
                user_id=user_id,
                client_id=client_id,
                connected_at=datetime.utcnow()
            )
            
            self.connections[connection_id] = connection
            self.user_connections[user_id].add(connection_id)
            
            # Log connection
            await self.log_connection_event("connect", connection)
            
            return connection_id
    
    async def disconnect(self, connection_id: str):
        """Remove connection"""
        async with self.lock:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                
                # Remove from user connections
                self.user_connections[connection.user_id].discard(connection_id)
                
                # Remove connection
                del self.connections[connection_id]
                
                # Log disconnection
                await self.log_connection_event("disconnect", connection)
    
    async def send_to_user(self, user_id: int, message: Dict):
        """Send message to all user connections"""
        connection_ids = self.user_connections.get(user_id, set())
        
        for conn_id in connection_ids:
            if conn_id in self.connections:
                await self.send_to_connection(conn_id, message)
    
    async def send_to_connection(self, connection_id: str, message: Dict):
        """Send message to specific connection"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            try:
                await connection.websocket.send_json(message)
            except Exception as e:
                # Handle send failure
                await self.handle_send_failure(connection_id, e)
    
    async def broadcast(self, message: Dict, exclude: Optional[Set[str]] = None):
        """Broadcast message to all connections"""
        exclude = exclude or set()
        
        for conn_id in self.connections:
            if conn_id not in exclude:
                await self.send_to_connection(conn_id, message)
    
    def get_connection_count(self) -> int:
        """Get total active connections"""
        return len(self.connections)
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get connection count for user"""
        return len(self.user_connections.get(user_id, set()))
```

### Connection State

```python
# app/models/websocket.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WebSocketConnection:
    """WebSocket connection state"""
    id: str
    websocket: WebSocket
    user_id: int
    client_id: Optional[str]
    connected_at: datetime
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if connection is stale"""
        return (datetime.utcnow() - self.last_activity).seconds > timeout_seconds
```

## Message Protocol

### Message Format

```python
# app/schemas/websocket.py
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime

class WebSocketMessage(BaseModel):
    """Standard WebSocket message format"""
    type: str = Field(..., description="Message type")
    data: Any = Field(..., description="Message payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    metadata: Optional[Dict] = {}

class OptimizationRequest(WebSocketMessage):
    """Optimization request message"""
    type: str = "optimization_request"
    data: OptimizationRequestData

class OptimizationRequestData(BaseModel):
    message: str
    workload_id: Optional[str]
    parameters: Optional[Dict]
    thread_id: Optional[str]

class AgentUpdate(WebSocketMessage):
    """Agent status update message"""
    type: str = "agent_update"
    data: AgentUpdateData

class AgentUpdateData(BaseModel):
    agent: str
    status: str
    message: str
    progress: Optional[int]
    details: Optional[Dict]

class ErrorMessage(WebSocketMessage):
    """Error message"""
    type: str = "error"
    data: ErrorData

class ErrorData(BaseModel):
    code: str
    message: str
    details: Optional[Any]
    retry_after: Optional[int]
```

### Message Validation

```python
# app/services/message_validator.py
class MessageValidator:
    """Validate WebSocket messages"""
    
    @staticmethod
    def validate_message(raw_data: Dict) -> WebSocketMessage:
        """Validate and parse message"""
        # Check message type
        message_type = raw_data.get("type")
        
        if not message_type:
            raise ValidationError("Message type is required")
        
        # Route to specific validator
        validators = {
            "optimization_request": OptimizationRequest,
            "stop_processing": StopProcessingMessage,
            "ping": PingMessage,
            "chat_message": ChatMessage
        }
        
        validator = validators.get(message_type)
        if not validator:
            raise ValidationError(f"Unknown message type: {message_type}")
        
        return validator(**raw_data)
    
    @staticmethod
    def validate_outgoing(message: Dict) -> bool:
        """Validate outgoing message"""
        required_fields = ["type", "data", "timestamp"]
        return all(field in message for field in required_fields)
```

## Event Types

### Client to Server Events

```typescript
// frontend/types/websocket.ts
export enum ClientEventType {
  OPTIMIZATION_REQUEST = "optimization_request",
  CHAT_MESSAGE = "chat_message",
  STOP_PROCESSING = "stop_processing",
  PING = "ping",
  SUBSCRIBE = "subscribe",
  UNSUBSCRIBE = "unsubscribe"
}

export interface ClientMessage {
  type: ClientEventType;
  data: any;
  correlation_id?: string;
}
```

### Server to Client Events

```typescript
export enum ServerEventType {
  AGENT_UPDATE = "agent_update",
  AGENT_RESULT = "agent_result",
  CHAT_RESPONSE = "chat_response",
  STATUS = "status",
  ERROR = "error",
  PONG = "pong",
  NOTIFICATION = "notification"
}

export interface ServerMessage {
  type: ServerEventType;
  data: any;
  timestamp: string;
  id: string;
  correlation_id?: string;
}
```

### Event Handlers

```python
# app/services/event_handlers.py
class WebSocketEventHandler:
    """Handle WebSocket events"""
    
    def __init__(self, agent_service, websocket_manager):
        self.agent_service = agent_service
        self.ws_manager = websocket_manager
        self.handlers = {
            "optimization_request": self.handle_optimization_request,
            "chat_message": self.handle_chat_message,
            "stop_processing": self.handle_stop_processing,
            "ping": self.handle_ping
        }
    
    async def handle_event(
        self,
        message: WebSocketMessage,
        connection_id: str,
        user: User
    ):
        """Route event to handler"""
        handler = self.handlers.get(message.type)
        
        if not handler:
            raise ValueError(f"No handler for event type: {message.type}")
        
        await handler(message, connection_id, user)
    
    async def handle_optimization_request(
        self,
        message: OptimizationRequest,
        connection_id: str,
        user: User
    ):
        """Handle optimization request"""
        # Create optimization task
        task_id = str(uuid.uuid4())
        
        # Send immediate acknowledgment
        await self.ws_manager.send_to_connection(
            connection_id,
            {
                "type": "status",
                "data": {
                    "status": "received",
                    "task_id": task_id
                },
                "correlation_id": message.correlation_id
            }
        )
        
        # Start agent processing
        asyncio.create_task(
            self.process_optimization(
                task_id=task_id,
                request=message.data,
                connection_id=connection_id,
                user=user
            )
        )
    
    async def process_optimization(
        self,
        task_id: str,
        request: OptimizationRequestData,
        connection_id: str,
        user: User
    ):
        """Process optimization with agent system"""
        try:
            # Setup callback for status updates
            async def status_callback(update: AgentUpdateData):
                await self.ws_manager.send_to_connection(
                    connection_id,
                    {
                        "type": "agent_update",
                        "data": update.dict(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            # Execute agent workflow
            result = await self.agent_service.execute_optimization(
                user_id=user.id,
                request=request,
                status_callback=status_callback
            )
            
            # Send final result
            await self.ws_manager.send_to_connection(
                connection_id,
                {
                    "type": "agent_result",
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            # Send error
            await self.ws_manager.send_to_connection(
                connection_id,
                {
                    "type": "error",
                    "data": {
                        "code": "PROCESSING_ERROR",
                        "message": str(e)
                    }
                }
            )
```

## Frontend Implementation

### WebSocket Provider

```typescript
// frontend/providers/WebSocketProvider.tsx
import React, { createContext, useContext, useEffect, useRef, useState } from 'react';

interface WebSocketContextType {
  isConnected: boolean;
  sendMessage: (message: ClientMessage) => void;
  subscribe: (eventType: string, handler: (data: any) => void) => void;
  unsubscribe: (eventType: string, handler: (data: any) => void) => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const messageQueue = useRef<ClientMessage[]>([]);
  const eventHandlers = useRef<Map<string, Set<(data: any) => void>>>(new Map());
  
  const connect = () => {
    const token = localStorage.getItem('jwt_token');
    if (!token) return;
    
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws?token=${token}`;
    ws.current = new WebSocket(wsUrl);
    
    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      
      // Send queued messages
      while (messageQueue.current.length > 0) {
        const message = messageQueue.current.shift();
        if (message) {
          ws.current?.send(JSON.stringify(message));
        }
      }
    };
    
    ws.current.onmessage = (event) => {
      try {
        const message: ServerMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.current.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      setIsConnected(false);
      
      // Attempt reconnection
      if (event.code !== 1000) { // Not a normal closure
        reconnectTimeout.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, 3000);
      }
    };
  };
  
  const handleMessage = (message: ServerMessage) => {
    // Call registered handlers for this event type
    const handlers = eventHandlers.current.get(message.type);
    if (handlers) {
      handlers.forEach(handler => handler(message.data));
    }
    
    // Global message handler
    const globalHandlers = eventHandlers.current.get('*');
    if (globalHandlers) {
      globalHandlers.forEach(handler => handler(message));
    }
  };
  
  const sendMessage = (message: ClientMessage) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      // Queue message for later
      messageQueue.current.push(message);
    }
  };
  
  const subscribe = (eventType: string, handler: (data: any) => void) => {
    if (!eventHandlers.current.has(eventType)) {
      eventHandlers.current.set(eventType, new Set());
    }
    eventHandlers.current.get(eventType)?.add(handler);
  };
  
  const unsubscribe = (eventType: string, handler: (data: any) => void) => {
    eventHandlers.current.get(eventType)?.delete(handler);
  };
  
  useEffect(() => {
    connect();
    
    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close(1000, 'Component unmounting');
      }
    };
  }, []);
  
  return (
    <WebSocketContext.Provider value={{ isConnected, sendMessage, subscribe, unsubscribe }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
};
```

### React Hook

```typescript
// frontend/hooks/useAgentOptimization.ts
import { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from '@/providers/WebSocketProvider';

interface OptimizationState {
  isProcessing: boolean;
  currentAgent: string | null;
  progress: number;
  result: any | null;
  error: string | null;
}

export const useAgentOptimization = () => {
  const { sendMessage, subscribe, unsubscribe } = useWebSocket();
  const [state, setState] = useState<OptimizationState>({
    isProcessing: false,
    currentAgent: null,
    progress: 0,
    result: null,
    error: null
  });
  
  useEffect(() => {
    const handleAgentUpdate = (data: any) => {
      setState(prev => ({
        ...prev,
        currentAgent: data.agent,
        progress: data.progress || prev.progress
      }));
    };
    
    const handleAgentResult = (data: any) => {
      setState(prev => ({
        ...prev,
        isProcessing: false,
        result: data,
        progress: 100
      }));
    };
    
    const handleError = (data: any) => {
      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: data.message
      }));
    };
    
    subscribe('agent_update', handleAgentUpdate);
    subscribe('agent_result', handleAgentResult);
    subscribe('error', handleError);
    
    return () => {
      unsubscribe('agent_update', handleAgentUpdate);
      unsubscribe('agent_result', handleAgentResult);
      unsubscribe('error', handleError);
    };
  }, [subscribe, unsubscribe]);
  
  const startOptimization = useCallback((request: any) => {
    setState({
      isProcessing: true,
      currentAgent: null,
      progress: 0,
      result: null,
      error: null
    });
    
    sendMessage({
      type: 'optimization_request',
      data: request,
      correlation_id: crypto.randomUUID()
    });
  }, [sendMessage]);
  
  const stopOptimization = useCallback(() => {
    sendMessage({
      type: 'stop_processing',
      data: {}
    });
  }, [sendMessage]);
  
  return {
    ...state,
    startOptimization,
    stopOptimization
  };
};
```

## Error Handling

### Connection Errors

```python
# app/services/websocket_error_handler.py
class WebSocketErrorHandler:
    """Handle WebSocket errors"""
    
    @staticmethod
    async def handle_connection_error(
        websocket: WebSocket,
        error: Exception
    ):
        """Handle connection-level errors"""
        error_message = {
            "type": "error",
            "data": {
                "code": "CONNECTION_ERROR",
                "message": str(error)
            }
        }
        
        try:
            await websocket.send_json(error_message)
        except:
            pass  # Connection might be broken
        
        # Log error
        logger.error(f"WebSocket connection error: {error}")
    
    @staticmethod
    async def handle_message_error(
        websocket: WebSocket,
        error: Exception,
        message: Optional[Dict] = None
    ):
        """Handle message processing errors"""
        error_data = {
            "code": "MESSAGE_ERROR",
            "message": str(error)
        }
        
        if message:
            error_data["original_message"] = message
        
        await websocket.send_json({
            "type": "error",
            "data": error_data
        })
    
    @staticmethod
    def get_error_code(error: Exception) -> str:
        """Map exception to error code"""
        error_mapping = {
            ValidationError: "VALIDATION_ERROR",
            AuthenticationError: "AUTH_ERROR",
            RateLimitError: "RATE_LIMIT",
            TimeoutError: "TIMEOUT"
        }
        
        for error_type, code in error_mapping.items():
            if isinstance(error, error_type):
                return code
        
        return "UNKNOWN_ERROR"
```

### Reconnection Strategy

```typescript
// frontend/utils/websocket-reconnect.ts
export class ReconnectingWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;
  private reconnectDecay = 1.5;
  private reconnectTimer: NodeJS.Timeout | null = null;
  
  constructor(url: string) {
    this.url = url;
    this.connect();
  }
  
  private connect() {
    this.ws = new WebSocket(this.url);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.onopen();
    };
    
    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event);
      
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.scheduleReconnect();
      }
      
      this.onclose(event);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.onerror(error);
    };
    
    this.ws.onmessage = (event) => {
      this.onmessage(event);
    };
  }
  
  private scheduleReconnect() {
    const timeout = Math.min(
      10000,
      this.reconnectInterval * Math.pow(this.reconnectDecay, this.reconnectAttempts)
    );
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      this.connect();
    }, timeout);
  }
  
  send(data: string | ArrayBuffer | Blob) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      throw new Error('WebSocket is not connected');
    }
  }
  
  close(code?: number, reason?: string) {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.ws?.close(code, reason);
  }
  
  // Event handlers to be overridden
  onopen() {}
  onclose(event: CloseEvent) {}
  onerror(error: Event) {}
  onmessage(event: MessageEvent) {}
}
```

## Security

### Authentication

```python
# app/auth/websocket_auth.py
async def verify_websocket_token(token: str) -> Optional[User]:
    """Verify JWT token for WebSocket connection"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != "access":
            return None
        
        # Check expiration
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            return None
        
        # Get user
        user = await get_user_by_id(payload["sub"])
        
        if not user or not user.is_active:
            return None
        
        return user
        
    except JWTError:
        return None
```

### Rate Limiting

```python
# app/middleware/websocket_rate_limit.py
class WebSocketRateLimiter:
    """Rate limiter for WebSocket messages"""
    
    def __init__(self, max_messages: int = 30, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.message_counts: Dict[str, List[datetime]] = defaultdict(list)
    
    async def check_rate_limit(self, connection_id: str) -> bool:
        """Check if connection has exceeded rate limit"""
        now = datetime.utcnow()
        
        # Clean old messages
        self.message_counts[connection_id] = [
            timestamp for timestamp in self.message_counts[connection_id]
            if (now - timestamp).seconds < self.window_seconds
        ]
        
        # Check count
        if len(self.message_counts[connection_id]) >= self.max_messages:
            return False
        
        # Record message
        self.message_counts[connection_id].append(now)
        return True
    
    async def handle_rate_limit_exceeded(
        self,
        websocket: WebSocket,
        connection_id: str
    ):
        """Handle rate limit exceeded"""
        await websocket.send_json({
            "type": "error",
            "data": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many messages",
                "retry_after": self.window_seconds
            }
        })
```

### Message Sanitization

```python
# app/security/websocket_sanitizer.py
class WebSocketMessageSanitizer:
    """Sanitize WebSocket messages"""
    
    @staticmethod
    def sanitize_input(data: Any) -> Any:
        """Sanitize user input"""
        if isinstance(data, str):
            # Remove potential XSS
            data = bleach.clean(data)
            
            # Limit length
            if len(data) > 10000:
                data = data[:10000]
        
        elif isinstance(data, dict):
            # Recursively sanitize
            return {
                key: WebSocketMessageSanitizer.sanitize_input(value)
                for key, value in data.items()
            }
        
        elif isinstance(data, list):
            # Limit array size
            if len(data) > 100:
                data = data[:100]
            
            return [
                WebSocketMessageSanitizer.sanitize_input(item)
                for item in data
            ]
        
        return data
```

## Performance & Scaling

### Connection Pooling

```python
# app/services/connection_pool.py
class WebSocketConnectionPool:
    """Connection pool for scaling"""
    
    def __init__(self, max_connections: int = 10000):
        self.max_connections = max_connections
        self.connections: Dict[str, WebSocketConnection] = {}
        self.connection_count = 0
    
    async def add_connection(
        self,
        websocket: WebSocket,
        user_id: int
    ) -> Optional[str]:
        """Add connection to pool"""
        if self.connection_count >= self.max_connections:
            # Pool is full
            await websocket.close(
                code=1013,  # Try again later
                reason="Server at capacity"
            )
            return None
        
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = WebSocketConnection(
            id=connection_id,
            websocket=websocket,
            user_id=user_id,
            connected_at=datetime.utcnow()
        )
        self.connection_count += 1
        
        return connection_id
    
    async def remove_connection(self, connection_id: str):
        """Remove connection from pool"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.connection_count -= 1
    
    async def cleanup_stale_connections(self):
        """Remove stale connections"""
        stale_connections = [
            conn_id for conn_id, conn in self.connections.items()
            if conn.is_stale()
        ]
        
        for conn_id in stale_connections:
            conn = self.connections[conn_id]
            await conn.websocket.close(code=1000, reason="Connection timeout")
            await self.remove_connection(conn_id)
```

### Redis Pub/Sub for Scaling

```python
# app/services/redis_pubsub.py
import redis.asyncio as redis

class WebSocketPubSub:
    """Redis pub/sub for multi-server WebSocket"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
        self.subscriptions = set()
    
    async def publish(self, channel: str, message: Dict):
        """Publish message to channel"""
        await self.redis.publish(
            channel,
            json.dumps(message)
        )
    
    async def subscribe(self, channel: str):
        """Subscribe to channel"""
        await self.pubsub.subscribe(channel)
        self.subscriptions.add(channel)
    
    async def listen(self):
        """Listen for messages"""
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
    
    async def close(self):
        """Close connections"""
        await self.pubsub.unsubscribe(*self.subscriptions)
        await self.redis.close()
```

### Load Balancing

```nginx
# nginx.conf for WebSocket load balancing
upstream websocket_backend {
    ip_hash;  # Sticky sessions
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    listen 443 ssl http2;
    server_name api.netrasystems.ai;
    
    location /ws {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
```

## Testing

### Unit Tests

```python
# tests/websocket/test_websocket_manager.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection"""
    manager = WebSocketManager()
    mock_websocket = Mock()
    
    # Test connection
    connection_id = await manager.connect(
        websocket=mock_websocket,
        user_id=1
    )
    
    assert connection_id is not None
    assert manager.get_connection_count() == 1
    assert manager.get_user_connection_count(1) == 1
    
    # Test disconnection
    await manager.disconnect(connection_id)
    assert manager.get_connection_count() == 0

@pytest.mark.asyncio
async def test_message_routing():
    """Test message routing"""
    handler = WebSocketEventHandler(Mock(), Mock())
    
    message = OptimizationRequest(
        data=OptimizationRequestData(
            message="Test",
            workload_id="test-123"
        )
    )
    
    await handler.handle_event(message, "conn-1", Mock())
    # Assert handler was called
```

### Integration Tests

```python
# tests/websocket/test_websocket_integration.py
from fastapi.testclient import TestClient

def test_websocket_flow():
    """Test complete WebSocket flow"""
    client = TestClient(app)
    
    with client.websocket_connect(f"/ws?token={valid_token}") as websocket:
        # Send message
        websocket.send_json({
            "type": "ping",
            "data": {}
        })
        
        # Receive response
        response = websocket.receive_json()
        assert response["type"] == "pong"
```

### Load Testing

```python
# tests/websocket/load_test.py
import asyncio
import websockets

async def stress_test_client(client_id: int, url: str):
    """Stress test client"""
    async with websockets.connect(url) as websocket:
        for i in range(100):
            await websocket.send(json.dumps({
                "type": "ping",
                "data": {"client_id": client_id, "message": i}
            }))
            
            response = await websocket.recv()
            # Validate response
            
            await asyncio.sleep(0.1)

async def run_load_test():
    """Run load test with multiple clients"""
    url = "ws://localhost:8000/ws?token=test_token"
    
    tasks = [
        stress_test_client(i, url)
        for i in range(100)  # 100 concurrent clients
    ]
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_load_test())
```

## Troubleshooting

### Common Issues

#### Connection Drops

**Symptoms**: WebSocket connections dropping unexpectedly

**Causes & Solutions**:
1. **Timeout**: Increase proxy timeout settings
2. **Memory**: Check server memory usage
3. **Network**: Verify network stability
4. **Rate Limiting**: Check if client is exceeding limits

#### Message Loss

**Symptoms**: Messages not being delivered

**Causes & Solutions**:
1. **Queue Overflow**: Increase message queue size
2. **Serialization**: Check for serialization errors
3. **Connection State**: Verify connection is active

#### High Latency

**Symptoms**: Slow message delivery

**Causes & Solutions**:
1. **Server Load**: Scale horizontally
2. **Message Size**: Compress large messages
3. **Network**: Use CDN or edge servers

### Debugging Tools

```python
# app/debug/websocket_debug.py
class WebSocketDebugger:
    """Debug WebSocket connections"""
    
    @staticmethod
    def log_message(direction: str, connection_id: str, message: Dict):
        """Log WebSocket message"""
        logger.debug(f"WS {direction} [{connection_id}]: {json.dumps(message)}")
    
    @staticmethod
    def get_connection_stats(manager: WebSocketManager) -> Dict:
        """Get connection statistics"""
        return {
            "total_connections": manager.get_connection_count(),
            "users_connected": len(manager.user_connections),
            "connections_by_user": {
                user_id: len(conns)
                for user_id, conns in manager.user_connections.items()
            }
        }
    
    @staticmethod
    async def health_check(websocket_url: str) -> bool:
        """Check WebSocket health"""
        try:
            async with websockets.connect(websocket_url) as ws:
                await ws.send(json.dumps({"type": "ping"}))
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                return data.get("type") == "pong"
        except:
            return False
```

### Monitoring

```python
# app/monitoring/websocket_metrics.py
from prometheus_client import Counter, Gauge, Histogram

# Metrics
ws_connections = Gauge('websocket_connections', 'Active WebSocket connections')
ws_messages_sent = Counter('websocket_messages_sent', 'Total messages sent')
ws_messages_received = Counter('websocket_messages_received', 'Total messages received')
ws_message_latency = Histogram('websocket_message_latency', 'Message processing latency')
ws_errors = Counter('websocket_errors', 'WebSocket errors', ['error_type'])

class WebSocketMetrics:
    """Track WebSocket metrics"""
    
    @staticmethod
    def record_connection(action: str):
        """Record connection event"""
        if action == "connect":
            ws_connections.inc()
        elif action == "disconnect":
            ws_connections.dec()
    
    @staticmethod
    def record_message(direction: str):
        """Record message"""
        if direction == "sent":
            ws_messages_sent.inc()
        elif direction == "received":
            ws_messages_received.inc()
    
    @staticmethod
    def record_latency(duration: float):
        """Record message processing latency"""
        ws_message_latency.observe(duration)
    
    @staticmethod
    def record_error(error_type: str):
        """Record error"""
        ws_errors.labels(error_type=error_type).inc()
```