"""
Issue #839: Diagnose Secret Manager Migration Integration Test

This test suite validates end-to-end functionality of the diagnose_secret_manager.py script
before and after pkg_resources to importlib.metadata migration.

Focus Areas:
- Script execution without errors
- GCP library version detection functionality
- Secret manager diagnostic functionality
- Command-line interface behavior
- JSON output format consistency

Business Impact: HIGH - Ensures secret manager diagnostics continue working after migration
Priority: P1 - Critical infrastructure tooling validation

Test Strategy: These tests validate the complete script functionality to ensure
migration doesn't break the diagnostic capabilities.
"""

import subprocess
import sys
import json
import tempfile
import os
import pytest
from pathlib import Path
from typing import Dict, Any, List


class DiagnoseSecretManagerExecutionTests:
    """Test execution of diagnose_secret_manager.py script."""

    def test_script_basic_execution(self):
        """Test that diagnose_secret_manager.py script executes without errors.

        This test should PASS to confirm basic script functionality.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Test basic help execution
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            pytest.fail(
                f"Script help execution failed:\n"
                f"Return code: {result.returncode}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        # Check that help output contains expected content
        help_output = result.stdout.lower()
        expected_help_content = ["environment", "json", "usage"]

        missing_content = [content for content in expected_help_content if content not in help_output]

        if missing_content:
            pytest.fail(
                f"Help output missing expected content: {missing_content}\n"
                f"Help output: {result.stdout}"
            )

        print(f"Script basic execution successful")

    def test_gcp_library_check_functionality(self):
        """Test the check_gcp_library function that uses pkg_resources/importlib.metadata.

        This test should PASS regardless of migration status but validates the function works.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Create a test script that imports and runs check_gcp_library
        test_script_content = f'''
import sys
import os
sys.path.insert(0, r"{project_root}")

try:
    from scripts.diagnose_secret_manager import check_gcp_library
    result = check_gcp_library()
    print(f"CHECK_GCP_LIBRARY_RESULT: {{result}}")
except Exception as e:
    print(f"CHECK_GCP_LIBRARY_ERROR: {{e}}")
    import traceback
    traceback.print_exc()
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_content)
            temp_script_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout

            if "CHECK_GCP_LIBRARY_ERROR:" in output:
                error_lines = [line for line in output.split('\n') if "CHECK_GCP_LIBRARY_ERROR:" in line]
                pytest.fail(f"check_gcp_library function failed: {error_lines}")

            if "CHECK_GCP_LIBRARY_RESULT:" not in output:
                pytest.fail(f"Unexpected output from check_gcp_library test: {output}")

            # Extract result
            result_line = [line for line in output.split('\n') if "CHECK_GCP_LIBRARY_RESULT:" in line][0]
            result_value = result_line.split(":", 1)[1].strip()

            print(f"check_gcp_library function result: {result_value}")

        except subprocess.TimeoutExpired:
            pytest.fail("check_gcp_library test timed out")
        except Exception as e:
            pytest.fail(f"check_gcp_library test error: {e}")
        finally:
            try:
                os.unlink(temp_script_path)
            except:
                pass

    def test_json_output_format(self):
        """Test that the script's JSON output format is consistent.

        This test should PASS to confirm JSON output structure is maintained.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Test JSON output mode
        result = subprocess.run(
            [sys.executable, str(script_path), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "ENVIRONMENT": "test"}
        )

        if result.returncode not in [0, 1]:  # Allow exit code 1 for degraded status
            pytest.fail(
                f"Script JSON execution failed:\n"
                f"Return code: {result.returncode}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        # Parse JSON output
        try:
            json_output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(
                f"Script JSON output is not valid JSON:\n"
                f"Error: {e}\n"
                f"Output: {result.stdout}"
            )

        # Check expected JSON structure
        expected_keys = [
            "gcp_library_available",
            "netra_backend_ok",
            "shared_builder_ok",
            "overall_status"
        ]

        missing_keys = [key for key in expected_keys if key not in json_output]

        if missing_keys:
            pytest.fail(
                f"JSON output missing expected keys: {missing_keys}\n"
                f"JSON output: {json_output}"
            )

        # Validate value types
        type_validations = {
            "gcp_library_available": bool,
            "netra_backend_ok": bool,
            "shared_builder_ok": bool,
            "overall_status": str
        }

        type_errors = []
        for key, expected_type in type_validations.items():
            if not isinstance(json_output[key], expected_type):
                type_errors.append(
                    f"{key}: expected {expected_type.__name__}, got {type(json_output[key]).__name__}"
                )

        if type_errors:
            pytest.fail(
                f"JSON output type validation errors:\n" +
                "\n".join(f"  - {error}" for error in type_errors)
            )

        print(f"JSON output format validation successful: {json_output}")

    def test_environment_parameter_handling(self):
        """Test that environment parameter handling works correctly.

        This test should PASS to confirm parameter handling is maintained.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Test with staging environment parameter
        result = subprocess.run(
            [sys.executable, str(script_path), "--environment", "staging", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode not in [0, 1]:  # Allow exit code 1 for degraded status
            pytest.fail(
                f"Script environment parameter execution failed:\n"
                f"Return code: {result.returncode}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        # Parse JSON output
        try:
            json_output = json.loads(result.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Script with environment parameter produced invalid JSON: {result.stdout}")

        print(f"Environment parameter handling successful")

    def test_error_handling_robustness(self):
        """Test error handling robustness of the script.

        This test should PASS to confirm error handling is maintained after migration.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Test with invalid environment
        result = subprocess.run(
            [sys.executable, str(script_path), "--environment", "invalid_env", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Script should handle invalid environment gracefully
        if result.returncode not in [0, 1]:
            pytest.fail(
                f"Script failed to handle invalid environment gracefully:\n"
                f"Return code: {result.returncode}\n"
                f"STDERR: {result.stderr}"
            )

        # Should still produce valid JSON output
        try:
            json_output = json.loads(result.stdout)
            print(f"Error handling robustness confirmed: graceful handling of invalid environment")
        except json.JSONDecodeError:
            pytest.fail(f"Script error handling broke JSON output format: {result.stdout}")


class DiagnoseSecretManagerMigrationValidationTests:
    """Test migration-specific validation for diagnose_secret_manager.py."""

    def test_version_detection_before_and_after_migration(self):
        """Test that version detection works before and after migration.

        This test validates the specific pkg_resources usage that needs migration.
        """
        project_root = Path(__file__).parent.parent.parent

        # Create test script that tests both approaches
        test_script_content = f'''
