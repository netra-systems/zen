from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
ENVIRONMENT VALIDATOR AGENT - ELITE ENGINEER
======================================
Real environment validation with actual database connectivity and security checks.
Validates production readiness and identifies security configurations.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add app to path for imports

import asyncpg
import clickhouse_driver
import redis
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


class EnvironmentValidationResult:
    """Represents validation result for a specific check."""
    
    def __init__(self, check_name: str, status: str, message: str, 
                 details: Optional[Dict] = None, response_time_ms: float = 0):
        self.check_name = check_name
        self.status = status  # "PASS", "FAIL", "WARNING", "SKIP"
        self.message = message
        self.details = details or {}
        self.response_time_ms = response_time_ms
        self.timestamp = datetime.now().isoformat()


class EnvironmentValidator:
    """ELITE ENGINEER Environment Validator Agent"""
    
    def __init__(self):
        self.results: List[EnvironmentValidationResult] = []
        self.start_time = time.time()
        self.env_files = self._discover_env_files()
        self.critical_failures = []
        
    def _discover_env_files(self) -> List[str]:
        """Discover all .env files in the project."""
        env_files = []
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.startswith(".env"):
                    env_files.append(os.path.join(root, file))
        return env_files
    
    def _load_env_file(self, env_file: str) -> Dict[str, str]:
        """Load environment variables from file."""
        env_vars = {}
        if not os.path.exists(env_file):
            return env_vars
            
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key] = value
        except Exception as e:
            self._add_result("env_file_load", "FAIL", 
                           f"Failed to load {env_file}: {str(e)}")
        return env_vars
    
    def _add_result(self, check_name: str, status: str, message: str, 
                   details: Optional[Dict] = None, response_time_ms: float = 0):
        """Add validation result."""
        result = EnvironmentValidationResult(
            check_name, status, message, details, response_time_ms
        )
        self.results.append(result)
        
        if status == "FAIL" and check_name in [
            "database_connection", "env_file_existence", "required_env_vars"
        ]:
            self.critical_failures.append(result)
    
    async def validate_environment_files(self):
        """Validate .env files existence and content."""
        print("Validating environment files...")
        
        # Check for main .env file
        if not os.path.exists(".env"):
            self._add_result("env_file_existence", "FAIL", 
                           "Main .env file not found", 
                           {"expected_path": "./.env"})
            return
            
        self._add_result("env_file_existence", "PASS", 
                        f"Found {len(self.env_files)} .env files", 
                        {"files": self.env_files})
        
        # Validate critical environment variables
        await self._validate_critical_env_vars()
    
    async def _validate_critical_env_vars(self):
        """Validate critical environment variables."""
        required_vars = [
            "DATABASE_URL", "SECRET_KEY", "JWT_SECRET_KEY", 
            "ENVIRONMENT", "CLICKHOUSE_HOST", "CLICKHOUSE_USER"
        ]
        
        main_env = self._load_env_file(".env")
        missing_vars = []
        weak_secrets = []
        
        for var in required_vars:
            if var not in main_env and var not in os.environ:
                missing_vars.append(var)
            elif var in ["SECRET_KEY", "JWT_SECRET_KEY"]:
                value = main_env.get(var) or os.environ.get(var, "")
                if len(value) < 32:
                    weak_secrets.append(f"{var} (length: {len(value)})")
        
        if missing_vars:
            self._add_result("required_env_vars", "FAIL", 
                           f"Missing required variables: {', '.join(missing_vars)}", 
                           {"missing": missing_vars})
        else:
            self._add_result("required_env_vars", "PASS", 
                           "All required environment variables present")
        
        if weak_secrets:
            self._add_result("secret_strength", "WARNING", 
                           f"Weak secrets detected: {', '.join(weak_secrets)}", 
                           {"weak_secrets": weak_secrets})
        else:
            self._add_result("secret_strength", "PASS", 
                           "All secrets meet minimum length requirements")
    
    async def test_postgresql_connectivity(self):
        """Test actual PostgreSQL database connectivity."""
        print("Testing PostgreSQL connectivity...")
        start_time = time.time()
        
        database_url = os.environ.get("DATABASE_URL") or self._load_env_file(".env").get("DATABASE_URL")
        
        if not database_url:
            self._add_result("postgres_connection", "FAIL", 
                           "#removed-legacynot configured")
            return
        
        try:
            # Test with SQLAlchemy
            engine = create_engine(database_url, pool_pre_ping=True)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                pg_version = result.fetchone()[0]
                response_time = (time.time() - start_time) * 1000
                
                # Test table access
                tables_result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in tables_result.fetchall()]
                
                self._add_result("postgres_connection", "PASS", 
                               f"PostgreSQL connected successfully", 
                               {
                                   "version": pg_version,
                                   "tables_count": len(tables),
                                   "sample_tables": tables[:5]
                               }, response_time)
                               
        except OperationalError as e:
            response_time = (time.time() - start_time) * 1000
            self._add_result("postgres_connection", "FAIL", 
                           f"PostgreSQL connection failed: {str(e)}", 
                           {"error_type": "OperationalError"}, response_time)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self._add_result("postgres_connection", "FAIL", 
                           f"PostgreSQL connection error: {str(e)}", 
                           {"error_type": type(e).__name__}, response_time)
    
    async def test_clickhouse_connectivity(self):
        """Test actual ClickHouse database connectivity."""
        print("Testing ClickHouse connectivity...")
        start_time = time.time()
        
        env_vars = self._load_env_file(".env")
        ch_host = env_vars.get("CLICKHOUSE_HOST") or os.environ.get("CLICKHOUSE_HOST")
        ch_port = env_vars.get("CLICKHOUSE_PORT", "8123")
        ch_user = env_vars.get("CLICKHOUSE_USER", "default")
        ch_password = env_vars.get("CLICKHOUSE_PASSWORD")
        
        if not ch_host:
            self._add_result("clickhouse_connection", "FAIL", 
                           "ClickHouse host not configured")
            return
        
        try:
            # Test ClickHouse connection
            client = clickhouse_driver.Client(
                host=ch_host,
                port=int(ch_port),
                user=ch_user,
                password=ch_password,
                secure=True
            )
            
            # Test basic query
            result = client.execute("SELECT version()")
            version = result[0][0] if result else "Unknown"
            
            # Test system information
            system_info = client.execute("SELECT * FROM system.settings LIMIT 5")
            response_time = (time.time() - start_time) * 1000
            
            self._add_result("clickhouse_connection", "PASS", 
                           f"ClickHouse connected successfully", 
                           {
                               "version": version,
                               "host": ch_host,
                               "port": ch_port,
                               "settings_count": len(system_info)
                           }, response_time)
                           
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self._add_result("clickhouse_connection", "FAIL", 
                           f"ClickHouse connection failed: {str(e)}", 
                           {"error_type": type(e).__name__}, response_time)
    
    async def test_redis_connectivity(self):
        """Test Redis connectivity if configured."""
        print("Testing Redis connectivity...")
        start_time = time.time()
        
        env_vars = self._load_env_file(".env")
        redis_url = env_vars.get("REDIS_URL") or os.environ.get("REDIS_URL")
        redis_password = env_vars.get("REDIS_PASSWORD")
        
        if not redis_url and not redis_password:
            self._add_result("redis_connection", "SKIP", 
                           "Redis not configured")
            return
        
        try:
            if redis_url:
                r = redis.from_url(redis_url)
            else:
                r = redis.Redis(password=redis_password)
            
            # Test connection
            info = r.info()
            response_time = (time.time() - start_time) * 1000
            
            self._add_result("redis_connection", "PASS", 
                           f"Redis connected successfully", 
                           {
                               "version": info.get("redis_version"),
                               "memory_used": info.get("used_memory_human"),
                               "connected_clients": info.get("connected_clients")
                           }, response_time)
                           
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self._add_result("redis_connection", "FAIL", 
                           f"Redis connection failed: {str(e)}", 
                           {"error_type": type(e).__name__}, response_time)
    
    async def validate_api_keys(self):
        """Validate API keys and authentication tokens."""
        print("Validating API keys and tokens...")
        
        env_vars = self._load_env_file(".env")
        
        # Check Google OAuth
        google_client_id = env_vars.get("GOOGLE_CLIENT_ID")
        google_client_secret = env_vars.get("GOOGLE_CLIENT_SECRET")
        
        if google_client_id and google_client_secret:
            self._add_result("google_oauth", "PASS", 
                           "Google OAuth credentials configured", 
                           {"client_id_prefix": google_client_id[:10] + "..."})
        else:
            self._add_result("google_oauth", "WARNING", 
                           "Google OAuth credentials not configured")
        
        # Check Gemini API key
        gemini_key = env_vars.get("GEMINI_API_KEY")
        if gemini_key:
            self._add_result("gemini_api", "PASS", 
                           "Gemini API key configured", 
                           {"key_prefix": gemini_key[:10] + "..."})
        else:
            self._add_result("gemini_api", "WARNING", 
                           "Gemini API key not configured")
        
        # Check Langfuse keys
        langfuse_public = env_vars.get("LANGFUSE_PUBLIC_KEY")
        langfuse_secret = env_vars.get("LANGFUSE_SECRET_KEY")
        
        if langfuse_public and langfuse_secret:
            self._add_result("langfuse_keys", "PASS", 
                           "Langfuse keys configured")
        else:
            self._add_result("langfuse_keys", "WARNING", 
                           "Langfuse keys not configured")
    
    async def check_service_ports(self):
        """Check if required service ports are available."""
        print("Checking service ports and availability...")
        
        ports_to_check = [
            (5433, "PostgreSQL"),
            (6379, "Redis"),
            (8000, "Backend API"),
            (3000, "Frontend")
        ]
        
        for port, service in ports_to_check:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    self._add_result(f"port_{port}", "PASS", 
                                   f"{service} port {port} is available")
                else:
                    self._add_result(f"port_{port}", "WARNING", 
                                   f"{service} port {port} is not responding")
                                   
            except Exception as e:
                self._add_result(f"port_{port}", "WARNING", 
                               f"Could not check {service} port {port}: {str(e)}")
    
    async def validate_security_configuration(self):
        """Validate security configuration and identify risks."""
        print("Validating security configuration...")
        
        env_vars = self._load_env_file(".env")
        security_issues = []
        
        # Check if secrets are properly secured
        if os.path.exists(".env"):
            self._add_result("env_file_security", "WARNING", 
                           ".env file contains secrets in plain text", 
                           {
                               "recommendation": "Use environment variables or secret management",
                               "risk_level": "HIGH"
                           })
        
        # Check secret strength
        fernet_key = env_vars.get("FERNET_KEY")
        if fernet_key:
            if len(fernet_key) >= 44:  # Base64 encoded 32-byte key
                self._add_result("fernet_key", "PASS", 
                               "Fernet encryption key properly configured")
            else:
                self._add_result("fernet_key", "FAIL", 
                               "Fernet key appears to be invalid length")
        
        # Check environment setting
        environment = env_vars.get("ENVIRONMENT", "development")
        if environment == "production":
            self._add_result("production_security", "WARNING", 
                           "Production environment detected - ensure proper security measures")
        else:
            self._add_result("development_security", "PASS", 
                           f"Running in {environment} environment")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_time = (time.time() - self.start_time) * 1000
        
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        warnings = len([r for r in self.results if r.status == "WARNING"])
        skipped = len([r for r in self.results if r.status == "SKIP"])
        
        # Determine overall readiness
        ready_for_launch = len(self.critical_failures) == 0
        
        report = {
            "validation_summary": {
                "ready_for_launch": ready_for_launch,
                "total_checks": len(self.results),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "skipped": skipped,
                "critical_failures": len(self.critical_failures),
                "total_validation_time_ms": round(total_time, 2),
                "timestamp": datetime.now().isoformat()
            },
            "environment_status": {
                "env_files_found": len(self.env_files),
                "database_connectivity": "CONNECTED" if any(r.check_name == "postgres_connection" and r.status == "PASS" for r in self.results) else "FAILED",
                "clickhouse_connectivity": "CONNECTED" if any(r.check_name == "clickhouse_connection" and r.status == "PASS" for r in self.results) else "FAILED",
                "redis_connectivity": "CONNECTED" if any(r.check_name == "redis_connection" and r.status == "PASS" for r in self.results) else "NOT_CONFIGURED"
            },
            "security_assessment": {
                "secrets_in_env_file": os.path.exists(".env"),
                "weak_secrets_detected": any(r.check_name == "secret_strength" and r.status == "WARNING" for r in self.results),
                "api_keys_configured": any(r.check_name.endswith("_api") and r.status == "PASS" for r in self.results)
            },
            "detailed_results": [
                {
                    "check": r.check_name,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details,
                    "response_time_ms": r.response_time_ms,
                    "timestamp": r.timestamp
                }
                for r in self.results
            ],
            "critical_failures": [
                {
                    "check": r.check_name,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.critical_failures
            ],
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if self.critical_failures:
            recommendations.append("CRITICAL: Fix critical failures before launching")
        
        if any(r.check_name == "env_file_security" and r.status == "WARNING" for r in self.results):
            recommendations.append("Security: Move secrets to environment variables or secret manager")
        
        if any(r.check_name == "clickhouse_connection" and r.status == "FAIL" for r in self.results):
            recommendations.append("Database: Fix ClickHouse connectivity for analytics features")
        
        if any(r.check_name == "redis_connection" and r.status == "FAIL" for r in self.results):
            recommendations.append("Cache: Configure Redis for improved performance")
        
        if not any(r.check_name.endswith("_api") and r.status == "PASS" for r in self.results):
            recommendations.append("API Keys: Configure LLM API keys for AI functionality")
        
        if len(self.critical_failures) == 0:
            recommendations.append("Environment appears ready for launch!")
        
        return recommendations


async def main():
    """Main environment validation execution."""
    print("=" * 60)
    print("NETRA AI ENVIRONMENT VALIDATOR AGENT")
    print("   Elite Engineer - Ultra Deep Think Mode")
    print("=" * 60)
    print()
    
    validator = EnvironmentValidator()
    
    # Run all validation checks
    await validator.validate_environment_files()
    await validator.test_postgresql_connectivity()
    await validator.test_clickhouse_connectivity()
    await validator.test_redis_connectivity()
    await validator.validate_api_keys()
    await validator.check_service_ports()
    await validator.validate_security_configuration()
    
    # Generate and display report
    report = validator.generate_report()
    
    print("\n" + "=" * 60)
    print("ENVIRONMENT VALIDATION REPORT")
    print("=" * 60)
    
    summary = report["validation_summary"]
    print(f"Ready for Launch: {'YES' if summary['ready_for_launch'] else 'NO'}")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Total Time: {summary['total_validation_time_ms']:.2f}ms")
    
    if summary["critical_failures"] > 0:
        print(f"\nCRITICAL FAILURES: {summary['critical_failures']}")
        for failure in report["critical_failures"]:
            print(f"   FAIL - {failure['check']}: {failure['message']}")
    
    print(f"\nCONNECTIVITY STATUS:")
    env_status = report["environment_status"]
    print(f"   PostgreSQL: {env_status['database_connectivity']}")
    print(f"   ClickHouse: {env_status['clickhouse_connectivity']}")
    print(f"   Redis: {env_status['redis_connectivity']}")
    
    print(f"\nSECURITY ASSESSMENT:")
    sec_status = report["security_assessment"]
    print(f"   Secrets in .env: {'WARNING' if sec_status['secrets_in_env_file'] else 'OK'}")
    print(f"   Weak secrets: {'WARNING' if sec_status['weak_secrets_detected'] else 'OK'}")
    print(f"   API keys configured: {'YES' if sec_status['api_keys_configured'] else 'NO'}")
    
    print(f"\nRECOMMENDATIONS:")
    for rec in report["recommendations"]:
        print(f"   {rec}")
    
    # Save detailed report
    with open("environment_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to: environment_validation_report.json")
    print("\n" + "=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if summary["ready_for_launch"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
