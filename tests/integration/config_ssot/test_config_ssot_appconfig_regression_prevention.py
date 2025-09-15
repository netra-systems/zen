"""
Regression prevention test suite for AppConfig SSOT compliance.

This test suite ensures that the SSOT violation fix remains in place
and prevents future regressions in database URL construction.

Issue #799: Prevent regression of AppConfig SSOT violations
"""
import pytest
import inspect
import ast
import os
from unittest.mock import patch
from netra_backend.app.schemas.config import AppConfig, DevelopmentConfig, StagingConfig, ProductionConfig
from shared.database_url_builder import DatabaseURLBuilder


class SSotViolationDetector(ast.NodeVisitor):
    """AST visitor to detect SSOT violations in source code."""
    
    def __init__(self):
        self.violations = []
        self.current_method = None
    
    def visit_FunctionDef(self, node):
        self.current_method = node.name
        self.generic_visit(node)
        self.current_method = None
    
    def visit_Call(self, node):
        # Detect manual URL construction patterns
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 'env' and 
                node.func.attr == 'get'):
                # Check if this env.get call is for URL construction
                if (len(node.args) > 0 and 
                    isinstance(node.args[0], ast.Constant) and
                    any(var in node.args[0].value for var in ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD'])):
                    self.violations.append(f"Direct env.get() call for {node.args[0].value} in {self.current_method}")
        
        self.generic_visit(node)
    
    def visit_JoinedStr(self, node):
        # Detect f-string URL construction
        if any(isinstance(value, ast.FormattedValue) for value in node.values):
            # Check if this looks like URL construction
            str_content = ""
            for value in node.values:
                if isinstance(value, ast.Constant):
                    str_content += value.value
            
            if "postgresql://" in str_content:
                self.violations.append(f"F-string URL construction in {self.current_method}: contains 'postgresql://'")
        
        self.generic_visit(node)


@pytest.mark.integration
class TestConfigSSotAppConfigRegressionPrevention:
    """Regression prevention tests for AppConfig SSOT compliance."""
    
    def test_appconfig_get_database_url_no_manual_construction_regression(self):
        """
        REGRESSION PREVENTION: Ensure AppConfig.get_database_url never regresses to manual construction.
        
        This test uses AST analysis to detect manual construction patterns.
        """
        # Get source code and parse it
        source = inspect.getsource(AppConfig.get_database_url)
        tree = ast.parse(source)
        
        # Use AST visitor to detect violations
        detector = SSotViolationDetector()
        detector.visit(tree)
        
        # Report any violations found
        assert not detector.violations, \
            f"REGRESSION: Manual URL construction detected in AppConfig.get_database_url: {detector.violations}"
    
    def test_appconfig_source_code_regression_analysis(self):
        """
        REGRESSION PREVENTION: Analyze AppConfig source for SSOT violation patterns.
        
        Comprehensive source code analysis for regression detection.
        """
        # Get full AppConfig class source
        source = inspect.getsource(AppConfig)
        
        # Define patterns that indicate SSOT violations
        violation_patterns = [
            # Direct URL construction patterns
            (r'f["\']postgresql://', "F-string PostgreSQL URL construction"),
            (r'f["\']clickhouse\+native://', "F-string ClickHouse URL construction"),
            (r'return f["\']postgresql://', "Direct f-string URL return"),
            
            # Manual environment access for URL construction
            (r'env\.get\(["\']POSTGRES_HOST["\']', "Direct POSTGRES_HOST environment access"),
            (r'env\.get\(["\']POSTGRES_USER["\']', "Direct POSTGRES_USER environment access"),
            (r'env\.get\(["\']POSTGRES_PASSWORD["\']', "Direct POSTGRES_PASSWORD environment access"),
            (r'env\.get\(["\']POSTGRES_DB["\']', "Direct POSTGRES_DB environment access"),
            (r'env\.get\(["\']CLICKHOUSE_HOST["\']', "Direct CLICKHOUSE_HOST environment access"),
            
            # Manual string formatting patterns
            (r'["\']postgresql://.*\{.*user.*\}.*\{.*password.*\}', "Manual PostgreSQL URL formatting"),
            (r'["\']clickhouse\+native://.*\{.*\}', "Manual ClickHouse URL formatting"),
        ]
        
        violations_found = []
        import re
        
        for pattern, description in violation_patterns:
            if re.search(pattern, source, re.IGNORECASE):
                violations_found.append(f"{description}: pattern '{pattern}' found")
        
        # Report violations
        assert not violations_found, \
            f"REGRESSION: SSOT violations detected in AppConfig source:\n" + "\n".join(violations_found)
    
    def test_development_config_ssot_regression_prevention(self):
        """
        REGRESSION PREVENTION: Ensure DevelopmentConfig maintains DatabaseURLBuilder SSOT usage.
        """
        # Test that DevelopmentConfig properly delegates to DatabaseURLBuilder
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            expected_ssot_url = "postgresql+asyncpg://ssot:ssot@localhost:5432/ssot_db"
            mock_builder.development.auto_url = expected_ssot_url
            mock_builder_class.return_value = mock_builder
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {'ENVIRONMENT': 'development'}
                mock_env.return_value = mock_env_instance
                
                # Create config - should use DatabaseURLBuilder
                config = DevelopmentConfig()
                
                # Verify DatabaseURLBuilder was called (SSOT usage)
                mock_builder_class.assert_called()
                
                # Verify URL comes from builder
                assert config.database_url == expected_ssot_url, \
                    f"REGRESSION: DevelopmentConfig not using DatabaseURLBuilder SSOT. Expected: {expected_ssot_url}, Got: {config.database_url}"
    
    def test_staging_config_ssot_regression_prevention(self):
        """
        REGRESSION PREVENTION: Ensure StagingConfig maintains DatabaseURLBuilder SSOT usage.
        """
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            expected_ssot_url = "postgresql+asyncpg://staging:staging@staging-host:5432/staging_db?ssl=require"
            mock_builder.staging.auto_url = expected_ssot_url
            mock_builder_class.return_value = mock_builder
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {'ENVIRONMENT': 'staging'}
                mock_env.return_value = mock_env_instance
                
                config = StagingConfig()
                
                mock_builder_class.assert_called()
                assert config.database_url == expected_ssot_url, \
                    f"REGRESSION: StagingConfig not using DatabaseURLBuilder SSOT"
    
    def test_production_config_ssot_regression_prevention(self):
        """
        REGRESSION PREVENTION: Ensure ProductionConfig maintains DatabaseURLBuilder SSOT usage.
        """
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            expected_ssot_url = "postgresql+asyncpg://prod:prod@/cloudsql/proj:region:inst/prod_db"
            mock_builder.production.auto_url = expected_ssot_url
            mock_builder_class.return_value = mock_builder
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_instance = MagicMock()
                mock_env_instance.as_dict.return_value = {'ENVIRONMENT': 'production'}
                mock_env.return_value = mock_env_instance
                
                config = ProductionConfig()
                
                mock_builder_class.assert_called()
                assert config.database_url == expected_ssot_url, \
                    f"REGRESSION: ProductionConfig not using DatabaseURLBuilder SSOT"
    
    def test_no_manual_fallback_logic_regression(self):
        """
        REGRESSION PREVENTION: Ensure no manual fallback logic exists that bypasses SSOT.
        """
        # Check AppConfig methods for manual fallback patterns
        methods_to_check = [
            (AppConfig.get_database_url, "get_database_url"),
            (AppConfig.get_clickhouse_url, "get_clickhouse_url"),
        ]
        
        for method, method_name in methods_to_check:
            source = inspect.getsource(method)
            
            # Patterns that indicate manual fallback logic
            fallback_patterns = [
                "if not.*database_url",  # Fallback when builder URL is None
                "# Fallback to construct",  # Comment indicating manual fallback
                "env.get.*host.*port.*user",  # Manual environment construction
            ]
            
            import re
            violations = []
            for pattern in fallback_patterns:
                if re.search(pattern, source, re.IGNORECASE):
                    violations.append(f"Manual fallback pattern '{pattern}' in {method_name}")
            
            assert not violations, \
                f"REGRESSION: Manual fallback logic detected:\n" + "\n".join(violations)
    
    def test_database_url_builder_integration_regression(self):
        """
        REGRESSION PREVENTION: Ensure DatabaseURLBuilder integration remains functional.
        
        This test validates that the SSOT integration actually works.
        """
        test_env = {
            'ENVIRONMENT': 'development',
            'POSTGRES_HOST': 'regression-test-host',
            'POSTGRES_USER': 'regression-user',
            'POSTGRES_PASSWORD': 'regression-pass',
            'POSTGRES_DB': 'regression-db'
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            # Test direct DatabaseURLBuilder usage
            builder = DatabaseURLBuilder(test_env)
            builder_url = builder.development.auto_url
            
            # Test AppConfig usage
            config = AppConfig()
            appconfig_url = config.get_database_url()
            
            # After SSOT fix, these should be consistent
            # If they differ, it indicates regression to manual construction
            assert appconfig_url is not None, "AppConfig should return a URL"
            
            # The URLs should follow the same pattern (indicating SSOT usage)
            # Both should come from DatabaseURLBuilder
            if builder_url and appconfig_url:
                # Extract connection components to compare SSOT consistency
                assert 'regression-test-host' in appconfig_url or 'localhost' in appconfig_url, \
                    f"REGRESSION: AppConfig URL doesn't reflect environment or SSOT pattern: {appconfig_url}"
    
    def test_clickhouse_url_construction_regression(self):
        """
        REGRESSION PREVENTION: Ensure ClickHouse URL construction doesn't regress to manual.
        """
        # Analyze ClickHouse URL construction method
        source = inspect.getsource(AppConfig.get_clickhouse_url)
        
        # Check for manual construction patterns
        manual_patterns = [
            r'f["\']clickhouse\+native://',  # F-string construction
            r'env\.get\(["\']CLICKHOUSE_HOST["\'].*env\.get\(["\']CLICKHOUSE_PORT["\']',  # Multiple env.get calls
        ]
        
        import re
        violations = []
        for pattern in manual_patterns:
            if re.search(pattern, source):
                violations.append(f"Manual ClickHouse construction pattern: {pattern}")
        
        # Allow controlled manual construction for ClickHouse (different from PostgreSQL SSOT violation)
        # But ensure it's not the same problematic pattern as the PostgreSQL issue
        
        # The key test is that it should use configuration objects, not direct env access
        if 'env.get(' in source and 'clickhouse' in source.lower():
            # This indicates potential regression to the same anti-pattern
            direct_env_usage = re.findall(r'env\.get\(["\'][^"\']*["\']', source)
            if len(direct_env_usage) > 2:  # More than reasonable for fallback
                violations.append(f"Excessive direct env.get usage: {direct_env_usage}")
        
        # Report violations if any
        if violations:
            pytest.fail(f"REGRESSION: ClickHouse URL construction issues:\n" + "\n".join(violations))
    
    def test_environment_isolation_regression(self):
        """
        REGRESSION PREVENTION: Ensure environment isolation is maintained through SSOT.
        """
        # Test that different environments produce different URLs through SSOT
        environments = ['development', 'staging', 'production']
        urls = {}
        
        for env in environments:
            test_env = {
                'ENVIRONMENT': env,
                'POSTGRES_HOST': f'{env}-host',
                'POSTGRES_USER': f'{env}-user',
                'POSTGRES_PASSWORD': f'{env}-pass',
                'POSTGRES_DB': f'{env}-db'
            }
            
            with patch.dict(os.environ, test_env, clear=False):
                builder = DatabaseURLBuilder(test_env)
                
                if env == 'development':
                    url = builder.development.auto_url
                elif env == 'staging':
                    url = builder.staging.auto_url
                elif env == 'production':
                    url = builder.production.auto_url
                
                urls[env] = url
        
        # Verify each environment gets appropriate URLs
        for env, url in urls.items():
            if url:  # Skip if builder returned None
                assert f'{env}-' in url or env in url, \
                    f"REGRESSION: Environment {env} URL doesn't reflect environment: {url}"
        
        # Verify URLs are different (proper isolation)
        unique_urls = set(url for url in urls.values() if url)
        assert len(unique_urls) >= 2, \
            f"REGRESSION: Environment isolation failed - URLs not differentiated: {urls}"
    
    def test_ssot_import_regression(self):
        """
        REGRESSION PREVENTION: Ensure DatabaseURLBuilder imports are maintained.
        """
        # Check that config files properly import DatabaseURLBuilder
        config_files = [
            'netra_backend.app.schemas.config',
        ]
        
        for module_name in config_files:
            try:
                module = __import__(module_name, fromlist=[''])
                
                # Check module source for DatabaseURLBuilder import
                if hasattr(module, '__file__'):
                    with open(module.__file__, 'r') as f:
                        source = f.read()
                    
                    # Verify DatabaseURLBuilder is imported
                    assert 'from shared.database_url_builder import DatabaseURLBuilder' in source, \
                        f"REGRESSION: DatabaseURLBuilder import missing from {module_name}"
                    
                    # Verify it's actually used (not just imported)
                    assert 'DatabaseURLBuilder(' in source, \
                        f"REGRESSION: DatabaseURLBuilder not used in {module_name}"
            
            except Exception as e:
                pytest.fail(f"REGRESSION: Error checking module {module_name}: {e}")
    
    def test_config_initialization_ssot_regression(self):
        """
        REGRESSION PREVENTION: Test config initialization uses SSOT consistently.
        """
        # Test various config initialization scenarios
        scenarios = [
            ('DevelopmentConfig', DevelopmentConfig),
            ('StagingConfig', StagingConfig),
            ('ProductionConfig', ProductionConfig),
        ]
        
        for config_name, config_class in scenarios:
            with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = MagicMock()
                mock_builder.development.auto_url = "postgresql+asyncpg://dev:dev@localhost:5432/dev"
                mock_builder.staging.auto_url = "postgresql+asyncpg://staging:staging@staging:5432/staging"
                mock_builder.production.auto_url = "postgresql+asyncpg://prod:prod@prod:5432/prod"
                mock_builder_class.return_value = mock_builder
                
                with patch('shared.isolated_environment.get_env') as mock_env:
                    mock_env_instance = MagicMock()
                    mock_env_instance.as_dict.return_value = {'ENVIRONMENT': 'test'}
                    mock_env.return_value = mock_env_instance
                    
                    # Initialize config
                    config = config_class()
                    
                    # Verify DatabaseURLBuilder was called during initialization
                    assert mock_builder_class.called, \
                        f"REGRESSION: {config_name} not using DatabaseURLBuilder during initialization"
                    
                    # Verify environment dict was passed
                    call_args = mock_builder_class.call_args
                    assert call_args is not None, f"REGRESSION: {config_name} not calling DatabaseURLBuilder properly"
                    assert len(call_args[0]) > 0, f"REGRESSION: {config_name} not passing environment to DatabaseURLBuilder"
