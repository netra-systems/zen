"""
Test Plan for Issue #502: UserExecutionContext Import Syntax Validation

Business Value Justification (BVJ):
- Segment: Platform Infrastructure  
- Business Goal: Ensure test infrastructure stability
- Value Impact: Prevent test collection failures that block development
- Strategic Impact: Core testing capability for golden path validation

CRITICAL: This test validates the syntax fix for Issue #502 where a broken import
statement in the golden path test file was preventing test collection.
"""

import ast
import subprocess
import sys
import pytest
from pathlib import Path
from typing import Any, Dict


class TestIssue502SyntaxValidation:
    """Test suite for Issue #502 syntax validation and import resolution."""
    
    def test_problematic_file_syntax_compiles(self):
        """
        Test that the problematic file compiles without syntax errors.
        
        ISSUE #502: Line 51 in test_service_dependency_golden_path_simple.py
        has a broken import statement that prevents Python compilation.
        """
        target_file = Path(__file__).parent.parent / "e2e/service_dependencies/test_service_dependency_golden_path_simple.py"
        
        # Verify the file exists
        assert target_file.exists(), f"Target file {target_file} does not exist"
        
        # Read file content
        with open(target_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Attempt to compile the file
        try:
            compiled = ast.parse(file_content, filename=str(target_file))
            assert compiled is not None, "File should compile to valid AST"
        except SyntaxError as e:
            pytest.fail(f"Syntax error in {target_file}:{e.lineno}: {e.msg}")
        except Exception as e:
            pytest.fail(f"Unexpected error parsing {target_file}: {e}")
    
    def test_user_execution_context_import_works(self):
        """
        Test that UserExecutionContext can be imported successfully.
        
        This validates that the import path is correct and the class is available.
        """
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Verify the class exists and has expected methods
            assert hasattr(UserExecutionContext, 'create_for_user'), \
                "UserExecutionContext should have create_for_user method"
            
        except ImportError as e:
            pytest.fail(f"Failed to import UserExecutionContext: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing UserExecutionContext: {e}")
    
    def test_service_dependencies_import_block(self):
        """
        Test that the service_dependencies import block works correctly.
        
        This validates that the multi-line import from service_dependencies
        works properly and doesn't conflict with the UserExecutionContext import.
        """
        try:
            from netra_backend.app.core.service_dependencies import (
                ServiceDependencyChecker,
                GoldenPathValidator,
                HealthCheckValidator,
                RetryMechanism,
                DependencyGraphResolver,
                ServiceType,
                EnvironmentType,
                DEFAULT_SERVICE_DEPENDENCIES
            )
            
            # Verify all components are available
            components = [
                ServiceDependencyChecker,
                GoldenPathValidator, 
                HealthCheckValidator,
                RetryMechanism,
                DependencyGraphResolver,
                ServiceType,
                EnvironmentType,
                DEFAULT_SERVICE_DEPENDENCIES
            ]
            
            for component in components:
                assert component is not None, \
                    f"Component {getattr(component, '__name__', str(component))} should be importable"
                
        except ImportError as e:
            pytest.fail(f"Failed to import service dependencies: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing service dependencies: {e}")
    
    def test_golden_path_test_file_collection(self):
        """
        Test that pytest can collect the golden path test file without errors.
        
        CRITICAL: This is the main issue - the syntax error was preventing
        pytest from collecting tests from the file.
        """
        target_file = "tests/e2e/service_dependencies/test_service_dependency_golden_path_simple.py"
        
        # Use pytest --collect-only to test collection without running
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--collect-only", "-q", target_file
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        # Check if collection succeeded
        if result.returncode != 0:
            pytest.fail(f"Test collection failed for {target_file}:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        
        # Verify that tests were actually collected
        stdout_content = result.stdout.lower()
        assert any(indicator in stdout_content for indicator in ["collected", "test session", "tests/"]), \
            f"No tests collected from {target_file}. Output: {result.stdout}"
    
    def test_user_execution_context_factory_method(self):
        """
        Test that UserExecutionContext.create_for_user works correctly.
        
        This validates that not only can we import the class, but we can
        actually use it as intended in the golden path tests.
        """
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Test the factory method with the same pattern used in the golden path test
            context = UserExecutionContext.create_for_user(
                user_id="test_user_502",
                thread_id="test_thread_502", 
                run_id="test_run_502"
            )
            
            # Verify context was created successfully
            assert context is not None, "UserExecutionContext should be created successfully"
            assert hasattr(context, 'user_id'), "Context should have user_id attribute"
            
        except ImportError as e:
            pytest.fail(f"Failed to import UserExecutionContext: {e}")
        except Exception as e:
            pytest.fail(f"UserExecutionContext.create_for_user failed: {e}")
    
    def test_combined_imports_as_in_fixed_file(self):
        """
        Test that both import statements work correctly when used together.
        
        This simulates the corrected import structure in the golden path file.
        """
        try:
            # Import UserExecutionContext separately (as it should be)
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Import the service dependencies in the multi-line block
            from netra_backend.app.core.service_dependencies import (
                ServiceDependencyChecker,
                GoldenPathValidator,
                HealthCheckValidator,
                ServiceType,
                EnvironmentType
            )
            
            # Verify both sets of imports work
            assert UserExecutionContext is not None
            assert ServiceDependencyChecker is not None
            assert GoldenPathValidator is not None
            
            # Test that we can use both together (as in the golden path test)
            context = UserExecutionContext.create_for_user(
                user_id="test_combined",
                thread_id="test_thread",
                run_id="test_run"
            )
            
            checker = ServiceDependencyChecker(environment=EnvironmentType.TESTING)
            validator = GoldenPathValidator()
            
            assert context is not None
            assert checker is not None
            assert validator is not None
            
        except Exception as e:
            pytest.fail(f"Combined imports and usage failed: {e}")
    
    def test_file_has_no_other_syntax_issues(self):
        """
        Test that fixing the import doesn't reveal other syntax issues.
        
        This is a regression prevention test to ensure the fix is complete.
        """
        target_file = Path(__file__).parent.parent / "e2e/service_dependencies/test_service_dependency_golden_path_simple.py"
        
        # Use py_compile to check for syntax errors
        import py_compile
        
        try:
            py_compile.compile(str(target_file), doraise=True)
        except py_compile.PyCompileError as e:
            pytest.fail(f"File has compilation errors: {e}")
        except SyntaxError as e:
            pytest.fail(f"File has syntax errors at line {e.lineno}: {e.msg}")


@pytest.mark.unit
class TestIssue502RegressionPrevention:
    """
    Additional tests to prevent regression of this type of issue.
    """
    
    def test_import_statement_patterns_in_test_files(self):
        """
        Test that similar import patterns in other test files are correct.
        
        This prevents the same type of syntax error from occurring elsewhere.
        """
        test_files = [
            "tests/e2e/service_dependencies/test_service_dependency_golden_path_simple.py"
        ]
        
        for test_file_path in test_files:
            target_file = Path(__file__).parent.parent.parent / test_file_path
            
            if not target_file.exists():
                continue  # Skip files that don't exist
            
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common problematic patterns
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Look for standalone import lines inside multi-line import blocks
                stripped = line.strip()
                if stripped.startswith('from ') and 'import' in stripped:
                    # Check if this line is inside a multi-line import
                    context_start = max(0, i-5)
                    context_end = min(len(lines), i+5)
                    context_lines = lines[context_start:context_end]
                    
                    # Look for opening parenthesis without closing on same line
                    for j, ctx_line in enumerate(context_lines):
                        if '(' in ctx_line and ')' not in ctx_line and 'import' in ctx_line:
                            # We found a multi-line import block
                            # The current line might be problematic if it's a complete import
                            if stripped.endswith(')') == False and ' (' not in stripped:
                                # This might be a standalone import inside a multi-line block
                                pytest.fail(f"Potential syntax issue in {test_file_path}:{i} - "
                                           f"standalone import line inside multi-line block: {stripped}")