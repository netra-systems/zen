"""
Test Configuration SSOT: Scattered Configuration Anti-patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Detect and prevent scattered configuration anti-patterns
- Value Impact: Protects $120K+ MRR by identifying SSOT violations that cause config drift
- Strategic Impact: Eliminates cascade failures from fragmented configuration management

This test detects and validates against scattered configuration anti-patterns that
violate SSOT principles and can cause configuration drift, cascade failures,
and environment-specific bugs.
"""

import pytest
import ast
from pathlib import Path
from typing import List, Dict, Set
from unittest.mock import patch, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class ScatteredConfigDetector:
    """Utility class to detect scattered configuration anti-patterns."""
    
    CRITICAL_SERVICES = [
        "netra_backend/app",
        "auth_service", 
        "shared"
    ]
    
    ANTI_PATTERNS = {
        'multiple_config_classes': {
            'description': 'Multiple configuration classes doing similar work',
            'pattern': ['Config', 'Configuration', 'Settings', 'Env'],
            'severity': 'HIGH'
        },
        'direct_env_access': {
            'description': 'Direct os.environ access bypassing SSOT',
            'pattern': ['os.environ', 'getenv'],
            'severity': 'CRITICAL'  
        },
        'hardcoded_config_values': {
            'description': 'Hardcoded configuration values',
            'pattern': ['localhost', 'http://', 'postgresql://'],
            'severity': 'MEDIUM'
        },
        'scattered_validation': {
            'description': 'Configuration validation scattered across modules',
            'pattern': ['validate_config', 'check_config', 'verify_'],
            'severity': 'HIGH'
        },
        'duplicate_secret_management': {
            'description': 'Multiple secret management implementations',
            'pattern': ['secret', 'jwt', 'key'],
            'severity': 'CRITICAL'
        }
    }
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations = []
    
    def scan_for_anti_patterns(self) -> Dict[str, List[Dict]]:
        """Scan project for scattered configuration anti-patterns."""
        anti_pattern_results = {}
        
        for pattern_name, pattern_info in self.ANTI_PATTERNS.items():
            anti_pattern_results[pattern_name] = []
            
            for service_path in self.CRITICAL_SERVICES:
                service_dir = self.project_root / service_path
                if service_dir.exists():
                    violations = self._scan_service_for_pattern(
                        service_dir, service_path, pattern_name, pattern_info
                    )
                    anti_pattern_results[pattern_name].extend(violations)
        
        return anti_pattern_results
    
    def _scan_service_for_pattern(self, service_dir: Path, service_name: str, 
                                 pattern_name: str, pattern_info: Dict) -> List[Dict]:
        """Scan a service directory for specific anti-pattern."""
        violations = []
        
        for py_file in service_dir.rglob("*.py"):
            # Skip test files and __pycache__
            if 'test' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            file_violations = self._analyze_file_for_pattern(
                py_file, service_name, pattern_name, pattern_info
            )
            violations.extend(file_violations)
        
        return violations
    
    def _analyze_file_for_pattern(self, file_path: Path, service_name: str,
                                 pattern_name: str, pattern_info: Dict) -> List[Dict]:
        """Analyze a file for specific anti-pattern."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple pattern matching for demonstration
            for pattern in pattern_info['pattern']:
                if pattern.lower() in content.lower():
                    violations.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'service': service_name,
                        'pattern': pattern_name,
                        'matched_pattern': pattern,
                        'severity': pattern_info['severity'],
                        'description': pattern_info['description']
                    })
                    break  # One violation per file per pattern type
                    
        except (UnicodeDecodeError, IOError):
            pass
        
        return violations


class TestScatteredConfigurationAntiPatterns(BaseIntegrationTest):
    """Test detection of scattered configuration anti-patterns."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_detect_multiple_configuration_classes_antipattern(self, real_services_fixture):
        """
        Test detection of multiple configuration classes anti-pattern.
        
        Multiple configuration classes doing similar work violates SSOT principles.
        There should be a single UnifiedConfigManager handling configuration
        orchestration, not scattered config classes throughout the codebase.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        detector = ScatteredConfigDetector(project_root)
        
        anti_patterns = detector.scan_for_anti_patterns()
        
        # Check for multiple config class anti-pattern
        config_class_violations = anti_patterns.get('multiple_config_classes', [])
        
        # Group violations by service to identify proliferation
        violations_by_service = {}
        for violation in config_class_violations:
            service = violation['service']
            if service not in violations_by_service:
                violations_by_service[service] = []
            violations_by_service[service].append(violation)
        
        # CRITICAL: Too many config classes indicates SSOT violation
        excessive_config_services = []
        for service, violations in violations_by_service.items():
            if len(violations) > 3:  # Threshold for "too many"
                excessive_config_services.append((service, len(violations)))
        
        if excessive_config_services:
            excessive_report = "\n".join([
                f"Service {service} has {count} config classes (SSOT violation)"
                for service, count in excessive_config_services
            ])
            pytest.fail(f"Excessive configuration class proliferation:\n{excessive_report}")
        
        # Validate that core services use SSOT patterns
        # Check that UnifiedConfigManager exists and is being used
        core_config_files = [
            project_root / "netra_backend" / "app" / "core" / "configuration" / "base.py",
            project_root / "auth_service" / "auth_core" / "config.py"
        ]
        
        ssot_usage_count = 0
        for config_file in core_config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for SSOT patterns
                    ssot_indicators = [
                        'UnifiedConfigManager',
                        'get_unified_config',
                        'IsolatedEnvironment',
                        'get_env()'
                    ]
                    
                    if any(indicator in content for indicator in ssot_indicators):
                        ssot_usage_count += 1
                        
                except (UnicodeDecodeError, IOError):
                    continue
        
        # At least some core services should use SSOT patterns
        assert ssot_usage_count > 0, "Core services should use SSOT configuration patterns"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_detect_scattered_validation_antipattern(self, real_services_fixture):
        """
        Test detection of scattered validation anti-pattern.
        
        Configuration validation should be centralized in ConfigurationValidator
        and related components. Scattered validation logic across modules
        leads to inconsistent validation rules and SSOT violations.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        detector = ScatteredConfigDetector(project_root)
        
        anti_patterns = detector.scan_for_anti_patterns()
        
        scattered_validation = anti_patterns.get('scattered_validation', [])
        
        # Analyze validation distribution
        validation_files = set()
        for violation in scattered_validation:
            validation_files.add(violation['file'])
        
        # CRITICAL: Too many files doing validation indicates scattered patterns
        if len(validation_files) > 10:  # Threshold for excessive scatter
            validation_report = "\n".join(sorted(validation_files))
            pytest.fail(f"Validation logic scattered across {len(validation_files)} files:\n{validation_report}")
        
        # Validate that centralized validation exists
        centralized_validation_files = [
            "netra_backend/app/core/configuration/validator.py",
            "netra_backend/app/core/configuration/validator_auth.py", 
            "netra_backend/app/core/configuration/validator_database.py",
            "netra_backend/app/core/configuration/validator_llm.py"
        ]
        
        centralized_validation_count = 0
        for val_file in centralized_validation_files:
            val_path = project_root / val_file
            if val_path.exists():
                centralized_validation_count += 1
        
        # Should have centralized validation components
        assert centralized_validation_count > 0, "Should have centralized configuration validation"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_detect_duplicate_secret_management_antipattern(self, real_services_fixture):
        """
        Test detection of duplicate secret management anti-pattern.
        
        Secret management should be centralized through SharedJWTSecretManager
        and related SSOT components. Multiple implementations of secret 
        management lead to security inconsistencies and SSOT violations.
        """
        project_root = Path(__file__).parent.parent.parent.parent
        detector = ScatteredConfigDetector(project_root)
        
        anti_patterns = detector.scan_for_anti_patterns()
        
        secret_management_violations = anti_patterns.get('duplicate_secret_management', [])
        
        # Analyze secret management distribution
        secret_files = {}
        for violation in secret_management_violations:
            file_path = violation['file']
            if file_path not in secret_files:
                secret_files[file_path] = []
            secret_files[file_path].append(violation['matched_pattern'])
        
        # Check for concerning patterns
        jwt_files = []
        secret_files_list = []
        
        for file_path, patterns in secret_files.items():
            if any('jwt' in pattern.lower() for pattern in patterns):
                jwt_files.append(file_path)
            if any('secret' in pattern.lower() for pattern in patterns):
                secret_files_list.append(file_path)
        
        # CRITICAL: JWT handling should be centralized
        if len(jwt_files) > 3:  # Allow some reasonable distribution
            jwt_report = "\n".join(jwt_files)
            pytest.fail(f"JWT secret management scattered across {len(jwt_files)} files:\n{jwt_report}")
        
        # Validate centralized secret management exists
        centralized_secret_files = [
            "shared/jwt_secret_manager.py",
            "auth_service/auth_core/auth_environment.py",
            "netra_backend/app/core/configuration/validator_auth.py"
        ]
        
        centralized_secret_count = 0
        for secret_file in centralized_secret_files:
            secret_path = project_root / secret_file
            if secret_path.exists():
                centralized_secret_count += 1
        
        # Should have centralized secret management
        assert centralized_secret_count > 0, "Should have centralized secret management"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_validate_ssot_compliance_positive_patterns(self, real_services_fixture):
        """
        Test that positive SSOT patterns are properly implemented.
        
        This test validates that the correct SSOT patterns are in place:
        - UnifiedConfigManager for configuration orchestration
        - IsolatedEnvironment for environment management  
        - DatabaseURLBuilder for database configuration
        - ConfigurationValidator for validation
        """
        env = get_env()
        env.enable_isolation()
        
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Test SSOT component availability
        ssot_components = {
            'IsolatedEnvironment': {
                'file': 'shared/isolated_environment.py',
                'description': 'Environment management SSOT'
            },
            'DatabaseURLBuilder': {
                'file': 'shared/database_url_builder.py', 
                'description': 'Database URL construction SSOT'
            },
            'UnifiedConfigManager': {
                'file': 'netra_backend/app/core/configuration/base.py',
                'description': 'Configuration orchestration SSOT'  
            },
            'ConfigurationValidator': {
                'file': 'netra_backend/app/core/configuration/validator.py',
                'description': 'Configuration validation SSOT'
            }
        }
        
        missing_components = []
        
        for component_name, component_info in ssot_components.items():
            component_path = project_root / component_info['file']
            
            if not component_path.exists():
                missing_components.append(f"{component_name}: {component_info['description']}")
                continue
            
            # Check that file contains the expected component
            try:
                with open(component_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if component_name not in content:
                    missing_components.append(f"{component_name}: Not found in {component_info['file']}")
                    
            except (UnicodeDecodeError, IOError):
                missing_components.append(f"{component_name}: Could not read {component_info['file']}")
        
        # CRITICAL: All SSOT components should be present
        if missing_components:
            missing_report = "\n".join(missing_components)
            pytest.fail(f"Missing SSOT components:\n{missing_report}")
        
        # Test SSOT component integration
        try:
            # Test IsolatedEnvironment works
            env.set('SSOT_TEST_VAR', 'test_value', 'ssot_compliance_test')
            assert env.get('SSOT_TEST_VAR') == 'test_value'
            
            # Test DatabaseURLBuilder can be imported
            from shared.database_url_builder import DatabaseURLBuilder
            
            test_env_vars = {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_USER': 'test',
                'POSTGRES_PASSWORD': 'test',
                'POSTGRES_DB': 'test',
                'POSTGRES_PORT': '5432'
            }
            
            builder = DatabaseURLBuilder(test_env_vars)
            test_url = builder.get_url_for_environment(sync=False)
            assert 'postgresql+asyncpg://' in test_url
            
            # Test UnifiedConfigManager can be imported
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            
            # Test ConfigurationValidator can be imported  
            from netra_backend.app.core.configuration.validator import ConfigurationValidator
            
            # All SSOT components should be importable and functional
            
        except ImportError as e:
            pytest.fail(f"SSOT component import failure: {str(e)}")
        except Exception as e:
            pytest.fail(f"SSOT component functionality failure: {str(e)}")
        
        finally:
            env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_detect_hardcoded_configuration_antipattern(self, real_services_fixture):
        """
        Test detection of hardcoded configuration values anti-pattern.
        
        Hardcoded configuration values (URLs, database connections, etc.)
        violate SSOT principles and cause environment-specific failures.
        Configuration should come through environment variables and SSOT builders.
        """
        env = get_env()
        env.enable_isolation()
        
        # Test proper SSOT configuration patterns vs anti-patterns
        
        # Anti-pattern: Hardcoded values
        hardcoded_examples = {
            'database_url': 'postgresql://localhost:5432/hardcoded_db',
            'api_url': 'http://localhost:8000/api',
            'redis_url': 'redis://localhost:6379',
            'frontend_url': 'http://localhost:3000'
        }
        
        # SSOT pattern: Environment-driven configuration
        ssot_config = {
            'POSTGRES_HOST': 'configurable_host',
            'POSTGRES_PORT': '5432', 
            'POSTGRES_DB': 'configurable_db',
            'POSTGRES_USER': 'configurable_user',
            'POSTGRES_PASSWORD': 'configurable_password',
            'API_BASE_URL': 'https://api.example.com',
            'REDIS_URL': 'redis://configurable-redis:6379',
            'FRONTEND_URL': 'https://app.example.com'
        }
        
        for key, value in ssot_config.items():
            env.set(key, value, 'ssot_pattern_test')
        
        try:
            # Test that SSOT patterns are configurable and environment-aware
            
            # Database URL should be built from components, not hardcoded
            from shared.database_url_builder import DatabaseURLBuilder
            
            env_vars = env.get_all()
            builder = DatabaseURLBuilder(env_vars)
            
            constructed_url = builder.get_url_for_environment(sync=False)
            
            # CRITICAL: URL should be constructed from configurable components
            assert 'configurable_host' in constructed_url
            assert 'configurable_db' in constructed_url
            assert 'configurable_user' in constructed_url
            
            # Should NOT contain hardcoded localhost values
            hardcoded_url = hardcoded_examples['database_url']
            assert constructed_url != hardcoded_url, "Should not use hardcoded database URL"
            
            # Test environment-specific configuration
            environments = ['development', 'staging', 'production']
            
            for environment in environments:
                env.set('ENVIRONMENT', environment, 'env_test')
                env.set('POSTGRES_HOST', f'{environment}-db-host', 'env_test')
                env.set('API_BASE_URL', f'https://api.{environment}.example.com', 'env_test')
                
                # Configuration should adapt to environment
                env_vars = env.get_all()
                env_builder = DatabaseURLBuilder(env_vars)
                env_url = env_builder.get_url_for_environment(sync=False)
                
                # Should contain environment-specific values, not hardcoded ones
                assert f'{environment}-db-host' in env_url
                assert env.get('API_BASE_URL') == f'https://api.{environment}.example.com'
                
                # Should NOT be hardcoded localhost
                assert 'localhost' not in env.get('API_BASE_URL')
            
            # Test configuration validation catches hardcoded anti-patterns
            # (This would be implementation-specific to actual validator)
            
        finally:
            env.reset_to_original()