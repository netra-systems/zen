# GCP Deployment Guide - Budget-Optimized ($1,000/month)

## Quick Deploy (10 minutes)

This guide enables a junior engineer to deploy the Netra AI Platform on Google Cloud Platform within budget constraints of $1,000/month maximum.

## Prerequisites

1. **Install Required Tools** (5 minutes)
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Install Terraform
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Install kubectl
gcloud components install kubectl

# Verify installations
gcloud version
terraform version
kubectl version --client
```

2. **Setup GCP Project**
```bash
# Set your project ID (replace with your actual project)
export PROJECT_ID="netra-production"
export REGION="us-central1"
export ZONE="us-central1-a"

# Create project (if new)
gcloud projects create $PROJECT_ID --name="Netra AI Platform"

# Set project
gcloud config set project $PROJECT_ID

# Enable billing (link your billing account)
gcloud alpha billing accounts list
gcloud alpha billing projects link $PROJECT_ID --billing-account=YOUR_BILLING_ID

# Enable required APIs
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable cloudrun.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│           Cloud Load Balancing                    │
│              ($20/month)                          │
└──────────────────┬──────────────┬─────────────────┘
                   │              │
    ┌──────────────▼────┐  ┌─────▼──────────────┐
    │  Cloud Run        │  │  Cloud Run         │
    │  Frontend         │  │  Backend           │
    │  (Next.js)        │  │  (FastAPI)         │
    │  1-3 instances    │  │  4GB RAM/2CPU      │
    │  ($40/month)      │  │  ($120/month)      │
    └───────────────────┘  └────────────────────┘
                   │              │
                   │    ┌─────────▼──────────┐
                   │    │  WebSocket         │
                   │    │  Connections       │
                   │    │  (Real-time)       │
                   │    └────────────────────┘
                   │              │
    ┌──────────────▼──────────────▼─────────────┐
    │         Cloud SQL PostgreSQL              │
    │         (db-custom-2-7680, 50GB SSD)     │
    │         Connection pooling enabled        │
    │           ($80/month)                     │
    └──────────┬─────────────────────────────────┘
               │
    ┌──────────▼─────────────────────────────┐
    │         Memorystore Redis              │
    │         (1GB basic tier)               │
    │         Session & Cache Management     │
    │           ($50/month)                  │
    └────────────────────────────────────────┘
               │
    ┌──────────▼─────────────────────────────┐
    │         Multi-Agent System             │
    │  ┌─────────────┐ ┌─────────────────┐   │
    │  │ Supervisor  │ │ Apex Optimizer  │   │
    │  │ Agent       │ │ Agent (30+ tools│   │
    │  └─────────────┘ └─────────────────┘   │
    │  ┌─────────────┐ ┌─────────────────┐   │
    │  │ Triage      │ │ Data Analysis   │   │
    │  │ Sub-Agent   │ │ Sub-Agent       │   │
    │  └─────────────┘ └─────────────────┘   │
    └────────────────────────────────────────┘
               │
    ┌──────────▼─────────────────────────────┐
    │      Optional: ClickHouse              │
    │      (Analytics - Deploy later)        │
    │      (Not included in base budget)     │
    └────────────────────────────────────────┘
```

## Cost Breakdown

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud Run (Backend) | 4GB RAM, 2 vCPU, WebSocket support | $120 |
| Cloud Run (Frontend) | 1GB RAM, 1 vCPU, 1-3 instances | $40 |
| Cloud SQL PostgreSQL | db-custom-2-7680, 50GB SSD, connection pooling | $80 |
| Memorystore Redis | 1GB basic tier for sessions/cache | $50 |
| Cloud Load Balancing | HTTP(S) LB with WebSocket support | $25 |
| Container Registry | 20GB storage for multi-stage builds | $8 |
| Cloud Storage | 100GB for backups and logs | $10 |
| Secret Manager | Environment variables and API keys | $5 |
| Logging & Monitoring | Agent execution and WebSocket metrics | $30 |
| **Subtotal** | | **$368/month** |
| **Buffer for scaling & ClickHouse** | | **$632/month** |
| **Total Budget** | | **$1,000/month** |

## Step 1: Create Terraform Configuration (2 minutes)

Create a new directory for terraform files:

```bash
mkdir -p terraform-gcp
cd terraform-gcp
```

Create `main.tf`:

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "cloudrun.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "redis.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com"
  ])
  
  service = each.value
  disable_on_destroy = false
}

# Artifact Registry for Container Images
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "netra-containers"
  format        = "DOCKER"
  description   = "Docker repository for Netra containers"
}

# Cloud SQL PostgreSQL Instance (Agent-optimized)
resource "google_sql_database_instance" "postgres" {
  name             = "netra-postgres-${random_id.db_name_suffix.hex}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-custom-2-7680"  # 2 vCPU, 7.5GB RAM for agent workloads
    
    disk_size = 50  # 50GB for agent state and logs
    disk_type = "PD_SSD"
    disk_autoresize = true
    disk_autoresize_limit = 100
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                       = var.region
      point_in_time_recovery_enabled = true  # Required for production
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = true
      private_network = null  # Using public IP to avoid VPC costs
      
      authorized_networks {
        name  = "allow-all"  # For development; restrict in production
        value = "0.0.0.0/0"
      }
    }

    database_flags {
      name  = "max_connections"
      value = "100"  # Increased for agent system
    }
    
    database_flags {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"  # Enable query monitoring
    }
    
    database_flags {
      name  = "work_mem"
      value = "64MB"  # Optimized for agent operations
    }
  }

  deletion_protection = false  # For easy cleanup; enable in production
}

resource "random_id" "db_name_suffix" {
  byte_length = 4
}

# Database
resource "google_sql_database" "main" {
  name     = "netra"
  instance = google_sql_database_instance.postgres.name
}

# Database User
resource "google_sql_user" "main" {
  name     = "netra_user"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Secret Manager for sensitive data
resource "google_secret_manager_secret" "db_password" {
  secret_id = "netra-db-password"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Additional secrets for OAuth and API keys
resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "netra-jwt-secret"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

# OAuth secrets
resource "google_secret_manager_secret" "google_client_id" {
  secret_id = "netra-google-client-id"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "google_client_secret" {
  secret_id = "netra-google-client-secret"
  
  replication {
    auto {}
  }
}

# API keys
resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "netra-anthropic-api-key"
  
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "netra-openai-api-key"
  
  replication {
    auto {}
  }
}

# Memorystore Redis for sessions and caching
resource "google_redis_instance" "cache" {
  name           = "netra-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  
  redis_version     = "REDIS_7_0"
  display_name      = "Netra Redis Cache"
  reserved_ip_range = "10.0.0.0/29"
  
  auth_enabled = true
}

# Cloud Run Service - Backend (Agent-optimized)
resource "google_cloud_run_service" "backend" {
  name     = "netra-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers/backend:latest"
        
        resources {
          limits = {
            cpu    = "2"    # Increased for agent processing
            memory = "4Gi"  # Required for multi-agent system
          }
        }
        
        ports {
          container_port = 8000
        }
        
        # Database configuration
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.main.name}:${random_password.db_password.result}@${google_sql_database_instance.postgres.public_ip_address}:5432/${google_sql_database.main.name}"
        }
        
        # Redis configuration
        env {
          name  = "REDIS_URL"
          value = "redis://:${google_redis_instance.cache.auth_string}@${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
        }
        
        # Authentication secrets
        env {
          name = "SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.jwt_secret.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name = "GOOGLE_CLIENT_ID"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.google_client_id.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name = "GOOGLE_CLIENT_SECRET"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.google_client_secret.secret_id
              key  = "latest"
            }
          }
        }
        
        # API Keys
        env {
          name = "ANTHROPIC_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.anthropic_api_key.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.openai_api_key.secret_id
              key  = "latest"
            }
          }
        }
        
        # Application configuration
        env {
          name  = "ENVIRONMENT"
          value = "production"
        }
        
        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }
        
        env {
          name  = "FRONTEND_URL"
          value = "https://netra-frontend-${random_id.db_name_suffix.hex}-${data.google_client_config.default.region}-${data.google_client_config.default.project}.a.run.app"
        }
        
        env {
          name  = "CORS_ORIGINS"
          value = "https://netra-frontend-${random_id.db_name_suffix.hex}-${data.google_client_config.default.region}-${data.google_client_config.default.project}.a.run.app,http://localhost:3000"
        }
        
        # Health check configuration
        liveness_probe {
          http_get {
            path = "/health/live"
          }
          initial_delay_seconds = 30
          period_seconds = 10
        }
        
        readiness_probe {
          http_get {
            path = "/health/ready"
          }
          initial_delay_seconds = 10
          period_seconds = 5
        }
      }
      
      # WebSocket configuration
      timeout_seconds = 300  # 5 minutes for long-running agent operations
      service_account_name = google_service_account.cloudrun.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "10"
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/cpu-throttling" = "false"  # Always-on CPU for WebSocket
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [google_project_service.apis, google_redis_instance.cache]
}

# Data source for current config
data "google_client_config" "default" {}

# Cloud Run Service - Frontend
resource "google_cloud_run_service" "frontend" {
  name     = "netra-frontend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers/frontend:latest"
        
        resources {
          limits = {
            cpu    = "0.5"
            memory = "1Gi"
          }
        }
        
        env {
          name  = "NEXT_PUBLIC_API_URL"
          value = google_cloud_run_service.backend.status[0].url
        }
        
        env {
          name  = "NEXT_PUBLIC_WS_URL"
          value = replace(google_cloud_run_service.backend.status[0].url, "https", "wss")
        }
        
        env {
          name  = "NEXT_PUBLIC_ENVIRONMENT"
          value = "production"
        }
        
        env {
          name  = "NEXTAUTH_URL"
          value = "https://netra-frontend-${random_id.db_name_suffix.hex}-${data.google_client_config.default.region}-${data.google_client_config.default.project}.a.run.app"
        }
        
        env {
          name = "NEXTAUTH_SECRET"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.jwt_secret.secret_id
              key  = "latest"
            }
          }
        }
      }
      
      service_account_name = google_service_account.cloudrun.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "3"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [google_cloud_run_service.backend]
}

# Service Account for Cloud Run
resource "google_service_account" "cloudrun" {
  account_id   = "netra-cloudrun"
  display_name = "Netra Cloud Run Service Account"
}

# IAM permissions for Cloud Run
resource "google_project_iam_member" "cloudrun_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

resource "google_project_iam_member" "cloudrun_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Allow unauthenticated access to Frontend (public app)
resource "google_cloud_run_service_iam_member" "frontend_public" {
  service  = google_cloud_run_service.frontend.name
  location = google_cloud_run_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Allow unauthenticated access to Backend API
resource "google_cloud_run_service_iam_member" "backend_public" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Storage bucket for backups
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-netra-backups"
  location      = var.region
  force_destroy = true

  lifecycle_rule {
    condition {
      age = 30  # Delete backups older than 30 days
    }
    action {
      type = "Delete"
    }
  }
  
  versioning {
    enabled = false  # Disabled to save costs
  }
}

# Outputs
output "frontend_url" {
  value = google_cloud_run_service.frontend.status[0].url
  description = "Frontend application URL"
}

output "backend_url" {
  value = google_cloud_run_service.backend.status[0].url
  description = "Backend API URL"
}

output "database_ip" {
  value = google_sql_database_instance.postgres.public_ip_address
  description = "Database public IP address"
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers"
  description = "Container registry URL"
}

output "redis_host" {
  value = google_redis_instance.cache.host
  description = "Redis instance host"
}

output "websocket_url" {
  value = replace(google_cloud_run_service.backend.status[0].url, "https", "wss")
  description = "WebSocket connection URL"
}
```

Create `terraform.tfvars`:

```hcl
# terraform.tfvars
project_id = "netra-production"  # Replace with your project ID
region     = "us-central1"
zone       = "us-central1-a"
```

## Step 2: Deploy Infrastructure (3 minutes)

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply -auto-approve

# Save the outputs
terraform output > deployment-info.txt
```

## Step 3: Build and Deploy Containers (3 minutes)

```bash
# Configure Docker for GCP
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Get the registry URL from terraform output
export REGISTRY=$(terraform output -raw artifact_registry)

# Build and push Backend (Multi-stage build)
cd ../  # Go to project root
docker build -f Dockerfile -t ${REGISTRY}/backend:latest --target backend .
docker push ${REGISTRY}/backend:latest

# Build and push Frontend (Multi-stage build)
docker build -f Dockerfile -t ${REGISTRY}/frontend:latest --target frontend .
docker push ${REGISTRY}/frontend:latest

# Update Cloud Run services with new images
gcloud run deploy netra-backend \
  --image ${REGISTRY}/backend:latest \
  --region ${REGION}

gcloud run deploy netra-frontend \
  --image ${REGISTRY}/frontend:latest \
  --region ${REGION}
```

## Step 4: Database Setup and Migrations (2 minutes)

```bash
# Get database connection info
export DB_IP=$(terraform output -raw database_ip)
export DB_PASSWORD=$(gcloud secrets versions access latest --secret="netra-db-password")

# Connect to database and setup extensions
gcloud sql connect netra-postgres-* --user=netra_user

# In the SQL prompt, create extensions and initial setup
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE SCHEMA IF NOT EXISTS public;
\q

# Run database initialization script
cd ../  # Go to project root
DATABASE_URL="postgresql://netra_user:${DB_PASSWORD}@${DB_IP}:5432/netra" \
  python create_db.py

# Run Alembic migrations
DATABASE_URL="postgresql://netra_user:${DB_PASSWORD}@${DB_IP}:5432/netra" \
  python run_migrations.py

# Create initial admin user (optional)
DATABASE_URL="postgresql://netra_user:${DB_PASSWORD}@${DB_IP}:5432/netra" \
  python -c "
import os
import asyncio
from app.services.database.user_repository import UserRepository
from app.db.postgres import get_database

async def create_admin():
    async with get_database() as db:
        user_repo = UserRepository(db)
        admin = await user_repo.create_user({
            'email': 'admin@netrasystems.ai',
            'name': 'Admin User',
            'is_admin': True
        })
        print(f'Created admin user: {admin.email}')

asyncio.run(create_admin())
"
```

## Step 5: Verify Deployment (2 minutes)

```bash
# Get URLs
export FRONTEND_URL=$(terraform output -raw frontend_url)
export BACKEND_URL=$(terraform output -raw backend_url)
export WEBSOCKET_URL=$(terraform output -raw websocket_url)

# Test backend health endpoints
curl ${BACKEND_URL}/health/live
curl ${BACKEND_URL}/health/ready

# Test authentication endpoint
curl ${BACKEND_URL}/api/auth/status

# Test frontend
curl -I ${FRONTEND_URL}

# Test WebSocket connection (using wscat if available)
# npm install -g wscat
# wscat -c "${WEBSOCKET_URL}/ws"

# Open in browser
echo "Frontend: ${FRONTEND_URL}"
echo "Backend API: ${BACKEND_URL}"
echo "WebSocket: ${WEBSOCKET_URL}/ws"
echo "Redis Host: $(terraform output -raw redis_host)"
echo "Database IP: ${DB_IP}"

# Save deployment info
cat > deployment-urls.txt << EOF
Deployment Information
====================
Frontend URL: ${FRONTEND_URL}
Backend API: ${BACKEND_URL}
WebSocket URL: ${WEBSOCKET_URL}/ws
Database IP: ${DB_IP}
Redis Host: $(terraform output -raw redis_host)
Project ID: ${PROJECT_ID}
Region: ${REGION}

Next Steps:
1. Configure OAuth in Google Console
2. Add API keys to Secret Manager
3. Test WebSocket connections
4. Monitor agent system health
EOF

echo "Deployment information saved to deployment-urls.txt"
```

## Step 6: Configure OAuth Setup (3 minutes)

```bash
# Set up Google OAuth credentials
# 1. Go to Google Cloud Console -> APIs & Services -> Credentials
# 2. Create OAuth 2.0 Client ID
# 3. Add authorized redirect URIs:
#    - ${FRONTEND_URL}/auth/callback/google
#    - http://localhost:3000/auth/callback/google (for development)

# Store OAuth credentials in Secret Manager
gcloud secrets versions add netra-google-client-id --data-file=- <<< "YOUR_GOOGLE_CLIENT_ID"
gcloud secrets versions add netra-google-client-secret --data-file=- <<< "YOUR_GOOGLE_CLIENT_SECRET"

# Store API keys
gcloud secrets versions add netra-anthropic-api-key --data-file=- <<< "YOUR_ANTHROPIC_API_KEY"
gcloud secrets versions add netra-openai-api-key --data-file=- <<< "YOUR_OPENAI_API_KEY"

# Restart services to pick up new environment variables
gcloud run deploy netra-backend --region=${REGION} --update-env-vars="RESTART=$(date +%s)"
gcloud run deploy netra-frontend --region=${REGION} --update-env-vars="RESTART=$(date +%s)"
```

## Step 7: WebSocket Testing and Verification (1 minute)

```bash
# Install WebSocket testing tool
npm install -g wscat

# Test WebSocket connection
echo "Testing WebSocket connection..."
wscat -c "${WEBSOCKET_URL}/ws" -w 5000 <<EOF
{"type": "ping", "data": {}}
EOF

# Expected response: {"type": "pong", "data": {}}

# Test agent interaction via WebSocket
wscat -c "${WEBSOCKET_URL}/ws" <<EOF
{
  "type": "agent_message",
  "data": {
    "message": "Hello, test the agent system",
    "thread_id": "test-thread-123"
  }
}
EOF

# Monitor WebSocket logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend \
  AND textPayload:websocket" \
  --limit 20
```

## Step 8: Agent System Configuration (2 minutes)

```bash
# Verify agent system health
curl ${BACKEND_URL}/api/agents/health

# Test supervisor agent
curl -X POST ${BACKEND_URL}/api/agents/supervisor/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Test agent orchestration"}'

# Check available sub-agents
curl ${BACKEND_URL}/api/agents/available

# Monitor agent execution metrics
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend \
  AND (textPayload:agent OR textPayload:supervisor)" \
  --limit 30

# Configure agent timeout settings (if needed)
gcloud run services update netra-backend \
  --update-env-vars="AGENT_TIMEOUT=300,WEBSOCKET_HEARTBEAT=30" \
  --region=${REGION}
```

## Monitoring & Logs

```bash
# View Cloud Run logs with agent-specific filters
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend" \
  --limit 50 --format json

# Monitor agent execution logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend \
  AND (textPayload:agent_execution OR textPayload:tool_call)" \
  --limit 30

# Monitor WebSocket connection metrics
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend \
  AND textPayload:websocket" \
  --limit 20

# Monitor database connection pool
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend \
  AND textPayload:database" \
  --limit 20

# Monitor costs
gcloud billing accounts get-iam-policy $(gcloud beta billing accounts list --format="value(name)")

# Set budget alert
gcloud billing budgets create \
  --billing-account=$(gcloud beta billing accounts list --format="value(name)") \
  --display-name="Netra Monthly Budget" \
  --budget-amount=1000 \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0

# Create monitoring dashboard for key metrics
cat > monitoring-dashboard.json << 'EOF'
{
  "displayName": "Netra AI Platform",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Cloud Run Request Count",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Agent Execution Time",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=cloud_run_revision AND textPayload:agent_execution_time"
                }
              }
            }]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "WebSocket Connections",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=cloud_run_revision AND textPayload:websocket_connection"
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF

