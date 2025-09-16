"""Test that all modules can be imported successfully.

This test suite validates that all Python modules in the codebase can be imported
without errors. This catches missing imports, circular dependencies, and syntax
errors that might not be caught by unit tests with heavy mocking.

This addresses the critical issue documented in SPEC/learnings/test_coverage_import_gap.xml
where import errors passed all tests but failed in production.
"""

import pytest
from pathlib import Path
import importlib.util
import sys
from typing import List, Tuple
from shared.isolated_environment import IsolatedEnvironment


def get_all_python_modules() -> List[Tuple[str, Path]]:
    """Find all Python modules in the netra_backend service.
    
    Returns:
        List of tuples containing (module_name, file_path)
    """
    modules = []
    
    # Get the base path for netra_backend
    base_path = Path(__file__).parent.parent  # netra_backend directory
    
    # Find all Python files
    for py_file in base_path.rglob('*.py'):
        # Skip test files, __pycache__, and migration files
        path_str = str(py_file)
        if any(skip in path_str for skip in [
            '__pycache__',
            '/tests/',
            '\\tests\\',
            '/migrations/',
            '\\migrations\\',
            'test_',
            '_test.py',
            'conftest.py',
            'setup.py'
        ]):
            continue
            
        # Convert file path to module name
        # Example: netra_backend/app/agents/base/agent.py -> netra_backend.app.agents.base.agent
        relative_path = py_file.relative_to(base_path.parent)
        module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
        module_name = '.'.join(module_parts)
        
        modules.append((module_name, py_file))
    
    return modules


@pytest.mark.import_validation
@pytest.mark.parametrize("module_name,file_path", get_all_python_modules())
def test_module_imports(module_name: str, file_path: Path):
    """Test that each module can be imported successfully.
    
    This test imports each module to verify:
    1. All import statements are valid
    2. No circular dependencies exist
    3. No syntax errors in module-level code
    4. All type annotations can be resolved
    
    Args:
        module_name: The fully qualified module name
        file_path: The path to the Python file
    """
    # Clear any cached imports to ensure fresh import
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    try:
        # Load the module using importlib
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            pytest.fail(f"Could not create module spec for {module_name}")
            
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules before execution to handle self-references
        sys.modules[module_name] = module
        
        # Execute the module (this is where import errors will occur)
        spec.loader.exec_module(module)
        
    except ImportError as e:
        pytest.fail(f"Import error in {module_name}: {e}")
    except SyntaxError as e:
        pytest.fail(f"Syntax error in {module_name}: {e}")
    except Exception as e:
        # Catch any other exceptions that might occur during import
        pytest.fail(f"Unexpected error importing {module_name}: {type(e).__name__}: {e}")
    finally:
        # Clean up sys.modules to avoid side effects
        if module_name in sys.modules:
            del sys.modules[module_name]


def test_critical_modules_have_required_imports():
    """Test that critical modules have their required imports.
    
    This test specifically checks for imports that were previously missing
    and caused production failures.
    """
    # Check TriageProcessor has ExecutionContext import
    from netra_backend.app.agents.triage.unified_triage_agent import processing
    
    # Verify the module has the ExecutionContext in its namespace
    assert hasattr(processing, 'ExecutionContext') or 'ExecutionContext' in dir(processing), \
        "TriageProcessor is missing ExecutionContext import"
    
    # Verify the class can be accessed (don't instantiate due to required dependencies)
    assert hasattr(processing, 'TriageProcessor'), "TriageProcessor class not found"
    assert processing.TriageProcessor is not None, "TriageProcessor class is None"


def test_no_duplicate_implementations():
    """Test that there are no duplicate implementations violating SSOT.
    
    This checks for common SSOT violations like multiple client implementations.
    """
    # Check for ClickHouse client duplicates (previously had 4 implementations)
    clickhouse_modules = []
    
    for module_name, _ in get_all_python_modules():
        if 'clickhouse' in module_name.lower() and 'client' in module_name.lower():
            if 'test' not in module_name:  # Skip test files
                clickhouse_modules.append(module_name)
    
    # There should only be one canonical ClickHouse client
    canonical = 'netra_backend.app.db.clickhouse'
    non_canonical = [m for m in clickhouse_modules if not m.startswith(canonical)]
    
    assert len(non_canonical) == 0, \
        f"Found non-canonical ClickHouse implementations: {non_canonical}. " \
        f"Use {canonical} instead."


if __name__ == "__main__":
    # Allow running directly for quick validation
    import sys
    
    print("Starting import validation for netra_backend...")
    modules = get_all_python_modules()
    print(f"Found {len(modules)} modules to validate")
    
    failures = []
    for module_name, file_path in modules:
        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            print(f"[OK] {module_name}")
        except Exception as e:
            print(f"[FAIL] {module_name}: {e}")
            failures.append((module_name, str(e)))
        finally:
            if module_name in sys.modules:
                del sys.modules[module_name]
    
    if failures:
        print(f"\n{len(failures)} modules failed to import:")
        for module, error in failures:
            print(f"  - {module}: {error}")
        sys.exit(1)
    else:
        print(f"\nAll {len(modules)} modules imported successfully!")
        sys.exit(0)