# WebSocket Docker Troubleshooting Guide

> **Quick Reference**: This guide helps diagnose and resolve WebSocket connection issues in Docker development environments.

## Table of Contents

- [Quick Diagnosis Commands](#quick-diagnosis-commands)
- [Common Issues & Solutions](#common-issues--solutions)
- [Configuration Checklist](#configuration-checklist)
- [Testing Tools](#testing-tools)
- [Advanced Troubleshooting](#advanced-troubleshooting)
- [Prevention & Maintenance](#prevention--maintenance)

---

## Quick Diagnosis Commands

Run these commands first to quickly identify the issue:

```bash
# 1. Test WebSocket configuration
python scripts/test_docker_websocket_fix.py

# 2. Check backend service health
curl http://localhost:8000/health

# 3. Verify Docker services are running
docker-compose -f docker-compose.dev.yml ps

# 4. Check environment variables
docker exec backend env | grep -E "(AUTH_BYPASS|WEBSOCKET|ENVIRONMENT)"

# 5. View WebSocket logs
docker logs backend | grep -i websocket
```

---

## Common Issues & Solutions

### 🔴 Issue 1: WebSocket Connection Refused

**Symptoms:**
- Browser error: `WebSocket connection to 'ws://localhost:8000/ws' failed`
- Console error: `ERR_CONNECTION_REFUSED`
- Frontend unable to connect to backend

**Diagnosis:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify Docker services
docker-compose -f docker-compose.dev.yml ps

# Check port mapping
netstat -an | grep :8000
```

**Solutions:**
1. **Start Docker services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Check for port conflicts:**
   ```bash
   # Kill any process using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

3. **Restart with clean state:**
   ```bash
   docker-compose -f docker-compose.dev.yml down
   docker-compose -f docker-compose.dev.yml up --build
   ```

4. **Verify port mapping in docker-compose.dev.yml:**
   ```yaml
   backend:
     ports:
       - "8000:8000"  # Ensure this mapping exists
   ```

---

### 🔴 Issue 2: Authentication Required Error

**Symptoms:**
- WebSocket connection closed with code 1008
- Error: `Authentication required: Use Authorization header`
- Authentication bypass not working

**Diagnosis:**
```bash
# Check environment variables
python scripts/test_docker_websocket_fix.py

# Verify auth bypass settings
docker exec backend env | grep AUTH_BYPASS
```

**Solutions:**
1. **Set authentication bypass environment variables:**
   ```bash
   # In .env.development.local
   ALLOW_DEV_AUTH_BYPASS=true
   WEBSOCKET_AUTH_BYPASS=true
   ENVIRONMENT=development
   ```

2. **Update docker-compose.dev.yml:**
   ```yaml
   backend:
     environment:
       - ALLOW_DEV_AUTH_BYPASS=true
       - WEBSOCKET_AUTH_BYPASS=true
       - ENVIRONMENT=development
   ```

3. **Restart services after environment changes:**
   ```bash
   docker-compose -f docker-compose.dev.yml restart
   ```

4. **Verify authentication bypass is active:**
   ```bash
   # Should show warnings about development auth bypass
   docker logs backend | grep -i "development auth bypass"
   ```

---

### 🔴 Issue 3: CORS Origin Not Allowed

**Symptoms:**
- Error: `WebSocket connection denied: Origin not allowed`
- CORS violation messages in logs
- Frontend can't establish WebSocket connection

**Diagnosis:**
```bash
# Check browser dev tools for origin header
# Look for origin value in Network tab WebSocket request

# Check CORS configuration
python -c "
from shared.cors_config import get_cors_origins
origins = get_cors_origins('development')
print('Allowed origins:', origins)
"
```

**Solutions:**
1. **Verify Docker service origins are included:**
   ```python
   # In shared/cors_config.py, ensure these exist in _get_development_origins():
   "http://frontend:3000",
   "http://backend:8000",
   "http://netra-frontend:3000",
   "http://netra-backend:8000",
   ```

2. **Add missing Docker bridge network IPs:**
   ```python
   # Docker bridge network IP ranges
   "http://172.17.0.1:3000",
   "http://172.17.0.1:8000",
   "http://172.18.0.1:3000",
   "http://172.18.0.1:8000",
   ```

3. **Ensure development environment is detected:**
   ```bash
   # Check environment detection
   docker exec backend python -c "
   from shared.cors_config import _detect_environment
   print('Detected environment:', _detect_environment())
   "
   ```

4. **Test CORS configuration:**
   ```bash
   python scripts/test_websocket_cors_comprehensive.py
   ```

---

### 🟡 Issue 4: Multiple Origin Headers

**Symptoms:**
- Warning: `Multiple different origin headers found`
- Inconsistent WebSocket connection behavior
- CORS validation sometimes fails

**Diagnosis:**
```bash
# Check for duplicate origin headers in browser dev tools
# Network tab → WebSocket request → Headers section

# Look for multiple Origin entries
```

**Solutions:**
1. **Verify resilient origin handling is implemented:**
   ```python
   # In netra_backend/app/core/websocket_cors.py
   # Should handle multiple identical origins gracefully
   ```

2. **Check for proxy or load balancer configuration issues:**
   ```bash
   # Review any reverse proxy configuration
   # Check if multiple proxies are adding origin headers
   ```

3. **Use development mode permissive handling:**
   ```python
   # Development mode should use first origin if multiples exist
   ```

---

### 🟡 Issue 5: Docker Service Discovery Issues

**Symptoms:**
- Services can't find each other by name
- Connection works with IP but not service name
- Intermittent connectivity issues

**Diagnosis:**
```bash
# Test service discovery
docker exec frontend ping backend
docker exec backend ping frontend

# Check Docker network
docker network ls
docker network inspect netra-core-generation-1_default
```

**Solutions:**
1. **Verify all services are on same Docker network:**
   ```bash
   docker-compose -f docker-compose.dev.yml down
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Use explicit network configuration:**
   ```yaml
   # In docker-compose.dev.yml
   networks:
     netra-network:
       driver: bridge
   
   services:
     backend:
       networks:
         - netra-network
     frontend:
       networks:
         - netra-network
   ```

3. **Add service aliases:**
   ```yaml
   backend:
     networks:
       netra-network:
         aliases:
           - netra-backend
           - api
   ```

---

## Configuration Checklist

### ✅ Environment Variables Check

**Backend (.env.development.local):**
- [ ] `ALLOW_DEV_AUTH_BYPASS=true`
- [ ] `WEBSOCKET_AUTH_BYPASS=true`
- [ ] `ENVIRONMENT=development`

**Frontend (.env.local):**
- [ ] `NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8000/ws`
- [ ] `NEXT_PUBLIC_API_URL=http://localhost:8000`
- [ ] `NEXT_PUBLIC_WS_URL=ws://localhost:8000`

**Docker Compose (docker-compose.dev.yml):**
- [ ] Backend service exposes port 8000
- [ ] Frontend service exposes port 3000
- [ ] Environment variables properly set
- [ ] Services on same network

### ✅ CORS Configuration Check

**In shared/cors_config.py:**
- [ ] Docker service names in development origins
- [ ] Bridge network IPs included
- [ ] Localhost variations covered
- [ ] Development environment detection working

### ✅ Authentication Configuration Check

**In netra_backend/app/websocket_core/auth.py:**
- [ ] Development auth bypass implemented
- [ ] Environment checks in place
- [ ] Warning logs for bypass mode
- [ ] Fallback security for production

---

## Testing Tools

### 1. Automated Configuration Test
```bash
# Comprehensive configuration validation
python scripts/test_docker_websocket_fix.py
```

### 2. E2E WebSocket Test
```bash
# End-to-end WebSocket functionality test
pytest tests/e2e/test_websocket_dev_docker_connection.py -v -s
```

### 3. CORS Validation Test
```bash
# CORS configuration and origin testing
python scripts/test_websocket_cors_comprehensive.py
```

### 4. Manual WebSocket Test
```bash
# Test WebSocket connection manually
wscat -c ws://localhost:8000/ws
```

### 5. Health Check Test
```bash
# Verify backend service availability
curl -v http://localhost:8000/health
```

---

## Advanced Troubleshooting

### Debug WebSocket Connection Flow

1. **Enable verbose logging:**
   ```bash
   # Add to backend environment
   LOG_LEVEL=DEBUG
   
   # Restart and check logs
   docker-compose -f docker-compose.dev.yml restart backend
   docker logs -f backend
   ```

2. **Test connection with curl:**
   ```bash
   # Test WebSocket endpoint with HTTP
   curl -v -H "Upgrade: websocket" \
        -H "Connection: Upgrade" \
        -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" \
        -H "Sec-WebSocket-Version: 13" \
        http://localhost:8000/ws
   ```

3. **Check middleware order:**
   ```python
   # In netra_backend/app/core/app_factory.py
   # Verify WebSocket middleware is applied before other middleware
   ```

### Network Troubleshooting

1. **Check Docker networking:**
   ```bash
   # List networks
   docker network ls
   
   # Inspect network details
   docker network inspect netra-core-generation-1_default
   ```

2. **Test internal connectivity:**
   ```bash
   # From frontend container to backend
   docker exec frontend curl http://backend:8000/health
   
   # From host to services
   curl http://localhost:8000/health
   curl http://localhost:3000
   ```

3. **Check port bindings:**
   ```bash
   # Verify ports are properly bound
   docker port backend
   docker port frontend
   ```

### Performance Troubleshooting

1. **Check resource usage:**
   ```bash
   # Monitor container resources
   docker stats
   ```

2. **Test WebSocket performance:**
   ```bash
   # Use WebSocket stress testing tools
   # Monitor connection latency and throughput
   ```

---

## Prevention & Maintenance

### Regular Maintenance Tasks

**Weekly:**
- [ ] Run `python scripts/test_docker_websocket_fix.py`
- [ ] Verify E2E WebSocket tests pass
- [ ] Check Docker container logs for warnings

**Monthly:**
- [ ] Review Docker CORS origins for new services
- [ ] Validate authentication bypass security
- [ ] Update documentation with any new issues

**Quarterly:**
- [ ] Audit authentication bypass logic
- [ ] Review Docker networking configuration
- [ ] Update troubleshooting procedures

### Best Practices

1. **Always test WebSocket configuration after changes:**
   ```bash
   # Run after any environment or Docker changes
   python scripts/test_docker_websocket_fix.py
   ```

2. **Use version control for configuration:**
   - Track changes to docker-compose files
   - Document environment variable changes
   - Keep troubleshooting steps updated

3. **Monitor logs proactively:**
   ```bash
   # Set up log monitoring for WebSocket issues
   docker logs -f backend | grep -E "(websocket|cors|auth)"
   ```

4. **Test in clean environments:**
   ```bash
   # Periodically test with clean Docker environment
   docker-compose -f docker-compose.dev.yml down -v
   docker-compose -f docker-compose.dev.yml up --build
   ```

---

## Quick Reference Commands

```bash
# Complete WebSocket Docker reset
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up --build -d
python scripts/test_docker_websocket_fix.py

# Check WebSocket connection manually
wscat -c ws://localhost:8000/ws

# View real-time WebSocket logs
docker logs -f backend | grep -i websocket

# Test CORS configuration
python -c "from shared.cors_config import get_cors_origins; print(get_cors_origins('development'))"

# Verify authentication bypass
docker exec backend python -c "
import os
print('ALLOW_DEV_AUTH_BYPASS:', os.getenv('ALLOW_DEV_AUTH_BYPASS'))
print('WEBSOCKET_AUTH_BYPASS:', os.getenv('WEBSOCKET_AUTH_BYPASS'))
print('ENVIRONMENT:', os.getenv('ENVIRONMENT'))
"
```

---

## Related Documentation

- [`SPEC/learnings/websocket_docker_fixes.xml`](../SPEC/learnings/websocket_docker_fixes.xml) - Complete fix documentation
- [`SPEC/websockets.xml`](../SPEC/websockets.xml) - WebSocket specification with Docker requirements
- [`shared/cors_config.py`](../shared/cors_config.py) - CORS configuration implementation
- [`netra_backend/app/websocket_core/auth.py`](../netra_backend/app/websocket_core/auth.py) - WebSocket authentication
- [`scripts/test_docker_websocket_fix.py`](../scripts/test_docker_websocket_fix.py) - Configuration validation script

---

*This guide is part of the Netra Apex AI Optimization Platform documentation. For additional help, run the diagnostic scripts or check the related specifications.*