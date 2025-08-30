#!/usr/bin/env python3
"""
Verify JWT Secret Synchronization Between Services

This script checks:
1. JWT secret loading from environment
2. JWT secret consistency between auth service and backend
3. Secret Manager connectivity and loading
4. Token validation between services
"""

import os
import sys
import logging
import jwt
from pathlib import Path
from typing import Dict, Tuple, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment_secrets() -> Dict[str, str]:
    """Check JWT secrets in environment variables."""
    secrets = {}
    
    # Check all JWT-related environment variables
    jwt_vars = [
        'JWT_SECRET_KEY',
        'JWT_SECRET',
        'JWT_SECRET_STAGING',
        'JWT_SECRET_PRODUCTION',
        'JWT_SECRET_DEVELOPMENT'
    ]
    
    logger.info("=" * 60)
    logger.info("CHECKING ENVIRONMENT VARIABLES")
    logger.info("=" * 60)
    
    for var in jwt_vars:
        value = os.environ.get(var)
        if value:
            secrets[var] = value
            logger.info(f"✓ {var}: {len(value)} chars, starts with '{value[:10]}...'")
        else:
            logger.info(f"✗ {var}: NOT SET")
    
    return secrets


def check_auth_service_secret() -> Tuple[Optional[str], str]:
    """Check how auth service loads JWT secret."""
    logger.info("\n" + "=" * 60)
    logger.info("CHECKING AUTH SERVICE SECRET LOADING")
    logger.info("=" * 60)
    
    try:
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        secret = AuthSecretLoader.get_jwt_secret()
        logger.info(f"✓ Auth service loaded JWT secret: {len(secret)} chars")
        logger.info(f"  Secret starts with: '{secret[:10]}...'")
        return secret, "SUCCESS"
    except Exception as e:
        logger.error(f"✗ Auth service failed to load JWT secret: {e}")
        return None, str(e)


def check_backend_secret() -> Tuple[Optional[str], str]:
    """Check how backend service loads JWT secret."""
    logger.info("\n" + "=" * 60)
    logger.info("CHECKING BACKEND SERVICE SECRET LOADING")
    logger.info("=" * 60)
    
    try:
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        
        secret = get_jwt_secret()
        logger.info(f"✓ Backend loaded JWT secret: {len(secret)} chars")
        logger.info(f"  Secret starts with: '{secret[:10]}...'")
        return secret, "SUCCESS"
    except Exception as e:
        logger.error(f"✗ Backend failed to load JWT secret: {e}")
        return None, str(e)


def check_secret_manager_builder() -> Dict[str, any]:
    """Check SecretManagerBuilder functionality."""
    logger.info("\n" + "=" * 60)
    logger.info("CHECKING SECRET MANAGER BUILDER")
    logger.info("=" * 60)
    
    results = {}
    
    try:
        from shared.secret_manager_builder import SecretManagerBuilder
        
        # Test for auth service
        auth_builder = SecretManagerBuilder(service="auth_service")
        auth_secret = auth_builder.auth.get_jwt_secret()
        results['auth_builder'] = auth_secret
        logger.info(f"✓ Auth builder loaded JWT: {len(auth_secret)} chars")
        
        # Test for backend service
        backend_builder = SecretManagerBuilder(service="netra_backend")
        backend_secret = backend_builder.auth.get_jwt_secret()
        results['backend_builder'] = backend_secret
        logger.info(f"✓ Backend builder loaded JWT: {len(backend_secret)} chars")
        
        # Check if they match
        if auth_secret == backend_secret:
            logger.info("✓ SecretManagerBuilder returns SAME secret for both services")
        else:
            logger.error("✗ SecretManagerBuilder returns DIFFERENT secrets!")
            logger.error(f"  Auth:    '{auth_secret[:20]}...'")
            logger.error(f"  Backend: '{backend_secret[:20]}...'")
            
    except Exception as e:
        logger.error(f"✗ SecretManagerBuilder failed: {e}")
        results['error'] = str(e)
    
    return results


