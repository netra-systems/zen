'''
'''
CRITICAL Test: Critical Service Imports Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability
- Value Impact: Prevents 100% of critical service startup failures from import errors
- Strategic/Revenue Impact: Tests can't protect revenue if they can't run - essential for test infrastructure

This test validates that ALL critical service imports work correctly before any tests can run.
If critical imports fail, the entire test suite becomes worthless.

Critical Test Coverage:
- Main Backend Service (app.main)
- Auth Service (auth_service.main)
- Frontend Dev Launcher (dev_launcher.launcher)
- Core Agent Services (app.agents.supervisor)
- WebSocket Manager (app.ws_manager)
- Auth Integration (app.auth_integration.auth)
- Database Connections (app.db.postgres, app.db.clickhouse)
- Service Dependencies validation
- Circular dependency detection for critical paths
- Clear error reporting for import failures

Performance Requirement: Must complete in < 10 seconds
'''
'''

import importlib
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment

import pytest


class CriticalImportsValidator:
    """Validates that all critical service imports work correctly"""

    def __init__(self):
        pass
        self.project_root = Path(__file__).parent.parent.parent
        self.failed_imports: Dict[str, Dict[str, Any]] = {}
        self.start_time = 0.0

    Define CRITICAL modules that must import successfully
        self.critical_modules = [ ]
    # Main Services
        "netra_backend.app.main,"
        "auth_service.main,"
        "dev_launcher.launcher,"

    # Core Agent Infrastructure
        "netra_backend.app.agents.supervisor_agent_modern,"
        "netra_backend.app.agents.base_agent,"

    # Auth Integration (Critical for all services)
        "netra_backend.app.auth_integration.auth,"
        "netra_backend.app.auth_integration.models,"
        "netra_backend.app.auth_integration.validators,"

    # Database Core (Essential for data operations)
        "netra_backend.app.db.postgres,"
        "netra_backend.app.db.postgres_core,"
        "netra_backend.app.db.clickhouse,"
        "netra_backend.app.db.base,"

    # Core Application Infrastructure
        "netra_backend.app.config,"
        "netra_backend.app.dependencies,"
        "netra_backend.app.startup_module,"

    # Service Layer (Business Logic Core)
        "netra_backend.app.services.agent_service,"
        "netra_backend.app.services.base,"
        "netra_backend.app.services.service_factory,"

    # Route Layer (API Interface)
        "netra_backend.app.routes.agent_route,"
        "netra_backend.app.routes.health,"
        "netra_backend.app.routes.users,"
        "netra_backend.app.routes.websocket,"

    # Core Types and Schemas
        "netra_backend.app.schemas.core_models,"
        "netra_backend.app.schemas.agent_models,"
        "netra_backend.app.schemas.auth_types,"
        "netra_backend.app.schemas.websocket_models,"

    # Critical Middleware
        "netra_backend.app.middleware.error_middleware,"
        "netra_backend.app.middleware.security_middleware,"
        "netra_backend.app.middleware.metrics_middleware,"

    # Core Utilities
        "netra_backend.app.core.app_factory,"
        "netra_backend.app.core.exceptions,"
        "netra_backend.app.core.error_handlers,"

    # Auth Service Core
        "auth_service.auth_core.config,"
        "auth_service.main,"

    # Dev Launcher Core
        "dev_launcher.config,"
        "dev_launcher.launcher,"
        "dev_launcher.process_manager,"
        "dev_launcher.health_monitor"
    

    # Dependencies that MUST be available
        self.required_dependencies = [ ]
        "fastapi,"
        "uvicorn,"
        "pydantic,"
        "sqlalchemy,"
        "asyncpg,"
        "psycopg2,"
        "redis,"
        "websockets,"
        "httpx,"
        "pytest,"
        "openai,"
        "anthropic,"
        "alembic,"
        "structlog"
    

    def validate_dependencies(self) -> Dict[str, Any]:
        """Validate all required dependencies are installed"""
        missing_deps = []
        dependency_errors = {}

        for dep in self.required_dependencies:
        try:
        importlib.import_module(dep)
        except ImportError as e:
        missing_deps.append(dep)
        dependency_errors[dep] = { }
        "error: str(e),"
        "type": "ImportError"
                

        return { }
        "missing_dependencies: missing_deps,"
        "dependency_errors: dependency_errors,"
        "all_dependencies_available: len(missing_deps) == 0"
                

    def attempt_critical_import(self, module_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Attempt to import a critical module with detailed error capture"""
        try:
        # Clear any existing module to ensure fresh import
        if module_name in sys.modules:
        del sys.modules[module_name]

            # Attempt the import
        importlib.import_module(module_name)
        return True, None, None

        except ImportError as e:
        return False, "ImportError", ""
        except SyntaxError as e:
        return False, "SyntaxError", ""
        except ModuleNotFoundError as e:
        return False, "ModuleNotFoundError, str(e)"
        except Exception as e:
        error_type = type(e).__name__
        return False, error_type, ""

    def validate_critical_imports(self) -> Dict[str, Any]:
        """Validate all critical imports work correctly"""
        self.start_time = time.time()

    # Step 1: Validate dependencies first
        dependency_results = self.validate_dependencies()

    # Step 2: Test critical module imports
        successful_imports = []

        for module_name in self.critical_modules:
        success, error_type, error_msg = self.attempt_critical_import(module_name)

        if success:
        successful_imports.append(module_name)
        else:
        self.failed_imports[module_name] = { }
        "error_type: error_type,"
        "error_message: error_msg,"
        "critical: True"
                

        elapsed_time = time.time() - self.start_time

        return { }
        "total_critical_modules: len(self.critical_modules),"
        "successful_imports: len(successful_imports),"
        "failed_imports: len(self.failed_imports),"
        "success_rate: (len(successful_imports) / len(self.critical_modules)) * 100,"
        "elapsed_time_seconds: round(elapsed_time, 2),"
        "dependency_validation: dependency_results,"
        "failed_import_details: self.failed_imports,"
        "successful_modules: successful_imports"
                

    def detect_circular_imports(self) -> List[str]:
        """Detect potential circular import issues in critical modules"""
        circular_issues = []

    Simple circular import detection by checking for common patterns
        for module_name in self.critical_modules:
        try:
            Try importing twice to catch circular import issues
        if module_name in sys.modules:
        del sys.modules[module_name]

        importlib.import_module(module_name)

                # Clear and try again
        if module_name in sys.modules:
        del sys.modules[module_name]

        importlib.import_module(module_name)

        except RecursionError:
        circular_issues.append("")
        except ImportError as e:
        if "circular" in str(e).lower() or "recursion in str(e).lower():"
        circular_issues.append("")

        return circular_issues


        @pytest.mark.e2e
class TestCriticalImportsValidation:
        """Critical imports validation test suite"""

        @pytest.fixture
    def validator(self):
        """Create critical imports validator"""
        return CriticalImportsValidator()

        @pytest.fixture
    def validation_results(self, validator):
        """Run critical imports validation"""
        pass
        return validator.validate_critical_imports()

        @pytest.mark.e2e
    def test_all_dependencies_available(self, validation_results):
        """Test that all required dependencies are installed and importable"""
        dependency_validation = validation_results["dependency_validation]"

        if not dependency_validation["all_dependencies_available]:"
        missing_deps = dependency_validation["missing_dependencies]"
        error_details = dependency_validation["dependency_errors]"

        failure_msg = ""
        failure_msg += "Install missing packages:"
        "
        "

        for dep in missing_deps:
        error_info = error_details.get(dep, {})
        failure_msg += ""

        pytest.fail(failure_msg)

        @pytest.mark.e2e
    def test_all_critical_modules_importable(self, validation_results):
        """Test that ALL critical modules can be imported without errors"""
        pass
        failed_imports = validation_results["failed_imports]"
        success_rate = validation_results["success_rate]"

        if failed_imports > 0:
        failure_report = ""
        failure_report += ""
        failure_report += "=" * 80 + "
        failure_report += "=" * 80 + "
        "
        "

        # Report each failure with detailed information
        for module_name, error_info in validation_results["failed_import_details].items():"
        failure_report += ""
        failure_report += ""
        failure_report += ""
        failure_report += "-" * 60 + "
        failure_report += "-" * 60 + "
        "
        "

        failure_report += "
        failure_report += "
        FIRE:  CRITICAL: These import failures will cause cascading test failures!
        "
        "
        failure_report += "Fix these imports before running any other tests."
        "
        "

        pytest.fail(failure_report)

        @pytest.mark.e2e
    def test_no_circular_dependencies(self, validator):
        """Test that critical modules have no circular import dependencies"""
        circular_issues = validator.detect_circular_imports()

        if circular_issues:
        failure_msg = "Circular import dependencies detected in critical modules:"
        "
        "
        for issue in circular_issues:
        failure_msg += ""
        failure_msg += "
        failure_msg += "
        Circular imports must be resolved to prevent runtime failures."
        Circular imports must be resolved to prevent runtime failures."

        pytest.fail(failure_msg)

        @pytest.mark.e2e
    def test_performance_requirement(self, validation_results):
        """Test that critical imports validation completes within 10 seconds"""
        pass
        elapsed_time = validation_results["elapsed_time_seconds]"
        max_time = 10.0

        if elapsed_time > max_time:
        pytest.fail( )
        ""
        f"Slow imports indicate dependency or configuration issues."
        

        @pytest.mark.e2e
    def test_100_percent_success_rate_required(self, validation_results):
        """Test that 100% of critical modules import successfully"""
        success_rate = validation_results["success_rate]"

        if success_rate < 100.0:
        failed_count = validation_results["failed_imports]"
        total_count = validation_results["total_critical_modules]"

        pytest.fail( )
        ""
        f"100% success rate required for critical service imports. "
        f"ANY critical import failure compromises entire system stability."
        

        @pytest.mark.e2e
    def test_critical_services_coverage(self, validation_results, validator):
        """Test that all essential service categories are covered"""
        pass
        successful_modules = validation_results["successful_modules]"

    Verify we have successful imports from each critical category
        required_categories = { }
        "main_services": ["netra_backend.app.main", "auth_service.main", "dev_launcher.launcher],"
        "agent_core": ["netra_backend.app.agents.supervisor_agent_modern", "netra_backend.app.agents.base_agent],"
        "auth": ["netra_backend.app.auth_integration.auth],"
        "database": ["netra_backend.app.db.postgres", "netra_backend.app.db.clickhouse],"
        "config": ["netra_backend.app.config]"
    

        missing_categories = []
        for category, required_modules in required_categories.items():
        if not any(module in successful_modules for module in required_modules):
        missing_categories.append("")

        if missing_categories:
        pytest.fail( )
        f"Missing critical service categories:"
        " +"
        "
        "
        ".join("" for cat in missing_categories)"
                    

        @pytest.mark.e2e
    def test_validation_summary_report(self, validation_results):
        """Generate comprehensive validation summary report"""
        print("")
         + =" * 26 + " CRITICAL IMPORTS VALIDATION  + =" * 26)"
        print("")
        print("")
        print("")
        print("")
        print("")

        dependency_validation = validation_results["dependency_validation]"
        if dependency_validation["all_dependencies_available]:"
        print("All required dependencies available)"
        else:
        missing_count = len(dependency_validation["missing_dependencies])"
        print("")

        if validation_results["failed_imports] == 0:"
        print("")
        ALL CRITICAL IMPORTS SUCCESSFUL - Test infrastructure ready!")"
        else:
        print("")

        print("= * 80)"

                    # This test always passes - it's for reporting only'
        assert True, "Critical imports validation report generated"


                    # Standalone function for direct execution
    def run_critical_imports_validation():
        """Run critical imports validation directly"""
        pass
        validator = CriticalImportsValidator()
        results = validator.validate_critical_imports()

        print("")
         + ="*80)"
        print("CRITICAL IMPORTS VALIDATION RESULTS)"
        print("=*80)"

        if results["failed_imports] == 0:"
        print("")
        print("")
        return True
        else:
        print("")
        print("")
        Failed modules:")"
        for module, error in results["failed_import_details].items():"
        print("")
        return False


        if __name__ == "__main__:"
        success = run_critical_imports_validation()
        sys.exit(0 if success else 1)