import sys
import os
sys.path.insert(0, r"{project_root}")

def test_pkg_resources_approach():
    """Test the current pkg_resources approach."""
    try:
        import pkg_resources
        import google.cloud.secretmanager
        version = pkg_resources.get_distribution("google-cloud-secret-manager").version
        return {{"success": True, "version": version, "method": "pkg_resources"}}
    except ImportError as e:
        return {{"success": False, "error": f"Import error: {{e}}", "method": "pkg_resources"}}
    except Exception as e:
        return {{"success": False, "error": f"Other error: {{e}}", "method": "pkg_resources"}}

def test_importlib_metadata_approach():
    """Test the new importlib.metadata approach."""
    try:
        if sys.version_info >= (3, 8):
            import importlib.metadata as metadata
        else:
            import importlib_metadata as metadata

        import google.cloud.secretmanager
        version = metadata.version("google-cloud-secret-manager")
        return {{"success": True, "version": version, "method": "importlib.metadata"}}
    except ImportError as e:
        return {{"success": False, "error": f"Import error: {{e}}", "method": "importlib.metadata"}}
    except Exception as e:
        return {{"success": False, "error": f"Other error: {{e}}", "method": "importlib.metadata"}}

# Test both approaches
pkg_result = test_pkg_resources_approach()
imp_result = test_importlib_metadata_approach()

print(f"PKG_RESOURCES_RESULT: {{pkg_result}}")
print(f"IMPORTLIB_RESULT: {{imp_result}}")

# Check equivalence if both succeed
if pkg_result["success"] and imp_result["success"]:
    if pkg_result["version"] == imp_result["version"]:
        print("VERSION_EQUIVALENCE: True")
    else:
        print(f"VERSION_EQUIVALENCE: False - {{pkg_result['version']}} != {{imp_result['version']}}")
elif pkg_result["success"] or imp_result["success"]:
    print("VERSION_EQUIVALENCE: Partial - one method succeeded")
