"""Test that all modules can be imported successfully for auth_service.

This test suite validates that all Python modules in the auth_service can be imported
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
    """Find all Python modules in the auth_service.
    
    Returns:
        List of tuples containing (module_name, file_path)
    """
    modules = []
    
    # Get the base path for auth_service
    base_path = Path(__file__).parent.parent  # auth_service directory
    
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
        # Example: auth_service/auth_core/routes/auth_routes.py -> auth_service.auth_core.routes.auth_routes
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


def test_auth_service_independence():
    """Test that auth_service doesn't import from netra_backend.
    
    This ensures service independence as documented in:
    - SPEC/learnings/oauth_service_independence_violation.xml
    - SPEC/independent_services.xml
    """
    violations = []
    
    for module_name, file_path in get_all_python_modules():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for imports from netra_backend
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Only check lines that start with 'from' or 'import' keywords
            stripped_line = line.strip()
            if stripped_line.startswith(('from netra_backend', 'import netra_backend')):
                violations.append(f"{file_path}:{i} - {line.strip()}")
    
    assert len(violations) == 0, \
        f"Auth service must not import from netra_backend (service independence violation):\n" + \
        "\n".join(violations)


def test_critical_auth_imports():
    """Test that critical auth modules have their required functionality."""
    # Check that auth routes has proper architecture components
    from auth_service.auth_core.routes import auth_routes
    
    # These should be available in the module (architecture components, not direct imports)
    critical_components = [
        'AuthService',  # For JWT and auth handling (architecture correct)
        'OAuthManager',  # For OAuth handling
        'router',  # For FastAPI routing
    ]
    
    for component in critical_components:
        assert component in dir(auth_routes) or hasattr(auth_routes, component), \
            f"auth_routes is missing critical component: {component}"
            
    # Verify JWT functionality is available through AuthService
    # This is the correct architecture - JWT should not be imported directly in routes
    assert hasattr(auth_routes, 'AuthService'), \
        "auth_routes must have AuthService for JWT functionality"


def test_jwt_secret_key_usage():
    """Test that auth service uses JWT_SECRET_KEY, not JWT_SECRET.
    
    As documented in SPEC/learnings/jwt_secret_standardization.xml
    """
    violations = []
    
    for module_name, file_path in get_all_python_modules():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for deprecated JWT_SECRET usage
        if 'JWT_SECRET' in content and 'JWT_SECRET_KEY' not in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'JWT_SECRET' in line and 'JWT_SECRET_KEY' not in line:
                    if not line.strip().startswith('#'):  # Skip comments
                        violations.append(f"{file_path}:{i} - {line.strip()}")
    
    assert len(violations) == 0, \
        f"Found usage of deprecated JWT_SECRET (should be JWT_SECRET_KEY):\n" + \
        "\n".join(violations)


if __name__ == "__main__":
    # Allow running directly for quick validation
    import sys
    
    print("Starting import validation for auth_service...")
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
    
    # Run independence check
    print("\nChecking service independence...")
    test_auth_service_independence()
    print("[OK] Auth service is independent")
    
    # Run JWT secret check
    print("\nChecking JWT_SECRET_KEY usage...")
    test_jwt_secret_key_usage()
    print("[OK] Using correct JWT_SECRET_KEY")
    
    if failures:
        print(f"\n{len(failures)} modules failed to import:")
        for module, error in failures:
            print(f"  - {module}: {error}")
        sys.exit(1)
    else:
        print(f"\nAll {len(modules)} modules imported successfully!")
        sys.exit(0)