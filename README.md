# Netra Apex AI Optimization Platform

> **Status:** Active Development Beta | **Current Version:** 1.0.0 | **SSOT Architecture Compliance:** 98.7%

Netra Apex is a comprehensive AI optimization platform designed to capture value from customer AI spend through multi-agent AI collaboration. The platform delivers intelligent AI infrastructure optimization, real-time chat-based agent interactions, and advanced analytics to help organizations optimize their AI operations.

**🎯 Golden Path Priority:** User login → AI responses (90% of platform value delivered through chat)

## 🏗️ Architecture Overview

Netra Apex follows a microservice architecture with SSOT (Single Source of Truth) compliance:

- **Backend Service** (`netra_backend/`) - Core API, WebSocket handling, and agent orchestration
- **Authentication Service** (`auth_service/`) - JWT-based authentication and session management  
- **Frontend** (`frontend/`) - Next.js React application with real-time WebSocket integration
- **Shared Libraries** (`shared/`) - Common utilities and SSOT configurations

### Core Infrastructure
- **3-Tier Data Persistence:** Redis (hot cache) → PostgreSQL (warm storage) → ClickHouse (analytics)
- **Real-time Communication:** WebSocket-based agent progress tracking and transparency
- **Multi-User Isolation:** Factory-based execution contexts ensuring complete user separation

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (Backend services)
- **Node.js 18+** (Frontend - current: Next.js 14.2.18)
- **Docker & Docker Compose** (Development environment)
- **PostgreSQL 15+** (Primary database)
- **Redis 7+** (Caching and session storage)
- **ClickHouse 25.7+** (Analytics database)

### Development Setup

1. **Clone and Environment Setup**
   ```bash
   git clone <repository-url>
   cd netra-apex
   # Configure environment variables based on your target environment
   ```

2. **Backend Dependencies**
   ```bash
   # Install Python dependencies (see requirements.txt for complete list)
   pip install -r requirements.txt
   
   # Run database migrations
   python -m alembic upgrade head
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev  # Starts on http://localhost:3000
   ```

4. **Docker Development Environment (Recommended)**
   ```bash
   # Start all services with health checks
   docker-compose -f docker/docker-compose.alpine-dev.yml up -d
   
   # Verify services are healthy
   docker-compose ps
   ```

5. **Testing Infrastructure**
   ```bash
   # Quick system validation
   python3 tests/unified_test_runner.py --execution-mode development --category smoke
   
   # Full development test suite
   python3 tests/unified_test_runner.py --execution-mode development --real-services
   ```

### Testing & Validation

The project uses a comprehensive SSOT (Single Source of Truth) testing framework with 21 test categories:

```bash
# Quick smoke tests (1 minute)
python3 tests/unified_test_runner.py --execution-mode development --category smoke

# Mission-critical business functionality (8 minutes)
python3 tests/unified_test_runner.py --execution-mode development --category mission_critical

# Golden path user flow validation (15 minutes)
python3 tests/unified_test_runner.py --execution-mode development --category golden_path_e2e --real-services

# Integration tests with real services (10 minutes)
python3 tests/unified_test_runner.py --execution-mode development --category integration --real-services

# List all available test categories
python3 tests/unified_test_runner.py --list-categories
```

**Frontend Testing:**
```bash
cd frontend
npm run test:unit           # Unit tests
npm run test:integration    # Integration tests with mocked services
npm run test:real           # Tests with real backend services
npm run test:cypress        # E2E tests with Cypress
```

## 🎯 Core Features

### 🤖 Multi-Agent AI System
The platform's primary value delivery mechanism through intelligent agent collaboration:

- **Supervisor Agent** - Central orchestration coordinating sub-agent workflows
- **Data Helper Agent** - Analyzes data requirements and availability for optimization
- **Triage Agent** - Intelligent request routing with data sufficiency evaluation  
- **APEX Optimizer Agent** - AI infrastructure cost and performance optimization
- **Factory-Based Isolation** - Complete separation of user execution contexts

### 💬 Real-time Chat Interface (90% of Platform Value)
Delivers substantive AI interactions through transparent, progressive agent execution:

- **WebSocket Events** - Five critical events for user transparency:
  - `agent_started` - User sees AI engagement begins
  - `agent_thinking` - Real-time reasoning updates  
  - `tool_executing` - Tool usage transparency
  - `tool_completed` - Tool results delivery
  - `agent_completed` - Final response ready
