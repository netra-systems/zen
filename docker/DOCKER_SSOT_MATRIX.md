# 🚨 DOCKER SINGLE SOURCE OF TRUTH (SSOT) MATRIX

## CRITICAL: ONE Configuration Per Use Case - NO ALTERNATIVES

This document defines the EXACT Docker configuration to use for each scenario. 
**NO FALLBACKS. NO ALTERNATIVES. NO "IF THIS FAILS, TRY THAT" LOGIC.**

---

## THE MATRIX: Use Cases and Their EXACT Configurations

| Use Case | Environment | Dockerfile | Compose File | Command | Port Range |
|----------|-------------|------------|--------------|---------|------------|
| **LOCAL DEVELOPMENT** | DEV | `docker/backend.Dockerfile`<br>`docker/auth.Dockerfile`<br>`docker/frontend.Dockerfile` | `docker-compose.yml` | `docker-compose up` | 5432, 6379, 8000, 8081 |
| **AUTOMATED TESTING** | TEST | `docker/backend.alpine.Dockerfile`<br>`docker/auth.alpine.Dockerfile`<br>`docker/frontend.alpine.Dockerfile` | `docker-compose.alpine-test.yml` | `docker-compose -f docker-compose.alpine-test.yml up` | 5435, 6381, 8002, 8083 |
| **STAGING DEPLOYMENT** | STAGING | `docker/backend.staging.alpine.Dockerfile`<br>`docker/auth.staging.alpine.Dockerfile`<br>`docker/frontend.staging.alpine.Dockerfile` | *(GCP managed)* | `python scripts/deploy_to_gcp.py --project netra-staging --build-local` | *(GCP managed)* |
| **PRODUCTION** | PROD | `docker/backend.staging.alpine.Dockerfile`<br>`docker/auth.staging.alpine.Dockerfile`<br>`docker/frontend.staging.alpine.Dockerfile` | *(GCP managed)* | `python scripts/deploy_to_gcp.py --project netra-production --build-local` | *(GCP managed)* |

---

## DECISION TREE: "If You Want X, Use EXACTLY Y"

```
Are you developing locally?
├─ YES → Use docker-compose.yml (DEV environment)
└─ NO → Are you running automated tests?
    ├─ YES → Use docker-compose.alpine-test.yml (TEST environment) 
    └─ NO → Are you deploying to staging?
        ├─ YES → Use docker-compose.staging.yml (STAGING environment)
        └─ NO → You're in production (GCP manages containers)
```

---

## EXACT COMMANDS FOR EACH SCENARIO

### Local Development
```bash
# Start development environment
docker-compose up -d

# Stop development environment  
docker-compose down
```

### Automated Testing
```bash
# Start test environment
docker-compose -f docker-compose.alpine-test.yml up -d

# Run tests with containers
python tests/unified_test_runner.py --real-services

# Stop test environment
docker-compose -f docker-compose.alpine-test.yml down
```

### Staging Deployment (GCP)
```bash
# Deploy to staging with Alpine images (default)
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Deploy to staging with regular images (not recommended)
python scripts/deploy_to_gcp.py --project netra-staging --build-local --no-alpine
```

### Production (GCP)
```bash
# Deploy to production with Alpine images (default)
python scripts/deploy_to_gcp.py --project netra-production --build-local

# Deploy to production with regular images (not recommended) 
python scripts/deploy_to_gcp.py --project netra-production --build-local --no-alpine
```

---

## STRICT VALIDATION RULES

### ✅ ALLOWED Behavior
- Use EXACTLY the configuration specified in the matrix
- Hard fail if the required configuration is missing
- Clear error messages explaining which file is missing

### ❌ FORBIDDEN Behavior
- **NO "try X, fallback to Y" logic**
- **NO silent switching between configurations**
- **NO auto-detection of "best" configuration**
- **NO combining multiple compose files**
- **NO environment-based guessing**

---

## ERROR HANDLING: Fail Fast and Clear

When a required configuration is missing, the system MUST:

