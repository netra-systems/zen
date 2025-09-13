# Netra Apex AI Optimization Platform - System Architecture Overview

> **Executive Summary**: Netra Apex is an enterprise AI workload optimization platform that reduces customer AI costs by 30-50% through intelligent multi-agent orchestration, real-time optimization recommendations, and performance-based value capture.

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Business Value & Architecture](#business-value--architecture)
3. [System Overview](#system-overview)
4. [Service Architecture](#service-architecture)
5. [Technology Stack](#technology-stack)
6. [Data Flow & Communication](#data-flow--communication)
7. [Common User Workflows](#common-user-workflows)
8. [Business Value Mapping](#business-value-mapping)
9. [Development & Deployment](#development--deployment)
10. [Monitoring & Observability](#monitoring--observability)

---

## Executive Summary

### What is Netra Apex?

Netra Apex is a sophisticated AI optimization platform designed to analyze and optimize enterprise AI workloads in real-time. The platform uses a multi-agent system to provide intelligent recommendations that reduce AI costs while maintaining or improving performance.

**Key Value Propositions:**
- **Cost Reduction**: 30-50% reduction in AI infrastructure spend
- **Performance Optimization**: 2-3x improvement in processing speed
- **Real-time Intelligence**: Live optimization recommendations via WebSocket streaming
- **Enterprise Security**: OAuth-first authentication with enterprise-grade security
- **Revenue Sharing Model**: 20% of customer savings captured as platform fee

### Business Model
```mermaid
graph TB
    A[Customer AI Spend<br/>$100K/month] --> B[Netra Optimization<br/>30% reduction]
    B --> C[Customer Saves<br/>$30K/month]
    C --> D[Netra Fee<br/>20% of savings = $6K]
    D --> E[Customer Net Benefit<br/>$24K/month]
    
    style A fill:#ffebee
    style B fill:#e8f5e9
    style C fill:#e3f2fd
    style D fill:#fff3e0
    style E fill:#f3e5f5
```

---

## Business Value & Architecture

### Revenue-Driven Design Philosophy

Every component in Netra Apex is designed with business value justification:

| Customer Segment | Monthly AI Spend | Netra Optimization | Customer Savings | Netra Revenue |
|-----------------|------------------|-------------------|------------------|---------------|
| **Free** | < $1K | Basic optimization | Up to $300/month | $0 (conversion focus) |
| **Early** | $1K - $10K | Standard optimization | $300 - $3K/month | $60 - $600/month |
| **Mid** | $10K - $100K | Advanced optimization | $3K - $30K/month | $600 - $6K/month |
| **Enterprise** | > $100K | Full platform + custom | > $30K/month | Negotiated contracts |

### Platform Architecture Principles

```mermaid
graph LR
    A[Business Goals] --> B[Technical Architecture]
    B --> C[Customer Value]
    C --> D[Revenue Capture]
    D --> A
    
    A1[Cost Reduction] --> A
    A2[Performance Gains] --> A
    A3[Developer Productivity] --> A
    
    B1[Multi-Agent System] --> B
    B2[Real-time Processing] --> B
    B3[Scalable Infrastructure] --> B
    
    C1[30-50% Cost Savings] --> C
    C2[2-3x Speed Improvement] --> C
    C3[20 hrs/week Time Saved] --> C
    
    D1[Performance-based Pricing] --> D
    D2[Tier-based Features] --> D
    D3[Enterprise Contracts] --> D
```

---

## System Overview

### High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser<br/>Next.js Frontend]
        MOBILE[Mobile App<br/>Future]
        API[API Clients<br/>Python/JS/Go]
    end
    
    subgraph "Application Services"
        AUTH[Auth Service<br/>FastAPI - OAuth & JWT]
        BACKEND[Main Backend<br/>FastAPI - Business Logic]
        FRONTEND[Frontend Service<br/>Next.js - UI]
    end
    
    subgraph "AI & Processing"
        SUPERVISOR[Supervisor Agent<br/>Orchestration]
        SUBAGENTS[Sub-Agents<br/>5 Specialized Agents]
        TOOLS[Apex Tools<br/>30+ Optimization Tools]
    end
    
    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Primary Data)]
        CLICKHOUSE[(ClickHouse<br/>Analytics)]
        REDIS[(Redis<br/>Cache & Sessions)]
    end
    
    WEB --> FRONTEND
    MOBILE --> BACKEND
    API --> BACKEND
    
    FRONTEND --> AUTH
    FRONTEND --> BACKEND
    
    BACKEND --> SUPERVISOR
    SUPERVISOR --> SUBAGENTS
    SUBAGENTS --> TOOLS
    
    BACKEND --> POSTGRES
    BACKEND --> CLICKHOUSE
    BACKEND --> REDIS
    
    AUTH --> POSTGRES
    
    style AUTH fill:#e1f5fe
    style BACKEND fill:#e8f5e9
    style FRONTEND fill:#fff3e0
    style SUPERVISOR fill:#f3e5f5
    style POSTGRES fill:#ffebee
    style CLICKHOUSE fill:#e0f2f1
    style REDIS fill:#fce4ec
```

### System Characteristics

**🔹 Microservice Architecture**: Three independent services (Frontend, Backend, Auth Service)
**🔹 Multi-Agent Intelligence**: Sophisticated AI agent system with supervisor pattern
**🔹 Real-time Communication**: WebSocket-based streaming for live updates
**🔹 Dual Database Strategy**: PostgreSQL for transactions, ClickHouse for analytics
**🔹 OAuth-First Security**: Enterprise-grade authentication with JWT tokens
**🔹 Cloud-Native Design**: GCP deployment with auto-scaling capabilities

---

## Service Architecture

### Service Overview

| Service | Technology | Port (Dev) | Purpose | Key Features |
|---------|------------|------------|---------|--------------|
| **Frontend** | Next.js 15 | Dynamic | Web UI | React 19, TypeScript, TailwindCSS |
| **Backend** | FastAPI | Dynamic | Business Logic | Multi-agent system, WebSocket, APIs |
| **Auth Service** | FastAPI | Dynamic | Authentication | OAuth 2.0, JWT, Session management |

*Note: All ports are dynamically discovered in development via `.service_discovery/` directory*

### Service Independence

```mermaid
graph TB
    subgraph "Service Boundaries"
        subgraph "Frontend Service"
            F1[Next.js App]
            F2[React Components]
            F3[State Management]
            F4[API Client]
        end
        
        subgraph "Backend Service"
            B1[FastAPI App]
            B2[Agent System]
            B3[Business Logic]
            B4[Database Models]
        end
        
        subgraph "Auth Service"
            A1[FastAPI App]
            A2[OAuth Integration]
            A3[JWT Management]
            A4[User Management]
        end
    end
    
    F4 -.->|HTTP/WebSocket| B1
    F4 -.->|HTTP| A1
    B1 -.->|Token Validation| A1
    
    style Frontend fill:#fff3e0
    style Backend fill:#e8f5e9
    style "Auth Service" fill:#e1f5fe
```

**Key Principle**: Each service is 100% independent with no shared code dependencies, ensuring independent deployment and scaling.

### Multi-Agent System Architecture

```mermaid
graph TB
    subgraph "Agent Orchestration Layer"
        SUPERVISOR[Supervisor Agent<br/>Orchestrates workflow]
    end
    
    subgraph "Specialized Sub-Agents"
        TRIAGE[Triage Agent<br/>Request analysis]
        DATA[Data Agent<br/>Information gathering]
        OPTIMIZATION[Optimization Agent<br/>Core recommendations]
        ACTIONS[Actions Agent<br/>Implementation planning]
        REPORTING[Reporting Agent<br/>Result compilation]
    end
    
    subgraph "Apex Optimizer Tools"
        COST[Cost Analysis Tools<br/>5 tools]
        PERF[Performance Tools<br/>8 tools]
        CACHE[Cache Optimization<br/>7 tools]
        POLICY[Policy Management<br/>6 tools]
        REPORT[Reporting Tools<br/>4 tools]
    end
    
    USER[User Request] --> SUPERVISOR
    SUPERVISOR --> TRIAGE
    TRIAGE --> DATA
    DATA --> OPTIMIZATION
    OPTIMIZATION --> ACTIONS
    ACTIONS --> REPORTING
    
    OPTIMIZATION --> COST
    OPTIMIZATION --> PERF
    OPTIMIZATION --> CACHE
    OPTIMIZATION --> POLICY
    REPORTING --> REPORT
    
    REPORTING --> RESULT[Optimization Report]
    
    style SUPERVISOR fill:#f3e5f5
    style TRIAGE fill:#e8f5e9
    style DATA fill:#e1f5fe
    style OPTIMIZATION fill:#fff3e0
    style ACTIONS fill:#ffebee
    style REPORTING fill:#e0f2f1
```

**Agent Workflow**: Sequential execution with state persistence, error recovery, and real-time progress updates via WebSocket.

---

## Technology Stack

### Comprehensive Technology Overview

```mermaid
graph TB
    subgraph "Frontend Technologies"
        NEXTJS[Next.js 15<br/>React Framework]
        REACT[React 19<br/>UI Components]
        TS[TypeScript 5.0+<br/>Type Safety]
        TAILWIND[TailwindCSS<br/>Styling]
        ZUSTAND[Zustand<br/>State Management]
        SHADCN[shadcn/ui<br/>Component Library]
    end
    
    subgraph "Backend Technologies"
        FASTAPI[FastAPI 0.104+<br/>Async Web Framework]
        PYTHON[Python 3.11+<br/>Primary Language]
        SQLALCHEMY[SQLAlchemy 2.0+<br/>Database ORM]
        PYDANTIC[Pydantic 2.0+<br/>Data Validation]
        AUTHLIB[Authlib 1.2+<br/>OAuth Integration]
        WEBSOCKETS[WebSockets 12.0+<br/>Real-time Communication]
    end
    
    subgraph "Data Technologies"
        POSTGRES[(PostgreSQL<br/>Primary Database)]
        CLICKHOUSE[(ClickHouse<br/>Analytics Database)]
        REDIS[(Redis 7.0+<br/>Cache & Sessions)]
        ALEMBIC[Alembic 1.12+<br/>Database Migrations]
    end
    
    subgraph "Infrastructure Technologies"
        DOCKER[Docker<br/>Containerization]
        GCP[Google Cloud Platform<br/>Cloud Infrastructure]
        TERRAFORM[Terraform<br/>Infrastructure as Code]
        GITHUB[GitHub Actions<br/>CI/CD Pipeline]
    end
    
    NEXTJS --> REACT
    REACT --> TS
    TS --> TAILWIND
    
    FASTAPI --> PYTHON
    PYTHON --> SQLALCHEMY
    SQLALCHEMY --> POSTGRES
    
    FASTAPI --> REDIS
    FASTAPI --> CLICKHOUSE
    
    style NEXTJS fill:#61dafb
    style FASTAPI fill:#009688
    style POSTGRES fill:#336791
    style CLICKHOUSE fill:#ffcc02
    style REDIS fill:#dc382d
    style GCP fill:#4285f4
```

### Technology Choices & Rationale

| Technology | Version | Why Chosen | Business Value |
|------------|---------|------------|----------------|
| **FastAPI** | 0.104+ | Async-first, automatic OpenAPI, high performance | Reduces development time, scales efficiently |
| **Next.js** | 15.0+ | SSR/SSG, excellent DX, React ecosystem | Fast development, SEO-friendly, great UX |
| **PostgreSQL** | 15+ | ACID compliance, rich feature set, reliability | Data integrity, complex queries, enterprise-ready |
| **ClickHouse** | 23+ | Column-oriented, analytics optimized, fast | Real-time analytics, cost optimization insights |
| **Redis** | 7.0+ | In-memory, pub/sub, session management | Low latency, session persistence, caching |
| **TypeScript** | 5.0+ | Type safety, IDE support, error prevention | Reduces bugs, improves maintainability |

---

## Data Flow & Communication

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Auth Service
    participant G as Google OAuth
    participant B as Backend
    
    U->>F: Click Login
    F->>A: Redirect to /auth/oauth
    A->>G: Redirect to Google
    G->>U: Show consent screen
    U->>G: Grant permission
    G->>A: Callback with auth code
    A->>G: Exchange code for tokens
    G->>A: Return user info
    A->>A: Create/update user
    A->>A: Generate JWT token
    A->>F: Redirect with token
    F->>F: Store token in localStorage
    F->>B: API call with Bearer token
    B->>A: Validate token
    A->>B: Return user context
    B->>F: Return API response
```

### Real-time Communication Flow

```mermaid
sequenceDiagram
    participant F as Frontend
    participant B as Backend
    participant S as Supervisor Agent
    participant SA as Sub-Agents
    
    F->>B: WebSocket connection (with JWT)
    B->>B: Authenticate user
    B-->>F: Connection established
    
    F->>B: Send user message
    B->>S: Initialize supervisor
    S->>SA: Execute sub-agents sequentially
    
    loop Agent Execution
        SA->>B: Agent progress update
        B-->>F: Stream update via WebSocket
        F->>F: Update UI in real-time
    end
    
    SA->>S: Final results
    S->>B: Compiled report
    B-->>F: Final response
    F->>F: Display complete results
```

### Data Processing Pipeline

```mermaid
graph LR
    subgraph "Input Processing"
        USER[User Request] --> VALIDATE[Input Validation]
        VALIDATE --> QUEUE[Message Queue]
    end
    
    subgraph "AI Processing"
        QUEUE --> TRIAGE[Triage Analysis]
        TRIAGE --> COLLECT[Data Collection]
        COLLECT --> OPTIMIZE[Optimization Engine]
        OPTIMIZE --> PLAN[Action Planning]
        PLAN --> COMPILE[Report Generation]
    end
    
    subgraph "Output & Storage"
        COMPILE --> STREAM[WebSocket Streaming]
        COMPILE --> STORE[Database Storage]
        STREAM --> DISPLAY[UI Updates]
        STORE --> ANALYTICS[Analytics DB]
    end
    
    style USER fill:#e3f2fd
    style OPTIMIZE fill:#e8f5e9
    style STREAM fill:#fff3e0
    style ANALYTICS fill:#fce4ec
```

---

## Common User Workflows

### Workflow 1: New User Onboarding

```mermaid
graph TD
    A[Visit Platform] --> B[Click Sign Up]
    B --> C[OAuth with Google]
    C --> D[Grant Permissions]
    D --> E[Account Created]
    E --> F[Redirect to Chat]
    F --> G[See Example Prompts]
    G --> H[Try First Optimization]
    H --> I[View Results]
    I --> J[Upgrade Prompt]
    
    style A fill:#e3f2fd
    style E fill:#e8f5e9
    style I fill:#fff3e0
    style J fill:#ffebee
```

**Steps Explained:**
1. **Landing Page**: User discovers platform value proposition
2. **Authentication**: One-click OAuth with Google (no manual registration)
3. **Onboarding**: Guided tour of features and capabilities
4. **First Experience**: Pre-built example prompts for immediate value
5. **Results**: Real-time optimization recommendations
6. **Conversion**: Upgrade path clearly presented

### Workflow 2: AI Workload Optimization

```mermaid
graph TD
    A[Describe AI Workload] --> B[Upload Configuration/Logs]
    B --> C[Triage Agent Analysis]
    C --> D[Data Collection Phase]
    D --> E[Optimization Recommendations]
    E --> F[Cost/Performance Analysis]
    F --> G[Implementation Plan]
    G --> H[Generated Report]
    H --> I[Download/Share Results]
    
    style C fill:#f3e5f5
    style E fill:#e8f5e9
    style F fill:#fff3e0
    style H fill:#e1f5fe
```

**Real-time Updates**: Each phase streams live updates to the user via WebSocket, showing:
- Current agent executing
- Tools being used
- Preliminary findings
- Progress indicators

### Workflow 3: Enterprise Integration

```mermaid
graph TD
    A[API Key Setup] --> B[SDK Integration]
    B --> C[Automated Monitoring]
    C --> D[Threshold Alerts]
    D --> E[Optimization Triggers]
    E --> F[Automated Implementation]
    F --> G[Performance Tracking]
    G --> H[ROI Reporting]
    
    style A fill:#e3f2fd
    style C fill:#e8f5e9
    style E fill:#fff3e0
    style H fill:#ffebee
```

**Enterprise Features**:
- Programmatic API access
- Automated optimization workflows
- Custom thresholds and alerts
- Integration with existing monitoring systems

---

## Business Value Mapping

### Customer Value Creation

```mermaid
graph TB
    subgraph "Customer Pain Points"
        P1[High AI Costs<br/>$100K+/month]
        P2[Performance Issues<br/>Slow responses]
        P3[Complex Optimization<br/>Manual effort]
        P4[Lack of Visibility<br/>Black box spending]
    end
    
    subgraph "Netra Solutions"
        S1[Cost Optimization<br/>30-50% reduction]
        S2[Performance Tuning<br/>2-3x speed boost]
        S3[Automated Analysis<br/>AI-driven insights]
        S4[Real-time Analytics<br/>Transparent reporting]
    end
    
    subgraph "Business Outcomes"
        O1[Reduced OpEx<br/>$30K-50K/month saved]
        O2[Faster Products<br/>Better user experience]
        O3[Team Efficiency<br/>20 hrs/week saved]
        O4[Strategic Decisions<br/>Data-driven choices]
    end
    
    P1 --> S1 --> O1
    P2 --> S2 --> O2
    P3 --> S3 --> O3
    P4 --> S4 --> O4
    
    style P1 fill:#ffebee
    style S1 fill:#e8f5e9
    style O1 fill:#e3f2fd
```

### Revenue Model Deep Dive

| Customer Tier | Monthly AI Spend | Platform Fee Structure | Annual Revenue Potential |
|---------------|------------------|----------------------|------------------------|
| **Free** | $0 - $1K | $0 (conversion focus) | $0 |
| **Early** | $1K - $10K | 20% of savings | $1.4K - $14K |
| **Mid** | $10K - $100K | 20% of savings | $14K - $144K |
| **Enterprise** | $100K+ | Negotiated (15-25%) | $216K+ |

**Key Metrics**:
- **Average Customer Lifetime Value**: $180K (Mid tier)
- **Payback Period**: 3 months average
- **Customer Acquisition Cost**: $2K average
- **Net Revenue Retention**: 120% target

---

## Development & Deployment

### Development Environment

```mermaid
graph TB
    subgraph "Local Development"
        DEV[dev_launcher.py<br/>Orchestrated startup]
        DISCOVERY[Service Discovery<br/>Dynamic ports]
        SERVICES[All Services<br/>Hot reload enabled]
    end
    
    subgraph "Development Database"
        POSTGRES_DEV[(PostgreSQL<br/>Local instance)]
        REDIS_DEV[(Redis<br/>Local instance)]
        CLICKHOUSE_DEV[(ClickHouse<br/>Docker container)]
    end
    
    subgraph "Development Features"
        MOCK_LLM[Mock LLM Mode<br/>Fast testing]
        DEV_AUTH[Dev Login<br/>/auth/dev/login]
        HOT_RELOAD[Hot Reload<br/>All services]
        SEED_DATA[Test Data<br/>Auto-seeded]
    end
    
    DEV --> DISCOVERY
    DISCOVERY --> SERVICES
    SERVICES --> POSTGRES_DEV
    SERVICES --> REDIS_DEV
    SERVICES --> CLICKHOUSE_DEV
    
    style DEV fill:#e8f5e9
    style SERVICES fill:#e1f5fe
    style MOCK_LLM fill:#fff3e0
```

**Quick Start**:
```bash
# One command to start everything
python scripts/dev_launcher.py

# Or use unified test runner
python unified_test_runner.py --category integration --no-coverage --fast-fail
```

### Staging Environment (GCP)

```mermaid
graph TB
    subgraph "Google Cloud Platform"
        LB[Load Balancer<br/>SSL/TLS termination]
        CR_FE[Cloud Run<br/>Frontend]
        CR_BE[Cloud Run<br/>Backend]
        CR_AU[Cloud Run<br/>Auth Service]
    end
    
    subgraph "Managed Services"
        SQL[Cloud SQL<br/>PostgreSQL]
        REDIS_GCP[Memorystore<br/>Redis]
        SM[Secret Manager<br/>Credentials]
    end
    
    subgraph "Domains"
        FE_DOMAIN[staging.netrasystems.ai]
        BE_DOMAIN[api.staging.netrasystems.ai]
        AU_DOMAIN[auth.staging.netrasystems.ai]
    end
    
    LB --> CR_FE
    LB --> CR_BE
    LB --> CR_AU
    
    CR_FE --> FE_DOMAIN
    CR_BE --> BE_DOMAIN
    CR_AU --> AU_DOMAIN
    
    CR_BE --> SQL
    CR_BE --> REDIS_GCP
    CR_AU --> SQL
    
    CR_BE --> SM
    CR_AU --> SM
    
    style LB fill:#4285f4
    style SQL fill:#336791
    style SM fill:#ff5722
```

**Deployment Command**:
```bash
# Deploy to staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Deploy with health checks
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
```

### Environment Configuration

| Environment | Database | Authentication | LLM Mode | SSL |
|-------------|----------|---------------|----------|-----|
| **Development** | Local PostgreSQL | Dev login available | Mock mode available | Not required |
| **Staging** | Cloud SQL (Unix socket) | OAuth required | Real LLMs | Required |
| **Production** | Cloud SQL (Multi-region) | OAuth + 2FA | Real LLMs | Required |

---

## Monitoring & Observability

### Health Monitoring System

```mermaid
graph TB
    subgraph "Health Check Endpoints"
        BASIC[/health<br/>Basic liveness]
        READY[/health/ready<br/>Dependencies check]
        METRICS[/health/metrics<br/>Prometheus metrics]
    end
    
    subgraph "Monitoring Stack"
        PROMETHEUS[Prometheus<br/>Metrics collection]
        GRAFANA[Grafana<br/>Visualization]
        ALERT[Alert Manager<br/>Notifications]
    end
    
    subgraph "Key Metrics"
        SLI[Service Level Indicators<br/>Response time, availability]
        SLO[Service Level Objectives<br/>99.9% uptime target]
        ERROR[Error Budget<br/>0.1% error allowance]
    end
    
    BASIC --> PROMETHEUS
    READY --> PROMETHEUS
    METRICS --> PROMETHEUS
    
    PROMETHEUS --> GRAFANA
    PROMETHEUS --> ALERT
    
    PROMETHEUS --> SLI
    SLI --> SLO
    SLO --> ERROR
    
    style PROMETHEUS fill:#e36c09
    style GRAFANA fill:#f46800
    style SLO fill:#4285f4
```

### Business Metrics Dashboard

```mermaid
graph TB
    subgraph "Customer Metrics"
        CAC[Customer Acquisition Cost<br/>$2K average]
        LTV[Customer Lifetime Value<br/>$180K average]
        CHURN[Churn Rate<br/>5% monthly target]
        NRR[Net Revenue Retention<br/>120% target]
    end
    
    subgraph "Platform Metrics"
        MAU[Monthly Active Users<br/>Growth tracking]
        USAGE[API Usage<br/>By tier analysis]
        COSTS[Infrastructure Costs<br/>Cost optimization]
        SAVINGS[Customer Savings<br/>Value delivered]
    end
    
    subgraph "Financial Metrics"
        MRR[Monthly Recurring Revenue<br/>Growth tracking]
        ARR[Annual Recurring Revenue<br/>Predictability]
        GROSS[Gross Margin<br/>Profitability]
        ROI[Customer ROI<br/>Value demonstration]
    end
    
    CAC --> LTV
    LTV --> MRR
    USAGE --> COSTS
    SAVINGS --> ROI
    
    style CAC fill:#e3f2fd
    style LTV fill:#e8f5e9
    style MRR fill:#fff3e0
    style ROI fill:#f3e5f5
```

### Performance Benchmarks

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **API Response Time** | < 200ms p95 | 150ms p95 | ✅ Meeting |
| **Agent Processing** | < 30s average | 25s average | ✅ Meeting |
| **WebSocket Latency** | < 50ms | 35ms | ✅ Meeting |
| **System Availability** | 99.9% | 99.95% | ✅ Exceeding |
| **Database Query Time** | < 100ms p95 | 80ms p95 | ✅ Meeting |

---

## Troubleshooting & Common Issues

### Common Development Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Port Conflicts** | Services fail to start | Use `python scripts/dev_launcher.py` for automatic port discovery |
| **Database Connection** | Connection refused errors | Ensure PostgreSQL is running and credentials are correct |
| **Import Errors** | ModuleNotFoundError | Use absolute imports: `from netra_backend.app.services import ...` |
| **WebSocket Issues** | Connection drops | Check JWT token in connection headers |

### Staging Deployment Issues

| Issue | Root Cause | Solution |
|-------|------------|----------|
| **503 Errors** | SSL parameter conflicts | Run `resolve_ssl_parameter_conflicts()` |
| **Health Check Fails** | Missing secrets | Verify all secrets in GCP Secret Manager |
| **No Traffic** | Traffic not routed | Run `gcloud run services update-traffic --to-latest` |
| **OAuth Errors** | Wrong redirect URIs | Update OAuth console with correct staging domains |

---

## Getting Started

### For Developers

1. **Clone Repository**: `git clone [repository-url]`
2. **Setup Environment**: `python scripts/dev_launcher.py`
3. **Run Tests**: `python unified_test_runner.py --category integration --fast-fail`
4. **Access Application**: Check `.service_discovery/` for actual ports

### For Product Managers

1. **Review [Business Metrics](business/REVENUE_TRACKING.md)**: Understanding value creation
2. **Check [API Documentation](architecture/API_DOCUMENTATION.md)**: Feature capabilities by tier
3. **Monitor [Dashboards](#business-metrics-dashboard)**: Real-time business metrics

### For DevOps Engineers

1. **Deploy Staging**: `python scripts/deploy_to_gcp.py --project netra-staging --build-local`
2. **Monitor Health**: Check `/health/ready` endpoints
3. **Review Logs**: Use GCP Logging for troubleshooting

---

## Next Steps

### Documentation Deep Dives

- **[Service Interactions](architecture/SERVICE_INTERACTIONS.md)** - Detailed API flows and patterns
- **[Agent System](agents/AGENT_SYSTEM.md)** - Multi-agent architecture deep dive
- **[Database Schema](architecture/DATABASE_SCHEMA.md)** - Data model documentation
- **[Security Architecture](auth/AUTHENTICATION_SECURITY.md)** - Security implementation details

### Related Resources

- **[CLAUDE.md](../CLAUDE.md)** - AI agent development instructions
- **[Cross-System Context](../SPEC/cross_system_context_reference.md)** - Complete system context
- **[Architecture Specs](../SPEC/architecture.xml)** - Technical architecture specifications

---

**Last Updated**: December 2025
**Document Version**: 1.2
**System Status**: Production Ready - All Critical Infrastructure Operational
**Maintained By**: Netra Platform Team

## Current System Metrics (2025-12-09)

- **System Health**: 87% (EXCELLENT)
- **Golden Path Status**: FULLY OPERATIONAL 
- **SSOT Compliance**: 83.3% Real System
- **Mission Critical Tests**: 120+ tests protecting core business value
- **Production Readiness**: CONFIRMED - Ready for deployment
- **Business Value Protection**: $500K+ ARR functionality validated

*This document provides a comprehensive overview of the Netra Apex AI Optimization Platform. For detailed implementation information, refer to the specific documentation linked throughout this document.*