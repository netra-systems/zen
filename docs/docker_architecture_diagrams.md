# Docker Architecture and Deployment Diagrams

## Docker Build and Caching Process

```mermaid
graph TB
    subgraph "Multi-Stage Build"
        A[Dockerfile]
        A --> B[Builder Stage<br/>Alpine 3.19]
        B --> B1[Build Deps<br/>gcc, musl-dev]
        B1 --> B2[requirements.txt<br/>CACHE HIT]
        B2 --> B3[pip install<br/>~520MB]
        B3 --> B4[Clean cache]
        
        B4 --> C[Prod Stage<br/>Alpine 3.19]
        C --> C1[Runtime Deps<br/>libpq, curl]
        C1 --> C2[Create User]
        C2 --> C3[Copy Packages]
        C3 --> C4[Copy App Code<br/>LAST for cache]
        C4 --> D[Final Image<br/>~843MB]
    end
```

## Docker Cache Layers

```mermaid
graph TB
    E[Base Image<br/>ALWAYS CACHED]
    E --> F[System Deps<br/>CACHED if unchanged]
    F --> G[requirements.txt<br/>CACHED if unchanged]
    G --> H[pip install<br/>CACHED if unchanged]
    H --> I[App Code<br/>REBUILDS on change]
    
    style E fill:#9f9
    style F fill:#9f9
    style G fill:#9f9
    style H fill:#afa
    style I fill:#faa
```

## Service Dependencies and Startup

```mermaid
graph TB
    PG[PostgreSQL]
    REDIS[Redis]
    CH[ClickHouse]
    MIG[Migration<br/>One-shot]
    
    PG -->|healthy| MIG
    REDIS -->|healthy| AUTH
    CH -->|started| BACK
    
    MIG -->|completed| BACK
    PG -->|healthy| AUTH
    
    AUTH[Auth<br/>503MB]
    BACK[Backend<br/>843MB]
    
    REDIS -->|healthy| BACK
    
    AUTH -->|healthy| FRONT
    BACK -->|healthy| FRONT
    
    FRONT[Frontend<br/>754MB]
    
    style MIG fill:#f9f
    style PG fill:#9f9
    style REDIS fill:#9f9
```

## GCP Deployment Pipeline

```mermaid
graph TB
    subgraph "Local"
        DEV[Developer]
        DEV --> BUILD[Build]
        BUILD --> TEST[Test]
    end
    
    TEST --> CI[CI/CD]
    
    subgraph "GitHub Actions"
        CI --> VAL[Validate]
        VAL --> BLD[Build All]
        BLD --> TST[Test Suite]
    end
    
    TST --> DPL[deploy_to_gcp.py]
    
    subgraph "GCP"
        DPL --> AR[Artifact<br/>Registry]
        AR --> CR1[Backend<br/>Cloud Run]
        AR --> CR2[Auth<br/>Cloud Run]
        AR --> CR3[Frontend<br/>Cloud Run]
        AR --> MJ[Migration<br/>Cloud Job]
    end
    
    subgraph "Managed"
        SQL[Cloud SQL]
        MEM[Redis]
        BQ[BigQuery]
    end
    
    MJ -->|migrates| SQL
    CR1 --> SQL
    CR1 --> MEM
    CR1 --> BQ
    CR2 --> SQL
    CR2 --> MEM
```

## Deployment Stages

```mermaid
graph TB
    S1[Build & Push Images]
    S1 --> S2[Run Migration Job]
    S2 --> S3[Deploy Services]
    
    subgraph S3[Deploy Services]
        S3A[Auth Service]
        S3B[Backend Service]
        S3C[Frontend Service]
    end
    
    S3 --> S4[Health Checks]
    S4 --> S5[Deployment Complete]
    
    style S2 fill:#f9f
    style S4 fill:#9f9
    style S5 fill:#9f9
```

## Container Size Breakdown

```mermaid
pie title "Backend Container (843MB)"
    "Python Packages" : 520
    "Application Code" : 48
    "Base Alpine" : 50
    "Shared Libs" : 5
    "System Deps" : 20
    "Other" : 200
```

```mermaid
pie title "Python Packages (520MB)"
    "pandas" : 78
    "numpy+libs" : 78
    "langchain" : 50
    "Google AI" : 30
    "faker" : 23
    "sqlalchemy" : 22
    "OpenAI" : 30
    "Other" : 209
```

## Build Timeline

