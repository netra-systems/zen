# Staging E2E Configuration Guide

This guide provides comprehensive instructions for configuring the staging environment for E2E test execution. It addresses the critical configuration issues that block E2E tests and provides step-by-step remediation.

## Critical Issues Addressed

### 1. JWT_SECRET_KEY Configuration (KeyError in tests)
- **Issue**: JWT_SECRET_KEY not configured in staging environment
- **Impact**: Authentication failures, WebSocket 403 errors
- **Solution**: Proper secret management with Google Secret Manager

### 2. Redis Connection Configuration (ConnectionRefusedError)
- **Issue**: Redis trying to connect to localhost:6379 instead of staging instance
- **Impact**: Cache failures, session management issues
- **Solution**: Proper VPC connector and Memorystore configuration

### 3. PostgreSQL SSL Configuration Issues
- **Issue**: SSL certificate verification failures
- **Impact**: Database connection failures
- **Solution**: Proper SSL configuration with Cloud SQL

### 4. Test Runner Bugs
- **Issue**: Variable scoping issues in unified test runner
- **Impact**: Test execution failures
- **Solution**: Code fixes and proper error handling

## Prerequisites

### GCP Access Requirements
```bash
# 1. Authenticate with GCP
gcloud auth login

# 2. Set project
gcloud config set project netra-staging

# 3. Required IAM roles:
# - Secret Manager Secret Accessor
# - Cloud SQL Client
# - Redis Client
```

### Required Services
- Google Secret Manager (secrets)
- Cloud SQL (PostgreSQL database)
- Memorystore (Redis cache)
- VPC Connector (private network access)

## Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
# Run the automated staging environment setup
python scripts/setup_staging_environment.py

# This script will:
# - Validate GCP access
# - Setup JWT secrets
# - Configure database connections
# - Configure Redis connections
# - Update environment files
# - Validate connectivity
```

### Option 2: Individual Component Fixes
```bash
# Fix Redis configuration only
python scripts/fix_staging_redis_config.py

# Fix PostgreSQL SSL configuration only
python scripts/fix_staging_postgres_ssl.py
```

### Option 3: Manual Configuration
Follow the detailed manual configuration steps below.

## Detailed Configuration

### 1. JWT Secret Configuration

#### Required Secrets in Google Secret Manager
```bash
# Create JWT secret for staging
gcloud secrets create jwt-secret-staging --project=netra-staging

# Add secret value (32+ character string)
echo "your-secure-jwt-secret-32-characters-minimum" | gcloud secrets versions add jwt-secret-staging --data-file=-
```

#### Environment Variables
```bash
# In .env.staging.tests
JWT_SECRET_KEY=loaded_from_secret_manager
JWT_SECRET_STAGING=loaded_from_secret_manager
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRY_MINUTES=15
JWT_REFRESH_EXPIRY_DAYS=7
```

#### Secret Loading Configuration
```bash
# Enable lenient validation for staging
JWT_SECRET_VALIDATION_MODE=lenient
SECRET_LOADING_MODE=staging
GOOGLE_APPLICATION_CREDENTIALS_MODE=auto_detect
```

### 2. Redis Configuration

#### Memorystore Instance Configuration
- **Instance ID**: `staging-redis`
- **Region**: `us-central1`
- **Private IP**: `10.69.0.4`
- **Port**: `6379`
- **Auth**: Enabled with password

#### Required Secrets
```bash
# Create Redis password secret
gcloud secrets create redis-password-staging --project=netra-staging
echo "your-redis-password" | gcloud secrets versions add redis-password-staging --data-file=-

# Create Redis URL secret
echo "redis://:your-redis-password@10.69.0.4:6379/0" | gcloud secrets versions add redis-url-staging --data-file=-
```

#### Environment Variables
```bash
# In .env.staging.tests
REDIS_HOST=10.69.0.4
REDIS_PORT=6379
REDIS_DB=0
REDIS_MODE=production
REDIS_URL=loaded_from_secret_manager
REDIS_PASSWORD=loaded_from_secret_manager
REDIS_TIMEOUT=600
REDIS_CONNECTION_POOL_SIZE=50
```

### 3. PostgreSQL Configuration

#### Cloud SQL Instance Configuration
- **Instance ID**: `staging-postgres`
- **Region**: `us-central1`
- **Private IP**: `10.69.0.3`
- **Database**: `netra_staging`
- **User**: `postgres`

#### Required Secrets
```bash
# Create database password secret
gcloud secrets create postgres-password-staging --project=netra-staging
echo "your-postgres-password" | gcloud secrets versions add postgres-password-staging --data-file=-

