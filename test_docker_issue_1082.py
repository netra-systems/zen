#!/usr/bin/env python3
"""
Test Docker Infrastructure Build Failures - Issue #1082
Direct validation without pytest framework dependency
"""
import os
import json
from pathlib import Path

def test_docker_infrastructure_issue_1082():
    """Test Docker infrastructure issues for Issue #1082"""
    print("=== TESTING DOCKER INFRASTRUCTURE ISSUE #1082 ===")

    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")

    # Test results
    test_results = {}
    issues_found = []

    # Test 1: Check netra_backend directory
    print("\n1. Testing netra_backend source directory...")
    netra_backend_dir = project_root / 'netra_backend'

    if netra_backend_dir.exists():
        print(f"   [PASS] netra_backend directory exists: {netra_backend_dir}")
        test_results['netra_backend_exists'] = True

        if os.access(netra_backend_dir, os.R_OK):
            print(f"   [PASS] netra_backend directory is readable")
            test_results['netra_backend_readable'] = True
        else:
            print(f"   [FAIL] netra_backend directory is NOT readable")
            test_results['netra_backend_readable'] = False
            issues_found.append("netra_backend directory not readable - will cause Docker COPY failures")
    else:
        print(f"   [FAIL] netra_backend directory does NOT exist: {netra_backend_dir}")
        test_results['netra_backend_exists'] = False
        issues_found.append("netra_backend directory missing - will cause Docker COPY failures")

    # Test 2: Check Docker files
    print("\n2. Testing Docker files...")
    dockerfiles_dir = project_root / 'dockerfiles'
    docker_dir = project_root / 'docker'

    alpine_dockerfiles = [
        'backend.alpine.Dockerfile',
        'auth.alpine.Dockerfile',
        'frontend.alpine.Dockerfile',
        'backend.staging.alpine.Dockerfile',
        'auth.staging.alpine.Dockerfile',
        'frontend.staging.alpine.Dockerfile'
    ]

    found_dockerfiles = []
    missing_dockerfiles = []

    for dockerfile_name in alpine_dockerfiles:
        dockerfile_path = dockerfiles_dir / dockerfile_name
        if dockerfile_path.exists():
            found_dockerfiles.append(dockerfile_name)
            print(f"   [PASS] Found {dockerfile_name}")
        else:
            missing_dockerfiles.append(dockerfile_name)
            print(f"   [FAIL] Missing {dockerfile_name}")

    test_results['found_dockerfiles'] = found_dockerfiles
    test_results['missing_dockerfiles'] = missing_dockerfiles

    if missing_dockerfiles:
        issues_found.append(f"Missing Alpine Dockerfiles: {missing_dockerfiles}")

    # Test 3: Check COPY command sources in existing Dockerfiles
    print("\n3. Testing COPY command sources...")
    copy_issues = []

    for dockerfile_name in found_dockerfiles:
        dockerfile_path = dockerfiles_dir / dockerfile_name
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()

            copy_commands = []
            for i, line in enumerate(content.split('\n'), 1):
                if line.strip().startswith('COPY '):
                    copy_commands.append((i, line.strip()))

            print(f"   Found {len(copy_commands)} COPY commands in {dockerfile_name}")

            for line_num, copy_cmd in copy_commands:
                # Parse COPY command
                parts = copy_cmd.split()
                if len(parts) >= 3:
                    if parts[1].startswith('--'):
                        source = parts[2] if len(parts) > 2 else None
                    else:
                        source = parts[1]

                    if source and not source.startswith('/'):
                        # Relative path - check if exists
                        full_source_path = project_root / source
                        if not full_source_path.exists():
                            copy_issue = f"{dockerfile_name}:{line_num} - COPY source missing: {source}"
                            copy_issues.append(copy_issue)
                            print(f"   [FAIL] {copy_issue}")
                        else:
                            print(f"   [PASS] COPY source exists: {source}")

        except Exception as e:
            copy_issue = f"Failed to parse {dockerfile_name}: {str(e)}"
            copy_issues.append(copy_issue)
            print(f"   [FAIL] {copy_issue}")

    test_results['copy_issues'] = copy_issues
    if copy_issues:
        issues_found.extend(copy_issues)

    # Test 4: Check .dockerignore
    print("\n4. Testing .dockerignore files...")
    dockerignore_files = [
        docker_dir / '.dockerignore',
        dockerfiles_dir / '.dockerignore',
        project_root / '.dockerignore'
    ]

    existing_dockerignore = None
    for dockerignore_path in dockerignore_files:
        if dockerignore_path.exists():
            existing_dockerignore = dockerignore_path
            print(f"   [PASS] Found .dockerignore: {dockerignore_path}")
            break

    if not existing_dockerignore:
        print(f"   [FAIL] No .dockerignore file found")
        issues_found.append("No .dockerignore file - all files included in build context")
        test_results['dockerignore_exists'] = False
    else:
        test_results['dockerignore_exists'] = True
        test_results['dockerignore_path'] = str(existing_dockerignore)

    # Test 5: Check for problematic files
    print("\n5. Testing for problematic files...")
    problematic_files = []

    if netra_backend_dir.exists():
        # Look for __pycache__ directories
        pycache_dirs = list(netra_backend_dir.rglob('__pycache__'))
        if pycache_dirs:
            problematic_files.extend([str(p) for p in pycache_dirs[:3]])
            print(f"   [FAIL] Found {len(pycache_dirs)} __pycache__ directories")

        # Look for .pyc files
        pyc_files = list(netra_backend_dir.rglob('*.pyc'))
        if pyc_files:
            problematic_files.extend([str(p) for p in pyc_files[:3]])
            print(f"   [FAIL] Found {len(pyc_files)} .pyc files")

    test_results['problematic_files'] = problematic_files
    if problematic_files:
        issues_found.append(f"Found problematic files that can cause cache issues: {problematic_files}")

    # Summary
    print("\n=== TEST RESULTS SUMMARY ===")
    print(f"Total issues found: {len(issues_found)}")

    if issues_found:
        print("\n[CRITICAL] DOCKER INFRASTRUCTURE ISSUES DETECTED:")
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. {issue}")

        print(f"\n[SUCCESS] This test successfully detected {len(issues_found)} issues that would cause Docker Infrastructure Build Failures (Issue #1082)")
        print("These issues would cause cache key computation failures and COPY instruction problems in Alpine builds.")
    else:
        print("\n[SUCCESS] No Docker infrastructure issues detected")
        print("All Docker build context validation checks passed")

    print(f"\n[RESULTS] Full test results: {json.dumps(test_results, indent=2)}")

    # Save results
    results_file = project_root / 'docker_issue_1082_test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'issue': '#1082 Docker Infrastructure Build Failures',
            'test_timestamp': '2025-09-15T14:53:00Z',
            'issues_found': issues_found,
            'test_results': test_results
        }, f, indent=2)

    print(f"\n[SAVED] Results saved to: {results_file}")

    return len(issues_found), test_results

if __name__ == "__main__":
    issue_count, results = test_docker_infrastructure_issue_1082()
    exit(0 if issue_count == 0 else 1)  # Exit with error if issues found