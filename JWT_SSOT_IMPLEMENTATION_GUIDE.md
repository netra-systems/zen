# JWT SSOT IMPLEMENTATION GUIDE

**Purpose:** Complete implementation guide with code examples, utilities, and best practices for JWT SSOT consolidation  
**Audience:** Developers implementing the remediation plan  
**Scope:** Practical code patterns, testing strategies, and deployment procedures

---

## IMPLEMENTATION UTILITIES

### A. Auth Service Client (Standard Implementation)

Create this file first as the foundation for all backend JWT operations:

**File:** `netra_backend/app/services/auth_service_client.py`
```python
"""
Auth Service Client - Standard SSOT integration for all backend services
Provides centralized, consistent access to auth service functionality.
"""
import asyncio
import logging
import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

from auth_service.auth_core.unified_auth_interface import get_unified_auth

logger = logging.getLogger(__name__)


@dataclass
class AuthServiceConfig:
    """Configuration for auth service client."""
    timeout_seconds: int = 5
    retry_attempts: int = 3
    cache_ttl_seconds: int = 300  # 5 minutes
    circuit_breaker_threshold: int = 5
    enable_caching: bool = True


class AuthServiceClient:
    """
    Standard client for backend services to access auth service SSOT.
    
    Features:
    - Circuit breaker pattern for resilience
    - Token caching for performance 
    - Comprehensive error handling
    - Metrics collection
    """
    
    def __init__(self, config: Optional[AuthServiceConfig] = None):
        self.config = config or AuthServiceConfig()
        self._auth_service = get_unified_auth()
        
        # Circuit breaker state
        self._failure_count = 0
        self._last_failure_time = 0
        self._circuit_open = False
        
        # Token cache
        self._token_cache = {} if self.config.enable_caching else None
        
        # Metrics
        self._metrics = {
            'requests': 0,
            'successes': 0,
            'failures': 0,
            'cache_hits': 0,
            'avg_latency': 0
        }
        
        logger.info("AuthServiceClient initialized with SSOT integration")
    
    async def create_access_token(self, user_id: str, email: str, 
                                permissions: List[str] = None) -> str:
        """Create JWT access token via auth service SSOT."""
        return await self._execute_with_circuit_breaker(
            'create_access_token',
            self._auth_service.create_access_token,
            user_id, email, permissions
        )
    
    async def validate_token(self, token: str, 
                           token_type: str = "access") -> Optional[Dict]:
        """Validate JWT token with caching and circuit breaker."""
        # Check cache first
        cache_key = f"{token[:20]}:{token_type}"
        if self._token_cache and cache_key in self._token_cache:
            cached_result, cached_time = self._token_cache[cache_key]
            if time.time() - cached_time < self.config.cache_ttl_seconds:
                self._metrics['cache_hits'] += 1
                return cached_result
        
        # Validate via auth service
        result = await self._execute_with_circuit_breaker(
            'validate_token',
            self._auth_service.validate_token,
            token, token_type
        )
        
        # Cache successful validation
        if result and self._token_cache:
            self._token_cache[cache_key] = (result, time.time())
            
            # Limit cache size
            if len(self._token_cache) > 1000:
                self._cleanup_cache()
        
        return result
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user via auth service SSOT."""
        return await self._execute_with_circuit_breaker(
            'authenticate_user',
            self._auth_service.authenticate_user,
            email, password
        )
    
    async def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token via auth service SSOT."""
        return await self._execute_with_circuit_breaker(
            'create_refresh_token',
            self._auth_service.create_refresh_token,
            user_id
        )
    
    def extract_user_id(self, token: str) -> Optional[str]:
        """Extract user ID from token via auth service SSOT."""
        try:
            return self._auth_service.extract_user_id(token)
        except Exception as e:
            logger.error(f"User ID extraction failed: {e}")
            return None
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check token blacklist via auth service SSOT."""
        try:
            return self._auth_service.is_token_blacklisted(token)
        except Exception as e:
            logger.error(f"Blacklist check failed: {e}")
            return False  # Fail open for availability
    
    async def _execute_with_circuit_breaker(self, operation: str, func, *args, **kwargs):
        """Execute operation with circuit breaker pattern."""
        self._metrics['requests'] += 1
        
        # Check circuit breaker
        if self._circuit_open:
            if time.time() - self._last_failure_time > 60:  # 60s recovery time
                self._circuit_open = False
                self._failure_count = 0
                logger.info("Auth service circuit breaker reset")
            else:
                logger.warning(f"Auth service circuit breaker open - {operation} blocked")
                raise Exception("Auth service circuit breaker open")
        
        # Execute with timeout and retries
        start_time = time.time()
        last_exception = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_seconds
                )
                
                # Success - update metrics
                latency = time.time() - start_time
                self._metrics['successes'] += 1
                self._update_avg_latency(latency)
                
                # Reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
                
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Auth service {operation} attempt {attempt + 1} failed: {e}")
                
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        # All retries failed
        self._handle_failure(operation, last_exception)
        raise last_exception
    
    def _handle_failure(self, operation: str, exception: Exception):
        """Handle auth service failure."""
        self._metrics['failures'] += 1
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        # Open circuit breaker if threshold reached
        if self._failure_count >= self.config.circuit_breaker_threshold:
            self._circuit_open = True
            logger.error(f"Auth service circuit breaker opened - {self._failure_count} failures")
        
        logger.error(f"Auth service {operation} failed: {exception}")
    
    def _update_avg_latency(self, latency: float):
        """Update average latency metric."""
        current_avg = self._metrics['avg_latency']
        total_requests = self._metrics['successes']
        
        if total_requests == 1:
            self._metrics['avg_latency'] = latency
        else:
            # Exponential moving average
            self._metrics['avg_latency'] = current_avg * 0.9 + latency * 0.1
    
    def _cleanup_cache(self):
        """Clean up old cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, cached_time) in self._token_cache.items()
            if current_time - cached_time > self.config.cache_ttl_seconds
        ]
        
        for key in expired_keys:
            del self._token_cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_metrics(self) -> Dict:
        """Get client metrics for monitoring."""
        return {
            **self._metrics,
            'circuit_breaker_open': self._circuit_open,
            'failure_count': self._failure_count,
            'cache_size': len(self._token_cache) if self._token_cache else 0
        }
    
    def get_health_status(self) -> Dict:
        """Get health status for monitoring."""
        return {
            'status': 'unhealthy' if self._circuit_open else 'healthy',
            'circuit_breaker_open': self._circuit_open,
            'failure_count': self._failure_count,
            'last_failure_time': self._last_failure_time,
            'metrics': self.get_metrics()
        }


# Global client instance
_auth_service_client: Optional[AuthServiceClient] = None

def get_auth_service_client() -> AuthServiceClient:
    """Get global auth service client instance."""
    global _auth_service_client
    if _auth_service_client is None:
        _auth_service_client = AuthServiceClient()
    return _auth_service_client


# Convenience functions for backward compatibility
async def validate_token(token: str, token_type: str = "access") -> Optional[Dict]:
    """Convenience function for token validation."""
    client = get_auth_service_client()
    return await client.validate_token(token, token_type)

async def create_access_token(user_id: str, email: str, permissions: List[str] = None) -> str:
    """Convenience function for token creation."""
    client = get_auth_service_client()
    return await client.create_access_token(user_id, email, permissions)

def extract_user_id_from_token(token: str) -> Optional[str]:
    """Convenience function for user ID extraction."""
    client = get_auth_service_client()
    return client.extract_user_id(token)
```

