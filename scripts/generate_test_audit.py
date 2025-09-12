"""
Generate comprehensive test organization audit

Business Value Justification (BVJ):
1. Segment: Platform/Internal
2. Business Goal: Development Velocity
3. Value Impact: Identifies test organization issues blocking development
4. Strategic Impact: Reduces development friction by 50%
"""

import os
import json
import subprocess
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).parent.parent

# Directories to exclude from test counting
EXCLUDE_DIRS = {
    '.venv', 'venv', '.env', 'env',
    'node_modules', '__pycache__', '.git',
    'site-packages', 'dist-packages',
    'build', 'dist', '.tox', '.pytest_cache',
    '.mypy_cache', '.coverage', 'htmlcov',
    'Lib', 'lib', 'lib64', 'Scripts', 'bin',
    'include', 'Include', 'share'
}

def is_excluded_path(path: Path) -> bool:
    """Check if path should be excluded"""
    path_parts = set(path.parts)
    return bool(path_parts.intersection(EXCLUDE_DIRS))

def count_test_files() -> Dict[str, int]:
    """Count test files by location"""
    counts = defaultdict(int)
    
    # Count Python test files
    for path in PROJECT_ROOT.rglob("test*.py"):
        if not is_excluded_path(path):
            parent = path.parent.name
            counts[parent] += 1
    
    for path in PROJECT_ROOT.rglob("*test.py"):
        if not is_excluded_path(path):
            parent = path.parent.name
            counts[parent] += 1
    
    # Count TypeScript/JavaScript test files
    for pattern in ["*.test.ts", "*.test.tsx", "*.test.js", "*.test.jsx", "*.spec.ts", "*.spec.tsx"]:
        for path in PROJECT_ROOT.rglob(pattern):
            if not is_excluded_path(path):
                parent = path.parent.name
                counts[f"{parent} (JS/TS)"] += 1
    
    return dict(counts)

def analyze_test_structure() -> Dict:
    """Analyze test organization structure"""
    structure = {
        "test_directories": [],
        "conftest_files": [],
        "test_runners": [],
        "test_configs": [],
        "naming_patterns": defaultdict(int),
        "test_frameworks": []
    }
    
    # Find test directories
    for path in PROJECT_ROOT.rglob("test*"):
        if path.is_dir() and not is_excluded_path(path):
            rel_path = path.relative_to(PROJECT_ROOT)
            if "test" in path.name.lower():
                structure["test_directories"].append(str(rel_path))
    
    # Find conftest files
    for path in PROJECT_ROOT.rglob("conftest.py"):
        if not is_excluded_path(path):
            structure["conftest_files"].append(str(path.relative_to(PROJECT_ROOT)))
    
    # Find test runners
    for path in PROJECT_ROOT.glob("**/test*.py"):
        if not is_excluded_path(path) and "runner" in path.name:
            structure["test_runners"].append(str(path.relative_to(PROJECT_ROOT)))
    
    # Find test configs
    for pattern in ["pytest.ini", "pyproject.toml", "jest.config.*", ".env.test*", ".env.mock*"]:
        for path in PROJECT_ROOT.rglob(pattern):
            if not is_excluded_path(path):
                structure["test_configs"].append(str(path.relative_to(PROJECT_ROOT)))
    
    # Analyze naming patterns
    for path in PROJECT_ROOT.rglob("test*.py"):
        if not is_excluded_path(path):
            name = path.stem
            if name.startswith("test_") and name.endswith("_l3"):
                structure["naming_patterns"]["L3 pattern"] += 1
            elif name.startswith("test_") and name.endswith("_critical"):
                structure["naming_patterns"]["Critical suffix"] += 1
            elif name.startswith("test_") and name.endswith("_comprehensive"):
                structure["naming_patterns"]["Comprehensive suffix"] += 1
            elif name.startswith("test_"):
                structure["naming_patterns"]["Standard pytest"] += 1
            else:
                structure["naming_patterns"]["Non-standard"] += 1
    
    return structure

def check_test_health() -> Dict:
    """Check test health indicators"""
    health = {
        "import_errors": [],
        "collection_warnings": [],
        "failing_tests": [],
        "test_framework_size": 0
    }
    
    # Count test framework files
    test_framework_path = PROJECT_ROOT / "test_framework"
    if test_framework_path.exists():
        py_files = list(test_framework_path.rglob("*.py"))
        health["test_framework_size"] = len([f for f in py_files if not is_excluded_path(f)])
    
    # Check for bad_tests.json
    bad_tests_file = PROJECT_ROOT / "test_reports" / "bad_tests.json"
    if bad_tests_file.exists():
        try:
            with open(bad_tests_file, 'r') as f:
                bad_tests = json.load(f)
                health["failing_tests"] = len(bad_tests.get("tests", []))
        except:
            pass
    
    return health

