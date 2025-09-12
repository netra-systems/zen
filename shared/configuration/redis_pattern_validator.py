"""
Redis Configuration Pattern Validator
Validates that all services follow unified Redis configuration patterns as defined in Five Whys solution.
"""
from typing import Dict, List, Optional, Any, Tuple
import logging
import importlib
import inspect
from pathlib import Path

logger = logging.getLogger(__name__)


class RedisPatternViolation:
    """Represents a Redis configuration pattern violation."""
    
    def __init__(self, 
                 service: str, 
                 file_path: str, 
                 violation_type: str, 
                 description: str,
                 line_number: Optional[int] = None,
                 suggested_fix: Optional[str] = None):
        self.service = service
        self.file_path = file_path
        self.violation_type = violation_type
        self.description = description
        self.line_number = line_number
        self.suggested_fix = suggested_fix
    
    def __str__(self) -> str:
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"
        
        return f"[{self.service}] {self.violation_type}: {self.description} ({location})"


class RedisConfigurationPatternValidator:
    """
    Validates Redis configuration patterns across all services.
    
    Ensures compliance with Five Whys unified configuration management:
    1. All services use RedisConfigurationBuilder pattern
    2. No direct REDIS_URL environment access  
    3. Proper Docker environment detection
    4. Consistent environment-specific behavior
    5. Service independence maintained
    """
    
    EXPECTED_PATTERNS = {
        "redis_builder_import": [
            "from shared.redis_configuration_builder import RedisConfigurationBuilder",
            "from auth_core.redis_config_builder import get_auth_redis_builder"
        ],
        "redis_builder_usage": [
            "RedisConfigurationBuilder(",
            "get_auth_redis_builder(",
            "builder.get_url_for_environment()"
        ],
        "forbidden_patterns": [
            'env.get("REDIS_URL"',  # Direct REDIS_URL access forbidden
            'os.environ.get("REDIS_URL"',  # Direct OS environ access forbidden  
            'redis://localhost:6379',  # Hard-coded URLs forbidden
            'return "redis://'  # Hard-coded return URLs forbidden
        ]
    }
    
    APPROVED_SERVICES = {
        "netra_backend": {
            "config_file": "netra_backend/app/core/backend_environment.py",
            "expected_builder": "RedisConfigurationBuilder",
            "expected_import": "from shared.redis_configuration_builder import RedisConfigurationBuilder"
        },
        "auth_service": {
            "config_file": "auth_service/auth_core/auth_environment.py", 
            "expected_builder": "get_auth_redis_builder",
            "expected_import": "from auth_core.redis_config_builder import get_auth_redis_builder"
        }
    }
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize validator with project root path."""
        self.project_root = project_root or Path.cwd()
        self.violations: List[RedisPatternViolation] = []
    
    def validate_all_services(self) -> List[RedisPatternViolation]:
        """
        Validate Redis configuration patterns across all services.
        
        Returns:
            List of RedisPatternViolation objects
        """
        self.violations.clear()
        
        for service_name, service_config in self.APPROVED_SERVICES.items():
            self._validate_service(service_name, service_config)
        
        # Scan for unauthorized Redis configurations
        self._scan_for_unauthorized_redis_usage()
        
        return self.violations
    
    def _validate_service(self, service_name: str, service_config: Dict[str, str]) -> None:
        """Validate a specific service's Redis configuration."""
        config_file = self.project_root / service_config["config_file"]
        
        if not config_file.exists():
            self.violations.append(
                RedisPatternViolation(
                    service=service_name,
                    file_path=str(config_file),
                    violation_type="MISSING_CONFIG_FILE",
                    description=f"Expected configuration file not found",
                    suggested_fix=f"Create {service_config['config_file']} with proper Redis configuration"
                )
            )
            return
        
        content = config_file.read_text()
        lines = content.split('\n')
        
        # Check for proper import
        expected_import = service_config["expected_import"]
        if expected_import not in content:
            self.violations.append(
                RedisPatternViolation(
                    service=service_name,
                    file_path=str(config_file),
                    violation_type="MISSING_BUILDER_IMPORT",
                    description=f"Missing required import: {expected_import}",
                    suggested_fix=f"Add import: {expected_import}"
                )
            )
        
        # Check for proper builder usage
        expected_builder = service_config["expected_builder"]
        if expected_builder not in content:
            self.violations.append(
                RedisPatternViolation(
                    service=service_name,
                    file_path=str(config_file),
                    violation_type="MISSING_BUILDER_USAGE",
                    description=f"Missing required builder usage: {expected_builder}",
                    suggested_fix=f"Use {expected_builder} for Redis configuration"
                )
            )
        
        # Check for forbidden patterns
        self._check_forbidden_patterns(service_name, config_file, lines)
        
        # Check for proper environment detection
        self._check_environment_detection(service_name, config_file, content)
    
    def _check_forbidden_patterns(self, service_name: str, config_file: Path, lines: List[str]) -> None:
        """Check for forbidden Redis configuration patterns."""
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            for forbidden_pattern in self.EXPECTED_PATTERNS["forbidden_patterns"]:
                if forbidden_pattern in line_stripped:
                    # Skip if it's in a comment or docstring
                    if line_stripped.startswith('#') or '"""' in line_stripped:
                        continue
                    
                    self.violations.append(
                        RedisPatternViolation(
                            service=service_name,
                            file_path=str(config_file),
                            violation_type="FORBIDDEN_PATTERN",
                            description=f"Direct Redis URL access forbidden: {forbidden_pattern}",
                            line_number=line_num,
                            suggested_fix="Use RedisConfigurationBuilder instead"
                        )
                    )
    
    def _check_environment_detection(self, service_name: str, config_file: Path, content: str) -> None:
        """Check for proper environment detection patterns."""
        required_methods = [
            "get_url_for_environment",
            "is_docker_environment",
            "apply_docker_hostname_resolution"
        ]
        
        for method in required_methods:
            if method not in content:
                self.violations.append(
                    RedisPatternViolation(
                        service=service_name,
                        file_path=str(config_file),
                        violation_type="MISSING_ENVIRONMENT_DETECTION",
                        description=f"Missing environment detection method: {method}",
                        suggested_fix=f"Ensure RedisConfigurationBuilder provides {method}"
                    )
                )
    
    def _scan_for_unauthorized_redis_usage(self) -> None:
        """Scan for unauthorized Redis configuration usage across the codebase."""
        # Scan Python files for Redis usage outside approved services
        python_files = list(self.project_root.rglob("*.py"))
        
        for py_file in python_files:
            # Skip approved service config files
            if any(str(py_file).endswith(config["config_file"]) 
                   for config in self.APPROVED_SERVICES.values()):
                continue
            
            # Skip test files and migration files (allowed to have direct Redis access)
            if "test" in str(py_file) or "migration" in str(py_file):
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Check for unauthorized Redis URL patterns
                    unauthorized_patterns = [
                        'REDIS_URL',
                        'redis://localhost',
                        'redis://redis',  # Docker Redis without builder
                        'redis://127.0.0.1'
                    ]
                    
                    for pattern in unauthorized_patterns:
                        if pattern in line_stripped and not line_stripped.startswith('#'):
                            # Skip if it's in builder or shared config files
                            if 'redis_configuration_builder' in str(py_file) or 'shared' in str(py_file):
                                continue
                                
                            self.violations.append(
                                RedisPatternViolation(
                                    service="UNKNOWN",
                                    file_path=str(py_file),
                                    violation_type="UNAUTHORIZED_REDIS_USAGE",
                                    description=f"Unauthorized Redis pattern: {pattern}",
                                    line_number=line_num,
                                    suggested_fix="Use service-specific RedisConfigurationBuilder"
                                )
                            )
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue
    
    def validate_redis_environment_variables(self, env_vars: Dict[str, str]) -> List[RedisPatternViolation]:
        """
        Validate Redis environment variables follow expected patterns.
        
        Args:
            env_vars: Dictionary of environment variables
            
        Returns:
            List of violations found
        """
        violations = []
        
        # Check for deprecated REDIS_URL usage
        if 'REDIS_URL' in env_vars and env_vars.get('ENVIRONMENT') in ['staging', 'production']:
            violations.append(
                RedisPatternViolation(
                    service="ENVIRONMENT",
                    file_path="environment_variables",
                    violation_type="DEPRECATED_REDIS_URL",
                    description="REDIS_URL environment variable deprecated in staging/production",
                    suggested_fix="Use component variables: REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB"
                )
            )
        
        # Check for required Redis components in staging/production
        if env_vars.get('ENVIRONMENT') in ['staging', 'production']:
            required_redis_vars = ['REDIS_HOST']
            missing_vars = [var for var in required_redis_vars if var not in env_vars]
            
            if missing_vars:
                violations.append(
                    RedisPatternViolation(
                        service="ENVIRONMENT",
                        file_path="environment_variables",
                        violation_type="MISSING_REDIS_COMPONENTS",
                        description=f"Missing required Redis variables: {missing_vars}",
                        suggested_fix=f"Add environment variables: {', '.join(missing_vars)}"
                    )
                )
        
        return violations
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive Redis configuration compliance report.
        
        Returns:
            Dictionary containing compliance status and details
        """
        violations = self.validate_all_services()
        
        # Group violations by type
        violation_types = {}
        for violation in violations:
            if violation.violation_type not in violation_types:
                violation_types[violation.violation_type] = []
            violation_types[violation.violation_type].append(violation)
        
        # Calculate compliance score
        total_checks = len(self.APPROVED_SERVICES) * 4  # 4 checks per service
        violations_count = len(violations)
        compliance_score = max(0, (total_checks - violations_count) / total_checks * 100)
        
        return {
            "compliance_score": round(compliance_score, 1),
            "total_violations": violations_count,
            "violation_types": {
                vtype: len(vlist) for vtype, vlist in violation_types.items()
            },
            "violations_by_service": {
                service: [v for v in violations if v.service == service]
                for service in list(self.APPROVED_SERVICES.keys()) + ["UNKNOWN", "ENVIRONMENT"]
            },
            "detailed_violations": violations,
            "recommendations": self._generate_recommendations(violation_types)
        }
    
    def _generate_recommendations(self, violation_types: Dict[str, List[RedisPatternViolation]]) -> List[str]:
        """Generate actionable recommendations based on violation patterns."""
        recommendations = []
        
        if "MISSING_BUILDER_IMPORT" in violation_types:
            recommendations.append(
                "Add proper RedisConfigurationBuilder imports to all service configuration files"
            )
        
        if "FORBIDDEN_PATTERN" in violation_types:
            recommendations.append(
                "Replace direct REDIS_URL access with RedisConfigurationBuilder pattern"
            )
        
        if "UNAUTHORIZED_REDIS_USAGE" in violation_types:
            recommendations.append(
                "Consolidate unauthorized Redis usage into service-specific configuration builders"
            )
        
        if "MISSING_ENVIRONMENT_DETECTION" in violation_types:
            recommendations.append(
                "Ensure all Redis configurations support Docker environment detection"
            )
        
        if not recommendations:
            recommendations.append("All Redis configuration patterns are compliant!")
        
        return recommendations


def validate_redis_patterns(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience function to validate Redis configuration patterns.
    
    Args:
        project_root: Path to project root, defaults to current working directory
        
    Returns:
        Compliance report dictionary
    """
    validator = RedisConfigurationPatternValidator(project_root)
    return validator.generate_compliance_report()


def print_redis_compliance_report(project_root: Optional[Path] = None) -> None:
    """
    Print Redis configuration compliance report to console.
    
    Args:
        project_root: Path to project root, defaults to current working directory
    """
    report = validate_redis_patterns(project_root)
    
    print("=" * 60)
    print("REDIS CONFIGURATION COMPLIANCE REPORT")
    print("=" * 60)
    print(f"Compliance Score: {report['compliance_score']}%")
    print(f"Total Violations: {report['total_violations']}")
    print()
    
    if report['total_violations'] > 0:
        print("VIOLATIONS BY TYPE:")
        for vtype, count in report['violation_types'].items():
            print(f"  {vtype}: {count}")
        print()
        
        print("DETAILED VIOLATIONS:")
        for violation in report['detailed_violations']:
            print(f"  [U+2022] {violation}")
        print()
    
    print("RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"  [U+2022] {rec}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    print_redis_compliance_report()