# Netra AI Platform - Comprehensive Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Environment Variables Configuration](#environment-variables-configuration)
4. [Local Development Setup](#local-development-setup)
5. [Docker Deployment](#docker-deployment)
6. [GCP Production Deployment](#gcp-production-deployment)
7. [Post-Deployment Configuration](#post-deployment-configuration)
8. [Monitoring & Health Checks](#monitoring--health-checks)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Rollback Procedures](#rollback-procedures)
11. [Scaling Guidelines](#scaling-guidelines)
12. [Security Hardening](#security-hardening)
13. [Backup & Recovery](#backup--recovery)
14. [Cost Optimization](#cost-optimization)

---

## Overview

The Netra AI Optimization Platform is a multi-agent system designed for optimizing AI workloads. This guide provides comprehensive instructions for deploying the platform from local development to production on Google Cloud Platform.

### Architecture Components
- **Backend**: FastAPI application with WebSocket support
- **Frontend**: Next.js application with real-time updates
- **Databases**: PostgreSQL (primary), ClickHouse (analytics), Redis (caching)
- **Agent System**: Supervisor + 5 specialized sub-agents
- **Infrastructure**: Cloud Run, Cloud SQL, Secret Manager

### Deployment Environments
| Environment | Purpose | Cost Estimate |
|------------|---------|---------------|
| **Local** | Development & testing | $0 |
| **Staging** | Pre-production testing | ~$100/month |
| **Production** | Live system | ~$200-1000/month |

---

## Pre-Deployment Checklist

### Required Tools Installation

```bash
# 1. Python 3.11+
python --version  # Should be 3.11 or higher

# 2. Node.js 18+
node --version    # Should be 18.x or higher

# 3. Docker
docker --version  # Should be 20.x or higher

# 4. Google Cloud SDK
gcloud --version  # Latest version

# 5. Terraform
terraform --version  # Should be 1.0 or higher

# 6. PostgreSQL Client
psql --version    # For database operations

# 7. Redis (optional for local)
redis-cli --version

# 8. Git
git --version
```

### Account Requirements

- [ ] Google Cloud Platform account with billing enabled
- [ ] GitHub account (for CI/CD)
- [ ] Domain name (optional)
- [ ] SSL certificates (auto-generated)

### API Keys Required

```bash
# Create a .env file for local development
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://postgres:123@localhost:5432/netra
CLICKHOUSE_URL=clickhouse://default:password@localhost:9000/netra
REDIS_URL=redis://localhost:6379/0

# Authentication & Security
JWT_SECRET_KEY=your-super-secret-jwt-key-min-64-chars-$(openssl rand -hex 32)
SECRET_KEY=your-app-secret-key-$(openssl rand -hex 32)
FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# OAuth Configuration (Google)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# AI Model API Keys
GEMINI_API_KEY=your-gemini-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key  # Optional

# Observability (Optional)
LANGFUSE_SECRET_KEY=your-langfuse-secret
LANGFUSE_PUBLIC_KEY=your-langfuse-public

# Environment Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
MAX_CONNECTIONS=100

# WebSocket Configuration
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_TIMEOUT=300
WEBSOCKET_MAX_CONNECTIONS=1000

# Agent System Configuration
AGENT_MAX_EXECUTION_TIME=600
AGENT_HEARTBEAT_INTERVAL=60
AGENT_MAX_CONCURRENT_OPERATIONS=10
AGENT_TOOL_TIMEOUT=120
SUPERVISOR_ORCHESTRATION_TIMEOUT=300

# Database Pool Configuration
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true

# Session Management
SESSION_TIMEOUT=7200
SESSION_REFRESH_THRESHOLD=1800
SESSION_CLEANUP_INTERVAL=3600
REDIS_SESSION_PREFIX=netra:session:

# Frontend Environment Variables
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=$(openssl rand -hex 32)
EOF
```

---

## Environment Variables Configuration

### Backend Environment Variables

```bash
# Required Environment Variables
DATABASE_URL                 # PostgreSQL connection string
REDIS_URL                    # Redis connection string (optional in dev)
JWT_SECRET_KEY               # JWT signing key (min 64 chars)
SECRET_KEY                   # Application secret key
ENVIRONMENT                  # development/staging/production

# Optional but Recommended
CLICKHOUSE_URL               # ClickHouse connection (for analytics)
FERNET_KEY                   # Encryption key for secrets
LOG_LEVEL                    # DEBUG/INFO/WARNING/ERROR
CORS_ORIGINS                 # Comma-separated allowed origins
MAX_CONNECTIONS              # Database max connections

# OAuth Configuration
GOOGLE_CLIENT_ID             # Google OAuth client ID
GOOGLE_CLIENT_SECRET         # Google OAuth client secret

# AI Model API Keys
GEMINI_API_KEY              # Google Gemini API key
ANTHROPIC_API_KEY           # Anthropic Claude API key
OPENAI_API_KEY              # OpenAI API key (optional)

# Observability
LANGFUSE_SECRET_KEY         # Langfuse secret key
LANGFUSE_PUBLIC_KEY         # Langfuse public key

# WebSocket Settings
WEBSOCKET_HEARTBEAT_INTERVAL  # Default: 30 seconds
WEBSOCKET_TIMEOUT             # Default: 300 seconds
WEBSOCKET_MAX_CONNECTIONS     # Default: 1000

# Agent Configuration
AGENT_MAX_EXECUTION_TIME      # Default: 600 seconds
AGENT_MAX_CONCURRENT_OPS      # Default: 10
SUPERVISOR_TIMEOUT            # Default: 300 seconds
```

### Frontend Environment Variables

```bash
# Required
NEXT_PUBLIC_API_URL          # Backend API URL
NEXT_PUBLIC_WS_URL           # WebSocket URL
NEXT_PUBLIC_ENVIRONMENT      # Environment name

# Authentication
NEXTAUTH_URL                 # NextAuth base URL
NEXTAUTH_SECRET              # NextAuth secret key

# Optional
NEXT_PUBLIC_GOOGLE_CLIENT_ID # Google OAuth client ID
NEXT_PUBLIC_ENABLE_ANALYTICS # Enable analytics (true/false)
```

---

## Local Development Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/netra-core-generation-1.git
cd netra-core-generation-1/v2
```

### Step 2: Backend Setup

```bash
# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup PostgreSQL database
psql -U postgres -c "CREATE DATABASE netra;"

# Run database migrations
alembic upgrade head

# Create initial admin user (optional)
python scripts/create_admin.py --email admin@netra.ai --password secure-password

# Start backend server
uvicorn app.main:app --reload --port 8000
```

### Step 3: Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build the application
npm run build

# Start development server
npm run dev
```

### Step 4: Start Supporting Services

```bash
# Start PostgreSQL (if not running)
# Windows: Use PostgreSQL service
# Mac: brew services start postgresql
# Linux: sudo systemctl start postgresql

# Start Redis (optional for development)
redis-server

# Start ClickHouse (optional for analytics)
docker run -d -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server
```

### Step 5: Verify Local Setup

```bash
# Test backend health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000

# Test WebSocket connection
wscat -c ws://localhost:8000/ws
```

---

## Docker Deployment

### Step 1: Build Docker Images

```bash
# Build backend image
docker build -f Dockerfile.backend -t netra-backend:latest .

# Build frontend image
cd frontend
docker build -f Dockerfile -t netra-frontend:latest .
cd ..
```

### Step 2: Create Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: netra
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secure-password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  backend:
    image: netra-backend:latest
    environment:
      DATABASE_URL: postgresql://postgres:secure-password@postgres:5432/netra
      REDIS_URL: redis://redis:6379
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: docker
    ports:
      - "8000:8080"
    depends_on:
      - postgres
      - redis

  frontend:
    image: netra-frontend:latest
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8080
      NEXT_PUBLIC_WS_URL: ws://backend:8080
    ports:
      - "3000:8080"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

### Step 3: Start Docker Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## GCP Production Deployment

### Step 1: Initial GCP Setup

```bash
# Set project variables
export PROJECT_ID="netra-production"
export REGION="us-central1"
export ZONE="us-central1-a"

# Create new project (if needed)
gcloud projects create $PROJECT_ID --name="Netra AI Platform"

# Set active project
gcloud config set project $PROJECT_ID

# Enable billing
gcloud alpha billing accounts list
gcloud alpha billing projects link $PROJECT_ID \
  --billing-account=YOUR_BILLING_ACCOUNT_ID

# Enable required APIs
gcloud services enable \
  compute.googleapis.com \
  container.googleapis.com \
  sqladmin.googleapis.com \
  cloudrun.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  redis.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

### Step 2: Terraform Infrastructure Setup

```bash
# Navigate to terraform directory
cd terraform-gcp

# Create terraform.tfvars from example
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your configuration
cat > terraform.tfvars << EOF
project_id = "${PROJECT_ID}"
region     = "${REGION}"
zone       = "${ZONE}"

# Environment
environment = "production"

# Database settings (adjust for production needs)
db_tier      = "db-custom-2-7680"  # 2 vCPU, 7.5GB RAM
db_disk_size = 50                  # 50GB SSD

# Backend settings
backend_cpu           = "2"        # 2 vCPU
backend_memory        = "4Gi"      # 4GB RAM
backend_min_instances = 1          # Minimum instances
backend_max_instances = 10         # Maximum instances

# Frontend settings
frontend_cpu           = "1"       # 1 vCPU
frontend_memory        = "2Gi"     # 2GB RAM
frontend_min_instances = 1         # Minimum instances
frontend_max_instances = 5         # Maximum instances
EOF

# Initialize Terraform
terraform init

# Review infrastructure plan
terraform plan

# Apply infrastructure (creates all GCP resources)
terraform apply -auto-approve

# Save outputs
terraform output -json > deployment-outputs.json
```

### Step 3: Store Secrets in Secret Manager

```bash
# Generate secure secrets
export JWT_SECRET=$(openssl rand -hex 64)
export FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Store in Secret Manager
echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key --data-file=-
echo -n "$FERNET_KEY" | gcloud secrets create fernet-key --data-file=-
echo -n "your-gemini-api-key" | gcloud secrets create gemini-api-key --data-file=-
echo -n "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-
echo -n "your-google-client-id" | gcloud secrets create google-client-id --data-file=-
echo -n "your-google-client-secret" | gcloud secrets create google-client-secret --data-file=-
```

### Step 4: Build and Deploy Containers

```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Get registry URL from Terraform
export REGISTRY=$(terraform output -raw artifact_registry)

# Build and push backend
docker build -f Dockerfile.backend -t ${REGISTRY}/backend:latest .
docker push ${REGISTRY}/backend:latest

# Build and push frontend
cd frontend
docker build -f Dockerfile -t ${REGISTRY}/frontend:latest .
docker push ${REGISTRY}/frontend:latest
cd ..

# Deploy to Cloud Run
gcloud run deploy netra-backend \
  --image ${REGISTRY}/backend:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 2 \
  --memory 4Gi \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "ENVIRONMENT=production,LOG_LEVEL=INFO" \
  --set-secrets "JWT_SECRET_KEY=jwt-secret-key:latest,GEMINI_API_KEY=gemini-api-key:latest"

gcloud run deploy netra-frontend \
  --image ${REGISTRY}/frontend:latest \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 2Gi \
  --min-instances 1 \
  --max-instances 5
```

### Step 5: Database Setup and Migration

```bash
# Get database connection info
export DB_IP=$(terraform output -raw database_ip)
export DB_PASSWORD=$(gcloud secrets versions access latest --secret="netra-db-password")

# Connect to database
gcloud sql connect $(terraform output -raw database_connection_name) --user=netra_user

# In SQL prompt, create initial schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
\q

# Run Alembic migrations
DATABASE_URL="postgresql://netra_user:${DB_PASSWORD}@${DB_IP}:5432/netra" \
  alembic upgrade head

# Create initial admin user
DATABASE_URL="postgresql://netra_user:${DB_PASSWORD}@${DB_IP}:5432/netra" \
  python scripts/create_admin.py --email admin@netra.ai
```

### Step 6: Configure Redis (Production)

```bash
# Create Redis instance
gcloud redis instances create netra-redis \
  --size=1 \
  --region=${REGION} \
  --redis-version=redis_7_0 \
  --display-name="Netra Redis Cache" \
  --tier=basic

# Get Redis host
export REDIS_HOST=$(gcloud redis instances describe netra-redis --region=${REGION} --format="value(host)")

# Update backend with Redis URL
gcloud run services update netra-backend \
  --update-env-vars "REDIS_URL=redis://${REDIS_HOST}:6379" \
  --region ${REGION}
```

### Step 7: Setup ClickHouse (Optional - Analytics)

```bash
# Create Compute Engine instance for ClickHouse
gcloud compute instances create netra-clickhouse \
  --machine-type=e2-standard-4 \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --zone=${ZONE} \
  --tags=clickhouse-server

# SSH into instance and install ClickHouse
gcloud compute ssh netra-clickhouse --zone=${ZONE} --command='
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates dirmngr
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv E0C56BD4
echo "deb https://repo.clickhouse.tech/deb/stable/ main/" | sudo tee /etc/apt/sources.list.d/clickhouse.list
sudo apt-get update
sudo apt-get install -y clickhouse-server clickhouse-client
sudo systemctl enable clickhouse-server
sudo systemctl start clickhouse-server
'

# Create firewall rule
gcloud compute firewall-rules create allow-clickhouse \
  --allow tcp:8123,tcp:9000 \
  --source-ranges 0.0.0.0/0 \
  --target-tags clickhouse-server

# Get ClickHouse IP
export CLICKHOUSE_IP=$(gcloud compute instances describe netra-clickhouse \
  --zone=${ZONE} --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

# Update backend with ClickHouse URL
gcloud run services update netra-backend \
  --update-env-vars "CLICKHOUSE_URL=clickhouse://default:password@${CLICKHOUSE_IP}:9000/netra" \
  --region ${REGION}
```

---

## Post-Deployment Configuration

### Step 1: Configure OAuth

```bash
# 1. Go to Google Cloud Console > APIs & Services > Credentials
# 2. Create OAuth 2.0 Client ID
# 3. Add authorized redirect URIs:

export FRONTEND_URL=$(terraform output -raw frontend_url)
export BACKEND_URL=$(terraform output -raw backend_url)

# Add these redirect URIs:
# - ${FRONTEND_URL}/auth/callback/google
# - ${BACKEND_URL}/api/auth/google/callback
# - http://localhost:3000/auth/callback/google (for development)

# 4. Update secrets with OAuth credentials
echo -n "your-client-id" | gcloud secrets versions add google-client-id --data-file=-
echo -n "your-client-secret" | gcloud secrets versions add google-client-secret --data-file=-
```

### Step 2: Configure Custom Domain (Optional)

```bash
# Create domain mapping
gcloud run domain-mappings create \
  --service netra-frontend \
  --domain app.yourdomain.com \
  --region ${REGION}

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain app.yourdomain.com \
  --region ${REGION}

# Configure DNS at your domain registrar with provided records
```

### Step 3: Setup Monitoring

```bash
# Create monitoring dashboard
cat > monitoring-dashboard.json << 'EOF'
{
  "displayName": "Netra Production Dashboard",
  "gridLayout": {
    "widgets": [
      {
        "title": "Request Rate",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"netra-backend\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }]
        }
      },
      {
        "title": "Error Rate",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_revision\" AND severity=\"ERROR\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_RATE"
                }
              }
            }
          }]
        }
      },
      {
        "title": "Response Time",
        "xyChart": {
          "dataSets": [{
            "timeSeriesQuery": {
              "timeSeriesFilter": {
                "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\"",
                "aggregation": {
                  "alignmentPeriod": "60s",
                  "perSeriesAligner": "ALIGN_PERCENTILE_95"
                }
              }
            }
          }]
        }
      }
    ]
  }
}
EOF

gcloud monitoring dashboards create --config-from-file=monitoring-dashboard.json
```

### Step 4: Setup Alerting

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=$(gcloud beta billing accounts list --format="value(name)" | head -n1) \
  --display-name="Netra Monthly Budget" \
  --budget-amount=1000 \
  --threshold-rule=percent=0.5,basis=current-spend \
  --threshold-rule=percent=0.9,basis=current-spend \
  --threshold-rule=percent=1.0,basis=current-spend

# Create uptime check
gcloud monitoring uptime-checks create netra-health \
  --display-name="Netra Health Check" \
  --resource-type=uptime-url \
  --monitored-resource="{'type':'uptime_url','labels':{'host':'${BACKEND_URL#https://}','project_id':'${PROJECT_ID}'}}" \
  --http-check="{'path':'/health','port':443,'use-ssl':true}" \
  --period=1m
```

---

## Monitoring & Health Checks

### Health Check Endpoints

```bash
# Backend health checks
curl ${BACKEND_URL}/health         # Basic health
curl ${BACKEND_URL}/health/live    # Liveness probe
curl ${BACKEND_URL}/health/ready   # Readiness probe
curl ${BACKEND_URL}/health/startup # Startup probe

# Frontend health check
curl ${FRONTEND_URL}/api/health

# WebSocket health check
wscat -c ${BACKEND_URL/https/wss}/ws -x '{"type":"ping"}'
```

### Monitoring Queries

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend" \
  --limit=50 --format=json

# View error logs
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit=20

# View database connections
gcloud sql operations list --instance=$(terraform output -raw database_connection_name)

# View Redis metrics
gcloud redis instances describe netra-redis --region=${REGION}

# View costs
gcloud billing accounts get-iam-policy $(gcloud beta billing accounts list --format="value(name)")
```

### Performance Metrics

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s ${BACKEND_URL}/health

# Where curl-format.txt contains:
cat > curl-format.txt << 'EOF'
time_namelookup:  %{time_namelookup}s\n
time_connect:  %{time_connect}s\n
time_appconnect:  %{time_appconnect}s\n
time_pretransfer:  %{time_pretransfer}s\n
time_redirect:  %{time_redirect}s\n
time_starttransfer:  %{time_starttransfer}s\n
time_total:  %{time_total}s\n
EOF

# Load test (using Apache Bench)
ab -n 1000 -c 10 ${BACKEND_URL}/health
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Database Connection Issues

```bash
# Check database status
gcloud sql instances describe $(terraform output -raw database_connection_name)

# Test connection
gcloud sql connect $(terraform output -raw database_connection_name) --user=netra_user

# Check authorized networks
gcloud sql instances patch $(terraform output -raw database_connection_name) \
  --authorized-networks=0.0.0.0/0  # WARNING: Only for debugging

# Restart database
gcloud sql instances restart $(terraform output -raw database_connection_name)
```

#### 2. Cloud Run Service Not Starting

```bash
# Check service logs
gcloud run services logs read netra-backend --region=${REGION} --limit=100

# Check service status
gcloud run services describe netra-backend --region=${REGION}

# Update memory/CPU if needed
gcloud run services update netra-backend \
  --memory=8Gi \
  --cpu=4 \
  --region=${REGION}

# Force new deployment
gcloud run deploy netra-backend \
  --image ${REGISTRY}/backend:latest \
  --region ${REGION} \
  --force
```

#### 3. WebSocket Connection Drops

```bash
# Check WebSocket timeout settings
gcloud run services update netra-backend \
  --timeout=3600 \
  --region=${REGION}

# Update Cloud Run to use HTTP/2
gcloud run services update netra-backend \
  --use-http2 \
  --region=${REGION}

# Check ingress settings
gcloud run services update netra-backend \
  --ingress=all \
  --region=${REGION}
```

#### 4. High Memory Usage

```bash
# Check current usage
gcloud run services describe netra-backend --region=${REGION} --format="value(spec.template.spec.containers[0].resources)"

# Scale up resources
gcloud run services update netra-backend \
  --memory=8Gi \
  --cpu=4 \
  --region=${REGION}

# Enable CPU boost during startup
gcloud run services update netra-backend \
  --cpu-boost \
  --region=${REGION}
```

#### 5. Authentication Issues

```bash
# Check OAuth configuration
gcloud secrets versions access latest --secret="google-client-id"
gcloud secrets versions access latest --secret="google-client-secret"

# Verify redirect URIs in Google Console
# Console > APIs & Services > Credentials > OAuth 2.0 Client IDs

# Check JWT secret
gcloud secrets versions access latest --secret="jwt-secret-key"

# Test authentication endpoint
curl -X POST ${BACKEND_URL}/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

#### 6. Redis Connection Issues

```bash
# Check Redis instance
gcloud redis instances describe netra-redis --region=${REGION}

# Get connection info
gcloud redis instances get-auth-string netra-redis --region=${REGION}

# Test connection from Cloud Shell
gcloud redis instances connect netra-redis --region=${REGION}
```

---

## Rollback Procedures

### Quick Rollback (Last Known Good)

```bash
# Rollback Cloud Run to previous revision
gcloud run services update-traffic netra-backend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=${REGION}

gcloud run services update-traffic netra-frontend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=${REGION}
```

### Database Rollback

```bash
# List available backups
gcloud sql backups list --instance=$(terraform output -raw database_connection_name)

# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=$(terraform output -raw database_connection_name)

# Or restore to a point in time
gcloud sql instances restore-backup $(terraform output -raw database_connection_name) \
  --backup-id=BACKUP_ID \
  --restore-point-in-time=2024-01-15T10:00:00Z
```

### Full Infrastructure Rollback

```bash
# Using Terraform state
cd terraform-gcp

# Check state history
terraform state list

# Import previous state
terraform state pull > current.tfstate
# Restore previous state file
cp terraform.tfstate.backup terraform.tfstate

# Reapply previous configuration
terraform apply
```

### Emergency Shutdown

```bash
# Stop all services immediately
gcloud run services update netra-backend --max-instances=0 --region=${REGION}
gcloud run services update netra-frontend --max-instances=0 --region=${REGION}

# Stop database (retains data)
gcloud sql instances patch $(terraform output -raw database_connection_name) \
  --activation-policy=NEVER
```

---

## Scaling Guidelines

### Horizontal Scaling

```bash
# Scale Cloud Run instances
gcloud run services update netra-backend \
  --min-instances=2 \
  --max-instances=20 \
  --region=${REGION}

# Configure autoscaling
gcloud run services update netra-backend \
  --cpu-throttling \
  --max-instances=50 \
  --concurrency=100 \
  --region=${REGION}
```

### Vertical Scaling

```bash
# Scale up resources
gcloud run services update netra-backend \
  --cpu=8 \
  --memory=32Gi \
  --region=${REGION}

# Scale database
gcloud sql instances patch $(terraform output -raw database_connection_name) \
  --tier=db-custom-4-16384  # 4 vCPU, 16GB RAM
```

### Database Connection Pool Scaling

```bash
# Update connection pool settings
gcloud run services update netra-backend \
  --update-env-vars "\
DB_POOL_SIZE=50,\
DB_MAX_OVERFLOW=100,\
DB_POOL_TIMEOUT=30,\
DB_POOL_RECYCLE=3600" \
  --region=${REGION}

# Update PostgreSQL max connections
gcloud sql instances patch $(terraform output -raw database_connection_name) \
  --database-flags=max_connections=200
```

---

## Security Hardening

### 1. Network Security

```bash
# Restrict database access to Cloud Run only
gcloud sql instances patch $(terraform output -raw database_connection_name) \
  --authorized-networks=""  # Remove public access

# Use Cloud SQL Proxy instead
gcloud run services update netra-backend \
  --add-cloudsql-instances=$(terraform output -raw database_connection_name) \
  --region=${REGION}
```

### 2. Secret Rotation

```bash
# Rotate JWT secret
NEW_JWT_SECRET=$(openssl rand -hex 64)
echo -n "$NEW_JWT_SECRET" | gcloud secrets versions add jwt-secret-key --data-file=-

# Rotate database password
NEW_DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users set-password netra_user \
  --instance=$(terraform output -raw database_connection_name) \
  --password="$NEW_DB_PASSWORD"
```

### 3. Enable Cloud Armor (DDoS Protection)

```bash
# Create security policy
gcloud compute security-policies create netra-security-policy \
  --description="Security policy for Netra"

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
  --security-policy=netra-security-policy \
  --expression="origin.region_code == 'CN'" \
  --action=deny-403

# Add DDoS protection
gcloud compute security-policies rules create 2000 \
  --security-policy=netra-security-policy \
  --expression="origin.asn == 13335" \
  --action=throttle \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60
```

### 4. Enable Audit Logging

```bash
# Enable audit logs
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/logging.logWriter"

# Configure log retention
gcloud logging buckets update _Default \
  --location=global \
  --retention-days=30
```

---

## Backup & Recovery

### Automated Backup Setup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
PROJECT_ID=$(gcloud config get-value project)
INSTANCE_NAME=$(gcloud sql instances list --format="value(name)" | grep netra-postgres)
BUCKET_NAME="${PROJECT_ID}-netra-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
gcloud sql backups create \
  --instance=$INSTANCE_NAME \
  --description="Automated backup ${DATE}"

# Export to GCS
gcloud sql export sql $INSTANCE_NAME \
  gs://${BUCKET_NAME}/postgres-${DATE}.sql \
  --database=netra

# Redis backup (if using Memorystore)
gcloud redis instances export \
  gs://${BUCKET_NAME}/redis-${DATE}.rdb \
  netra-redis \
  --region=${REGION}

# Keep only last 30 days of backups
gsutil -m ls -la gs://${BUCKET_NAME}/ | \
  grep -E "postgres-.*\.sql" | \
  sort -k2 | \
  head -n -30 | \
  awk '{print $3}' | \
  xargs -I {} gsutil rm {}

echo "Backup completed: ${DATE}"
EOF

chmod +x backup.sh

# Schedule daily backups using Cloud Scheduler
gcloud scheduler jobs create app-engine daily-backup \
  --schedule="0 2 * * *" \
  --time-zone="UTC" \
  --attempt-deadline="1800s" \
  --http-method=GET \
  --uri="${BACKEND_URL}/api/admin/backup"
```

### Manual Backup

```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=$(terraform output -raw database_connection_name) \
  --description="Manual backup $(date +%Y%m%d_%H%M%S)"

# Export to local file
gcloud sql export sql $(terraform output -raw database_connection_name) \
  gs://${PROJECT_ID}-netra-backups/manual-backup.sql \
  --database=netra

# Download backup
gsutil cp gs://${PROJECT_ID}-netra-backups/manual-backup.sql ./backup.sql
```

### Recovery Procedures

```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=$(terraform output -raw database_connection_name)

# Import from SQL file
gcloud sql import sql $(terraform output -raw database_connection_name) \
  gs://${PROJECT_ID}-netra-backups/backup.sql \
  --database=netra

# Point-in-time recovery
gcloud sql instances restore-backup $(terraform output -raw database_connection_name) \
  --backup-id=BACKUP_ID \
  --restore-point-in-time=2024-01-15T10:00:00Z
```

---

## Cost Optimization

### Current Cost Breakdown

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud Run Backend | 2 vCPU, 4GB RAM | ~$120 |
| Cloud Run Frontend | 1 vCPU, 2GB RAM | ~$40 |
| Cloud SQL | db-custom-2-7680 | ~$80 |
| Redis | 1GB Basic | ~$50 |
| Container Registry | 20GB | ~$8 |
| **Total** | | **~$298/month** |

### Cost Reduction Strategies

```bash
# 1. Use committed use discounts (up to 57% savings)
gcloud compute commitments create netra-commitment \
  --region=${REGION} \
  --resources=vcpu=4,memory=8GB \
  --plan=TWELVE_MONTH

# 2. Enable CPU throttling (only charge when processing)
gcloud run services update netra-backend \
  --cpu-throttling \
  --region=${REGION}

# 3. Schedule scaling for off-hours
# Scale down at night (10 PM)
gcloud scheduler jobs create http scale-down \
  --location=${REGION} \
  --schedule="0 22 * * *" \
  --uri="${BACKEND_URL}/admin/scale" \
  --http-method=POST \
  --message-body='{"min_instances": 0, "max_instances": 1}'

# Scale up in morning (6 AM)
gcloud scheduler jobs create http scale-up \
  --location=${REGION} \
  --schedule="0 6 * * *" \
  --uri="${BACKEND_URL}/admin/scale" \
  --http-method=POST \
  --message-body='{"min_instances": 1, "max_instances": 10}'

# 4. Use Spot VMs for ClickHouse
gcloud compute instances create netra-clickhouse \
  --provisioning-model=SPOT \
  --instance-termination-action=STOP \
  --max-run-duration=24h

# 5. Optimize database tier based on usage
gcloud sql instances patch $(terraform output -raw database_connection_name) \
  --tier=db-f1-micro  # During low usage
  --tier=db-custom-2-7680  # During high usage
```

### Budget Monitoring

```bash
# Set up budget alerts
gcloud billing budgets create \
  --billing-account=$(gcloud beta billing accounts list --format="value(name)") \
  --display-name="Netra Monthly Budget" \
  --budget-amount=500 \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.8 \
  --threshold-rule=percent=1.0

# Check current month spend
gcloud billing accounts get-iam-policy $(gcloud beta billing accounts list --format="value(name)")

# Export billing data to BigQuery for analysis
gcloud billing accounts get-iam-policy $(gcloud beta billing accounts list --format="value(name)")
```

---

## Maintenance Tasks

### Regular Maintenance Schedule

```bash
# Weekly tasks
cat > weekly-maintenance.sh << 'EOF'
#!/bin/bash
# Run every Sunday at 2 AM

# 1. Update container images
gcloud run deploy netra-backend --image ${REGISTRY}/backend:latest --region=${REGION}
gcloud run deploy netra-frontend --image ${REGISTRY}/frontend:latest --region=${REGION}

# 2. Clean up old logs
gcloud logging logs delete projects/${PROJECT_ID}/logs/run.googleapis.com --quiet

# 3. Optimize database
gcloud sql instances patch $(terraform output -raw database_connection_name) \
  --database-flags=autovacuum=on,log_autovacuum_min_duration=0

# 4. Check SSL certificates
gcloud compute ssl-certificates list

# 5. Review security policies
gcloud compute security-policies list
EOF

# Monthly tasks
cat > monthly-maintenance.sh << 'EOF'
#!/bin/bash
# Run on 1st of each month

# 1. Rotate secrets
./rotate-secrets.sh

# 2. Review and optimize costs
gcloud billing accounts get-iam-policy $(gcloud beta billing accounts list --format="value(name)")

# 3. Update dependencies
cd /app && pip list --outdated
cd /app/frontend && npm outdated

# 4. Performance review
gcloud monitoring dashboards list

# 5. Security audit
gcloud projects get-iam-policy ${PROJECT_ID}
EOF
```

---

## Appendix

### A. Environment Variable Reference

```bash
# Complete list of environment variables
# Backend
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
CLICKHOUSE_URL=clickhouse://user:pass@host:9000/dbname
JWT_SECRET_KEY=minimum-64-character-secret-key
SECRET_KEY=application-secret-key
FERNET_KEY=base64-encoded-fernet-key
ENVIRONMENT=development|staging|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
CORS_ORIGINS=comma,separated,origins
MAX_CONNECTIONS=100
GOOGLE_CLIENT_ID=oauth-client-id
GOOGLE_CLIENT_SECRET=oauth-client-secret
GEMINI_API_KEY=gemini-api-key
ANTHROPIC_API_KEY=anthropic-api-key
OPENAI_API_KEY=openai-api-key
LANGFUSE_SECRET_KEY=langfuse-secret
LANGFUSE_PUBLIC_KEY=langfuse-public
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_TIMEOUT=300
WEBSOCKET_MAX_CONNECTIONS=1000
AGENT_MAX_EXECUTION_TIME=600
AGENT_HEARTBEAT_INTERVAL=60
AGENT_MAX_CONCURRENT_OPERATIONS=10
AGENT_TOOL_TIMEOUT=120
SUPERVISOR_ORCHESTRATION_TIMEOUT=300
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
SESSION_TIMEOUT=7200
SESSION_REFRESH_THRESHOLD=1800
SESSION_CLEANUP_INTERVAL=3600
REDIS_SESSION_PREFIX=netra:session:

# Frontend
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_WS_URL=wss://api.example.com
NEXT_PUBLIC_ENVIRONMENT=production
NEXTAUTH_URL=https://app.example.com
NEXTAUTH_SECRET=nextauth-secret-key
NEXT_PUBLIC_GOOGLE_CLIENT_ID=oauth-client-id
NEXT_PUBLIC_ENABLE_ANALYTICS=true
```

### B. Port Configuration

| Service | Development | Docker | Production |
|---------|------------|--------|------------|
| Backend API | 8000 | 8080 | 8080 |
| Frontend | 3000 | 8080 | 8080 |
| PostgreSQL | 5432 | 5432 | 5432 |
| Redis | 6379 | 6379 | 6379 |
| ClickHouse HTTP | 8123 | 8123 | 8123 |
| ClickHouse Native | 9000 | 9000 | 9000 |

### C. Required GCP APIs

```bash
# Minimum required APIs
compute.googleapis.com          # Compute Engine
container.googleapis.com        # Kubernetes Engine
sqladmin.googleapis.com        # Cloud SQL
cloudrun.googleapis.com        # Cloud Run
artifactregistry.googleapis.com # Artifact Registry
secretmanager.googleapis.com   # Secret Manager

# Optional but recommended
redis.googleapis.com           # Memorystore Redis
monitoring.googleapis.com      # Cloud Monitoring
logging.googleapis.com         # Cloud Logging
cloudbilling.googleapis.com    # Billing API
cloudscheduler.googleapis.com  # Cloud Scheduler
```

### D. Useful Commands Reference

```bash
# Docker
docker build -t image:tag .
docker run -p 8000:8000 image:tag
docker-compose up -d
docker-compose logs -f service
docker-compose down -v

# Terraform
terraform init
terraform plan
terraform apply -auto-approve
terraform destroy -auto-approve
terraform output

# Google Cloud
gcloud config set project PROJECT_ID
gcloud services enable SERVICE_NAME
gcloud run deploy SERVICE --image IMAGE
gcloud sql instances list
gcloud secrets list
gcloud logging read "FILTER" --limit=N

# Database
psql -h HOST -U USER -d DATABASE
alembic upgrade head
alembic revision -m "description"

# Testing
pytest tests/
npm test
curl -X GET URL
wscat -c ws://URL
```

---

## Support & Resources

- **Documentation**: https://github.com/your-org/netra-docs
- **Issue Tracker**: https://github.com/your-org/netra/issues
- **GCP Console**: https://console.cloud.google.com
- **Terraform Registry**: https://registry.terraform.io
- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Next.js Docs**: https://nextjs.org/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com

---

**Last Updated**: January 2025
**Version**: 2.0.0
**Maintained By**: Netra DevOps Team