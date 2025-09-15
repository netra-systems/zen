from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'\nenv = get_env()\nComprehensive Next.js Configuration Validation Tests\n\nTests that will INITIALLY FAIL to reproduce the Next.js config warning:\n"Invalid next.config.ts options detected: Unrecognized key(s) in object: \'swcMinify\'"\n\nThis test suite covers:\n1. Config validation tests\n2. Version migration tests  \n3. Build impact tests\n4. Extended scenarios\n\nAll tests are designed to FAIL initially to demonstrate the issues.\n'
import pytest
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

class NextJSConfigValidator:
    """
    Next.js configuration validator that will initially fail
    to demonstrate config compatibility issues.
    """
    DEPRECATED_OPTIONS_BY_VERSION = {'13.0.0': ['target', 'distDir'], '14.0.0': ['swcMinify', 'experimental.esmExternals'], '15.0.0': ['experimental.serverComponents', 'experimental.appDir']}
    REQUIRED_OPTIONS = ['output', 'productionBrowserSourceMaps']

    def __init__(self, config_path: str=None, next_version: str='15.1.0'):
        self.config_path = config_path or self._get_frontend_config_path()
        self.next_version = next_version
        self.config_content = None
        self.warnings = []
        self.errors = []

    def _get_frontend_config_path(self) -> str:
        """Get the path to the frontend next.config.ts file."""
        current_dir = Path(__file__).parent
        while current_dir.parent != current_dir:
            config_path = current_dir / 'frontend' / 'next.config.ts'
            if config_path.exists():
                return str(config_path)
            current_dir = current_dir.parent
        raise FileNotFoundError('Could not find frontend/next.config.ts')

    def load_config(self) -> Dict[str, Any]:
        """Load and parse Next.js config (initially will fail for some configs)."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f'Config file not found: {self.config_path}')
        with open(self.config_path, 'r') as f:
            self.config_content = f.read()
        config = {}
        if 'swcMinify: false' in self.config_content:
            config['swcMinify'] = False
        if "output: 'standalone'" in self.config_content:
            config['output'] = 'standalone'
        if 'productionBrowserSourceMaps: true' in self.config_content:
            config['productionBrowserSourceMaps'] = True
        return config

    def validate_deprecated_options(self) -> List[str]:
        """Validate deprecated options (will initially fail to detect all)."""
        deprecated_options = []
        for version, options in self.DEPRECATED_OPTIONS_BY_VERSION.items():
            if self._version_gte(self.next_version, version):
                for option in options:
                    if option in self.config_content:
                        deprecated_options.append(option)
                        self.warnings.append(f"Deprecated option '{option}' found")
        return deprecated_options

    def validate_required_options(self) -> List[str]:
        """Validate required options (will initially have incomplete checks)."""
        missing_options = []
        config = self.load_config()
        for option in self.REQUIRED_OPTIONS:
            if option not in config:
                missing_options.append(option)
                self.errors.append(f"Required option '{option}' missing")
        return missing_options

    def _version_gte(self, current: str, target: str) -> bool:
        """Compare versions (simplified, will initially have edge case failures)."""
        current_parts = [int(x) for x in current.split('.')]
        target_parts = [int(x) for x in target.split('.')]
        max_len = max(len(current_parts), len(target_parts))
        current_parts += [0] * (max_len - len(current_parts))
        target_parts += [0] * (max_len - len(target_parts))
        return current_parts >= target_parts

class MockNextJSBuild:
    """Mock Next.js build process to simulate build failures."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.build_output = []
        self.build_success = True
        self.warnings = []

    def run_build(self, environment: str='development') -> Dict[str, Any]:
        """Simulate Next.js build (will initially fail with bad configs)."""
        self.build_output = []
        if 'swcMinify' in open(self.config_path).read():
            warning = "Invalid next.config.ts options detected: Unrecognized key(s) in object: 'swcMinify'"
            self.warnings.append(warning)
            self.build_output.append(f'warn - {warning}')
        config_content = open(self.config_path).read()
        if 'domains:' in config_content and 'remotePatterns:' not in config_content:
            self.warnings.append('images.domains is deprecated, use images.remotePatterns')
        if environment == 'production' and 'ignoreBuildErrors: true' in config_content:
            self.warnings.append('TypeScript errors ignored in production build')
        return {'success': self.build_success, 'output': self.build_output, 'warnings': self.warnings, 'environment': environment}

@pytest.fixture
def config_validator():
    """Provide a config validator instance."""
    return NextJSConfigValidator()

