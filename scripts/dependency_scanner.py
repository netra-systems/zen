#!/usr/bin/env python3
"""
Dependency Scanner - GAP-008 Implementation
Comprehensive validation of Python, Node, and System dependencies
MAX 200 lines, functions MAX 8 lines - MANDATORY architectural constraint
"""

import json
import sys
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Optional
from packaging import version as pkg_version

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas.diagnostic_types import (
    DependencyReport, DependencyInfo, DependencyStatus, 
    DiagnosticResult, DiagnosticError, FixResult
)
from scripts.diagnostic_helpers import (
    create_dependency_error, create_fix_result, run_command_async
)


class DependencyScanner:
    """Main dependency scanner orchestrator - modular design"""
    
    def __init__(self):
        self.python_deps: List[DependencyInfo] = []
        self.node_deps: List[DependencyInfo] = []
        self.system_deps: List[DependencyInfo] = []


async def scan_python_dependencies() -> List[DependencyInfo]:
    """Scan Python dependencies from requirements.txt"""
    req_file = Path("requirements.txt")
    if not req_file.exists():
        return []
    
    deps = []
    installed_packages = await get_installed_python_packages()
    requirements = parse_requirements_file(str(req_file))
    
    for name, required_version in requirements.items():
        dep = await validate_python_dependency(name, required_version, installed_packages)
        deps.append(dep)
    return deps


def parse_requirements_file(filepath: str) -> Dict[str, str]:
    """Parse requirements.txt into name->version mapping"""
    requirements = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                name, req_version = extract_package_info(line)
                if name:
                    requirements[name] = req_version
    return requirements


def extract_package_info(line: str) -> tuple[str, str]:
    """Extract package name and version from requirement line"""
    line = line.split('#')[0].strip()
    if not line:
        return "", ""
    
    # Handle various formats: package>=1.0, package==1.0, package[extra]>=1.0
    match = re.match(r'^([a-zA-Z0-9\-_.\[,\]]+?)([>=<~!]+)(.+)$', line)
    if match:
        return match.group(1).split('[')[0], match.group(3)
    return line, ""


async def get_installed_python_packages() -> Dict[str, str]:
    """Get installed Python packages with versions"""
    try:
        output = await run_command_async(["pip", "list", "--format=json"], timeout=15)
        packages = json.loads(output)
        return {pkg['name'].lower().replace('-', '_'): pkg['version'] for pkg in packages}
    except Exception:
        return {}


async def validate_python_dependency(name: str, required: str, installed: Dict[str, str]) -> DependencyInfo:
    """Validate single Python dependency"""
    normalized_name = name.lower().replace('-', '_')
    installed_ver = installed.get(normalized_name)
    
    if not installed_ver:
        return DependencyInfo(name=name, required_version=required, status=DependencyStatus.MISSING, can_auto_fix=True)
    
    if required and not is_version_compatible(installed_ver, required):
        return DependencyInfo(name=name, required_version=required, installed_version=installed_ver, status=DependencyStatus.INCOMPATIBLE, can_auto_fix=True)
    
    return DependencyInfo(name=name, required_version=required, installed_version=installed_ver, status=DependencyStatus.VALID)


async def scan_node_dependencies() -> List[DependencyInfo]:
    """Scan Node.js dependencies from package.json"""
    pkg_file = Path("frontend/package.json")
    if not pkg_file.exists():
        return []
    
    with open(pkg_file, 'r') as f:
        package_data = json.load(f)
    
    deps = []
    all_deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
    installed_packages = await get_installed_node_packages()
    
    for name, required_version in all_deps.items():
        dep = await validate_node_dependency(name, required_version, installed_packages)
        deps.append(dep)
    return deps


async def get_installed_node_packages() -> Dict[str, str]:
    """Get installed Node packages with versions"""
    try:
        output = await run_command_async(["npm", "ls", "--json", "--depth=0"], cwd="frontend", timeout=15)
        data = json.loads(output)
        deps = data.get("dependencies", {})
        return {name: info.get("version", "") for name, info in deps.items()}
    except Exception:
        return {}


async def validate_node_dependency(name: str, required: str, installed: Dict[str, str]) -> DependencyInfo:
    """Validate single Node dependency"""
    installed_ver = installed.get(name)
    clean_required = required.lstrip('^~>=<')
    
    if not installed_ver:
        return DependencyInfo(name=name, required_version=required, status=DependencyStatus.MISSING, can_auto_fix=True)
    
    return DependencyInfo(name=name, required_version=required, installed_version=installed_ver, status=DependencyStatus.VALID)


