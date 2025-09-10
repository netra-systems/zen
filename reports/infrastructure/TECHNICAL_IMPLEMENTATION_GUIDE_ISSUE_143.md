# Technical Implementation Guide: GitHub Issue #143 Infrastructure Fixes

**OBJECTIVE:** Provide step-by-step implementation guidance for critical infrastructure remediation  
**SCOPE:** P0 and P1 priority fixes with specific commands and validation  
**AUDIENCE:** Engineering team implementing the remediation plan

## 🚨 P0 CRITICAL IMPLEMENTATIONS (Execute Immediately)

### 1. Redis Timeout Configuration Fix ⚠️ IMMEDIATE ACTION REQUIRED

**ISSUE:** 30-second Redis timeout in GCP WebSocket initialization causing health endpoint failures.

**FILE TO MODIFY:** `/netra_backend/app/websocket_core/gcp_initialization_validator.py`

**CURRENT PROBLEMATIC CODE (around line 139):**
```python
self.readiness_checks['redis'] = ServiceReadinessCheck(
    name='redis',
    validator=self._check_redis_ready,
    timeout_seconds=30.0,  # ❌ TOO LONG - causes health endpoint timeouts
    retry_count=3,
    retry_delay=1.0,
    is_critical=False
)
```

**REQUIRED FIX:**
```python
# File: netra_backend/app/websocket_core/gcp_initialization_validator.py

class GCPWebSocketInitializationValidator:
    def _configure_redis_check(self, environment: str, is_gcp: bool):
        """Configure Redis readiness check with environment-appropriate timeouts."""
        
        if is_gcp and environment in ['staging', 'production']:
            # Health endpoints need fast timeouts in GCP
            timeout = 3.0
            retry_count = 2
            retry_delay = 0.5
            description = "Fast Redis check for GCP health endpoints"
        elif environment == 'development':
            # Local development can be more lenient
            timeout = 10.0
            retry_count = 3
            retry_delay = 1.0
            description = "Development Redis check with longer timeout"
        else:
            # Default reasonable timeout
            timeout = 5.0
            retry_count = 3
            retry_delay = 0.5
            description = "Standard Redis readiness check"
        
        self.readiness_checks['redis'] = ServiceReadinessCheck(
            name='redis',
            validator=self._check_redis_ready,
            timeout_seconds=timeout,  # ✅ FIXED: Environment-appropriate timeout
            retry_count=retry_count,
            retry_delay=retry_delay,
            is_critical=False,  # Allow degraded mode
            description=description
        )
```

**IMPLEMENTATION STEPS:**

1. **Backup Current File:**
```bash
cp netra_backend/app/websocket_core/gcp_initialization_validator.py \
   netra_backend/app/websocket_core/gcp_initialization_validator.py.backup
```

2. **Apply the Fix:**
```bash
# Open file for editing
code netra_backend/app/websocket_core/gcp_initialization_validator.py

# Look for line ~139 where Redis timeout is configured
# Replace 30.0 with environment-appropriate logic as shown above
```

3. **Validate the Fix:**
```bash
# Run the Redis timeout test to verify fix
python -m pytest netra_backend/tests/unit/websocket_core/test_redis_timeout_fix_unit.py -xvs

# Expected: Tests should now PASS instead of failing
```

4. **Deploy and Test:**
```bash
# Deploy to staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local --service backend

# Test health endpoint
curl -w "%{time_total}\n" https://your-staging-url/health/ready
# Should respond in < 8 seconds consistently
```

**VALIDATION CHECKLIST:**
- [ ] Test passes: `test_redis_timeout_configuration_staging_environment`
- [ ] Health endpoint responds in < 8 seconds
- [ ] No timeout errors in deployment logs
- [ ] WebSocket connections still work normally

### 2. Complete WebSocket Protocol Deployment Fix

**ISSUE:** Frontend/backend version mismatch causing WebSocket authentication failures in staging.

**STATUS CHECK:**
```bash
# Check current deployment status
python scripts/deploy_to_gcp.py --project netra-staging --status

# Check if deployment completed successfully
gcloud run services describe netra-backend-staging --region us-central1 --format="value(status.latestReadyRevisionName)"
```

**IF DEPLOYMENT FAILED or INCOMPLETE:**

1. **Complete Backend Deployment:**
```bash
# Ensure clean build and deploy
python scripts/deploy_to_gcp.py --project netra-staging --build-local --service backend --force-rebuild
```