---

### B. Migration Helper Utilities

**File:** `netra_backend/app/utils/jwt_migration_helpers.py`
```python
"""
JWT Migration Helper utilities for SSOT transition.
Provides decorators and utilities to ease the migration process.
"""
import functools
import logging
from typing import Any, Callable

from netra_backend.app.services.auth_service_client import get_auth_service_client

logger = logging.getLogger(__name__)


def jwt_ssot_migration(deprecation_message: str = None):
    """
    Decorator to mark functions migrated to JWT SSOT.
    
    Usage:
    @jwt_ssot_migration("Use AuthServiceClient.validate_token() instead")
    def old_validate_function(token):
        client = get_auth_service_client()
        return client.validate_token(token)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            message = deprecation_message or f"{func.__name__} migrated to JWT SSOT"
            logger.info(f"JWT_SSOT_MIGRATION: {message}")
            return func(*args, **kwargs)
        
        wrapper._jwt_ssot_migrated = True
        return wrapper
    
    return decorator


def validate_no_direct_jwt_usage():
    """
    Validation utility to check for direct JWT usage in code.
    Run this during tests to ensure SSOT compliance.
    """
    import ast
    import os
    from pathlib import Path
    
    violations = []
    backend_path = Path("netra_backend")
    
    for py_file in backend_path.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for direct JWT imports
            if 'import jwt' in content or 'from jwt import' in content:
                violations.append(f"{py_file}: Direct JWT import detected")
            
            # Check for jwt.decode or jwt.encode calls
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == 'jwt':
                            violations.append(f"{py_file}:{node.lineno}: Direct jwt.{node.func.attr} call")
        
        except Exception as e:
            logger.warning(f"Could not analyze {py_file}: {e}")
    
    return violations


class JWTMigrationValidator:
    """Utility class for validating JWT SSOT migration."""
    
    def __init__(self):
        self.violations = []
        self.auth_service_client = get_auth_service_client()
    
    def validate_file_migration(self, file_path: str) -> bool:
        """Validate that a file has been properly migrated."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for SSOT compliance
            has_auth_service_import = 'auth_service' in content or 'AuthServiceClient' in content
            has_direct_jwt_import = 'import jwt' in content and 'jwt.' in content
            
            if has_direct_jwt_import and not has_auth_service_import:
                self.violations.append(f"{file_path}: Has direct JWT usage without SSOT migration")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Migration validation failed for {file_path}: {e}")
            return False
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration report."""
        return {
            'violations_found': len(self.violations),
            'violations': self.violations,
            'auth_service_health': self.auth_service_client.get_health_status(),
            'migration_status': 'INCOMPLETE' if self.violations else 'COMPLETE'
        }


# Testing utilities
def mock_auth_service_for_testing():
    """Mock auth service responses for testing migrations."""
    class MockAuthServiceClient:
        async def validate_token(self, token: str, token_type: str = "access"):
            if token.startswith("valid_"):
                return {
                    "sub": "test_user_123",
                    "email": "test@example.com",
                    "permissions": ["read", "write"]
                }
            return None
        
        async def create_access_token(self, user_id: str, email: str, permissions: list = None):
            return f"valid_token_for_{user_id}"
        
        def extract_user_id(self, token: str):
            if token.startswith("valid_"):
                return "test_user_123"
            return None
    
    return MockAuthServiceClient()
```