- **Multi-User Support** - Concurrent isolated user sessions
- **Progress Tracking** - Real-time agent workflow visibility

### 📊 Advanced Analytics & Performance
- **3-Tier Persistence** - Redis (hot) → PostgreSQL (warm) → ClickHouse (analytics)
- **Cost Optimization** - AI infrastructure spend analysis and recommendations
- **Usage Analytics** - Platform adoption and effectiveness metrics
- **Custom Dashboards** - Configurable business intelligence views

### 🔐 Enterprise Authentication & Security
- **JWT-Based Authentication** - Secure token-based user validation
- **OAuth Integration** - Third-party authentication provider support
- **Session Management** - Redis-backed secure session handling
- **AuthTicketManager** - Advanced authentication ticket system with secure token generation

## 🔧 Configuration & Environment Management

The platform uses SSOT-compliant environment management through `IsolatedEnvironment`:

### Environment Configurations
- **Development:** `.env` (local development)
- **Testing:** `.env.test.local` (test environment) 
- **Staging:** `.env.staging.tests` (staging environment)
- **Production:** GCP Secret Manager with secure secret loading

### Critical Configuration Areas
- **Database Connections** - PostgreSQL, Redis, ClickHouse with SSL and VPC connector support
- **Authentication** - JWT_SECRET_KEY, OAuth credentials, session management
- **Service Endpoints** - CORS settings, WebSocket endpoints, load balancer configuration
- **Feature Flags** - Demo mode, optimization settings, WebSocket authentication

### Staging Domain Configuration (Current)
**CRITICAL:** Always use current staging domains:
- **Backend/Auth:** https://staging.netrasystems.ai
- **Frontend:** https://staging.netrasystems.ai  
- **WebSocket:** wss://api-staging.netrasystems.ai

❌ **DEPRECATED:** *.staging.netrasystems.ai URLs (SSL certificate failures)

## 🚀 Deployment

### Google Cloud Platform (Primary)

The platform deploys to GCP with Cloud Run, VPC connectors, and load balancers:

```bash
# Deploy to staging with local build
python3 scripts/deploy_to_gcp.py --project netra-staging --build-local

# Deploy with comprehensive health checks
python3 scripts/deploy_to_gcp.py --project netra-staging --run-checks

# Production deployment (requires approval)
python3 scripts/deploy_to_gcp.py --project netra-production --run-checks
```

### Infrastructure Requirements
- **VPC Connector** - `staging-connector` with all-traffic egress for database access
- **SSL Certificates** - Valid for `*.netrasystems.ai` domains
- **Load Balancer** - Health checks configured for extended startup times (600s database timeout)
- **Secret Manager** - Secure credential management with service account validation

### Deployment Validation
```bash
# Pre-deployment system audit
python3 scripts/pre_deployment_audit.py

# Post-deployment validation
python3 tests/unified_test_runner.py --execution-mode development --category post_deployment
```

## 🧪 Development Guidelines

### SSOT Architecture Standards (98.7% Compliance)
- **SSOT Compliance** - Mandatory Single Source of Truth patterns across all modules
- **Absolute Imports Only** - No relative imports anywhere in the codebase
- **Service Independence** - Complete isolation between microservices
- **Factory Pattern** - User execution contexts for multi-user isolation

### Testing Philosophy
- **Real Services First** - No mocks in integration/E2E tests (use real databases, services)
- **Mission-Critical Coverage** - 21 test categories protecting $500K+ ARR functionality
- **WebSocket Event Validation** - All 5 critical events must be tested and delivered
- **Golden Path Testing** - Complete user journey validation (login → AI responses)

### Key Development Commands

```bash
# SSOT architecture compliance audit (target: >87.5%)
python3 scripts/check_architecture_compliance.py

# String literals validation (prevent config drift)
python3 scripts/query_string_literals.py validate "your_string"

# Mission-critical WebSocket events validation
python3 tests/mission_critical/test_websocket_agent_events_suite.py

# Complete system health check
python3 scripts/pre_deployment_audit.py
```

### Development Priorities
1. **Golden Path First** - User login → AI responses (90% of business value)
2. **SSOT Compliance** - Maintain architectural integrity
3. **Real Testing** - Validate with actual services, not mocks
4. **Business Value Focus** - Every feature must serve customer AI optimization needs