@pytest.fixture
def mock_build():
    """Provide a mock build instance."""
    validator = NextJSConfigValidator()
    return MockNextJSBuild(validator.config_path)

class NextJSConfigValidationTests:
    """Core configuration validation tests that will initially fail."""

    def test_deprecated_swc_minify_option_detected(self, config_validator):
        """Test that swcMinify deprecated option is detected (WILL FAIL INITIALLY)."""
        deprecated_options = config_validator.validate_deprecated_options()
        assert 'swcMinify' in deprecated_options, 'swcMinify deprecated option should be detected'
        assert len(config_validator.warnings) > 0, 'Should have warnings for deprecated options'

    def test_next_15_compatibility_validation(self, config_validator):
        """Test Next.js 15 specific compatibility issues (WILL FAIL INITIALLY)."""
        config_validator.next_version = '15.1.0'
        deprecated = config_validator.validate_deprecated_options()
        assert 'swcMinify' in deprecated, 'swcMinify should be flagged as deprecated in Next.js 15'
        config_content = config_validator.config_content or config_validator.load_config()
        assert 'experimental.esmExternals' not in str(config_content), 'esmExternals should be removed in Next.js 15'
        assert 'domains:' not in str(config_content), 'images.domains deprecated in Next.js 15'

    def test_required_config_fields_validation(self, config_validator):
        """Test required configuration fields validation (WILL FAIL INITIALLY)."""
        missing = config_validator.validate_required_options()
        assert len(missing) == 0, f'Missing required options: {missing}'
        config = config_validator.load_config()
        assert 'rewrites' in config or callable(getattr(config, 'rewrites', None)), 'rewrites function should be defined'
        assert 'webpack' in config, 'webpack configuration should be present'

    def test_type_safety_validation(self, config_validator):
        """Test configuration type safety (WILL FAIL INITIALLY)."""
        config = config_validator.load_config()
        if 'productionBrowserSourceMaps' in config:
            assert isinstance(config['productionBrowserSourceMaps'], bool), 'productionBrowserSourceMaps should be boolean'
        if 'output' in config:
            valid_outputs = ['standalone', 'export', 'static']
            assert config['output'] in valid_outputs, f'output should be one of {valid_outputs}'
        if 'swcMinify' in config:
            assert isinstance(config['swcMinify'], bool), 'swcMinify should be boolean when present'

    def test_environment_specific_config_issues(self, config_validator):
        """Test environment-specific configuration problems (WILL FAIL INITIALLY)."""
        config_content = config_validator.config_content or open(config_validator.config_path).read()
        assert 'ignoreBuildErrors: true' not in config_content or 'development' in env.get('NODE_ENV', ''), 'ignoreBuildErrors should only be true in development'
        assert 'ignoreDuringBuilds: true' not in config_content or 'staging' in env.get('NODE_ENV', ''), 'ignoreDuringBuilds should only be true in staging'
        if env.get('NODE_ENV') == 'production':
            assert 'productionBrowserSourceMaps: false' in config_content, 'Source maps should be disabled in production'

class NextJSVersionMigrationTests:
    """Version migration tests that will initially fail."""

    def test_migration_from_next_13_to_15(self, config_validator):
        """Test migration path from Next.js 13 to 15 (WILL FAIL INITIALLY)."""
        old_deprecated = ['target', 'distDir']
        new_deprecated = config_validator.validate_deprecated_options()
        for option in old_deprecated:
            assert option not in new_deprecated, f'Next.js 13 deprecated option {option} should be migrated'
        config_content = open(config_validator.config_path).read()
        assert 'experimental.appDir' not in config_content, 'appDir is now stable, remove experimental prefix'
        assert 'experimental.serverComponents' not in config_content, 'serverComponents is now default'

    def test_breaking_changes_detection(self, config_validator):
        """Test detection of breaking changes between versions (WILL FAIL INITIALLY)."""
        breaking_changes = []
        config_content = open(config_validator.config_path).read()
        if 'swcMinify' in config_content:
            breaking_changes.append('swcMinify removed in Next.js 14+')
        if 'domains:' in config_content:
            breaking_changes.append('images.domains deprecated, use remotePatterns')
        assert len(breaking_changes) > 0, 'Should detect breaking changes in current config'
        assert 'target' not in config_content, 'target option removed in Next.js 13'
        assert 'future.webpack5' not in config_content, 'webpack5 is now default'

    def test_upgrade_path_validation(self, config_validator):
        """Test validation of upgrade paths (WILL FAIL INITIALLY)."""
        current_version = '15.1.0'
        upgrade_issues = self._get_upgrade_issues(config_validator, current_version)
        assert len(upgrade_issues) > 0, 'Should identify issues preventing upgrade'
        config_content = open(config_validator.config_path).read()
        expected_blockers = []
        if 'swcMinify' in config_content:
            expected_blockers.append('Remove swcMinify option')
        assert len(expected_blockers) > 0, 'Should have identified upgrade blockers'

    def _get_upgrade_issues(self, validator: NextJSConfigValidator, target_version: str) -> List[str]:
        """Get issues preventing upgrade to target version."""
        return []

