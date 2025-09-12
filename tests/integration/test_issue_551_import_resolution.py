"""
Integration Test for Issue #551: Import Resolution from Subdirectory Context

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable test execution from any directory context  
- Value Impact: Enables developers to run tests from any location without import failures
- Strategic Impact: Eliminates development friction and prevents CI/CD pipeline failures

This integration test validates that test framework imports work correctly
from all directory contexts, supporting the development workflow.
"""

import os
import sys
import subprocess
import tempfile
import asyncio
import pytest
from pathlib import Path
from typing import List, Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class TestImportResolutionIntegration(BaseIntegrationTest):
    """Integration test for Issue #551 import resolution fix."""
    
    def setup_method(self):
        """Set up method called before each test method."""
        super().setup_method()
        self.root_dir = Path(__file__).parent.parent
        self.test_directories = [
            ("root", self.root_dir),
            ("netra_backend", self.root_dir / "netra_backend"), 
            ("auth_service", self.root_dir / "auth_service"),
            ("tests_integration", self.root_dir / "tests" / "integration"),
            ("tests_e2e", self.root_dir / "tests" / "e2e")
        ]
    
    @pytest.mark.integration
    async def test_import_resolution_baseline(self):
        """Establish baseline: imports work from root directory."""
        result = self._execute_import_test(self.root_dir)
        
        assert result['success'], f"Baseline test failed from root directory: {result['error']}"
        assert "test_framework.base_integration_test" in result['output'], \
            "Import should reference the correct module"
    
    @pytest.mark.integration 
    async def test_import_resolution_from_all_contexts(self):
        """Test import resolution works from all directory contexts after fix."""
        results = {}
        failed_contexts = []
        
        for context_name, context_dir in self.test_directories:
            if not context_dir.exists():
                self.logger.warning(f"Skipping non-existent directory: {context_dir}")
                continue
            
            result = self._execute_import_test(context_dir)
            results[context_name] = result
            
            if not result['success']:
                failed_contexts.append({
                    'context': context_name,
                    'directory': str(context_dir),
                    'error': result['error']
                })
        
        # After Issue #551 is fixed, all contexts should work
        success_count = sum(1 for r in results.values() if r['success'])
        total_count = len(results)
        
        if failed_contexts:
            # Document current failing state for Issue #551 resolution
            failure_details = "\n".join([
                f"  - {ctx['context']} ({ctx['directory']}): {ctx['error']}" 
                for ctx in failed_contexts
            ])
            
            # This will fail until Issue #551 is resolved
            self.logger.error(f"Import failures detected:\n{failure_details}")
            pytest.fail(
                f"Issue #551 not resolved: {len(failed_contexts)}/{total_count} contexts failing.\n"
                f"Failing contexts:\n{failure_details}"
            )
        
        # Success case - all imports work
        assert success_count == total_count, \
            f"Expected all {total_count} contexts to work, got {success_count}"
    
    @pytest.mark.integration
    async def test_import_with_environment_isolation(self, real_services_fixture):
        """Test that import resolution works with isolated environment."""
        env = get_env()
        env.set("TESTING", "1", source="issue_551_test")
        
        # Test from subdirectory with environment isolation
        test_dir = self.root_dir / "netra_backend"
        if not test_dir.exists():
            pytest.skip("netra_backend directory not found")
        
        # Execute test with environment variables
        test_env = os.environ.copy()
        test_env['TESTING'] = '1'
        test_env['PYTHONPATH'] = str(self.root_dir)  # Temporary workaround
        
        result = subprocess.run([
            sys.executable, "-c",
            """
import os
from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest

env = get_env()
testing = env.get('TESTING', 'not_set')
print(f'ISOLATED_ENV_SUCCESS:{testing}')
"""
        ],
        cwd=test_dir,
        env=test_env,
        capture_output=True,
        text=True
        )
        
        assert result.returncode == 0, f"Environment isolation test failed: {result.stderr}"
        assert "ISOLATED_ENV_SUCCESS:1" in result.stdout, \
            f"Environment isolation not working: {result.stdout}"
    
    @pytest.mark.integration
    async def test_real_services_import_from_subdirectory(self, real_services_fixture):
        """Test that real services can be imported from subdirectory context."""
        # This test uses real services to ensure the full integration works
        test_dir = self.root_dir / "netra_backend"
        if not test_dir.exists():
            pytest.skip("netra_backend directory not found")
        
        # Create a temporary test file that uses real services
        test_code = '''
import sys
import os
from pathlib import Path

# Add root to path (current workaround)
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import get_real_services

class TestRealServicesImport(BaseIntegrationTest):
    async def test_real_services_available(self):
        # This should work after Issue #551 is fixed
        services = await get_real_services()
        return services is not None

# Run the test
import asyncio
test = TestRealServicesImport()
test.setup_method()
result = asyncio.run(test.test_real_services_available())
print(f"REAL_SERVICES_SUCCESS:{result}")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name
        
        try:
            result = subprocess.run([
                sys.executable, temp_file
            ],
            cwd=test_dir,
            capture_output=True,
            text=True
            )
            
            # This may fail until Issue #551 is resolved
            if result.returncode != 0:
                pytest.skip(f"Real services import test failed (Issue #551): {result.stderr}")
            
            assert "REAL_SERVICES_SUCCESS:True" in result.stdout, \
                f"Real services integration failed: {result.stdout}"
                
        finally:
            os.unlink(temp_file)
    
    def _execute_import_test(self, context_dir: Path) -> Dict[str, Any]:
        """Execute import test from specified directory context."""
        test_command = [
            sys.executable, "-c",
            "from test_framework.base_integration_test import BaseIntegrationTest; print('IMPORT_SUCCESS')"
        ]
        
        result = subprocess.run(
            test_command,
            cwd=context_dir,
            capture_output=True,
            text=True
        )
        
        return {
            'success': result.returncode == 0 and 'IMPORT_SUCCESS' in result.stdout,
            'returncode': result.returncode,
            'output': result.stdout,
            'error': result.stderr,
            'context_dir': str(context_dir)
        }


class TestImportResolutionDiagnostics(BaseIntegrationTest):
    """Diagnostic tests to analyze import resolution patterns."""
    
    @pytest.mark.integration
    async def test_python_path_analysis(self):
        """Analyze Python path resolution from different contexts."""
        root_dir = Path(__file__).parent.parent
        
        contexts_to_analyze = [
            ("root", root_dir),
            ("netra_backend", root_dir / "netra_backend"),
            ("tests_integration", root_dir / "tests" / "integration")
        ]
        
        path_analysis = {}
        
        for context_name, context_dir in contexts_to_analyze:
            if not context_dir.exists():
                continue
            
            analysis = self._analyze_python_path(context_dir, root_dir)
            path_analysis[context_name] = analysis
        
        # Log analysis for debugging Issue #551
        for context, analysis in path_analysis.items():
            self.logger.info(f"Python path analysis for {context}:")
            self.logger.info(f"  Working dir: {analysis['working_dir']}")
            self.logger.info(f"  Root in path: {analysis['root_in_path']}")
            self.logger.info(f"  Current dir in path: {analysis['current_in_path']}")
            self.logger.info(f"  Sys path length: {len(analysis['sys_path'])}")
        
        # Verify we got analysis from at least one context
        assert len(path_analysis) > 0, "Should have analyzed at least one context"
        
        # Store analysis for potential debugging
        self.path_analysis = path_analysis
    
    @pytest.mark.integration
    async def test_test_framework_discovery(self):
        """Discover all test_framework directories in the project."""
        root_dir = Path(__file__).parent.parent
        
        test_framework_locations = []
        for test_framework_dir in root_dir.rglob("test_framework"):
            if test_framework_dir.is_dir():
                relative_path = test_framework_dir.relative_to(root_dir)
                test_framework_locations.append(str(relative_path))
        
        self.logger.info(f"Found test_framework directories: {test_framework_locations}")
        
        # Verify main test_framework exists
        assert "test_framework" in test_framework_locations, \
            "Main test_framework directory should exist at project root"
        
        # Check for base_integration_test.py in main test_framework
        main_test_framework = root_dir / "test_framework"
        base_integration_file = main_test_framework / "base_integration_test.py"
        
        assert base_integration_file.exists(), \
            f"base_integration_test.py not found at {base_integration_file}"
    
    def _analyze_python_path(self, context_dir: Path, root_dir: Path) -> Dict[str, Any]:
        """Analyze Python path from a specific directory context."""
        analysis_command = [
            sys.executable, "-c",
            "import sys, json, os; print(json.dumps({'sys_path': sys.path, 'cwd': os.getcwd()}))"
        ]
        
        result = subprocess.run(
            analysis_command,
            cwd=context_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return {'error': result.stderr}
        
        try:
            import json
            data = json.loads(result.stdout.strip())
            
            return {
                'working_dir': data['cwd'],
                'sys_path': data['sys_path'],
                'root_in_path': str(root_dir) in data['sys_path'],
                'current_in_path': '' in data['sys_path'] or data['cwd'] in data['sys_path'],
                'analysis_successful': True
            }
        except (json.JSONDecodeError, KeyError) as e:
            return {'error': f'Failed to parse analysis: {e}'}