2. **Force Frontend Redeploy:**
```bash
# Navigate to frontend directory
cd frontend

# Force rebuild with cache invalidation
npm run build -- --no-cache

# Deploy with cache busting
npm run deploy:staging -- --invalidate-cache

# Verify deployed version contains correct WebSocket protocol
curl -s https://your-staging-frontend-url/_next/static/js/main.js | grep -o "jwt-auth.*encodedToken"
```

3. **Verify WebSocket Protocol Format:**
```bash
# Test WebSocket connection with correct protocol
python scripts/test_websocket_protocol.py --environment staging --protocol "jwt-auth,jwt.test-token"
```

**VALIDATION CHECKLIST:**
- [ ] Backend deployment completed successfully
- [ ] Frontend deployed with cache invalidation
- [ ] WebSocket protocol format verified in deployed bundle
- [ ] WebSocket authentication succeeds in staging
- [ ] No 1011 WebSocket errors in logs

### 3. Emergency State Registry Scope Bug Verification

**STATUS:** ✅ **ALREADY FIXED** in commit `93442498d`, but needs validation

**VERIFICATION STEPS:**

1. **Confirm Fix is Deployed:**
```bash
# Check current branch and commits
git log --oneline -5 | grep "state_registry scope"

# Verify fix is in current deployment
git show 93442498d --stat
```

2. **Run Validation Tests:**
```bash
# Test that reproduces the original bug - should now PASS
python -m pytest netra_backend/tests/unit/websocket_core/test_state_registry_scope_bug.py -xvs

# Expected output: Tests should PASS (bug fixed)
# Previous output: NameError: name 'state_registry' is not defined
```

3. **End-to-End WebSocket Validation:**
```bash
# Test complete WebSocket connection flow
python -m pytest tests/e2e/test_websocket_connection_complete_flow.py -xvs

# Monitor WebSocket connections in staging
python scripts/websocket_connection_monitor.py --environment staging --duration 60s
```

**VALIDATION CHECKLIST:**
- [ ] Scope bug test passes (no NameError)
- [ ] WebSocket connections succeed in staging
- [ ] State registry properly accessible throughout connection lifecycle
- [ ] No connection failure spikes in monitoring

## 🔥 P1 INFRASTRUCTURE IMPLEMENTATIONS (Next Week)

### 4. GCP Load Balancer Header Forwarding Fix

**ISSUE:** GCP Load Balancer stripping authentication headers for WebSocket connections.

**TERRAFORM FILE:** `/terraform-gcp-staging/load-balancer.tf`

**CURRENT CONFIGURATION ANALYSIS:**
```bash
# First, examine current configuration
cat terraform-gcp-staging/load-balancer.tf | grep -A 20 -B 5 "websocket\|/ws"

# Check current header forwarding rules
terraform show | grep -A 10 -B 10 "header"
```

**REQUIRED TERRAFORM CHANGES:**

1. **Update URL Map Configuration:**
```hcl
# File: terraform-gcp-staging/load-balancer.tf

resource "google_compute_url_map" "default" {
  name            = "netra-staging-url-map"
  description     = "URL map for Netra staging environment"
  default_service = google_compute_backend_service.backend.self_link

  # ADD: WebSocket-specific path matcher
  host_rule {
    hosts        = ["your-staging-domain.com"]
    path_matcher = "websocket-matcher"
  }

  path_matcher {
    name            = "websocket-matcher"
    default_service = google_compute_backend_service.backend.self_link

    # WebSocket paths with header forwarding
    path_rule {
      paths   = ["/ws", "/websocket"]
      service = google_compute_backend_service.backend.self_link
      
      # CRITICAL: Header forwarding for WebSocket authentication
      header_action {
        # Forward Authorization header
        request_headers_to_add {
          header_name  = "X-Original-Authorization"
          header_value = "{http_authorization}"
          replace      = false
        }
        
        # Forward WebSocket protocol header
        request_headers_to_add {
          header_name  = "X-Original-WebSocket-Protocol"
          header_value = "{http_sec_websocket_protocol}"
          replace      = false
        }
        
        # Preserve original headers
        request_headers_to_remove = []
      }
    }

    # Regular API paths (existing configuration)
    path_rule {
      paths   = ["/api/*", "/health/*"]
      service = google_compute_backend_service.backend.self_link
    }
  }
}

# ADD: Backend service configuration for WebSocket support
resource "google_compute_backend_service" "websocket_backend" {
  name                  = "netra-staging-websocket-backend"
  description           = "Backend service for WebSocket connections"
  protocol              = "HTTP"
  timeout_sec           = 86400  # 24 hours for long WebSocket connections
  enable_cdn           = false   # Disable CDN for WebSocket
  load_balancing_scheme = "EXTERNAL"

  backend {
    group           = google_compute_region_network_endpoint_group.backend.self_link
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
  }

  # WebSocket-specific health check
  health_checks = [google_compute_health_check.websocket.self_link]

  # Custom headers for WebSocket support
  custom_request_headers = [
    "X-WebSocket-Support: enabled",
    "X-Load-Balancer: gcp-staging"
  ]
}

# ADD: WebSocket health check
resource "google_compute_health_check" "websocket" {
  name                = "netra-staging-websocket-health"
  description         = "Health check for WebSocket backend"
  timeout_sec         = 10
  check_interval_sec  = 30
  unhealthy_threshold = 3
  healthy_threshold   = 2

  http_health_check {
    request_path         = "/health"
    port                 = "8000"
    host                 = "your-staging-domain.com"
    proxy_header         = "PROXY_V1"
  }
}
```

