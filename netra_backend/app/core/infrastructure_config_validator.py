"""
Infrastructure Configuration Validator for Issue #1278

CRITICAL PURPOSE: Validate configuration files and environment variables
to detect deprecated domain patterns and infrastructure misconfigurations
that can cause SSL certificate failures and connectivity issues.

Business Impact: Prevents production outages by catching configuration
errors before deployment. Supports $500K+ ARR platform reliability.

Issue #1278 Focus:
- Detect deprecated *.staging.netrasystems.ai patterns
- Validate correct *.netrasystems.ai usage
- Check VPC connector configuration
- Validate database timeout settings
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ConfigIssueType(Enum):
    """Configuration issue types for Issue #1278."""
    DEPRECATED_DOMAIN = "deprecated_domain"
    INVALID_SSL_CONFIG = "invalid_ssl_config"
    MISSING_VPC_CONFIG = "missing_vpc_config"
    INSUFFICIENT_TIMEOUT = "insufficient_timeout"
    SECURITY_RISK = "security_risk"
    PERFORMANCE_ISSUE = "performance_issue"
    COMPLIANCE_VIOLATION = "compliance_violation"


class ConfigSeverity(Enum):
    """Configuration issue severity levels."""
    CRITICAL = "critical"    # Will cause production failures
    HIGH = "high"           # Likely to cause issues
    MEDIUM = "medium"       # May cause issues
    LOW = "low"            # Best practice violation
    INFO = "info"          # Informational


@dataclass
class ConfigIssue:
    """Configuration validation issue."""
    issue_type: ConfigIssueType
    severity: ConfigSeverity
    file_path: str
    line_number: Optional[int]
    issue_description: str
    current_value: str
    recommended_value: str
    remediation_steps: List[str]
    issue_reference: str = "#1278"
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            from datetime import datetime, timezone
            self.timestamp = datetime.now(timezone.utc).isoformat()