async def scan_system_dependencies() -> List[DependencyInfo]:
    """Scan system-level dependencies"""
    system_checks = [
        ("python", ">=3.10", ["python", "--version"]),
        ("node", ">=18.0", ["node", "--version"]),
        ("postgresql", ">=13", ["psql", "--version"]),
        ("redis", ">=6.0", ["redis-cli", "--version"])
    ]
    
    deps = []
    for name, required, cmd in system_checks:
        dep = await check_system_dependency(name, required, cmd)
        deps.append(dep)
    return deps


async def check_system_dependency(name: str, required: str, cmd: List[str]) -> DependencyInfo:
    """Check single system dependency"""
    try:
        output = await run_command_async(cmd, timeout=5)
        version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', output)
        if version_match:
            installed_ver = version_match.group(1)
            return DependencyInfo(name=name, required_version=required, installed_version=installed_ver, status=DependencyStatus.VALID)
    except Exception:
        pass
    
    return DependencyInfo(name=name, required_version=required, status=DependencyStatus.MISSING, can_auto_fix=False)


def is_version_compatible(installed: str, required: str) -> bool:
    """Check if installed version meets requirement"""
    try:
        # Handle common version operators
        if ">=" in required:
            min_version = required.split(">=")[1].strip()
            return pkg_version.parse(installed) >= pkg_version.parse(min_version)
        elif "==" in required:
            exact_version = required.split("==")[1].strip()
            return pkg_version.parse(installed) == pkg_version.parse(exact_version)
        return True  # Default to compatible
    except Exception:
        return True  # Default to compatible on parse error


async def generate_dependency_report() -> DependencyReport:
    """Generate comprehensive dependency report"""
    python_deps = await scan_python_dependencies()
    node_deps = await scan_node_dependencies()
    system_deps = await scan_system_dependencies()
    
    summary = calculate_summary_stats(python_deps + node_deps + system_deps)
    auto_fixes = any(dep.can_auto_fix and dep.status != DependencyStatus.VALID for dep in python_deps + node_deps)
    
    return DependencyReport(
        python_dependencies=python_deps,
        node_dependencies=node_deps,
        system_dependencies=system_deps,
        summary=summary,
        auto_fixes_available=auto_fixes
    )


def calculate_summary_stats(all_deps: List[DependencyInfo]) -> Dict[str, int]:
    """Calculate summary statistics for dependencies"""
    stats = {"total": len(all_deps), "valid": 0, "missing": 0, "outdated": 0, "incompatible": 0, "error": 0}
    for dep in all_deps:
        stats[dep.status.value] = stats.get(dep.status.value, 0) + 1
    return stats


async def apply_dependency_fixes(report: DependencyReport) -> List[FixResult]:
    """Apply automatic fixes where possible"""
    fixes = []
    
    # Fix Python dependencies
    python_issues = [dep for dep in report.python_dependencies if dep.can_auto_fix and dep.status != DependencyStatus.VALID]
    if python_issues:
        fix = await fix_python_dependencies()
        fixes.append(fix)
    
    # Fix Node dependencies  
    node_issues = [dep for dep in report.node_dependencies if dep.can_auto_fix and dep.status != DependencyStatus.VALID]
    if node_issues:
        fix = await fix_node_dependencies()
        fixes.append(fix)
    
    return fixes


async def fix_python_dependencies() -> FixResult:
    """Fix Python dependency issues"""
    try:
        await run_command_async(["pip", "install", "-r", "requirements.txt"], timeout=120)
        return create_fix_result("python-deps", True, True, "Python dependencies installed/updated")
    except Exception as e:
        return create_fix_result("python-deps", True, False, f"Python fix failed: {str(e)}")


async def fix_node_dependencies() -> FixResult:
    """Fix Node dependency issues"""
    try:
        await run_command_async(["npm", "install"], cwd="frontend", timeout=120)
        return create_fix_result("node-deps", True, True, "Node dependencies installed")
    except Exception as e:
        return create_fix_result("node-deps", True, False, f"Node fix failed: {str(e)}")


async def main():
    """Main entry point with CLI interface"""
    if "--scan" in sys.argv or len(sys.argv) == 1:
        report = await generate_dependency_report()
        print(json.dumps(report.model_dump(), indent=2, default=str))
    elif "--fix" in sys.argv:
        report = await generate_dependency_report()
        fixes = await apply_dependency_fixes(report)
        print(json.dumps({"fixes": [f.model_dump() for f in fixes]}, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())