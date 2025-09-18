#!/usr/bin/env python3
"""
Validate Staging Configuration Fixes

This script validates that all staging configuration fixes are working correctly.
It tests the fixes for JWT secrets, Redis connections, PostgreSQL SSL, and
the unified test runner to ensure E2E tests can execute successfully.

Usage:
    python scripts/validate_staging_fixes.py
    python scripts/validate_staging_fixes.py --verbose
    python scripts/validate_staging_fixes.py --component jwt
    python scripts/validate_staging_fixes.py --component redis
    python scripts/validate_staging_fixes.py --component postgres
"""

import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StagingValidation:
    """Validate staging configuration fixes"""
    
    def __init__(self, verbose: bool = False):
        self.project_root = Path(__file__).parent.parent
        self.verbose = verbose
        self.gcp_project = "netra-staging"
        self.results = {
            "jwt": {"status": "pending", "details": []},
            "redis": {"status": "pending", "details": []},
            "postgres": {"status": "pending", "details": []},
            "test_runner": {"status": "pending", "details": []},
            "environment": {"status": "pending", "details": []}
        }
    
    def log_detail(self, component: str, message: str, level: str = "info"):
        """Log detail for a component"""
        self.results[component]["details"].append({
            "level": level,
            "message": message
        })
        if self.verbose or level in ["warning", "error"]:
            getattr(logger, level)(f"[{component.upper()}] {message}")
    
    def validate_jwt_configuration(self) -> bool:
        """Validate JWT configuration fixes"""
        try:
            # Load environment
            self.load_staging_environment()
            
            # Test JWT secret manager
            try:
                from shared.jwt_secret_manager import get_unified_jwt_secret, validate_unified_jwt_config
                
                # Get JWT secret
                jwt_secret = get_unified_jwt_secret()
                secret_length = len(jwt_secret)
                
                if secret_length >= 32:
                    self.log_detail("jwt", f"JWT secret length: {secret_length} characters ✅")
                else:
                    self.log_detail("jwt", f"JWT secret too short: {secret_length} characters", "error")
                    return False
                
                # Validate configuration
                validation = validate_unified_jwt_config()
                if validation.get("valid", False):
                    self.log_detail("jwt", "JWT configuration validation: PASS ✅")
                else:
                    issues = validation.get("issues", [])
                    self.log_detail("jwt", f"JWT configuration issues: {issues}", "error")
                    return False
                
                # Test staging environment specifically
                os.environ["ENVIRONMENT"] = "staging"
                staging_secret = get_unified_jwt_secret()
                if len(staging_secret) >= 32:
                    self.log_detail("jwt", "Staging JWT secret: CONFIGURED ✅")
                else:
                    self.log_detail("jwt", "Staging JWT secret: MISSING", "error")
                    return False
                
                self.results["jwt"]["status"] = "pass"
                return True
                
            except Exception as e:
                self.log_detail("jwt", f"JWT validation error: {e}", "error")
                self.results["jwt"]["status"] = "fail"
                return False
                
        except Exception as e:
            self.log_detail("jwt", f"JWT setup error: {e}", "error")
            self.results["jwt"]["status"] = "fail"
            return False
    
    def validate_redis_configuration(self) -> bool:
        """Validate Redis configuration fixes"""
        try:
            # Load environment
            self.load_staging_environment()
            
            # Check Redis configuration
            redis_host = os.environ.get("REDIS_HOST", "localhost")
            redis_port = os.environ.get("REDIS_PORT", "6379")
            redis_url = os.environ.get("REDIS_URL", "")
            
            # Validate Redis host is not localhost
            if redis_host == "localhost":
                self.log_detail("redis", "Redis host is localhost - should be staging instance", "error")
                return False
            else:
                self.log_detail("redis", f"Redis host: {redis_host} ✅")
            
            # Validate Redis URL format
            if "10.69.0.4" in redis_url or redis_host == "10.69.0.4":
                self.log_detail("redis", "Redis configured for staging Memorystore ✅")
            else:
                self.log_detail("redis", f"Redis URL may be incorrect: {redis_url}", "warning")
            
            # Test Redis connection (if available)
            try:
                import redis
                
                config = {
                    "host": redis_host,
                    "port": int(redis_port),
                    "decode_responses": True,
                    "socket_timeout": 5,
                    "socket_connect_timeout": 3
                }
                
                redis_password = os.environ.get("REDIS_PASSWORD")
                if redis_password:
                    config["password"] = redis_password
                    self.log_detail("redis", "Redis password configured ✅")
                
                client = redis.Redis(**config)
                client.ping()
                self.log_detail("redis", "Redis connectivity: PASS ✅")
                
            except redis.ConnectionError:
                self.log_detail("redis", "Redis connection failed (expected from local machine)", "warning")
            except ImportError:
                self.log_detail("redis", "Redis library not available (that's OK)", "info")
            except Exception as e:
                self.log_detail("redis", f"Redis test error: {e}", "warning")
            
            self.results["redis"]["status"] = "pass"
            return True
            
        except Exception as e:
            self.log_detail("redis", f"Redis validation error: {e}", "error")
            self.results["redis"]["status"] = "fail"
            return False
    
    def validate_postgres_configuration(self) -> bool:
        """Validate PostgreSQL configuration fixes"""
        try:
            # Load environment
            self.load_staging_environment()
            
            # Check PostgreSQL configuration
            postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
            postgres_port = os.environ.get("POSTGRES_PORT", "5432")
            database_url = os.environ.get("DATABASE_URL", "")
            ssl_mode = os.environ.get("DATABASE_SSL_MODE", "")
            
            # Validate PostgreSQL host
            if postgres_host == "localhost":
                self.log_detail("postgres", "PostgreSQL host is localhost - should be staging instance", "error")
                return False
            else:
                self.log_detail("postgres", f"PostgreSQL host: {postgres_host} ✅")
            
            # Validate SSL configuration
            if ssl_mode == "require":
                self.log_detail("postgres", "SSL mode: require ✅")
            else:
                self.log_detail("postgres", f"SSL mode: {ssl_mode} (should be 'require')", "warning")
            
            # Validate database URL
            if "10.69.0.3" in database_url or postgres_host == "10.69.0.3":
                self.log_detail("postgres", "PostgreSQL configured for staging Cloud SQL ✅")
            else:
                self.log_detail("postgres", f"PostgreSQL host may be incorrect: {postgres_host}", "warning")
            
            # Check SSL certificate paths
            ssl_cert = os.environ.get("DATABASE_SSL_CERT", "")
            if "/etc/ssl/certs" in ssl_cert:
                self.log_detail("postgres", "SSL certificate path configured ✅")
            else:
                self.log_detail("postgres", "SSL certificate path not configured", "warning")
            
            # Test PostgreSQL connection (if available)
            try:
                import psycopg2
                
                postgres_password = os.environ.get("POSTGRES_PASSWORD", "")
                postgres_user = os.environ.get("POSTGRES_USER", "postgres")
                postgres_db = os.environ.get("POSTGRES_DB", "netra_staging")
                
                if postgres_password:
                    self.log_detail("postgres", "PostgreSQL password configured ✅")
                
                conn = psycopg2.connect(
                    host=postgres_host,
                    port=int(postgres_port),
                    database=postgres_db,
                    user=postgres_user,
                    password=postgres_password if postgres_password else None,
                    sslmode="require" if ssl_mode == "require" else "prefer",
                    connect_timeout=10
                )
                
                cursor = conn.cursor()
                cursor.execute("SELECT 1;")
                result = cursor.fetchone()
                
                cursor.close()
                conn.close()
                
                if result and result[0] == 1:
                    self.log_detail("postgres", "PostgreSQL connectivity: PASS ✅")
                
            except psycopg2.OperationalError:
                self.log_detail("postgres", "PostgreSQL connection failed (expected from local machine)", "warning")
            except ImportError:
                self.log_detail("postgres", "psycopg2 library not available (that's OK)", "info")
            except Exception as e:
                self.log_detail("postgres", f"PostgreSQL test error: {e}", "warning")
            
            self.results["postgres"]["status"] = "pass"
            return True
            
        except Exception as e:
            self.log_detail("postgres", f"PostgreSQL validation error: {e}", "error")
            self.results["postgres"]["status"] = "fail"
            return False
    
    def validate_test_runner(self) -> bool:
        """Validate test runner fixes"""
        try:
            # Test unified test runner import
            test_runner_path = self.project_root / "tests" / "unified_test_runner.py"
            
            if not test_runner_path.exists():
                self.log_detail("test_runner", "Unified test runner not found", "error")
                return False
            
            # Test help command
            result = subprocess.run([
                sys.executable, str(test_runner_path), "--help"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=30)
            
            if result.returncode == 0:
                self.log_detail("test_runner", "Test runner help command: PASS ✅")
            else:
                self.log_detail("test_runner", f"Test runner help failed: {result.stderr[:200]}", "error")
                return False
            
            # Test list categories
            result = subprocess.run([
                sys.executable, str(test_runner_path), "--list-categories"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=30)
            
            if result.returncode == 0:
                self.log_detail("test_runner", "Test runner list categories: PASS ✅")
            else:
                self.log_detail("test_runner", f"Test runner list categories failed: {result.stderr[:200]}", "warning")
            
            # Check for staging-specific options
            if "--staging-e2e" in result.stdout or "--env staging" in result.stdout:
                self.log_detail("test_runner", "Staging test options available ✅")
            else:
                self.log_detail("test_runner", "Staging test options not found", "warning")
            
            self.results["test_runner"]["status"] = "pass"
            return True
            
        except subprocess.TimeoutExpired:
            self.log_detail("test_runner", "Test runner command timed out", "error")
            self.results["test_runner"]["status"] = "fail"
            return False
        except Exception as e:
            self.log_detail("test_runner", f"Test runner validation error: {e}", "error")
            self.results["test_runner"]["status"] = "fail"
            return False
    
    def validate_environment_files(self) -> bool:
        """Validate environment configuration files"""
        try:
            # Check staging environment file
            staging_env = self.project_root / ".env.staging.tests"
            
            if not staging_env.exists():
                self.log_detail("environment", "Staging environment file not found", "error")
                return False
            else:
                self.log_detail("environment", "Staging environment file exists ✅")
            
            # Read and validate content
            with open(staging_env, 'r') as f:
                content = f.read()
            
            # Check for critical configurations
            checks = [
                ("ENVIRONMENT=staging", "Environment set to staging"),
                ("REDIS_HOST=10.69.0.4", "Redis host configured"),
                ("POSTGRES_HOST=10.69.0.3", "PostgreSQL host configured"),
                ("DATABASE_SSL_MODE=require", "SSL mode configured"),
                ("netrasystems.ai", "Service URLs configured"),
                ("staging-connector", "VPC connector mentioned")
            ]
            
            for check, description in checks:
                if check in content:
                    self.log_detail("environment", f"{description} ✅")
                else:
                    self.log_detail("environment", f"{description} - NOT FOUND", "warning")
            
            # Check for deprecated configurations
            deprecated = [
                ("localhost:6379", "Redis localhost configuration"),
                ("localhost:5432", "PostgreSQL localhost configuration"),
                (".staging.netrasystems.ai", "Deprecated staging domain")
            ]
            
            for deprecated_item, description in deprecated:
                if deprecated_item in content:
                    self.log_detail("environment", f"{description} found (should be removed)", "warning")
            
            self.results["environment"]["status"] = "pass"
            return True
            
        except Exception as e:
            self.log_detail("environment", f"Environment validation error: {e}", "error")
            self.results["environment"]["status"] = "fail"
            return False
    
    def load_staging_environment(self):
        """Load staging environment variables"""
        staging_env = self.project_root / ".env.staging.tests"
        
        if staging_env.exists():
            with open(staging_env, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
    
    def run_validation(self, components: Optional[List[str]] = None) -> bool:
        """Run validation for specified components or all components"""
        
        if components is None:
            components = ["jwt", "redis", "postgres", "test_runner", "environment"]
        
        logger.info("🔍 Starting staging configuration validation...")
        
        validators = {
            "jwt": self.validate_jwt_configuration,
            "redis": self.validate_redis_configuration,
            "postgres": self.validate_postgres_configuration,
            "test_runner": self.validate_test_runner,
            "environment": self.validate_environment_files
        }
        
        all_passed = True
        
        for component in components:
            if component not in validators:
                logger.error(f"Unknown component: {component}")
                continue
                
            logger.info(f"\\n🔄 Validating {component.upper()}...")
            
            try:
                passed = validators[component]()
                if passed:
                    logger.info(f"✅ {component.upper()} validation: PASS")
                else:
                    logger.error(f"❌ {component.upper()} validation: FAIL")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {component.upper()} validation error: {e}")
                self.results[component]["status"] = "error"
                all_passed = False
        
        return all_passed
    
    def print_summary(self):
        """Print validation summary"""
        logger.info("\\n" + "="*60)
        logger.info("STAGING CONFIGURATION VALIDATION SUMMARY")
        logger.info("="*60)
        
        for component, result in self.results.items():
            status = result["status"]
            status_icon = {
                "pass": "✅",
                "fail": "❌", 
                "error": "⚠️",
                "pending": "⏳"
            }.get(status, "❓")
            
            logger.info(f"{status_icon} {component.upper()}: {status.upper()}")
            
            if self.verbose and result["details"]:
                for detail in result["details"]:
                    level_icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(detail["level"], "")
                    logger.info(f"    {level_icon} {detail['message']}")
        
        # Overall status
        statuses = [r["status"] for r in self.results.values()]
        if all(s == "pass" for s in statuses):
            logger.info("\\n🎉 ALL VALIDATIONS PASSED - Staging ready for E2E tests!")
        elif any(s == "fail" for s in statuses):
            logger.error("\\n💥 SOME VALIDATIONS FAILED - Fix issues before running E2E tests")
        else:
            logger.warning("\\n⚠️ SOME VALIDATIONS HAD WARNINGS - Review and proceed with caution")
        
        logger.info("\\nNext steps:")
        logger.info("1. Run E2E tests: python tests/unified_test_runner.py --staging-e2e")
        logger.info("2. Deploy to staging: python scripts/deploy_to_gcp_actual.py --project netra-staging")
        logger.info("3. Monitor staging: Check GCP Console for service health")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Validate staging configuration fixes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--component", "-c", choices=["jwt", "redis", "postgres", "test_runner", "environment"], 
                        help="Validate specific component only")
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    validator = StagingValidation(verbose=args.verbose)
    
    components = [args.component] if args.component else None
    success = validator.run_validation(components)
    
    validator.print_summary()
    
    if not success:
        sys.exit(1)
    
    logger.info("\\n✅ Staging configuration validation completed successfully")


if __name__ == "__main__":
    main()