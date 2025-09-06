# Netra Core - Generation 1

## 🔄 Recent Changes

### January 2025: UVS Architecture Transition
- **[NEW] Unified Validation System (UVS)** - Streamlined 2-agent triage model with data sufficiency validation
  - See **[UVS Triage Architecture Transition Guide](./docs/UVS_TRIAGE_ARCHITECTURE_TRANSITION.md)** for complete details
  - Data Intelligence Agent (formerly Data Helper) now PRIMARY agent handling 80% of requests
  - Intelligent data sufficiency states: Insufficient → Minimal → Sufficient → Optimal
  - Iterative data gathering until sufficient data achieved for analysis
- **Simplified Agent Hierarchy** - Reduced from 3 triage agents to 1 unified triage agent
- **Enhanced Data Processing** - Automatic data gathering when insufficient data detected

## 📊 Business Context

### Value Proposition
The Netra Core platform delivers AI optimization value across all customer segments by providing:

- **Cost Reduction**: 30-70% reduction in AI/LLM spending through intelligent model routing and optimization
- **Performance Improvement**: 40-60% improvement in response times through caching and batching strategies
- **Scale Enablement**: 10x scalability through efficient resource management
- **Progressive Value Delivery**: Immediate value even with partial data (40-60% optimization possible)

### Customer Segments & Data Handling

| Segment | Data Completeness | Value Delivery Strategy |
|---------|------------------|------------------------|
| **Free** | <40% (Insufficient) | Education + Quick templates + Value demonstration |
| **Early** | 40-79% (Partial) | Immediate wins + Progressive optimization + Data collection |
| **Mid** | 60-85% (Mostly complete) | Phased implementation + Quality preservation |
| **Enterprise** | 80-100% (Sufficient) | Full optimization + Compliance focus + Custom strategies |

### Adaptive Workflow Architecture

The platform implements **adaptive workflows** based on data completeness:

1. **Sufficient Data (≥80%)**: Full optimization workflow with high confidence
2. **Partial Data (40-79%)**: Modified workflow with caveats, immediate value, and progressive enhancement
3. **Insufficient Data (<40%)**: Focus on education, data collection, and value demonstration

See [Orchestration Data Handling Patterns](./ORCHESTRATION_DATA_HANDLING_PATTERNS.md) for comprehensive patterns and examples.
See [Netra Optimization Breakdown](./NETRA_OPTIMIZATION_BREAKDOWN.md) for detailed system optimization architecture (AI-specific vs general).

### Key Business Metrics

- **Conversion Rate**: Users providing data after initial insufficient data scenario
- **Value Delivery Rate**: Successful optimizations despite incomplete data
- **Confidence Accuracy**: Correlation between confidence scores and actual outcomes
- **Time to Value**: <24 hours for initial recommendations, 1-3 weeks for full implementation

## 🏗️ Architecture Overview

-- [Documentation Index](./index.md)

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
- **[UVS Triage Architecture Transition](./docs/UVS_TRIAGE_ARCHITECTURE_TRANSITION.md)** - NEW: Unified Validation System with data sufficiency states
- **[Frontend Architecture Diagrams](./frontend/docs/FRONTEND_ARCHITECTURE_DIAGRAMS.md)** - Complete frontend architecture with loading flows, WebSocket events, and state management
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