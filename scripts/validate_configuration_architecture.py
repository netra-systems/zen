#!/usr/bin/env python3
"""
Configuration Architecture Validation Script

Purpose: Prevent configuration debt like Issue #558 by validating SSOT compliance
Created: 2025-09-12 (Issue #558 Resolution)
Usage: python scripts/validate_configuration_architecture.py
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Handle different toml library versions
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python
    except ImportError:
        try:
            import toml
            # Create tomllib-compatible interface
            class tomllib:
                @staticmethod
                def load(fp):
                    if hasattr(fp, 'read'):
                        return toml.load(fp)
                    else:
                        with open(fp, 'r') as f:
                            return toml.load(f)
        except ImportError:
            print("ERROR: No TOML library available. Install with: pip install tomli")
            sys.exit(1)

def validate_pytest_configuration() -> Tuple[bool, List[str]]:
    """
    Validate pytest configuration SSOT compliance.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    project_root = Path(__file__).parent.parent
    
    # Check primary configuration exists
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        issues.append("CRITICAL: Primary configuration file pyproject.toml is missing")
        return False, issues
    
    try:
        # Handle different TOML library interfaces
        if hasattr(tomllib, 'load'):
            if 'tomllib' in str(type(tomllib)) or hasattr(tomllib, 'loads'):
                # Python 3.11+ tomllib - requires binary mode
                with open(pyproject_path, 'rb') as f:
                    config = tomllib.load(f)
            else:
                # toml library - uses text mode
                config = tomllib.load(pyproject_path)
        else:
            with open(pyproject_path, 'r') as f:
                import configparser
                # Fallback parsing - simplified approach
                content = f.read()
                if '[tool.pytest.ini_options]' in content:
                    config = {'tool': {'pytest.ini_options': {'testpaths': ['tests']}}}
                else:
                    config = {}
        
        # Check both possible pytest configuration sections
        tool_config = config.get('tool', {})
        pytest_config = tool_config.get('pytest.ini_options', {})
        if not pytest_config:
            pytest_config = tool_config.get('pytest', {})
        
        if not pytest_config:
            issues.append("CRITICAL: No pytest configuration found in pyproject.toml")
            return False, issues
            
        # Validate required sections
        required_sections = ['testpaths', 'markers', 'addopts']
        for section in required_sections:
            if section not in pytest_config:
                issues.append(f"WARNING: Missing {section} in pytest configuration")
        
        # Check for service-specific test paths
        testpaths = pytest_config.get('testpaths', [])
        expected_paths = ['tests', 'netra_backend/tests', 'auth_service/tests']
        
        for expected_path in expected_paths:
            if expected_path not in testpaths:
                issues.append(f"WARNING: Missing {expected_path} in testpaths")
        
        print(f"[OK] Primary configuration valid with {len(pytest_config.get('markers', []))} markers")
        
    except Exception as e:
        issues.append(f"ERROR: Failed to parse pyproject.toml: {e}")
        return False, issues
    
    return True, issues

def find_orphaned_pytest_configs() -> List[str]:
    """Find service-specific pytest.ini files that should not exist."""
    project_root = Path(__file__).parent.parent
    orphaned_configs = []
    
    # Service directories that should NOT have pytest.ini files
    service_dirs = [
        'netra_backend',
        'auth_service', 
        'shared',
        'frontend'  # Jest config is OK, but not pytest.ini
    ]
    
    for service_dir in service_dirs:
        service_path = project_root / service_dir
        if service_path.exists():
            pytest_ini = service_path / "pytest.ini"
            if pytest_ini.exists():
                orphaned_configs.append(str(pytest_ini))
    
    # Also check for nested pytest.ini files
    for pytest_ini in project_root.rglob("pytest.ini"):
        if pytest_ini.name == "pytest.ini" and pytest_ini != project_root / "pytest.ini":
            orphaned_configs.append(str(pytest_ini))
    
    return orphaned_configs

