"""
Phase 4: SSOT Compliance Final Validation Tests
Issue #757 - Final SSOT compliance validation

These tests validate final SSOT compliance after deprecated
configuration manager removal.
"""
import os
import sys
import pytest
from pathlib import Path
import importlib.util

class TestSSOTComplianceFinalValidation:
    """Phase 4 Tests - Final SSOT compliance validation"""

    def test_deprecated_manager_completely_removed_FINAL(self):
        """FINAL: Deprecated configuration manager completely removed"""
        deprecated_path = Path('netra_backend/app/core/managers/unified_configuration_manager.py')
        assert not deprecated_path.exists(), f'SSOT VIOLATION: Deprecated configuration manager still exists at {deprecated_path}. SSOT compliance requires complete removal of duplicate implementations.'
        print('✅ Deprecated configuration manager completely removed')

    def test_canonical_ssot_is_only_configuration_source_FINAL(self):
        """FINAL: Canonical SSOT is the only configuration source"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            canonical_config = UnifiedConfigManager()
            assert canonical_config is not None, 'Canonical UnifiedConfigManager not available'
            deprecated_import_failed = False
            try:
                from netra_backend.app.core.configuration.base import UnifiedConfigurationManager
                deprecated_import_failed = False
            except ImportError:
                deprecated_import_failed = True
            assert deprecated_import_failed, f'SSOT VIOLATION: Deprecated configuration manager still importable. SSOT requires single source of truth for configuration.'
            print('✅ Canonical UnifiedConfigManager is the only configuration source')
        except ImportError as e:
            pytest.fail(f'Canonical UnifiedConfigManager not available: {e}')

    def test_no_import_references_to_deprecated_manager_FINAL(self):
        """FINAL: No code references deprecated configuration manager"""
        search_directories = ['netra_backend/app', 'scripts', 'tests']
        deprecated_import_references = []
        for directory in search_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            for py_file in dir_path.rglob('*.py'):
                if py_file.name == 'test_ssot_compliance_final_757.py':
                    continue
                try:
                    content = py_file.read_text(encoding='utf-8')
                    deprecated_patterns = ['from netra_backend.app.core.configuration.base', 'import unified_configuration_manager', 'UnifiedConfigurationManager']
                    for pattern in deprecated_patterns:
                        if pattern in content:
                            deprecated_import_references.append((str(py_file), pattern))
                            break
                except Exception:
                    continue
        assert len(deprecated_import_references) == 0, f'SSOT VIOLATION: Code still references deprecated configuration manager: {deprecated_import_references[:10]}... All references must be updated to canonical UnifiedConfigManager.'
        print('✅ No code references deprecated configuration manager')

    def test_canonical_configuration_provides_complete_interface_FINAL(self):
        """FINAL: Canonical configuration provides complete required interface"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            canonical_config = UnifiedConfigManager()
            public_interface = [attr for attr in dir(canonical_config) if not attr.startswith('_')]
            assert len(public_interface) >= 10, f'Canonical UnifiedConfigManager provides insufficient interface: {len(public_interface)} public attributes: {public_interface}. SSOT requires comprehensive functionality replacement.'
            accessible_interface = {}
            for attr_name in public_interface:
                try:
                    attr = getattr(canonical_config, attr_name)
                    if callable(attr):
                        result = attr()
                        accessible_interface[attr_name] = f'method: {type(result).__name__}'
                    else:
                        accessible_interface[attr_name] = f'property: {type(attr).__name__}'
                except Exception as e:
                    accessible_interface[attr_name] = f'error: {str(e)[:30]}'
            successful_access = sum((1 for result in accessible_interface.values() if not result.startswith('error')))
            assert successful_access >= len(public_interface) * 0.8, f'Canonical UnifiedConfigManager interface partially broken: {accessible_interface}. SSOT requires fully functional replacement.'
            print(f'✅ Canonical UnifiedConfigManager provides complete interface: {successful_access}/{len(public_interface)} attributes accessible')
        except ImportError as e:
            pytest.fail(f'Cannot validate canonical configuration interface: {e}')

    def test_deployment_scripts_use_canonical_configuration_FINAL(self):
        """FINAL: All deployment scripts use canonical configuration"""
        deployment_files = ['scripts/deploy_to_gcp.py', 'scripts/refresh_dev_services.py', 'docker-compose.yml', 'docker-compose.test.yml', 'docker-compose.dev.yml']
        deployment_config_references = {}
        for deployment_file in deployment_files:
            file_path = Path(deployment_file)
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text(encoding='utf-8')
                references = {'deprecated': 'unified_configuration_manager' in content, 'canonical': 'core.configuration.base' in content or 'UnifiedConfigManager' in content, 'mixed': False}
                references['mixed'] = references['deprecated'] and references['canonical']
                deployment_config_references[str(deployment_file)] = references
            except Exception:
                continue
        ssot_violations = []
        for file_path, refs in deployment_config_references.items():
            if refs['deprecated']:
                ssot_violations.append(f'{file_path}: uses deprecated config')
            if refs['mixed']:
                ssot_violations.append(f'{file_path}: mixed configuration references')
        assert len(ssot_violations) == 0, f'DEPLOYMENT SSOT VIOLATIONS: {ssot_violations}. All deployment scripts must use canonical configuration only.'
        print(f'✅ All deployment scripts comply with SSOT: {len(deployment_config_references)} files checked')

    def test_test_files_use_canonical_configuration_FINAL(self):
        """FINAL: Test files use canonical configuration (with migration tolerance)"""
        test_directories = ['tests', 'netra_backend/tests']
        test_config_usage = {'total_test_files': 0, 'deprecated_usage': 0, 'canonical_usage': 0, 'no_config_usage': 0}
        deprecated_test_files = []
        for test_dir in test_directories:
            test_path = Path(test_dir)
            if not test_path.exists():
                continue
            for py_file in test_path.rglob('*.py'):
                if py_file.name.startswith('test_') or 'test' in py_file.parts:
                    test_config_usage['total_test_files'] += 1
                    try:
                        content = py_file.read_text(encoding='utf-8')
                        has_deprecated = 'unified_configuration_manager' in content
                        has_canonical = 'core.configuration.base' in content or 'UnifiedConfigManager' in content
                        if has_deprecated:
                            test_config_usage['deprecated_usage'] += 1
                            deprecated_test_files.append(str(py_file))
                        elif has_canonical:
                            test_config_usage['canonical_usage'] += 1
                        else:
                            test_config_usage['no_config_usage'] += 1
                    except Exception:
                        continue
        total_files = test_config_usage['total_test_files']
        if total_files > 0:
            deprecated_percentage = test_config_usage['deprecated_usage'] / total_files * 100
            canonical_percentage = test_config_usage['canonical_usage'] / total_files * 100
            excessive_deprecated_usage = deprecated_percentage > 10
            if excessive_deprecated_usage:
                print(f"⚠️ High deprecated configuration usage in tests: {deprecated_percentage:.1f}% ({test_config_usage['deprecated_usage']}/{total_files})")
                print(f'Files using deprecated config: {deprecated_test_files[:5]}...')
            assert not excessive_deprecated_usage, f'EXCESSIVE DEPRECATED CONFIG USAGE IN TESTS: {deprecated_percentage:.1f}% of test files still use deprecated configuration. SSOT requires migration to canonical configuration.'
            print(f"✅ Test configuration usage acceptable: {canonical_percentage:.1f}% canonical, {deprecated_percentage:.1f}% deprecated, {test_config_usage['no_config_usage'] / total_files * 100:.1f}% no config")

    def test_configuration_architecture_coherence_FINAL(self):
        """FINAL: Configuration architecture is coherent and well-structured"""
        canonical_config_dir = Path('netra_backend/app/core/configuration')
        assert canonical_config_dir.exists(), 'Canonical configuration directory missing - architecture incomplete'
        config_files = list(canonical_config_dir.glob('*.py'))
        assert len(config_files) >= 1, f'Insufficient configuration files in canonical directory: {config_files}'
        base_config_file = canonical_config_dir / 'base.py'
        assert base_config_file.exists(), 'Base configuration file missing from canonical directory'
        base_config_size = base_config_file.stat().st_size
        assert base_config_size >= 1000, f'Base configuration file too small ({base_config_size} bytes) - insufficient for comprehensive configuration management'
        config_architecture = {'base_config': base_config_file.exists(), 'directory_exists': canonical_config_dir.exists(), 'sufficient_files': len(config_files) >= 1, 'substantial_implementation': base_config_size >= 1000}
        architecture_score = sum(config_architecture.values())
        assert architecture_score >= 4, f'Configuration architecture incomplete: {config_architecture}'
        print(f'✅ Configuration architecture coherent: {len(config_files)} files, {base_config_size} bytes base config')

    def test_ssot_principles_fully_implemented_FINAL(self):
        """FINAL: SSOT principles fully implemented for configuration"""
        ssot_compliance_checks = {'single_source': True, 'no_duplication': True, 'consistent_interface': True, 'proper_imports': True, 'deployment_ready': True}
        deprecated_exists = Path('netra_backend/app/core/managers/unified_configuration_manager.py').exists()
        canonical_exists = Path('netra_backend/app/core/configuration/base.py').exists()
        ssot_compliance_checks['single_source'] = canonical_exists and (not deprecated_exists)
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            deprecated_importable = True
            try:
                from netra_backend.app.core.configuration.base import UnifiedConfigurationManager
            except ImportError:
                deprecated_importable = False
            ssot_compliance_checks['no_duplication'] = not deprecated_importable
            config = UnifiedConfigManager()
            interface_methods = [m for m in dir(config) if not m.startswith('_')]
            ssot_compliance_checks['consistent_interface'] = len(interface_methods) >= 5
        except ImportError:
            ssot_compliance_checks['consistent_interface'] = False
            ssot_compliance_checks['no_duplication'] = True
        ssot_score = sum(ssot_compliance_checks.values())
        total_checks = len(ssot_compliance_checks)
        assert ssot_score >= total_checks, f'SSOT PRINCIPLES NOT FULLY IMPLEMENTED: {ssot_compliance_checks}. Score: {ssot_score}/{total_checks}. Full SSOT compliance required.'
        print(f'✅ SSOT principles fully implemented: {ssot_score}/{total_checks} checks passed')
        print(f'SSOT compliance details: {ssot_compliance_checks}')

