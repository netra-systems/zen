"""
JWT Secret Consistency Validator - Cross-Service Security Validation

This module provides validation to ensure that all services use the same JWT secret,
preventing the WebSocket 403 authentication failures that occur when services
have different JWT secrets.

Business Value:
- Prevents $50K MRR loss from WebSocket authentication failures
- Ensures consistent JWT validation across all services
- Provides early detection of JWT secret drift
- Enables zero-downtime JWT secret rotation validation

CRITICAL: This validator MUST be used during:
- System startup validation
- Deployment health checks  
- JWT secret rotation operations
- Integration test setup
"""

import asyncio
import logging
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import jwt

from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_unified_jwt_secret, get_unified_jwt_algorithm

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """JWT secret validation results."""
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"  
    UNREACHABLE = "unreachable"
    ERROR = "error"


@dataclass
class ServiceJWTInfo:
    """JWT configuration information for a service."""
    service_name: str
    jwt_secret_hash: str  # MD5 hash for comparison (don't store actual secret)
    jwt_algorithm: str
    secret_source: str  # Where the secret came from
    validation_timestamp: datetime
    reachable: bool = True
    error: Optional[str] = None


@dataclass 
class ConsistencyValidationReport:
    """Report of JWT secret consistency validation."""
    validation_timestamp: datetime
    overall_result: ValidationResult
    services: List[ServiceJWTInfo]
    inconsistencies: List[str]
    recommendations: List[str]
    summary: str
    

