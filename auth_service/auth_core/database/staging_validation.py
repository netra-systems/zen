"""
Auth Service Staging Deployment Validation

Provides validation utilities for staging deployment to catch common issues:
1. Database URL format validation for Cloud SQL
2. SSL parameter compatibility checks
3. Credential format validation
4. Pre-deployment connection testing (without actual connection)

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent staging deployment failures
- Value Impact: Reduces deployment downtime and debugging time
- Strategic Impact: Ensures reliable auth service availability
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class StagingDatabaseValidator:
    """Validates database configuration for staging deployment."""
    
    @staticmethod
    def validate_database_url_format(url: str) -> Dict[str, any]:
        """Validate database URL format for staging compatibility.
        
        Args:
            url: Database URL to validate
            
        Returns:
            Dictionary with validation results and recommendations
        """
        if not url:
            return {
                "valid": False,
                "error": "Database URL is empty",
                "recommendations": ["Set POSTGRES_* environment variables"]
            }
        
        results = {
            "valid": True,
            "warnings": [],
            "recommendations": [],
            "url_type": "unknown",
            "ssl_handling": "unknown"
        }
        
        try:
            parsed = urlparse(url)
            
            # Check URL scheme
            if not url.startswith(("postgresql://", "postgres://")):
                results["valid"] = False
                results["error"] = f"Invalid scheme: {parsed.scheme}"
                results["recommendations"].append("Use postgresql:// or postgres:// scheme")
                return results
            
            # Determine connection type
            if "/cloudsql/" in url:
                results["url_type"] = "cloud_sql"
                results.update(StagingDatabaseValidator._validate_cloud_sql_format(url))
            elif parsed.hostname:
                results["url_type"] = "tcp"
                results.update(StagingDatabaseValidator._validate_tcp_format(url))
            else:
                results["valid"] = False
                results["error"] = "No hostname or Cloud SQL path found"
                
        except Exception as e:
            results["valid"] = False
            results["error"] = f"URL parsing failed: {e}"
            
        return results
    
    @staticmethod
    def _validate_cloud_sql_format(url: str) -> Dict[str, any]:
        """Validate Cloud SQL specific format requirements."""
        results = {
            "warnings": [],
            "recommendations": []
        }
        
        # Check for SSL parameters (should be removed for Cloud SQL)
        if "sslmode=" in url or "ssl=" in url:
            results["warnings"].append("SSL parameters found in Cloud SQL URL")
            results["recommendations"].append("SSL parameters will be automatically removed for Cloud SQL Unix sockets")
            results["ssl_handling"] = "auto_remove"
        else:
            results["ssl_handling"] = "none_needed"
        
        # Check Cloud SQL path format
        cloud_sql_pattern = r'/cloudsql/([^:]+):([^:]+):([^&/?]+)'
        if not re.search(cloud_sql_pattern, url):
            results["warnings"].append("Cloud SQL path format may be incorrect")
            results["recommendations"].append("Expected format: /cloudsql/project:region:instance")
        
        # Check for missing database name
        if "@/" in url and "?" in url:
            db_part = url.split("@/")[1].split("?")[0]
            if not db_part:
                results["warnings"].append("Database name not specified in Cloud SQL URL")
                results["recommendations"].append("Specify database name after @/ in URL")
        
        return results
    
    @staticmethod
    def _validate_tcp_format(url: str) -> Dict[str, any]:
        """Validate TCP connection format requirements."""
        results = {
            "warnings": [],
            "recommendations": []
        }
        
        parsed = urlparse(url)
        
        # Check for SSL parameters
        if "sslmode=" in url:
            results["ssl_handling"] = "convert_to_ssl"
            results["recommendations"].append("sslmode will be converted to ssl for asyncpg compatibility")
        elif "ssl=" in url:
            results["ssl_handling"] = "compatible"
        else:
            results["warnings"].append("No SSL parameters specified for TCP connection")
            results["recommendations"].append("Consider adding ssl=require for production security")
            results["ssl_handling"] = "none_specified"
        
        # Check hostname format
        if parsed.hostname:
            if parsed.hostname == "localhost":
                results["warnings"].append("Using localhost in staging URL")
                results["recommendations"].append("Use actual staging database hostname")
        
        # Check port
        if not parsed.port:
            results["warnings"].append("Port not specified, will use default")
            results["recommendations"].append("Explicitly specify port (usually 5432)")
        
        return results
    
    @staticmethod
    def validate_credentials_format(url: str) -> Dict[str, any]:
        """Validate credential format in database URL.
        
        Args:
            url: Database URL with credentials
            
        Returns:
            Validation results for credentials
        """
        results = {
            "valid": True,
            "warnings": [],
            "recommendations": [],
            "credential_issues": []
        }
        
        try:
            parsed = urlparse(url)
            
            # Check username - enhanced validation for problematic patterns
            if not parsed.username:
                results["credential_issues"].append("No username specified")
                results["recommendations"].append("Specify username in URL")
            else:
                # Check for specific problematic patterns found in logs
                if parsed.username == "user_pr-4":
                    results["credential_issues"].append("Invalid username pattern 'user_pr-4' - this will cause authentication failures")
                    results["recommendations"].append("Use correct username - should be 'postgres' for Cloud SQL")
                elif re.match(r'user_pr-\d+', parsed.username):
                    results["credential_issues"].append(f"Invalid username pattern '{parsed.username}' - appears to be misconfigured PR-specific user")
                    results["recommendations"].append("Use correct staging username - should be 'postgres' for Cloud SQL")
                elif parsed.username in ["postgres", "root", "admin"]:
                    # Only warn for postgres in staging, don't fail
                    results["warnings"].append(f"Using common username '{parsed.username}'")
                    if parsed.username == "postgres":
                        results["recommendations"].append("Username 'postgres' is acceptable for Cloud SQL but ensure password is secure")
                    else:
                        results["recommendations"].append("Consider using service-specific username for security")
                
                # Check for other invalid patterns
                if parsed.username.startswith("user_") and not parsed.username == "user":
                    results["warnings"].append(f"Username pattern '{parsed.username}' may be auto-generated and incorrect")
                    results["recommendations"].append("Verify username matches staging database configuration")
            
            # Check password - enhanced validation for weak passwords
            if not parsed.password:
                results["credential_issues"].append("No password specified")
                results["recommendations"].append("Specify password in URL")
            else:
                # Check for insecure default passwords
                insecure_passwords = ["password", "123456", "admin", "123", "password123", "admin123", "test"]
                if parsed.password.lower() in insecure_passwords:
                    results["credential_issues"].append("Using insecure default password")
                    results["recommendations"].append("Use secure password")
                
                # Check for weak passwords (too short)
                elif len(parsed.password) < 8:
                    results["credential_issues"].append("Password is shorter than 8 characters")
                    results["recommendations"].append("Use password with at least 8 characters for security")
                    
                # Check for very weak passwords (only numbers)
                elif parsed.password.isdigit() and len(parsed.password) < 12:
                    results["credential_issues"].append("Password contains only numbers and is too short")
                    results["recommendations"].append("Use complex password with letters, numbers, and symbols")
                
                # Check for development/test passwords in staging
                test_passwords = ["wrong_password", "test_password", "development_password", "dev_password"]
                if any(test_pwd in parsed.password.lower() for test_pwd in test_passwords):
                    results["credential_issues"].append("Password appears to be a test/development password")
                    results["recommendations"].append("Use secure production password for staging")
            
            # Check for placeholder patterns - expanded list
            placeholder_patterns = [
                r'\$\([A-Z_]+\)',  # $(VARIABLE)
                r'\${[A-Z_]+}',    # ${VARIABLE}
                r'REPLACE_WITH_',   # REPLACE_WITH_*
                r'your-.*-password', # your-*-password
                r'CHANGE_ME',       # CHANGE_ME
                r'TODO',            # TODO
                r'PLACEHOLDER',     # PLACEHOLDER
                r'EXAMPLE',         # EXAMPLE
            ]
            
            for pattern in placeholder_patterns:
                if re.search(pattern, parsed.password or "", re.IGNORECASE):
                    results["credential_issues"].append("Password contains placeholder text")
                    results["recommendations"].append("Replace placeholder with actual secure password")
                    break
            
            # Additional validation for staging environment
            if "staging" in (url.lower() if url else ""):
                # Staging-specific checks
                if parsed.username and parsed.username.startswith("dev_"):
                    results["warnings"].append("Username appears to be development-specific in staging environment")
                    results["recommendations"].append("Verify username is correct for staging database")
                    
                if parsed.password and "dev" in parsed.password.lower():
                    results["warnings"].append("Password contains 'dev' which may indicate development credentials")
                    results["recommendations"].append("Ensure password is staging-appropriate, not development")
            
            # Mark as invalid if critical issues found
            if results["credential_issues"]:
                results["valid"] = False
                
        except Exception as e:
            results["valid"] = False
            results["error"] = f"Credential validation failed: {e}"
            
        return results
    
    @staticmethod
    def pre_deployment_validation(database_url: Optional[str] = None) -> Dict[str, any]:
        """Comprehensive pre-deployment validation for auth service.
        
        Args:
            database_url: Optional URL to validate, builds from POSTGRES_* vars if None
            
        Returns:
            Complete validation report
        """
        if database_url is None:
            from shared.database_url_builder import DatabaseURLBuilder
            from shared.isolated_environment import get_env
            builder = DatabaseURLBuilder(get_env().as_dict())
            database_url = builder.get_url_for_environment(sync=False) or ""
        
        report = {
            "overall_status": "unknown",
            "database_url": database_url[:50] + "..." if len(database_url) > 50 else database_url,
            "validations": {},
            "critical_issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # URL Format validation
        url_validation = StagingDatabaseValidator.validate_database_url_format(database_url)
        report["validations"]["url_format"] = url_validation
        
        if not url_validation["valid"]:
            report["critical_issues"].append(f"URL format: {url_validation.get('error', 'Invalid')}")
        else:
            report["warnings"].extend(url_validation.get("warnings", []))
            report["recommendations"].extend(url_validation.get("recommendations", []))
        
        # Credential validation
        credential_validation = StagingDatabaseValidator.validate_credentials_format(database_url)
        report["validations"]["credentials"] = credential_validation
        
        if not credential_validation["valid"]:
            report["critical_issues"].extend(credential_validation.get("credential_issues", []))
        else:
            report["warnings"].extend(credential_validation.get("warnings", []))
            report["recommendations"].extend(credential_validation.get("recommendations", []))
        
        # SSL compatibility validation
        ssl_validation = StagingDatabaseValidator._validate_ssl_compatibility(database_url)
        report["validations"]["ssl_compatibility"] = ssl_validation
        
        if not ssl_validation["valid"]:
            report["critical_issues"].append(ssl_validation.get("error", "SSL compatibility issue"))
        else:
            report["recommendations"].extend(ssl_validation.get("recommendations", []))
        
        # Determine overall status
        if report["critical_issues"]:
            report["overall_status"] = "failed"
        elif report["warnings"]:
            report["overall_status"] = "warning"
        else:
            report["overall_status"] = "passed"
        
        return report
    
    @staticmethod
    def _validate_ssl_compatibility(url: str) -> Dict[str, any]:
        """Validate SSL parameter compatibility with asyncpg."""
        results = {
            "valid": True,
            "recommendations": []
        }
        
        try:
            import re
            
            # Test SSL parameter conversion
            is_cloud_sql = "/cloudsql/" in url
            
            # Convert SSL params for asyncpg
            if is_cloud_sql:
                converted = re.sub(r'[&?]sslmode=[^&]*', '', url)
                converted = re.sub(r'[&?]ssl=[^&]*', '', converted)
                converted = re.sub(r'&&+', '&', converted)
                converted = re.sub(r'[&?]$', '', converted)
            else:
                converted = url.replace("sslmode=require", "ssl=require") if "sslmode=require" in url else url
            
            if is_cloud_sql:
                # Cloud SQL should have no SSL parameters after conversion
                has_ssl_after = any(param in converted for param in ["sslmode=", "ssl="])
                if has_ssl_after:
                    results["valid"] = False
                    results["error"] = "SSL parameters not properly removed for Cloud SQL"
                else:
                    results["recommendations"].append("SSL parameters correctly handled for Cloud SQL")
            else:
                # Regular connections should convert sslmode to ssl
                if "sslmode=" in url and "ssl=" not in converted and "sslmode=" in converted:
                    results["valid"] = False
                    results["error"] = "sslmode parameter not converted to ssl for asyncpg"
                else:
                    results["recommendations"].append("SSL parameters compatible with asyncpg")
                    
        except Exception as e:
            results["valid"] = False
            results["error"] = f"SSL compatibility check failed: {e}"
        
        return results
    
    @staticmethod
    def print_validation_report(report: Dict[str, any]) -> None:
        """Print a formatted validation report.
        
        Args:
            report: Validation report from pre_deployment_validation()
        """
        status_symbol = {
            "passed": "PASS",
            "warning": "WARN", 
            "failed": "FAIL",
            "unknown": "UNKNOWN"
        }.get(report["overall_status"], "UNKNOWN")
        
        print(f"\nAuth Service Staging Validation Report")
        print("=" * 50)
        print(f"Overall Status: {status_symbol} {report['overall_status'].upper()}")
        print(f"Database URL: {report['database_url']}")
        
        if report["critical_issues"]:
            print(f"\nCritical Issues ({len(report['critical_issues'])}):")
            for issue in report["critical_issues"]:
                print(f"  X {issue}")
        
        if report["warnings"]:
            print(f"\nWarnings ({len(report['warnings'])}):")
            for warning in report["warnings"]:
                print(f"  ! {warning}")
        
        if report["recommendations"]:
            print(f"\nRecommendations ({len(report['recommendations'])}):")
            for rec in report["recommendations"]:
                print(f"  -> {rec}")
        
        print("\n" + "=" * 50)


def validate_staging_deployment() -> bool:
    """Main validation function for staging deployment.
    
    Returns:
        True if validation passes, False if critical issues found
    """
    print("Validating Auth Service for Staging Deployment...")
    
    validator = StagingDatabaseValidator()
    report = validator.pre_deployment_validation()
    
    validator.print_validation_report(report)
    
    return report["overall_status"] in ["passed", "warning"]


if __name__ == "__main__":
    # Run validation on current environment
    success = validate_staging_deployment()
    
    if not success:
        print("\nValidation failed. Fix critical issues before deploying.")
        exit(1)
    else:
        print(f"\nValidation passed. Ready for staging deployment.")
        exit(0)