## 📊 System Health & Monitoring

### Real-time Health Monitoring
- **Service Health Endpoints** - `/health` on all services (backend:8000, auth:8081, frontend:3000)
- **WebSocket Event Monitor** - Real-time connection health and event delivery tracking
- **3-Tier Database Health** - PostgreSQL/Redis/ClickHouse connectivity validation
- **SSOT Architecture Compliance** - Currently at 98.7% (target: >87.5%)

### Current System Status
**Golden Path Status:** ✅ Architecturally Ready | ❌ Requires Infrastructure Fixes

Key metrics tracked:
- **Mission-Critical Tests** - 21 categories protecting core functionality
- **WebSocket Events** - 5 critical events delivery validation
- **Multi-User Isolation** - Factory-based execution context integrity
- **Authentication Flow** - JWT/OAuth integration health

### Monitoring Commands
```bash
# Check current system health
python3 tests/unified_test_runner.py --execution-mode development --category smoke

# Monitor WebSocket events
python3 tests/mission_critical/test_websocket_agent_events_suite.py

# Architecture compliance audit
python3 scripts/check_architecture_compliance.py
```

## 🤝 Contributing

**Active Development Beta** - Focus on mission-critical functionality and SSOT compliance.

### Contribution Priorities
1. **Golden Path First** - User login → AI responses (90% of platform value)
2. **SSOT Compliance** - Maintain 98.7% architecture compliance (no SSOT violations)
3. **Real Service Testing** - Use actual databases/services, no mocks in integration tests
4. **Business Value Focus** - Features must serve customer AI optimization needs

### Development Workflow
```bash
# Before making changes - check system health
python3 tests/unified_test_runner.py --execution-mode development --category smoke

# After changes - validate SSOT compliance
python3 scripts/check_architecture_compliance.py

# Before commit - run mission-critical tests
python3 tests/unified_test_runner.py --execution-mode development --category mission_critical
```

### Key Requirements
- All changes must pass mission-critical test suite
- WebSocket events must deliver all 5 critical events
- No new SSOT violations introduced
- Factory pattern isolation maintained for multi-user scenarios

## 📚 Documentation & Resources

### Core Documentation
- **Golden Path Flow** - `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md` - Complete user journey analysis
- **System Status** - `reports/MASTER_WIP_STATUS.md` - Current system health and issues
- **Architecture Guide** - `CLAUDE.md` - Comprehensive development rules and patterns
- **Test Execution** - `reports/TEST_EXECUTION_GUIDE.md` - Complete testing methodology

### API & Development
- **Runtime API Docs** - Available at service health endpoints
- **SSOT Import Registry** - `docs/SSOT_IMPORT_REGISTRY.md` - Authoritative import reference
- **Definition of Done** - `reports/DEFINITION_OF_DONE_CHECKLIST.md` - Module completion checklists

## 🔍 Troubleshooting

### Common Issues & Solutions

**WebSocket Connection Failures:**
- Verify staging domains: `wss://api-staging.netrasystems.ai` (not *.staging.netrasystems.ai)
- Check VPC connector and load balancer configuration
- Validate all 5 WebSocket events are being sent

**Authentication Issues:**
- Use `JWT_SECRET_KEY` (not `JWT_SECRET`) 
- Verify OAuth ports: 3000, 8000, 8001, 8081
- Check AuthTicketManager configuration

**Database Connectivity:**
- Ensure VPC connector configured for Cloud Run
- Validate PostgreSQL/Redis/ClickHouse endpoints
- Check 600s timeout configuration

**Test Infrastructure:**
- Use `python3 tests/unified_test_runner.py --real-services` for accurate testing
- Never use mocks in integration/E2E tests
- Validate mission-critical tests pass

## 📞 Support & Contact

**Development Support:**
- **Primary Documentation** - Check `docs/` and `reports/` directories first
- **System Issues** - Review `reports/MASTER_WIP_STATUS.md` for known issues
- **GitHub Issues** - For bug reports and feature requests (follow GitHub style guide)

**Business Contact:**
- **Email** - dev@netrasystems.ai
- **Focus** - AI infrastructure optimization for enterprise customers

---

**Netra Apex** - Capturing value from customer AI spend through multi-agent collaboration  
**Version:** 1.0.0 | **SSOT Compliance:** 98.7% | **Golden Path:** User login → AI responses