class NextJSBuildImpactTests:
    """Build impact tests that will initially fail."""

    def test_build_warnings_with_deprecated_config(self, mock_build):
        """Test that build generates warnings for deprecated config (WILL FAIL INITIALLY)."""
        result = mock_build.run_build('development')
        assert len(result['warnings']) > 0, 'Should generate warnings for deprecated options'
        swc_warning_found = any(('swcMinify' in warning for warning in result['warnings']))
        assert swc_warning_found, 'Should warn about swcMinify deprecated option'
        domains_warning = any(('domains' in warning for warning in result['warnings']))
        assert domains_warning, 'Should warn about deprecated images.domains'

    def test_production_build_failures(self, mock_build):
        """Test production build failures with invalid config (WILL FAIL INITIALLY)."""
        result = mock_build.run_build('production')
        production_issues = [w for w in result['warnings'] if 'production' in w.lower()]
        assert len(production_issues) > 0, 'Should have production-specific warnings'
        assert result['success'] == True, 'Build should still succeed despite warnings'
        typescript_issues = [w for w in result['warnings'] if 'TypeScript' in w]
        assert len(typescript_issues) > 0, 'Should warn about ignored TypeScript errors in production'

    def test_webpack_compilation_with_bad_config(self, config_validator, mock_build):
        """Test webpack compilation issues with bad config (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        assert 'config.externals' in config_content, 'Should have webpack externals configuration'
        result = mock_build.run_build('development')
        webpack_warnings = [w for w in result['warnings'] if 'webpack' in w.lower()]
        assert len(webpack_warnings) == 0, 'Should not have webpack-specific warnings with current config'

    def test_runtime_behavior_with_missing_config(self, config_validator):
        """Test runtime behavior when required config is missing (WILL FAIL INITIALLY)."""
        config = config_validator.load_config()
        if 'output' not in config:
            assert False, 'Missing output config should cause runtime issues'
        if 'rewrites' not in config:
            assert False, 'Missing rewrites should cause API routing issues'
        config_content = open(config_validator.config_path).read()
        if 'NEXT_PUBLIC_API_URL' not in config_content:
            assert False, 'Missing API URL environment variable should cause runtime failures'

class ExtendedConfigScenariosTests:
    """Extended configuration scenario tests that will initially fail."""

    def test_dynamic_config_generation_issues(self, config_validator):
        """Test issues with dynamic config generation (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        if 'process.env.NEXT_PUBLIC_API_URL' in config_content:
            assert env.get('NEXT_PUBLIC_API_URL'), 'Required environment variable missing'
        if 'async rewrites()' in config_content:
            assert 'backendUrl' in config_content, 'Dynamic rewrites should define backendUrl'
        assert 'if (process.env.NODE_ENV' not in config_content, 'Avoid conditional config in next.config.ts'

    def test_config_inheritance_and_merging(self, config_validator):
        """Test configuration inheritance and merging issues (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        if 'withNextra' in config_content or 'withPWA' in config_content:
            assert False, 'Config plugins should be properly merged'
        if 'standalone' in config_content and 'static' in config_content:
            assert False, 'Conflicting output configurations detected'

    def test_plugin_compatibility_issues(self, config_validator):
        """Test plugin compatibility issues (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        if '@next/bundle-analyzer' in config_content:
            assert 'ANALYZE' in os.environ, 'Bundle analyzer requires ANALYZE environment variable'
        plugins = []
        if 'withPWA' in config_content:
            plugins.append('PWA')
        if 'withNextra' in config_content:
            plugins.append('Nextra')
        if len(plugins) > 1:
            assert False, f'Multiple plugins may conflict: {plugins}'

    def test_environment_variable_validation(self, config_validator):
        """Test environment variable validation in config (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        import re
        env_vars = re.findall('process\\.env\\.(\\w+)', config_content)
        required_vars = ['NEXT_PUBLIC_API_URL', 'NODE_ENV']
        for var in required_vars:
            if var in env_vars:
                assert env.get(var), f'Required environment variable {var} is not set'
        if 'NEXT_PUBLIC_API_URL' in env_vars:
            api_url = env.get('NEXT_PUBLIC_API_URL', 'http://localhost:8000')
            assert api_url.startswith(('http://', 'https://')), 'API URL should be a valid HTTP URL'

    def test_security_configuration_issues(self, config_validator):
        """Test security-related configuration issues (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        if 'productionBrowserSourceMaps: true' in config_content:
            assert env.get('NODE_ENV') != 'production', 'Source maps should be disabled in production for security'
        if 'ignoreBuildErrors: true' in config_content:
            assert env.get('NODE_ENV') != 'production', 'Build errors should not be ignored in production'
        if 'domains:' in config_content:
            domains_match = re.search('domains:\\s*\\[(.*?)\\]', config_content, re.DOTALL)
            if domains_match:
                domains_str = domains_match.group(1)
                assert "'*'" not in domains_str, 'Wildcard domains are security risk'
                assert "'localhost'" not in domains_str or env.get('NODE_ENV') != 'production', 'localhost domain should not be in production'

    def test_performance_configuration_validation(self, config_validator):
        """Test performance-related configuration validation (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        if 'swcMinify: false' in config_content:
            assert False, "swcMinify should be enabled for better performance (or removed as it's default)"
        if 'outputFileTracing' not in config_content:
            assert False, 'outputFileTracing should be configured for optimal bundle size'
        if 'webpack:' in config_content:
            assert 'config.externals' in config_content, 'Webpack externals should be configured for performance'

    def test_typescript_configuration_integration(self, config_validator):
        """Test TypeScript configuration integration issues (WILL FAIL INITIALLY)."""
        config_content = open(config_validator.config_path).read()
        if 'ignoreBuildErrors: true' in config_content:
            tsconfig_path = Path(config_validator.config_path).parent / 'tsconfig.json'
            if tsconfig_path.exists():
                with open(tsconfig_path) as f:
                    tsconfig = json.load(f)
                assert tsconfig.get('compilerOptions', {}).get('strict') != True, 'Strict TypeScript with ignored build errors is inconsistent'
        if 'typescript:' in config_content:
            assert 'ignoreBuildErrors' in config_content, 'TypeScript section should have ignoreBuildErrors'

class ConfigValidationIntegrationTests:
    """Integration tests for configuration validation (will initially fail)."""

    def test_end_to_end_config_validation(self, config_validator, mock_build):
        """Test complete end-to-end configuration validation (WILL FAIL INITIALLY)."""
        deprecated = config_validator.validate_deprecated_options()
        missing = config_validator.validate_required_options()
        build_result = mock_build.run_build('production')
        total_issues = len(deprecated) + len(missing) + len(build_result['warnings'])
        assert total_issues > 0, 'Should find configuration issues in current setup'
        swc_issue_found = 'swcMinify' in deprecated or any(('swcMinify' in warning for warning in build_result['warnings']))
        assert swc_issue_found, 'Should detect swcMinify configuration issue'

    def test_multi_environment_validation(self, config_validator):
        """Test configuration validation across multiple environments (WILL FAIL INITIALLY)."""
        environments = ['development', 'staging', 'production']
        for env in environments:
            with patch.dict(os.environ, {'NODE_ENV': env}):
                env_issues = self._validate_environment_config(config_validator, env)
                if env == 'production':
                    assert len(env_issues) == 0, f'Production should have no config issues: {env_issues}'
                else:
                    pass

    def _validate_environment_config(self, validator: NextJSConfigValidator, environment: str) -> List[str]:
        """Validate configuration for specific environment."""
        issues = []
        config_content = open(validator.config_path).read()
        if environment == 'production':
            if 'ignoreBuildErrors: true' in config_content:
                issues.append('Build errors ignored in production')
            if 'productionBrowserSourceMaps: true' in config_content:
                issues.append('Source maps enabled in production')
        return issues

    def test_regression_prevention(self, config_validator):
        """Test that configuration changes don't introduce regressions (WILL FAIL INITIALLY)."""
        current_config = config_validator.load_config()
        test_config = current_config.copy()
        test_config['swcMinify'] = True
        if 'swcMinify' in test_config:
            assert False, 'Adding swcMinify would be a regression in Next.js 15'
        breaking_changes = ['target', 'future.webpack5', 'experimental.appDir']
        for change in breaking_changes:
            if change in str(test_config):
                assert False, f'Adding {change} would be a regression'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')