# Create database URL secret
echo "postgresql://postgres:your-postgres-password@10.69.0.3:5432/netra_staging?sslmode=require" | gcloud secrets versions add database-url-staging --data-file=-
```

#### Environment Variables
```bash
# In .env.staging.tests
POSTGRES_HOST=10.69.0.3
POSTGRES_PORT=5432
POSTGRES_DB=netra_staging
POSTGRES_USER=postgres
POSTGRES_PASSWORD=loaded_from_secret_manager
DATABASE_URL=loaded_from_secret_manager

# SSL Configuration
DATABASE_SSL_MODE=require
DATABASE_SSL_CERT=/etc/ssl/certs/ca-certificates.crt
DATABASE_SSL_ROOT_CERT=/etc/ssl/certs/ca-certificates.crt
DATABASE_SSL_VERIFY=false

# Connection Pool Configuration
DATABASE_TIMEOUT=600
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=50
DATABASE_POOL_TIMEOUT=600
```

### 4. VPC Connector Configuration

#### Terraform Configuration
```hcl
# In terraform-gcp-staging/vpc-connector.tf
resource "google_vpc_access_connector" "staging_connector" {
  name          = "staging-connector"
  project       = "netra-staging"
  region        = "us-central1"
  ip_cidr_range = "10.69.0.0/24"
  
  # Enable access to private services
  subnet {
    name       = "staging-subnet"
    project_id = "netra-staging"
  }
}
```

#### Cloud Run Configuration
```yaml
# Ensure VPC connector is configured for all services
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/vpc-access-connector: staging-connector
        run.googleapis.com/vpc-access-egress: all-traffic
```

## Service URLs Configuration

### Required Service Endpoints
```bash
# In .env.staging.tests
ENVIRONMENT=staging
GCP_PROJECT_ID=netra-staging

# Service URLs - CRITICAL: Use *.netrasystems.ai domains
NETRA_BACKEND_URL=https://staging.netrasystems.ai
AUTH_SERVICE_URL=https://staging.netrasystems.ai
FRONTEND_URL=https://staging.netrasystems.ai
NETRA_API_URL=https://staging.netrasystems.ai
WEBSOCKET_URL=wss://api-staging.netrasystems.ai/api/v1/websocket

# DO NOT USE: *.staging.netrasystems.ai (causes SSL failures)
```

### Load Balancer Configuration
- Backend service mapped to `staging.netrasystems.ai`
- WebSocket service mapped to `api-staging.netrasystems.ai`
- SSL certificates for `*.netrasystems.ai`

## Test Execution

### Environment Setup
```bash
# Load staging environment
export $(grep -v '^#' .env.staging.tests | xargs)

# Verify GCP access
gcloud auth list --filter=status:ACTIVE

# Set GCP project
gcloud config set project netra-staging
```

### Test Execution Commands
```bash
# Run staging E2E tests
python tests/unified_test_runner.py --staging-e2e

# Run specific category in staging
python tests/unified_test_runner.py --category integration --env staging

# Run full staging validation
python tests/unified_test_runner.py --categories unit integration api --env staging --real-services

# Run mission-critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py

# Run with real LLM (for complete E2E validation)
python tests/unified_test_runner.py --category e2e --env staging --real-llm
```

### Docker-Free Testing (Recommended for Staging)
```bash
# Skip Docker for staging tests (use real services)
python tests/unified_test_runner.py --env staging --no-docker --real-services

# Use staging services with bypassed local infrastructure
python tests/unified_test_runner.py --env staging --prefer-staging --no-services
```

## Troubleshooting

### JWT Secret Issues
```bash
# Check JWT secret configuration
python -c "
from shared.jwt_secret_manager import get_unified_jwt_secret, validate_unified_jwt_config
print('JWT Secret Length:', len(get_unified_jwt_secret()))
print('Validation:', validate_unified_jwt_config())
"

# Validate JWT secret in staging
ENVIRONMENT=staging python -c "
from shared.jwt_secret_manager import get_unified_jwt_secret
print('Staging JWT Secret configured:', len(get_unified_jwt_secret()) >= 32)
"
```

### Redis Connection Issues
```bash
# Test Redis connectivity
python -c "
import redis
import os
os.environ['REDIS_HOST'] = '10.69.0.4'
os.environ['REDIS_PORT'] = '6379'
r = redis.Redis(host='10.69.0.4', port=6379, decode_responses=True)
print('Redis ping:', r.ping())
"