```mermaid
gantt
    title Docker Optimization
    dateFormat HH:mm
    axisFormat %H:%M
    
    section Analysis
    Size Issue      :done, a1, 00:00, 10m
    Check Layers    :done, a2, after a1, 15m
    Check Packages  :done, a3, after a2, 10m
    
    section Optimize
    Remove SPEC     :done, o1, after a3, 5m
    Remove Deps     :done, o2, after o1, 5m
    Migration Svc   :done, o3, after o2, 10m
    Clean Cache     :done, o4, after o3, 5m
    
    section Validate
    Rebuild         :done, v1, after o4, 15m
    Verify Size     :done, v2, after v1, 5m
    Test            :active, v3, after v2, 10m
```

## SSOT Docker Architecture

```mermaid
graph TB
    B1[backend.alpine]
    A1[auth.alpine]
    F1[frontend.alpine]
    M1[migration.alpine]
    
    B1 --> B2[backend.staging]
    A1 --> A2[auth.staging]
    F1 --> F2[frontend.staging]
    
    B2 --> C3[staging.yml]
    A2 --> C3
    F2 --> C3
    
    B1 --> C1[alpine-test.yml]
    A1 --> C1
    F1 --> C1
    M1 --> C1
    
    R1[requirements.txt]
    R2[migration-reqs.txt]
    R3[auth-reqs.txt]
    R4[package.json]
    
    R1 --> B1
    R2 --> M1
    R3 --> A1
    R4 --> F1
    
    style M1 fill:#f96
    style B1 fill:#69f
    style A1 fill:#69f
    style F1 fill:#69f
```

## Key Insights

### Layer Caching Strategy
Place most stable components (base image, system deps) first, volatile code last

### Multi-Stage Builds
Separate build dependencies from runtime to reduce final image size

### Service Separation
Migration as separate service reduces complexity and size

### Dependency Order
Critical for startup - migrations must complete before backend starts

### Size Reality
500-900MB is normal for AI/ML Python containers with required libraries

## Quick Reference

| Service | Size | Main Contributors | Optimization |
|---------|------|-------------------|--------------|
| Backend | 843MB | Python packages (520MB), App code (48MB) | Limited - packages required |
| Frontend | 754MB | Node modules, Next.js build | Limited - production build |
| Auth | 503MB | Python packages, Auth logic | Limited - security libs required |
| Migration | ~250MB | Minimal Python + Alembic | Already optimized |

## Optimization Results

### Before Optimization
- Backend: 905MB (included SPEC, alembic, unnecessary build deps)
- Frontend: 754MB (unchanged - already optimized)
- Auth: 503MB (minimal changes)

### After Optimization
- Backend: 843MB (62MB reduction)
- Frontend: 754MB (unchanged)
- Auth: 503MB (unchanged)
- Migration: 250MB (new separate service)

### What Was Removed
- SPEC folder: 47.7MB (documentation not needed at runtime)
- Alembic migrations: Moved to separate service
- Build dependencies: rust, cargo, make, g++ (unnecessary)
- Test directories and cache files

### What Cannot Be Reduced
- pandas: 78MB (required for data processing)
- numpy: 78MB (required by pandas and ML)
- langchain: 50MB (AI orchestration)
- faker: 23MB (synthetic data generation)
- Google/OpenAI SDKs: 60MB+ (AI capabilities)

## Build Time Visualizations

### Build Time Comparison

```mermaid
graph TB
    subgraph "First Build - 120s"
        A1[Base Image<br/>2.5s]
        A1 --> A2[System Deps<br/>8.3s]
        A2 --> A3[Pip Install<br/>61.3s]
        A3 --> A4[Copy & Export<br/>25s]
    end
```

```mermaid
graph TB
    subgraph "Cached Build - 2s"
        B1[Check Cache<br/>0.1s]
        B1 --> B2[Verify Layers<br/>0.1s]
        B2 --> B3[Export Image<br/>1.8s]
    end
```

```mermaid
graph TB
    subgraph "Code Change - Variable"
        C1[Cached Layers<br/>0s]
        C1 --> C2[Copy Code<br/>0.3s]
        C2 --> C3[Clean Files<br/>0.2s]
        C3 --> C4[Export<br/>2-20s varies]
    end
```

### Build Time Visual Comparison

```mermaid
graph TB
    subgraph "Time Scale (seconds)"
        T0[0s]
        T30[30s]
        T60[60s]
        T90[90s]
        T120[120s]
    end
    
    subgraph "Build Scenarios"
        F[First: 120s total]
        C[Cached: 2s total]
        CO[Code Change: 2-25s]
        R[Req Change: 85s total]
    end
    
    style F fill:#f99
    style C fill:#9f9
    style CO fill:#ff9
    style R fill:#f9f
```

