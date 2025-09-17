"""
Issue #839: importlib.metadata Migration Functional Equivalence Test

This test suite validates that importlib.metadata provides functional equivalence
to pkg_resources for our specific use cases, proving the migration path is viable.

Focus Areas:
- Version information retrieval equivalence
- Package discovery and iteration equivalence
- Error handling equivalence
- Performance comparison between old and new APIs

Business Impact: HIGH - Ensures migration maintains functionality
Priority: P1 - Validation of migration path viability

Test Strategy: These tests compare pkg_resources vs importlib.metadata behavior
to ensure functional equivalence before and after migration.
"""

import sys
import pytest
from typing import Dict, List, Optional, Set
import warnings


class ImportlibMetadataEquivalenceTests:
    """Test functional equivalence between pkg_resources and importlib.metadata."""

    def test_version_retrieval_equivalence(self):
        """Test that importlib.metadata.version() provides equivalent results to pkg_resources.get_distribution().version.

        This test should PASS to prove importlib.metadata is a viable replacement.
        """
        # Import both libraries
        try:
            import pkg_resources
        except ImportError:
            pytest.skip("pkg_resources not available")

        try:
            if sys.version_info >= (3, 8):
                import importlib.metadata as metadata
            else:
                import importlib_metadata as metadata
        except ImportError:
            pytest.skip("importlib.metadata not available")

        # Test with known packages that should be available
        test_packages = ["pytest", "setuptools"]

        # Add google-cloud-secret-manager if available (our specific case)
        try:
            pkg_resources.get_distribution("google-cloud-secret-manager")
            test_packages.append("google-cloud-secret-manager")
        except pkg_resources.DistributionNotFound:
            pass

        version_comparisons = {}

        for package_name in test_packages:
            pkg_resources_version = None
            importlib_version = None
            pkg_resources_error = None
            importlib_error = None

            # Test pkg_resources
            try:
                pkg_resources_version = pkg_resources.get_distribution(package_name).version
            except Exception as e:
                pkg_resources_error = str(e)

            # Test importlib.metadata
            try:
                importlib_version = metadata.version(package_name)
            except Exception as e:
                importlib_error = str(e)

            version_comparisons[package_name] = {
                'pkg_resources_version': pkg_resources_version,
                'importlib_version': importlib_version,
                'pkg_resources_error': pkg_resources_error,
                'importlib_error': importlib_error
            }

        # Analyze results
        equivalence_failures = []
        for package_name, comparison in version_comparisons.items():
            pkg_version = comparison['pkg_resources_version']
            imp_version = comparison['importlib_version']
            pkg_error = comparison['pkg_resources_error']
            imp_error = comparison['importlib_error']

            if pkg_error and imp_error:
                # Both failed - check if errors are equivalent
                if "not found" in pkg_error.lower() and "not found" in imp_error.lower():
                    # Both indicate package not found - this is equivalent
                    continue
                else:
                    equivalence_failures.append(
                        f"{package_name}: Different error types - "
                        f"pkg_resources: {pkg_error}, importlib: {imp_error}"
                    )
            elif pkg_error and not imp_error:
                equivalence_failures.append(
                    f"{package_name}: pkg_resources failed ({pkg_error}) but importlib succeeded ({imp_version})"
                )
            elif not pkg_error and imp_error:
                equivalence_failures.append(
                    f"{package_name}: pkg_resources succeeded ({pkg_version}) but importlib failed ({imp_error})"
                )
            elif pkg_version != imp_version:
                equivalence_failures.append(
                    f"{package_name}: Version mismatch - pkg_resources: {pkg_version}, importlib: {imp_version}"
                )

        if equivalence_failures:
            pytest.fail(
                f"Version retrieval equivalence failures:\n" +
                "\n".join(f"  - {failure}" for failure in equivalence_failures)
            )

        # Success case
        successful_comparisons = len([c for c in version_comparisons.values()
                                    if c['pkg_resources_version'] == c['importlib_version']])

        assert successful_comparisons > 0, f"No successful version comparisons found"
        print(f"Version retrieval equivalence confirmed for {successful_comparisons} packages")

    def test_package_iteration_equivalence(self):
        """Test that importlib.metadata.distributions() provides equivalent results to pkg_resources.working_set.

        This test should PASS to prove importlib.metadata is a viable replacement.
        """
        # Import both libraries
        try:
            import pkg_resources
        except ImportError:
            pytest.skip("pkg_resources not available")

        try:
            if sys.version_info >= (3, 8):
                import importlib.metadata as metadata
            else:
                import importlib_metadata as metadata
        except ImportError:
            pytest.skip("importlib.metadata not available")

        # Get packages from pkg_resources
        pkg_resources_packages = {}
        try:
            for pkg in pkg_resources.working_set:
                pkg_resources_packages[pkg.project_name.lower()] = {
                    'name': pkg.project_name,
                    'version': pkg.version,
                    'location': getattr(pkg, 'location', None)
                }
        except Exception as e:
            pytest.skip(f"pkg_resources.working_set failed: {e}")

        # Get packages from importlib.metadata
        importlib_packages = {}
        try:
            for dist in metadata.distributions():
                name = dist.metadata['Name']
                importlib_packages[name.lower()] = {
                    'name': name,
                    'version': dist.version,
                    'location': str(dist.locate_file('')) if hasattr(dist, 'locate_file') else None
                }
        except Exception as e:
            pytest.skip(f"importlib.metadata.distributions() failed: {e}")

        # Compare package sets
        pkg_resources_names = set(pkg_resources_packages.keys())
        importlib_names = set(importlib_packages.keys())

        # Allow some differences due to different discovery mechanisms
        only_in_pkg_resources = pkg_resources_names - importlib_names
        only_in_importlib = importlib_names - pkg_resources_names
        common_packages = pkg_resources_names & importlib_names

        # Check if we have reasonable overlap
        if len(common_packages) == 0:
            pytest.fail("No common packages found between pkg_resources and importlib.metadata")

        overlap_percentage = len(common_packages) / max(len(pkg_resources_names), len(importlib_names)) * 100

        if overlap_percentage < 70:  # Allow 30% difference due to discovery differences
            pytest.fail(
                f"Low package discovery overlap: {overlap_percentage:.1f}%\n"
                f"pkg_resources found: {len(pkg_resources_names)} packages\n"
                f"importlib.metadata found: {len(importlib_names)} packages\n"
                f"Common packages: {len(common_packages)}"
            )

        # Compare versions for common packages
        version_mismatches = []
        for name in list(common_packages)[:10]:  # Check first 10 common packages
            pkg_info = pkg_resources_packages[name]
            imp_info = importlib_packages[name]

            if pkg_info['version'] != imp_info['version']:
                version_mismatches.append(
                    f"{name}: pkg_resources={pkg_info['version']}, importlib={imp_info['version']}"
                )

        if version_mismatches:
            pytest.fail(
                f"Version mismatches in common packages:\n" +
                "\n".join(f"  - {mismatch}" for mismatch in version_mismatches)
            )

        print(f"Package iteration equivalence confirmed: {overlap_percentage:.1f}% overlap")
        print(f"Common packages tested: {len(common_packages)}")
        print(f"Packages only in pkg_resources: {len(only_in_pkg_resources)}")
        print(f"Packages only in importlib.metadata: {len(only_in_importlib)}")

    def test_error_handling_equivalence(self):
        """Test that error handling is equivalent between pkg_resources and importlib.metadata.

        This test should PASS to prove error handling is consistent.
        """
        # Import both libraries
        try:
            import pkg_resources
        except ImportError:
            pytest.skip("pkg_resources not available")

        try:
            if sys.version_info >= (3, 8):
                import importlib.metadata as metadata
            else:
                import importlib_metadata as metadata
        except ImportError:
            pytest.skip("importlib.metadata not available")

        # Test with non-existent package
        fake_package_name = "this-package-definitely-does-not-exist-12345"

        # Test pkg_resources error
        pkg_resources_error = None
        try:
            pkg_resources.get_distribution(fake_package_name)
        except Exception as e:
            pkg_resources_error = e

        # Test importlib.metadata error
        importlib_error = None
        try:
            metadata.version(fake_package_name)
        except Exception as e:
            importlib_error = e

        # Both should have errors
        if pkg_resources_error is None:
            pytest.fail("Expected pkg_resources to raise an error for non-existent package")

        if importlib_error is None:
            pytest.fail("Expected importlib.metadata to raise an error for non-existent package")

        # Check error types are reasonable
        expected_error_types = ["NotFound", "DistributionNotFound", "PackageNotFound"]

        pkg_error_type = type(pkg_resources_error).__name__
        imp_error_type = type(importlib_error).__name__

        pkg_error_reasonable = any(expected in pkg_error_type for expected in expected_error_types)
        imp_error_reasonable = any(expected in imp_error_type for expected in expected_error_types)

        if not pkg_error_reasonable:
            pytest.fail(f"pkg_resources error type unexpected: {pkg_error_type}")

        if not imp_error_reasonable:
            pytest.fail(f"importlib.metadata error type unexpected: {imp_error_type}")

        print(f"Error handling equivalence confirmed:")
        print(f"  pkg_resources: {pkg_error_type}")
        print(f"  importlib.metadata: {imp_error_type}")

    def test_specific_migration_cases(self):
        """Test specific migration cases used in our codebase.

        This test validates the exact usage patterns that need to be migrated.
        """
        # Import both libraries
        try:
            import pkg_resources
        except ImportError:
            pytest.skip("pkg_resources not available")

        try:
            if sys.version_info >= (3, 8):
                import importlib.metadata as metadata
            else:
                import importlib_metadata as metadata
        except ImportError:
            pytest.skip("importlib.metadata not available")

        # Test Case 1: Version retrieval (diagnose_secret_manager.py usage)
        test_package = None
        try:
            # Try with google-cloud-secret-manager first (our actual case)
            pkg_resources.get_distribution("google-cloud-secret-manager")
            test_package = "google-cloud-secret-manager"
        except pkg_resources.DistributionNotFound:
            # Fallback to pytest (should be available)
            test_package = "pytest"

        if test_package:
            # Old way: pkg_resources.get_distribution("package").version
            old_version = pkg_resources.get_distribution(test_package).version

            # New way: importlib.metadata.version("package")
            new_version = metadata.version(test_package)

            if old_version != new_version:
                pytest.fail(
                    f"Version retrieval migration case failed for {test_package}:\n"
                    f"  Old method: {old_version}\n"
                    f"  New method: {new_version}"
                )

        # Test Case 2: Package enumeration (test_pytest_environment_validation.py usage)
        # Old way: {pkg.project_name.lower(): pkg for pkg in pkg_resources.working_set}
        old_packages = {pkg.project_name.lower(): pkg for pkg in pkg_resources.working_set}

        # New way: {dist.metadata['Name'].lower(): dist for dist in importlib.metadata.distributions()}
        new_packages = {dist.metadata['Name'].lower(): dist for dist in metadata.distributions()}

        # Check that we can get similar data from both
        common_names = set(old_packages.keys()) & set(new_packages.keys())

        if len(common_names) < 5:  # Should have at least 5 common packages
            pytest.fail(
                f"Package enumeration migration case failed:\n"
                f"  Old method found: {len(old_packages)} packages\n"
                f"  New method found: {len(new_packages)} packages\n"
                f"  Common packages: {len(common_names)}"
            )

        # Test accessing package information for common packages
        test_name = list(common_names)[0]
        old_pkg = old_packages[test_name]
        new_pkg = new_packages[test_name]

        # Check that we can get equivalent information
        old_name = old_pkg.project_name
        new_name = new_pkg.metadata['Name']

        old_version = old_pkg.version
        new_version = new_pkg.version

        if old_version != new_version:
            pytest.fail(
                f"Package information migration case failed for {test_name}:\n"
                f"  Old version: {old_version}\n"
                f"  New version: {new_version}"
            )

        print(f"Specific migration cases validated:")
        print(f"  Version retrieval: {test_package} v{old_version}")
        print(f"  Package enumeration: {len(common_names)} common packages")

    def test_performance_comparison(self):
        """Compare performance between pkg_resources and importlib.metadata.

        This test documents performance characteristics but should PASS.
        """
        import time

        # Import both libraries
        try:
            import pkg_resources
        except ImportError:
            pytest.skip("pkg_resources not available")

        try:
            if sys.version_info >= (3, 8):
                import importlib.metadata as metadata
            else:
                import importlib_metadata as metadata
        except ImportError:
            pytest.skip("importlib.metadata not available")

        # Test version retrieval performance
        test_package = "pytest"  # Should be available

        # Time pkg_resources
        start_time = time.time()
        for _ in range(10):
            try:
                version = pkg_resources.get_distribution(test_package).version
            except:
                break
        pkg_resources_time = time.time() - start_time

        # Time importlib.metadata
        start_time = time.time()
        for _ in range(10):
            try:
                version = metadata.version(test_package)
            except:
                break
        importlib_time = time.time() - start_time

        # Test package enumeration performance
        start_time = time.time()
        old_packages = list(pkg_resources.working_set)
        pkg_resources_enum_time = time.time() - start_time

        start_time = time.time()
        new_packages = list(metadata.distributions())
        importlib_enum_time = time.time() - start_time

        print(f"Performance comparison:")
        print(f"  Version retrieval (10x):")
        print(f"    pkg_resources: {pkg_resources_time:.4f}s")
        print(f"    importlib.metadata: {importlib_time:.4f}s")
        print(f"  Package enumeration:")
        print(f"    pkg_resources: {pkg_resources_enum_time:.4f}s ({len(old_packages)} packages)")
        print(f"    importlib.metadata: {importlib_enum_time:.4f}s ({len(new_packages)} packages)")

        # Performance is informational - test should pass
        assert True, "Performance comparison completed"