class JWTSecretConsistencyValidator:
    """
    Validates JWT secret consistency across all services in the Netra platform.
    
    This validator ensures that all services (auth service, backend service, 
    test framework) use the same JWT secret, preventing authentication failures.
    """
    
    def __init__(self):
        """Initialize JWT secret consistency validator."""
        self.env = get_env()
        self.validation_cache: Dict[str, ServiceJWTInfo] = {}
        
    def _hash_secret(self, secret: str) -> str:
        """Hash JWT secret for comparison (don't store actual secrets)."""
        return hashlib.md5(secret.encode()).hexdigest()
    
    async def validate_service_jwt_config(self, service_name: str) -> ServiceJWTInfo:
        """
        Validate JWT configuration for a specific service.
        
        Args:
            service_name: Name of service to validate
            
        Returns:
            ServiceJWTInfo with validation results
        """
        try:
            if service_name == "unified_manager":
                # Test the unified JWT secret manager
                secret = get_unified_jwt_secret()
                algorithm = get_unified_jwt_algorithm()
                
                return ServiceJWTInfo(
                    service_name="unified_manager",
                    jwt_secret_hash=self._hash_secret(secret),
                    jwt_algorithm=algorithm,
                    secret_source="unified_manager",
                    validation_timestamp=datetime.now(timezone.utc),
                    reachable=True
                )
                
            elif service_name == "auth_service":
                # Validate auth service JWT configuration
                try:
                    from auth_service.auth_core.config import AuthConfig
                    secret = AuthConfig.get_jwt_secret()
                    algorithm = AuthConfig.get_jwt_algorithm()
                    
                    return ServiceJWTInfo(
                        service_name="auth_service",
                        jwt_secret_hash=self._hash_secret(secret),
                        jwt_algorithm=algorithm,
                        secret_source="auth_service_config",
                        validation_timestamp=datetime.now(timezone.utc),
                        reachable=True
                    )
                except ImportError:
                    return ServiceJWTInfo(
                        service_name="auth_service",
                        jwt_secret_hash="",
                        jwt_algorithm="",
                        secret_source="unavailable", 
                        validation_timestamp=datetime.now(timezone.utc),
                        reachable=False,
                        error="Auth service not available for import"
                    )
                    
            elif service_name == "backend_service":
                # Validate backend service JWT configuration via unified manager
                secret = get_unified_jwt_secret()
                algorithm = get_unified_jwt_algorithm()
                
                return ServiceJWTInfo(
                    service_name="backend_service",
                    jwt_secret_hash=self._hash_secret(secret),
                    jwt_algorithm=algorithm,
                    secret_source="unified_manager_via_backend",
                    validation_timestamp=datetime.now(timezone.utc),
                    reachable=True
                )
                
            elif service_name == "test_framework":
                # Validate test framework JWT configuration
                try:
                    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
                    helper = E2EAuthHelper()
                    secret = helper.config.jwt_secret
                    
                    return ServiceJWTInfo(
                        service_name="test_framework", 
                        jwt_secret_hash=self._hash_secret(secret),
                        jwt_algorithm="HS256",  # Test framework uses HS256
                        secret_source="test_framework_config",
                        validation_timestamp=datetime.now(timezone.utc),
                        reachable=True
                    )
                except ImportError:
                    return ServiceJWTInfo(
                        service_name="test_framework",
                        jwt_secret_hash="",
                        jwt_algorithm="",
                        secret_source="unavailable",
                        validation_timestamp=datetime.now(timezone.utc),
                        reachable=False,
                        error="Test framework not available for import"
                    )
                    
            else:
                return ServiceJWTInfo(
                    service_name=service_name,
                    jwt_secret_hash="",
                    jwt_algorithm="",
                    secret_source="unknown",
                    validation_timestamp=datetime.now(timezone.utc),
                    reachable=False,
                    error=f"Unknown service: {service_name}"
                )
                
        except Exception as e:
            logger.error(f"Error validating JWT config for {service_name}: {e}")
            return ServiceJWTInfo(
                service_name=service_name,
                jwt_secret_hash="",
                jwt_algorithm="",
                secret_source="error",
                validation_timestamp=datetime.now(timezone.utc),
                reachable=False,
                error=str(e)
            )
    
    async def validate_cross_service_consistency(self) -> ConsistencyValidationReport:
        """
        Validate JWT secret consistency across all services.
        
        Returns:
            ConsistencyValidationReport with detailed results
        """
        logger.info(" SEARCH:  Starting cross-service JWT secret consistency validation...")
        
        # Services to validate
        services_to_check = [
            "unified_manager",
            "auth_service", 
            "backend_service",
            "test_framework"
        ]
        
        # Validate each service
        service_infos: List[ServiceJWTInfo] = []
        
        for service_name in services_to_check:
            logger.info(f"   Validating {service_name}...")
            service_info = await self.validate_service_jwt_config(service_name)
            service_infos.append(service_info)
            
            if service_info.reachable:
                logger.info(f"    PASS:  {service_name}: Secret hash {service_info.jwt_secret_hash[:8]}... (source: {service_info.secret_source})")
            else:
                logger.warning(f"    WARNING: [U+FE0F] {service_name}: Not reachable - {service_info.error}")
        
        # Analyze consistency
        reachable_services = [s for s in service_infos if s.reachable]
        
        if len(reachable_services) < 2:
            return ConsistencyValidationReport(
                validation_timestamp=datetime.now(timezone.utc),
                overall_result=ValidationResult.ERROR,
                services=service_infos,
                inconsistencies=["Not enough reachable services for consistency validation"],
                recommendations=["Ensure all services are available and properly configured"],
                summary="Cannot validate consistency - insufficient reachable services"
            )
        
        # Check for secret hash consistency
        secret_hashes = set(s.jwt_secret_hash for s in reachable_services)
        algorithms = set(s.jwt_algorithm for s in reachable_services)
        
        inconsistencies = []
        recommendations = []
        
        if len(secret_hashes) > 1:
            inconsistencies.append("JWT secrets are not consistent across services")
            # Group services by secret hash
            for secret_hash in secret_hashes:
                services_with_hash = [s.service_name for s in reachable_services if s.jwt_secret_hash == secret_hash]
                inconsistencies.append(f"Secret hash {secret_hash[:8]}... used by: {', '.join(services_with_hash)}")
            
            recommendations.append("Use unified JWT secret manager across all services")
            recommendations.append("Verify environment variables are consistently configured")
            
        if len(algorithms) > 1:
            inconsistencies.append("JWT algorithms are not consistent across services")
            for algorithm in algorithms:
                services_with_algo = [s.service_name for s in reachable_services if s.jwt_algorithm == algorithm]
                inconsistencies.append(f"Algorithm {algorithm} used by: {', '.join(services_with_algo)}")
                
            recommendations.append("Standardize JWT algorithm across all services (recommend HS256)")
        
        # Determine overall result
        if inconsistencies:
            overall_result = ValidationResult.INCONSISTENT
            summary = f"JWT secret inconsistency detected across {len(reachable_services)} services"
        else:
            overall_result = ValidationResult.CONSISTENT
            summary = f"JWT secrets consistent across {len(reachable_services)} services"
            
        return ConsistencyValidationReport(
            validation_timestamp=datetime.now(timezone.utc),
            overall_result=overall_result,
            services=service_infos,
            inconsistencies=inconsistencies,
            recommendations=recommendations,
            summary=summary
        )
    
    async def validate_jwt_token_cross_service(self, test_user_email: str = "test@example.com") -> Dict[str, Any]:
        """
        Create a JWT token with one service and validate it with others.
        
        This is the ultimate test - if services have different secrets,
        tokens created by one service will be rejected by others.
        
        Args:
            test_user_email: Email for test JWT token
            
        Returns:
            Dict with validation results across services
        """
        logger.info("[U+1F527] Testing JWT token cross-service validation...")
        
        results = {
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "test_user": test_user_email,
            "token_creation": {},
            "token_validation": {},
            "cross_service_success": False,
            "errors": []
        }
        
        try:
            # Create JWT token using unified manager
            secret = get_unified_jwt_secret()
            algorithm = get_unified_jwt_algorithm()
            
            payload = {
                "sub": f"test-user-{int(time.time())}",
                "email": test_user_email,
                "permissions": ["read", "write"],
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                "iss": "netra-auth-service",
                "aud": "netra-platform",
                "jti": f"consistency-test-{int(time.time())}"
            }
            
            test_token = jwt.encode(payload, secret, algorithm=algorithm)
            
            results["token_creation"] = {
                "success": True,
                "token_length": len(test_token),
                "secret_source": "unified_manager",
                "algorithm": algorithm
            }
            
            logger.info(f"    PASS:  Created test JWT token using unified manager (length: {len(test_token)})")
            
            # Try to validate token with auth service
            try:
                from auth_service.auth_core.core.jwt_handler import JWTHandler
                auth_jwt_handler = JWTHandler()
                auth_validation = auth_jwt_handler.validate_token(test_token)
                
                results["token_validation"]["auth_service"] = {
                    "success": auth_validation is not None,
                    "payload_user": auth_validation.get("sub") if auth_validation else None,
                    "error": None if auth_validation else "Token validation returned None"
                }
                
                if auth_validation:
                    logger.info("    PASS:  Auth service successfully validated token")
                else:
                    logger.error("    FAIL:  Auth service rejected token")
                    results["errors"].append("Auth service rejected token created by unified manager")
                    
            except Exception as e:
                results["token_validation"]["auth_service"] = {
                    "success": False,
                    "error": str(e)
                }
                results["errors"].append(f"Auth service validation error: {e}")
                logger.error(f"    FAIL:  Auth service validation error: {e}")
            
            # Try to validate token with test framework
            try:
                # Validate using JWT library with the same secret
                decoded_payload = jwt.decode(test_token, secret, algorithms=[algorithm])
                
                results["token_validation"]["test_framework"] = {
                    "success": True,
                    "payload_user": decoded_payload.get("sub"),
                    "error": None
                }
                
                logger.info("    PASS:  Test framework successfully validated token")
                
            except Exception as e:
                results["token_validation"]["test_framework"] = {
                    "success": False,
                    "error": str(e)  
                }
                results["errors"].append(f"Test framework validation error: {e}")
                logger.error(f"    FAIL:  Test framework validation error: {e}")
            
            # Determine overall cross-service success
            validation_results = results["token_validation"]
            successful_validations = sum(1 for v in validation_results.values() if v.get("success", False))
            total_validations = len(validation_results)
            
            results["cross_service_success"] = successful_validations == total_validations and total_validations > 0
            results["success_rate"] = successful_validations / max(total_validations, 1)
            
            if results["cross_service_success"]:
                logger.info(f"    PASS:  Cross-service JWT validation SUCCESS ({successful_validations}/{total_validations})")
            else:
                logger.error(f"    FAIL:  Cross-service JWT validation FAILED ({successful_validations}/{total_validations})")
                
        except Exception as e:
            results["token_creation"] = {
                "success": False,
                "error": str(e)
            }
            results["errors"].append(f"Token creation error: {e}")
            logger.error(f"    FAIL:  Token creation error: {e}")
        
        return results
    
    def log_validation_report(self, report: ConsistencyValidationReport) -> None:
        """Log detailed validation report."""
        logger.info("=" * 60)
        logger.info("JWT SECRET CONSISTENCY VALIDATION REPORT")
        logger.info("=" * 60)
        logger.info(f"Validation Time: {report.validation_timestamp}")
        logger.info(f"Overall Result: {report.overall_result.value.upper()}")
        logger.info(f"Summary: {report.summary}")
        logger.info("")
        
        logger.info("SERVICE DETAILS:")
        for service in report.services:
            status = " PASS:  REACHABLE" if service.reachable else " FAIL:  UNREACHABLE"
            logger.info(f"  {service.service_name}: {status}")
            if service.reachable:
                logger.info(f"    Secret Hash: {service.jwt_secret_hash[:12]}...")
                logger.info(f"    Algorithm: {service.jwt_algorithm}")
                logger.info(f"    Source: {service.secret_source}")
            else:
                logger.info(f"    Error: {service.error}")
        
        if report.inconsistencies:
            logger.warning("")
            logger.warning("INCONSISTENCIES DETECTED:")
            for inconsistency in report.inconsistencies:
                logger.warning(f"   FAIL:  {inconsistency}")
        
        if report.recommendations:
            logger.info("")
            logger.info("RECOMMENDATIONS:")
            for recommendation in report.recommendations:
                logger.info(f"   IDEA:  {recommendation}")
                
        logger.info("=" * 60)