# Check VPC connector status
gcloud compute networks vpc-access connectors describe staging-connector --region=us-central1
```

### Database Connection Issues
```bash
# Test database connectivity
python -c "
import psycopg2
conn = psycopg2.connect(
    host='10.69.0.3',
    port=5432,
    database='netra_staging',
    user='postgres',
    password='your-password',
    sslmode='require'
)
print('Database connected:', conn.status == 1)
conn.close()
"

# Check Cloud SQL instance status
gcloud sql instances describe staging-postgres
```

### Secret Manager Access Issues
```bash
# Test secret access
gcloud secrets versions access latest --secret=jwt-secret-staging

# Check IAM permissions
gcloud projects get-iam-policy netra-staging --flatten="bindings[].members" --filter="bindings.members:*YOUR_EMAIL*"
```

### VPC Connector Issues
```bash
# Check VPC connector logs
gcloud logging read "resource.type=vpc_access_connector AND resource.labels.connector_name=staging-connector" --limit=10

# Test private IP connectivity from Cloud Run
# (This requires deploying a test service)
```

## Common Error Messages and Solutions

### Error: `KeyError: 'JWT_SECRET_KEY'`
**Solution**: Run JWT secret setup
```bash
python scripts/setup_staging_environment.py
```

### Error: `ConnectionRefusedError: [Errno 111] Connection refused (localhost:6379)`
**Solution**: Fix Redis configuration
```bash
python scripts/fix_staging_redis_config.py
```

### Error: `psycopg2.OperationalError: SSL connection failed`
**Solution**: Fix PostgreSQL SSL configuration
```bash
python scripts/fix_staging_postgres_ssl.py
```

### Error: `test_results referenced before assignment`
**Solution**: This was fixed in the test runner, run latest version

### Error: `SSL certificate verify failed`
**Solution**: Use proper SSL configuration:
```bash
# In environment config
DATABASE_SSL_VERIFY=false  # For private IP connections
DATABASE_SSL_MODE=require  # Still require SSL encryption
```

## Production Readiness Checklist

### Security
- [ ] JWT secrets properly configured in Secret Manager
- [ ] Database passwords stored in Secret Manager
- [ ] Redis passwords stored in Secret Manager
- [ ] SSL certificates valid for production domains
- [ ] VPC connector properly secured

### Performance
- [ ] Database connection pooling configured
- [ ] Redis connection pooling configured
- [ ] Timeout values appropriate for production load
- [ ] Health check intervals optimized

### Monitoring
- [ ] Application logs forwarded to Cloud Logging
- [ ] Database connection monitoring enabled
- [ ] Redis performance monitoring enabled
- [ ] WebSocket connection monitoring enabled

### Testing
- [ ] All E2E tests pass in staging
- [ ] Mission-critical tests pass
- [ ] WebSocket agent events working
- [ ] Authentication flow validated
- [ ] Database operations validated
- [ ] Cache operations validated

## Business Impact

### Cost of Configuration Issues
- **E2E Test Failures**: Delayed releases, reduced confidence
- **Authentication Issues**: $50K+ MRR at risk from WebSocket failures
- **Database Issues**: Data integrity and user experience problems
- **Cache Issues**: Performance degradation and session problems

### Value of Proper Configuration
- **Reliable Testing**: Confidence in staging environment
- **Production Readiness**: Smooth deployments
- **Issue Prevention**: Catch problems before production
- **Performance Validation**: Verify scalability and reliability

## Support and Resources

### Documentation
- [CLAUDE.md](../CLAUDE.md) - Project instructions and priorities
- [TEST_EXECUTION_GUIDE.md](../TEST_EXECUTION_GUIDE.md) - Comprehensive test execution methodology
- [GOLDEN_PATH_USER_FLOW_COMPLETE.md](GOLDEN_PATH_USER_FLOW_COMPLETE.md) - User journey analysis

### Scripts and Tools
- `scripts/setup_staging_environment.py` - Automated staging setup
- `scripts/fix_staging_redis_config.py` - Redis configuration fix
- `scripts/fix_staging_postgres_ssl.py` - PostgreSQL SSL fix
- `tests/unified_test_runner.py` - Unified test execution

### Contact and Escalation
- For urgent issues blocking E2E tests, escalate immediately
- Document all configuration changes in SSOT files
- Update this guide with new issues and solutions

---

**Last Updated**: 2025-09-17  
**Version**: 1.0  
**Status**: Active - Critical for staging E2E test execution