class InfrastructureConfigValidator:
    """Validator for infrastructure configuration issues related to Issue #1278."""
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize validator with project root directory."""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        
        # Deprecated domain patterns that cause SSL failures (Issue #1278)
        self.deprecated_patterns = [
            r'.*\.staging\.netrasystems\.ai',
            r'staging\.staging\.netrasystems\.ai',
            r'api\.staging\.netrasystems\.ai',
            r'[a-zA-Z0-9-]+\.staging\.netrasystems\.ai'
        ]
        
        # Correct domain patterns
        self.correct_patterns = [
            r'staging\.netrasystems\.ai',
            r'api.staging\.netrasystems\.ai',
            r'[a-zA-Z0-9-]+\.netrasystems\.ai'
        ]
        
        # Configuration files to check
        self.config_files = [
            'docker-compose*.yml',
            'docker-compose*.yaml', 
            '.env*',
            'terraform-gcp-staging/*.tf',
            'terraform-gcp-staging/*.tfvars',
            'netra_backend/app/config.py',
            'netra_backend/app/core/configuration/*.py',
            'frontend/next.config.js',
            'frontend/src/config/*.ts',
            'frontend/src/config/*.js',
            'scripts/*.py',
            'auth_service/*.py',
            '*.json',
            '*.yaml',
            '*.yml'
        ]

    def validate_domain_patterns(self, content: str, file_path: str) -> List[ConfigIssue]:
        """Validate domain patterns for Issue #1278 compliance."""
        issues = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            if line.strip().startswith('#') or not line.strip():
                continue
                
            # Check for deprecated patterns
            for pattern in self.deprecated_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    deprecated_domain = match.group(0)
                    
                    # Suggest correct replacement
                    if 'staging.staging' in deprecated_domain:
                        recommended = deprecated_domain.replace('.staging.netrasystems.ai', '.netrasystems.ai')
                    elif deprecated_domain.endswith('.staging.netrasystems.ai'):
                        # Replace subdomain.staging.netrasystems.ai with subdomain.netrasystems.ai
                        recommended = deprecated_domain.replace('.staging.netrasystems.ai', '.netrasystems.ai')
                    else:
                        recommended = "staging.netrasystems.ai or api.staging.netrasystems.ai"
                    
                    issues.append(ConfigIssue(
                        issue_type=ConfigIssueType.DEPRECATED_DOMAIN,
                        severity=ConfigSeverity.CRITICAL,
                        file_path=file_path,
                        line_number=line_num,
                        issue_description=f"Deprecated domain pattern detected: {deprecated_domain}",
                        current_value=deprecated_domain,
                        recommended_value=recommended,
                        remediation_steps=[
                            f"Replace '{deprecated_domain}' with '{recommended}'",
                            "Update SSL certificate configuration to match new domain",
                            "Test connectivity after domain change",
                            "Update load balancer configuration if needed"
                        ]
                    ))
        
        return issues

    def validate_vpc_configuration(self, content: str, file_path: str) -> List[ConfigIssue]:
        """Validate VPC connector configuration for Issue #1278."""
        issues = []
        lines = content.split('\n')
        
        # Check for VPC connector settings
        vpc_connector_found = False
        connector_name = None
        egress_setting = None
        
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for VPC connector configuration
            if 'vpc_connector' in line_lower or 'vpcconnector' in line_lower:
                vpc_connector_found = True
                if ':' in line:
                    connector_name = line.split(':')[-1].strip().strip('"\'')
            
            # Check egress settings
            if 'vpc_egress' in line_lower or 'egress' in line_lower:
                if ':' in line:
                    egress_setting = line.split(':')[-1].strip().strip('"\'')
        
        # Validate VPC connector configuration
        if not vpc_connector_found and 'terraform' in file_path.lower():
            issues.append(ConfigIssue(
                issue_type=ConfigIssueType.MISSING_VPC_CONFIG,
                severity=ConfigSeverity.CRITICAL,
                file_path=file_path,
                line_number=None,
                issue_description="VPC connector configuration missing",
                current_value="None",
                recommended_value="staging-connector",
                remediation_steps=[
                    "Add VPC connector configuration to Cloud Run service",
                    "Set vpc_connector_name = 'staging-connector'",
                    "Configure vpc_egress = 'all-traffic'",
                    "Ensure VPC connector exists in staging environment"
                ]
            ))
        
        # Check egress setting
        if egress_setting and egress_setting.lower() not in ['all-traffic', 'all_traffic']:
            issues.append(ConfigIssue(
                issue_type=ConfigIssueType.MISSING_VPC_CONFIG,
                severity=ConfigSeverity.HIGH,
                file_path=file_path,
                line_number=None,
                issue_description="VPC egress setting may cause connectivity issues",
                current_value=egress_setting,
                recommended_value="all-traffic",
                remediation_steps=[
                    "Set vpc_egress = 'all-traffic' for Cloud Run",
                    "This ensures connectivity to Cloud SQL and Redis",
                    "Test database connectivity after change"
                ]
            ))
        
        return issues

    def validate_timeout_settings(self, content: str, file_path: str) -> List[ConfigIssue]:
        """Validate timeout settings for Issue #1278 database connectivity."""
        issues = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check database timeout settings
            if any(keyword in line_lower for keyword in ['timeout', 'connect_timeout', 'query_timeout']):
                # Extract timeout value
                timeout_match = re.search(r'(\d+)', line)
                if timeout_match:
                    timeout_value = int(timeout_match.group(1))
                    
                    # Database timeouts should be at least 600s for Issue #1278
                    if 'database' in line_lower or 'postgres' in line_lower or 'sql' in line_lower:
                        if timeout_value < 600:
                            issues.append(ConfigIssue(
                                issue_type=ConfigIssueType.INSUFFICIENT_TIMEOUT,
                                severity=ConfigSeverity.HIGH,
                                file_path=file_path,
                                line_number=line_num,
                                issue_description=f"Database timeout too low: {timeout_value}s",
                                current_value=str(timeout_value),
                                recommended_value="600",
                                remediation_steps=[
                                    f"Increase timeout to 600 seconds minimum",
                                    "This addresses Issue #1278 Cloud SQL connectivity timeouts",
                                    "Test database connections after change",
                                    "Monitor for timeout errors in logs"
                                ]
                            ))
                    
                    # Health check timeouts
                    elif 'health' in line_lower and timeout_value < 60:
                        issues.append(ConfigIssue(
                            issue_type=ConfigIssueType.INSUFFICIENT_TIMEOUT,
                            severity=ConfigSeverity.MEDIUM,
                            file_path=file_path,
                            line_number=line_num,
                            issue_description=f"Health check timeout too low: {timeout_value}s",
                            current_value=str(timeout_value),
                            recommended_value="60",
                            remediation_steps=[
                                "Increase health check timeout to 60+ seconds",
                                "This accommodates slow infrastructure responses",
                                "Prevents false positive health check failures"
                            ]
                        ))
        
        return issues

    def validate_ssl_configuration(self, content: str, file_path: str) -> List[ConfigIssue]:
        """Validate SSL configuration for Issue #1278."""
        issues = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for SSL verification disabled
            if any(pattern in line_lower for pattern in [
                'verify_ssl=false', 'ssl_verify=false', 'verify=false',
                'ssl_verification=false', 'check_hostname=false'
            ]):
                issues.append(ConfigIssue(
                    issue_type=ConfigIssueType.SECURITY_RISK,
                    severity=ConfigSeverity.HIGH,
                    file_path=file_path,
                    line_number=line_num,
                    issue_description="SSL verification disabled",
                    current_value="false",
                    recommended_value="true",
                    remediation_steps=[
                        "Enable SSL verification for security",
                        "Ensure SSL certificates are properly configured",
                        "Use valid certificates for *.netrasystems.ai domains",
                        "Test SSL connectivity after enabling verification"
                    ]
                ))
            
            # Check for insecure HTTP usage in production
            if 'http://' in line and any(domain in line for domain in ['netrasystems.ai', 'staging']):
                issues.append(ConfigIssue(
                    issue_type=ConfigIssueType.SECURITY_RISK,
                    severity=ConfigSeverity.MEDIUM,
                    file_path=file_path,
                    line_number=line_num,
                    issue_description="HTTP used instead of HTTPS for staging domains",
                    current_value=line.strip(),
                    recommended_value=line.strip().replace('http://', 'https://'),
                    remediation_steps=[
                        "Replace HTTP with HTTPS for all staging domains",
                        "Ensure SSL certificates are configured",
                        "Update load balancer to redirect HTTP to HTTPS"
                    ]
                ))
        
        return issues

    def validate_file(self, file_path: Path) -> List[ConfigIssue]:
        """Validate a single configuration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return []
        
        issues = []
        file_path_str = str(file_path.relative_to(self.project_root))
        
        # Run all validation checks
        issues.extend(self.validate_domain_patterns(content, file_path_str))
        issues.extend(self.validate_vpc_configuration(content, file_path_str))
        issues.extend(self.validate_timeout_settings(content, file_path_str))
        issues.extend(self.validate_ssl_configuration(content, file_path_str))
        
        return issues

    def validate_environment_variables(self) -> List[ConfigIssue]:
        """Validate environment variables for Issue #1278 compliance."""
        issues = []
        
        # Check environment variables for deprecated patterns
        for key, value in os.environ.items():
            if not value:
                continue
                
            # Check for deprecated domain patterns in env vars
            for pattern in self.deprecated_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    recommended = value
                    for deprecated_pattern in self.deprecated_patterns:
                        recommended = re.sub(deprecated_pattern, 
                                           lambda m: m.group(0).replace('.staging.netrasystems.ai', '.netrasystems.ai'),
                                           recommended, flags=re.IGNORECASE)
                    
                    issues.append(ConfigIssue(
                        issue_type=ConfigIssueType.DEPRECATED_DOMAIN,
                        severity=ConfigSeverity.CRITICAL,
                        file_path="environment_variables",
                        line_number=None,
                        issue_description=f"Environment variable {key} contains deprecated domain",
                        current_value=f"{key}={value}",
                        recommended_value=f"{key}={recommended}",
                        remediation_steps=[
                            f"Update environment variable {key}",
                            f"Change from: {value}",
                            f"Change to: {recommended}",
                            "Restart services after environment change"
                        ]
                    ))
        
        # Check critical environment variables for Issue #1278
        critical_vars = {
            'VPC_CONNECTOR': 'staging-connector',
            'DATABASE_TIMEOUT': '600',
            'POSTGRES_TIMEOUT': '600'
        }
        
        for var_name, recommended_value in critical_vars.items():
            current_value = os.environ.get(var_name)
            
            if not current_value:
                issues.append(ConfigIssue(
                    issue_type=ConfigIssueType.MISSING_VPC_CONFIG if 'VPC' in var_name else ConfigIssueType.INSUFFICIENT_TIMEOUT,
                    severity=ConfigSeverity.HIGH,
                    file_path="environment_variables",
                    line_number=None,
                    issue_description=f"Missing critical environment variable: {var_name}",
                    current_value="None",
                    recommended_value=recommended_value,
                    remediation_steps=[
                        f"Set environment variable {var_name}={recommended_value}",
                        "This addresses Issue #1278 infrastructure requirements",
                        "Restart services after setting variable"
                    ]
                ))
        
        return issues

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive configuration validation for Issue #1278."""
        logger.info("Starting comprehensive configuration validation for Issue #1278...")
        
        start_time = time.time()
        validation_results = {
            "validation_run_id": f"config_validation_{int(start_time)}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "issue_reference": "#1278",
            "purpose": "Infrastructure configuration validation for Issue #1278",
            "files_checked": [],
            "issues": [],
            "environment_issues": [],
            "summary": {}
        }
        
        # Validate configuration files
        for pattern in self.config_files:
            files = list(self.project_root.glob(pattern))
            for file_path in files:
                if file_path.is_file():
                    validation_results["files_checked"].append(str(file_path.relative_to(self.project_root)))
                    file_issues = self.validate_file(file_path)
                    validation_results["issues"].extend([asdict(issue) for issue in file_issues])
        
        # Validate environment variables
        env_issues = self.validate_environment_variables()
        validation_results["environment_issues"].extend([asdict(issue) for issue in env_issues])
        
        # Generate summary
        all_issues = validation_results["issues"] + validation_results["environment_issues"]
        
        issue_counts = {}
        severity_counts = {}
        
        for issue in all_issues:
            issue_type = issue["issue_type"]
            severity = issue["severity"]
            
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        validation_results["summary"] = {
            "total_files_checked": len(validation_results["files_checked"]),
            "total_issues_found": len(all_issues),
            "critical_issues": severity_counts.get("critical", 0),
            "high_priority_issues": severity_counts.get("high", 0),
            "issue_breakdown": issue_counts,
            "severity_breakdown": severity_counts,
            "validation_duration_seconds": round(time.time() - start_time, 2),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "overall_status": self._determine_validation_status(severity_counts)
        }
        
        logger.info(f"Configuration validation complete: {len(all_issues)} issues found, "
                   f"{severity_counts.get('critical', 0)} critical")
        
        return validation_results

    def _determine_validation_status(self, severity_counts: Dict[str, int]) -> str:
        """Determine overall validation status."""
        if severity_counts.get("critical", 0) > 0:
            return "critical_issues_found"
        elif severity_counts.get("high", 0) > 0:
            return "high_priority_issues_found"
        elif severity_counts.get("medium", 0) > 0:
            return "minor_issues_found"
        else:
            return "configuration_compliant"

    def format_validation_report(self, results: Dict[str, Any]) -> str:
        """Format validation results for console output."""
        output = []
        output.append("=" * 80)
        output.append(f"INFRASTRUCTURE CONFIGURATION VALIDATION - Issue {results['issue_reference']}")
        output.append(f"Validation ID: {results['validation_run_id']}")
        output.append(f"Timestamp: {results['start_time']}")
        output.append("=" * 80)
        
        # Summary
        summary = results["summary"]
        output.append(f"\nVALIDATION STATUS: {summary['overall_status'].upper()}")
        output.append(f"Files Checked: {summary['total_files_checked']}")
        output.append(f"Total Issues: {summary['total_issues_found']}")
        output.append(f"Critical Issues: {summary['critical_issues']}")
        output.append(f"High Priority: {summary['high_priority_issues']}")
        
        # Critical issues detail
        if summary["critical_issues"] > 0:
            output.append("\n🚨 CRITICAL CONFIGURATION ISSUES:")
            output.append("-" * 50)
            
            all_issues = results["issues"] + results["environment_issues"]
            critical_issues = [issue for issue in all_issues if issue["severity"] == "critical"]
            
            for issue in critical_issues:
                output.append(f"❌ {issue['file_path']}:{issue.get('line_number', 'N/A')}")
                output.append(f"   Issue: {issue['issue_description']}")
                output.append(f"   Current: {issue['current_value']}")
                output.append(f"   Recommended: {issue['recommended_value']}")
                output.append(f"   Type: {issue['issue_type']}")
                
                # Show first remediation step
                if issue["remediation_steps"]:
                    output.append(f"   💡 Fix: {issue['remediation_steps'][0]}")
                output.append("")
        
        # Issue breakdown
        if summary["issue_breakdown"]:
            output.append("\nISSUE TYPE BREAKDOWN:")
            output.append("-" * 30)
            for issue_type, count in summary["issue_breakdown"].items():
                output.append(f"• {issue_type.replace('_', ' ').title()}: {count}")
        
        # Remediation summary
        output.append("\n" + "!" * 60)
        output.append("INFRASTRUCTURE TEAM REMEDIATION CHECKLIST:")
        output.append("✅ Review all critical configuration issues above")
        output.append("✅ Update deprecated domain patterns to *.netrasystems.ai")
        output.append("✅ Ensure VPC connector is properly configured")
        output.append("✅ Increase database timeouts to 600+ seconds")
        output.append("✅ Validate SSL certificate configuration")
        output.append("✅ Test connectivity after configuration changes")
        output.append("!" * 60)
        
        return "\n".join(output)


# Convenience function
def validate_infrastructure_config(project_root: Optional[str] = None) -> Dict[str, Any]:
    """Run infrastructure configuration validation."""
    validator = InfrastructureConfigValidator(project_root)
    results = validator.run_comprehensive_validation()
    report = validator.format_validation_report(results)
    print(report)
    return results


if __name__ == "__main__":
    import sys
    from datetime import datetime, timezone
    import time
    
    project_root = sys.argv[1] if len(sys.argv) > 1 else None
    validate_infrastructure_config(project_root)