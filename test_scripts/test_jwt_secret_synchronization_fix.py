#!/usr/bin/env python3
"""
JWT Secret Synchronization Fix Validation Script
=================================================

This script validates the JWT secret synchronization fix by testing:
1. SharedJWTSecretManager loading with enhanced logging
2. Auth service JWT secret loading 
3. Backend service JWT secret loading
4. Cross-service consistency validation
5. Staging environment specific testing

Author: Claude Code - JWT Synchronization Fix
Date: 2025-09-01
"""

import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Windows console compatibility
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")  # Set UTF-8 encoding

class JWTSecretSynchronizationValidator:
    """Comprehensive JWT secret synchronization validator."""
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }
    
    def log_test_result(self, test_name: str, passed: bool, details: str = None, error: str = None):
        """Log test result."""
        self.test_results["total_tests"] += 1
        if passed:
            self.test_results["passed_tests"] += 1
            print(f"[PASS] {test_name}")
        else:
            self.test_results["failed_tests"] += 1
            print(f"[FAIL] {test_name}")
        
        self.test_results["test_details"].append({
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        if details:
            print(f"  Details: {details}")
        if error:
            print(f"  Error: {error}")
    
    def test_shared_jwt_secret_manager_enhanced(self) -> bool:
        """Test enhanced SharedJWTSecretManager with comprehensive logging."""
        print("\n=== TESTING ENHANCED SHARED JWT SECRET MANAGER ===")
        
        try:
            from shared.jwt_secret_manager import SharedJWTSecretManager
            
            # Test 1: Get diagnostics
            try:
                diagnostics = SharedJWTSecretManager.get_secret_loading_diagnostics()
                print(f"JWT Secret Loading Diagnostics:")
                print(json.dumps(diagnostics, indent=2))
                
                self.log_test_result("SharedJWTSecretManager.get_secret_loading_diagnostics", True, 
                                   f"Environment: {diagnostics['current_environment']}")
            except Exception as e:
                self.log_test_result("SharedJWTSecretManager.get_secret_loading_diagnostics", False, error=str(e))
                return False
            
            # Test 2: Clear cache and load secret
            try:
                SharedJWTSecretManager.clear_cache()
                secret = SharedJWTSecretManager.get_jwt_secret()
                secret_hash = hashlib.sha256(secret.encode()).hexdigest()[:16]
                
                self.log_test_result("SharedJWTSecretManager.get_jwt_secret", True,
                                   f"Length: {len(secret)}, Hash: {secret_hash}")
                
                return secret
            except Exception as e:
                self.log_test_result("SharedJWTSecretManager.get_jwt_secret", False, error=str(e))
                return False
                
        except Exception as e:
            self.log_test_result("SharedJWTSecretManager import", False, error=str(e))
            return False
    
    def test_auth_service_jwt_secret(self) -> bool:
        """Test auth service JWT secret loading."""
        print("\n=== TESTING AUTH SERVICE JWT SECRET ===")
        
        try:
            from auth_service.auth_core.config import AuthConfig
            
            # Test auth config JWT secret
            try:
                secret = AuthConfig.get_jwt_secret()
                secret_hash = hashlib.sha256(secret.encode()).hexdigest()[:16]
                
                self.log_test_result("AuthConfig.get_jwt_secret", True,
                                   f"Length: {len(secret)}, Hash: {secret_hash}")
                
                return secret
            except Exception as e:
                self.log_test_result("AuthConfig.get_jwt_secret", False, error=str(e))
                return False
                
        except Exception as e:
            self.log_test_result("AuthConfig import", False, error=str(e))
            return False
    
    def test_backend_jwt_secret(self) -> bool:
        """Test backend JWT secret loading."""
        print("\n=== TESTING BACKEND JWT SECRET ===")
        
        try:
            from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
            
            # Test backend JWT secret
            try:
                secret = get_jwt_secret()
                secret_hash = hashlib.sha256(secret.encode()).hexdigest()[:16]
                
                self.log_test_result("Backend get_jwt_secret", True,
                                   f"Length: {len(secret)}, Hash: {secret_hash}")
                
                return secret
            except Exception as e:
                self.log_test_result("Backend get_jwt_secret", False, error=str(e))
                return False
                
        except Exception as e:
            self.log_test_result("Backend JWT secret import", False, error=str(e))
            return False
    
    def test_cross_service_synchronization(self, shared_secret, auth_secret, backend_secret) -> bool:
        """Test cross-service JWT secret synchronization."""
        print("\n=== TESTING CROSS-SERVICE SYNCHRONIZATION ===")
        
        if not shared_secret or not auth_secret or not backend_secret:
            self.log_test_result("Cross-service synchronization", False, 
                               error="One or more secrets failed to load")
            return False
        
        # Test shared vs auth
        if shared_secret == auth_secret:
            self.log_test_result("Shared vs Auth service sync", True,
                               "Secrets match")
        else:
            self.log_test_result("Shared vs Auth service sync", False,
                               f"Secrets differ - Shared: {len(shared_secret)} chars, Auth: {len(auth_secret)} chars")
            return False
        
        # Test shared vs backend
        if shared_secret == backend_secret:
            self.log_test_result("Shared vs Backend service sync", True,
                               "Secrets match")
        else:
            self.log_test_result("Shared vs Backend service sync", False,
                               f"Secrets differ - Shared: {len(shared_secret)} chars, Backend: {len(backend_secret)} chars")
            return False
        
        # Test auth vs backend
        if auth_secret == backend_secret:
            self.log_test_result("Auth vs Backend service sync", True,
                               "Secrets match")
        else:
            self.log_test_result("Auth vs Backend service sync", False,
                               f"Secrets differ - Auth: {len(auth_secret)} chars, Backend: {len(backend_secret)} chars")
            return False
        
        # All tests passed
        self.log_test_result("Complete cross-service synchronization", True,
                           "All services use identical JWT secrets")
        return True
    
    def test_staging_environment_consistency(self) -> bool:
        """Test staging environment specific consistency."""
        print("\n=== TESTING STAGING ENVIRONMENT CONSISTENCY ===")
        
        try:
            from shared.jwt_secret_manager import SharedJWTSecretManager
            from shared.isolated_environment import IsolatedEnvironment
            
            # Test force environment consistency
            try:
                staging_secret = SharedJWTSecretManager.force_environment_consistency("staging")
                secret_hash = hashlib.sha256(staging_secret.encode()).hexdigest()[:16]
                
                self.log_test_result("Force staging environment consistency", True,
                                   f"Length: {len(staging_secret)}, Hash: {secret_hash}")
                
                # Validate it's not a development secret
                if "development" in staging_secret.lower():
                    self.log_test_result("Staging secret validation", False,
                                       error="Using development secret in staging environment")
                    return False
                else:
                    self.log_test_result("Staging secret validation", True,
                                       "Not using development secret")
                
                # Test secret strength for staging
                if len(staging_secret) >= 32:
                    self.log_test_result("Staging secret strength", True,
                                       f"Secret is {len(staging_secret)} characters (>= 32 required)")
                else:
                    self.log_test_result("Staging secret strength", False,
                                       f"Secret is only {len(staging_secret)} characters (< 32 required)")
                    return False
                
                return staging_secret
                
            except Exception as e:
                self.log_test_result("Force staging environment consistency", False, error=str(e))
                return False
                
        except Exception as e:
            self.log_test_result("Staging consistency test setup", False, error=str(e))
            return False
    
    def test_jwt_validation_synchronization(self, secret: str) -> bool:
        """Test JWT validation synchronization using the secret."""
        print("\n=== TESTING JWT VALIDATION SYNCHRONIZATION ===")
        
        if not secret:
            self.log_test_result("JWT validation synchronization", False,
                               error="No secret provided")
            return False
        
        try:
            from shared.jwt_secret_manager import SharedJWTSecretManager
            
            # Test synchronization validation
            try:
                # Clear cache first
                SharedJWTSecretManager.clear_cache()
                
                # Run validation
                result = SharedJWTSecretManager.validate_synchronization()
                
                self.log_test_result("JWT synchronization validation", result,
                                   "Validation passed")
                
                return result
                
            except Exception as e:
                self.log_test_result("JWT synchronization validation", False, error=str(e))
                return False
                
        except Exception as e:
            self.log_test_result("JWT validation test setup", False, error=str(e))
            return False
    
    def run_all_tests(self) -> bool:
        """Run all JWT secret synchronization tests."""
        print("JWT SECRET SYNCHRONIZATION FIX VALIDATION")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test 1: Enhanced SharedJWTSecretManager
        shared_secret = self.test_shared_jwt_secret_manager_enhanced()
        
        # Test 2: Auth service JWT secret
        auth_secret = self.test_auth_service_jwt_secret()
        
        # Test 3: Backend JWT secret  
        backend_secret = self.test_backend_jwt_secret()
        
        # Test 4: Cross-service synchronization
        sync_result = self.test_cross_service_synchronization(shared_secret, auth_secret, backend_secret)
        
        # Test 5: Staging environment consistency
        staging_secret = self.test_staging_environment_consistency()
        
        # Test 6: JWT validation synchronization
        if shared_secret:
            validation_result = self.test_jwt_validation_synchronization(shared_secret)
        else:
            validation_result = False
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY:")
        print(f"Total tests: {self.test_results['total_tests']}")
        print(f"Passed: {self.test_results['passed_tests']}")
        print(f"Failed: {self.test_results['failed_tests']}")
        print(f"Duration: {duration:.2f} seconds")
        
        success = self.test_results['failed_tests'] == 0
        
        if success:
            print("\n[SUCCESS] ALL TESTS PASSED!")
            print("JWT secret synchronization is working correctly.")
            
            if shared_secret:
                secret_hash = hashlib.sha256(shared_secret.encode()).hexdigest()[:16]
                print(f"Common JWT secret hash: {secret_hash}")
        else:
            print("\n[ERROR] SOME TESTS FAILED!")
            print("JWT secret synchronization issues detected.")
        
        return success


def main():
    """Main test execution."""
    validator = JWTSecretSynchronizationValidator()
    
    try:
        success = validator.run_all_tests()
        
        # Save detailed results
        results_file = Path("jwt_secret_sync_test_results.json")
        with open(results_file, 'w') as f:
            json.dump(validator.test_results, f, indent=2)
        
        print(f"\nDetailed results saved to: {results_file}")
        
        return success
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)