def generate_audit_report() -> str:
    """Generate comprehensive audit report"""
    counts = count_test_files()
    structure = analyze_test_structure()
    health = check_test_health()
    
    # Calculate totals
    total_test_files = sum(counts.values())
    total_conftest = len(structure["conftest_files"])
    total_test_dirs = len(structure["test_directories"])
    
    report = f"""# Test Organization Audit Report

## Executive Summary

The Netra codebase test organization analysis reveals opportunities for improvement in test structure and maintenance.

## Current State Analysis

### 1. Test File Distribution
- **{total_test_files} test files** across the project (excluding dependencies)
- **{total_conftest} conftest.py files** for pytest configuration
- **{total_test_dirs} test directories** identified
- **{health['test_framework_size']} files** in test_framework directory
"""
    
    if health["failing_tests"]:
        report += f"- **{health['failing_tests']} failing tests** tracked in bad_tests.json\n"
    
    report += f"""
### 2. Test Locations

Top test directories by file count:
"""
    
    # Sort and show top locations
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for location, count in sorted_counts:
        report += f"- `{location}/`: {count} test files\n"
    
    report += f"""
### 3. Organizational Patterns

#### 3.1 Test Naming Conventions
"""
    
    for pattern, count in structure["naming_patterns"].items():
        report += f"- {pattern}: {count} files\n"
    
    report += f"""
#### 3.2 Test Structure
- Test directories: {len(structure['test_directories'])}
- Configuration files: {len(structure['test_configs'])}
- Test runners found: {len(structure['test_runners'])}

### 4. Key Test Directories
"""
    
    # Show main test directories
    main_dirs = [d for d in structure["test_directories"] if "/" not in d][:10]
    for dir_name in main_dirs:
        report += f"- `{dir_name}/`\n"
    
    report += """
## Identified Issues

### 1. Configuration Sprawl
"""
    
    if total_conftest > 10:
        report += f"- **Excessive conftest files** ({total_conftest}): Should be consolidated\n"
    
    if len(structure["test_configs"]) > 5:
        report += f"- **Multiple test configurations** ({len(structure['test_configs'])}): Creates confusion\n"
    
    if len(structure["test_runners"]) > 3:
        report += f"- **Multiple test runners** ({len(structure['test_runners'])}): Overlapping functionality\n"
    
    report += """
### 2. Test Organization
"""
    
    if structure["naming_patterns"].get("L3 pattern", 0) > 0:
        report += f"- **Inconsistent L3 pattern** used in {structure['naming_patterns']['L3 pattern']} files\n"
    
    if structure["naming_patterns"].get("Non-standard", 0) > 0:
        report += f"- **Non-standard naming** in {structure['naming_patterns']['Non-standard']} files\n"
    
    legacy_dirs = [d for d in structure["test_directories"] if "legacy" in d.lower()]
    if legacy_dirs:
        report += f"- **Legacy test directories** found: {len(legacy_dirs)} directories\n"
    
    report += """
## Recommendations

### Immediate Actions (Priority 1)
1. **Consolidate Configuration**: Reduce conftest.py files to service-level only
2. **Standardize Naming**: Use consistent `test_*.py` pattern
3. **Archive Legacy Tests**: Move or remove legacy test directories

### Short-term Improvements (Priority 2)
1. **Simplify Test Framework**: Reduce test_framework to essential components
2. **Unify Test Runners**: Single test runner with clear options
3. **Clear Test Levels**: Define and document 3-5 clear test levels

### Long-term Goals (Priority 3)
1. **Test Organization**: Group tests by domain/service
2. **Performance Optimization**: Implement proper parallel execution
3. **Documentation**: Single source of truth for test guidelines

## Business Impact

- **Development Velocity**: Test complexity impacts productivity
- **Maintenance Burden**: Complex structure requires more maintenance
- **Quality Assurance**: Disorganized tests reduce confidence

## Next Steps

1. Run this audit regularly to track improvements
2. Prioritize fixes based on development impact
3. Document decisions in SPEC/learnings/testing.xml
"""
    
    return report

def main():
    """Generate and save test audit report"""
    report = generate_audit_report()
    
    output_file = PROJECT_ROOT / "TEST_ORGANIZATION_AUDIT.md"
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f" PASS:  Test audit report generated: {output_file}")
    
    # Also print summary
    counts = count_test_files()
    total = sum(counts.values())
    print(f"\n CHART:  Summary:")
    print(f"  - Total test files: {total} (excluding dependencies)")
    print(f"  - Test locations: {len(counts)}")
    
    structure = analyze_test_structure()
    print(f"  - Conftest files: {len(structure['conftest_files'])}")
    print(f"  - Test directories: {len(structure['test_directories'])}")

if __name__ == "__main__":
    main()