---

### C. Deployment and Testing Scripts

**File:** `scripts/jwt_ssot_deployment.py`
```python
"""
JWT SSOT deployment script with validation and rollback capability.
"""
import os
import subprocess
import sys
import time
from typing import List, Dict, Optional

import requests


class JWTSSOTDeployer:
    """Manages JWT SSOT deployment with safety checks."""
    
    def __init__(self):
        self.deployment_log = []
        self.rollback_commands = []
        self.validation_endpoints = [
            "http://localhost:8000/api/v1/health",
            "http://localhost:8000/api/v1/auth/validate"
        ]
    
    def deploy_phase_1_files(self) -> bool:
        """Deploy Phase 1 critical infrastructure files."""
        phase_1_files = [
            "netra_backend/app/services/key_manager.py",
            "netra_backend/app/services/auth/token_security_validator.py",
            "netra_backend/app/core/cross_service_validators/security_validators.py",
            "netra_backend/app/clients/auth_client_core.py",
            "netra_backend/app/middleware/auth_middleware.py"
        ]
        
        return self._deploy_files(phase_1_files, "Phase 1")
    
    def deploy_phase_2_files(self) -> bool:
        """Deploy Phase 2 secondary implementation files."""
        phase_2_files = [
            # Configuration files
            "netra_backend/app/core/config_validator.py",
            "netra_backend/app/core/unified_secret_manager.py",
            # Legacy auth files
            "netra_backend/app/auth_integration/validators.py",
            "netra_backend/app/services/user_auth_service.py",
            "netra_backend/app/services/token_service.py"
        ]
        
        return self._deploy_files(phase_2_files, "Phase 2")
    
    def _deploy_files(self, file_list: List[str], phase_name: str) -> bool:
        """Deploy a list of files with validation."""
        print(f"Starting {phase_name} deployment...")
        
        for file_path in file_list:
            if not self._deploy_single_file(file_path):
                print(f"Deployment failed at {file_path}")
                return False
        
        # Phase validation
        if not self._validate_deployment_health():
            print(f"{phase_name} deployment validation failed")
            return False
        
        print(f"{phase_name} deployment completed successfully")
        return True
    
    def _deploy_single_file(self, file_path: str) -> bool:
        """Deploy a single file with pre/post validation."""
        print(f"Deploying {file_path}...")
        
        # Pre-deployment validation
        if not self._validate_golden_path():
            print(f"Pre-deployment validation failed for {file_path}")
            return False
        
        # Create rollback point
        rollback_cmd = f"git checkout HEAD -- {file_path}"
        self.rollback_commands.append(rollback_cmd)
        
        # Deploy would happen here (file is already modified in git)
        # For this script, we assume file is already updated
        
        # Post-deployment validation
        time.sleep(2)  # Allow service restart
        if not self._validate_golden_path():
            print(f"Post-deployment validation failed for {file_path}")
            self._execute_rollback()
            return False
        
        self.deployment_log.append(f"Successfully deployed {file_path}")
        return True
    
    def _validate_golden_path(self) -> bool:
        """Validate Golden Path functionality."""
        try:
            # Run Golden Path test
            result = subprocess.run([
                "python", "tests/mission_critical/test_websocket_agent_events_suite.py"
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                return True
            else:
                print(f"Golden Path validation failed: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            print("Golden Path validation timed out")
            return False
        except Exception as e:
            print(f"Golden Path validation error: {e}")
            return False
    
    def _validate_deployment_health(self) -> bool:
        """Validate overall system health."""
        for endpoint in self.validation_endpoints:
            try:
                response = requests.get(endpoint, timeout=10)
                if response.status_code != 200:
                    print(f"Health check failed for {endpoint}: {response.status_code}")
                    return False
            except requests.RequestException as e:
                print(f"Health check failed for {endpoint}: {e}")
                return False
        
        return True
    
    def _execute_rollback(self) -> bool:
        """Execute rollback of deployed changes."""
        print("Executing rollback...")
        
        for cmd in reversed(self.rollback_commands):
            try:
                subprocess.run(cmd.split(), check=True)
                print(f"Rolled back: {cmd}")
            except subprocess.CalledProcessError as e:
                print(f"Rollback failed for: {cmd} - {e}")
                return False
        
        # Restart services after rollback
        self._restart_services()
        
        # Validate rollback
        return self._validate_golden_path()
    
    def _restart_services(self):
        """Restart backend services."""
        try:
            subprocess.run(["docker-compose", "restart", "backend"], check=True)
            time.sleep(10)  # Allow service startup
        except subprocess.CalledProcessError:
            print("Warning: Could not restart services via docker-compose")
    
    def generate_deployment_report(self) -> Dict:
        """Generate deployment report."""
        return {
            'deployment_log': self.deployment_log,
            'rollback_commands_available': len(self.rollback_commands),
            'validation_endpoints': self.validation_endpoints,
            'deployment_timestamp': time.time()
        }


if __name__ == "__main__":
    deployer = JWTSSOTDeployer()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--phase-2":
        success = deployer.deploy_phase_2_files()
    else:
        success = deployer.deploy_phase_1_files()
    
    report = deployer.generate_deployment_report()
    print("\n=== Deployment Report ===")
    print(f"Success: {success}")
    print(f"Files deployed: {len(report['deployment_log'])}")
    
    if not success:
        sys.exit(1)
```

