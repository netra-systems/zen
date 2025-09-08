#!/usr/bin/env python3
"""
Test Environment Setup and Validation Script
Ensures proper test environment configuration for all services
"""

import os
import sys
# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import json
import subprocess
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment

@dataclass
class ServiceHealth:
    name: str
    host: str
    port: int
    status: str
    error: Optional[str] = None

@dataclass
class ConfigurationIssue:
    severity: str  # "error", "warning", "info"
    category: str
    message: str
    fix_suggestion: Optional[str] = None

class TestEnvironmentValidator:
    """Validates and sets up test environment configuration"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.test_env_file = self.project_root / ".env.mock"
        self.issues: List[ConfigurationIssue] = []
        self.env = IsolatedEnvironment()
        
    def check_port_availability(self, host: str, port: int) -> bool:
        """Check if a port is available for connection"""
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.error, socket.timeout):
            return False
    
    def check_service_health(self) -> List[ServiceHealth]:
        """Check health of required services"""
        services = [
            ServiceHealth("PostgreSQL", "localhost", 5432, "unknown"),
            ServiceHealth("Redis", "localhost", 6379, "unknown"),
            ServiceHealth("ClickHouse HTTP", "localhost", 8124, "unknown"),
            ServiceHealth("ClickHouse Native", "localhost", 9001, "unknown"),
            ServiceHealth("Auth Service", "127.0.0.1", 8081, "unknown"),
            ServiceHealth("Backend Service", "localhost", 8000, "unknown"),
            ServiceHealth("WebSocket", "localhost", 8080, "unknown"),
        ]
        
        for service in services:
            if self.check_port_availability(service.host, service.port):
                service.status = "healthy"
            else:
                service.status = "unavailable"
                service.error = f"Cannot connect to {service.host}:{service.port}"
        
        return services
    
    def validate_environment_variables(self) -> None:
        """Validate critical environment variables"""
        # Load test environment
        if self.test_env_file.exists():
            self.env.load_from_file(str(self.test_env_file))
        
        # Critical variables that must be set
        critical_vars = {
            "JWT_SECRET_KEY": "JWT secret for authentication",
            "JWT_SECRET": "JWT secret for auth service",
            "SERVICE_SECRET": "Service-to-service authentication secret",
            "DATABASE_URL": "PostgreSQL connection string",
            "REDIS_URL": "Redis connection string",
            "FERNET_KEY": "Encryption key for sensitive data",
        }
        
        for var, description in critical_vars.items():
            value = self.env.get(var)
            if not value:
                self.issues.append(ConfigurationIssue(
                    severity="error",
                    category="environment",
                    message=f"Missing {var}: {description}",
                    fix_suggestion=f"Add {var} to .env.mock file"
                ))
            elif var in ["JWT_SECRET_KEY", "JWT_SECRET", "SERVICE_SECRET"] and len(value) < 32:
                self.issues.append(ConfigurationIssue(
                    severity="error",
                    category="security",
                    message=f"{var} is too short (must be at least 32 characters)",
                    fix_suggestion=f"Update {var} in .env.mock with a longer value"
                ))
        
        # Check for real API keys when using real LLM testing
        if self.env.get("ENABLE_REAL_LLM_TESTING") == "true":
            api_keys = {
                "GEMINI_API_KEY": "Google AI/Gemini API key",
                "ANTHROPIC_API_KEY": "Anthropic Claude API key",
                "OPENAI_API_KEY": "OpenAI API key",
            }
            
            has_real_key = False
            for var, description in api_keys.items():
                value = self.env.get(var)
                if value and not value.startswith("test-"):
                    has_real_key = True
                    break
            
            if not has_real_key:
                self.issues.append(ConfigurationIssue(
                    severity="warning",
                    category="api_keys",
                    message="Real LLM testing enabled but no valid API keys found",
                    fix_suggestion="Set GEMINI_API_KEY from your .env file or disable real LLM testing"
                ))
    
    def check_database_connectivity(self) -> None:
        """Check database connectivity"""
        try:
            import psycopg2
            
            # Parse DATABASE_URL
            db_url = self.env.get("DATABASE_URL")
            if not db_url:
                self.issues.append(ConfigurationIssue(
                    severity="error",
                    category="database",
                    message="#removed-legacynot set",
                    fix_suggestion="Set #removed-legacyin .env.mock"
                ))
                return
            
            # Test connection
            try:
                conn = psycopg2.connect(db_url)
                conn.close()
            except Exception as e:
                self.issues.append(ConfigurationIssue(
                    severity="error",
                    category="database",
                    message=f"Cannot connect to PostgreSQL: {str(e)}",
                    fix_suggestion="Ensure PostgreSQL is running and credentials are correct"
                ))
        except ImportError:
            self.issues.append(ConfigurationIssue(
                severity="warning",
                category="dependencies",
                message="psycopg2 not installed, cannot test database connectivity",
                fix_suggestion="pip install psycopg2-binary"
            ))
    
    def check_redis_connectivity(self) -> None:
        """Check Redis connectivity"""
        try:
            import redis
            
            redis_url = self.env.get("REDIS_URL", "redis://localhost:6379/1")
            
            try:
                r = redis.from_url(redis_url)
                r.ping()
            except Exception as e:
                self.issues.append(ConfigurationIssue(
                    severity="warning",
                    category="redis",
                    message=f"Cannot connect to Redis: {str(e)}",
                    fix_suggestion="Ensure Redis is running or set TEST_DISABLE_REDIS=true"
                ))
        except ImportError:
            self.issues.append(ConfigurationIssue(
                severity="info",
                category="dependencies",
                message="redis not installed, skipping Redis connectivity check",
                fix_suggestion="pip install redis"
            ))
    
    def setup_test_databases(self) -> None:
        """Create test databases if they don't exist"""
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            
            # Connect to default postgres database
            conn = psycopg2.connect(
                host=self.env.get("POSTGRES_HOST", "localhost"),
                port=int(self.env.get("POSTGRES_PORT", 5432)),
                user=self.env.get("POSTGRES_USER", "postgres"),
                password=self.env.get("POSTGRES_PASSWORD", "postgres"),
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            # Create test database if it doesn't exist
            test_db = self.env.get("POSTGRES_DB", "netra_test")
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{test_db}'")
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {test_db}")
                print(f"✓ Created test database: {test_db}")
            else:
                print(f"✓ Test database already exists: {test_db}")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            self.issues.append(ConfigurationIssue(
                severity="error",
                category="database",
                message=f"Failed to setup test database: {str(e)}",
                fix_suggestion="Ensure PostgreSQL is running with correct credentials"
            ))
    
    def copy_api_keys_from_dev(self) -> None:
        """Copy real API keys from .env to test environment if available"""
        if not self.env_file.exists():
            return
        
        # Load dev environment
        dev_env = IsolatedEnvironment()
        dev_env.load_from_file(str(self.env_file))
        
        # Copy API keys if they exist and are not test values
        api_keys = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
        
        for key in api_keys:
            dev_value = dev_env.get(key)
            if dev_value and not dev_value.startswith("test-") and not dev_value.startswith("sk-"):
                test_value = self.env.get(key)
                if not test_value or test_value.startswith("test-"):
                    self.env.set(key, dev_value, source="copied_from_dev")
                    print(f"✓ Copied {key} from .env to test environment")
        
        # Also set GOOGLE_API_KEY to match GEMINI_API_KEY
        gemini_key = self.env.get("GEMINI_API_KEY")
        if gemini_key and not gemini_key.startswith("test-"):
            self.env.set("GOOGLE_API_KEY", gemini_key, source="mirrored_from_gemini")
    
    def generate_report(self) -> str:
        """Generate validation report"""
        report = []
        report.append("\n" + "="*60)
        report.append("TEST ENVIRONMENT VALIDATION REPORT")
        report.append("="*60 + "\n")
        
        # Service Health
        report.append("SERVICE HEALTH CHECK:")
        report.append("-"*30)
        services = self.check_service_health()
        for service in services:
            status_icon = "✓" if service.status == "healthy" else "✗"
            report.append(f"  {status_icon} {service.name}: {service.status}")
            if service.error:
                report.append(f"     └─ {service.error}")
        
        # Configuration Issues
        if self.issues:
            report.append("\nCONFIGURATION ISSUES:")
            report.append("-"*30)
            
            # Group by severity
            errors = [i for i in self.issues if i.severity == "error"]
            warnings = [i for i in self.issues if i.severity == "warning"]
            info = [i for i in self.issues if i.severity == "info"]
            
            if errors:
                report.append(f"\nERRORS ({len(errors)}):")
                for issue in errors:
                    report.append(f"  ✗ [{issue.category}] {issue.message}")
                    if issue.fix_suggestion:
                        report.append(f"     → Fix: {issue.fix_suggestion}")
            
            if warnings:
                report.append(f"\nWARNINGS ({len(warnings)}):")
                for issue in warnings:
                    report.append(f"  ⚠ [{issue.category}] {issue.message}")
                    if issue.fix_suggestion:
                        report.append(f"     → Fix: {issue.fix_suggestion}")
            
            if info:
                report.append(f"\nINFO ({len(info)}):")
                for issue in info:
                    report.append(f"  ℹ [{issue.category}] {issue.message}")
        else:
            report.append("\n✓ No configuration issues found!")
        
        # Summary
        report.append("\n" + "="*60)
        error_count = len([i for i in self.issues if i.severity == "error"])
        if error_count > 0:
            report.append(f"RESULT: ✗ FAILED - {error_count} error(s) must be fixed")
        else:
            report.append("RESULT: ✓ READY - Test environment is properly configured")
        report.append("="*60)
        
        return "\n".join(report)
    
    def fix_common_issues(self) -> None:
        """Attempt to fix common configuration issues"""
        print("\nAttempting to fix common issues...")
        
        # Create test database
        self.setup_test_databases()
        
        # Copy API keys from dev environment
        self.copy_api_keys_from_dev()
        
        # Ensure test env file exists with proper values
        if not self.test_env_file.exists():
            print("✓ Created .env.mock file with default values")
        
        # Export test environment for child processes
        env_dict = self.env.get_subprocess_env()
        for key, value in env_dict.items():
            os.environ[key] = value
        
        print("✓ Test environment variables exported")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup and validate test environment")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common issues")
    parser.add_argument("--export", action="store_true", help="Export test environment variables")
    parser.add_argument("--real-llm", action="store_true", help="Enable real LLM testing")
    args = parser.parse_args()
    
    validator = TestEnvironmentValidator()
    
    # Set real LLM flag if requested
    if args.real_llm:
        validator.env.set("ENABLE_REAL_LLM_TESTING", "true", source="cli")
    
    # Run validation
    validator.validate_environment_variables()
    validator.check_database_connectivity()
    validator.check_redis_connectivity()
    
    # Fix issues if requested
    if args.fix:
        validator.fix_common_issues()
        # Re-validate after fixes
        validator.issues.clear()
        validator.validate_environment_variables()
        validator.check_database_connectivity()
        validator.check_redis_connectivity()
    
    # Generate and print report
    report = validator.generate_report()
    print(report)
    
    # Export environment if requested
    if args.export:
        print("\nExporting test environment variables...")
        env_dict = validator.env.get_subprocess_env()
        for key, value in env_dict.items():
            os.environ[key] = value
        print("✓ Environment variables exported")
    
    # Return exit code based on errors
    error_count = len([i for i in validator.issues if i.severity == "error"])
    sys.exit(error_count)

if __name__ == "__main__":
    main()