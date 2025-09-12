#!/usr/bin/env python3
"""
Validates and tests the database connection for staging environment.
Fetches the actual secret from Google Cloud and tests connectivity.

**UPDATED**: Now uses DatabaseURLBuilder for centralized URL construction.
"""

import asyncio
import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Optional, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StagingDatabaseValidator:
    """Validates staging database connection and credentials."""
    
    def __init__(self):
        self.project_id = "netra-staging"
        self.region = "us-central1"
        self.instance_name = "staging-shared-postgres"
        self.database_name = "postgres"
        self.env = get_env()
        
    def fetch_secret_from_gcp(self, secret_name: str) -> Optional[str]:
        """Fetch a secret from Google Cloud Secret Manager."""
        try:
            cmd = [
                "gcloud", "secrets", "versions", "access", "latest",
                "--secret", secret_name,
                "--project", self.project_id
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            return result.stdout.strip()
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch secret {secret_name}: {e}")
            logger.error(f"Error output: {e.stderr}")
            return None
    
    def parse_database_url(self, url: str) -> dict:
        """Parse a database URL into components."""
        try:
            parsed = urlparse(url)
            
            # Handle special case for Cloud SQL Unix socket URLs
            if '/cloudsql/' in url:
                # Extract host from query parameters
                query_params = {}
                if parsed.query:
                    for param in parsed.query.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            query_params[key] = value
                
                return {
                    'scheme': parsed.scheme,
                    'username': parsed.username or 'postgres',
                    'password': unquote(parsed.password) if parsed.password else None,
                    'database': parsed.path.lstrip('/') if parsed.path else self.database_name,
                    'host': query_params.get('host', ''),
                    'port': parsed.port or 5432,
                    'is_unix_socket': True,
                    'query': parsed.query
                }
            else:
                return {
                    'scheme': parsed.scheme,
                    'username': parsed.username or 'postgres',
                    'password': unquote(parsed.password) if parsed.password else None,
                    'host': parsed.hostname or 'localhost',
                    'port': parsed.port or 5432,
                    'database': parsed.path.lstrip('/') if parsed.path else self.database_name,
                    'is_unix_socket': False,
                    'query': parsed.query
                }
        except Exception as e:
            logger.error(f"Failed to parse URL: {e}")
            return {}
    
    def build_correct_database_url(self, username: str, password: str) -> str:
        """Build the correct database URL for Cloud SQL using DatabaseURLBuilder."""
        # Build environment variables dict for DatabaseURLBuilder
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": f"/cloudsql/{self.project_id}:{self.region}:{self.instance_name}",
            "POSTGRES_USER": username,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": self.database_name,
        }
        
        # Create builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid:
            logger.error(f"Database configuration error: {error_msg}")
            return ""
        
        # Get URL for staging environment (sync version)
        url = builder.get_url_for_environment(sync=True)
        
        if not url:
            logger.error("Failed to generate database URL")
            return ""
        
        return url
    
    async def test_connection_with_asyncpg(self, url: str) -> bool:
        """Test database connection using asyncpg."""
        try:
            import asyncpg
            
            # Parse the URL for asyncpg
            parsed = self.parse_database_url(url)
            
            if parsed['is_unix_socket']:
                # For Unix socket connections
                conn = await asyncpg.connect(
                    host=parsed['host'],
                    database=parsed['database'],
                    user=parsed['username'],
                    password=parsed['password']
                )
            else:
                # For TCP connections
                conn = await asyncpg.connect(
                    host=parsed['host'],
                    port=parsed['port'],
                    database=parsed['database'],
                    user=parsed['username'],
                    password=parsed['password']
                )
            
            # Test the connection
            version = await conn.fetchval('SELECT version()')
            logger.info(f" PASS:  Connection successful with asyncpg")
            logger.info(f"   PostgreSQL version: {version[:50]}...")
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  asyncpg connection failed: {e}")
            return False
    
    async def test_connection_with_sqlalchemy(self, url: str) -> bool:
        """Test database connection using SQLAlchemy."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            
            # Convert to asyncpg URL format using DatabaseURLBuilder
            env_vars = {
                "ENVIRONMENT": "staging",
                "DATABASE_URL": url,
            }
            builder = DatabaseURLBuilder(env_vars)
            async_url = builder.get_url_for_environment(sync=False)
            
            # Remove SSL parameters for Unix socket connections
            if '/cloudsql/' in async_url:
                async_url = async_url.replace('sslmode=require', '').replace('?&', '?').rstrip('?&')
            
            engine = create_async_engine(
                async_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=1,
                max_overflow=0
            )
            
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT current_user, current_database()"))
                row = result.fetchone()
                logger.info(f" PASS:  Connection successful with SQLAlchemy")
                logger.info(f"   Current user: {row[0]}")
                logger.info(f"   Current database: {row[1]}")
            
            await engine.dispose()
            return True
            
        except Exception as e:
            logger.error(f" FAIL:  SQLAlchemy connection failed: {e}")
            return False
    
    def validate_and_fix_secret(self) -> Tuple[bool, Optional[str]]:
        """Validate the database-url-staging secret and fix if needed."""
        logger.info("\n" + "="*60)
        logger.info("STAGING DATABASE CONNECTION VALIDATION")
        logger.info("="*60)
        
        # Fetch the current #removed-legacyfrom staging secret
        logger.info("\n1. Fetching #removed-legacyfrom Google Secret Manager...")
        database_url = self.fetch_secret_from_gcp("database-url-staging")
        
        if not database_url:
            logger.error("    FAIL:  Failed to fetch database-url-staging secret")
            logger.info("\n   Creating new secret...")
            
            # Get the password from a different secret or use a known value
            password = self.fetch_secret_from_gcp("postgres-password-staging")
            if not password:
                # Use the password from the debug script (this should be replaced with the actual password)
                password = "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K"
                logger.warning("    WARNING: [U+FE0F] Using hardcoded password - this should be updated!")
            
            database_url = self.build_correct_database_url("postgres", password)
            logger.info(f"   Generated URL: {database_url[:50]}...")
            
        else:
            logger.info(f"    PASS:  Retrieved database URL from secret")
            
            # Parse and validate the URL
            parsed = self.parse_database_url(database_url)
            logger.info(f"\n2. Validating URL components:")
            logger.info(f"   Username: {parsed.get('username', 'NOT SET')}")
            logger.info(f"   Password: {'SET' if parsed.get('password') else 'NOT SET'}")
            logger.info(f"   Database: {parsed.get('database', 'NOT SET')}")
            logger.info(f"   Host: {parsed.get('host', 'NOT SET')[:50]}...")
            logger.info(f"   Unix Socket: {parsed.get('is_unix_socket', False)}")
            
            # Check for common issues
            issues = []
            if not parsed.get('password'):
                issues.append("Missing password")
            if 'localhost' in database_url.lower():
                issues.append("Contains 'localhost' (not allowed in staging)")
            if not parsed.get('is_unix_socket') and 'sslmode' not in database_url:
                issues.append("Missing SSL mode for TCP connection")
            if parsed.get('username') != 'postgres':
                issues.append(f"Unexpected username: {parsed.get('username')}")
            
            if issues:
                logger.warning(f"\n    WARNING: [U+FE0F] Issues found: {', '.join(issues)}")
                
                # Try to fix the URL
                logger.info("\n   Attempting to fix the URL...")
                password = parsed.get('password')
                if not password:
                    password = self.fetch_secret_from_gcp("postgres-password-staging")
                    if not password:
                        password = "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K"
                
                database_url = self.build_correct_database_url("postgres", password)
                logger.info(f"   Fixed URL: {database_url[:50]}...")
        
        return True, database_url
    
    async def run_validation(self):
        """Run the complete validation process."""
        success, database_url = self.validate_and_fix_secret()
        
        if not success or not database_url:
            logger.error("\n FAIL:  Failed to get valid database URL")
            return False
        
        # Test the connection
        logger.info("\n3. Testing database connection...")
        
        # Test with asyncpg
        logger.info("\n   Testing with asyncpg...")
        asyncpg_success = await self.test_connection_with_asyncpg(database_url)
        
        # Test with SQLAlchemy
        logger.info("\n   Testing with SQLAlchemy...")
        sqlalchemy_success = await self.test_connection_with_sqlalchemy(database_url)
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*60)
        logger.info(f"asyncpg connection: {' PASS:  SUCCESS' if asyncpg_success else ' FAIL:  FAILED'}")
        logger.info(f"SQLAlchemy connection: {' PASS:  SUCCESS' if sqlalchemy_success else ' FAIL:  FAILED'}")
        
        if asyncpg_success and sqlalchemy_success:
            logger.info("\n PASS:  Database connection is working correctly!")
            logger.info("\nNext steps:")
            logger.info("1. Update the database-url-staging secret if needed")
            logger.info("2. Redeploy services to use the correct credentials")
            
            # Offer to update the secret
            logger.info("\n" + "="*60)
            logger.info("UPDATE SECRET COMMAND")
            logger.info("="*60)
            logger.info("To update the secret in Google Cloud, run:")
            logger.info(f"\necho '{database_url}' | gcloud secrets versions add database-url-staging --data-file=- --project={self.project_id}")
            
        else:
            logger.error("\n FAIL:  Database connection validation failed!")
            logger.error("\nTroubleshooting steps:")
            logger.error("1. Check if the postgres password is correct")
            logger.error("2. Verify Cloud SQL instance is running")
            logger.error("3. Check IAM permissions for the service account")
        
        return asyncpg_success and sqlalchemy_success


def main():
    """Main entry point."""
    validator = StagingDatabaseValidator()
    success = asyncio.run(validator.run_validation())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()