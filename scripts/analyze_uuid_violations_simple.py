#!/usr/bin/env python3
"""
Simple Analysis Script for Issue #89 UnifiedIDManager Migration

This script provides detailed analysis of uuid.uuid4() violations across the codebase
to inform the remediation plan with accurate data and priority targeting.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import argparse


def find_python_files(project_root):
    """Find all Python files in the project."""
    python_files = []
    
    for root, dirs, files in os.walk(project_root):
        # Skip common ignore directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
            '__pycache__', 'node_modules', 'venv', 'env', '.git', 'htmlcov'
        ]]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
                
    return python_files


def analyze_file(file_path, project_root):
    """Analyze a single file for uuid.uuid4() violations."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
        violations = []
        
        # Check each line for violations
        for line_num, line in enumerate(lines, 1):
            if 'uuid.uuid4()' in line:
                violations.append({
                    'file_path': str(file_path.relative_to(project_root)),
                    'line_number': line_num,
                    'line_content': line.strip(),
                    'violation_type': get_violation_type(line)
                })
                
        return violations
        
    except Exception as e:
        print(f"Warning: Error analyzing {file_path}: {e}")
        return []


def get_violation_type(line):
    """Determine the type of UUID violation."""
    if 'uuid.uuid4().hex[' in line:
        return 'string_format'
    elif 'str(uuid.uuid4())' in line:
        return 'method_call'
    else:
        return 'direct_uuid'


def categorize_file(file_path):
    """Categorize file by service and module type."""
    path_str = str(file_path).lower()
    
    # Service type
    if 'netra_backend' in path_str:
        service = 'netra_backend'
    elif 'auth_service' in path_str:
        service = 'auth_service'
    elif 'shared' in path_str:
        service = 'shared'
    elif 'test' in path_str:
        service = 'tests'
    else:
        service = 'other'
    
    # Module category
    if any(pattern in path_str for pattern in ['websocket', 'ws_']):
        category = 'websocket'
    elif any(pattern in path_str for pattern in ['auth', 'session']):
        category = 'auth'
    elif any(pattern in path_str for pattern in ['agent', 'supervisor']):
        category = 'agents'
    elif 'models.py' in path_str:
        category = 'models'
    elif any(pattern in path_str for pattern in ['factory', 'create']):
        category = 'factories'
    elif any(pattern in path_str for pattern in ['test']):
        category = 'tests'
    else:
        category = 'other'
    
    # Business priority
    if any(pattern in path_str for pattern in ['websocket', 'auth', 'supervisor', 'execution']):
        priority = 'critical'
    elif any(pattern in path_str for pattern in ['agent', 'tool', 'models']):
        priority = 'high'
    elif service in ['netra_backend', 'shared']:
        priority = 'medium'
    else:
        priority = 'low'
    
    return service, category, priority