2. **Validate and Apply Terraform Changes:**
```bash
# Navigate to terraform directory
cd terraform-gcp-staging

# Initialize Terraform (if needed)
terraform init

# Validate configuration
terraform validate

# Plan changes - review carefully
terraform plan -out=websocket-headers.tfplan

# Apply changes (after review)
terraform apply websocket-headers.tfplan
```

3. **Verify Header Forwarding:**
```bash
# Test header forwarding with curl
curl -H "Authorization: Bearer test-token" \
     -H "Sec-WebSocket-Protocol: jwt-auth" \
     -H "Upgrade: websocket" \
     -H "Connection: Upgrade" \
     -v https://your-staging-domain.com/ws

# Check backend logs for received headers
gcloud logging read 'resource.type="cloud_run_revision" AND jsonPayload.message~"Authorization\|WebSocket-Protocol"' --limit=10
```

**VALIDATION CHECKLIST:**
- [ ] Terraform plan shows header forwarding additions
- [ ] Terraform apply completes without errors
- [ ] Load balancer configuration updated successfully
- [ ] Authorization headers reach backend service
- [ ] WebSocket protocol headers preserved
- [ ] WebSocket authentication success rate improves

### 5. Test Infrastructure Restoration

**ISSUE:** Mission-critical tests disabled due to Docker/GCP integration failures.

**AFFECTED TEST PATTERN:**
```bash
# Find all commented-out require_docker_services decorators
grep -r "# @require_docker_services" tests/ netra_backend/tests/

# Find tests that should be using real services but aren't
grep -r "@pytest.mark.skip.*docker\|@pytest.mark.skip.*integration" tests/
```

**PHASE 1: Docker Service Integration Fix**

1. **Restore Docker Compose for Testing:**
```bash
# Ensure Docker services are defined for testing
cat > test-services.docker-compose.yml << EOF
version: '3.8'
services:
  postgres-test:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: netra_test
      POSTGRES_USER: netra_test
      POSTGRES_PASSWORD: test_password
    ports:
      - "5433:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U netra_test"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis-test:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  auth-service-test:
    build:
      context: .
      dockerfile: dockerfiles/auth.test.alpine.Dockerfile
    environment:
      - ENVIRONMENT=test
      - JWT_SECRET_KEY=test-secret-key
      - POSTGRES_HOST=postgres-test
      - REDIS_HOST=redis-test
    ports:
      - "8001:8000"
    depends_on:
      postgres-test:
        condition: service_healthy
      redis-test:
        condition: service_healthy
EOF
```

2. **Fix Test Service Management:**
```bash
# Update UnifiedDockerManager for test services
# File: test_framework/unified_docker_manager.py

class UnifiedDockerManager:
    def start_test_services(self):
        """Start Docker services required for testing."""
        try:
            # Start test-specific compose file
            subprocess.run([
                'docker', 'compose', 
                '-f', 'test-services.docker-compose.yml',
                'up', '-d', '--wait'
            ], check=True)
            
            # Wait for health checks
            self._wait_for_test_services_ready()
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start test services: {e}")
            return False
    
    def _wait_for_test_services_ready(self):
        """Wait for all test services to be healthy."""
        services = ['postgres-test', 'redis-test', 'auth-service-test']
        for service in services:
            # Check service health status
            self._wait_for_service_health(service)
```

**PHASE 2: Re-enable Real Service Tests**

1. **Restore require_docker_services Decorators:**
```bash
# Create script to restore decorators
cat > scripts/restore_test_decorators.py << 'EOF'
#!/usr/bin/env python3
import os
import re

def restore_decorators():
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Restore commented decorators
                restored = re.sub(
                    r'# @require_docker_services\(\)',
                    '@require_docker_services()',
                    content
                )
                
                if restored != content:
                    with open(filepath, 'w') as f:
                        f.write(restored)
                    print(f"Restored decorators in: {filepath}")

if __name__ == "__main__":
    restore_decorators()
EOF

python scripts/restore_test_decorators.py
```