def test_token_validation(jwt_secret: str) -> bool:
    """Test JWT token creation and validation."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING TOKEN VALIDATION")
    logger.info("=" * 60)
    
    try:
        # Create a test token
        payload = {
            'user_id': 'test_user',
            'email': 'test@example.com',
            'exp': 9999999999  # Far future
        }
        
        token = jwt.encode(payload, jwt_secret, algorithm='HS256')
        logger.info(f"✓ Created test token: {token[:50]}...")
        
        # Decode it back
        decoded = jwt.decode(token, jwt_secret, algorithms=['HS256'])
        logger.info(f"✓ Decoded token successfully: user_id={decoded.get('user_id')}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Token validation failed: {e}")
        return False


def check_cross_service_validation(auth_secret: str, backend_secret: str) -> bool:
    """Check if tokens created by one service can be validated by the other."""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING CROSS-SERVICE TOKEN VALIDATION")
    logger.info("=" * 60)
    
    if not auth_secret or not backend_secret:
        logger.error("✗ Cannot test cross-service validation - one or both secrets missing")
        return False
    
    try:
        # Create token with auth service secret
        payload = {'user_id': 'test', 'exp': 9999999999}
        auth_token = jwt.encode(payload, auth_secret, algorithm='HS256')
        logger.info(f"✓ Created token with auth secret")
        
        # Try to decode with backend secret
        try:
            decoded = jwt.decode(auth_token, backend_secret, algorithms=['HS256'])
            logger.info(f"✓ Backend can decode auth token - SECRETS MATCH!")
            return True
        except jwt.InvalidSignatureError:
            logger.error(f"✗ Backend CANNOT decode auth token - SECRETS DON'T MATCH!")
            logger.error(f"  Auth secret:    '{auth_secret[:20]}...' (len={len(auth_secret)})")
            logger.error(f"  Backend secret: '{backend_secret[:20]}...' (len={len(backend_secret)})")
            return False
            
    except Exception as e:
        logger.error(f"✗ Cross-service validation error: {e}")
        return False


def main():
    """Main verification flow."""
    logger.info("JWT SECRET SYNCHRONIZATION VERIFICATION")
    logger.info("=" * 60)
    
    # Get current environment
    env = os.environ.get('ENVIRONMENT', 'development')
    logger.info(f"Environment: {env}")
    
    # Check environment variables
    env_secrets = check_environment_secrets()
    
    # Check auth service
    auth_secret, auth_error = check_auth_service_secret()
    
    # Check backend service
    backend_secret, backend_error = check_backend_secret()
    
    # Check SecretManagerBuilder
    builder_results = check_secret_manager_builder()
    
    # Cross-service validation
    if auth_secret and backend_secret:
        cross_valid = check_cross_service_validation(auth_secret, backend_secret)
    else:
        cross_valid = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    issues = []
    
    # Check if secrets match
    if auth_secret and backend_secret:
        if auth_secret == backend_secret:
            logger.info("✓ Auth and Backend use SAME JWT secret")
        else:
            logger.error("✗ Auth and Backend use DIFFERENT JWT secrets!")
            issues.append("Services using different JWT secrets")
    
    # Check if builder secrets match
    if 'auth_builder' in builder_results and 'backend_builder' in builder_results:
        if builder_results['auth_builder'] == builder_results['backend_builder']:
            logger.info("✓ SecretManagerBuilder consistent across services")
        else:
            logger.error("✗ SecretManagerBuilder returns different secrets per service!")
            issues.append("SecretManagerBuilder inconsistency")
    
    # Final verdict
    if not issues and cross_valid:
        logger.info("\n✅ JWT SECRET SYNCHRONIZATION: WORKING CORRECTLY")
        return 0
    else:
        logger.error("\n❌ JWT SECRET SYNCHRONIZATION: ISSUES DETECTED")
        for issue in issues:
            logger.error(f"  - {issue}")
        
        # Suggest fixes
        logger.info("\n" + "=" * 60)
        logger.info("RECOMMENDED FIXES")
        logger.info("=" * 60)
        
        if auth_secret != backend_secret:
            logger.info("1. Ensure both services load JWT_SECRET_KEY from the same source")
            logger.info("2. Check that environment variables are set consistently")
            logger.info("3. For staging/production, verify Google Secret Manager secrets")
            
            # Check which env var would fix it
            if 'JWT_SECRET_KEY' in env_secrets:
                logger.info(f"\n   Set both services to use JWT_SECRET_KEY from environment:")
                logger.info(f"   JWT_SECRET_KEY='{env_secrets['JWT_SECRET_KEY']}'")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())