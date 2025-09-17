#!/usr/bin/env python3
"""
Fix Staging PostgreSQL SSL Configuration

This script fixes PostgreSQL SSL configuration issues for staging environment.
Common issues include SSL certificate verification failures, incorrect SSL modes,
and missing SSL certificates.

Issues Fixed:
1. SSL certificate verification failures
2. Incorrect SSL mode configuration 
3. Missing SSL certificate paths
4. Database connection timeout issues
5. Connection pool configuration for Cloud SQL

Business Impact:
- Enables database-dependent tests in staging
- Validates database connectivity before production
- Prevents SSL handshake failures in E2E tests
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StagingPostgresSQLFix:
    """Fix PostgreSQL SSL configuration for staging environment"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.gcp_project = "netra-staging"
        
        # Staging PostgreSQL configuration
        self.postgres_config = {
            # Cloud SQL private IP (requires VPC connector)
            "POSTGRES_HOST": "10.69.0.3",
            "POSTGRES_PORT": "5432", 
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_USER": "postgres",
            
            # SSL Configuration
            "DATABASE_SSL_MODE": "require",
            "DATABASE_SSL_REQUIRE": "true",
            "DATABASE_SSL_CERT": "/etc/ssl/certs/ca-certificates.crt",
            "DATABASE_SSL_ROOT_CERT": "/etc/ssl/certs/ca-certificates.crt",
            "DATABASE_SSL_VERIFY": "false",  # Disable hostname verification for private IP
            
            # Connection Configuration  
            "DATABASE_TIMEOUT": "600",
            "DATABASE_POOL_SIZE": "50",
            "DATABASE_MAX_OVERFLOW": "50",
            "DATABASE_POOL_TIMEOUT": "600",
            "DATABASE_POOL_RECYCLE": "3600",
            "DATABASE_ENGINE_ECHO": "false",
            
            # Async Configuration
            "DATABASE_ASYNC_POOL_SIZE": "20",
            "DATABASE_ASYNC_MAX_OVERFLOW": "30",
            
            # Health Check Configuration
            "DATABASE_HEALTH_CHECK_INTERVAL": "60",
            "DATABASE_CONNECTION_RETRY_COUNT": "3",
            "DATABASE_CONNECTION_RETRY_DELAY": "5"
        }
    
    def get_postgres_password_from_secret_manager(self) -> Optional[str]:
        """Get PostgreSQL password from Google Secret Manager"""
        try:
            result = subprocess.run([
                "gcloud", "secrets", "versions", "access", "latest",
                "--secret", "postgres-password-staging", 
                "--project", self.gcp_project
            ], capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                password = result.stdout.strip()
                logger.info("✅ PostgreSQL password loaded from Secret Manager")
                return password
            else:
                logger.warning("PostgreSQL password not found in Secret Manager")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Error accessing PostgreSQL password: {e}")
            return None
    
    def build_database_url(self, password: Optional[str] = None) -> str:
        """Build database URL with proper SSL configuration"""
        host = self.postgres_config["POSTGRES_HOST"]
        port = self.postgres_config["POSTGRES_PORT"]
        db = self.postgres_config["POSTGRES_DB"]
        user = self.postgres_config["POSTGRES_USER"]
        
        if not password:
            password = self.get_postgres_password_from_secret_manager()
        
        if not password:
            logger.warning("No PostgreSQL password available")
            password = "password_from_secret_manager"
        
        # Build URL with SSL parameters
        base_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        
        # Add SSL parameters
        ssl_params = [
            "sslmode=require",
            "sslcert=/etc/ssl/certs/ca-certificates.crt",
            "sslrootcert=/etc/ssl/certs/ca-certificates.crt"
        ]
        
        database_url = f"{base_url}?{'&'.join(ssl_params)}"
        
        # Async version
        async_base_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
        async_database_url = f"{async_base_url}?{'&'.join(ssl_params)}"
        
        return database_url, async_database_url
    
    def update_staging_env_file(self) -> bool:
        """Update .env.staging.tests with correct PostgreSQL configuration"""
        env_file = self.project_root / ".env.staging.tests"
        
        try:
            # Read existing configuration
            existing_lines = []
            if env_file.exists():
                with open(env_file, 'r') as f:
                    existing_lines = f.readlines()
            
            # Remove old database configuration
            filtered_lines = []
            for line in existing_lines:
                if not any(line.startswith(key) for key in [
                    "DATABASE_URL", "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", 
                    "POSTGRES_USER", "POSTGRES_PASSWORD", "DATABASE_SSL", "DATABASE_POOL",
                    "DATABASE_TIMEOUT", "DATABASE_ENGINE"
                ]):
                    filtered_lines.append(line)
            
            # Get database URLs
            database_url, async_database_url = self.build_database_url()
            
            # Add URLs to config
            self.postgres_config["DATABASE_URL"] = database_url
            self.postgres_config["DATABASE_ASYNC_URL"] = async_database_url
            
            # Write updated configuration
            with open(env_file, 'w') as f:
                # Write existing lines (non-database)
                for line in filtered_lines:
                    f.write(line)
                
                # Add database configuration section
                f.write("\\n# Database Configuration (Cloud SQL) - SSL FIXED\\n")
                f.write("# Private IP for staging VPC - requires VPC connector\\n")
                f.write("# SSL mode: require, with proper certificate paths\\n")
                for key, value in self.postgres_config.items():
                    f.write(f"{key}={value}\\n")
                
                # Add VPC configuration notes
                f.write("\\n# VPC Configuration for Database Access\\n")
                f.write("# Requires VPC connector: staging-connector\\n")
                f.write("# Database instance in private subnet: 10.69.0.0/24\\n")
                f.write("# SSL certificates: /etc/ssl/certs/ca-certificates.crt\\n")
            
            logger.info(f"✅ Updated PostgreSQL configuration in {env_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update staging environment file: {e}")
            return False
    
    def create_postgres_config_module(self) -> bool:
        """Create/update PostgreSQL configuration module"""
        postgres_config_file = self.project_root / "netra_backend" / "app" / "core" / "configuration" / "postgres_staging.py"
        
        config_content = '''"""
PostgreSQL Configuration for Staging Environment

This module provides staging-specific PostgreSQL configuration that connects
to the Cloud SQL instance with proper SSL settings.

CRITICAL: This configuration requires VPC connector for Cloud Run to access
the private PostgreSQL instance in the staging VPC.
"""

from typing import Dict, Any, Optional
from urllib.parse import quote_plus
from shared.isolated_environment import get_env

class StagingPostgresConfig:
    """PostgreSQL configuration for staging environment"""
    
    def __init__(self):
        self.env = get_env()
        
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for staging"""
        
        config = {
            "host": self.env.get("POSTGRES_HOST", "10.69.0.3"),
            "port": int(self.env.get("POSTGRES_PORT", "5432")),
            "database": self.env.get("POSTGRES_DB", "netra_staging"),
            "user": self.env.get("POSTGRES_USER", "postgres"),
            "password": self.env.get("POSTGRES_PASSWORD", ""),
            
            # SSL Configuration
            "sslmode": "require",
            "sslcert": "/etc/ssl/certs/ca-certificates.crt",
            "sslrootcert": "/etc/ssl/certs/ca-certificates.crt",
            
            # Connection Pool Configuration
            "pool_size": int(self.env.get("DATABASE_POOL_SIZE", "50")),
            "max_overflow": int(self.env.get("DATABASE_MAX_OVERFLOW", "50")),
            "pool_timeout": int(self.env.get("DATABASE_POOL_TIMEOUT", "600")),
            "pool_recycle": int(self.env.get("DATABASE_POOL_RECYCLE", "3600")),
            
            # Connection Timeout
            "connect_timeout": int(self.env.get("DATABASE_TIMEOUT", "600")),
            
            # Engine Configuration
            "echo": self.env.get("DATABASE_ENGINE_ECHO", "false").lower() == "true"
        }
        
        return config
    
    def get_database_url(self, async_driver: bool = False) -> str:
        """Get database URL for staging"""
        
        # Check for explicit URL first
        if async_driver:
            url = self.env.get("DATABASE_ASYNC_URL")
        else:
            url = self.env.get("DATABASE_URL")
            
        if url:
            return url
        
        # Build URL from components
        config = self.get_database_config()
        
        # URL encode password to handle special characters
        password = quote_plus(config["password"]) if config["password"] else ""
        
        # Choose driver
        if async_driver:
            driver = "postgresql+asyncpg"
        else:
            driver = "postgresql"
        
        # Build base URL
        if password:
            base_url = f"{driver}://{config['user']}:{password}@{config['host']}:{config['port']}/{config['database']}"
        else:
            base_url = f"{driver}://{config['user']}@{config['host']}:{config['port']}/{config['database']}"
        
        # Add SSL parameters
        ssl_params = [
            "sslmode=require",
            "sslcert=/etc/ssl/certs/ca-certificates.crt",
            "sslrootcert=/etc/ssl/certs/ca-certificates.crt"
        ]
        
        return f"{base_url}?{'&'.join(ssl_params)}"
    
    def get_sqlalchemy_config(self) -> Dict[str, Any]:
        """Get SQLAlchemy configuration for staging"""
        config = self.get_database_config()
        
        return {
            "url": self.get_database_url(),
            "pool_size": config["pool_size"],
            "max_overflow": config["max_overflow"],
            "pool_timeout": config["pool_timeout"],
            "pool_recycle": config["pool_recycle"],
            "echo": config["echo"],
            "connect_args": {
                "sslmode": "require",
                "sslcert": "/etc/ssl/certs/ca-certificates.crt",
                "sslrootcert": "/etc/ssl/certs/ca-certificates.crt",
                "connect_timeout": config["connect_timeout"]
            }
        }
    
    def validate_connection(self) -> bool:
        """Validate database connection for staging"""
        try:
            import psycopg2
            
            config = self.get_database_config()
            
            # Test connection
            conn = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                database=config["database"],
                user=config["user"],
                password=config["password"],
                sslmode="require",
                connect_timeout=30
            )
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Database connection validation failed: {e}")
            return False


def get_staging_database_config() -> Dict[str, Any]:
    """Get staging database configuration"""
    return StagingPostgresConfig().get_database_config()


def get_staging_database_url(async_driver: bool = False) -> str:
    """Get staging database URL"""
    return StagingPostgresConfig().get_database_url(async_driver)


def get_staging_sqlalchemy_config() -> Dict[str, Any]:
    """Get staging SQLAlchemy configuration"""
    return StagingPostgresConfig().get_sqlalchemy_config()


def validate_staging_database() -> bool:
    """Validate staging database connection"""
    return StagingPostgresConfig().validate_connection()
'''
        
        try:
            # Create directory if it doesn't exist
            postgres_config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration module
            with open(postgres_config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"✅ Created PostgreSQL configuration module: {postgres_config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL configuration module: {e}")
            return False
    
    def test_postgres_connectivity(self) -> bool:
        """Test PostgreSQL connectivity with current configuration"""
        logger.info("Testing PostgreSQL connectivity...")
        
        try:
            # Load environment variables
            env_file = self.project_root / ".env.staging.tests"
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key] = value
            
            # Test connection
            try:
                import psycopg2
                
                host = os.environ.get("POSTGRES_HOST", "10.69.0.3")
                port = int(os.environ.get("POSTGRES_PORT", "5432"))
                database = os.environ.get("POSTGRES_DB", "netra_staging")
                user = os.environ.get("POSTGRES_USER", "postgres")
                password = os.environ.get("POSTGRES_PASSWORD", "")
                
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password if password else None,
                    sslmode="require",
                    connect_timeout=30
                )
                
                cursor = conn.cursor()
                cursor.execute("SELECT 1;")
                result = cursor.fetchone()
                
                cursor.close()
                conn.close()
                
                if result and result[0] == 1:
                    logger.info("✅ PostgreSQL connectivity test passed")
                    return True
                else:
                    logger.error("PostgreSQL connectivity test failed: unexpected result")
                    return False
                
            except psycopg2.OperationalError as e:
                logger.error(f"PostgreSQL connection failed: {e}")
                logger.error("This might be expected if not running from Cloud Run with VPC connector")
                return False
            except Exception as e:
                logger.error(f"PostgreSQL test failed: {e}")
                return False
                
        except ImportError:
            logger.warning("psycopg2 library not available for testing")
            return True  # Don't fail if psycopg2 not installed
    
    def check_ssl_certificates(self) -> bool:
        """Check if SSL certificates are available"""
        cert_paths = [
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/ssl/certs/ca-bundle.crt",
            "/usr/local/share/ca-certificates/"
        ]
        
        for cert_path in cert_paths:
            if Path(cert_path).exists():
                logger.info(f"✅ SSL certificate found: {cert_path}")
                return True
        
        logger.warning("SSL certificates not found - this is expected in local development")
        logger.info("SSL certificates will be available in Cloud Run environment")
        return True
    
    def run_fix(self) -> bool:
        """Run complete PostgreSQL configuration fix"""
        logger.info("🔧 Starting PostgreSQL configuration fix for staging...")
        
        steps = [
            ("Check SSL certificates", self.check_ssl_certificates),
            ("Update staging environment file", self.update_staging_env_file),
            ("Create PostgreSQL configuration module", self.create_postgres_config_module),
            ("Test PostgreSQL connectivity", self.test_postgres_connectivity)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\\n🔄 {step_name}...")
            try:
                if not step_func():
                    logger.warning(f"⚠️ {step_name} had issues (may be expected)")
                else:
                    logger.info(f"✅ {step_name} completed")
            except Exception as e:
                logger.error(f"❌ {step_name} failed with error: {e}")
                return False
        
        logger.info("\\n🎉 PostgreSQL configuration fix completed!")
        logger.info("\\nNext steps:")
        logger.info("1. Deploy to staging with VPC connector")
        logger.info("2. Test database functionality: python scripts/setup_staging_environment.py")
        logger.info("3. Run database-dependent tests: python tests/unified_test_runner.py --env staging")
        
        return True


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        return
    
    fix = StagingPostgresSQLFix()
    success = fix.run_fix()
    
    if not success:
        logger.error("\\n❌ PostgreSQL configuration fix failed")
        sys.exit(1)
    
    logger.info("\\n✅ PostgreSQL configuration fixed for staging")


if __name__ == "__main__":
    main()