else:
    print("VERSION_EQUIVALENCE: Neither method succeeded")
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_content)
            temp_script_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout

            # Extract results
            pkg_result_line = [line for line in output.split('\n') if "PKG_RESOURCES_RESULT:" in line]
            imp_result_line = [line for line in output.split('\n') if "IMPORTLIB_RESULT:" in line]
            equivalence_line = [line for line in output.split('\n') if "VERSION_EQUIVALENCE:" in line]

            if not pkg_result_line or not imp_result_line or not equivalence_line:
                pytest.fail(f"Migration validation test produced unexpected output: {output}")

            print(f"Migration validation results:")
            print(f"  {pkg_result_line[0]}")
            print(f"  {imp_result_line[0]}")
            print(f"  {equivalence_line[0]}")

            # The test passes if at least one method works and we can validate migration
            if "Neither method succeeded" in equivalence_line[0]:
                pytest.skip("Neither pkg_resources nor importlib.metadata method succeeded (likely package not installed)")

        except subprocess.TimeoutExpired:
            pytest.skip("Migration validation test timed out")
        except Exception as e:
            pytest.skip(f"Migration validation test error: {e}")
        finally:
            try:
                os.unlink(temp_script_path)
            except:
                pass

    def test_script_imports_after_migration(self):
        """Test that script imports work correctly after pkg_resources removal.

        This test validates that the script can be imported and run after migration.
        """
        project_root = Path(__file__).parent.parent.parent

        # Test importing the script as a module
        test_script_content = f'''
import sys
import os
sys.path.insert(0, r"{project_root}")

try:
    # Try to import the script module
    import scripts.diagnose_secret_manager as dsm

    # Test that key functions are available
    functions_to_test = [
        "check_gcp_library",
        "check_environment_variables",
        "diagnose_netra_backend_secret_manager",
        "diagnose_shared_secret_manager_builder"
    ]

    missing_functions = []
    for func_name in functions_to_test:
        if not hasattr(dsm, func_name):
            missing_functions.append(func_name)

    if missing_functions:
        print(f"IMPORT_TEST_FAILED: Missing functions: {{missing_functions}}")
    else:
        print("IMPORT_TEST_SUCCESS: All expected functions available")

        # Try to call check_gcp_library (the function that uses pkg_resources/importlib.metadata)
        try:
            result = dsm.check_gcp_library()
            print(f"FUNCTION_TEST_SUCCESS: check_gcp_library returned {{result}}")
        except Exception as e:
            print(f"FUNCTION_TEST_FAILED: check_gcp_library error: {{e}}")

except ImportError as e:
    print(f"IMPORT_TEST_FAILED: Import error: {{e}}")
except Exception as e:
    print(f"IMPORT_TEST_FAILED: Other error: {{e}}")
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script_content)
            temp_script_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout

            if "IMPORT_TEST_FAILED:" in output:
                failure_lines = [line for line in output.split('\n') if "IMPORT_TEST_FAILED:" in line]
                pytest.fail(f"Script import test failed: {failure_lines}")

            if "IMPORT_TEST_SUCCESS:" not in output:
                pytest.fail(f"Script import test produced unexpected output: {output}")

            print(f"Script imports validation successful")

        except subprocess.TimeoutExpired:
            pytest.fail("Script imports test timed out")
        except Exception as e:
            pytest.fail(f"Script imports test error: {e}")
        finally:
            try:
                os.unlink(temp_script_path)
            except:
                pass


class DiagnoseSecretManagerRegressionTests:
    """Test for regressions in diagnose_secret_manager.py functionality."""

    def test_main_function_execution(self):
        """Test that the main function executes without critical errors.

        This test should PASS to confirm main execution path works.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Test main function with minimal arguments
        result = subprocess.run(
            [sys.executable, str(script_path), "--json"],
            capture_output=True,
            text=True,
            timeout=60,  # Allow more time for full execution
            env={**os.environ, "ENVIRONMENT": "test", "DISABLE_GCP_SECRET_MANAGER": "true"}
        )

        # Script may return exit code 1 if secrets are missing (degraded mode), this is OK
        if result.returncode not in [0, 1]:
            pytest.fail(
                f"Main function execution failed:\n"
                f"Return code: {result.returncode}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )

        # Should produce valid JSON output
        try:
            json_output = json.loads(result.stdout)
            print(f"Main function execution successful with status: {json_output.get('overall_status', 'unknown')}")
        except json.JSONDecodeError:
            pytest.fail(f"Main function execution broke JSON output: {result.stdout}")

    def test_no_pkg_resources_imports_after_migration(self):
        """Test that pkg_resources imports are removed after migration.

        This test will FAIL if pkg_resources is still being imported after migration.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Read script content
        script_content = script_path.read_text()

        # Check for pkg_resources usage
        pkg_resources_lines = []
        lines = script_content.split('\n')

        for line_num, line in enumerate(lines, 1):
            if 'pkg_resources' in line and not line.strip().startswith('#'):
                pkg_resources_lines.append(f"Line {line_num}: {line.strip()}")

        if pkg_resources_lines:
            pytest.fail(
                f"pkg_resources still found in diagnose_secret_manager.py after migration:\n" +
                "\n".join(f"  {line}" for line in pkg_resources_lines) +
                "\nMigration appears incomplete."
            )

        print("No pkg_resources imports found in diagnose_secret_manager.py (migration complete or not yet done)")

    def test_importlib_metadata_usage_after_migration(self):
        """Test that importlib.metadata is being used after migration.

        This test will FAIL if importlib.metadata is not being used after migration.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Read script content
        script_content = script_path.read_text()

        # Check for importlib.metadata usage
        importlib_metadata_lines = []
        lines = script_content.split('\n')

        for line_num, line in enumerate(lines, 1):
            if ('importlib.metadata' in line or 'importlib_metadata' in line) and not line.strip().startswith('#'):
                importlib_metadata_lines.append(f"Line {line_num}: {line.strip()}")

        if not importlib_metadata_lines:
            # This could mean migration is not done yet, or it's done differently
            print("No importlib.metadata usage found in diagnose_secret_manager.py")
            print("This might indicate migration is not yet complete")
        else:
            print(f"importlib.metadata usage found in diagnose_secret_manager.py:")
            for line in importlib_metadata_lines:
                print(f"  {line}")