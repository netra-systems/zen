#!/usr/bin/env python3
"""
Test Docker Resource State Issues - Issue #1082
Direct validation without pytest framework dependency
"""
import os
import json
import shutil
import psutil
from pathlib import Path

def test_docker_resource_state_issue_1082():
    """Test Docker resource state issues for Issue #1082"""
    print("=== TESTING DOCKER RESOURCE STATE ISSUE #1082 ===")

    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")

    # Test results
    test_results = {}
    issues_found = []

    # Test 1: Check disk space
    print("\n1. Testing available disk space...")
    try:
        project_disk_usage = shutil.disk_usage(project_root)
        available_gb = project_disk_usage.free / (1024**3)
        total_gb = project_disk_usage.total / (1024**3)
        used_gb = project_disk_usage.used / (1024**3)

        min_required_gb = 5.0
        usage_percent = (used_gb / total_gb) * 100

        print(f"   Disk space: {available_gb:.2f}GB available, {total_gb:.2f}GB total, {usage_percent:.1f}% used")

        if available_gb < min_required_gb:
            issues_found.append(
                f"Insufficient disk space: {available_gb:.2f}GB available, {min_required_gb}GB required"
            )
            print(f"   [FAIL] Insufficient disk space")
        else:
            print(f"   [PASS] Sufficient disk space")

        if usage_percent > 90:
            issues_found.append(f"Disk usage critically high: {usage_percent:.1f}% full")
            print(f"   [FAIL] Disk usage critically high")

        test_results['disk_space'] = {
            'available_gb': available_gb,
            'total_gb': total_gb,
            'used_gb': used_gb,
            'usage_percent': usage_percent
        }

    except Exception as e:
        issues_found.append(f"Failed to check disk space: {str(e)}")
        print(f"   [FAIL] Error checking disk space: {e}")

    # Test 2: Check system memory
    print("\n2. Testing system memory...")
    try:
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        total_gb = memory.total / (1024**3)
        used_gb = memory.used / (1024**3)

        min_required_gb = 2.0
        usage_percent = memory.percent

        print(f"   Memory: {available_gb:.2f}GB available, {total_gb:.2f}GB total, {usage_percent:.1f}% used")

        if available_gb < min_required_gb:
            issues_found.append(
                f"Insufficient memory: {available_gb:.2f}GB available, {min_required_gb}GB required"
            )
            print(f"   [FAIL] Insufficient memory")
        else:
            print(f"   [PASS] Sufficient memory")

        if usage_percent > 90:
            issues_found.append(f"Memory usage critically high: {usage_percent:.1f}% used")
            print(f"   [FAIL] Memory usage critically high")

        test_results['memory'] = {
            'available_gb': available_gb,
            'total_gb': total_gb,
            'used_gb': used_gb,
            'usage_percent': usage_percent
        }

    except Exception as e:
        issues_found.append(f"Failed to check system memory: {str(e)}")
        print(f"   [FAIL] Error checking memory: {e}")

    # Test 3: Check swap usage
    print("\n3. Testing swap usage...")
    try:
        swap = psutil.swap_memory()
        if swap.total > 0:
            swap_percent = swap.percent
            swap_gb = swap.total / (1024**3)
            swap_used_gb = swap.used / (1024**3)

            print(f"   Swap: {swap_used_gb:.2f}GB used, {swap_gb:.2f}GB total, {swap_percent:.1f}% used")

            if swap_percent > 80:
                issues_found.append(f"Swap usage high: {swap_percent:.1f}% used")
                print(f"   [FAIL] Swap usage high")
            else:
                print(f"   [PASS] Swap usage normal")

            test_results['swap'] = {
                'total_gb': swap_gb,
                'used_gb': swap_used_gb,
                'usage_percent': swap_percent
            }
        else:
            print(f"   [INFO] No swap configured")
            test_results['swap'] = None

    except Exception as e:
        print(f"   [INFO] Could not check swap: {e}")

    # Test 4: Check Docker cache directories
    print("\n4. Testing Docker cache directories...")
    docker_data_locations = [
        Path.home() / '.docker',
        Path('/var/lib/docker'),
        Path('/tmp/docker-buildx'),
        project_root / '.docker-cache'
    ]

    cache_issues = []
    for cache_location in docker_data_locations:
        if cache_location.exists():
            try:
                if not os.access(cache_location, os.R_OK):
                    cache_issues.append(f"Docker cache directory not readable: {cache_location}")
                    print(f"   [FAIL] Cache directory not readable: {cache_location}")
                    continue

                # Quick size check (limit to prevent long scan)
                total_size = 0
                file_count = 0
                for file_path in cache_location.rglob('*'):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                            file_count += 1
                            if file_count > 1000:  # Limit for performance
                                break
                        except (OSError, PermissionError):
                            pass

                cache_size_gb = total_size / (1024**3)
                print(f"   [INFO] Cache {cache_location}: {cache_size_gb:.2f}GB, {file_count:,}+ files")

                if cache_size_gb > 20:
                    cache_issues.append(
                        f"Docker cache oversized: {cache_location} = {cache_size_gb:.2f}GB"
                    )
                    print(f"   [FAIL] Cache oversized: {cache_location}")

            except Exception as e:
                cache_issues.append(f"Failed to analyze cache directory {cache_location}: {str(e)}")
                print(f"   [FAIL] Error analyzing cache {cache_location}: {e}")

    if cache_issues:
        issues_found.extend(cache_issues)

    test_results['cache_issues'] = cache_issues

    # Test 5: Check file descriptor limits
    print("\n5. Testing file descriptor limits...")
    try:
        import resource
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)

        current_process = psutil.Process()
        current_fds = len(current_process.open_files()) + len(current_process.connections())

        min_required_fds = 1000
        available_fds = soft_limit - current_fds

        print(f"   File descriptors: {available_fds} available, {current_fds} used, {soft_limit} soft limit")

        if available_fds < min_required_fds:
            issues_found.append(
                f"Insufficient file descriptors: {available_fds} available, {min_required_fds} required"
            )
            print(f"   [FAIL] Insufficient file descriptors")
        else:
            print(f"   [PASS] Sufficient file descriptors")

        if soft_limit < 4096:
            issues_found.append(f"File descriptor soft limit too low: {soft_limit}")
            print(f"   [FAIL] File descriptor limit too low")

        test_results['file_descriptors'] = {
            'soft_limit': soft_limit,
            'hard_limit': hard_limit,
            'current_fds': current_fds,
            'available_fds': available_fds
        }

    except Exception as e:
        issues_found.append(f"Failed to check file descriptor limits: {str(e)}")
        print(f"   [FAIL] Error checking file descriptors: {e}")

    # Test 6: Check for Docker-related processes
    print("\n6. Testing Docker-related processes...")
    try:
        docker_processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_info = proc.info
                if proc_info['name'] and any(docker_term in proc_info['name'].lower()
                                            for docker_term in ['docker', 'containerd', 'buildx']):
                    docker_processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            if len(docker_processes) >= 20:
                break

        print(f"   Docker processes: {len(docker_processes)} found")

        if len(docker_processes) > 10:
            issues_found.append(f"Many Docker-related processes running: {len(docker_processes)}")
            print(f"   [FAIL] Too many Docker processes")
        else:
            print(f"   [PASS] Normal number of Docker processes")

        test_results['docker_processes'] = len(docker_processes)

    except Exception as e:
        print(f"   [INFO] Could not check Docker processes: {e}")

    # Summary
    print("\n=== TEST RESULTS SUMMARY ===")
    print(f"Total issues found: {len(issues_found)}")

    if issues_found:
        print("\n[CRITICAL] DOCKER RESOURCE STATE ISSUES DETECTED:")
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. {issue}")

        print(f"\n[SUCCESS] This test successfully detected {len(issues_found)} resource issues that would cause Docker Infrastructure Build Failures (Issue #1082)")
        print("These resource issues would cause cache key computation failures and build performance problems.")
    else:
        print("\n[SUCCESS] No Docker resource state issues detected")
        print("All Docker resource validation checks passed")

    print(f"\n[RESULTS] Full test results: {json.dumps(test_results, indent=2)}")

    # Save results
    results_file = project_root / 'docker_resource_state_1082_test_results.json'
    with open(results_file, 'w') as f:
        json.dump({
            'issue': '#1082 Docker Resource State Issues',
            'test_timestamp': '2025-09-15T14:54:00Z',
            'issues_found': issues_found,
            'test_results': test_results
        }, f, indent=2)

    print(f"\n[SAVED] Results saved to: {results_file}")

    return len(issues_found), test_results

if __name__ == "__main__":
    issue_count, results = test_docker_resource_state_issue_1082()
    exit(0 if issue_count == 0 else 1)  # Exit with error if issues found