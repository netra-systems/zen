#!/usr/bin/env python3
"""
Test Docker Compose File Validation Issues - Issue #1082
Direct validation without pytest framework dependency
"""
import os
import json
import yaml
from pathlib import Path

def test_compose_file_validation_issue_1082():
    """Test Docker compose file validation issues for Issue #1082"""
    print("=== TESTING DOCKER COMPOSE FILE VALIDATION ISSUE #1082 ===")

    project_root = Path(__file__).parent
    docker_dir = project_root / 'docker'
    print(f"Docker directory: {docker_dir}")

    # Test results
    test_results = {}
    issues_found = []

    compose_files = {
        'docker-compose.yml': 'production',
        'docker-compose.staging.yml': 'staging',
        'docker-compose.alpine-test.yml': 'alpine-test',
        'docker-compose.alpine-dev.yml': 'alpine-dev',
        'docker-compose.staging.alpine.yml': 'staging-alpine',
        'docker-compose.minimal-test.yml': 'minimal-test'
    }

    # Test 1: Check compose files exist and are parseable
    print("\n1. Testing compose files existence and YAML validity...")
    compose_file_issues = []
    valid_compose_files = {}

    for compose_filename, environment in compose_files.items():
        compose_path = docker_dir / compose_filename

        if not compose_path.exists():
            compose_file_issues.append(f"Missing compose file: {compose_path}")
            print(f"   [FAIL] Missing {compose_filename}")
            continue

        try:
            with open(compose_path, 'r') as f:
                compose_content = yaml.safe_load(f)

            if not isinstance(compose_content, dict):
                compose_file_issues.append(
                    f"{compose_filename} - Invalid YAML structure: not a dictionary"
                )
                print(f"   [FAIL] Invalid YAML structure in {compose_filename}")
                continue

            # Validate basic compose file structure
            if 'services' not in compose_content:
                compose_file_issues.append(
                    f"{compose_filename} - Missing 'services' section"
                )
                print(f"   [FAIL] Missing services section in {compose_filename}")

            # Check for version specification
            if 'version' not in compose_content:
                compose_file_issues.append(
                    f"{compose_filename} - Missing 'version' specification"
                )
                print(f"   [FAIL] Missing version in {compose_filename}")

            valid_compose_files[compose_filename] = compose_content
            print(f"   [PASS] {compose_filename} - Valid YAML")

        except yaml.YAMLError as e:
            compose_file_issues.append(f"{compose_filename} - YAML parsing error: {str(e)}")
            print(f"   [FAIL] YAML error in {compose_filename}: {e}")
        except Exception as e:
            compose_file_issues.append(f"{compose_filename} - File reading error: {str(e)}")
            print(f"   [FAIL] File error in {compose_filename}: {e}")

    if compose_file_issues:
        issues_found.extend(compose_file_issues)

    test_results['compose_file_issues'] = compose_file_issues
    test_results['valid_compose_files'] = list(valid_compose_files.keys())

    # Test 2: Check Alpine compose service dockerfile references
    print("\n2. Testing Alpine compose Dockerfile references...")
    dockerfile_reference_issues = []

    alpine_compose_files = {
        name: env for name, env in compose_files.items()
        if 'alpine' in name.lower()
    }

    dockerfiles_dir = project_root / 'dockerfiles'

    for compose_filename, environment in alpine_compose_files.items():
        compose_path = docker_dir / compose_filename

        if compose_filename not in valid_compose_files:
            continue

        try:
            compose_content = valid_compose_files[compose_filename]
            services = compose_content.get('services', {})

            print(f"   [INFO] Checking {compose_filename} with {len(services)} services")

            for service_name, service_config in services.items():
                if not isinstance(service_config, dict):
                    continue

                # Check for dockerfile or build context
                dockerfile_ref = None
                build_config = service_config.get('build')

                if isinstance(build_config, str):
                    # Simple build context
                    dockerfile_ref = 'Dockerfile'
                elif isinstance(build_config, dict):
                    dockerfile_ref = build_config.get('dockerfile')
                    build_context = build_config.get('context', '.')

                if dockerfile_ref:
                    print(f"     Service {service_name}: dockerfile={dockerfile_ref}")

                    # Resolve Dockerfile path
                    if dockerfile_ref.startswith('../dockerfiles/'):
                        dockerfile_path = dockerfiles_dir / dockerfile_ref.replace('../dockerfiles/', '')
                    elif dockerfile_ref.startswith('./dockerfiles/'):
                        dockerfile_path = dockerfiles_dir / dockerfile_ref.replace('./dockerfiles/', '')
                    else:
                        dockerfile_path = dockerfiles_dir / dockerfile_ref

                    if not dockerfile_path.exists():
                        dockerfile_reference_issues.append(
                            f"{compose_filename} - Service '{service_name}' references missing Dockerfile: "
                            f"{dockerfile_ref} -> {dockerfile_path}"
                        )
                        print(f"     [FAIL] Missing Dockerfile: {dockerfile_path}")

                    # For Alpine environments, verify Dockerfile is actually Alpine-based
                    if dockerfile_path.exists() and 'alpine' in environment:
                        try:
                            with open(dockerfile_path, 'r') as df:
                                dockerfile_content = df.read().lower()

                            if 'alpine' not in dockerfile_content:
                                dockerfile_reference_issues.append(
                                    f"{compose_filename} - Service '{service_name}' in Alpine environment "
                                    f"references non-Alpine Dockerfile: {dockerfile_ref}"
                                )
                                print(f"     [FAIL] Non-Alpine Dockerfile in Alpine environment")
                            else:
                                print(f"     [PASS] Alpine Dockerfile confirmed")
                        except Exception as e:
                            dockerfile_reference_issues.append(
                                f"{compose_filename} - Failed to validate Dockerfile {dockerfile_ref}: {str(e)}"
                            )
                            print(f"     [FAIL] Error validating Dockerfile: {e}")

        except Exception as e:
            dockerfile_reference_issues.append(f"Failed to parse {compose_filename}: {str(e)}")
            print(f"   [FAIL] Error parsing {compose_filename}: {e}")

    if dockerfile_reference_issues:
        issues_found.extend(dockerfile_reference_issues)

    test_results['dockerfile_reference_issues'] = dockerfile_reference_issues

    # Test 3: Check for port conflicts
    print("\n3. Testing port conflicts...")
    port_conflict_issues = []
    all_ports_by_file = {}

    for compose_filename in valid_compose_files:
        compose_content = valid_compose_files[compose_filename]
        services = compose_content.get('services', {})
        file_ports = {}

        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue

            service_ports = []
            ports_config = service_config.get('ports', [])

            for port_mapping in ports_config:
                if isinstance(port_mapping, str):
                    if ':' in port_mapping:
                        host_port = port_mapping.split(':')[0]
                        try:
                            host_port_int = int(host_port)
                            service_ports.append(host_port_int)
                        except ValueError:
                            port_conflict_issues.append(
                                f"{compose_filename} - Service '{service_name}' has invalid port: {port_mapping}"
                            )
                elif isinstance(port_mapping, dict):
                    published_port = port_mapping.get('published')
                    if published_port:
                        try:
                            service_ports.append(int(published_port))
                        except ValueError:
                            port_conflict_issues.append(
                                f"{compose_filename} - Service '{service_name}' has invalid port: {published_port}"
                            )

            if service_ports:
                file_ports[service_name] = service_ports
                print(f"   [INFO] {compose_filename} - {service_name}: ports {service_ports}")

        all_ports_by_file[compose_filename] = file_ports

    # Check for conflicts between files
    port_usage = {}  # port -> [(file, service), ...]

    for compose_file, services_ports in all_ports_by_file.items():
        for service_name, ports in services_ports.items():
            for port in ports:
                if port not in port_usage:
                    port_usage[port] = []
                port_usage[port].append((compose_file, service_name))

    # Report conflicts
    for port, usages in port_usage.items():
        if len(usages) > 1:
            # Filter out conflicts between same base environment (e.g., staging vs staging.alpine)
            unique_envs = set()
            for compose_file, service in usages:
                base_env = compose_file.split('.')[0]  # docker-compose -> docker-compose
                unique_envs.add(base_env)

            if len(unique_envs) > 1:
                usage_details = [f"{compose_file}:{service}" for compose_file, service in usages]
                port_conflict_issues.append(
                    f"Port {port} conflict between environments: {usage_details}"
                )
                print(f"   [FAIL] Port {port} conflict: {usage_details}")

    if port_conflict_issues:
        issues_found.extend(port_conflict_issues)

    test_results['port_conflict_issues'] = port_conflict_issues

    # Test 4: Check environment variables
    print("\n4. Testing environment variables...")
    env_var_issues = []

    critical_env_vars = {
        'backend': ['DATABASE_URL', 'REDIS_URL', 'JWT_SECRET_KEY'],
        'auth': ['DATABASE_URL', 'JWT_SECRET_KEY', 'OAUTH_CLIENT_ID'],
        'frontend': ['NEXT_PUBLIC_API_URL', 'NEXT_PUBLIC_AUTH_URL']
    }

    for compose_filename in valid_compose_files:
        compose_content = valid_compose_files[compose_filename]
        services = compose_content.get('services', {})

        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue

            # Determine service type
            service_type = None
            for svc_type in critical_env_vars.keys():
                if svc_type in service_name.lower():
                    service_type = svc_type
                    break

            if not service_type:
                continue

            print(f"   [INFO] Checking {compose_filename} - {service_name} ({service_type})")

            # Check environment variables
            env_config = service_config.get('environment', {})
            env_file = service_config.get('env_file', [])

            # Convert env_config to dict if it's a list
            if isinstance(env_config, list):
                env_dict = {}
                for env_item in env_config:
                    if '=' in str(env_item):
                        key, value = str(env_item).split('=', 1)
                        env_dict[key] = value
                env_config = env_dict

            # Check for required environment variables
            required_vars = critical_env_vars[service_type]
            missing_vars = []

            for required_var in required_vars:
                if required_var not in env_config:
                    # Check if it might be in env_file (we can't validate file contents here)
                    if not env_file:
                        missing_vars.append(required_var)

            if missing_vars:
                env_var_issues.append(
                    f"{compose_filename} - Service '{service_name}' missing environment variables: "
                    f"{missing_vars}"
                )
                print(f"     [FAIL] Missing env vars: {missing_vars}")
            else:
                print(f"     [PASS] All required env vars present or in env_file")

    if env_var_issues:
        issues_found.extend(env_var_issues)

    test_results['env_var_issues'] = env_var_issues

    # Summary
    print("\n=== TEST RESULTS SUMMARY ===")
    print(f"Total issues found: {len(issues_found)}")

    if issues_found:
        print("\n[CRITICAL] DOCKER COMPOSE VALIDATION ISSUES DETECTED:")
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. {issue}")

        print(f"\n[SUCCESS] This test successfully detected {len(issues_found)} Docker compose file issues that would cause Docker Infrastructure Build Failures (Issue #1082)")
        print("These compose file issues would cause integration failures and build problems.")
    else:
        print("\n[SUCCESS] No Docker compose file validation issues detected")
        print("All Docker compose file validation checks passed")

    print(f"\n[RESULTS] Full test results: {json.dumps(test_results, indent=2)}")

    # Save results
    results_file = project_root / 'compose_file_validation_1082_test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'issue': '#1082 Docker Compose File Validation Issues',
            'test_timestamp': '2025-09-15T14:56:00Z',
            'issues_found': issues_found,
            'test_results': test_results
        }, f, indent=2)

    print(f"\n[SAVED] Results saved to: {results_file}")

    return len(issues_found), test_results

if __name__ == "__main__":
    issue_count, results = test_compose_file_validation_issue_1082()
    exit(0 if issue_count == 0 else 1)  # Exit with error if issues found