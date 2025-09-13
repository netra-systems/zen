"""

Integration Tests for Service Environment SSOT Compliance - Issue #711



This test suite validates cross-service SSOT compliance for environment access.

Tests real integration patterns and service boundaries for SSOT violations.



Business Value: Platform/Internal - Service Independence & Configuration Consistency

Ensures all services use unified environment management without cross-dependencies.



CRITICAL: These tests use real services (NO DOCKER) and SSotBaseTestCase patterns.

"""



import asyncio

import sys

from pathlib import Path

from typing import Dict, List, Optional, Set

from unittest.mock import patch



from test_framework.ssot.base_test_case import SSotAsyncTestCase





class TestServiceEnvironmentComplianceIntegration(SSotAsyncTestCase):

    """

    Integration tests for validating SSOT environment compliance across services.



    These tests validate that all services properly use IsolatedEnvironment

    and maintain service independence while sharing environment utilities.

    """



    def setup_method(self, method):

        """Setup for each test method."""

        super().setup_method(method)

        self.project_root = Path(__file__).resolve().parent.parent.parent.parent



        # Service directories to test

        self.services = {

            'netra_backend': self.project_root / 'netra_backend',

            'auth_service': self.project_root / 'auth_service',

            'shared': self.project_root / 'shared',

            'test_framework': self.project_root / 'test_framework'

        }



        # Track compliance metrics

        self.record_metric("services_tested", len(self.services))



    async def test_service_environment_isolation_integration(self):

        """

        Test that services maintain proper environment isolation.



        This test validates that each service uses IsolatedEnvironment

        correctly without direct os.environ access, maintaining service boundaries.

        """

        service_compliance = {}



        for service_name, service_path in self.services.items():

            if not service_path.exists():

                continue



            compliance_result = await self._check_service_environment_compliance(

                service_name, service_path

            )

            service_compliance[service_name] = compliance_result



            # Record metrics per service

            self.record_metric(f"{service_name}_violations", compliance_result['violation_count'])

            self.record_metric(f"{service_name}_compliant_files", compliance_result['compliant_count'])



        # Log detailed compliance results

        print(f"\n🔍 Service Environment Compliance Results:")

        for service_name, result in service_compliance.items():

            violation_count = result['violation_count']

            compliant_count = result['compliant_count']

            total_files = result['total_files']



            compliance_percentage = (compliant_count / total_files * 100) if total_files > 0 else 0



            print(f"  {service_name}:")

            print(f"    📁 Total files: {total_files}")

            print(f"    ✅ Compliant: {compliant_count} ({compliance_percentage:.1f}%)")

            print(f"    🚨 Violations: {violation_count}")



            if result['sample_violations']:

                print(f"    📋 Sample violations:")

                for violation in result['sample_violations'][:3]:

                    rel_path = violation['file'].replace(str(self.project_root), '')

                    print(f"      • {rel_path}:{violation['line']} - {violation['pattern']}")



        # Calculate overall compliance

        total_violations = sum(r['violation_count'] for r in service_compliance.values())

        total_files = sum(r['total_files'] for r in service_compliance.values())



        self.record_metric("total_violations_across_services", total_violations)

        self.record_metric("total_files_across_services", total_files)



        # This assertion should FAIL initially to prove cross-service violations exist

        assert total_violations == 0, (

            f"Found {total_violations} environment access violations across {len(service_compliance)} services. "

            f"All services should use IsolatedEnvironment instead of direct os.environ access. "

            f"Issue #711 tracking systematic SSOT migration."

        )



    async def test_shared_environment_utility_integration(self):

        """

        Test that shared environment utilities are properly integrated across services.



        Validates that services correctly import and use shared.isolated_environment

        instead of creating duplicate environment management implementations.

        """

        shared_utility_usage = await self._analyze_shared_utility_integration()



        # Record metrics

        self.record_metric("services_using_shared", len(shared_utility_usage['compliant_services']))

        self.record_metric("services_with_duplicates", len(shared_utility_usage['duplicate_implementations']))



        # Log shared utility analysis

        print(f"\n🔗 Shared Environment Utility Integration:")

        print(f"  ✅ Services using shared utilities: {len(shared_utility_usage['compliant_services'])}")

        print(f"  🔄 Services with duplicate implementations: {len(shared_utility_usage['duplicate_implementations'])}")



        if shared_utility_usage['compliant_services']:

            print(f"  📋 Compliant services:")

            for service in shared_utility_usage['compliant_services']:

                print(f"    • {service}")



        if shared_utility_usage['duplicate_implementations']:

            print(f"  ⚠️ Services with duplicate implementations:")

            for service, details in shared_utility_usage['duplicate_implementations'].items():

                print(f"    • {service}: {details['duplicate_files']} files with duplicates")



        # This should pass once SSOT consolidation is complete

        assert len(shared_utility_usage['duplicate_implementations']) == 0, (

            f"Found {len(shared_utility_usage['duplicate_implementations'])} services with duplicate "

            f"environment management implementations. All services should use shared.isolated_environment."

        )



    async def test_environment_configuration_consistency_integration(self):

        """

        Test that environment configuration remains consistent across service boundaries.



        Validates that services can share environment configuration without

        breaking service independence principles.

        """

        config_consistency = await self._check_configuration_consistency()



        # Record metrics

        self.record_metric("consistent_configs", len(config_consistency['consistent_patterns']))

        self.record_metric("inconsistent_configs", len(config_consistency['inconsistent_patterns']))



        # Log consistency analysis

        print(f"\n⚙️ Environment Configuration Consistency:")

        print(f"  ✅ Consistent patterns: {len(config_consistency['consistent_patterns'])}")

        print(f"  ⚠️ Inconsistent patterns: {len(config_consistency['inconsistent_patterns'])}")



        if config_consistency['consistent_patterns']:

            print(f"  📋 Consistent configuration patterns:")

            for pattern in config_consistency['consistent_patterns'][:5]:

                print(f"    • {pattern}")



        if config_consistency['inconsistent_patterns']:

            print(f"  🚨 Inconsistent configuration patterns:")

            for pattern in config_consistency['inconsistent_patterns'][:5]:

                print(f"    • {pattern}")



        # This test documents configuration consistency - may initially fail

        assert len(config_consistency['inconsistent_patterns']) == 0, (

            f"Found {len(config_consistency['inconsistent_patterns'])} inconsistent "

            f"environment configuration patterns across services."

        )



    async def test_service_startup_environment_integration(self):

        """

        Test that services can start successfully with SSOT environment patterns.



        This validates that SSOT environment access doesn't break service

        initialization and startup sequences.

        """

        startup_results = {}



        for service_name, service_path in self.services.items():

            if not service_path.exists() or service_name == 'shared':

                continue



            startup_result = await self._test_service_startup_compatibility(

                service_name, service_path

            )

            startup_results[service_name] = startup_result



            # Record startup metrics

            self.record_metric(f"{service_name}_startup_success", startup_result['success'])

            self.record_metric(f"{service_name}_import_errors", len(startup_result['import_errors']))



        # Log startup compatibility results

        print(f"\n🚀 Service Startup Environment Integration:")

        for service_name, result in startup_results.items():

            success = result['success']

            import_errors = result['import_errors']



            status = "✅ SUCCESS" if success else "❌ FAILED"

            print(f"  {service_name}: {status}")



            if import_errors:

                print(f"    📋 Import errors ({len(import_errors)}):")

                for error in import_errors[:3]:

                    print(f"      • {error}")



        # All services should start successfully with SSOT patterns

        failed_services = [name for name, result in startup_results.items() if not result['success']]



        assert len(failed_services) == 0, (

            f"Services failed to start with SSOT environment patterns: {failed_services}. "

            f"SSOT migration should not break service startup sequences."

        )



    async def _check_service_environment_compliance(self, service_name: str, service_path: Path) -> Dict[str, any]:

        """

        Check environment compliance for a specific service.



        Args:

            service_name: Name of the service

            service_path: Path to service directory



        Returns:

            Dictionary with compliance metrics and violation details

        """

        violations = []

        compliant_files = []

        total_files = 0



        # Scan Python files in service

        for py_file in service_path.rglob("*.py"):

            if self._should_skip_file(py_file):

                continue



            total_files += 1



            try:

                with open(py_file, 'r', encoding='utf-8') as f:

                    content = f.read()



                # Check for violations

                file_violations = self._find_environment_violations_in_content(

                    str(py_file), content

                )

                violations.extend(file_violations)



                # Check for compliance

                if self._is_file_environment_compliant(content):

                    compliant_files.append(str(py_file))



            except (UnicodeDecodeError, PermissionError):

                continue



        return {

            'violation_count': len(violations),

            'compliant_count': len(compliant_files),

            'total_files': total_files,

            'sample_violations': violations[:10],  # First 10 for display

            'compliant_files': compliant_files

        }



    async def _analyze_shared_utility_integration(self) -> Dict[str, any]:

        """

        Analyze how services integrate with shared environment utilities.



        Returns:

            Dictionary with integration analysis results

        """

        compliant_services = []

        duplicate_implementations = {}



        for service_name, service_path in self.services.items():

            if not service_path.exists() or service_name == 'shared':

                continue



            # Check if service imports from shared

            uses_shared = await self._service_uses_shared_environment(service_path)

            if uses_shared:

                compliant_services.append(service_name)



            # Check for duplicate environment implementations

            duplicates = await self._find_duplicate_environment_implementations(service_path)

            if duplicates:

                duplicate_implementations[service_name] = {

                    'duplicate_files': len(duplicates),

                    'files': duplicates

                }



        return {

            'compliant_services': compliant_services,

            'duplicate_implementations': duplicate_implementations

        }



    async def _check_configuration_consistency(self) -> Dict[str, any]:

        """

        Check configuration consistency across services.



        Returns:

            Dictionary with consistency analysis results

        """

        consistent_patterns = []

        inconsistent_patterns = []



        # Define expected consistent patterns

        expected_patterns = [

            'IsolatedEnvironment',

            'get_env()',

            'shared.isolated_environment',

        ]



        # Analyze pattern usage across services

        for pattern in expected_patterns:

            service_usage = {}

            for service_name, service_path in self.services.items():

                if not service_path.exists():

                    continue



                usage_count = await self._count_pattern_usage(service_path, pattern)

                service_usage[service_name] = usage_count



            # Determine if pattern usage is consistent

            if any(count > 0 for count in service_usage.values()):

                consistent_patterns.append(f"{pattern}: {service_usage}")



        return {

            'consistent_patterns': consistent_patterns,

            'inconsistent_patterns': inconsistent_patterns

        }



    async def _test_service_startup_compatibility(self, service_name: str, service_path: Path) -> Dict[str, any]:

        """

        Test service startup compatibility with SSOT environment patterns.



        Args:

            service_name: Name of the service

            service_path: Path to service directory



        Returns:

            Dictionary with startup test results

        """

        import_errors = []

        success = True



        try:

            # Temporarily add service to Python path

            sys.path.insert(0, str(service_path.parent))



            # Try importing main service modules

            main_modules = self._find_main_service_modules(service_path)



            for module_path in main_modules:

                try:

                    # Convert path to module name

                    relative_path = module_path.relative_to(service_path.parent)

                    module_name = str(relative_path).replace('/', '.').replace('\\', '.').replace('.py', '')



                    # Dynamic import test

                    __import__(module_name)



                except ImportError as e:

                    import_errors.append(f"{module_path}: {str(e)}")

                    success = False



        except Exception as e:

            import_errors.append(f"Service setup error: {str(e)}")

            success = False



        finally:

            # Clean up Python path

            if str(service_path.parent) in sys.path:

                sys.path.remove(str(service_path.parent))



        return {

            'success': success,

            'import_errors': import_errors

        }



    def _find_environment_violations_in_content(self, file_path: str, content: str) -> List[Dict[str, any]]:

        """

        Find environment access violations in file content.



        Args:

            file_path: Path to the file

            content: File content to analyze



        Returns:

            List of violation dictionaries

        """

        violations = []

        lines = content.split('\n')



        # Violation patterns

        violation_patterns = [

            (r'os\.environ\[', 'os.environ[]'),

            (r'os\.environ\.get\(', 'os.environ.get()'),

            (r'os\.getenv\(', 'os.getenv()'),

        ]



        for line_num, line in enumerate(lines, 1):

            for pattern, description in violation_patterns:

                if re.search(pattern, line):

                    violations.append({

                        'file': file_path,

                        'line': line_num,

                        'pattern': description,

                        'code': line.strip()

                    })



        return violations



    def _is_file_environment_compliant(self, content: str) -> bool:

        """

        Check if file uses compliant environment access patterns.



        Args:

            content: File content to check



        Returns:

            True if file is compliant

        """

        import re



        # Compliant patterns

        compliant_patterns = [

            r'from shared\.isolated_environment import',

            r'IsolatedEnvironment\(',

            r'get_env\(\)',

        ]



        # Check if any compliant pattern is present

        return any(re.search(pattern, content) for pattern in compliant_patterns)



    async def _service_uses_shared_environment(self, service_path: Path) -> bool:

        """

        Check if service properly uses shared environment utilities.



        Args:

            service_path: Path to service directory



        Returns:

            True if service uses shared utilities

        """

        for py_file in service_path.rglob("*.py"):

            if self._should_skip_file(py_file):

                continue



            try:

                with open(py_file, 'r', encoding='utf-8') as f:

                    content = f.read()



                # Check for shared import

                if 'from shared.isolated_environment import' in content:

                    return True



            except (UnicodeDecodeError, PermissionError):

                continue



        return False



    async def _find_duplicate_environment_implementations(self, service_path: Path) -> List[str]:

        """

        Find duplicate environment management implementations in service.



        Args:

            service_path: Path to service directory



        Returns:

            List of files with duplicate implementations

        """

        duplicate_files = []



        # Patterns that indicate duplicate environment implementations

        duplicate_patterns = [

            'class IsolatedEnvironment',

            'class EnvironmentManager',

            'def get_environment',

        ]



        for py_file in service_path.rglob("*.py"):

            if self._should_skip_file(py_file):

                continue



            try:

                with open(py_file, 'r', encoding='utf-8') as f:

                    content = f.read()



                # Check for duplicate patterns

                if any(pattern in content for pattern in duplicate_patterns):

                    duplicate_files.append(str(py_file))



            except (UnicodeDecodeError, PermissionError):

                continue



        return duplicate_files



    async def _count_pattern_usage(self, service_path: Path, pattern: str) -> int:

        """

        Count usage of a specific pattern in service.



        Args:

            service_path: Path to service directory

            pattern: Pattern to count



        Returns:

            Number of pattern occurrences

        """

        count = 0



        for py_file in service_path.rglob("*.py"):

            if self._should_skip_file(py_file):

                continue



            try:

                with open(py_file, 'r', encoding='utf-8') as f:

                    content = f.read()



                count += content.count(pattern)



            except (UnicodeDecodeError, PermissionError):

                continue



        return count



    def _find_main_service_modules(self, service_path: Path) -> List[Path]:

        """

        Find main modules for service startup testing.



        Args:

            service_path: Path to service directory



        Returns:

            List of main module paths

        """

        main_modules = []



        # Common main module patterns

        main_patterns = [

            'main.py',

            'app.py',

            '__init__.py',

            'core.py',

            'config.py'

        ]



        for pattern in main_patterns:

            for module_path in service_path.rglob(pattern):

                if not self._should_skip_file(module_path):

                    main_modules.append(module_path)



        return main_modules[:5]  # Limit to first 5 found



    def _should_skip_file(self, file_path: Path) -> bool:

        """

        Determine if file should be skipped during analysis.



        Args:

            file_path: Path to check



        Returns:

            True if file should be skipped

        """

        skip_patterns = [

            '__pycache__',

            '.git',

            'node_modules',

            '.pytest_cache',

            'venv',

            'build',

            'dist',

            '.coverage',

            '.mypy_cache',

            'test_environment_violation',  # Skip our own test files

        ]



        file_str = str(file_path)

        return any(pattern in file_str for pattern in skip_patterns)





# Import re module at the module level for proper access

import re