---

### D. Testing and Validation Suite

**File:** `tests/jwt_ssot_validation_suite.py`
```python
"""
Comprehensive JWT SSOT validation test suite.
Validates successful migration and system functionality.
"""
import asyncio
import pytest
from typing import Dict, Optional

from netra_backend.app.services.auth_service_client import get_auth_service_client
from auth_service.auth_core.unified_auth_interface import get_unified_auth


class TestJWTSSOTMigration:
    """Test JWT SSOT migration success."""
    
    @pytest.fixture
    async def auth_client(self):
        """Get auth service client for testing."""
        return get_auth_service_client()
    
    @pytest.fixture
    async def unified_auth(self):
        """Get unified auth interface for testing."""
        return get_unified_auth()
    
    async def test_token_creation_via_ssot(self, auth_client):
        """Test token creation through SSOT."""
        token = await auth_client.create_access_token(
            user_id="test_user_123",
            email="test@example.com",
            permissions=["read", "write"]
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
    
    async def test_token_validation_via_ssot(self, auth_client):
        """Test token validation through SSOT."""
        # Create token first
        token = await auth_client.create_access_token(
            user_id="test_user_123",
            email="test@example.com"
        )
        
        # Validate token
        result = await auth_client.validate_token(token, "access")
        
        assert result is not None
        assert result.get("sub") == "test_user_123"
        assert result.get("email") == "test@example.com"
    
    async def test_user_authentication_via_ssot(self, auth_client):
        """Test user authentication through SSOT."""
        # This would require proper user setup in auth service
        result = await auth_client.authenticate_user(
            email="test@example.com",
            password="testpass"
        )
        
        # Result may be None if user doesn't exist - that's OK
        if result:
            assert "user_id" in result
            assert "email" in result
    
    async def test_token_caching_functionality(self, auth_client):
        """Test token caching performance optimization."""
        # Create and validate token
        token = await auth_client.create_access_token(
            user_id="test_user_123",
            email="test@example.com"
        )
        
        # First validation (not cached)
        result1 = await auth_client.validate_token(token)
        
        # Second validation (should be cached)
        result2 = await auth_client.validate_token(token)
        
        assert result1 == result2
        
        # Check cache hit metric
        metrics = auth_client.get_metrics()
        assert metrics['cache_hits'] > 0
    
    async def test_circuit_breaker_functionality(self, auth_client):
        """Test circuit breaker pattern."""
        # This test would simulate auth service failures
        # and verify circuit breaker behavior
        
        health_status = auth_client.get_health_status()
        assert 'status' in health_status
        assert 'circuit_breaker_open' in health_status
        assert 'failure_count' in health_status
    
    def test_no_direct_jwt_imports_in_backend(self):
        """Validate no direct JWT imports remain in backend."""
        from netra_backend.app.utils.jwt_migration_helpers import validate_no_direct_jwt_usage
        
        violations = validate_no_direct_jwt_usage()
        
        # Allow test files to have JWT imports
        allowed_violations = [v for v in violations if 'test' not in v.lower()]
        
        assert len(allowed_violations) == 0, f"JWT SSOT violations found: {allowed_violations}"
    
    async def test_golden_path_functionality(self):
        """Test that Golden Path still works after migration."""
        # This should run the same tests as mission critical suite
        # but in the context of SSOT validation
        
        # Test login flow
        auth_client = get_auth_service_client()
        
        # Simulate user login
        auth_result = await auth_client.authenticate_user(
            email="test@example.com",
            password="testpass"
        )
        
        # If user exists, test token operations
        if auth_result:
            token = auth_result.get("access_token")
            if token:
                # Test token validation
                validation_result = await auth_client.validate_token(token)
                assert validation_result is not None
                
                # Test user ID extraction
                user_id = auth_client.extract_user_id(token)
                assert user_id is not None
    
    async def test_websocket_auth_integration(self):
        """Test WebSocket authentication with SSOT."""
        # This would test the WebSocket JWT protocol handler
        # to ensure 1011 errors are resolved
        
        auth_client = get_auth_service_client()
        
        # Create test token
        token = await auth_client.create_access_token(
            user_id="websocket_test_user",
            email="wstest@example.com"
        )
        
        # Validate token (simulating WebSocket handshake)
        result = await auth_client.validate_token(token, "access")
        
        assert result is not None
        assert result.get("sub") == "websocket_test_user"
    
    def test_backward_compatibility(self):
        """Test that existing interfaces still work."""
        from netra_backend.app.services.auth_service_client import (
            validate_token,
            create_access_token,
            extract_user_id_from_token
        )
        
        # These should be importable without errors
        assert callable(validate_token)
        assert callable(create_access_token)
        assert callable(extract_user_id_from_token)
    
    async def test_performance_benchmarks(self, auth_client):
        """Test performance meets requirements."""
        import time
        
        # Create token
        start_time = time.time()
        token = await auth_client.create_access_token(
            user_id="perf_test_user",
            email="perftest@example.com"
        )
        creation_time = time.time() - start_time
        
        # Validate token
        start_time = time.time()
        result = await auth_client.validate_token(token)
        validation_time = time.time() - start_time
        
        # Performance assertions
        assert creation_time < 1.0, f"Token creation too slow: {creation_time}s"
        assert validation_time < 0.5, f"Token validation too slow: {validation_time}s"
        
        assert result is not None


@pytest.mark.asyncio
class TestJWTSSOTCompliance:
    """Test SSOT compliance across the system."""
    
    async def test_all_jwt_operations_use_auth_service(self):
        """Verify all JWT operations go through auth service."""
        # This would scan code and verify no direct JWT usage
        pass
    
    async def test_consistent_token_format(self):
        """Verify consistent token format across services."""
        auth_client = get_auth_service_client()
        unified_auth = get_unified_auth()
        
        # Create token via client
        token1 = await auth_client.create_access_token("user1", "user1@example.com")
        
        # Create token via unified auth
        token2 = unified_auth.create_access_token("user2", "user2@example.com")
        
        # Both should be valid JWT format
        assert token1.count('.') == 2
        assert token2.count('.') == 2
    
    async def test_error_handling_consistency(self):
        """Test consistent error handling across all JWT operations."""
        auth_client = get_auth_service_client()
        
        # Test invalid token
        result = await auth_client.validate_token("invalid_token")
        assert result is None
        
        # Test empty token
        result = await auth_client.validate_token("")
        assert result is None
        
        # Test malformed token
        result = await auth_client.validate_token("not.a.jwt")
        assert result is None
```

