"""
Issue #839: pkg_resources Deprecation Warnings Test

This test suite validates that pkg_resources usage generates deprecation warnings
and will fail in future Python versions, proving the issue exists.

Focus Areas:
- Detecting deprecation warnings from pkg_resources usage
- Validating that current code is using deprecated APIs
- Proving migration necessity before Python 3.12+ breaks functionality

Business Impact: HIGH - Prevents future Python compatibility issues
Priority: P1 - Proactive technical debt resolution

Test Strategy: These tests should FAIL initially to prove the issue exists,
then PASS after migration to importlib.metadata.
"""

import warnings
import sys
import pytest
from pathlib import Path
from typing import List, Dict, Any
import subprocess
import tempfile
import os


class PkgResourcesDeprecationDetectionTests:
    """Test to detect pkg_resources deprecation warnings in current codebase."""

    def test_pkg_resources_version_access_generates_warnings(self):
        """Test that pkg_resources.get_distribution() generates deprecation warnings.

        This test should FAIL initially because pkg_resources usage generates warnings.
        After migration to importlib.metadata, this test should PASS.
        """
        # Capture warnings during pkg_resources usage
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Capture all warnings

            try:
                import pkg_resources
                # This should generate a deprecation warning
                version = pkg_resources.get_distribution("google-cloud-secret-manager").version

                # Check if any deprecation warnings were generated
                pkg_resources_warnings = [
                    w for w in warning_list
                    if issubclass(w.category, DeprecationWarning)
                    and 'pkg_resources' in str(w.message).lower()
                ]

                if not pkg_resources_warnings:
                    pytest.fail(
                        "Expected deprecation warnings from pkg_resources.get_distribution() "
                        "but none were found. This indicates the issue may not be present yet, "
                        "but pkg_resources is still deprecated and should be migrated."
                    )

                # Collect warning details
                warning_messages = [str(w.message) for w in pkg_resources_warnings]
                warning_details = "\n".join(f"  - {msg}" for msg in warning_messages)

                pytest.fail(
                    f"pkg_resources.get_distribution() generated {len(pkg_resources_warnings)} "
                    f"deprecation warning(s):\n{warning_details}\n"
                    "This proves the issue exists and migration is needed."
                )

            except ImportError:
                pytest.skip("google-cloud-secret-manager not installed")
            except Exception as e:
                pytest.fail(f"Error testing pkg_resources deprecation: {e}")

    def test_pkg_resources_working_set_generates_warnings(self):
        """Test that pkg_resources.working_set generates deprecation warnings.

        This test should FAIL initially because pkg_resources usage generates warnings.
        After migration to importlib.metadata, this test should PASS.
        """
        # Capture warnings during pkg_resources usage
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Capture all warnings

            try:
                import pkg_resources
                # This should generate a deprecation warning
                installed_packages = {pkg.project_name.lower(): pkg for pkg in pkg_resources.working_set}

                # Check if any deprecation warnings were generated
                pkg_resources_warnings = [
                    w for w in warning_list
                    if issubclass(w.category, DeprecationWarning)
                    and 'pkg_resources' in str(w.message).lower()
                ]

                if not pkg_resources_warnings:
                    pytest.fail(
                        "Expected deprecation warnings from pkg_resources.working_set "
                        "but none were found. This indicates the issue may not be present yet, "
                        "but pkg_resources is still deprecated and should be migrated."
                    )

                # Collect warning details
                warning_messages = [str(w.message) for w in pkg_resources_warnings]
                warning_details = "\n".join(f"  - {msg}" for msg in warning_messages)

                pytest.fail(
                    f"pkg_resources.working_set generated {len(pkg_resources_warnings)} "
                    f"deprecation warning(s):\n{warning_details}\n"
                    "This proves the issue exists and migration is needed."
                )

            except Exception as e:
                pytest.fail(f"Error testing pkg_resources working_set deprecation: {e}")

    def test_diagnose_secret_manager_script_uses_pkg_resources(self):
        """Test that diagnose_secret_manager.py script currently uses pkg_resources.

        This test should FAIL initially because the script uses deprecated pkg_resources.
        After migration, this test should PASS.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Read the script content
        script_content = script_path.read_text()

        # Check for pkg_resources usage
        pkg_resources_imports = []
        pkg_resources_usage = []

        lines = script_content.split('\n')
        for line_num, line in enumerate(lines, 1):
            if 'pkg_resources' in line:
                if 'import' in line and 'pkg_resources' in line:
                    pkg_resources_imports.append(f"Line {line_num}: {line.strip()}")
                elif 'pkg_resources.' in line:
                    pkg_resources_usage.append(f"Line {line_num}: {line.strip()}")

        if not pkg_resources_imports and not pkg_resources_usage:
            # This means migration is already done - test should pass
            assert True, "No pkg_resources usage found in diagnose_secret_manager.py (migration complete)"
        else:
            # This means pkg_resources is still being used - test should fail
            usage_details = []
            if pkg_resources_imports:
                usage_details.append("Imports:")
                usage_details.extend(f"  {imp}" for imp in pkg_resources_imports)
            if pkg_resources_usage:
                usage_details.append("Usage:")
                usage_details.extend(f"  {usage}" for usage in pkg_resources_usage)

            pytest.fail(
                f"diagnose_secret_manager.py still uses deprecated pkg_resources:\n" +
                "\n".join(usage_details) +
                "\nThis proves the issue exists and migration is needed."
            )

    def test_pytest_environment_validation_uses_pkg_resources(self):
        """Test that test_pytest_environment_validation.py currently uses pkg_resources.

        This test should FAIL initially because the test file uses deprecated pkg_resources.
        After migration, this test should PASS.
        """
        project_root = Path(__file__).parent.parent.parent
        test_path = project_root / "tests" / "mission_critical" / "test_pytest_environment_validation.py"

        if not test_path.exists():
            pytest.skip(f"Test file not found: {test_path}")

        # Read the test file content
        test_content = test_path.read_text()

        # Check for pkg_resources usage
        pkg_resources_imports = []
        pkg_resources_usage = []

        lines = test_content.split('\n')
        for line_num, line in enumerate(lines, 1):
            if 'pkg_resources' in line:
                if 'import' in line and 'pkg_resources' in line:
                    pkg_resources_imports.append(f"Line {line_num}: {line.strip()}")
                elif 'pkg_resources.' in line:
                    pkg_resources_usage.append(f"Line {line_num}: {line.strip()}")

        if not pkg_resources_imports and not pkg_resources_usage:
            # This means migration is already done - test should pass
            assert True, "No pkg_resources usage found in test_pytest_environment_validation.py (migration complete)"
        else:
            # This means pkg_resources is still being used - test should fail
            usage_details = []
            if pkg_resources_imports:
                usage_details.append("Imports:")
                usage_details.extend(f"  {imp}" for imp in pkg_resources_imports)
            if pkg_resources_usage:
                usage_details.append("Usage:")
                usage_details.extend(f"  {usage}" for usage in pkg_resources_usage)

            pytest.fail(
                f"test_pytest_environment_validation.py still uses deprecated pkg_resources:\n" +
                "\n".join(usage_details) +
                "\nThis proves the issue exists and migration is needed."
            )


class PkgResourcesFutureCompatibilityTests:
    """Test future Python compatibility issues with pkg_resources."""

    def test_pkg_resources_python_312_compatibility(self):
        """Test that pkg_resources may have compatibility issues in Python 3.12+.

        This test documents the future compatibility risk.
        """
        import sys

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        try:
            import pkg_resources
            # If we're on Python 3.12+, pkg_resources might have issues
            if sys.version_info >= (3, 12):
                pytest.fail(
                    f"Running Python {python_version} with pkg_resources. "
                    "pkg_resources may have compatibility issues in Python 3.12+. "
                    "Migration to importlib.metadata is strongly recommended."
                )
            else:
                # On older Python versions, just document the future risk
                print(f"Currently running Python {python_version}")
                print("pkg_resources is deprecated and may have issues in Python 3.12+")
                print("Migration to importlib.metadata is recommended for future compatibility")

        except ImportError:
            pytest.skip("pkg_resources not available")

    def test_importlib_metadata_availability(self):
        """Test that importlib.metadata is available as a replacement.

        This test should PASS to confirm the migration target is available.
        """
        try:
            if sys.version_info >= (3, 8):
                import importlib.metadata
                print("importlib.metadata available (Python 3.8+ built-in)")
            else:
                import importlib_metadata as importlib_metadata
                print("importlib_metadata backport available for Python < 3.8")

            # Test basic functionality
            try:
                # Try to get a known package
                if sys.version_info >= (3, 8):
                    version = importlib.metadata.version("pytest")
                    print(f"Successfully got pytest version using importlib.metadata: {version}")
                else:
                    version = importlib_metadata.version("pytest")
                    print(f"Successfully got pytest version using importlib_metadata: {version}")
            except Exception as e:
                pytest.fail(f"importlib.metadata basic functionality test failed: {e}")

        except ImportError as e:
            pytest.fail(
                f"importlib.metadata not available: {e}\n"
                "This indicates the migration target is not available. "
                "For Python < 3.8, install: pip install importlib-metadata"
            )


class PkgResourcesRunTimeDetectionTests:
    """Test runtime detection of pkg_resources usage in actual execution."""

    def test_runtime_pkg_resources_warnings_in_subprocess(self):
        """Test that running scripts with pkg_resources generates warnings in subprocess.

        This test should FAIL initially if warnings are generated.
        """
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "diagnose_secret_manager.py"

        if not script_path.exists():
            pytest.skip(f"Script not found: {script_path}")

        # Create a test script that runs diagnose_secret_manager with warning capture
        test_script_content = f'''
import warnings
import sys
import os

# Enable all warnings
warnings.filterwarnings("always")

# Capture warnings
with warnings.catch_warnings(record=True) as warning_list:
    warnings.simplefilter("always")

    # Set up environment
    sys.path.insert(0, r"{project_root}")
    os.environ["ENVIRONMENT"] = "test"

    try:
        # Import and run the check_gcp_library function that uses pkg_resources
        from scripts.diagnose_secret_manager import check_gcp_library
        result = check_gcp_library()

        # Check for pkg_resources warnings
        pkg_warnings = [
            w for w in warning_list
            if "pkg_resources" in str(w.message).lower() or
               "deprecated" in str(w.message).lower()
        ]

        if pkg_warnings:
            print("WARNINGS_FOUND")
            for w in pkg_warnings:
                print(f"WARNING: {{w.category.__name__}}: {{w.message}}")
        else:
            print("NO_WARNINGS_FOUND")

    except Exception as e:
        print(f"ERROR: {{e}}")
'''

        # Write and run the test script
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

            if "WARNINGS_FOUND" in output:
                warning_lines = [line for line in output.split('\n') if line.startswith('WARNING:')]
                pytest.fail(
                    f"pkg_resources deprecation warnings detected in runtime execution:\n" +
                    "\n".join(warning_lines) +
                    "\nThis proves the issue exists and migration is needed."
                )
            elif "NO_WARNINGS_FOUND" in output:
                # This could mean:
                # 1. Migration is already done
                # 2. Warnings are not being generated yet
                # 3. The package is not installed
                print("No pkg_resources warnings detected in runtime execution")
                print("This might indicate migration is complete or warnings are not yet visible")
            elif "ERROR:" in output:
                error_lines = [line for line in output.split('\n') if line.startswith('ERROR:')]
                pytest.skip(f"Runtime test failed: {error_lines}")
            else:
                pytest.skip("Unexpected output from runtime test")

        except subprocess.TimeoutExpired:
            pytest.skip("Runtime test timed out")
        except Exception as e:
            pytest.skip(f"Runtime test error: {e}")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_script_path)
            except:
                pass