#!/usr/bin/env python3
"""
Staging JWT Secret Consistency Fix Script
==========================================

This script implements the emergency fix identified in the Five Whys analysis:
Ensures JWT secret consistency between auth service and backend service in staging.

Business Impact: Restores $120K+ MRR by fixing WebSocket authentication failures
Technical Impact: Restores 95%+ authentication success rate (from 62-63%)

CRITICAL: Run this script in staging environment only.
"""

import asyncio
import hashlib
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

import httpx
from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_jwt_secret_manager, get_unified_jwt_secret

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Staging environment constants
STAGING_AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"
STAGING_BACKEND_URL = "https://api.staging.netrasystems.ai"
GCP_PROJECT = "netra-staging"


class StagingJWTSecretFixer:
    """Fixes JWT secret consistency issues in staging environment."""
    
    def __init__(self):
        self.env = get_env()
        self.jwt_manager = get_jwt_secret_manager()
        self.environment = self.env.get("ENVIRONMENT", "unknown")
        
        # Safety check - only run in staging
        if self.environment.lower() != "staging":
            raise ValueError(f"This script only runs in staging environment. Current: {self.environment}")
        
        logger.info("Staging JWT Secret Consistency Fixer initialized")
    
    def calculate_secret_hash(self, secret: str) -> str:
        """Calculate safe hash of JWT secret for comparison."""
        return hashlib.sha256(secret.encode()).hexdigest()[:16]
    
    async def check_auth_service_health(self) -> Dict[str, Any]:
        """Check if auth service is accessible and healthy."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{STAGING_AUTH_SERVICE_URL}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    return {
                        "accessible": True,
                        "healthy": health_data.get("status") == "healthy",
                        "data": health_data
                    }
                else:
                    return {
                        "accessible": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e)
            }
    
    async def check_backend_service_health(self) -> Dict[str, Any]:
        """Check if backend service is accessible and healthy."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{STAGING_BACKEND_URL}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    return {
                        "accessible": True,
                        "healthy": health_data.get("status") == "healthy",
                        "data": health_data
                    }
                else:
                    return {
                        "accessible": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e)
            }
    
    def get_current_jwt_secret_status(self) -> Dict[str, Any]:
        """Get current JWT secret configuration status."""
        try:
            # Get unified JWT secret
            unified_secret = get_unified_jwt_secret()
            secret_hash = self.calculate_secret_hash(unified_secret)
            
            # Get debug info from JWT manager
            debug_info = self.jwt_manager.get_debug_info()
            
            # Check available secret sources
            available_secrets = {}
            for secret_name in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET"]:
                secret_value = self.env.get(secret_name)
                available_secrets[secret_name] = {
                    "available": secret_value is not None,
                    "length": len(secret_value) if secret_value else 0,
                    "hash": self.calculate_secret_hash(secret_value) if secret_value else None
                }
            
            return {
                "unified_secret_available": True,
                "unified_secret_hash": secret_hash,
                "unified_secret_length": len(unified_secret),
                "available_secrets": available_secrets,
                "debug_info": debug_info
            }
            
        except Exception as e:
            return {
                "unified_secret_available": False,
                "error": str(e)
            }
    
    async def test_token_generation_validation_loop(self) -> Dict[str, Any]:
        """Test complete token generation and validation cycle."""
        try:
            # Step 1: Generate token with auth service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{STAGING_AUTH_SERVICE_URL}/auth/dev-login", json={
                    "email": "staging-e2e-user-001@test.local",
                    "provider": "test"
                })
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "step": "token_generation",
                        "error": f"Auth service returned {response.status_code}: {response.text}"
                    }
                
                token_data = response.json()
                test_token = token_data.get("access_token")
                
                if not test_token:
                    return {
                        "success": False,
                        "step": "token_generation",
                        "error": "No access token returned from auth service"
                    }
            
            # Step 2: Validate token with auth service (baseline)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{STAGING_AUTH_SERVICE_URL}/auth/validate", json={
                    "token": test_token,
                    "token_type": "access"
                })
                
                auth_validation_success = response.status_code == 200
                auth_validation_data = response.json() if response.status_code == 200 else response.text
            
            # Step 3: Validate token with backend service (via auth client)
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            
            auth_client = AuthServiceClient()
            backend_validation_result = await auth_client.validate_token(test_token)
            backend_validation_success = (
                backend_validation_result is not None and 
                backend_validation_result.get("valid", False)
            )
            
            return {
                "success": auth_validation_success and backend_validation_success,
                "token_generated": True,
                "auth_validation": {
                    "success": auth_validation_success,
                    "data": auth_validation_data
                },
                "backend_validation": {
                    "success": backend_validation_success,
                    "data": backend_validation_result
                },
                "cross_service_consistency": auth_validation_success and backend_validation_success
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def force_jwt_secret_refresh(self) -> Dict[str, Any]:
        """Force refresh of JWT secrets by clearing caches and reloading."""
        try:
            logger.info("Forcing JWT secret refresh...")
            
            # Clear JWT manager cache
            self.jwt_manager.clear_cache()
            
            # Reload environment
            import importlib
            from shared import isolated_environment
            importlib.reload(isolated_environment)
            
            # Reinitialize JWT manager
            from shared.jwt_secret_manager import get_jwt_secret_manager
            self.jwt_manager = get_jwt_secret_manager()
            
            # Validate new configuration
            new_status = self.get_current_jwt_secret_status()
            
            return {
                "success": new_status["unified_secret_available"],
                "new_status": new_status
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_gcp_secret_manager_versions(self) -> Dict[str, Any]:
        """Check GCP Secret Manager for JWT secret versions."""
        try:
            import subprocess
            
            # Check JWT_SECRET_STAGING versions
            result = subprocess.run([
                "gcloud", "secrets", "versions", "list", "jwt-secret-staging",
                "--project", GCP_PROJECT, "--format", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                versions = json.loads(result.stdout)
                return {
                    "success": True,
                    "secret_name": "jwt-secret-staging",
                    "versions": len(versions),
                    "latest_version": versions[0] if versions else None,
                    "all_versions": versions
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def deploy_service_with_secret_refresh(self, service: str) -> Dict[str, Any]:
        """Deploy service with explicit secret refresh."""
        try:
            logger.info(f"Deploying {service} service with secret refresh...")
            
            # Deploy with secret validation
            result = subprocess.run([
                "python", "scripts/deploy_to_gcp.py",
                "--project", GCP_PROJECT,
                "--service", service,
                "--check-secrets",
                "--force-secret-refresh"
            ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Deployment timeout (10 minutes)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_comprehensive_diagnosis(self) -> Dict[str, Any]:
        """Run comprehensive diagnosis of JWT secret consistency."""
        logger.info("Running comprehensive JWT secret consistency diagnosis...")
        
        diagnosis = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self.environment,
            "steps": {}
        }
        
        # Step 1: Check service health
        logger.info("Step 1: Checking service health...")
        auth_health = await self.check_auth_service_health()
        backend_health = await self.check_backend_service_health()
        
        diagnosis["steps"]["service_health"] = {
            "auth_service": auth_health,
            "backend_service": backend_health
        }
        
        # Step 2: Check JWT secret configuration
        logger.info("Step 2: Checking JWT secret configuration...")
        jwt_status = self.get_current_jwt_secret_status()
        diagnosis["steps"]["jwt_configuration"] = jwt_status
        
        # Step 3: Check GCP Secret Manager
        logger.info("Step 3: Checking GCP Secret Manager...")
        gcp_status = self.check_gcp_secret_manager_versions()
        diagnosis["steps"]["gcp_secrets"] = gcp_status
        
        # Step 4: Test token generation and validation
        logger.info("Step 4: Testing token generation and validation...")
        token_test = await self.test_token_generation_validation_loop()
        diagnosis["steps"]["token_validation_test"] = token_test
        
        # Overall assessment
        services_healthy = (
            auth_health.get("accessible", False) and 
            backend_health.get("accessible", False)
        )
        
        jwt_configured = jwt_status.get("unified_secret_available", False)
        token_validation_works = token_test.get("cross_service_consistency", False)
        
        diagnosis["overall_assessment"] = {
            "services_healthy": services_healthy,
            "jwt_configured": jwt_configured,
            "token_validation_works": token_validation_works,
            "issue_confirmed": services_healthy and jwt_configured and not token_validation_works
        }
        
        return diagnosis
    
    async def run_emergency_fix(self) -> Dict[str, Any]:
        """Run emergency fix to restore JWT secret consistency."""
        logger.info("Starting emergency JWT secret consistency fix...")
        
        fix_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "steps": {}
        }
        
        # Step 1: Run initial diagnosis
        logger.info("Step 1: Initial diagnosis...")
        initial_diagnosis = await self.run_comprehensive_diagnosis()
        fix_results["steps"]["initial_diagnosis"] = initial_diagnosis
        
        if not initial_diagnosis["overall_assessment"]["issue_confirmed"]:
            logger.info("No JWT secret consistency issue detected - no fix needed")
            return {
                **fix_results,
                "fix_needed": False,
                "message": "No JWT secret consistency issue detected"
            }
        
        logger.warning("JWT secret consistency issue CONFIRMED - proceeding with fix")
        
        # Step 2: Force JWT secret refresh
        logger.info("Step 2: Forcing JWT secret refresh...")
        refresh_result = await self.force_jwt_secret_refresh()
        fix_results["steps"]["jwt_secret_refresh"] = refresh_result
        
        # Step 3: Re-deploy auth service with secret validation
        logger.info("Step 3: Re-deploying auth service...")
        auth_deploy_result = await self.deploy_service_with_secret_refresh("auth")
        fix_results["steps"]["auth_service_deployment"] = auth_deploy_result
        
        # Step 4: Re-deploy backend service with secret validation
        logger.info("Step 4: Re-deploying backend service...")
        backend_deploy_result = await self.deploy_service_with_secret_refresh("backend")
        fix_results["steps"]["backend_service_deployment"] = backend_deploy_result
        
        # Step 5: Wait for services to start
        logger.info("Step 5: Waiting for services to restart...")
        await asyncio.sleep(60)  # Wait for services to fully start
        
        # Step 6: Final validation
        logger.info("Step 6: Final validation...")
        final_diagnosis = await self.run_comprehensive_diagnosis()
        fix_results["steps"]["final_validation"] = final_diagnosis
        
        # Success assessment
        fix_success = (
            final_diagnosis["overall_assessment"]["token_validation_works"] and
            auth_deploy_result.get("success", False) and
            backend_deploy_result.get("success", False)
        )
        
        fix_results.update({
            "fix_needed": True,
            "fix_success": fix_success,
            "auth_success_rate_expected": "95%+" if fix_success else "Still degraded",
            "business_impact": "$120K+ MRR restored" if fix_success else "Still at risk"
        })
        
        return fix_results


async def main():
    """Main function to run JWT secret consistency fix."""
    print("=" * 70)
    print("STAGING JWT SECRET CONSISTENCY FIX")
    print("=" * 70)
    print("Business Impact: $120K+ MRR restoration")
    print("Technical Impact: Restore 95%+ auth success rate")
    print("=" * 70)
    
    try:
        # Initialize fixer
        fixer = StagingJWTSecretFixer()
        
        # Choose operation mode
        if len(sys.argv) > 1 and sys.argv[1] == "diagnose":
            print("DIAGNOSTIC MODE: Analyzing JWT secret consistency...")
            result = await fixer.run_comprehensive_diagnosis()
            
            print("\nDIAGNOSTIC RESULTS:")
            print("=" * 50)
            print(json.dumps(result, indent=2))
            
            if result["overall_assessment"]["issue_confirmed"]:
                print("\n❌ JWT SECRET CONSISTENCY ISSUE CONFIRMED")
                print("Run with 'fix' argument to apply emergency fix")
                return 1
            else:
                print("\n✅ JWT SECRET CONSISTENCY OK")
                return 0
        
        elif len(sys.argv) > 1 and sys.argv[1] == "fix":
            print("EMERGENCY FIX MODE: Applying JWT secret consistency fix...")
            result = await fixer.run_emergency_fix()
            
            print("\nEMERGENCY FIX RESULTS:")
            print("=" * 50)
            print(json.dumps(result, indent=2))
            
            if result.get("fix_success", False):
                print("\n✅ EMERGENCY FIX SUCCESSFUL")
                print("JWT secret consistency restored")
                print("Expected auth success rate: 95%+")
                print("Business impact: $120K+ MRR restored")
                return 0
            else:
                print("\n❌ EMERGENCY FIX FAILED")
                print("Manual intervention required")
                return 1
        
        else:
            print("Usage:")
            print("  python staging_jwt_secret_consistency_fix.py diagnose")
            print("  python staging_jwt_secret_consistency_fix.py fix")
            return 1
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))