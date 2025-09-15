#!/usr/bin/env python3
"""
SSOT Configuration Manager Import Fix Script - Issue #757
Systematically updates deprecated imports to canonical SSOT imports.
"""

import os
import re


def fix_file_imports(file_path):
    """Fix deprecated imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # The canonical SSOT import replacement
        canonical_import = """from netra_backend.app.core.configuration.base import (
    UnifiedConfigManager,
    get_config,
    get_config_value,
    set_config_value,
    validate_config_value,
    get_environment,
    is_production,
    is_development,
    is_testing,
    config_manager
)"""

        # Find and replace the deprecated import block
        pattern = r'from netra_backend\.app\.core\.managers\.unified_configuration_manager import \((.*?)\)'
        if re.search(pattern, content, re.DOTALL):
            new_content = re.sub(pattern, canonical_import, content, flags=re.DOTALL)

            # Write the updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No match in: {file_path}")
            return False

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Main execution."""
    # List of files with deprecated imports
    files_to_fix = [
        "tests/integration/configuration_ssot/test_configuration_consolidation_integration.py",
        "tests/compliance/configuration_ssot/test_configuration_manager_enforcement.py",
        "tests/unit/configuration_ssot/test_configuration_manager_duplication_detection.py",
        "tests/unit/config_ssot/test_config_manager_ssot_violations_issue_667.py",
        "tests/integration/config_ssot/test_config_system_consistency_integration_issue_667.py",
        "tests/unit/ssot_validation/test_config_environment_access_ssot.py",
        "tests/mission_critical/test_config_manager_ssot_violations.py",
        "tests/integration/core/managers/test_unified_state_manager_integration.py",
        "tests/integration/core/test_unified_id_manager_integration.py",
        "tests/e2e/test_unified_configuration_manager_gcp_staging_production_critical.py",
        "scripts/validate_unified_managers.py",
        "scripts/validate_unified_configuration_manager_test_suite.py",
        "netra_backend/tests/unit/test_service_dependencies_unit.py",
        "netra_backend/tests/unit/core/managers/test_unified_configuration_manager_comprehensive.py",
        "netra_backend/tests/unit/core/managers/test_unified_configuration_manager_complete_coverage.py",
        "netra_backend/tests/unit/core/managers/test_unified_configuration_manager_100_percent_coverage.py",
        "netra_backend/tests/integration/test_unified_configuration_manager_real_services_critical.py",
        "netra_backend/tests/integration/test_complete_ssot_workflow_integration.py",
        "tests/integration/configuration/test_staging_configuration_validation_failures.py",
        "tests/integration/configuration/test_redis_deprecation_validation.py",
        "netra_backend/tests/unit/core/managers/test_unified_configuration_manager_ssot_business_critical.py",
        "netra_backend/tests/unit/core/configuration/test_base_ssot_violation_remediation.py",
        "netra_backend/tests/integration/config_ssot/test_config_ssot_service_secret_validation.py",
        "netra_backend/tests/unit/test_configuration_management_core.py",
        "tests/integration/factory_ssot/test_factory_ssot_configuration_redundancy.py",
        "netra_backend/tests/unit/core/managers/test_unified_configuration_manager_real.py",
        "netra_backend/tests/unit/core/managers/test_unified_configuration_manager_fixed.py",
        "netra_backend/tests/integration/test_unified_configuration_manager_comprehensive.py",
        "netra_backend/tests/integration/test_isolated_environment_config_integration.py",
        "netra_backend/tests/integration/test_cross_service_config_validation_integration.py",
        "netra_backend/tests/integration/test_config_shared_components_comprehensive.py",
        "netra_backend/tests/integration/test_config_cascade_propagation.py",
        "netra_backend/tests/integration/test_configuration_management_integration.py",
        "test_framework/fixtures/configuration_test_fixtures.py",
        "tests/core/test_ssot_managers.py",
        "scripts/validate_unified_managers_simple.py"
    ]

    print(f"SSOT Configuration Import Fix - Found {len(files_to_fix)} files")

    fixed_count = 0
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_file_imports(file_path):
                fixed_count += 1
        else:
            print(f"File not found: {file_path}")

    print(f"\nCompleted: Fixed {fixed_count}/{len(files_to_fix)} files")


if __name__ == "__main__":
    main()