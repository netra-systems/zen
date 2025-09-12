#!/usr/bin/env python3
"""
Integration test to validate Golden Path test collection works properly.

This test validates pytest collection works for Golden Path tests that depend
on UserExecutionContext imports from the affected files in issue #502.

Expected behavior: FAIL initially (collection blocked by syntax errors)
After fixes: PASS (collection succeeds)
"""

import os
import sys
import subprocess
import unittest
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestGoldenPathTestDiscovery(unittest.TestCase):
    """Test that Golden Path tests can be collected properly."""
    
    def setUp(self):
        """Set up test with Golden Path test directories and files."""
        self.project_root = project_root
        
        # Golden Path test directories and files
        self.golden_path_test_locations = [
            "tests/integration/golden_path",
            "tests/e2e/golden_path",
            "tests/mission_critical",
            # Specific files that might depend on UserExecutionContext
            "tests/integration/golden_path/test_agent_orchestration_execution_comprehensive.py",
            "tests/e2e/golden_path/test_complete_user_journey.py",
        ]
        
        # Files that are known to import from affected modules
        self.dependency_test_files = [
            "tests/integration/test_websocket_agent_events.py",
            "tests/integration/test_agent_execution_integration.py",
            "tests/e2e/test_complete_agent_workflow.py"
        ]
    
    def test_pytest_collection_golden_path_directories(self):
        """Test that pytest can collect Golden Path test directories."""
        collection_failures = []
        
        for test_location in self.golden_path_test_locations:
            full_path = self.project_root / test_location
            
            if not full_path.exists():
                # Not a failure if path doesn't exist
                continue
                
            try:
                # Run pytest collection only (no execution)
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    str(full_path), 
                    "--collect-only", 
                    "--quiet",
                    "--tb=short"
                ], capture_output=True, text=True, cwd=self.project_root, timeout=30)
                
                if result.returncode != 0:
                    collection_failures.append({
                        'location': test_location,
                        'returncode': result.returncode,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    })
                    
            except subprocess.TimeoutExpired:
                collection_failures.append({
                    'location': test_location,
                    'returncode': -1,
                    'stdout': '',
                    'stderr': 'Timeout during collection'
                })
            except Exception as e:
                collection_failures.append({
                    'location': test_location,
                    'returncode': -2,
                    'stdout': '',
                    'stderr': f'Exception during collection: {str(e)}'
                })
        
        if collection_failures:
            failure_msg = "Golden Path test collection failed:\n"
            for failure in collection_failures:
                failure_msg += f"\n  Location: {failure['location']}"
                failure_msg += f"\n  Return Code: {failure['returncode']}"
                if failure['stderr']:
                    failure_msg += f"\n  Error: {failure['stderr']}"
                if failure['stdout']:
                    failure_msg += f"\n  Output: {failure['stdout']}"
                failure_msg += "\n"
            
            self.fail(failure_msg)
    
    def test_unified_test_runner_golden_path_collection(self):
        """Test that unified test runner can collect Golden Path tests."""
        # Check if unified test runner exists
        unified_runner_path = self.project_root / "tests" / "unified_test_runner.py"
        
        if not unified_runner_path.exists():
            self.skipTest("Unified test runner not found")
        
        collection_failures = []
        
        try:
            # Use unified test runner for collection
            result = subprocess.run([
                sys.executable, str(unified_runner_path),
                "--collect-only",
                "--category", "integration",
                "--no-coverage",
                "--quiet"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=60)
            
            if result.returncode != 0:
                collection_failures.append({
                    'runner': 'unified_test_runner',
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                })
                
        except subprocess.TimeoutExpired:
            collection_failures.append({
                'runner': 'unified_test_runner',
                'returncode': -1,
                'stdout': '',
                'stderr': 'Timeout during unified runner collection'
            })
        except Exception as e:
            collection_failures.append({
                'runner': 'unified_test_runner',
                'returncode': -2,
                'stdout': '',
                'stderr': f'Exception during unified runner collection: {str(e)}'
            })
        
        if collection_failures:
            failure_msg = "Unified test runner collection failed:\n"
            for failure in collection_failures:
                failure_msg += f"\n  Runner: {failure['runner']}"
                failure_msg += f"\n  Return Code: {failure['returncode']}"
                if failure['stderr']:
                    failure_msg += f"\n  Error: {failure['stderr']}"
                failure_msg += "\n"
            
            self.fail(failure_msg)
    
    def test_specific_dependency_files_collection(self):
        """Test collection of specific files that depend on UserExecutionContext."""
        collection_failures = []
        
        for test_file in self.dependency_test_files:
            full_path = self.project_root / test_file
            
            if not full_path.exists():
                continue
                
            try:
                # Run pytest collection on specific file
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    str(full_path),
                    "--collect-only",
                    "--quiet",
                    "--tb=line"
                ], capture_output=True, text=True, cwd=self.project_root, timeout=30)
                
                if result.returncode != 0:
                    # Check if error is related to UserExecutionContext imports
                    error_output = result.stderr + result.stdout
                    if any(pattern in error_output.lower() for pattern in [
                        'userexecutioncontext', 'syntax error', 'import error'
                    ]):
                        collection_failures.append({
                            'file': test_file,
                            'returncode': result.returncode,
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'related_to_issue': True
                        })
                    else:
                        # Non-related collection failure
                        collection_failures.append({
                            'file': test_file,
                            'returncode': result.returncode,
                            'stdout': result.stdout,
                            'stderr': result.stderr,
                            'related_to_issue': False
                        })
                        
            except subprocess.TimeoutExpired:
                collection_failures.append({
                    'file': test_file,
                    'returncode': -1,
                    'stdout': '',
                    'stderr': 'Timeout during file collection',
                    'related_to_issue': False
                })
            except Exception as e:
                collection_failures.append({
                    'file': test_file,
                    'returncode': -2,
                    'stdout': '',
                    'stderr': f'Exception: {str(e)}',
                    'related_to_issue': False
                })
        
        # Only fail if we have issue-related collection failures
        issue_related_failures = [f for f in collection_failures if f.get('related_to_issue', False)]
        
        if issue_related_failures:
            failure_msg = "Test collection failed due to UserExecutionContext issues:\n"
            for failure in issue_related_failures:
                failure_msg += f"\n  File: {failure['file']}"
                failure_msg += f"\n  Return Code: {failure['returncode']}"
                if failure['stderr']:
                    failure_msg += f"\n  Error: {failure['stderr']}"
                failure_msg += "\n"
            
            self.fail(failure_msg)
        
        # Report non-issue-related failures as info but don't fail
        non_issue_failures = [f for f in collection_failures if not f.get('related_to_issue', True)]
        if non_issue_failures:
            print(f"\nInfo: {len(non_issue_failures)} test files had collection issues unrelated to issue #502")
    
    def test_import_chain_validation(self):
        """Test that import chains from affected files can be resolved."""
        import_chain_failures = []
        
        # Files from issue #502 that contain UserExecutionContext imports
        affected_modules = [
            "netra_backend.app.agents.supervisor.agent_execution_core",
            "netra_backend.app.agents.supervisor.workflow_orchestrator", 
            "netra_backend.app.agents.supervisor.user_execution_engine",
            "netra_backend.app.agents.supervisor.agent_routing",
            "netra_backend.app.websocket_core.connection_executor",
            "netra_backend.app.websocket_core.unified_manager"
        ]
        
        for module_name in affected_modules:
            try:
                # Test if we can at least attempt to import the module
                # This will fail if there are syntax errors
                import importlib
                importlib.import_module(module_name)
                
            except SyntaxError as e:
                import_chain_failures.append({
                    'module': module_name,
                    'error_type': 'SyntaxError',
                    'error': str(e),
                    'line': getattr(e, 'lineno', None)
                })
            except ImportError as e:
                # ImportError might be due to missing dependencies, which is different from syntax
                if 'syntax' in str(e).lower():
                    import_chain_failures.append({
                        'module': module_name,
                        'error_type': 'ImportError (syntax-related)',
                        'error': str(e),
                        'line': None
                    })
                # Otherwise, ignore ImportError as it might be due to missing dependencies
            except Exception as e:
                import_chain_failures.append({
                    'module': module_name,
                    'error_type': type(e).__name__,
                    'error': str(e),
                    'line': None
                })
        
        if import_chain_failures:
            failure_msg = "Import chain validation failed (syntax errors in affected modules):\n"
            for failure in import_chain_failures:
                failure_msg += f"\n  Module: {failure['module']}"
                failure_msg += f"\n  Error Type: {failure['error_type']}"
                failure_msg += f"\n  Error: {failure['error']}"
                if failure['line']:
                    failure_msg += f"\n  Line: {failure['line']}"
                failure_msg += "\n"
            
            self.fail(failure_msg)


if __name__ == '__main__':
    unittest.main(verbosity=2)