### Layer Build Times

```mermaid
pie title "First Build Time Distribution (120s)"
    "Pip Install" : 61
    "Export Image" : 20
    "System Deps" : 8
    "Copy Packages" : 5
    "Base Image" : 3
    "Other" : 23
```

## Why Builds Can Be 2 Seconds Even With Code Changes

### The Export Time Variable

The key difference between a 2-second and 25-second build with code changes is **export complexity**:

```mermaid
graph TB
    subgraph "2-Second Build"
        S1[Small Change<br/>1 file]
        S1 --> S2[Layer Diff<br/>100KB]
        S2 --> S3[Quick Export<br/>0.1s]
        S3 --> S4[Total: 2s]
    end
    
    subgraph "25-Second Build"
        L1[Large Change<br/>100 files]
        L1 --> L2[Layer Diff<br/>10MB]
        L2 --> L3[Compression<br/>15s]
        L3 --> L4[Total: 25s]
    end
```

### Factors Affecting Export Time

| Factor | Impact on Export | Time Difference |
|--------|-----------------|-----------------|
| Number of changed files | High | 1 file: 0.1s, 100 files: 15s |
| Size of changes | High | 1KB: instant, 10MB: 10-20s |
| Layer compression | Medium | Small layers skip compression |
| Disk I/O speed | Medium | SSD: fast, HDD: slow |
| Docker daemon load | Low | Busy: +5s, Idle: normal |

### Real Examples

```bash
# Scenario 1: Fix typo in one file (2 seconds)
echo "# Fix typo" >> app/main.py
docker build .
#9 [stage-1 7/8] COPY netra_backend /app/netra_backend
#9 DONE 0.1s  <-- Tiny diff
#10 exporting to image
#10 DONE 0.1s  <-- Almost instant
Total: 2 seconds

# Scenario 2: Refactor multiple modules (25 seconds)
# Changed 50+ files across app/
docker build .
#9 [stage-1 7/8] COPY netra_backend /app/netra_backend
#9 DONE 0.3s  <-- Same copy time
#10 exporting to image
#10 compressing layer... 12.1s  <-- Compression needed!
#10 DONE 20.5s
Total: 25 seconds
```

## Docker Build Caching Examples

### First Build (No Cache) - ~120 seconds total
```bash
#1 [internal] load build definition from backend.alpine.Dockerfile
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.11-alpine3.19
#2 DONE 0.8s

#3 [builder 1/5] FROM python:3.11-alpine3.19
#3 resolve 0.0s done
#3 sha256:abc123... 3.4MB / 3.4MB 2.1s done
#3 extracting sha256:abc123... 0.4s done
#3 DONE 2.5s

#4 [builder 2/5] RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev
#4 0.312 fetch https://dl-cdn.alpinelinux.org/alpine/v3.19/main/x86_64/APKINDEX.tar.gz
#4 1.105 Installing gcc (13.2.1) musl-dev (1.2.4) libffi-dev (3.4.4) postgresql-dev (15.3)
#4 DONE 8.3s

#5 [builder 3/5] COPY requirements.txt .
#5 DONE 0.1s

#6 [builder 4/5] RUN pip install --no-cache-dir --user -r requirements.txt
#6 1.2 Collecting pandas==2.3.2
#6 2.4 Downloading pandas-2.3.2.tar.gz (5.2 MB)
#6 8.1 Collecting numpy==2.3.2
#6 9.3 Downloading numpy-2.3.2.tar.gz (18.4 MB)
... [150+ packages installing]
#6 DONE 61.3s  <-- SLOWEST LAYER

#7 [stage-1 3/8] RUN apk add --no-cache libpq curl tini
#7 DONE 2.1s

#8 [stage-1 5/8] COPY --from=builder /root/.local /home/netra/.local
#8 DONE 5.2s  <-- 520MB of Python packages

#9 [stage-1 7/8] COPY netra_backend /app/netra_backend
#9 DONE 0.3s

#10 exporting to image
#10 exporting layers 14.3s done
#10 naming to netra-alpine-test-backend:latest done
#10 DONE 19.5s

Total: ~120 seconds
```

