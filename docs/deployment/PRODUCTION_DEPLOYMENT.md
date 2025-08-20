# Netra Apex - Production Deployment Guide

## Overview

This guide covers production deployment procedures for the Netra Apex AI Optimization Platform, focusing on enterprise-grade deployment with security, scalability, and reliability.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Production Environment Setup](#production-environment-setup)
- [Security Configuration](#security-configuration)
- [Database Setup](#database-setup)
- [Application Deployment](#application-deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Load Balancing & Scaling](#load-balancing--scaling)
- [Backup & Disaster Recovery](#backup--disaster-recovery)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Infrastructure Requirements

**Minimum Production Resources:**
- **CPU**: 4 vCPUs per service instance
- **Memory**: 8GB RAM per backend instance, 4GB per frontend
- **Storage**: 100GB+ for databases, 50GB for application logs
- **Network**: Load balancer with SSL termination
- **Database**: PostgreSQL 14+, ClickHouse, Redis cluster

**Recommended Production Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│                Load Balancer (HAProxy/NGINX)            │
│                     SSL Termination                     │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
    ┌───▼────┐                 ┌────▼────┐
    │Frontend│                 │ Backend │
    │(3 inst)│                 │(3 inst) │
    └────────┘                 └─────────┘
                                    │
    ┌──────────────────────────────┴──────────────────────┐
    │                                                     │
┌───▼───┐          ┌───────▼────┐          ┌────▼─────┐
│Postgres│         │ClickHouse │          │  Redis   │
│Cluster │         │  Cluster  │          │ Cluster  │
└────────┘         └────────────┘          └──────────┘
```

### Required Software

- **Docker** 20.10+ with Docker Compose
- **Kubernetes** 1.24+ (recommended for scaling)
- **Helm** 3.8+ (for K8s deployments)
- **Google Cloud SDK** (for GCP deployments)
- **PostgreSQL** 14+
- **Redis** 7+
- **ClickHouse** 22.8+

### Access Requirements

- **Google Cloud**: Project with billing enabled, necessary APIs enabled
- **SSL Certificates**: Valid SSL certificates for your domain
- **DNS Management**: Control over DNS records for your domain
- **Secrets Management**: Google Secret Manager or equivalent

## Production Environment Setup

### 1. Environment Configuration

**Critical Environment Variables:**

```env
# Production Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Domain Configuration
FRONTEND_URL=https://app.yourdomain.com
API_URL=https://api.yourdomain.com
ALLOWED_ORIGINS=https://app.yourdomain.com

# Security (CRITICAL: Generate strong values)
JWT_SECRET_KEY=<generate-256-bit-key>
FERNET_KEY=<generate-with-cryptography>
SECRET_KEY=<generate-strong-secret>
GOOGLE_CLIENT_ID=<production-oauth-client-id>
GOOGLE_CLIENT_SECRET=<production-oauth-client-secret>

# Database Configuration (Production)
DATABASE_URL=postgresql://netra_user:strong_password@postgres-cluster:5432/netra_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600

# ClickHouse Configuration
CLICKHOUSE_URL=clickhouse://netra_user:strong_password@clickhouse-cluster:9000/netra_analytics
CLICKHOUSE_MAX_CONNECTIONS=10

# Redis Configuration
REDIS_URL=redis://redis-cluster:6379/0
REDIS_MAX_CONNECTIONS=20

# LLM Provider Configuration (Production Keys)
GEMINI_API_KEY=<production-gemini-key>
OPENAI_API_KEY=<production-openai-key>  # Optional
ANTHROPIC_API_KEY=<production-anthropic-key>  # Optional

# Monitoring & Observability
SENTRY_DSN=<production-sentry-dsn>
PROMETHEUS_METRICS_ENABLED=true
GRAFANA_API_KEY=<grafana-api-key>

# Business Metrics
STRIPE_SECRET_KEY=<production-stripe-key>  # For payment processing
ANALYTICS_TRACKING_ID=<production-google-analytics>
```

### 2. Generate Production Secrets

```bash
# Generate secure keys
python -c "import secrets; print(secrets.token_urlsafe(32))"  # JWT_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # FERNET_KEY
python -c "import secrets; print(secrets.token_urlsafe(64))"  # SECRET_KEY
```

**CRITICAL**: Store these in Google Secret Manager, not in environment files:

```bash
# Store secrets in Google Secret Manager
gcloud secrets create netra-jwt-secret --data-file=jwt_secret.txt
gcloud secrets create netra-fernet-key --data-file=fernet_key.txt
gcloud secrets create netra-database-url --data-file=database_url.txt
```

## Security Configuration

### 1. SSL/TLS Setup

**Requirements:**
- Valid SSL certificate for your domain
- TLS 1.2+ only
- HSTS headers enabled
- Secure cookie settings

```nginx
# NGINX SSL Configuration
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
```

### 2. Authentication & Authorization

**OAuth 2.0 Production Setup:**

1. **Google OAuth Configuration:**
   ```bash
   # Create production OAuth client
   # Set authorized origins: https://app.yourdomain.com
   # Set authorized redirect URIs: https://api.yourdomain.com/api/auth/google/callback
   ```

2. **JWT Configuration:**
   ```python
   # Production JWT settings in app/core/configuration/auth.py
   JWT_ALGORITHM = "HS256"
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Short-lived for security
   JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
   ```

### 3. Network Security

```yaml
# Docker Compose Network Security
networks:
  netra-internal:
    driver: bridge
    internal: true  # No external access
  netra-external:
    driver: bridge

services:
  backend:
    networks:
      - netra-internal
      - netra-external
  
  postgres:
    networks:
      - netra-internal  # Database not exposed externally
```

## Database Setup

### 1. PostgreSQL Production Setup

```sql
-- Create production database
CREATE DATABASE netra_prod;
CREATE USER netra_user WITH ENCRYPTED PASSWORD 'strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE netra_prod TO netra_user;

-- Performance optimization
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_segments = 32;
ALTER SYSTEM SET checkpoint_completion_target = 0.7;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
```

```bash
# Run production migrations
python database_scripts/run_migrations.py --environment production

# Create database indexes for performance
python database_scripts/create_production_indexes.py
```

### 2. ClickHouse Production Setup

```sql
-- Create analytics database
CREATE DATABASE netra_analytics;

-- Create optimized tables for production
CREATE TABLE netra_analytics.workload_events (
    timestamp DateTime64,
    user_id UInt32,
    event_type LowCardinality(String),
    event_data String,
    cost_impact Decimal(10,2),
    optimization_type LowCardinality(String),
    INDEX idx_user_id user_id TYPE minmax GRANULARITY 8192,
    INDEX idx_event_type event_type TYPE set(100) GRANULARITY 8192
) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, user_id)
TTL timestamp + INTERVAL 2 YEAR;

-- Create materialized views for business metrics
CREATE MATERIALIZED VIEW netra_analytics.savings_summary
ENGINE = SummingMergeTree()
ORDER BY (user_id, toYYYYMM(timestamp))
AS SELECT
    user_id,
    toYYYYMM(timestamp) as month,
    sum(cost_impact) as total_savings,
    count() as optimization_count
FROM netra_analytics.workload_events
WHERE cost_impact > 0
GROUP BY user_id, month;
```

### 3. Redis Production Cluster

```bash
# Redis Cluster Configuration (redis.conf)
cluster-enabled yes
cluster-config-file nodes-6379.conf
cluster-node-timeout 5000
appendonly yes
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Application Deployment

### 1. Docker Production Images

**Backend Dockerfile.prod:**
```dockerfile
FROM python:3.11-slim

# Production optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install production dependencies
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash netra
USER netra

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health/ready || exit 1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Frontend Dockerfile.prod:**
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --only=production

COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.prod.conf /etc/nginx/nginx.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

### 2. Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - backend
      - frontend
    networks:
      - netra-external

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile.prod
    environment:
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
      - NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com/ws
    networks:
      - netra-external
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CLICKHOUSE_URL=${CLICKHOUSE_URL}
    depends_on:
      - postgres
      - redis
      - clickhouse
    networks:
      - netra-internal
      - netra-external
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=netra_prod
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgresql.prod.conf:/etc/postgresql/postgresql.conf
    networks:
      - netra-internal
    restart: unless-stopped

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    environment:
      - CLICKHOUSE_DB=netra_analytics
      - CLICKHOUSE_USER=${CLICKHOUSE_USER}
      - CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD}
    volumes:
      - clickhouse_data:/var/lib/clickhouse
      - ./clickhouse-config.xml:/etc/clickhouse-server/config.xml
    networks:
      - netra-internal
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server /etc/redis/redis.conf
    volumes:
      - redis_data:/data
      - ./redis.prod.conf:/etc/redis/redis.conf
    networks:
      - netra-internal
    restart: unless-stopped

volumes:
  postgres_data:
  clickhouse_data:
  redis_data:

networks:
  netra-internal:
    driver: bridge
    internal: true
  netra-external:
    driver: bridge
```

### 3. Deployment Commands

```bash
# Production deployment sequence
./deploy-production.sh
```

**deploy-production.sh:**
```bash
#!/bin/bash
set -e

echo "🚀 Starting Netra Apex Production Deployment..."

# 1. Pre-deployment checks
echo "🔍 Running pre-deployment checks..."
python scripts/pre_deployment_checks.py --environment production

# 2. Build production images
echo "🏗️ Building production images..."
docker-compose -f docker-compose.prod.yml build --no-cache

# 3. Database migrations
echo "📊 Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm backend python database_scripts/run_migrations.py

# 4. Deploy services
echo "🎯 Deploying services..."
docker-compose -f docker-compose.prod.yml up -d

# 5. Health checks
echo "🏥 Running health checks..."
sleep 30
python scripts/production_health_check.py --timeout 300

# 6. Post-deployment verification
echo "✅ Running post-deployment verification..."
python scripts/post_deployment_verification.py

echo "🎉 Production deployment completed successfully!"
```

## Monitoring & Observability

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'netra-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'netra-postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']

  - job_name: 'netra-redis'
    static_configs:
      - targets: ['redis_exporter:9121']
```

### 2. Grafana Dashboards

**Key Dashboards:**
- **Business Metrics**: Customer savings, ROI calculations, tier usage
- **System Performance**: Response times, throughput, error rates
- **Infrastructure**: Database performance, memory usage, CPU utilization
- **Security**: Authentication failures, rate limiting, suspicious activity

### 3. Alerting Rules

```yaml
# alerting-rules.yml
groups:
  - name: netra.rules
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: DatabaseConnectionPool
        expr: database_connections_active / database_connections_max > 0.8
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool near capacity"
          
      - alert: BusinessMetricFailure
        expr: rate(savings_calculation_errors[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Business metric calculation failures"
```

## Load Balancing & Scaling

### 1. NGINX Load Balancer Configuration

```nginx
# nginx.prod.conf
upstream netra_backend {
    least_conn;
    server backend_1:8000 max_fails=3 fail_timeout=30s;
    server backend_2:8000 max_fails=3 fail_timeout=30s;
    server backend_3:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

upstream netra_frontend {
    server frontend_1:3000;
    server frontend_2:3000;
    server frontend_3:3000;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://netra_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 2. Auto-scaling Configuration

```yaml
# kubernetes/hpa.yml
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
  maxReplicas: 10
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

## Backup & Disaster Recovery

### 1. Database Backup Strategy

```bash
# backup-script.sh
#!/bin/bash

BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -h postgres -U netra_user netra_prod > "$BACKUP_DIR/postgres_backup.sql"

# ClickHouse backup
clickhouse-backup create "netra_$(date +%Y%m%d_%H%M%S)"

# Upload to cloud storage
gsutil cp -r $BACKUP_DIR gs://netra-backups/

# Cleanup old backups (keep 30 days)
find /backups -type d -mtime +30 -exec rm -rf {} +
```

### 2. Disaster Recovery Plan

**RTO (Recovery Time Objective):** 4 hours
**RPO (Recovery Point Objective):** 1 hour

**Recovery Procedures:**

1. **Database Recovery:**
   ```bash
   # Restore PostgreSQL
   psql -h postgres -U netra_user netra_prod < backup.sql
   
   # Restore ClickHouse
   clickhouse-backup restore netra_20241220_143000
   ```

2. **Application Recovery:**
   ```bash
   # Redeploy from backup
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **DNS Failover:**
   ```bash
   # Update DNS to failover region
   gcloud dns record-sets transaction start --zone=production
   gcloud dns record-sets transaction remove --zone=production --name=api.yourdomain.com --type=A --ttl=300 --rrdatas=OLD_IP
   gcloud dns record-sets transaction add --zone=production --name=api.yourdomain.com --type=A --ttl=300 --rrdatas=NEW_IP
   gcloud dns record-sets transaction execute --zone=production
   ```

## Troubleshooting

### 1. Common Issues

#### High CPU Usage
```bash
# Check container resources
docker stats

# Check slow queries
docker exec postgres psql -U netra_user -d netra_prod -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Scale up if needed
docker-compose -f docker-compose.prod.yml up -d --scale backend=5
```

#### Memory Issues
```bash
# Check memory usage
free -h
docker exec backend python scripts/memory_profiler.py

# Optimize database connections
echo "max_connections = 200" >> postgresql.prod.conf
docker-compose restart postgres
```

#### Database Connection Issues
```bash
# Check connection pool
docker exec backend python scripts/check_db_connections.py

# Check database logs
docker logs postgres | tail -100

# Reset connections if needed
docker exec postgres psql -U netra_user -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';"
```

### 2. Performance Optimization

#### Backend Performance
```bash
# Enable performance profiling
export ENABLE_PROFILING=true

# Check agent response times
curl -H "Authorization: Bearer $TOKEN" "https://api.yourdomain.com/api/metrics/performance"

# Database query optimization
python scripts/analyze_slow_queries.py --environment production
```

#### Frontend Performance
```bash
# Check bundle size
npm run analyze

# Monitor Core Web Vitals
npm run lighthouse-ci

# CDN optimization
gsutil -m cp -r frontend/dist/* gs://netra-cdn/
```

### 3. Security Incidents

#### Authentication Issues
```bash
# Check failed login attempts
docker exec backend python scripts/security_audit.py --failed-logins

# Reset user sessions if needed
docker exec redis redis-cli FLUSHDB 1

# Rotate JWT secrets
python scripts/rotate_jwt_secret.py --environment production
```

#### Suspicious Activity
```bash
# Check access logs
docker logs nginx | grep -E "(404|403|401)" | tail -100

# Block suspicious IPs
iptables -A INPUT -s SUSPICIOUS_IP -j DROP

# Review security headers
curl -I https://api.yourdomain.com
```

## Production Deployment Checklist

### Pre-Deployment
- [ ] **Environment Variables**: All production secrets configured in Secret Manager
- [ ] **SSL Certificates**: Valid certificates installed and configured
- [ ] **Database**: Production database created with proper user permissions
- [ ] **DNS**: Domain configured to point to production infrastructure
- [ ] **Monitoring**: Prometheus, Grafana, and alerting configured
- [ ] **Backups**: Automated backup system configured and tested
- [ ] **Load Testing**: System tested under expected production load

### Deployment
- [ ] **Pre-deployment Checks**: All health checks passing
- [ ] **Database Migrations**: Applied successfully
- [ ] **Image Builds**: All containers built without errors
- [ ] **Service Deployment**: All services started successfully
- [ ] **Health Checks**: All endpoints responding correctly
- [ ] **WebSocket**: Real-time communication functioning
- [ ] **Authentication**: OAuth flow working correctly

### Post-Deployment
- [ ] **Monitoring**: All metrics being collected
- [ ] **Alerts**: Alert rules active and notifications working
- [ ] **Performance**: Response times within SLA targets
- [ ] **Security**: Security headers and HTTPS functioning
- [ ] **Business Metrics**: Revenue tracking and ROI calculations working
- [ ] **Documentation**: Deployment documented and team notified
- [ ] **Backup Verification**: First backup completed successfully

---

**Production Deployment Status**: This guide provides enterprise-grade deployment procedures for Netra Apex. Always test in staging environment before production deployment.

**Related Documentation**:
- [Staging Deployment Guide](STAGING_DEPLOYMENT_COMPLETE_GUIDE.md)
- [Monitoring Guide](../operations/MONITORING_GUIDE.md)
- [Security Documentation](../auth/AUTHENTICATION_SECURITY.md)
- [Configuration Guide](../configuration/CONFIGURATION_GUIDE.md)