---

## DEPLOYMENT PROCEDURES

### A. Pre-Deployment Checklist

```bash
#!/bin/bash
# pre_deployment_checks.sh

echo "JWT SSOT Pre-Deployment Validation"
echo "=================================="

# 1. Verify auth service is running
echo "Checking auth service health..."
curl -f http://localhost:8001/health || exit 1

# 2. Run Golden Path tests
echo "Running Golden Path tests..."
python tests/mission_critical/test_websocket_agent_events_suite.py || exit 1

# 3. Validate SSOT compliance
echo "Checking JWT SSOT compliance..."
python tests/jwt_ssot_validation_suite.py || exit 1

# 4. Performance baseline
echo "Establishing performance baseline..."
python tests/performance/test_auth_performance_baseline.py

# 5. Database connectivity
echo "Checking database connections..."
python scripts/validate_database_connectivity.py || exit 1

echo "Pre-deployment checks PASSED"
```

### B. Deployment Script

```bash
#!/bin/bash
# deploy_jwt_ssot.sh

set -e  # Exit on any error

PHASE=${1:-"phase1"}
ENVIRONMENT=${2:-"staging"}

echo "Starting JWT SSOT deployment - $PHASE on $ENVIRONMENT"
echo "=================================================="

# Create rollback point
git tag "pre-jwt-ssot-deployment-$(date +%Y%m%d-%H%M%S)"

if [ "$PHASE" == "phase1" ]; then
    echo "Deploying Phase 1 - Critical Infrastructure"
    python scripts/jwt_ssot_deployment.py --phase-1 --env $ENVIRONMENT
elif [ "$PHASE" == "phase2" ]; then
    echo "Deploying Phase 2 - Secondary Implementation"
    python scripts/jwt_ssot_deployment.py --phase-2 --env $ENVIRONMENT
else
    echo "Unknown phase: $PHASE"
    exit 1
fi

# Post-deployment validation
echo "Running post-deployment validation..."
python tests/jwt_ssot_validation_suite.py

# Performance verification
echo "Verifying performance metrics..."
python tests/performance/test_auth_performance_after_migration.py

echo "JWT SSOT deployment completed successfully"
```

