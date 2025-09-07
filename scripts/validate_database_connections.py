#!/usr/bin/env python
"""
Database Connection Validation Script
=====================================

This script validates database connectivity for all environments,
specifically focusing on staging issues.

CRITICAL MISSION: Fix staging database connectivity
- Test PostgreSQL connections
- Test Redis connections
- Test ClickHouse connections
- Validate configuration per environment
- Generate detailed reports

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Stability - Ensure core data persistence works
- Value Impact: Prevents data loss and system failures
- Strategic Impact: Foundation for all other services
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Import our utilities
from shared.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseConnectionValidator:
    """
    Comprehensive database connection validator.
    
    Tests all database connections (PostgreSQL, Redis, ClickHouse)
    across all environments with detailed reporting.
    """
    
    def __init__(self, environment: str = "staging"):
        """Initialize validator for specific environment."""
        self.environment = environment.lower()
        self.env = get_env()
        self.results: Dict[str, Any] = {
            'environment': self.environment,
            'timestamp': datetime.utcnow().isoformat(),
            'postgresql': {},
            'redis': {},
            'clickhouse': {},
            'configuration': {},
            'overall_status': 'unknown'
        }
        
        # Load environment-specific configuration
        self._load_environment_config()
        
        logger.info(f"DatabaseConnectionValidator initialized for {self.environment}")
    
    def _load_environment_config(self) -> None:
        """Load environment-specific configuration file."""
        env_file = PROJECT_ROOT / f".env.{self.environment}"
        backup_env_file = PROJECT_ROOT / f".env.{self.environment}.backup" 
        template_env_file = PROJECT_ROOT / f".env.{self.environment}.template"
        
        # CRITICAL: Prioritize the main .env.staging file over backup
        loaded_file = None
        if env_file.exists():
            loaded_file = env_file
            logger.info(f"Loading primary environment file: {env_file}")
        elif backup_env_file.exists():
            loaded_file = backup_env_file
            logger.warning(f"Using backup environment file: {backup_env_file}")
        elif template_env_file.exists():
            loaded_file = template_env_file
            logger.warning(f"Using template environment file: {template_env_file}")
        
        if loaded_file:
            try:
                # Load using IsolatedEnvironment
                load_count, errors = self.env.load_from_file(loaded_file, override_existing=True)
                if load_count > 0:
                    logger.info(f"Loaded {load_count} variables from {loaded_file}")
                if errors:
                    for error in errors:
                        logger.warning(f"Config load warning: {error}")
                        
                self.results['configuration']['loaded_from'] = str(loaded_file)
                self.results['configuration']['variables_loaded'] = load_count
                self.results['configuration']['load_errors'] = errors
            except Exception as e:
                logger.error(f"Failed to load environment file {loaded_file}: {e}")
                self.results['configuration']['load_error'] = str(e)
        else:
            logger.warning(f"No environment file found for {self.environment}")
            self.results['configuration']['load_error'] = f"No .env file found for {self.environment}"
    
    async def validate_postgresql(self) -> Dict[str, Any]:
        """Validate PostgreSQL connectivity."""
        logger.info("Validating PostgreSQL connectivity...")
        
        postgresql_result = {
            'status': 'unknown',
            'connection_test': None,
            'configuration_validation': None,
            'url_builder_analysis': None,
            'staging_specific_issues': [],
            'recommendations': []
        }
        
        try:
            # Create DatabaseURLBuilder
            env_dict = self.env.as_dict()
            url_builder = DatabaseURLBuilder(env_dict)
            
            # Get URL builder analysis
            postgresql_result['url_builder_analysis'] = {
                'environment': url_builder.environment,
                'has_cloud_sql': url_builder.cloud_sql.is_cloud_sql,
                'has_tcp_config': url_builder.tcp.has_config,
                'debug_info': url_builder.debug_info()
            }
            
            # Validate configuration
            is_valid, error_msg = url_builder.validate()
            postgresql_result['configuration_validation'] = {
                'is_valid': is_valid,
                'error_message': error_msg,
                'postgres_host': url_builder.postgres_host,
                'postgres_port': url_builder.postgres_port,
                'postgres_db': url_builder.postgres_db,
                'postgres_user': url_builder.postgres_user,
                'postgres_password': '***' if url_builder.postgres_password else None
            }
            
            # Check for staging-specific issues
            if self.environment == "staging":
                postgresql_result['staging_specific_issues'] = self._check_staging_postgresql_issues(url_builder)
            
            # Get database URL
            database_url = url_builder.get_url_for_environment(sync=False)
            if database_url:
                masked_url = url_builder.mask_url_for_logging(database_url)
                logger.info(f"Database URL: {masked_url}")
                
                # Test connection
                connection_test = await self._test_postgresql_connection(database_url)
                postgresql_result['connection_test'] = connection_test
                
                if connection_test['connected']:
                    postgresql_result['status'] = 'healthy'
                else:
                    postgresql_result['status'] = 'failed'
                    postgresql_result['recommendations'].append(
                        "Check database credentials and network connectivity"
                    )
            else:
                postgresql_result['status'] = 'configuration_error'
                postgresql_result['connection_test'] = {
                    'connected': False,
                    'error': 'Could not construct database URL from configuration'
                }
                postgresql_result['recommendations'].append(
                    "Verify POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD environment variables are properly set"
                )
                
        except Exception as e:
            logger.error(f"PostgreSQL validation failed: {e}")
            postgresql_result['status'] = 'validation_error'
            postgresql_result['error'] = str(e)
        
        self.results['postgresql'] = postgresql_result
        return postgresql_result
    
    def _check_staging_postgresql_issues(self, url_builder: DatabaseURLBuilder) -> List[str]:
        """Check for known staging PostgreSQL issues."""
        issues = []
        
        # Issue 1: localhost in staging
        if url_builder.postgres_host == "localhost":
            issues.append("CRITICAL: Using localhost for database host in staging - should use Cloud SQL or proper staging database host")
        
        # Issue 2: Known problematic user patterns
        if url_builder.postgres_user and url_builder.postgres_user.startswith("user_pr-"):
            issues.append(f"CRITICAL: Invalid user pattern '{url_builder.postgres_user}' - known to cause authentication failures")
        
        # Issue 3: Development passwords in staging
        if url_builder.postgres_password == "postgres":
            issues.append("WARNING: Using development password 'postgres' in staging - should use secure staging password")
        
        # Issue 4: Missing environment variables
        required_vars = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
        missing_vars = []
        for var in required_vars:
            if not self.env.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            issues.append(f"CRITICAL: Missing required environment variables: {missing_vars}")
        
        # Issue 5: Port configuration
        postgres_port = url_builder.postgres_port
        if postgres_port == "5435":  # Test port being used in staging
            issues.append("WARNING: Using test port 5435 in staging - verify this is correct")
        
        return issues
    
    async def _test_postgresql_connection(self, database_url: str) -> Dict[str, Any]:
        """Test PostgreSQL connection."""
        connection_result = {
            'connected': False,
            'error': None,
            'response_time_ms': None,
            'server_version': None,
            'database_name': None
        }
        
        try:
            # Use asyncpg directly for connection test
            import asyncpg
            from urllib.parse import urlparse
            
            # Parse URL for asyncpg
            parsed = urlparse(database_url)
            
            # Remove SQLAlchemy driver prefix if present
            clean_url = database_url
            if "postgresql+asyncpg://" in database_url:
                clean_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            
            start_time = datetime.utcnow()
            
            # Connect with timeout
            conn = await asyncio.wait_for(
                asyncpg.connect(clean_url),
                timeout=10.0
            )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Test basic query
            server_version = await conn.fetchval("SELECT version()")
            database_name = await conn.fetchval("SELECT current_database()")
            
            await conn.close()
            
            connection_result.update({
                'connected': True,
                'response_time_ms': round(response_time, 2),
                'server_version': server_version,
                'database_name': database_name
            })
            
            logger.info(f"PostgreSQL connection successful - {database_name} in {response_time:.2f}ms")
            
        except asyncio.TimeoutError:
            error_msg = "Connection timeout (10s)"
            connection_result['error'] = error_msg
            logger.error(f"PostgreSQL connection timeout: {error_msg}")
        except ImportError as e:
            error_msg = f"asyncpg not available: {e}"
            connection_result['error'] = error_msg
            logger.error(f"PostgreSQL connection test failed: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            connection_result['error'] = error_msg
            logger.error(f"PostgreSQL connection failed: {error_msg}")
        
        return connection_result
    
    async def validate_redis(self) -> Dict[str, Any]:
        """Validate Redis connectivity."""
        logger.info("Validating Redis connectivity...")
        
        redis_result = {
            'status': 'unknown',
            'connection_test': None,
            'configuration': {},
            'staging_specific_issues': [],
            'recommendations': []
        }
        
        try:
            # Get Redis configuration
            redis_host = self.env.get("REDIS_HOST", "")
            redis_port = self.env.get("REDIS_PORT", "6379")
            redis_password = self.env.get("REDIS_PASSWORD", "")
            redis_db = self.env.get("REDIS_DB", "0")
            redis_url = self.env.get("REDIS_URL", "")
            
            redis_result['configuration'] = {
                'redis_host': redis_host,
                'redis_port': redis_port,
                'redis_db': redis_db,
                'redis_password': '***' if redis_password else None,
                'redis_url': redis_url[:50] + "..." if len(redis_url) > 50 else redis_url
            }
            
            # Check for staging-specific issues
            if self.environment == "staging":
                if redis_host in ["localhost", "127.0.0.1"]:
                    redis_result['staging_specific_issues'].append(
                        "WARNING: Using localhost for Redis in staging - should use staging Redis instance"
                    )
                
                if "staging-redis" in redis_host:
                    redis_result['staging_specific_issues'].append(
                        "INFO: Using staging-redis hostname - verify this resolves correctly"
                    )
            
            # Test connection
            if redis_host or redis_url:
                connection_test = await self._test_redis_connection(redis_host, redis_port, redis_password, redis_db, redis_url)
                redis_result['connection_test'] = connection_test
                
                if connection_test['connected']:
                    redis_result['status'] = 'healthy'
                else:
                    redis_result['status'] = 'failed'
                    redis_result['recommendations'].append(
                        "Check Redis connection settings and network connectivity"
                    )
            else:
                redis_result['status'] = 'not_configured'
                redis_result['recommendations'].append(
                    "Redis not configured - set REDIS_HOST or REDIS_URL if Redis is required"
                )
                
        except Exception as e:
            logger.error(f"Redis validation failed: {e}")
            redis_result['status'] = 'validation_error'
            redis_result['error'] = str(e)
        
        self.results['redis'] = redis_result
        return redis_result
    
    async def _test_redis_connection(self, host: str, port: str, password: str, db: str, redis_url: str) -> Dict[str, Any]:
        """Test Redis connection."""
        connection_result = {
            'connected': False,
            'error': None,
            'response_time_ms': None,
            'redis_version': None,
            'memory_usage': None
        }
        
        try:
            import redis.asyncio as redis
            
            # Create Redis client
            if redis_url:
                client = redis.from_url(redis_url, decode_responses=True)
            else:
                client = redis.Redis(
                    host=host,
                    port=int(port),
                    password=password if password else None,
                    db=int(db),
                    decode_responses=True
                )
            
            start_time = datetime.utcnow()
            
            # Test connection with timeout
            await asyncio.wait_for(client.ping(), timeout=5.0)
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Get Redis info
            info = await client.info()
            redis_version = info.get('redis_version', 'unknown')
            used_memory = info.get('used_memory_human', 'unknown')
            
            await client.aclose()
            
            connection_result.update({
                'connected': True,
                'response_time_ms': round(response_time, 2),
                'redis_version': redis_version,
                'memory_usage': used_memory
            })
            
            logger.info(f"Redis connection successful - v{redis_version} in {response_time:.2f}ms")
            
        except asyncio.TimeoutError:
            error_msg = "Connection timeout (5s)"
            connection_result['error'] = error_msg
            logger.error(f"Redis connection timeout: {error_msg}")
        except ImportError as e:
            error_msg = f"redis-py not available: {e}"
            connection_result['error'] = error_msg
            logger.error(f"Redis connection test failed: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            connection_result['error'] = error_msg
            logger.error(f"Redis connection failed: {error_msg}")
        
        return connection_result
    
    async def validate_clickhouse(self) -> Dict[str, Any]:
        """Validate ClickHouse connectivity."""
        logger.info("Validating ClickHouse connectivity...")
        
        clickhouse_result = {
            'status': 'unknown',
            'connection_test': None,
            'configuration': {},
            'staging_specific_issues': [],
            'recommendations': []
        }
        
        try:
            # Get ClickHouse configuration
            clickhouse_url = self.env.get("CLICKHOUSE_URL", "")
            clickhouse_host = self.env.get("CLICKHOUSE_HOST", "")
            clickhouse_port = self.env.get("CLICKHOUSE_PORT", "8123")
            clickhouse_user = self.env.get("CLICKHOUSE_USER", "default")
            clickhouse_password = self.env.get("CLICKHOUSE_PASSWORD", "")
            clickhouse_secure = self.env.get("CLICKHOUSE_SECURE", "false").lower() == "true"
            
            clickhouse_result['configuration'] = {
                'clickhouse_host': clickhouse_host,
                'clickhouse_port': clickhouse_port,
                'clickhouse_user': clickhouse_user,
                'clickhouse_password': '***' if clickhouse_password else None,
                'clickhouse_secure': clickhouse_secure,
                'clickhouse_url': clickhouse_url[:50] + "..." if len(clickhouse_url) > 50 else clickhouse_url
            }
            
            # Check for staging-specific issues
            if self.environment == "staging":
                if "clickhouse.cloud" in clickhouse_host:
                    clickhouse_result['staging_specific_issues'].append(
                        "INFO: Using ClickHouse Cloud for staging - verify credentials and connectivity"
                    )
                
                if clickhouse_port == "8443":
                    clickhouse_result['staging_specific_issues'].append(
                        "INFO: Using secure ClickHouse port 8443"
                    )
            
            # Test connection
            if clickhouse_host or clickhouse_url:
                connection_test = await self._test_clickhouse_connection(
                    clickhouse_url, clickhouse_host, clickhouse_port, 
                    clickhouse_user, clickhouse_password, clickhouse_secure
                )
                clickhouse_result['connection_test'] = connection_test
                
                if connection_test['connected']:
                    clickhouse_result['status'] = 'healthy'
                else:
                    clickhouse_result['status'] = 'failed'
                    clickhouse_result['recommendations'].append(
                        "Check ClickHouse connection settings and network connectivity"
                    )
            else:
                clickhouse_result['status'] = 'not_configured'
                clickhouse_result['recommendations'].append(
                    "ClickHouse not configured - set CLICKHOUSE_HOST or CLICKHOUSE_URL if ClickHouse is required"
                )
                
        except Exception as e:
            logger.error(f"ClickHouse validation failed: {e}")
            clickhouse_result['status'] = 'validation_error'
            clickhouse_result['error'] = str(e)
        
        self.results['clickhouse'] = clickhouse_result
        return clickhouse_result
    
    async def _test_clickhouse_connection(self, url: str, host: str, port: str, user: str, password: str, secure: bool) -> Dict[str, Any]:
        """Test ClickHouse connection."""
        connection_result = {
            'connected': False,
            'error': None,
            'response_time_ms': None,
            'clickhouse_version': None,
            'server_info': None
        }
        
        try:
            import aiohttp
            import urllib.parse
            
            # Build connection URL if not provided
            if not url:
                protocol = "https" if secure else "http"
                auth_part = f"{user}:{password}@" if password else f"{user}@"
                url = f"{protocol}://{auth_part}{host}:{port}/"
            
            start_time = datetime.utcnow()
            
            # Test connection with simple query
            async with aiohttp.ClientSession() as session:
                query_url = url.rstrip('/') + "/?query=SELECT%20version()"
                
                async with session.get(query_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        version_text = await response.text()
                        
                        end_time = datetime.utcnow()
                        response_time = (end_time - start_time).total_seconds() * 1000
                        
                        connection_result.update({
                            'connected': True,
                            'response_time_ms': round(response_time, 2),
                            'clickhouse_version': version_text.strip(),
                            'server_info': f"Status {response.status}"
                        })
                        
                        logger.info(f"ClickHouse connection successful in {response_time:.2f}ms")
                    else:
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        connection_result['error'] = error_msg
                        logger.error(f"ClickHouse connection failed: {error_msg}")
            
        except asyncio.TimeoutError:
            error_msg = "Connection timeout (10s)"
            connection_result['error'] = error_msg
            logger.error(f"ClickHouse connection timeout: {error_msg}")
        except ImportError as e:
            error_msg = f"aiohttp not available: {e}"
            connection_result['error'] = error_msg
            logger.error(f"ClickHouse connection test failed: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            connection_result['error'] = error_msg
            logger.error(f"ClickHouse connection failed: {error_msg}")
        
        return connection_result
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete database validation."""
        logger.info(f"Starting full database validation for {self.environment} environment")
        
        # Run all validations
        await self.validate_postgresql()
        await self.validate_redis()
        await self.validate_clickhouse()
        
        # Determine overall status
        statuses = []
        if self.results['postgresql']['status'] in ['healthy', 'not_configured']:
            statuses.append('postgresql_ok')
        else:
            statuses.append('postgresql_failed')
        
        if self.results['redis']['status'] in ['healthy', 'not_configured']:
            statuses.append('redis_ok')
        else:
            statuses.append('redis_failed')
        
        if self.results['clickhouse']['status'] in ['healthy', 'not_configured']:
            statuses.append('clickhouse_ok')
        else:
            statuses.append('clickhouse_failed')
        
        # Overall status logic
        if all('_ok' in status for status in statuses):
            if any('not_configured' in str(result['status']) for result in [
                self.results['postgresql'], self.results['redis'], self.results['clickhouse']
            ]):
                self.results['overall_status'] = 'partial'
            else:
                self.results['overall_status'] = 'healthy'
        else:
            self.results['overall_status'] = 'failed'
        
        logger.info(f"Validation complete - Overall status: {self.results['overall_status']}")
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate human-readable validation report."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"DATABASE CONNECTION VALIDATION REPORT")
        lines.append(f"Environment: {self.environment.upper()}")
        lines.append(f"Timestamp: {self.results['timestamp']}")
        lines.append(f"Overall Status: {self.results['overall_status'].upper()}")
        lines.append("=" * 80)
        
        # PostgreSQL Section
        pg = self.results['postgresql']
        lines.append("\nPOSTGRESQL")
        lines.append(f"Status: {pg['status'].upper()}")
        
        if pg.get('staging_specific_issues'):
            lines.append("Staging Issues:")
            for issue in pg['staging_specific_issues']:
                lines.append(f"  WARNING: {issue}")
        
        if pg.get('connection_test'):
            ct = pg['connection_test']
            if ct['connected']:
                lines.append(f"[SUCCESS] Connection successful ({ct['response_time_ms']}ms)")
                lines.append(f"   Database: {ct['database_name']}")
                lines.append(f"   Server: {ct['server_version'][:50]}...")
            else:
                lines.append(f"[FAILED] Connection failed: {ct['error']}")
        
        # Redis Section  
        redis = self.results['redis']
        lines.append(f"\nREDIS")
        lines.append(f"Status: {redis['status'].upper()}")
        
        if redis.get('staging_specific_issues'):
            lines.append("Staging Issues:")
            for issue in redis['staging_specific_issues']:
                lines.append(f"  WARNING: {issue}")
        
        if redis.get('connection_test'):
            ct = redis['connection_test']
            if ct['connected']:
                lines.append(f"[SUCCESS] Connection successful ({ct['response_time_ms']}ms)")
                lines.append(f"   Version: {ct['redis_version']}")
                lines.append(f"   Memory: {ct['memory_usage']}")
            else:
                lines.append(f"[FAILED] Connection failed: {ct['error']}")
        
        # ClickHouse Section
        ch = self.results['clickhouse']
        lines.append(f"\nCLICKHOUSE")
        lines.append(f"Status: {ch['status'].upper()}")
        
        if ch.get('staging_specific_issues'):
            lines.append("Staging Issues:")
            for issue in ch['staging_specific_issues']:
                lines.append(f"  WARNING: {issue}")
        
        if ch.get('connection_test'):
            ct = ch['connection_test']
            if ct['connected']:
                lines.append(f"[SUCCESS] Connection successful ({ct['response_time_ms']}ms)")
                lines.append(f"   Version: {ct['clickhouse_version']}")
            else:
                lines.append(f"[FAILED] Connection failed: {ct['error']}")
        
        # Recommendations
        all_recommendations = []
        for service in ['postgresql', 'redis', 'clickhouse']:
            service_recs = self.results[service].get('recommendations', [])
            all_recommendations.extend(service_recs)
        
        if all_recommendations:
            lines.append(f"\nRECOMMENDATIONS")
            for i, rec in enumerate(all_recommendations, 1):
                lines.append(f"{i}. {rec}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def save_report(self, report_path: Optional[Path] = None) -> Path:
        """Save validation report to file."""
        if report_path is None:
            report_path = PROJECT_ROOT / "reports" / f"database_validation_{self.environment}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Ensure reports directory exists
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save JSON results
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Save human-readable report
        txt_path = report_path.with_suffix('.txt')
        with open(txt_path, 'w') as f:
            f.write(self.generate_report())
        
        logger.info(f"Validation report saved to {report_path}")
        logger.info(f"Human-readable report saved to {txt_path}")
        
        return report_path


async def main():
    """Main validation script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Connection Validator")
    parser.add_argument("--environment", "-e", default="staging", 
                       choices=["development", "test", "staging", "production"],
                       help="Environment to validate (default: staging)")
    parser.add_argument("--output", "-o", type=Path,
                       help="Output file path for report")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Quiet mode - minimal output")
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    # Create validator
    validator = DatabaseConnectionValidator(args.environment)
    
    try:
        # Run validation
        results = await validator.run_full_validation()
        
        # Print summary
        if not args.quiet:
            print(validator.generate_report())
        
        # Save report
        report_path = validator.save_report(args.output)
        
        # Exit code based on overall status
        if results['overall_status'] == 'healthy':
            print(f"[SUCCESS] All database connections healthy for {args.environment}")
            return 0
        elif results['overall_status'] == 'partial':
            print(f"[WARNING] Some databases not configured for {args.environment}")
            return 0
        else:
            print(f"[FAILED] Database connection failures detected for {args.environment}")
            return 1
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)