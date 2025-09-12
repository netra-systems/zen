from shared.isolated_environment import get_env
"""
Deployment Preflight Checks

CRITICAL: These checks MUST pass before deployment to staging/production.
This prevents deployment of broken configurations that would fail at runtime.
"""
import os
import sys
import asyncio
import logging
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentPreflightChecker:
    """
    Validates that all critical infrastructure is properly configured
    before allowing deployment to staging/production.
    """
    
    def __init__(self, environment: str):
        """
        Initialize preflight checker for specific environment.
        
        Args:
            environment: Target environment (staging/production)
        """
        self.environment = environment
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    async def check_jwt_secret_configuration(self) -> bool:
        """
        Validate JWT secret configuration and synchronization.
        
        Returns:
            bool: True if JWT configuration is valid
        """
        try:
            from shared.jwt_secret_manager import SharedJWTSecretManager, validate_jwt_configuration
            
            # Validate JWT configuration
            if not validate_jwt_configuration():
                self.errors.append("JWT configuration validation failed")
                return False
            
            # Get the actual secret to ensure it's loadable
            secret = SharedJWTSecretManager.get_jwt_secret()
            
            # Validate secret quality
            if len(secret) < 32:
                self.errors.append(f"JWT secret too short: {len(secret)} chars (minimum 32)")
                return False
            
            # Check for development secrets in production
            if self.environment in ["staging", "production"]:
                if "development" in secret.lower():
                    self.errors.append("Development JWT secret detected in production environment")
                    return False
            
            logger.info(f" PASS:  JWT secret configuration valid: {len(secret)} chars")
            return True
            
        except Exception as e:
            self.errors.append(f"JWT secret validation error: {e}")
            return False
    
    async def check_clickhouse_connectivity(self) -> bool:
        """
        Validate ClickHouse is accessible and configured.
        
        Returns:
            bool: True if ClickHouse is accessible
        """
        if self.environment not in ["staging", "production"]:
            logger.info("Skipping ClickHouse check for development environment")
            return True
        
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            
            # Check if ClickHouse is configured
            if not config.clickhouse_native.host and not config.clickhouse_https.host:
                self.errors.append("ClickHouse host not configured (REQUIRED in staging/production)")
                return False
            
            # Try to connect to ClickHouse
            from netra_backend.app.db.clickhouse import get_clickhouse_client
            client = get_clickhouse_client()
            
            # Simple ping test
            result = client.execute("SELECT 1")
            if result[0][0] != 1:
                self.errors.append("ClickHouse ping test failed")
                return False
            
            logger.info(f" PASS:  ClickHouse connectivity verified: {config.clickhouse_native.host or config.clickhouse_https.host}")
            return True
            
        except ImportError:
            self.errors.append("ClickHouse client not available")
            return False
        except Exception as e:
            self.errors.append(f"ClickHouse connectivity error: {e}")
            return False
    
    async def check_redis_connectivity(self) -> bool:
        """
        Validate Redis is accessible and configured.
        
        Returns:
            bool: True if Redis is accessible
        """
        if self.environment not in ["staging", "production"]:
            logger.info("Skipping Redis check for development environment")
            return True
        
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            
            # Check if Redis is configured
            if not config.redis.host:
                self.errors.append("Redis host not configured (REQUIRED in staging/production)")
                return False
            
            # Try to connect to Redis
            import redis.asyncio as redis
            
            # Create Redis connection
            redis_url = f"redis://{config.redis.username}:{config.redis.password}@{config.redis.host}:{config.redis.port}"
            client = redis.from_url(redis_url)
            
            # Simple ping test
            if not await client.ping():
                self.errors.append("Redis ping test failed")
                return False
            
            await client.close()
            
            logger.info(f" PASS:  Redis connectivity verified: {config.redis.host}")
            return True
            
        except ImportError:
            self.errors.append("Redis client not available")
            return False
        except Exception as e:
            self.errors.append(f"Redis connectivity error: {e}")
            return False
    
    async def check_database_connectivity(self) -> bool:
        """
        Validate PostgreSQL database is accessible.
        
        Returns:
            bool: True if database is accessible
        """
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            
            if not config.database_url:
                self.errors.append("Database URL not configured")
                return False
            
            # Try to connect to database
            from sqlalchemy.ext.asyncio import create_async_engine
            engine = create_async_engine(config.database_url)
            
            async with engine.connect() as conn:
                result = await conn.execute("SELECT 1")
                if not result:
                    self.errors.append("Database connectivity test failed")
                    return False
            
            await engine.dispose()
            
            logger.info(" PASS:  Database connectivity verified")
            return True
            
        except Exception as e:
            self.errors.append(f"Database connectivity error: {e}")
            return False
    
    async def check_auth_service_sync(self) -> bool:
        """
        Validate auth service and backend JWT secrets are synchronized.
        
        Returns:
            bool: True if services are synchronized
        """
        try:
            # Import both service configurations
            from auth_service.auth_core.config import AuthConfig
            from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
            
            # Get JWT secrets from both services
            auth_secret = AuthConfig.get_jwt_secret()
            backend_manager = UnifiedSecretManager()
            backend_secret = backend_manager.get_jwt_secret()
            
            # Verify they match
            if auth_secret != backend_secret:
                self.errors.append(
                    f"JWT secret mismatch between services! "
                    f"Auth: {auth_secret[:10]}... Backend: {backend_secret[:10]}..."
                )
                return False
            
            logger.info(" PASS:  Auth service and backend JWT secrets synchronized")
            return True
            
        except Exception as e:
            self.errors.append(f"Auth service sync check error: {e}")
            return False
    
    async def check_environment_variables(self) -> bool:
        """
        Validate required environment variables are set.
        
        Returns:
            bool: True if all required variables are set
        """
        required_vars = {
            "staging": [
                "ENVIRONMENT",
                "JWT_SECRET_KEY",
                "DATABASE_URL",
            ],
            "production": [
                "ENVIRONMENT", 
                "JWT_SECRET_KEY",
                "DATABASE_URL",
                "GCP_PROJECT_ID",
            ]
        }
        
        missing_vars = []
        for var in required_vars.get(self.environment, []):
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.errors.append(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        logger.info(" PASS:  All required environment variables present")
        return True
    
    async def run_all_checks(self) -> Tuple[bool, Dict[str, bool]]:
        """
        Run all preflight checks.
        
        Returns:
            Tuple[bool, Dict[str, bool]]: Overall status and individual check results
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"DEPLOYMENT PREFLIGHT CHECKS - {self.environment.upper()}")
        logger.info(f"{'='*60}\n")
        
        checks = {
            "Environment Variables": self.check_environment_variables(),
            "JWT Secret Configuration": self.check_jwt_secret_configuration(),
            "Auth Service Sync": self.check_auth_service_sync(),
            "Database Connectivity": self.check_database_connectivity(),
            "Redis Connectivity": self.check_redis_connectivity(),
            "ClickHouse Connectivity": self.check_clickhouse_connectivity(),
        }
        
        results = {}
        for name, check_coro in checks.items():
            logger.info(f"Checking {name}...")
            try:
                result = await check_coro
                results[name] = result
                if result:
                    logger.info(f"   PASS:  {name}: PASSED")
                else:
                    logger.error(f"   FAIL:  {name}: FAILED")
            except Exception as e:
                logger.error(f"   FAIL:  {name}: ERROR - {e}")
                results[name] = False
                self.errors.append(f"{name} check failed: {e}")
        
        # Overall status
        all_passed = all(results.values())
        
        logger.info(f"\n{'='*60}")
        if all_passed:
            logger.info(" PASS:  ALL PREFLIGHT CHECKS PASSED")
        else:
            logger.error(" FAIL:  PREFLIGHT CHECKS FAILED")
            logger.error("\nErrors detected:")
            for error in self.errors:
                logger.error(f"  - {error}")
        
        if self.warnings:
            logger.warning("\nWarnings:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        logger.info(f"{'='*60}\n")
        
        return all_passed, results


async def main():
    """Main entry point for preflight checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deployment Preflight Checks")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default=os.environ.get("ENVIRONMENT", "development"),
        help="Target deployment environment"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit on first failure"
    )
    
    args = parser.parse_args()
    
    # Set environment
    os.environ["ENVIRONMENT"] = args.environment
    
    # Run checks
    checker = DeploymentPreflightChecker(args.environment)
    passed, results = await checker.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
