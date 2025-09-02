# Netra Core - Generation 1

## 🏗️ Architecture Overview

### 📚 Key Architecture Documents

- **[User Context Architecture](./USER_CONTEXT_ARCHITECTURE.md)** - **CRITICAL**: Complete guide to the new Factory-based user isolation architecture with execution engines and WebSocket event emitters
- [WebSocket Modernization Report](./WEBSOCKET_MODERNIZATION_REPORT.md) - Details of WebSocket isolation implementation
- [Tool Dispatcher Migration Guide](./TOOL_DISPATCHER_MIGRATION_GUIDE.md) - Migration from singleton to request-scoped tool dispatchers

## 🎯 Core System Design

The Netra Core system implements a **Factory-based, request-scoped architecture** that ensures complete user isolation and eliminates shared state issues. See the **[User Context Architecture](./USER_CONTEXT_ARCHITECTURE.md)** for detailed diagrams and explanations.

### Key Components

#### 1. Execution Factory Pattern
- `ExecutionEngineFactory` - Creates per-request execution engines
- `WebSocketBridgeFactory` - Creates per-user WebSocket emitters  
- `ToolExecutorFactory` - Creates isolated tool dispatchers

#### 2. User Isolation
- `UserExecutionContext` - Complete request isolation
- `IsolatedExecutionEngine` - Per-request execution with no shared state
- `UserWebSocketEmitter` - User-specific event delivery

#### 3. Resource Management
- Per-user semaphores (max 5 concurrent executions)
- Memory thresholds (1024MB limit)
- Automatic cleanup and lifecycle management

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis (for caching)

### Installation

```bash
# Clone the repository
git clone https://github.com/netra/netra-core-generation-1.git
cd netra-core-generation-1

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python netra_backend/manage.py migrate

# Start the application
docker-compose up
```

## 📖 Documentation

### Architecture & Design
- **[User Context Architecture](./USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns and user isolation (START HERE)
- [Agent System Architecture](./docs/AGENT_SYSTEM_ARCHITECTURE.md) - Agent execution pipeline
- [Agent Architecture Diagrams](./docs/agent_architecture_mermaid.md) - Visual architecture guides

### Migration Guides
- [Tool Dispatcher Migration](./TOOL_DISPATCHER_MIGRATION_GUIDE.md) - Migrate from singleton to request-scoped
- [WebSocket Modernization](./WEBSOCKET_MODERNIZATION_REPORT.md) - WebSocket isolation patterns

### Critical Reports
- [Critical Security Implementation](./CRITICAL_SECURITY_IMPLEMENTATION_SUMMARY.md)
- [Phase 0 Completion Report](./PHASE_0_COMPLETION_REPORT.md)

## 🏛️ System Architecture

The system follows a multi-tier architecture with complete user isolation:

```
┌─────────────────┐
│   Frontend UI   │
├─────────────────┤
│   API Gateway   │
├─────────────────┤
│ Factory Layer   │ ← Creates isolated instances per request
├─────────────────┤
│ Execution Layer │ ← User-specific execution contexts
├─────────────────┤
│ Infrastructure  │ ← Shared, immutable resources
└─────────────────┘
```

For detailed architecture diagrams and explanations, see **[User Context Architecture](./USER_CONTEXT_ARCHITECTURE.md)**.

## 🔒 Security

The system implements multiple security boundaries:

1. **Request Isolation** - Each request gets its own execution context
2. **User Isolation** - Complete separation between concurrent users
3. **Resource Limits** - Per-user semaphores and memory limits
4. **Permission Layers** - Tool execution permission checking
5. **Secure Cleanup** - Automatic resource cleanup on request completion

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run security tests
pytest tests/security

# Run all tests with coverage
pytest --cov=netra_backend --cov-report=html
```

## 📊 Monitoring

The system provides comprehensive metrics:

- **ExecutionEngineFactory Metrics** - Engine creation, active count, cleanup stats
- **UserExecutionContext Metrics** - Per-request execution tracking
- **WebSocketBridge Metrics** - Event delivery and connection health

Access metrics endpoint: `GET /api/metrics`

## 🤝 Contributing

Please read our contributing guidelines before submitting PRs.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all tests pass
5. Submit a pull request

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all functions
- Document all public APIs
- Write comprehensive tests

## 📚 Additional Resources

- [API Documentation](./docs/api/README.md)
- [Agent System Guide](./docs/agents/AGENT_SYSTEM.md)
- [WebSocket Events](./docs/websocket/events.md)
- [Database Schema](./docs/database/schema.md)

## 📝 License

This project is proprietary and confidential.

## 🆘 Support

For questions or issues:
- Check the **[User Context Architecture](./USER_CONTEXT_ARCHITECTURE.md)** first
- Review existing issues on GitHub
- Contact the development team

---

**⚠️ IMPORTANT**: Always refer to the **[User Context Architecture](./USER_CONTEXT_ARCHITECTURE.md)** when working with the execution engine, WebSocket events, or tool dispatchers. This document is the authoritative guide for the system's isolation and factory patterns.