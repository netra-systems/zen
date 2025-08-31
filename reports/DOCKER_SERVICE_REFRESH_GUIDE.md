# Docker Service-Specific Refresh Guide

## Executive Summary
This guide provides EXACT commands to refresh individual services after changes. Use these instead of rebuilding everything to save time.

## 🎯 Quick Decision Tree
1. **Dockerfile changed?** → Full rebuild required
2. **docker-compose.yml changed?** → Recreate container
3. **Code changed?** → Depends on volume mounts
4. **Environment vars changed?** → Recreate container
5. **.dockerignore changed?** → Full rebuild required

---

## 📦 Frontend Service Refresh

### When Frontend Dockerfile Changes
```bash
# Stop frontend only
docker-compose --profile dev stop dev-frontend

# Rebuild frontend image (no cache)
docker-compose --profile dev build --no-cache dev-frontend

# Start frontend with new image
docker-compose --profile dev up -d dev-frontend

# Verify it's running
docker logs netra-dev-frontend --tail 50
```

### When Frontend Code Changes (package.json, next.config.ts, etc.)
```bash
# Since code is baked into image, must rebuild
docker-compose --profile dev build dev-frontend
docker-compose --profile dev up -d dev-frontend

# Check image size (MUST be <200MB)
docker images | grep frontend
```

### When Frontend Environment Variables Change
```bash
# Just recreate container (image doesn't change)
docker-compose --profile dev up -d --force-recreate dev-frontend
```

---

## 🔧 Backend Service Refresh

### When Backend Dockerfile Changes
```bash
# Stop backend
docker-compose --profile dev stop dev-backend

# Rebuild backend image
docker-compose --profile dev build --no-cache dev-backend

# Start backend with new image
docker-compose --profile dev up -d dev-backend

# Watch logs for startup
docker logs -f netra-dev-backend
```

### When Backend Code Changes
```bash
# Rebuild image (code is baked in)
docker-compose --profile dev build dev-backend
docker-compose --profile dev up -d dev-backend

# Verify health check passes
curl http://localhost:8000/health
```

### When Backend Dependencies Change (requirements.txt)
```bash
# Full rebuild required for dependency changes
docker-compose --profile dev build --no-cache dev-backend
docker-compose --profile dev up -d dev-backend
```

---

## 🔐 Auth Service Refresh

### When Auth Dockerfile Changes
```bash
# Stop auth service
docker-compose --profile dev stop dev-auth

# Rebuild auth image
docker-compose --profile dev build --no-cache dev-auth

# Start auth with new image
docker-compose --profile dev up -d dev-auth

# Verify health
curl http://localhost:8081/health
```

### When Auth Configuration Changes
```bash
# Recreate container with new env vars
docker-compose --profile dev up -d --force-recreate dev-auth

# Check service status
docker exec netra-dev-auth curl http://localhost:8081/health
```

---

## 🗄️ Database Services Refresh

### PostgreSQL Refresh
```bash
# WARNING: This will DELETE all data!
docker-compose --profile dev stop dev-postgres
docker volume rm netra-postgres-data  # DELETES DATA
docker-compose --profile dev up -d dev-postgres

# Wait for healthy state
docker exec netra-dev-postgres pg_isready -U netra
```

### Redis Refresh
```bash
# Stop and remove (data in memory anyway)
docker-compose --profile dev stop dev-redis
docker-compose --profile dev rm -f dev-redis
docker-compose --profile dev up -d dev-redis

# Test connection
docker exec netra-dev-redis redis-cli ping
```

### ClickHouse Refresh
```bash
# Stop and recreate
docker-compose --profile dev stop dev-clickhouse
docker-compose --profile dev up -d --force-recreate dev-clickhouse

# Verify it's running
docker exec netra-dev-clickhouse clickhouse-client --query "SELECT 1"
```

---

## 🔄 Dependency Order Refresh

When multiple services need refresh, follow this order:

```bash
# 1. Databases first (they have no dependencies)
docker-compose --profile dev up -d dev-postgres dev-redis dev-clickhouse

# 2. Wait for databases to be healthy
sleep 10  # Or use proper health checks

# 3. Auth service (depends on postgres/redis)
docker-compose --profile dev up -d dev-auth

# 4. Backend (depends on all above)
docker-compose --profile dev up -d dev-backend

# 5. Frontend (depends on backend/auth)
docker-compose --profile dev up -d dev-frontend
```

---

## 🚨 Emergency Full Refresh

When things are really broken:

```bash
# NUCLEAR OPTION - Deletes EVERYTHING
docker-compose --profile dev down -v  # Removes volumes too!
docker system prune -af --volumes      # Cleans everything
docker-compose --profile dev build --no-cache
docker-compose --profile dev up -d

# Verify all services running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## 📊 Verification Commands

After ANY refresh:

```bash
# Check all containers are running
docker ps | grep netra

# Check resource usage (should be under limits)
docker stats --no-stream

# Check specific service health
curl http://localhost:8000/health    # Backend
curl http://localhost:8081/health    # Auth
curl http://localhost:3000/api/health # Frontend

# Check logs for errors
docker-compose --profile dev logs --tail=20

# Check image sizes
docker images | grep netra
```

---

## ⚠️ Common Pitfalls

### 1. Forgetting to Stop Service First
```bash
# WRONG - might not pick up changes
docker-compose --profile dev up -d dev-backend

# RIGHT - ensures clean restart
docker-compose --profile dev stop dev-backend
docker-compose --profile dev up -d dev-backend
```

### 2. Not Clearing Build Cache When Needed
```bash
# If Dockerfile changed, MUST use --no-cache
docker-compose --profile dev build --no-cache service-name
```

### 3. Not Checking Dependencies
```bash
# Backend depends on auth - if auth is down, backend fails
# Always check dependency health first:
docker ps | grep auth
```

### 4. Cached Environment Variables
```bash
# Environment changes need --force-recreate
docker-compose --profile dev up -d --force-recreate service-name
```

---

## 🔍 Troubleshooting Refresh Issues

### Service Won't Start After Refresh
```bash
# Check logs
docker logs netra-dev-[service] --tail 100

# Check if port is already in use
netstat -an | grep [PORT]

# Force remove and recreate
docker-compose --profile dev rm -f dev-[service]
docker-compose --profile dev up -d dev-[service]
```

### Image Size Increased After Refresh
```bash
# Check what's in the image
docker run --rm -it [image-name] sh
ls -la /
du -sh /*

# Rebuild with proper .dockerignore
docker-compose --profile dev build --no-cache [service]
```

### Health Checks Failing
```bash
# Check health check command directly
docker exec [container] [health-check-command]

# Increase start_period if service needs more time
# Edit docker-compose.yml healthcheck section
```

---

## 📝 Service Refresh Checklist

Before refreshing any service:
- [ ] Commit or stash local changes
- [ ] Check which services depend on this one
- [ ] Verify .dockerignore is correct
- [ ] Confirm Docker has enough resources
- [ ] Note current image sizes for comparison

After refresh:
- [ ] Service container is running
- [ ] Health check passes
- [ ] Logs show no errors
- [ ] Image size is reasonable
- [ ] Dependent services still working
- [ ] Resource usage within limits

---

## 🔗 Related Documentation
- [Docker Stability Learnings](DOCKER_STABILITY_LEARNINGS.md)
- [Docker Volume Optimization](SPEC/docker_volume_optimization.xml)
- [Frontend Docker Optimization](SPEC/frontend_docker_optimization.xml)

---
**Last Updated:** August 31, 2025
**Status:** ✅ COMPREHENSIVE GUIDE