class TestConfigurationMigrationCompleteness:
    """Validate migration completeness and system stability"""

    def test_system_stability_after_migration_FINAL(self):
        """FINAL: System remains stable after configuration migration"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            stability_results = []
            for attempt in range(5):
                try:
                    config = UnifiedConfigManager()
                    methods = [m for m in dir(config) if not m.startswith('_') and callable(getattr(config, m))]
                    if len(methods) > 0:
                        first_method = getattr(config, methods[0])
                        first_method()
                    stability_results.append(True)
                except Exception as e:
                    stability_results.append(False)
                    print(f'Stability test {attempt + 1} failed: {e}')
            stability_score = sum(stability_results)
            assert stability_score >= len(stability_results), f'SYSTEM UNSTABLE AFTER MIGRATION: {stability_results}. Configuration migration has introduced instability.'
            print(f'✅ System stable after migration: {stability_score}/{len(stability_results)} tests passed')
        except ImportError as e:
            pytest.fail(f'System stability test failed - cannot import canonical configuration: {e}')

    def test_business_continuity_preserved_FINAL(self):
        """FINAL: Business continuity preserved after migration"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            config = UnifiedConfigManager()
            business_continuity_checks = {'configuration_available': config is not None, 'methods_accessible': len([m for m in dir(config) if not m.startswith('_')]) >= 5, 'instantiation_reliable': True, 'interface_complete': True}
            try:
                config_methods = [m for m in dir(config) if not m.startswith('_') and callable(getattr(config, m))]
                method_execution_results = []
                for method_name in config_methods[:3]:
                    try:
                        method = getattr(config, method_name)
                        method()
                        method_execution_results.append(True)
                    except Exception:
                        method_execution_results.append(False)
                interface_completeness = sum(method_execution_results) >= len(method_execution_results) * 0.7
                business_continuity_checks['interface_complete'] = interface_completeness
            except Exception:
                business_continuity_checks['interface_complete'] = False
            continuity_score = sum(business_continuity_checks.values())
            assert continuity_score >= len(business_continuity_checks), f'BUSINESS CONTINUITY COMPROMISED: {business_continuity_checks}. Configuration migration has affected business operations.'
            print(f'✅ Business continuity preserved: {continuity_score}/{len(business_continuity_checks)} checks passed')
        except ImportError as e:
            pytest.fail(f'Business continuity test failed: {e}')

    def test_golden_path_configuration_support_FINAL(self):
        """FINAL: Configuration fully supports Golden Path requirements"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            config = UnifiedConfigManager()
            golden_path_requirements = ['authentication', 'websocket', 'database', 'cors', 'api']
            golden_path_support = {}
            config_methods = [m for m in dir(config) if not m.startswith('_')]
            for requirement in golden_path_requirements:
                related_methods = [m for m in config_methods if requirement in m.lower()]
                golden_path_support[requirement] = len(related_methods)
            total_support = sum(golden_path_support.values())
            requirements_covered = sum((1 for count in golden_path_support.values() if count > 0))
            sufficient_support = total_support >= 10 or requirements_covered >= 3
            assert sufficient_support, f'INSUFFICIENT GOLDEN PATH CONFIGURATION SUPPORT: {golden_path_support}. Configuration must support critical Golden Path requirements for $500K+ ARR.'
            print(f'✅ Golden Path configuration support adequate: {requirements_covered}/{len(golden_path_requirements)} requirements covered, {total_support} total related methods')
        except ImportError as e:
            pytest.fail(f'Golden Path configuration support test failed: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')