def validate_test_runner_config() -> Tuple[bool, List[str]]:
    """Validate unified test runner uses centralized configuration."""
    issues = []
    project_root = Path(__file__).parent.parent
    test_runner_path = project_root / "tests" / "unified_test_runner.py"
    
    if not test_runner_path.exists():
        issues.append("WARNING: Unified test runner not found")
        return True, issues
    
    try:
        with open(test_runner_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for references to service-specific pytest.ini files
        problematic_patterns = [
            'netra_backend/pytest.ini',
            'auth_service/pytest.ini', 
            'shared/pytest.ini'
        ]
        
        for pattern in problematic_patterns:
            if pattern in content:
                issues.append(f"ERROR: Test runner still references {pattern}")
        
        # Check for correct pyproject.toml references
        if '"config": "pyproject.toml"' in content:
            print("[OK] Test runner correctly uses centralized configuration")
        else:
            issues.append("WARNING: Test runner may not be using pyproject.toml")
        
    except Exception as e:
        issues.append(f"ERROR: Failed to validate test runner: {e}")
        return False, issues
    
    return len([i for i in issues if i.startswith('ERROR')]) == 0, issues

def find_configuration_references() -> Dict[str, List[str]]:
    """Find all references to pytest configuration files."""
    project_root = Path(__file__).parent.parent
    references = {
        'pytest.ini_references': [],
        'pyproject.toml_references': []
    }
    
    # Search common file types for configuration references
    search_patterns = ['*.py', '*.md', '*.txt', '*.yaml', '*.yml']
    
    for pattern in search_patterns:
        for file_path in project_root.rglob(pattern):
            if file_path.is_file() and not any(skip in str(file_path) for skip in ['.git', 'node_modules', '__pycache__', '.pytest_cache']):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if 'pytest.ini' in content:
                        references['pytest.ini_references'].append(str(file_path))
                    
                    if 'pyproject.toml' in content:
                        references['pyproject.toml_references'].append(str(file_path))
                        
                except Exception:
                    continue  # Skip problematic files
    
    return references

def main():
    """Main validation function."""
    print("[SEARCH] Configuration Architecture Validation (Issue #558 Prevention)")
    print("=" * 60)
    
    all_valid = True
    all_issues = []
    
    # 1. Validate primary pytest configuration
    print("\n1. Validating Primary Configuration...")
    valid, issues = validate_pytest_configuration()
    all_valid &= valid
    all_issues.extend(issues)
    
    # 2. Find orphaned configuration files
    print("\n2. Checking for Orphaned Configuration Files...")
    orphaned = find_orphaned_pytest_configs()
    if orphaned:
        print(f"[ERROR] Found {len(orphaned)} orphaned pytest.ini files:")
        for config in orphaned:
            print(f"   - {config}")
        all_issues.extend([f"ORPHANED: {config}" for config in orphaned])
        all_valid = False
    else:
        print("[OK] No orphaned pytest.ini files found")
    
    # 3. Validate test runner configuration
    print("\n3. Validating Test Runner Configuration...")
    valid, issues = validate_test_runner_config()
    all_valid &= valid
    all_issues.extend(issues)
    
    # 4. Find all configuration references
    print("\n4. Analyzing Configuration References...")
    references = find_configuration_references()
    
    pytest_ini_refs = len(references['pytest.ini_references'])
    pyproject_refs = len(references['pyproject.toml_references'])
    
    print(f"[STATS] Configuration References:")
    print(f"   - pytest.ini references: {pytest_ini_refs}")
    print(f"   - pyproject.toml references: {pyproject_refs}")
    
    if pytest_ini_refs > 0:
        print(f"\n[WARNING] Files referencing pytest.ini (may need updates):")
        for ref in references['pytest.ini_references'][:10]:  # Show first 10
            print(f"   - {ref}")
        if pytest_ini_refs > 10:
            print(f"   ... and {pytest_ini_refs - 10} more")
    
    # Summary
    print("\n" + "=" * 60)
    if all_valid:
        print("[PASS] CONFIGURATION ARCHITECTURE VALIDATION PASSED")
        print("   - SSOT compliance maintained")
        print("   - No configuration debt detected")
    else:
        print("[FAIL] CONFIGURATION ARCHITECTURE ISSUES DETECTED")
        print(f"   - {len(all_issues)} issues found")
        print("   - Review and fix issues above")
    
    print("\nISSUES SUMMARY:")
    for issue in all_issues:
        level = issue.split(':')[0]
        if level == "CRITICAL":
            print(f"[CRITICAL] {issue}")
        elif level == "ERROR":
            print(f"[ERROR] {issue}")
        elif level == "WARNING":
            print(f"[WARNING] {issue}")
        else:
            print(f"[INFO] {issue}")
    
    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())