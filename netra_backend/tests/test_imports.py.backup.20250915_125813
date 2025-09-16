"""
Comprehensive Import Tests for Netra Backend

This module runs import tests for all critical modules to ensure
no import errors exist in the codebase.
"""

# Test framework import - using pytest fixtures instead

import sys
from pathlib import Path
from typing import List, Tuple
from shared.isolated_environment import IsolatedEnvironment

import pytest

# Add parent directory to path

from test_framework.import_tester import ImportResult, ImportTester

class TestImports:
    """Test class for module imports"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        # Get project root path (parent of netra_backend/)
        project_root = Path(__file__).parent.parent.parent
        self.tester = ImportTester(root_path=str(project_root), verbose=False)
        self.critical_errors = []
    
    def _assert_import_success(self, result: ImportResult):
        """Assert that an import was successful"""
        if not result.success:
            error_msg = f"""
Import Failed: {result.module_path}
Error Type: {result.error_type}
Error Message: {result.error_message}
Missing Dependencies: {', '.join(result.missing_dependencies) if result.missing_dependencies else 'None'}
"""
            if result.circular_imports:
                error_msg += f"Circular Import Path: {' -> '.join(result.circular_imports)}\n"
            
            pytest.fail(error_msg)
    
    def test_main_application_import(self):
        """Test main application can be imported"""
        result = self.tester.test_module('netra_backend.app.main')
        self._assert_import_success(result)
    
    def test_config_import(self):
        """Test configuration module can be imported"""
        result = self.tester.test_module('netra_backend.app.config')
        self._assert_import_success(result)
    
    def test_startup_module_import(self):
        """Test startup module can be imported"""
        result = self.tester.test_module('netra_backend.app.startup_module')
        self._assert_import_success(result)
    
    def test_database_modules(self):
        """Test all database modules can be imported"""
        db_modules = [
            'netra_backend.app.db.database_manager',
            'netra_backend.app.db.postgres_core',
            'netra_backend.app.db.clickhouse_init',
            'netra_backend.app.core.clickhouse_connection_manager',
        ]
        
        for module_path in db_modules:
            result = self.tester.test_module(module_path)
            self._assert_import_success(result)
    
    def test_core_services(self):
        """Test core service modules can be imported"""
        service_modules = [
            'netra_backend.app.services.agent_service',
            'netra_backend.app.services.websocket.message_handler',  # Fixed: use actual websocket module
            'netra_backend.app.services.thread_service',
            'netra_backend.app.services.corpus_service',
            'netra_backend.app.services.generation_service',
            'netra_backend.app.services.mcp_service',
            'netra_backend.app.services.security_service',
        ]
        
        for module_path in service_modules:
            result = self.tester.test_module(module_path)
            self._assert_import_success(result)
    
    def test_agent_modules(self):
        """Test agent modules can be imported"""
        agent_modules = [
            'netra_backend.app.agents.base_agent',
            'netra_backend.app.agents.supervisor_consolidated',
            'netra_backend.app.agents.triage_sub_agent.agent',
            'netra_backend.app.agents.corpus_admin.agent',
            'netra_backend.app.agents.data_sub_agent.agent',
            'netra_backend.app.agents.github_analyzer.agent',
            'netra_backend.app.agents.supply_researcher.agent',
        ]
        
        for module_path in agent_modules:
            result = self.tester.test_module(module_path)
            self._assert_import_success(result)
    
    def test_route_modules(self):
        """Test route modules can be imported"""
        route_modules = [
            'netra_backend.app.routes.health',
            'netra_backend.app.routes.agent_route',
            'netra_backend.app.routes.websocket_unified',
            'netra_backend.app.routes.threads_route',
            'netra_backend.app.routes.corpus',
            'netra_backend.app.routes.admin',
            'netra_backend.app.routes.config',
            'netra_backend.app.routes.generation',
            'netra_backend.app.routes.quality',
            'netra_backend.app.routes.supply',
            'netra_backend.app.routes.synthetic_data',
        ]
        
        for module_path in route_modules:
            result = self.tester.test_module(module_path)
            self._assert_import_success(result)
    
    def test_core_infrastructure(self):
        """Test core infrastructure modules"""
        core_modules = [
            'netra_backend.app.core.websocket_message_handler',  # Fixed: use actual websocket module
            'netra_backend.app.core.error_handlers',
            'netra_backend.app.core.configuration.base',
            'netra_backend.app.core.configuration.database',
            'netra_backend.app.core.configuration.unified_secrets',
            'netra_backend.app.core.agent_recovery',
            'netra_backend.app.core.health.checks',
            'netra_backend.app.core.resource_manager',
        ]
        
        for module_path in core_modules:
            result = self.tester.test_module(module_path)
            self._assert_import_success(result)
    
    def test_middleware_modules(self):
        """Test middleware modules can be imported"""
        middleware_modules = [
            'netra_backend.app.middleware.security_headers_factory',
        ]
        
        for module_path in middleware_modules:
            result = self.tester.test_module(module_path)
            self._assert_import_success(result)
    
    def test_no_circular_imports(self):
        """Test that there are no circular imports in critical modules"""
        # This test will detect circular imports automatically
        # through the ImportTester's circular import detection
        critical_modules = [
            'netra_backend.app.main',
            'netra_backend.app.config',
            'netra_backend.app.services.agent_service',
            'netra_backend.app.agents.supervisor_consolidated',
        ]
        
        for module_path in critical_modules:
            result = self.tester.test_module(module_path)
            if result.circular_imports:
                pytest.fail(f"Circular import detected in {module_path}: {' -> '.join(result.circular_imports)}")
    
    @pytest.mark.slow
    def test_all_app_modules(self):
        """Test all modules in the app package (comprehensive but slow)"""
        report = self.tester.test_package('netra_backend.app', recursive=True)
        
        if report.failed_imports > 0:
            # Construct detailed failure message
            failures = [r for r in report.results if not r.success]
            
            # Group by error type
            by_error_type = {}
            for failure in failures:
                error_type = failure.error_type or "Unknown"
                if error_type not in by_error_type:
                    by_error_type[error_type] = []
                by_error_type[error_type].append(failure)
            
            error_msg = f"\n{report.failed_imports} import failures detected:\n"
            for error_type, results in by_error_type.items():
                error_msg += f"\n{error_type} ({len(results)} modules):\n"
                for result in results[:3]:  # Show first 3 of each type
                    error_msg += f"  - {result.module_path}: {result.error_message}\n"
                if len(results) > 3:
                    error_msg += f"  ... and {len(results) - 3} more\n"
            
            pytest.fail(error_msg)

@pytest.mark.fast
class TestFastFailImports:
    """Fast-fail import tests for CI/CD"""
    
    def test_critical_imports_fast_fail(self):
        """Test most critical imports with fast-fail behavior"""
        tester = ImportTester(verbose=False)
        
        # These are the absolute minimum imports needed for the app to start
        critical_modules = [
            ('netra_backend.app.main', 'Main application entry point'),
            ('netra_backend.app.config', 'Configuration loading'),
            ('netra_backend.app.startup_module', 'Application startup'),
            ('netra_backend.app.db.database_manager', 'Database connectivity'),
        ]
        
        for module_path, description in critical_modules:
            result = tester.test_module(module_path)
            if not result.success:
                error_msg = f"""