1. **Hard Fail** immediately
2. **Display exact error** with the missing file path
3. **Show the solution** from this matrix
4. **NEVER silently use a fallback**

### Example Error Message:
```
❌ DOCKER SSOT VIOLATION
Missing required file: docker-compose.alpine-test.yml
Use Case: AUTOMATED TESTING
Solution: Restore docker-compose.alpine-test.yml from the SSOT matrix
See: docker/DOCKER_SSOT_MATRIX.md
```

---

## FILES TO DELETE IMMEDIATELY

The following files violate SSOT principles and create confusion:

### Obsolete Compose Files
- `docker-compose.alpine.yml` (ambiguous - dev or test?)
- `docker-compose.base.yml` (unused abstraction)
- `docker-compose.dev-optimized.yml` (optimization belongs in main)
- `docker-compose.podman.yml` (runtime detection handles this)
- `docker-compose.podman-mac.yml` (runtime detection handles this)  
- `docker-compose.podman-no-dns.yml` (runtime detection handles this)
- `docker-compose.pytest.yml` (use alpine-test.yml)
- `docker-compose.resource-optimized.yml` (optimization belongs in main)
- `docker-compose.test.yml` (use alpine-test.yml)
- `docker-compose.unified.yml` (confusing name)

### Obsolete Dockerfiles
- `docker/analytics.Dockerfile` (unused service)
- `docker/auth.development.Dockerfile` (use auth.Dockerfile)
- `docker/auth.podman.Dockerfile` (runtime detection handles this)
- `docker/auth.test.Dockerfile` (use auth.alpine.Dockerfile)
- `docker/backend.development.Dockerfile` (use backend.Dockerfile)
- `docker/backend.optimized.Dockerfile` (optimization belongs in main)
- `docker/backend.podman.Dockerfile` (runtime detection handles this)
- `docker/backend.podman-optimized.Dockerfile` (runtime detection handles this)
- `docker/backend.test.Dockerfile` (use backend.alpine.Dockerfile)
- `docker/frontend.development.Dockerfile` (use frontend.Dockerfile)
- `docker/frontend.podman.Dockerfile` (runtime detection handles this)
- `docker/frontend.podman-dev.Dockerfile` (runtime detection handles this)
- `docker/frontend.test.Dockerfile` (use frontend.alpine.Dockerfile)
- `docker/load-tester.Dockerfile` (separate testing concern)
- `docker/pytest.collection.Dockerfile` (testing infrastructure)
- `docker/pytest.execution.Dockerfile` (testing infrastructure) 
- `docker/pytest.stress.Dockerfile` (testing infrastructure)
- `docker/test-monitor.Dockerfile` (testing infrastructure)
- `docker/test-seeder.Dockerfile` (testing infrastructure)

### Root-Level Obsolete Files
- `Dockerfile.collection-demo` (demo artifacts)
- `Dockerfile.comparison-test` (demo artifacts)
- `Dockerfile.final-demo` (demo artifacts)
- `Dockerfile.memory-test` (demo artifacts)
- `Dockerfile.pytest-optimized` (demo artifacts)

---

## IMPLEMENTATION CHECKLIST

- [ ] UnifiedDockerManager updated to remove ALL fallback logic
- [ ] Scripts updated to use SSOT configurations only
- [ ] Validation script created (docker_ssot_enforcer.py)
- [ ] Obsolete files deleted
- [ ] Tests updated to use SSOT configurations
- [ ] Documentation updated to reference this matrix

---

## SUCCESS CRITERIA

✅ **One Command, One Result**: `docker-compose up` → Always uses docker-compose.yml  
✅ **Test Command Clarity**: Test runner → Always uses docker-compose.alpine-test.yml  
✅ **Zero Ambiguity**: No developer ever asks "which Docker file should I use?"  
✅ **Predictable Failures**: Missing file = clear error, not silent fallback  
✅ **Fast Resolution**: Error message points directly to this matrix for solution  

---

*This document is the SINGLE SOURCE OF TRUTH for Docker configurations. Any code that deviates from this matrix is a bug.*