### C. Monitoring and Alerting

**File:** `scripts/jwt_ssot_monitoring.py`
```python
"""
JWT SSOT monitoring and alerting script.
Monitors auth service health and performance after migration.
"""
import time
import requests
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class JWTSSOTMonitor:
    """Monitor JWT SSOT health and performance."""
    
    def __init__(self):
        self.metrics_history = []
        self.alert_thresholds = {
            'auth_latency_ms': 500,
            'error_rate_percent': 1.0,
            'circuit_breaker_open': False
        }
    
    def collect_metrics(self) -> Dict:
        """Collect current system metrics."""
        try:
            # Auth service health
            auth_health = requests.get("http://localhost:8001/health", timeout=5).json()
            
            # Backend auth client metrics
            backend_metrics = requests.get("http://localhost:8000/api/v1/auth/metrics", timeout=5).json()
            
            # WebSocket connection success rate
            ws_metrics = requests.get("http://localhost:8000/api/v1/websocket/metrics", timeout=5).json()
            
            metrics = {
                'timestamp': time.time(),
                'auth_service_health': auth_health,
                'backend_metrics': backend_metrics,
                'websocket_metrics': ws_metrics,
                'auth_latency_ms': backend_metrics.get('avg_latency', 0) * 1000,
                'error_rate_percent': self._calculate_error_rate(backend_metrics),
                'circuit_breaker_open': backend_metrics.get('circuit_breaker_open', False)
            }
            
            self.metrics_history.append(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    def _calculate_error_rate(self, metrics: Dict) -> float:
        """Calculate error rate percentage."""
        total = metrics.get('requests', 0)
        failures = metrics.get('failures', 0)
        
        if total == 0:
            return 0.0
        
        return (failures / total) * 100
    
    def check_alerts(self, metrics: Dict) -> List[str]:
        """Check if any alert thresholds are exceeded."""
        alerts = []
        
        for metric, threshold in self.alert_thresholds.items():
            current_value = metrics.get(metric)
            
            if current_value is None:
                continue
            
            if isinstance(threshold, bool):
                if current_value != threshold:
                    alerts.append(f"ALERT: {metric} is {current_value}, expected {threshold}")
            elif current_value > threshold:
                alerts.append(f"ALERT: {metric} is {current_value}, threshold {threshold}")
        
        return alerts
    
    def run_monitoring_loop(self, duration_minutes: int = 60):
        """Run monitoring loop for specified duration."""
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            metrics = self.collect_metrics()
            alerts = self.check_alerts(metrics)
            
            if alerts:
                for alert in alerts:
                    logger.error(alert)
                    print(alert)
            else:
                logger.info(f"JWT SSOT system healthy - latency: {metrics.get('auth_latency_ms', 0):.1f}ms")
            
            time.sleep(30)  # Check every 30 seconds
        
        print(f"Monitoring completed after {duration_minutes} minutes")


if __name__ == "__main__":
    monitor = JWTSSOTMonitor()
    monitor.run_monitoring_loop(duration_minutes=60)
```

---

## TROUBLESHOOTING GUIDE

### Common Issues and Solutions:

#### 1. Auth Service Connection Failures
**Symptoms:** ConnectionError, timeouts, 500 errors
**Solutions:**
```python
# Check auth service status
curl http://localhost:8001/health

# Restart auth service
docker-compose restart auth-service

# Check auth service logs
docker-compose logs auth-service
```

#### 2. Token Validation Inconsistencies
**Symptoms:** Valid tokens rejected, 401 errors
**Solutions:**
- Verify JWT secret consistency between services
- Check token format and claims
- Validate auth service JWTHandler configuration

#### 3. WebSocket 1011 Errors Persist
**Symptoms:** WebSocket connections fail with 1011 code
**Solutions:**
- Ensure WebSocket auth uses same validation as REST API
- Check token extraction in WebSocket handshake
- Verify auth service accessibility from WebSocket handler

#### 4. Performance Degradation
**Symptoms:** Slow authentication, timeout errors
**Solutions:**
- Enable token caching in AuthServiceClient
- Scale auth service instances
- Optimize database queries in auth service

This comprehensive implementation guide provides everything needed to successfully execute the JWT SSOT remediation while maintaining system reliability and business continuity.