CRITICAL IMPORT FAILURE - Application cannot start!

Module: {module_path}
Description: {description}
Error Type: {result.error_type}
Error: {result.error_message}

This is a critical failure that prevents the application from starting.
Please fix this import error immediately.

Troubleshooting steps:
1. Check if all dependencies are installed: pip install -r requirements.txt
2. Verify Python path includes the project root
3. Check for typos in import statements
4. Ensure the module file exists and has no syntax errors
"""
                if result.missing_dependencies:
                    error_msg += f"\nMissing Dependencies: {', '.join(result.missing_dependencies)}"
                    error_msg += "\nTry: pip install " + " ".join(result.missing_dependencies)
                
                pytest.fail(error_msg)

def test_import_performance():
    """Test that imports complete within reasonable time"""
    import time
    
    tester = ImportTester(verbose=False)
    
    slow_threshold = 2.0  # seconds
    very_slow_threshold = 5.0  # seconds
    
    modules_to_test = [
        'netra_backend.app.main',
        'netra_backend.app.config',
        'netra_backend.app.services.agent_service',
    ]
    
    slow_modules = []
    very_slow_modules = []
    
    for module_path in modules_to_test:
        start = time.time()
        result = tester.test_module(module_path)
        elapsed = time.time() - start
        
        if elapsed > very_slow_threshold:
            very_slow_modules.append((module_path, elapsed))
        elif elapsed > slow_threshold:
            slow_modules.append((module_path, elapsed))
    
    if very_slow_modules:
        warning = "\nVERY SLOW IMPORTS DETECTED:\n"
        for module, time_taken in very_slow_modules:
            warning += f"  - {module}: {time_taken:.2f}s (>{very_slow_threshold}s)\n"
        pytest.fail(warning + "\nThese modules take too long to import and may impact startup time.")
    
    if slow_modules:
        # Just warn about slow modules, don't fail
        warning = "\nSlow imports detected:\n"
        for module, time_taken in slow_modules:
            warning += f"  - {module}: {time_taken:.2f}s\n"
        print(warning)