gcloud monitoring dashboards create --config-from-file=monitoring-dashboard.json
```

## Cost Optimization Tips

1. **Use Committed Use Discounts**: Save up to 57% with 1-year commitments
```bash
gcloud compute commitments create netra-commit \
  --region=${REGION} \
  --resources=vcpu=2,memory=4GB \
  --plan=TWELVE_MONTH
```

2. **Enable Cloud Run CPU Allocation**: Only charge when processing requests
```bash
gcloud run services update netra-backend \
  --cpu-throttling \
  --region=${REGION}
```

3. **Schedule Scaling**: Scale down during off-hours
```bash
# Create Cloud Scheduler job to scale down at night
gcloud scheduler jobs create http scale-down \
  --location=${REGION} \
  --schedule="0 22 * * *" \
  --uri="${BACKEND_URL}/admin/scale" \
  --http-method=POST \
  --message-body='{"min_instances": 0, "max_instances": 1}'
```

4. **Deploy ClickHouse for Analytics** (optional, adds ~$100/month):
```bash
# Create ClickHouse instance for analytics
gcloud compute instances create netra-clickhouse \
  --machine-type=e2-standard-2 \
  --provisioning-model=SPOT \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-ssd \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --zone=${ZONE} \
  --tags=clickhouse-server

# Setup ClickHouse (run on the instance)
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