2. **Validate Test Infrastructure:**
```bash
# Test Docker service startup
python -c "
from test_framework.unified_docker_manager import UnifiedDockerManager
manager = UnifiedDockerManager()
success = manager.start_test_services()
print(f'Test services started: {success}')
"

# Run a sample integration test
python -m pytest tests/integration/test_database_connection.py -xvs --real-services

# Run mission critical tests with real services
python tests/unified_test_runner.py --real-services --category mission_critical
```

**PHASE 3: CI Pipeline Integration**

1. **Update CI Configuration:**
```yaml
# .github/workflows/test.yml (or equivalent)
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: netra_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run integration tests
        run: |
          python tests/unified_test_runner.py --real-services --category integration
      - name: Run mission critical tests
        run: |
          python tests/unified_test_runner.py --real-services --category mission_critical
```

**VALIDATION CHECKLIST:**
- [ ] Docker services start successfully for tests
- [ ] `@require_docker_services()` decorators restored
- [ ] Integration tests pass with real services
- [ ] Mission critical tests run without false success
- [ ] CI pipeline includes real service testing
- [ ] No test bypassing or mocking in critical paths

### 6. Import System Stability Fix

**ISSUE:** Import system instability during resource cleanup in Cloud Run causing "time not defined" errors.

**ROOT CAUSE:** Dynamic imports failing during garbage collection and memory pressure.

**IMPLEMENTATION STRATEGY:**

1. **Replace Dynamic Imports with Static Patterns:**

```python
# File: netra_backend/app/websocket_core/error_handlers.py

# BEFORE (PROBLEMATIC - Dynamic imports):
import importlib
import sys

def handle_websocket_error(error):
    try:
        # Dynamic import can fail during cleanup
        time_module = importlib.import_module('time')
        datetime_module = importlib.import_module('datetime')
        
        timestamp = time_module.time()
        # ... error handling
    except ImportError as e:
        # Import failure during resource cleanup
        raise RuntimeError("Import system unstable") from e

# AFTER (FIXED - Static imports):
import time
import datetime
import logging
from typing import Optional, Any

# Pre-import and cache critical modules at module level
_CRITICAL_MODULES = {
    'time': time,
    'datetime': datetime,
    'logging': logging
}

class ImportStabilityManager:
    """Manages stable access to critical modules during resource cleanup."""
    
    def __init__(self):
        # Pre-cache module references
        self._time = time
        self._datetime = datetime
        self._logging = logging
    
    def get_current_timestamp(self) -> float:
        """Get current timestamp with fallback protection."""
        try:
            return self._time.time()
        except (AttributeError, NameError):
            # Fallback if module reference corrupted
            import time as time_fallback
            return time_fallback.time()
    
    def log_error(self, message: str, error: Exception):
        """Log error with stability protection."""
        try:
            self._logging.error(f"{message}: {error}")
        except (AttributeError, NameError):
            # Fallback logging
            print(f"ERROR: {message}: {error}")

# Global stability manager
_stability_manager = ImportStabilityManager()

def handle_websocket_error(error: Exception) -> Optional[str]:
    """Handle WebSocket errors with import stability."""
    try:
        timestamp = _stability_manager.get_current_timestamp()
        error_id = f"ws_error_{int(timestamp)}"
        
        _stability_manager.log_error(
            f"WebSocket error [{error_id}]", error
        )
        
        return error_id
        
    except Exception as fallback_error:
        # Last resort error handling
        print(f"CRITICAL: Error handler failed: {fallback_error}")
        return None
```

2. **Implement Module Preloading:**

