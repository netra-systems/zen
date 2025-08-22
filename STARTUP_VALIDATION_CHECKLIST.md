# Netra Apex Cold Start Validation Checklist

**Purpose:** Validate complete dev launcher cold start flow  
**Last Updated:** 2025-08-22  
**Validation Time:** ~2 minutes

## Pre-Startup Validation

### Environment Setup
- [ ] **Project Root Verified:** Navigate to `C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1`
- [ ] **Environment File Exists:** `.env` file present with required variables
- [ ] **Dependencies Installed:** Python packages and Node.js modules installed
- [ ] **Docker Services:** Local PostgreSQL, Redis, ClickHouse containers running

### Critical Environment Variables Check
```bash
# Verify these exist in .env
grep -E "(DATABASE_URL|REDIS_URL|CLICKHOUSE_URL)" .env
grep -E "(JWT_SECRET_KEY|SECRET_KEY)" .env  
grep -E "(CLICKHOUSE.*PASSWORD|REDIS_PASSWORD)" .env
```

## Startup Execution

### 1. Launch Dev Environment
```bash
python scripts/dev_launcher.py
```

**Expected Output Indicators:**
- [ ] "Starting services..." message appears
- [ ] No immediate Python import errors
- [ ] Service discovery initialization

### 2. Backend Service Validation
**Look for these success indicators:**
- [ ] "BACKEND Starting backend server" message
- [ ] Port allocation (usually 8000)
- [ ] "Backend started on port XXXX" success message
- [ ] Health check: `curl http://localhost:8000/health/` returns `{"status": "healthy"}`

### 3. Auth Service Validation  
**Look for these success indicators:**
- [ ] "AUTH Starting auth service" message
- [ ] Dynamic port allocation (8083-8090 range)
- [ ] "Auth service started on port XXXX" success message
- [ ] Service initialization without errors

### 4. Frontend Service Validation
**Look for these success indicators:**
- [ ] "FRONTEND Starting frontend" message  
- [ ] Next.js compilation starts
- [ ] Turbopack compilation completes
- [ ] "Frontend ready on port 3000" message
- [ ] No compilation errors

### 5. Database Connectivity Validation
**Check for successful connections:**
- [ ] **PostgreSQL:** "Database connected" or similar success message
- [ ] **Redis:** No Redis connection errors in logs
- [ ] **ClickHouse:** Connection established, tables accessible

## System Health Validation

### Service Availability Check
```bash
# Backend API
curl -f http://localhost:8000/health/

# Frontend (should load without errors)  
curl -f http://localhost:3000

# Auth service health (port may vary)
curl -f http://localhost:8084/health || curl -f http://localhost:8083/health
```

### Final Startup Confirmation
**Look for these final indicators:**
- [ ] **"System Ready"** message appears
- [ ] **All 10/10 startup checks passing**  
- [ ] **Total startup time < 15 seconds**
- [ ] **No critical errors in any service logs**

## Post-Startup Validation

### Login Flow Test
- [ ] Navigate to `http://localhost:3000`
- [ ] Dev login option available
- [ ] OAuth login options present
- [ ] Login process completes without errors

### WebSocket Connection Test
- [ ] Chat UI loads properly
- [ ] WebSocket connection establishes (check browser dev tools)
- [ ] No WebSocket connection errors

### Sample Interaction Test
- [ ] Send a test message in chat interface
- [ ] Receive appropriate response (even if mock/placeholder)
- [ ] No JavaScript errors in browser console

## Troubleshooting Quick Fixes

### If Backend Health Check Fails:
1. Verify endpoint: `curl http://localhost:8000/health/` (note trailing slash)
2. Check backend logs for startup errors
3. Verify port is not in use: `netstat -an | grep :8000`

### If ClickHouse Connection Fails:
1. Verify `.env` has: `CLICKHOUSE_DEFAULT_PASSWORD=netra_dev_password`
2. Check `dev_launcher/service_config.py` has `"secure": False` for local config
3. Confirm Docker ClickHouse container is running

### If Environment Variable Warnings:
1. Add to `.env`:
   ```
   REDIS_PASSWORD=
   CLICKHOUSE_DEFAULT_PASSWORD=netra_dev_password
   CLICKHOUSE_DEVELOPMENT_PASSWORD=netra_dev_password
   ```

## Success Criteria

**✅ COLD START SUCCESSFUL:** All checkboxes above are checked  
**✅ SYSTEM OPERATIONAL:** All three services running and responsive  
**✅ DEVELOPMENT READY:** Full development environment functional  

## Emergency Recovery

If startup completely fails:
1. **Kill all processes:** `pkill -f "python.*dev_launcher"`
2. **Clean ports:** Check and kill processes on 3000, 8000, 8083-8090
3. **Verify Docker:** Restart PostgreSQL/Redis/ClickHouse containers  
4. **Check logs:** Review startup logs for specific error patterns
5. **Retry:** Run dev launcher again after cleanup

---

**Validation Status:** ✅ VERIFIED (2025-08-22)  
**Next Review:** After any major service configuration changes