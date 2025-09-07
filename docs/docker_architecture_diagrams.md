# Docker Architecture and Deployment Diagrams

## Docker Build and Caching Process

```mermaid
graph TB
    subgraph "Multi-Stage Build Process"
        A[Dockerfile] --> B[Builder Stage<br/>python:3.11-alpine3.19]
        B --> B1[Install Build Dependencies<br/>gcc, musl-dev, libffi, postgresql-dev]
        B1 --> B2[Copy requirements.txt<br/>CACHE HIT if unchanged]
        B2 --> B3[pip install packages<br/>~520MB for backend]
        B3 --> B4[Clean up test/cache dirs]
        
        B4 --> C[Production Stage<br/>python:3.11-alpine3.19]
        C --> C1[Install Runtime Dependencies<br/>libpq, curl, tini]
        C1 --> C2[Create non-root user]
        C2 --> C3[Copy Python packages<br/>from builder]
        C3 --> C4[Copy shared libs]
        C4 --> C5[Copy application code<br/>LAST for cache optimization]
        C5 --> C6[Clean up unnecessary files]
        C6 --> D[Final Image<br/>~843MB for backend]
    end

    subgraph "Docker Cache Layers"
        E[Layer 1: Base Image<br/>ALWAYS CACHED]
        F[Layer 2: System Deps<br/>CACHED if unchanged]
        G[Layer 3: requirements.txt<br/>CACHED if file unchanged]
        H[Layer 4: pip install<br/>CACHED if requirements unchanged]
        I[Layer 5: App Code<br/>REBUILDS on code change]
        
        E --> F --> G --> H --> I
    end

    subgraph "Cache Optimization Strategy"
        J[Most Stable] --> K[Base Image & System]
        K --> L[Python Dependencies]
        L --> M[Shared Libraries]
        M --> N[Application Code]
        N --> O[Most Volatile]
    end
```

## Service Dependencies and Startup Order

```mermaid
graph LR
    subgraph "Infrastructure Services"
        PG[PostgreSQL<br/>Alpine]
        REDIS[Redis<br/>Alpine]
        CH[ClickHouse<br/>Alpine]
    end

    subgraph "Application Services"
        MIG[Migration Service<br/>One-shot container]
        AUTH[Auth Service<br/>~503MB]
        BACK[Backend Service<br/>~843MB]
        FRONT[Frontend Service<br/>~754MB]
    end

    PG -->|healthy| MIG
    MIG -->|completed| BACK
    PG -->|healthy| AUTH
    REDIS -->|healthy| BACK
    REDIS -->|healthy| AUTH
    CH -->|started| BACK
    AUTH -->|healthy| FRONT
    BACK -->|healthy| FRONT

    style MIG fill:#f9f,stroke:#333,stroke-width:2px
    style PG fill:#9f9,stroke:#333,stroke-width:2px
    style REDIS fill:#9f9,stroke:#333,stroke-width:2px
```

## Deployment Process to GCP

```mermaid
graph TB
    subgraph "Local Development"
        DEV[Developer Machine]
        DEV --> BUILD[docker build<br/>Alpine Images]
        BUILD --> TEST[Run Tests<br/>docker-compose.alpine-test.yml]
    end

    subgraph "CI/CD Pipeline"
        TEST --> CI[GitHub Actions]
        CI --> VALIDATE[Validate Dockerfiles]
        VALIDATE --> BUILDCI[Build All Images]
        BUILDCI --> TESTCI[Run Test Suite]
    end

    subgraph "GCP Deployment"
        TESTCI --> DEPLOY[deploy_to_gcp.py]
        DEPLOY --> AR[Artifact Registry<br/>Push Images]
        
        AR --> CR[Cloud Run Services]
        CR --> BACK_CR[Backend Service<br/>2 CPU, 4GB RAM]
        CR --> AUTH_CR[Auth Service<br/>1 CPU, 2GB RAM]
        CR --> FRONT_CR[Frontend Service<br/>1 CPU, 2GB RAM]
        
        AR --> CRJ[Cloud Run Jobs]
        CRJ --> MIG_JOB[Migration Job<br/>Runs on deploy]
        
        subgraph "Managed Services"
            PSQL[Cloud SQL<br/>PostgreSQL]
            MEM[Memorystore<br/>Redis]
            BQ[BigQuery<br/>Analytics]
        end
        
        MIG_JOB -->|migrates| PSQL
        BACK_CR --> PSQL
        BACK_CR --> MEM
        BACK_CR --> BQ
        AUTH_CR --> PSQL
        AUTH_CR --> MEM
    end

    subgraph "Deployment Stages"
        STAGE1[1. Build & Push Images]
        STAGE2[2. Run Migration Job]
        STAGE3[3. Deploy Auth Service]
        STAGE4[4. Deploy Backend Service]
        STAGE5[5. Deploy Frontend Service]
        STAGE6[6. Health Checks]
        
        STAGE1 --> STAGE2 --> STAGE3 --> STAGE4 --> STAGE5 --> STAGE6
    end
```

