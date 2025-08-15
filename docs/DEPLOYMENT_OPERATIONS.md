# Deployment & Operations Guide

Comprehensive guide for deploying and operating the Netra AI Optimization Platform in production environments.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Infrastructure Requirements](#infrastructure-requirements)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployments](#cloud-deployments)
- [CI/CD Pipeline](#cicd-pipeline)
- [Monitoring & Observability](#monitoring--observability)
- [Backup & Recovery](#backup--recovery)
- [Scaling Strategies](#scaling-strategies)
- [Security Hardening](#security-hardening)
- [Operational Procedures](#operational-procedures)
- [Troubleshooting Guide](#troubleshooting-guide)

## Deployment Overview

### Architecture Components

```
┌──────────────────────────────────────────────────────┐
│                   Load Balancer                      │
│                  (NGINX/ALB/CloudFlare)              │
└──────────────────┬───────────────┬───────────────────┘
                   │               │
      ┌────────────▼───────┐ ┌────▼──────────────┐
      │   Frontend Cluster │ │  Backend Cluster  │
      │   (Next.js SSR)    │ │    (FastAPI)      │
      │   ┌────────────┐   │ │  ┌────────────┐   │
      │   │   Node 1   │   │ │  │   Node 1   │   │
      │   │   Node 2   │   │ │  │   Node 2   │   │
      │   │   Node N   │   │ │  │   Node N   │   │
      │   └────────────┘   │ │  └────────────┘   │
      └────────────────────┘ └────────────────────┘
                   │               │
      ┌────────────▼───────────────▼───────────────┐
      │              Data Layer                     │
      │  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
      │  │PostgreSQL│  │ClickHouse│  │  Redis   │ │
      │  │ Primary  │  │  Cluster │  │  Cluster │ │
      │  └──────────┘  └──────────┘  └──────────┘ │
      └─────────────────────────────────────────────┘
```

### Deployment Environments

| Environment | Purpose | Configuration |
|------------|---------|---------------|
| **Development** | Local development | Docker Compose, local DBs |
| **Staging** | Pre-production testing | Kubernetes, scaled down |
| **Production** | Live system | Kubernetes, full scale |
| **DR** | Disaster recovery | Cross-region standby |

## Infrastructure Requirements

### Minimum Requirements

#### Backend Servers
- **CPU**: 4 vCPUs
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **Network**: 1 Gbps
- **Count**: 2 minimum (HA)

#### Frontend Servers
- **CPU**: 2 vCPUs
- **RAM**: 4 GB
- **Storage**: 20 GB SSD
- **Network**: 1 Gbps
- **Count**: 2 minimum (HA)

#### Database Servers
- **PostgreSQL**:
  - CPU: 8 vCPUs
  - RAM: 32 GB
  - Storage: 500 GB SSD (IOPS optimized)
  - Replication: Primary + 1 replica minimum

- **ClickHouse**:
  - CPU: 8 vCPUs
  - RAM: 64 GB
  - Storage: 1 TB SSD
  - Cluster: 3 nodes minimum

- **Redis**:
  - CPU: 2 vCPUs
  - RAM: 8 GB
  - Storage: 20 GB SSD
  - Cluster: 3 nodes (1 primary, 2 replicas)

### Recommended Production Setup

```yaml
# production-infrastructure.yaml
infrastructure:
  regions:
    primary: us-east-1
    secondary: us-west-2
  
  compute:
    backend:
      instance_type: c5.2xlarge
      count: 6
      auto_scaling:
        min: 3
        max: 20
    
    frontend:
      instance_type: t3.large
      count: 4
      auto_scaling:
        min: 2
        max: 10
  
  databases:
    postgresql:
      instance_type: db.r5.2xlarge
      multi_az: true
      read_replicas: 2
      backup_retention: 30
    
    clickhouse:
      instance_type: r5.2xlarge
      nodes: 6
      replication_factor: 2
    
    redis:
      node_type: cache.r6g.xlarge
      cluster_mode: enabled
      num_shards: 3
```

## Docker Deployment

### Docker Images

#### Backend Dockerfile
```dockerfile
# Dockerfile.backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend Dockerfile
```dockerfile
# Dockerfile.frontend
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD node -e "require('http').get('http://localhost:3000/api/health')"

EXPOSE 3000

CMD ["npm", "start"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/netra
      - REDIS_URL=redis://redis:6379
      - CLICKHOUSE_URL=clickhouse://clickhouse:9000
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - clickhouse
    networks:
      - netra-network
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
      - NEXT_PUBLIC_WS_URL=ws://backend:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    networks:
      - netra-network
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 2G

  postgres:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=netra
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - netra-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    networks:
      - netra-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 8G

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - netra-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1G

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
      - frontend
    networks:
      - netra-network

networks:
  netra-network:
    driver: bridge

volumes:
  postgres_data:
  clickhouse_data:
  redis_data:
```

### Docker Deployment Commands

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Scale services
docker-compose up -d --scale backend=3 --scale frontend=2

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Remove everything including volumes
docker-compose down -v
```

## Kubernetes Deployment

### Kubernetes Manifests

#### Namespace
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: netra-production
```

#### Backend Deployment
```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netra-backend
  namespace: netra-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: netra-backend
  template:
    metadata:
      labels:
        app: netra-backend
    spec:
      containers:
      - name: backend
        image: netra/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: netra-secrets
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: netra-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: netra-backend
  namespace: netra-production
spec:
  selector:
    app: netra-backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### Frontend Deployment
```yaml
# k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netra-frontend
  namespace: netra-production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: netra-frontend
  template:
    metadata:
      labels:
        app: netra-frontend
    spec:
      containers:
      - name: frontend
        image: netra/frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.netrasystems.ai"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
---
apiVersion: v1
kind: Service
metadata:
  name: netra-frontend
  namespace: netra-production
spec:
  selector:
    app: netra-frontend
  ports:
  - port: 3000
    targetPort: 3000
  type: ClusterIP
```

#### Ingress Configuration
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: netra-ingress
  namespace: netra-production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/websocket-services: netra-backend
spec:
  tls:
  - hosts:
    - app.netrasystems.ai
    - api.netrasystems.ai
    secretName: netra-tls
  rules:
  - host: app.netrasystems.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: netra-frontend
            port:
              number: 3000
  - host: api.netrasystems.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: netra-backend
            port:
              number: 8000
```

#### Horizontal Pod Autoscaler
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: netra-backend-hpa
  namespace: netra-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: netra-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Helm Chart

```yaml
# helm/netra/values.yaml
global:
  domain: netrasystems.ai
  environment: production

backend:
  image:
    repository: netra/backend
    tag: latest
    pullPolicy: IfNotPresent
  
  replicas: 3
  
  resources:
    requests:
      memory: 2Gi
      cpu: 1
    limits:
      memory: 4Gi
      cpu: 2
  
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPU: 70
    targetMemory: 80

frontend:
  image:
    repository: netra/frontend
    tag: latest
  
  replicas: 2
  
  resources:
    requests:
      memory: 1Gi
      cpu: 500m
    limits:
      memory: 2Gi
      cpu: 1

postgresql:
  enabled: true
  auth:
    database: netra
    username: netra_user
  
  primary:
    persistence:
      size: 100Gi
  
  readReplicas:
    enabled: true
    replicas: 2

redis:
  enabled: true
  architecture: replication
  auth:
    enabled: true
  
  master:
    persistence:
      size: 10Gi
  
  replica:
    replicaCount: 2
```

### Kubernetes Commands

```bash
# Create namespace
kubectl create namespace netra-production

# Apply configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get deployments -n netra-production

# View pods
kubectl get pods -n netra-production

# Check logs
kubectl logs -n netra-production deployment/netra-backend

# Scale deployment
kubectl scale deployment netra-backend --replicas=5 -n netra-production

# Update image
kubectl set image deployment/netra-backend backend=netra/backend:v2.1.0 -n netra-production

# Rollback deployment
kubectl rollout undo deployment/netra-backend -n netra-production
```

## Cloud Deployments

### AWS Deployment

#### Terraform Configuration
```hcl
# terraform/aws/main.tf
provider "aws" {
  region = var.aws_region
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "netra-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = true
  
  tags = {
    Environment = "production"
    Application = "netra"
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "netra-cluster"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  node_groups = {
    main = {
      desired_capacity = 3
      max_capacity     = 10
      min_capacity     = 2
      
      instance_types = ["t3.large"]
      
      k8s_labels = {
        Environment = "production"
        Application = "netra"
      }
    }
  }
}

# RDS PostgreSQL
resource "aws_db_instance" "postgresql" {
  identifier = "netra-postgresql"
  
  engine         = "postgres"
  engine_version = "14.8"
  instance_class = "db.r5.xlarge"
  
  allocated_storage     = 100
  storage_encrypted     = true
  storage_type          = "gp3"
  
  db_name  = "netra"
  username = "netra_admin"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  multi_az               = true
  publicly_accessible    = false
  
  tags = {
    Environment = "production"
    Application = "netra"
  }
}

# ElastiCache Redis
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "netra-redis"
  replication_group_description = "Redis cluster for Netra"
  
  engine               = "redis"
  node_type            = "cache.r6g.large"
  number_cache_clusters = 3
  
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  subnet_group_name = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  snapshot_retention_limit = 7
  snapshot_window         = "03:00-05:00"
  
  tags = {
    Environment = "production"
    Application = "netra"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "netra-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = module.vpc.public_subnets
  
  enable_deletion_protection = true
  enable_http2              = true
  
  tags = {
    Environment = "production"
    Application = "netra"
  }
}
```

### Google Cloud Deployment

```yaml
# gcp/deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gcp-config
data:
  project_id: "netra-production"
  region: "us-central1"
  zone: "us-central1-a"
---
# GKE cluster configuration
apiVersion: container.gke.io/v1
kind: Cluster
metadata:
  name: netra-gke-cluster
spec:
  initialNodeCount: 3
  nodeConfig:
    machineType: n2-standard-4
    diskSizeGb: 100
    oauthScopes:
    - https://www.googleapis.com/auth/cloud-platform
```

### Azure Deployment

```powershell
# azure/deploy.ps1
# Create resource group
az group create --name netra-rg --location eastus

# Create AKS cluster
az aks create \
  --resource-group netra-rg \
  --name netra-aks \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Create Azure Database for PostgreSQL
az postgres server create \
  --resource-group netra-rg \
  --name netra-postgresql \
  --location eastus \
  --admin-user netraadmin \
  --admin-password $DB_PASSWORD \
  --sku-name GP_Gen5_2 \
  --version 14

# Create Azure Cache for Redis
az redis create \
  --resource-group netra-rg \
  --name netra-redis \
  --location eastus \
  --sku Premium \
  --vm-size P1
```

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: warp-custom-default
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=app tests/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: warp-custom-default
    steps:
    - uses: actions/checkout@v3
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Backend
      uses: docker/build-push-action@v4
      with:
        context: .
        file: ./Dockerfile.backend
        push: true
        tags: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:latest
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:${{ github.sha }}
    
    - name: Build and push Frontend
      uses: docker/build-push-action@v4
      with:
        context: ./frontend
        file: ./frontend/Dockerfile
        push: true
        tags: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:latest
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:${{ github.sha }}

  deploy:
    needs: build
    runs-on: warp-custom-default
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --name netra-cluster --region us-east-1
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/netra-backend \
          backend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:${{ github.sha }} \
          -n netra-production
        
        kubectl set image deployment/netra-frontend \
          frontend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:${{ github.sha }} \
          -n netra-production
        
        kubectl rollout status deployment/netra-backend -n netra-production
        kubectl rollout status deployment/netra-frontend -n netra-production
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: ""

test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pip install pytest pytest-cov
    - pytest --cov=app tests/
  coverage: '/TOTAL.*\s+(\d+%)$/'

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA -f Dockerfile.backend .
    - docker build -t $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA -f frontend/Dockerfile frontend/
    - docker push $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA

deploy:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl set image deployment/netra-backend backend=$CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA
    - kubectl set image deployment/netra-frontend frontend=$CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA
  only:
    - main
```

## Monitoring & Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    scrape_configs:
    - job_name: 'netra-backend'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - netra-production
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: netra-backend
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
    
    - job_name: 'netra-frontend'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - netra-production
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: netra-frontend
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "Netra Production Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds_bucket)"
          }
        ]
      },
      {
        "title": "Active WebSocket Connections",
        "targets": [
          {
            "expr": "websocket_connections"
          }
        ]
      }
    ]
  }
}
```

### Logging Configuration

```yaml
# logging/fluentd-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/netra-*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      <parse>
        @type json
      </parse>
    </source>
    
    <filter kubernetes.**>
      @type kubernetes_metadata
    </filter>
    
    <match **>
      @type elasticsearch
      host elasticsearch.monitoring.svc.cluster.local
      port 9200
      logstash_format true
      logstash_prefix netra
      <buffer>
        @type file
        path /var/log/fluentd-buffers/kubernetes.system.buffer
        flush_mode interval
        retry_type exponential_backoff
        flush_interval 5s
      </buffer>
    </match>
```

### Application Metrics

```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_connections = Gauge('active_connections', 'Active connections')
agent_processing_time = Histogram('agent_processing_seconds', 'Agent processing time', ['agent_name'])

# Middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    request_duration.observe(duration)
    
    return response
```

## Backup & Recovery

### Backup Strategy

```bash
#!/bin/bash
# backup.sh

# PostgreSQL Backup
pg_dump -h $DB_HOST -U $DB_USER -d netra > backup_$(date +%Y%m%d_%H%M%S).sql

# Upload to S3
aws s3 cp backup_*.sql s3://netra-backups/postgresql/

# ClickHouse Backup
clickhouse-client --query "BACKUP DATABASE netra_analytics TO '/backup/'"
aws s3 sync /backup/ s3://netra-backups/clickhouse/

# Redis Backup
redis-cli --rdb /backup/redis.rdb
aws s3 cp /backup/redis.rdb s3://netra-backups/redis/redis_$(date +%Y%m%d_%H%M%S).rdb
```

### Disaster Recovery Plan

```yaml
# dr-plan.yaml
disaster_recovery:
  rto: 4_hours  # Recovery Time Objective
  rpo: 1_hour   # Recovery Point Objective
  
  backup_schedule:
    postgresql:
      full: "0 2 * * *"  # Daily at 2 AM
      incremental: "0 */6 * * *"  # Every 6 hours
    
    clickhouse:
      full: "0 3 * * 0"  # Weekly on Sunday
      incremental: "0 */12 * * *"  # Every 12 hours
    
    redis:
      snapshot: "*/30 * * * *"  # Every 30 minutes
  
  recovery_procedures:
    - step: "Activate DR site"
      actions:
        - "Update DNS to point to DR region"
        - "Scale up DR infrastructure"
        - "Restore latest backups"
    
    - step: "Verify data integrity"
      actions:
        - "Run data validation scripts"
        - "Compare checksums"
        - "Verify replication lag"
    
    - step: "Application recovery"
      actions:
        - "Deploy application to DR cluster"
        - "Run smoke tests"
        - "Monitor for errors"
```

## Scaling Strategies

### Horizontal Scaling

```yaml
# scaling/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: netra-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: netra-backend
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 5
        periodSeconds: 15
```

### Vertical Scaling

```bash
# Vertical scaling for databases

# PostgreSQL
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET work_mem = '50MB';
SELECT pg_reload_conf();

# Redis
CONFIG SET maxmemory 16gb
CONFIG SET maxmemory-policy allkeys-lru
CONFIG REWRITE
```

## Security Hardening

### Security Checklist

```yaml
# security/checklist.yaml
security_requirements:
  network:
    - enable_network_policies: true
    - restrict_egress: true
    - use_private_subnets: true
    - implement_waf: true
  
  authentication:
    - enforce_mfa: true
    - rotate_secrets_regularly: true
    - use_service_accounts: true
    - implement_rbac: true
  
  encryption:
    - tls_everywhere: true
    - encrypt_at_rest: true
    - use_kms: true
    - rotate_certificates: true
  
  monitoring:
    - enable_audit_logging: true
    - implement_ids: true
    - monitor_anomalies: true
    - alert_on_violations: true
```

### Network Policies

```yaml
# security/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: netra-backend-policy
  namespace: netra-production
spec:
  podSelector:
    matchLabels:
      app: netra-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: netra-frontend
    - podSelector:
        matchLabels:
          app: nginx-ingress
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Operational Procedures

### Deployment Runbook

```markdown
# Deployment Runbook

## Pre-Deployment Checklist
- [ ] All tests passing
- [ ] Code review approved
- [ ] Database migrations ready
- [ ] Rollback plan prepared
- [ ] Monitoring alerts configured

## Deployment Steps

1. **Backup Current State**
   ```bash
   ./scripts/backup.sh
   ```

2. **Run Database Migrations**
   ```bash
   kubectl exec -it deployment/netra-backend -- alembic upgrade head
   ```

3. **Deploy Backend**
   ```bash
   kubectl set image deployment/netra-backend backend=netra/backend:$VERSION
   kubectl rollout status deployment/netra-backend
   ```

4. **Deploy Frontend**
   ```bash
   kubectl set image deployment/netra-frontend frontend=netra/frontend:$VERSION
   kubectl rollout status deployment/netra-frontend
   ```

5. **Verify Deployment**
   ```bash
   ./scripts/smoke-test.sh
   ```

## Rollback Procedure
```bash
kubectl rollout undo deployment/netra-backend
kubectl rollout undo deployment/netra-frontend
```
```

### Incident Response

```yaml
# incident-response.yaml
incident_response:
  severity_levels:
    P1:
      description: "Complete outage"
      response_time: 15_minutes
      escalation: immediate
    P2:
      description: "Major functionality impaired"
      response_time: 30_minutes
      escalation: 1_hour
    P3:
      description: "Minor functionality impaired"
      response_time: 2_hours
      escalation: 4_hours
    P4:
      description: "Low impact issue"
      response_time: 1_business_day
      escalation: optional
  
  response_team:
    on_call_engineer:
      responsibilities:
        - "Initial triage"
        - "Implement immediate fixes"
        - "Escalate if needed"
    
    incident_commander:
      responsibilities:
        - "Coordinate response"
        - "Communication"
        - "Decision making"
    
    subject_matter_expert:
      responsibilities:
        - "Technical guidance"
        - "Root cause analysis"
        - "Long-term fix"
```

## Troubleshooting Guide

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
kubectl top pods -n netra-production

# Check for memory leaks
kubectl exec -it deployment/netra-backend -- python -m tracemalloc

# Restart pods if needed
kubectl rollout restart deployment/netra-backend
```

#### Database Connection Issues
```bash
# Check database connectivity
kubectl exec -it deployment/netra-backend -- pg_isready -h $DB_HOST

# Check connection pool
kubectl exec -it deployment/netra-backend -- python -c "
from app.database import engine
print(engine.pool.status())
"

# Reset connections
kubectl exec -it deployment/netra-backend -- python -c "
from app.database import engine
engine.dispose()
"
```

#### WebSocket Connection Drops
```bash
# Check WebSocket connections
kubectl exec -it deployment/netra-backend -- python -c "
from app.services.websocket_manager import manager
print(manager.get_connection_stats())
"

# Check nginx configuration
kubectl exec -it deployment/nginx -- nginx -t

# Increase timeouts if needed
kubectl edit configmap nginx-config
```

### Performance Tuning

```python
# performance/tuning.py
# Database connection pooling
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_POOL_RECYCLE = 3600
SQLALCHEMY_POOL_PRE_PING = True
SQLALCHEMY_MAX_OVERFLOW = 40

# Redis connection pooling
REDIS_POOL = redis.ConnectionPool(
    max_connections=50,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 5,  # TCP_KEEPCNT
    }
)

# Async configuration
ASYNC_POOL_SIZE = 100
ASYNC_MAX_WORKERS = 50
```

### Health Checks

```bash
#!/bin/bash
# health-check.sh

# Backend health
curl -f http://api.netrasystems.ai/health || exit 1

# Frontend health
curl -f http://app.netrasystems.ai/api/health || exit 1

# Database health
pg_isready -h $DB_HOST || exit 1

# Redis health
redis-cli ping || exit 1

# WebSocket health
wscat -c ws://api.netrasystems.ai/ws?token=$TOKEN -x '{"type":"ping"}' || exit 1

echo "All systems healthy"
```