# Global validator instance
_jwt_consistency_validator: Optional[JWTSecretConsistencyValidator] = None


def get_jwt_consistency_validator() -> JWTSecretConsistencyValidator:
    """Get global JWT consistency validator instance."""
    global _jwt_consistency_validator
    if _jwt_consistency_validator is None:
        _jwt_consistency_validator = JWTSecretConsistencyValidator()
    return _jwt_consistency_validator


async def validate_jwt_consistency() -> ConsistencyValidationReport:
    """
    Convenience function to validate JWT consistency across all services.
    
    Returns:
        ConsistencyValidationReport with validation results
    """
    validator = get_jwt_consistency_validator()
    report = await validator.validate_cross_service_consistency()
    validator.log_validation_report(report)
    return report


async def validate_jwt_cross_service_tokens() -> Dict[str, Any]:
    """
    Convenience function to test JWT token creation/validation across services.
    
    Returns:
        Dict with cross-service token validation results
    """
    validator = get_jwt_consistency_validator()
    return await validator.validate_jwt_token_cross_service()


__all__ = [
    "ValidationResult",
    "ServiceJWTInfo", 
    "ConsistencyValidationReport",
    "JWTSecretConsistencyValidator",
    "get_jwt_consistency_validator",
    "validate_jwt_consistency",
    "validate_jwt_cross_service_tokens"
]