class ImportlibMetadataCompatibilityTests:
    """Test compatibility and edge cases for importlib.metadata."""

    def test_python_version_compatibility(self):
        """Test that importlib.metadata works across Python versions.

        This test should PASS to confirm the migration target is compatible.
        """
        import sys

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        if sys.version_info >= (3, 8):
            # Built-in importlib.metadata
            try:
                import importlib.metadata as metadata
                print(f"Using built-in importlib.metadata on Python {python_version}")
            except ImportError:
                pytest.fail(f"Built-in importlib.metadata not available on Python {python_version}")
        else:
            # Backport importlib_metadata
            try:
                import importlib_metadata as metadata
                print(f"Using importlib_metadata backport on Python {python_version}")
            except ImportError:
                pytest.fail(
                    f"importlib_metadata backport not available on Python {python_version}. "
                    "Install with: pip install importlib-metadata"
                )

        # Test basic functionality
        try:
            version = metadata.version("pytest")
            distributions = list(metadata.distributions())
            print(f"Basic functionality confirmed: pytest v{version}, {len(distributions)} packages found")
        except Exception as e:
            pytest.fail(f"Basic importlib.metadata functionality failed: {e}")

    def test_migration_safety(self):
        """Test that migration can be done safely without breaking existing functionality.

        This test should PASS to confirm migration safety.
        """
        # This test validates that both libraries can coexist during migration
        try:
            import pkg_resources
        except ImportError:
            pytest.skip("pkg_resources not available")

        try:
            if sys.version_info >= (3, 8):
                import importlib.metadata as metadata
            else:
                import importlib_metadata as metadata
        except ImportError:
            pytest.skip("importlib.metadata not available")

        # Test that both can be used in the same process
        test_package = "pytest"

        try:
            old_version = pkg_resources.get_distribution(test_package).version
            new_version = metadata.version(test_package)

            if old_version != new_version:
                pytest.fail(f"Coexistence safety check failed: {old_version} != {new_version}")

            print(f"Migration safety confirmed: Both libraries can coexist and return consistent results")

        except Exception as e:
            pytest.fail(f"Migration safety test failed: {e}")