```python
# File: netra_backend/app/core/module_preloader.py

"""Module preloader for import stability in Cloud Run environments."""

import sys
import time
import datetime
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, Set

class ModulePreloader:
    """Preloads and caches critical modules to prevent import failures."""
    
    def __init__(self):
        self._preloaded_modules: Dict[str, Any] = {}
        self._critical_modules = [
            'time', 'datetime', 'json', 'uuid', 'asyncio', 
            'logging', 'sys', 'os', 'threading', 'weakref'
        ]
    
    def preload_critical_modules(self):
        """Preload all critical modules at startup."""
        for module_name in self._critical_modules:
            try:
                if module_name in sys.modules:
                    self._preloaded_modules[module_name] = sys.modules[module_name]
                    logging.info(f"Preloaded module: {module_name}")
            except Exception as e:
                logging.warning(f"Failed to preload {module_name}: {e}")
    
    def get_module(self, module_name: str) -> Any:
        """Get preloaded module with fallback."""
        if module_name in self._preloaded_modules:
            return self._preloaded_modules[module_name]
        
        # Fallback import
        try:
            module = __import__(module_name)
            self._preloaded_modules[module_name] = module
            return module
        except ImportError:
            raise ImportError(f"Module {module_name} not available")

# Global preloader instance
_module_preloader = ModulePreloader()

def preload_modules_for_cloud_run():
    """Initialize module preloader for Cloud Run stability."""
    _module_preloader.preload_critical_modules()
    logging.info("Module preloading completed for Cloud Run")

def get_stable_module(name: str) -> Any:
    """Get module with stability guarantees."""
    return _module_preloader.get_module(name)
```

3. **Update Application Startup:**

```python
# File: netra_backend/app/core/app_factory.py

from netra_backend.app.core.module_preloader import preload_modules_for_cloud_run

def create_app():
    """Create FastAPI application with Cloud Run optimizations."""
    
    # CRITICAL: Preload modules before any other initialization
    preload_modules_for_cloud_run()
    
    app = FastAPI(title="Netra Apex API")
    
    # Continue with normal app initialization...
    setup_middleware(app)
    setup_routes(app)
    
    return app
```

4. **Update Error Handlers:**

```python
# Update all error handlers to use stable imports
# File: netra_backend/app/websocket_core/connection_handler.py

from netra_backend.app.core.module_preloader import get_stable_module

class ConnectionHandler:
    def __init__(self):
        # Get stable references at initialization
        self._time = get_stable_module('time')
        self._logging = get_stable_module('logging')
        self._json = get_stable_module('json')
    
    async def handle_error(self, error: Exception):
        """Handle connection errors with import stability."""
        try:
            timestamp = self._time.time()
            error_data = {
                'timestamp': timestamp,
                'error': str(error),
                'type': type(error).__name__
            }
            
            self._logging.error(
                f"Connection error: {self._json.dumps(error_data)}"
            )
            
        except Exception as handler_error:
            # Fallback error logging
            print(f"CRITICAL: Error handler failed: {handler_error}")
```

**VALIDATION CHECKLIST:**
- [ ] All dynamic imports replaced with static patterns
- [ ] Module preloader implemented and integrated
- [ ] Error handlers use stable module references  
- [ ] Application startup includes module preloading
- [ ] Load testing shows no import failures under pressure
- [ ] WebSocket error handling stable during resource cleanup

## Validation Commands Summary

### Quick Validation Suite
```bash
# P0 Critical validations
python -m pytest netra_backend/tests/unit/websocket_core/test_redis_timeout_fix_unit.py -xvs
python -m pytest netra_backend/tests/unit/websocket_core/test_state_registry_scope_bug.py -xvs
curl -w "%{time_total}\n" https://your-staging-url/health/ready

# P1 Infrastructure validations  
terraform validate && terraform plan
python tests/unified_test_runner.py --real-services --category integration
python scripts/websocket_load_test.py --concurrent 10 --duration 60s

# End-to-end Golden Path validation
python -m pytest tests/e2e/test_golden_path_complete_user_flow.py -xvs
```

### Comprehensive Validation Suite
```bash
# Complete infrastructure validation
./scripts/run_full_infrastructure_validation.sh

# Performance and stability testing
./scripts/run_performance_validation.sh

# Business functionality validation
./scripts/run_golden_path_validation.sh
```

## Emergency Contacts and Escalation

**If Critical Issues Arise:**

1. **Immediate Rollback:**
   ```bash
   # Rollback deployment
   python scripts/deploy_to_gcp.py --project netra-staging --rollback
   
   # Rollback Terraform changes
   terraform apply -target=google_compute_url_map.default -var-file=previous_state.tfvars
   ```

2. **Monitor System Health:**
   ```bash
   # Health check monitoring
   watch -n 5 'curl -w "%{time_total}\n" -s https://your-staging-url/health'
   
   # WebSocket connection monitoring  
   python scripts/websocket_health_monitor.py --alerts-enabled
   ```

3. **Communication:**
   - [ ] Notify engineering team of implementation status
   - [ ] Update GitHub issue #143 with progress
   - [ ] Document any deviations from plan

---

**Implementation Guide Version:** 1.0  
**Last Updated:** 2025-09-10  
**Estimated Implementation Time:** P0 fixes: 4-6 hours, P1 fixes: 2-3 days  
**Next Review:** After each P0 fix completion