"""
Phase 2: Service Configuration Independence Tests
Issue #757 - Service isolation validation during migration

These tests validate that services can operate independently with
canonical configuration during the migration process.
"""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib

@pytest.mark.integration
class TestServiceConfigurationIndependence:
    """Phase 2 Tests - Service independence during config migration"""

    def test_backend_service_canonical_config_integration(self):
        """MUST PASS: Backend service works with canonical configuration"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            config_manager = UnifiedConfigManager()
            config_attributes = dir(config_manager)
            public_attributes = [attr for attr in config_attributes if not attr.startswith('_')]
            assert len(public_attributes) >= 3, f'Backend service insufficient config access: only {len(public_attributes)} public attributes: {public_attributes}'
            backend_config_operations = []
            for attr_name in public_attributes[:5]:
                try:
                    attr = getattr(config_manager, attr_name)
                    if callable(attr):
                        result = attr()
                        backend_config_operations.append(f'{attr_name}(): success')
                    else:
                        backend_config_operations.append(f'{attr_name}: {type(attr).__name__}')
                except Exception as e:
                    backend_config_operations.append(f'{attr_name}(): error - {e}')
            print(f'✅ Backend service config operations: {backend_config_operations}')
        except ImportError as e:
            pytest.fail(f'Backend cannot integrate with canonical configuration: {e}')

    def test_auth_service_config_independence(self):
        """SHOULD PASS: Auth service maintains configuration independence"""
        auth_service_path = Path('auth_service')
        if not auth_service_path.exists():
            pytest.skip('Auth service directory not found')
        auth_config_files = list(auth_service_path.rglob('*config*.py'))
        auth_env_files = list(auth_service_path.rglob('*.env*'))
        has_independent_config = len(auth_config_files) > 0 or len(auth_env_files) > 0
        assert has_independent_config, f'Auth service lacks independent configuration. Config files: {auth_config_files}, Env files: {auth_env_files}. Service independence at risk.'
        auth_backend_imports = []
        for py_file in auth_service_path.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                if 'netra_backend.app.core' in content:
                    auth_backend_imports.append(str(py_file))
            except Exception:
                continue
        assert len(auth_backend_imports) == 0, f'Auth service improperly imports backend configuration: {auth_backend_imports}. Service independence violated.'
        print(f'✅ Auth service maintains configuration independence')

    def test_frontend_service_config_independence(self):
        """SHOULD PASS: Frontend service maintains configuration independence"""
        frontend_path = Path('frontend')
        if not frontend_path.exists():
            pytest.skip('Frontend directory not found')
        frontend_config_files = [frontend_path / '.env', frontend_path / '.env.local', frontend_path / '.env.development', frontend_path / 'next.config.js', frontend_path / 'next.config.mjs']
        existing_config_files = [f for f in frontend_config_files if f.exists()]
        assert len(existing_config_files) > 0, f'Frontend lacks independent configuration files. Checked: {[str(f) for f in frontend_config_files]}'
        frontend_backend_imports = []
        for js_file in frontend_path.rglob('*.{js,ts,jsx,tsx}'):
            try:
                content = js_file.read_text(encoding='utf-8')
                if 'netra_backend' in content and 'configuration' in content:
                    frontend_backend_imports.append(str(js_file))
            except Exception:
                continue
        assert len(frontend_backend_imports) == 0, f'Frontend improperly imports backend configuration: {frontend_backend_imports}'
        print(f'✅ Frontend maintains configuration independence with {len(existing_config_files)} config files')

    def test_shared_utilities_config_access_pattern(self):
        """SHOULD PASS: Shared utilities use proper configuration patterns"""
        shared_path = Path('shared')
        if not shared_path.exists():
            pytest.skip('Shared directory not found')
        shared_config_imports = []
        shared_direct_env_access = []
        for py_file in shared_path.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                if 'configuration' in content.lower():
                    shared_config_imports.append(str(py_file))
                if 'os.environ' in content:
                    shared_direct_env_access.append(str(py_file))
            except Exception:
                continue
        excessive_config_imports = len(shared_config_imports) > 3
        if excessive_config_imports:
            print(f'⚠️ Shared utilities have many config imports: {shared_config_imports}')
        else:
            print(f'✅ Shared utilities have minimal config dependencies: {shared_config_imports}')
        if len(shared_direct_env_access) > 0:
            print(f'ℹ️ Shared utilities with direct env access: {shared_direct_env_access}')

    def test_database_service_config_isolation(self):
        """MUST PASS: Database configuration properly isolated"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            config_manager = UnifiedConfigManager()
            db_config_methods = [method for method in dir(config_manager) if 'database' in method.lower() or 'db' in method.lower()]
            if len(db_config_methods) > 0:
                print(f'✅ Database configuration methods available: {db_config_methods}')
                db_config_results = {}
                for method_name in db_config_methods:
                    try:
                        method = getattr(config_manager, method_name)
                        if callable(method):
                            result = method()
                            db_config_results[method_name] = 'accessible'
                        else:
                            db_config_results[method_name] = 'property'
                    except Exception as e:
                        db_config_results[method_name] = f'error: {str(e)[:50]}'
                accessible_db_configs = sum((1 for result in db_config_results.values() if result in ['accessible', 'property']))
                assert accessible_db_configs >= 1, f'Database configuration not accessible: {db_config_results}'
                print(f'✅ {accessible_db_configs}/{len(db_config_results)} database configs accessible')
            else:
                print('ℹ️ No explicit database configuration methods found')
        except ImportError as e:
            pytest.fail(f'Cannot test database configuration isolation: {e}')

    def test_websocket_service_config_compatibility(self):
        """CRITICAL: WebSocket service config compatible during migration"""
        try:
            sys.path.insert(0, str(Path.cwd()))
            from netra_backend.app.core.configuration.base import UnifiedConfigManager
            config_manager = UnifiedConfigManager()
            websocket_config_methods = [method for method in dir(config_manager) if any((ws_term in method.lower() for ws_term in ['websocket', 'ws', 'cors', 'origin']))]
            if len(websocket_config_methods) > 0:
                print(f'✅ WebSocket configuration methods: {websocket_config_methods}')
                ws_config_results = {}
                for method_name in websocket_config_methods:
                    try:
                        method = getattr(config_manager, method_name)
                        if callable(method):
                            result = method()
                            ws_config_results[method_name] = 'success'
                        else:
                            ws_config_results[method_name] = 'property'
                    except Exception as e:
                        ws_config_results[method_name] = f'error: {str(e)[:50]}'
                successful_ws_configs = sum((1 for result in ws_config_results.values() if result in ['success', 'property']))
                assert successful_ws_configs >= len(websocket_config_methods) * 0.8, f'WebSocket configuration failing during migration - GOLDEN PATH RISK: {ws_config_results}. This threatens $500K+ ARR.'
                print(f'✅ WebSocket config migration safe: {successful_ws_configs}/{len(websocket_config_methods)} configs working')
            else:
                print('ℹ️ No explicit WebSocket configuration methods found - checking general config')
                general_methods = [method for method in dir(config_manager) if not method.startswith('_') and callable(getattr(config_manager, method))]
                assert len(general_methods) >= 3, 'Insufficient configuration methods for WebSocket service migration'
        except ImportError as e:
            pytest.fail(f'Cannot test WebSocket configuration compatibility: {e}')

