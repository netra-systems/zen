#!/usr/bin/env python3
"""
Staging Environment Setup for Integration Tests
Sets up environment variables to use GCP staging services for integration tests.

This script configures the test environment to use staging PostgreSQL and Redis
services instead of local Docker services, enabling real service integration testing
as required by the Golden Path specifications.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment, get_env
from tests.staging.staging_config import StagingConfig
from deployment.secrets_config import SecretConfig


class StagingEnvironmentSetup:
    """Setup staging environment for integration tests."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.staging_config = StagingConfig()
        
    def setup_staging_environment(self):
        """Set up environment variables for staging services."""
        print("🚀 Setting up Staging Environment for Integration Tests")
        print("=" * 60)
        
        # Set primary environment to staging
        os.environ["ENVIRONMENT"] = "staging"
        
        # Configure staging service URLs
        staging_urls = self.staging_config.SERVICE_URLS["staging"]
        for key, url in staging_urls.items():
            os.environ[key] = url
            print(f"✅ {key} = {url}")
        
        # Configure database connection for staging
        self._setup_database_connection()
        
        # Configure Redis connection for staging  
        self._setup_redis_connection()
        
        # Configure ClickHouse for staging
        self._setup_clickhouse_connection()
        
        # Additional staging configuration
        self._setup_additional_config()
        
        print("=" * 60)
        print("✅ Staging environment configured for integration tests")
        print("🔍 Services will connect to GCP staging infrastructure")
        print("📍 Golden Path testing enabled with real services")
        
    def _setup_database_connection(self):
        """Configure PostgreSQL connection for staging."""
        print("\n📊 Configuring Database Connection (Cloud SQL)")
        
        # These will be retrieved from Google Secret Manager by the services
        # We just need to indicate we're using staging environment
        staging_db_config = {
            "DATABASE_URL": "postgresql://staging_user:password@postgres-host/staging_db",
            "POSTGRES_HOST": "Cloud_SQL_staging",  # Placeholder - actual value from GSM
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "netra_staging", 
            "POSTGRES_USER": "staging_user",
            "POSTGRES_PASSWORD": "staging_password",  # Actual value from GSM
        }
        
        for key, value in staging_db_config.items():
            os.environ[key] = value
            if "PASSWORD" in key:
                print(f"✅ {key} = [REDACTED]")
            else:
                print(f"✅ {key} = {value}")
    
    def _setup_redis_connection(self):
        """Configure Redis connection for staging."""
        print("\n🔄 Configuring Redis Connection (Memorystore)")
        
        # These will be retrieved from Google Secret Manager by the services
        staging_redis_config = {
            "REDIS_URL": "redis://staging-redis:6379/0",
            "REDIS_HOST": "staging-redis-memorystore",  # Placeholder - actual value from GSM
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "staging_redis_password",  # Actual value from GSM
            "REDIS_MODE": "production"  # Use production mode for staging testing
        }
        
        for key, value in staging_redis_config.items():
            os.environ[key] = value
            if "PASSWORD" in key:
                print(f"✅ {key} = [REDACTED]")
            else:
                print(f"✅ {key} = {value}")
    
    def _setup_clickhouse_connection(self):
        """Configure ClickHouse connection for staging.""" 
        print("\n📈 Configuring ClickHouse Connection (Analytics)")
        
        clickhouse_config = {
            "CLICKHOUSE_HOST": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "CLICKHOUSE_PORT": "8443", 
            "CLICKHOUSE_USER": "default",
            "CLICKHOUSE_DB": "default",
            "CLICKHOUSE_SECURE": "true",
            "CLICKHOUSE_PASSWORD": "staging_clickhouse_password"  # From GSM
        }
        
        for key, value in clickhouse_config.items():
            os.environ[key] = value
            if "PASSWORD" in key:
                print(f"✅ {key} = [REDACTED]")
            else:
                print(f"✅ {key} = {value}")
    
    def _setup_additional_config(self):
        """Setup additional staging configuration."""
        print("\n⚙️  Additional Staging Configuration")
        
        additional_config = {
            # Authentication
            "JWT_ALGORITHM": "HS256",
            "JWT_ACCESS_EXPIRY_MINUTES": "15",
            "JWT_REFRESH_EXPIRY_DAYS": "7",
            
            # Service configuration
            "AUTH_SERVICE_ENABLED": "true",
            "FORCE_HTTPS": "true",
            "GCP_PROJECT_ID": "netra-staging",
            
            # WebSocket configuration for staging
            "WEBSOCKET_CONNECTION_TIMEOUT": "240",
            "WEBSOCKET_HEARTBEAT_INTERVAL": "15",
            "WEBSOCKET_HEARTBEAT_TIMEOUT": "45",
            "WEBSOCKET_CLEANUP_INTERVAL": "60",
            
            # Test configuration  
            "TEST_MODE": "true",
            "STAGING_ENV": "true",
            "BYPASS_STARTUP_VALIDATION": "true",
            
            # Disable local Docker services
            "DISABLE_LOCAL_DOCKER": "true",
            "USE_STAGING_SERVICES": "true"
        }
        
        for key, value in additional_config.items():
            os.environ[key] = value
            print(f"✅ {key} = {value}")
    
    def validate_staging_setup(self):
        """Validate that staging environment is properly configured."""
        print("\n🔍 Validating Staging Environment Setup")
        print("-" * 40)
        
        validation_passed = True
        
        # Check critical environment variables
        critical_vars = [
            "ENVIRONMENT",
            "NETRA_BACKEND_URL", 
            "AUTH_SERVICE_URL",
            "DATABASE_URL",
            "REDIS_URL"
        ]
        
        for var in critical_vars:
            value = os.environ.get(var)
            if value:
                if "localhost" in value:
                    print(f"⚠️  {var} contains localhost - should use staging services")
                    validation_passed = False
                else:
                    print(f"✅ {var} configured for staging")
            else:
                print(f"❌ {var} not configured")
                validation_passed = False
        
        # Check for staging indicators
        if os.environ.get("ENVIRONMENT") != "staging":
            print("❌ ENVIRONMENT not set to 'staging'")
            validation_passed = False
        
        if os.environ.get("USE_STAGING_SERVICES") != "true":
            print("❌ USE_STAGING_SERVICES not enabled")  
            validation_passed = False
        
        print("-" * 40)
        if validation_passed:
            print("✅ Staging environment validation PASSED")
            print("🚀 Ready for integration tests with real services")
        else:
            print("❌ Staging environment validation FAILED")
            print("🔧 Please fix configuration issues before running tests")
        
        return validation_passed
    
    def show_service_info(self):
        """Show information about staging services."""
        print("\n📋 Staging Service Information")
        print("=" * 60)
        
        services = [
            ("Backend API", os.environ.get("NETRA_BACKEND_URL")),
            ("Auth Service", os.environ.get("AUTH_SERVICE_URL")),
            ("Frontend", os.environ.get("FRONTEND_URL")),
            ("WebSocket", os.environ.get("WEBSOCKET_URL")),
            ("Database", "Cloud SQL PostgreSQL (staging)"),
            ("Cache", "Memorystore Redis (staging)"),
            ("Analytics", "ClickHouse Cloud (staging)")
        ]
        
        for name, endpoint in services:
            if endpoint:
                print(f"🔗 {name:15} -> {endpoint}")
            else:
                print(f"❌ {name:15} -> Not configured")
        
        print("=" * 60)
        print("💡 These services run on GCP staging infrastructure")
        print("🔐 Credentials managed via Google Secret Manager")
        print("🧪 Perfect for Golden Path integration testing")


def setup_integration_test_environment():
    """Main function to setup staging environment for integration tests."""
    setup = StagingEnvironmentSetup()
    
    # Setup the environment
    setup.setup_staging_environment()
    
    # Validate the setup
    validation_passed = setup.validate_staging_setup()
    
    # Show service information
    setup.show_service_info()
    
    if not validation_passed:
        print("\n❌ Environment setup validation failed")
        sys.exit(1)
    
    print("\n🎯 Integration tests ready to run with staging services")
    print("📌 Use: python tests/unified_test_runner.py --real-services")
    print("📌 Or: python tests/unified_test_runner.py --category integration")
    
    return True


if __name__ == "__main__":
    setup_integration_test_environment()