# Create firewall rule for ClickHouse
gcloud compute firewall-rules create allow-clickhouse \
  --allow tcp:8123,tcp:9000 \
  --source-ranges 0.0.0.0/0 \
  --target-tags clickhouse-server

# Get ClickHouse IP
export CLICKHOUSE_IP=$(gcloud compute instances describe netra-clickhouse --zone=${ZONE} --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
echo "ClickHouse available at: http://${CLICKHOUSE_IP}:8123"
```

5. **Session Management Configuration**:
```bash
# Configure Redis for optimal session handling
gcloud redis instances update netra-redis \
  --region=${REGION} \
  --enable-auth \
  --redis-config maxmemory-policy=allkeys-lru

# Update backend with session settings
gcloud run services update netra-backend \
  --update-env-vars="SESSION_TIMEOUT=3600,REDIS_SESSION_PREFIX=netra:session:" \
  --region=${REGION}
```

6. **WebSocket Heartbeat and Timeout Configuration**:
```bash
# Configure WebSocket settings for production
gcloud run services update netra-backend \
  --update-env-vars="WEBSOCKET_HEARTBEAT_INTERVAL=30,WEBSOCKET_TIMEOUT=300,AGENT_MAX_EXECUTION_TIME=600" \
  --region=${REGION}
```

7. **Database Connection Pool Optimization**:
```bash
# Update PostgreSQL settings for better connection handling
gcloud sql instances patch netra-postgres-* \
  --database-flags=max_connections=200,shared_preload_libraries=pg_stat_statements,work_mem=128MB

# Update backend with connection pool settings
gcloud run services update netra-backend \
  --update-env-vars="DB_POOL_SIZE=20,DB_MAX_OVERFLOW=30,DB_POOL_TIMEOUT=30" \
  --region=${REGION}
```

## Backup Strategy

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
# Daily backup script

# Backup PostgreSQL
gcloud sql backups create \
  --instance=netra-postgres-* \
  --description="Daily backup $(date +%Y%m%d)"

# Export to Cloud Storage
gcloud sql export sql netra-postgres-* \
  gs://netra-production-netra-backups/postgres-$(date +%Y%m%d).sql \
  --database=netra

# Clean old backups (keep last 7 days)
gsutil ls gs://netra-production-netra-backups/ | \
  grep postgres- | \
  sort | \
  head -n -7 | \
  xargs -I {} gsutil rm {}
EOF

chmod +x backup.sh

# Schedule daily backups
gcloud scheduler jobs create app-engine backup-job \
  --schedule="0 2 * * *" \
  --http-method=GET \
  --uri="https://YOUR_PROJECT.appspot.com/backup"
```

## Troubleshooting

### Issue: Cloud Run service not starting
```bash
# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Check service status
gcloud run services describe netra-backend --region=${REGION}

# Update memory if needed
gcloud run services update netra-backend --memory=4Gi --region=${REGION}
```

### Issue: Database connection failed
```bash
# Check Cloud SQL status
gcloud sql instances describe netra-postgres-*

# Test connection
gcloud sql connect netra-postgres-* --user=netra_user

# Check authorized networks
gcloud sql instances patch netra-postgres-* \
  --authorized-networks=0.0.0.0/0
```

### Issue: High costs
```bash
# Review cost breakdown
gcloud billing accounts get-iam-policy $(gcloud beta billing accounts list --format="value(name)")

# Check resource usage
gcloud monitoring metrics-explorer

# Reduce instance sizes
terraform apply -var="backend_cpu=0.5" -var="backend_memory=1Gi"
```

## Cleanup (if needed)

```bash
# Destroy all resources
terraform destroy -auto-approve

# Delete project (WARNING: This deletes everything!)
gcloud projects delete ${PROJECT_ID}
```

## Security Hardening (Post-Deployment)

Once running, implement these security measures:

```bash
# 1. Restrict database access
gcloud sql instances patch netra-postgres-* \
  --authorized-networks=YOUR_IP/32

# 2. Enable Cloud Armor (DDoS protection)
gcloud compute security-policies create netra-security-policy \
  --description="Security policy for Netra"

# 3. Setup IAP (Identity-Aware Proxy) for admin access
gcloud iap web enable --resource-type=backend-services \
  --service=netra-backend

# 4. Enable VPC Service Controls
gcloud access-context-manager perimeters create netra-perimeter \
  --resources=projects/$(gcloud config get-value project) \
  --restricted-services=storage.googleapis.com
```

## Support

- **GCP Console**: https://console.cloud.google.com
- **Terraform Docs**: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **Cost Calculator**: https://cloud.google.com/products/calculator

## Production Configuration

### Session Management
```bash
# Configure Redis for production session handling
gcloud redis instances update netra-redis \
  --region=${REGION} \
  --redis-config maxmemory-policy=allkeys-lru,timeout=0,tcp-keepalive=300

# Update session configuration
gcloud run services update netra-backend \
  --update-env-vars="
SESSION_TIMEOUT=7200,
SESSION_REFRESH_THRESHOLD=1800,
SESSION_CLEANUP_INTERVAL=3600,
REDIS_SESSION_PREFIX=netra:prod:session:
" \
  --region=${REGION}
```

### WebSocket Production Settings
```bash
# Configure WebSocket for production workload
gcloud run services update netra-backend \
  --update-env-vars="
WEBSOCKET_HEARTBEAT_INTERVAL=30,
WEBSOCKET_TIMEOUT=300,
WEBSOCKET_MAX_CONNECTIONS=1000,
WEBSOCKET_BUFFER_SIZE=65536
" \
  --region=${REGION}
```

### Agent System Production Configuration
```bash
# Configure agent timeouts and limits
gcloud run services update netra-backend \
  --update-env-vars="
AGENT_MAX_EXECUTION_TIME=600,
AGENT_HEARTBEAT_INTERVAL=60,
AGENT_MAX_CONCURRENT_OPERATIONS=10,
AGENT_TOOL_TIMEOUT=120,
SUPERVISOR_ORCHESTRATION_TIMEOUT=300
" \
  --region=${REGION}
```

### Database Connection Limits
```bash
# Optimize database connections for production
gcloud sql instances patch netra-postgres-* \
  --database-flags="
max_connections=200,
idle_in_transaction_session_timeout=300000,
statement_timeout=600000,
lock_timeout=30000,
shared_preload_libraries=pg_stat_statements
"

# Update backend connection pool
gcloud run services update netra-backend \
  --update-env-vars="
DB_POOL_SIZE=20,
DB_MAX_OVERFLOW=40,
DB_POOL_TIMEOUT=30,
DB_POOL_RECYCLE=3600,
DB_POOL_PRE_PING=true
" \
  --region=${REGION}
```

## Next Steps

1. **Custom Domain Setup**
   ```bash
   # Configure custom domain with Cloud DNS
   gcloud dns managed-zones create netra-zone --dns-name="yourdomain.com" --description="Netra DNS zone"
   gcloud run domain-mappings create --service netra-frontend --domain app.yourdomain.com --region ${REGION}
   ```

2. **SSL/TLS Certificate Management**
   ```bash
   # Cloud Run automatically handles SSL certificates for custom domains
   gcloud run services update netra-frontend --update-labels=ssl-cert-auto=true --region ${REGION}
   ```

3. **Cloud CDN Configuration**
   ```bash
   # Setup Cloud CDN for static assets
   gcloud compute backend-services create netra-backend-service --global
   gcloud compute url-maps create netra-url-map --default-backend-service netra-backend-service
   ```

4. **Advanced Monitoring Setup**
   ```bash
   # Create alerting policies for critical metrics
   gcloud alpha monitoring policies create \
     --policy-from-file=alerting-policy.yaml
   ```

5. **Backup Automation**
   ```bash
   # Setup automated daily backups
   gcloud scheduler jobs create app-engine daily-backup \
     --schedule="0 2 * * *" \
     --http-method=POST \
     --uri="${BACKEND_URL}/api/admin/backup"
   ```

6. **ClickHouse Analytics Integration**
   - Deploy ClickHouse for advanced analytics
   - Configure log streaming from Cloud Run
   - Setup analytics dashboards

7. **Security Hardening**
   - Enable Cloud Armor DDoS protection
   - Setup Identity-Aware Proxy for admin endpoints
   - Configure VPC Service Controls
   - Enable audit logging

---

**Total Deployment Time: ~15 minutes**
**Monthly Cost: $368 base + scaling buffer = < $1,000**
**Scalability: Handles 1M+ requests/day with agent system**
**WebSocket Support: Real-time agent interactions**
**Multi-Agent System: Supervisor + specialized sub-agents**