def main():
    """Main analysis entry point."""
    parser = argparse.ArgumentParser(description="Analyze UUID violations for Issue #89")
    parser.add_argument('--project-root', default='/c/GitHub/netra-apex',
                       help='Project root directory')
    parser.add_argument('--output', default=None,
                       help='Output file for report')
    
    args = parser.parse_args()
    
    print("Starting UUID violation analysis...")
    
    # Find all Python files
    python_files = find_python_files(args.project_root)
    print(f"Found {len(python_files)} Python files to analyze")
    
    # Analyze all files
    all_violations = []
    file_counts = {}
    
    for i, file_path in enumerate(python_files):
        if i % 500 == 0:
            print(f"Progress: {i}/{len(python_files)} files analyzed")
            
        violations = analyze_file(file_path, Path(args.project_root))
        if violations:
            all_violations.extend(violations)
            file_counts[str(file_path.relative_to(Path(args.project_root)))] = len(violations)
    
    print(f"Analysis complete: {len(all_violations)} violations in {len(file_counts)} files")
    
    # Categorize violations
    service_counts = defaultdict(int)
    category_counts = defaultdict(int)
    priority_counts = defaultdict(int)
    violation_type_counts = defaultdict(int)
    
    for violation in all_violations:
        file_path = violation['file_path']
        service, category, priority = categorize_file(file_path)
        
        service_counts[service] += 1
        category_counts[category] += 1
        priority_counts[priority] += 1
        violation_type_counts[violation['violation_type']] += 1
    
    # Generate report
    report = []
    report.append("# Issue #89 UnifiedIDManager Migration - Analysis Report\\n")
    report.append(f"**Total Violations:** {len(all_violations):,}")
    report.append(f"**Files Affected:** {len(file_counts):,}")
    report.append("")
    
    # Service breakdown
    report.append("## Service Impact Analysis\\n")
    report.append("| Service | Violations | Priority |")
    report.append("|---------|------------|----------|")
    
    service_priority_map = {
        'netra_backend': 'CRITICAL',
        'auth_service': 'CRITICAL',
        'shared': 'HIGH',
        'tests': 'LOW',
        'other': 'MEDIUM'
    }
    
    for service, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True):
        priority = service_priority_map.get(service, 'MEDIUM')
        report.append(f"| {service} | {count:,} | {priority} |")
    
    report.append("")
    
    # Category breakdown
    report.append("## Module Category Analysis\\n")
    report.append("| Category | Violations | Business Impact |")
    report.append("|----------|------------|-----------------|")
    
    category_impact_map = {
        'websocket': 'CRITICAL - Chat Functionality',
        'auth': 'CRITICAL - User Security',
        'agents': 'HIGH - AI Workflows',
        'models': 'HIGH - Data Integrity',
        'factories': 'MEDIUM - System Architecture',
        'tests': 'LOW - Development Quality',
        'other': 'LOW - General Support'
    }
    
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        impact = category_impact_map.get(category, 'MEDIUM')
        report.append(f"| {category} | {count:,} | {impact} |")
    
    report.append("")
    
    # Priority breakdown
    report.append("## Business Priority Analysis\\n")
    report.append("| Priority | Violations | Phase |")
    report.append("|----------|------------|-------|")
    
    for priority in ['critical', 'high', 'medium', 'low']:
        count = priority_counts[priority]
        phase = "Phase 1" if priority == 'critical' else "Phase 2" if priority == 'high' else "Phase 3"
        report.append(f"| {priority.upper()} | {count:,} | {phase} |")
    
    report.append("")
    
    # Top violating files
    report.append("## Top 30 Files Requiring Immediate Attention\\n")
    report.append("| File | Violations | Service | Category | Priority |")
    report.append("|------|------------|---------|----------|----------|")
    
    sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
    for file_path, count in sorted_files[:30]:
        service, category, priority = categorize_file(file_path)
        report.append(f"| `{file_path}` | {count} | {service} | {category} | {priority.upper()} |")
    
    report.append("")
    
    # Violation type breakdown
    report.append("## Violation Pattern Analysis\\n")
    report.append("| Pattern | Count | Remediation Strategy |")
    report.append("|---------|-------|---------------------|")
    
    remediation_strategies = {
        'direct_uuid': 'Replace with UnifiedIdGenerator.generate_base_id()',
        'string_format': 'Replace with UnifiedIdGenerator format methods',
        'method_call': 'Replace with appropriate UnifiedIdGenerator method'
    }
    
    for vtype, count in sorted(violation_type_counts.items(), key=lambda x: x[1], reverse=True):
        strategy = remediation_strategies.get(vtype, 'Custom migration needed')
        report.append(f"| {vtype} | {count:,} | {strategy} |")
    
    report.append("")
    
    # Migration effort estimate
    critical_count = priority_counts['critical']
    high_count = priority_counts['high']
    
    report.append("## Migration Effort Estimate\\n")
    report.append(f"- **Phase 1 (Critical):** {critical_count:,} violations - 1 week")
    report.append(f"- **Phase 2 (High):** {high_count:,} violations - 1 week")
    report.append(f"- **Phase 3 (Medium/Low):** {len(all_violations) - critical_count - high_count:,} violations - 2 weeks")
    report.append("")
    report.append("**Total Estimated Effort:** 4 weeks with 2 engineers")
    
    report_text = "\\n".join(report)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report_text)
        print(f"Report saved to: {args.output}")
    else:
        print(report_text)
    
    # Print top 20 files
    print(f"\\nTop 20 Files with Most Violations:")
    print("=" * 80)
    
    for i, (file_path, count) in enumerate(sorted_files[:20], 1):
        service, category, priority = categorize_file(file_path)
        print(f"{i:2d}. {file_path:<60} {count:3d} violations")
        print(f"    Service: {service:<15} Category: {category:<12} Priority: {priority.upper()}")
        print()


if __name__ == "__main__":
    main()