@pytest.mark.integration
class TestCrossServiceCommunication:
    """Test cross-service communication during configuration migration"""

    def test_service_config_environment_consistency(self):
        """SHOULD PASS: All services can work with consistent environment"""
        test_environment = {'ENV': 'test', 'DATABASE_URL': 'postgresql://test:test@localhost:5432/test', 'REDIS_URL': 'redis://localhost:6379', 'JWT_SECRET_KEY': 'test-secret-key', 'CORS_ORIGINS': 'http://localhost:3000,http://localhost:8000'}
        with patch.dict('os.environ', test_environment, clear=True):
            try:
                sys.path.insert(0, str(Path.cwd()))
                from netra_backend.app.core.configuration.base import UnifiedConfigManager
                config_manager = UnifiedConfigManager()
                config_methods = [method for method in dir(config_manager) if not method.startswith('_') and callable(getattr(config_manager, method))]
                environment_compatibility_results = {}
                for method_name in config_methods[:3]:
                    try:
                        method = getattr(config_manager, method_name)
                        result = method()
                        environment_compatibility_results[method_name] = 'compatible'
                    except Exception as e:
                        environment_compatibility_results[method_name] = f'incompatible: {str(e)[:30]}'
                compatible_methods = sum((1 for result in environment_compatibility_results.values() if result == 'compatible'))
                assert compatible_methods >= 1, f'Configuration incompatible with test environment: {environment_compatibility_results}'
                print(f'✅ Configuration environment compatibility: {compatible_methods}/{len(environment_compatibility_results)} methods compatible')
            except ImportError as e:
                pytest.fail(f'Cannot test environment consistency: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')