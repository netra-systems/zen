# Netra Apex AI Optimization Platform

> **Status:** Active Development Beta | **Version:** 1.0.0

Netra Apex is a comprehensive AI optimization platform that captures value from customer AI spend through multi-agent AI collaboration. The platform provides intelligent AI infrastructure optimization, chat-based interactions, and advanced analytics.

## 🏗️ Architecture Overview

Netra Apex is built as a microservice architecture with the following core services:

- **Backend Services** (`netra_backend/`) - Core API and agent orchestration
- **Authentication Service** (`auth_service/`) - JWT-based authentication and session management
- **Analytics Service** (`analytics_service/`) - Performance monitoring and optimization insights
- **Frontend** (`frontend/`) - Next.js-based user interface
- **Shared Libraries** (`shared/`) - Common utilities and configurations

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (Backend services)
- **Node.js 16+** (Frontend)
- **Docker & Docker Compose** (Development environment)
- **PostgreSQL** (Primary database)
- **Redis** (Caching and session storage)
- **ClickHouse** (Analytics and metrics)

### Development Setup

1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd netra-apex
   # Configure your environment variables (see .env.local as reference)
   ```

2. **Backend Setup**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt

   # Run database migrations
   python -m alembic upgrade head
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Docker Development Environment**
   ```bash
   # Start all services using Docker configuration
   cd docker
   docker-compose -f docker-compose.alpine-dev.yml up -d

   # Or use the unified test runner for development
   python tests/unified_test_runner.py --real-services
   ```

### Testing

The project uses a comprehensive testing framework with multiple test categories:

```bash
# Run all tests
python tests/unified_test_runner.py

# Run specific test categories
python tests/unified_test_runner.py --category integration
python tests/unified_test_runner.py --category e2e --real-services

# Frontend tests
cd frontend
npm test
npm run test:integration
```

## 🎯 Core Features

### AI Agent System
- **Supervisor Agent** - Central orchestration and workflow management
- **Data Helper Agent** - Data requirements analysis and optimization
- **Triage Agent** - Enhanced request routing with data sufficiency analysis
- **APEX Optimizer Agent** - AI infrastructure optimization

### Real-time Chat Interface
- WebSocket-based real-time communication
- Agent progress tracking and transparency
- Tool execution visibility
- Multi-user isolation and security

### Advanced Analytics
- 3-tier data persistence (Redis → PostgreSQL → ClickHouse)
- Performance monitoring and optimization insights
- Usage analytics and cost optimization
- Custom dashboard configurations

### Authentication & Security
- JWT-based authentication system
- OAuth integration support
- Session management with Redis
- Role-based access control

## 🔧 Configuration

The platform uses environment-specific configuration:

- **Development:** `.env` (local development)
- **Testing:** `.env.test.local` (test environment)
- **Staging:** `.env.staging.tests` (staging environment)
- **Production:** Managed through GCP Secret Manager

Key configuration areas:
- Database connections (PostgreSQL, Redis, ClickHouse)
- JWT secrets and OAuth credentials
- Service endpoints and CORS settings
- Feature flags and optimization settings

## 🚀 Deployment

### Google Cloud Platform (Staging)

```bash
# Deploy to staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Deploy with health checks
python scripts/deploy_to_gcp.py --project netra-staging --run-checks
```

### Production Deployment

Production deployments require additional validation and approval processes. See the deployment documentation in `docs/` for detailed instructions.

## 🧪 Development Guidelines

### Code Quality Standards
- **SSOT (Single Source of Truth)** compliance is mandatory
- Use absolute imports only (no relative imports)
- Follow architectural patterns and naming conventions
- Maintain service independence between microservices

### Testing Requirements
- Real services integration testing (no mocks in E2E tests)
- Comprehensive WebSocket event testing
- Multi-user isolation validation
- Performance and load testing

### Key Development Commands

```bash
# Architecture compliance check
python scripts/check_architecture_compliance.py

# String literals validation
python scripts/query_string_literals.py validate "your_string"

# Test infrastructure validation
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## 📊 System Health Monitoring

Monitor system health through:
- **Health Endpoints:** `/health` on all services
- **WebSocket Event Monitoring:** Real-time connection and event tracking
- **Database Connectivity:** Multi-tier persistence validation
- **Service Integration:** Cross-service communication validation

## 🤝 Contributing

This is an active development beta project. Key contribution guidelines:

1. **Golden Path Priority:** Focus on user login → AI response workflow
2. **SSOT Compliance:** Follow Single Source of Truth patterns
3. **Real Testing:** Use actual services, avoid mocks in integration tests
4. **Business Value Focus:** Prioritize features that serve customer AI optimization needs

## 📚 Documentation

- **Architecture:** `docs/` - Comprehensive system architecture documentation
- **API Documentation:** Available at runtime endpoints
- **Deployment Guides:** `docs/deployment/` - Environment-specific deployment instructions
- **Development Guides:** `CLAUDE.md` - Detailed development guidelines and architecture rules

## 🔍 Troubleshooting

Common issues and solutions:

- **WebSocket Connection Issues:** Check CORS configuration and VPC connector settings
- **Authentication Failures:** Verify JWT_SECRET_KEY configuration and OAuth endpoints
- **Database Connectivity:** Ensure VPC connector is configured for Cloud Run environments
- **Test Failures:** Use `python tests/unified_test_runner.py --real-services` for accurate testing

## 📞 Support

For development support and questions:
- **Email:** dev@netrasystems.ai
- **Documentation:** Check `docs/` directory for detailed guides
- **Issues:** Use GitHub Issues for bug reports and feature requests

---

**Netra Systems** - AI Infrastructure Optimization Platform