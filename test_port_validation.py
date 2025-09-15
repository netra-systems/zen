#!/usr/bin/env python3
"""Test script for Cloud Run PORT configuration validation"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from tests.integration.test_cloud_run_port_config import CloudRunPortConfigurationValidator

def main():
    validator = CloudRunPortConfigurationValidator()

    print("=== Cloud Run PORT Configuration Validation ===")
    print()

    # Test 1: Docker Compose Staging Validation
    print("1. Testing Docker Compose staging configuration...")
    staging_compose = Path('./docker/docker-compose.staging.yml')
    if staging_compose.exists():
        result = validator.validate_docker_compose_port_config(staging_compose)
        print(f"   Valid: {result['valid']}")
        print(f"   Services checked: {result['services_checked']}")
        print(f"   Total issues: {result['total_issues']}")
        print(f"   Critical issues: {result['critical_issues']}")

        if result['issues']:
            print("   Issues found:")
            for issue in result['issues']:
                print(f"   - {issue['service']}: {issue['severity']} - {issue['details']}")
        else:
            print("   No issues found!")
    else:
        print(f"   ERROR: File not found: {staging_compose}")

    print()

    # Test 2: Environment Files Port Conflicts
    print("2. Testing environment files for PORT conflicts...")
    conflict_analysis = validator.check_environment_port_conflicts()
    print(f"   Conflicts found: {conflict_analysis['conflicts_found']}")
    print(f"   Total conflicts: {conflict_analysis['total_conflicts']}")
    print(f"   Port definitions: {len(conflict_analysis['port_definitions'])}")

    if conflict_analysis['port_conflicts']:
        print("   Conflicts:")
        for conflict in conflict_analysis['port_conflicts']:
            print(f"   - {conflict['file']}:{conflict['line']} PORT={conflict['value']} ({conflict['issue']})")

    if conflict_analysis['port_definitions']:
        print("   Port definitions found:")
        for file, def_info in conflict_analysis['port_definitions'].items():
            print(f"   - {file}: PORT={def_info['value']} (line {def_info['line']})")

    print()
    print("=== Validation Complete ===")

if __name__ == '__main__':
    main()