### Second Build (With Cache, No Code Changes) - ~2 seconds
```bash
#1 [internal] load build definition from backend.alpine.Dockerfile
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.11-alpine3.19
#2 DONE 0.0s

#3 [internal] load .dockerignore
#3 DONE 0.0s

#4 [builder 1/5] FROM python:3.11-alpine3.19
#4 CACHED

#5 [builder 2/5] RUN apk add --no-cache gcc musl-dev libffi-dev postgresql-dev
#5 CACHED

#6 [builder 3/5] COPY requirements.txt .
#6 CACHED

#7 [builder 4/5] RUN pip install --no-cache-dir --user -r requirements.txt
#7 CACHED  <-- 61 seconds saved!

#8 [stage-1 2/8] RUN apk add --no-cache libpq curl tini
#8 CACHED

#9 [stage-1 5/8] COPY --from=builder /root/.local /home/netra/.local
#9 CACHED  <-- 520MB copy cached!

#10 [stage-1 7/8] COPY netra_backend /app/netra_backend
#10 CACHED

#11 exporting to image
#11 exporting layers done
#11 writing image sha256:4d3cad5313d3 done
#11 DONE 0.1s

Total: ~2 seconds (all cached)
```

### Third Build (Code Change Only) - ~25 seconds
```bash
#1-8 [Same as above, all CACHED]

#9 [stage-1 7/8] COPY netra_backend /app/netra_backend
#9 DONE 0.3s  <-- Only this rebuilds!

#10 [stage-1 8/8] RUN find /app -type d -name '__pycache__' -exec rm -rf {} +
#10 DONE 0.2s

#11 exporting to image
#11 exporting layers 4.1s done
#11 DONE 4.5s

Total: ~25 seconds (mostly export time)
```

### Fourth Build (Requirements Change) - ~85 seconds
```bash
#1-5 [Same as above, CACHED until requirements.txt]

#6 [builder 3/5] COPY requirements.txt .
#6 DONE 0.1s  <-- File changed, invalidates cache

#7 [builder 4/5] RUN pip install --no-cache-dir --user -r requirements.txt
#7 1.1 Collecting NEW_PACKAGE==1.0.0  <-- Must reinstall ALL packages
#7 2.3 Downloading NEW_PACKAGE-1.0.0.tar.gz
... [All 150+ packages reinstalling]
#7 DONE 58.2s  <-- Almost as slow as first build

#8-11 [Remaining layers must rebuild]
Total: ~85 seconds
```

## Cache Invalidation Rules

### What Invalidates Cache

| Change | Layers Invalidated | Rebuild Time |
|--------|-------------------|--------------|
| Dockerfile instruction | All layers from change onward | Full rebuild from change |
| requirements.txt | pip install + all following | ~85 seconds |
| Application code | Only code copy + cleanup | ~25 seconds |
| Base image update | Everything | ~120 seconds |
| Build args change | Layers using those args | Varies |

### Layer Timing Expectations

| Layer | First Build | Cached | Invalidated |
|-------|------------|--------|-------------|
| Base image pull | 2-5s | 0s | 2-5s |
| System deps (apk) | 5-10s | 0s | 5-10s |
| Copy requirements | 0.1s | 0s | 0.1s |
| pip install | 45-75s | 0s | 45-75s |
| Copy Python packages | 3-6s | 0s | 3-6s |
| Copy app code | 0.2-0.5s | 0s | 0.2-0.5s |
| Export image | 15-25s | 0.1s | 15-25s |

### Optimization Tips

#### Maximize Cache Hits
- Order Dockerfile from least to most frequently changing
- Separate requirements into base + app specific
- Use specific version tags for base images
- Group related RUN commands

#### Speed Up Rebuilds
```dockerfile
# Good: Separate rarely-changing deps
COPY requirements-base.txt .
RUN pip install -r requirements-base.txt
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bad: Everything in one file
COPY requirements.txt .
RUN pip install -r requirements.txt
```

#### Monitor Cache Usage
```bash
# See which layers are cached
docker build --progress=plain .

# Force specific layer rebuild
docker build --no-cache-filter stage-1 .

# Check cache size
docker system df
```

## Docker Commands Reference

### Build with no cache
```bash
docker-compose -f docker-compose.alpine-test.yml build --no-cache
```

### Build with cache debugging
```bash
DOCKER_BUILDKIT=1 docker build --progress=plain -f docker/backend.alpine.Dockerfile .
```

### Check container size breakdown
```bash
docker run --rm <image> du -sh /app/* | sort -rh
docker run --rm <image> du -sh /home/netra/.local/lib/python3.11/site-packages/* | sort -rh | head -20
```

### Analyze image layers
```bash
docker history <image> --no-trunc
docker inspect <image> | jq '.[0].RootFS.Layers' # See layer SHAs
```

### Clean up Docker resources
```bash
docker system prune -a --volumes
docker builder prune --all  # Clear build cache
```