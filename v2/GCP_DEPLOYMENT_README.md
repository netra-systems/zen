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
    │  (1 instance)     │  │  (2 instances)     │
    │  ($30/month)      │  │  ($80/month)       │
    └───────────────────┘  └────────────────────┘
                   │              │
    ┌──────────────▼──────────────▼─────────────┐
    │         Cloud SQL PostgreSQL              │
    │         (db-f1-micro, 20GB)              │
    │           ($40/month)                     │
    └────────────────────────────────────────────┘
                   │
    ┌──────────────▼─────────────────────────────┐
    │         Memorystore Redis                  │
    │         (Setup separately)                 │
    │         (Not included in budget)           │
    └─────────────────────────────────────────────┘
```

## Cost Breakdown

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| Cloud Run (Backend) | 2 instances, 1 vCPU, 2GB RAM | $80 |
| Cloud Run (Frontend) | 1 instance, 0.5 vCPU, 1GB RAM | $30 |
| Cloud SQL PostgreSQL | db-f1-micro, 20GB SSD | $40 |
| Cloud Load Balancing | HTTP(S) Load Balancer | $20 |
| Container Registry | 10GB storage | $5 |
| Cloud Storage | 50GB for backups | $5 |
| Logging & Monitoring | Basic tier | $20 |
| **Subtotal** | | **$200/month** |
| **Buffer for scaling** | | **$800/month** |
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
    "secretmanager.googleapis.com"
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

# Cloud SQL PostgreSQL Instance (Budget-optimized)
resource "google_sql_database_instance" "postgres" {
  name             = "netra-postgres-${random_id.db_name_suffix.hex}"
  database_version = "POSTGRES_14"
  region           = var.region

  settings {
    tier = "db-f1-micro"  # Smallest instance for budget
    
    disk_size = 20  # 20GB minimum
    disk_type = "PD_SSD"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                       = var.region
      point_in_time_recovery_enabled = false  # Disabled to save costs
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
      value = "50"
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

# Cloud Run Service - Backend
resource "google_cloud_run_service" "backend" {
  name     = "netra-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers/backend:latest"
        
        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi"
          }
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.main.name}:${random_password.db_password.result}@${google_sql_database_instance.postgres.public_ip_address}:5432/${google_sql_database.main.name}"
        }
        
        env {
          name = "JWT_SECRET_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.jwt_secret.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://redis-standalone:6379"  # Update with actual Redis URL
        }
      }
      
      service_account_name = google_service_account.cloudrun.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "5"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [google_project_service.apis]
}

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

# Build and push Backend
cd ../  # Go to project root
docker build -f Dockerfile.backend -t ${REGISTRY}/backend:latest .
docker push ${REGISTRY}/backend:latest

# Build and push Frontend
cd frontend
docker build -t ${REGISTRY}/frontend:latest .
docker push ${REGISTRY}/frontend:latest

# Update Cloud Run services with new images
gcloud run deploy netra-backend \
  --image ${REGISTRY}/backend:latest \
  --region ${REGION}

gcloud run deploy netra-frontend \
  --image ${REGISTRY}/frontend:latest \
  --region ${REGION}
```

## Step 4: Database Setup (1 minute)

```bash
# Get database connection info
export DB_IP=$(terraform output -raw database_ip)
export DB_PASSWORD=$(gcloud secrets versions access latest --secret="netra-db-password")

# Connect to database and run migrations
gcloud sql connect netra-postgres-* --user=netra_user

# In the SQL prompt, create initial schema
CREATE SCHEMA IF NOT EXISTS public;

# Exit SQL prompt and run migrations
cd ../  # Go to project root
DATABASE_URL="postgresql://netra_user:${DB_PASSWORD}@${DB_IP}:5432/netra" \
  python run_migrations.py
```

## Step 5: Verify Deployment (1 minute)

```bash
# Get URLs
export FRONTEND_URL=$(terraform output -raw frontend_url)
export BACKEND_URL=$(terraform output -raw backend_url)

# Test backend health
curl ${BACKEND_URL}/health

# Test frontend
curl ${FRONTEND_URL}

# Open in browser
echo "Frontend: ${FRONTEND_URL}"
echo "Backend API: ${BACKEND_URL}"
```

## Monitoring & Logs

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=netra-backend" \
  --limit 50 --format json

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

4. **Use Spot VMs for ClickHouse** (if needed later):
```bash
gcloud compute instances create netra-clickhouse \
  --machine-type=e2-medium \
  --provisioning-model=SPOT \
  --zone=${ZONE}
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

## Next Steps

1. Setup custom domain with Cloud DNS
2. Configure Cloud CDN for static assets
3. Implement Cloud Monitoring dashboards
4. Setup automated backups with Cloud Scheduler
5. Configure alerts for budget and performance

---

**Total Deployment Time: ~10 minutes**
**Monthly Cost: < $1,000**
**Scalability: Handles 100,000+ requests/day**