## Container Size Breakdown

```mermaid
pie title "Backend Container Size Distribution (843MB)"
    "Python Packages" : 520
    "Application Code" : 48
    "Base Alpine Python" : 50
    "Shared Libraries" : 5
    "System Dependencies" : 20
    "Other" : 200
```

```mermaid
pie title "Python Package Size Distribution (520MB)"
    "pandas" : 78
    "numpy + libs" : 78
    "langchain ecosystem" : 50
    "Google AI libs" : 30
    "faker" : 23
    "sqlalchemy" : 22
    "OpenAI/Anthropic" : 30
    "Other packages" : 209
```

## Build Optimization Timeline

```mermaid
gantt
    title Docker Build Optimization Process
    dateFormat HH:mm
    axisFormat %H:%M
    
    section Analysis
    Identify size issue           :done, analysis1, 00:00, 10m
    Investigate container layers  :done, analysis2, after analysis1, 15m
    Check Python packages         :done, analysis3, after analysis2, 10m
    
    section Optimization
    Remove SPEC/alembic          :done, opt1, after analysis3, 5m
    Remove build deps            :done, opt2, after opt1, 5m
    Create migration service     :done, opt3, after opt2, 10m
    Clean cache/test dirs        :done, opt4, after opt3, 5m
    
    section Validation
    Rebuild without cache        :done, val1, after opt4, 15m
    Verify size reduction        :done, val2, after val1, 5m
    Test functionality           :active, val3, after val2, 10m
```

## SSOT Docker Architecture

```mermaid
graph TD
    subgraph "Service Dockerfiles - SSOT"
        B1[backend.alpine.Dockerfile<br/>Default Backend]
        A1[auth.alpine.Dockerfile<br/>Default Auth]
        F1[frontend.alpine.Dockerfile<br/>Default Frontend]
        M1[migration.alpine.Dockerfile<br/>Migration Service]
    end

    subgraph "Environment Variants"
        B1 --> B2[backend.staging.alpine.Dockerfile<br/>Staging Override]
        A1 --> A2[auth.staging.alpine.Dockerfile<br/>Staging Override]
        F1 --> F2[frontend.staging.alpine.Dockerfile<br/>Staging Override]
    end

    subgraph "Compose Files"
        C1[docker-compose.alpine-test.yml<br/>Test Environment]
        C2[docker-compose.alpine.yml<br/>Dev Environment]
        C3[docker-compose.staging.yml<br/>Staging Environment]
    end

    subgraph "Shared Resources"
        R1[requirements.txt<br/>Backend Deps]
        R2[requirements-migration.txt<br/>Migration Deps]
        R3[auth_service/requirements.txt<br/>Auth Deps]
        R4[frontend/package.json<br/>Frontend Deps]
    end

    B1 --> C1
    A1 --> C1
    F1 --> C1
    M1 --> C1

    R1 --> B1
    R2 --> M1
    R3 --> A1
    R4 --> F1

    style M1 fill:#f96,stroke:#333,stroke-width:2px
    style B1 fill:#69f,stroke:#333,stroke-width:2px
    style A1 fill:#69f,stroke:#333,stroke-width:2px
    style F1 fill:#69f,stroke:#333,stroke-width:2px
```

## Key Insights

1. **Layer Caching Strategy**: Place most stable components (base image, system deps) first, volatile code last
2. **Multi-Stage Builds**: Separate build dependencies from runtime to reduce final image size
3. **Service Separation**: Migration as separate service reduces complexity and size
4. **Dependency Order**: Critical for startup - migrations must complete before backend starts
5. **Size Reality**: 500-900MB is normal for AI/ML Python containers with required libraries

## Quick Reference

| Service | Size | Main Contributors | Optimization Potential |
|---------|------|-------------------|----------------------|
| Backend | 843MB | Python packages (520MB), App code (48MB) | Limited - packages required |
| Frontend | 754MB | Node modules, Next.js build | Limited - production build |
| Auth | 503MB | Python packages, Auth logic | Limited - security libs required |
| Migration | ~250MB | Minimal Python + Alembic | Already optimized |