"""
Phase 1: Configuration Manager Duplication Crisis Detection Tests
Issue #757 - SSOT Violation Detection

These tests are DESIGNED TO FAIL to expose the P0 duplication crisis.
They validate that both deprecated and canonical configuration managers exist,
creating SSOT violations that must be resolved.
"""
import os
import sys
import inspect
from pathlib import Path
import pytest

class TestUnifiedConfigManagerDuplicationCrisis:
    """Phase 1 Tests - DESIGNED TO FAIL exposing duplication crisis"""

    def test_deprecated_manager_still_exists_SHOULD_FAIL(self):
        """CRITICAL P0: Test SHOULD FAIL - Deprecated manager file still exists"""
        deprecated_path = Path('netra_backend/app/core/managers/unified_configuration_manager.py')
        assert not deprecated_path.exists(), f'P0 SSOT VIOLATION: Deprecated configuration manager still exists at {deprecated_path}. This creates dangerous duplication with canonical SSOT at netra_backend/app/core/configuration/base.py'

    def test_file_size_indicates_massive_duplication_SHOULD_FAIL(self):
        """CRITICAL P0: Test SHOULD FAIL - Deprecated file is massive indicating duplication"""
        deprecated_path = Path('netra_backend/app/core/managers/unified_configuration_manager.py')
        canonical_path = Path('netra_backend/app/core/configuration/base.py')
        if not deprecated_path.exists():
            pytest.skip('Deprecated file already removed')
        deprecated_size = deprecated_path.stat().st_size
        canonical_size = canonical_path.stat().st_size
        assert deprecated_size < 1000, f'P0 SSOT VIOLATION: Deprecated manager is {deprecated_size} bytes vs canonical {canonical_size} bytes. Size indicates massive duplication that violates SSOT principles and creates maintenance nightmare.'

    def test_import_paths_create_confusion_SHOULD_FAIL(self):
        """CRITICAL P0: Test SHOULD FAIL - Multiple import paths create developer confusion"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigurationManager as DeprecatedManager
            deprecated_importable = True
        except ImportError:
            deprecated_importable = False
        try:
            from netra_backend.app.core.configuration.base import UnifiedConfigManager as CanonicalManager
            canonical_importable = True
        except ImportError:
            canonical_importable = False
        assert not (deprecated_importable and canonical_importable), f"P0 SSOT VIOLATION: Both deprecated and canonical configuration managers are importable, creating dangerous ambiguity. Developers don't know which to use, leading to inconsistent behavior and race conditions."

    def test_class_signature_duplication_SHOULD_FAIL(self):
        """CRITICAL P0: Test SHOULD FAIL - Classes have overlapping functionality"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigurationManager
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            deprecated_methods = set(dir(UnifiedConfigurationManager))
            canonical_methods = set(dir(UnifiedConfigManager))
            overlap = {m for m in deprecated_methods & canonical_methods if not m.startswith('_')}
            assert len(overlap) < 3, f'P0 SSOT VIOLATION: {len(overlap)} overlapping methods between deprecated and canonical managers: {sorted(overlap)}. This creates dangerous functional duplication violating SSOT principles.'
        except ImportError as e:
            pytest.skip(f'Import failed: {e}')

    def test_concurrent_instantiation_risk_SHOULD_FAIL(self):
        """CRITICAL P0: Test SHOULD FAIL - Both classes can be instantiated simultaneously"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigurationManager
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            deprecated_instance = None
            canonical_instance = None
            try:
                deprecated_instance = UnifiedConfigurationManager()
            except Exception:
                pass
            try:
                canonical_instance = UnifiedConfigManager()
            except Exception:
                pass
            both_instantiable = deprecated_instance is not None and canonical_instance is not None
            assert not both_instantiable, f'P0 SSOT VIOLATION: Both deprecated and canonical configuration managers can be instantiated simultaneously. This creates dangerous state inconsistency and race conditions in production.'
        except ImportError as e:
            pytest.skip(f'Import failed: {e}')

class TestCriticalBusinessImpactAnalysis:
    """Analyze the business-critical impact of this duplication crisis"""

    def test_golden_path_configuration_consistency_SHOULD_FAIL(self):
        """CRITICAL: Test SHOULD FAIL - Golden Path at risk from config inconsistency"""
        deprecated_exists = Path('netra_backend/app/core/managers/unified_configuration_manager.py').exists()
        canonical_exists = Path('netra_backend/app/core/configuration/base.py').exists()
        both_exist = deprecated_exists and canonical_exists
        assert not both_exist, f'CRITICAL BUSINESS RISK: Configuration duplication threatens Golden Path stability. $500K+ ARR at risk from inconsistent configuration state. Different services may use different config sources, causing race conditions in user authentication, WebSocket connections, and agent execution.'

    def test_production_deployment_risk_assessment_SHOULD_FAIL(self):
        """CRITICAL: Test SHOULD FAIL - Production deployment at risk"""
        deprecated_path = Path('netra_backend/app/core/managers/unified_configuration_manager.py')
        if not deprecated_path.exists():
            pytest.skip('Deprecated file already removed')
        try:
            with open(deprecated_path, 'r', encoding='utf-8') as f:
                content = f.read()
            production_keywords = ['DATABASE_URL', 'JWT_SECRET', 'REDIS_URL', 'GCP_PROJECT', 'staging', 'production']
            has_production_config = any((keyword in content for keyword in production_keywords))
            assert not has_production_config, f'CRITICAL DEPLOYMENT RISK: Deprecated configuration manager contains production-critical settings. Risk of deployment using wrong config source, causing service failures and customer impact.'
        except Exception as e:
            pytest.fail(f'Could not analyze deprecated file: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')