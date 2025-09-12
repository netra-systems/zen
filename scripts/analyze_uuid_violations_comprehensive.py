#!/usr/bin/env python3
"""
Comprehensive Analysis Script for Issue #89 UnifiedIDManager Migration

This script provides detailed analysis of uuid.uuid4() violations across the codebase
to inform the remediation plan with accurate data and priority targeting.

BUSINESS IMPACT ANALYSIS:
- Identifies files affecting $500K+ ARR workflows
- Prioritizes WebSocket/chat functionality fixes
- Maps service integration dependencies
- Quantifies technical debt and remediation effort

PHASE 1 TARGETING:
- Critical infrastructure files first
- Service integration points
- WebSocket routing consistency issues
- UserExecutionContext isolation problems
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import argparse


@dataclass
class ViolationInstance:
    """Single instance of uuid.uuid4() usage."""
    file_path: str
    line_number: int
    line_content: str
    context_function: str
    context_class: str
    violation_type: str  # direct_uuid, string_format, method_call
    business_priority: str  # critical, high, medium, low


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    file_path: str
    violation_count: int
    violations: List[ViolationInstance]
    service_type: str  # auth_service, netra_backend, frontend, shared, tests
    module_category: str  # websocket, models, agents, tools, etc
    business_impact: str  # critical, high, medium, low
    migration_difficulty: str  # easy, medium, hard, complex


class UUIDViolationAnalyzer:
    """Comprehensive analyzer for uuid.uuid4() violations across the codebase."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations: List[ViolationInstance] = []
        self.file_analyses: List[FileAnalysis] = []
        
        # Business critical patterns
        self.critical_patterns = {
            'websocket': ['websocket', 'WebSocket', 'ws_', 'connection', 'client_id'],
            'auth': ['auth', 'session', 'user_id', 'jwt', 'token'],
            'agents': ['agent', 'Agent', 'execution', 'supervisor', 'tool'],
            'models': ['models.py', 'Model', 'create', 'id =', 'primary_key'],
            'factories': ['factory', 'Factory', 'create_', 'get_or_create']
        }
        
        # Service priority mapping
        self.service_priorities = {
            'netra_backend': 'critical',  # Main business logic
            'auth_service': 'critical',   # Authentication system
            'shared': 'high',             # Shared libraries
            'frontend': 'medium',         # UI layer
            'analytics_service': 'medium', # Analytics
            'tests': 'low'                # Test files
        }
        
    def analyze_project(self) -> Dict[str, any]:
        """Run comprehensive analysis of the entire project."""
        print("🔍 Starting comprehensive UUID violation analysis...")
        
        # Find all Python files
        python_files = self._find_python_files()
        print(f"📊 Found {len(python_files)} Python files to analyze")
        
        # Analyze each file
        for i, file_path in enumerate(python_files):
            if i % 100 == 0:
                print(f"📈 Progress: {i}/{len(python_files)} files analyzed")
                
            self._analyze_file(file_path)
        
        # Generate summary statistics
        summary = self._generate_summary()
        
        print(f"✅ Analysis complete: {len(self.violations)} violations in {len(self.file_analyses)} files")
        return summary
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Walk through all directories
        for root, dirs, files in os.walk(self.project_root):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in [
                '__pycache__', 'node_modules', 'venv', 'env', '.git'
            ]]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
                    
        return python_files
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single file for uuid.uuid4() violations."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
            violations = []
            
            # Check each line for violations
            for line_num, line in enumerate(lines, 1):
                line_violations = self._check_line_for_violations(
                    file_path, line_num, line, content
                )
                violations.extend(line_violations)
            
            # Create file analysis if violations found
            if violations:
                file_analysis = FileAnalysis(
                    file_path=str(file_path.relative_to(self.project_root)),
                    violation_count=len(violations),
                    violations=violations,
                    service_type=self._determine_service_type(file_path),
                    module_category=self._determine_module_category(file_path),
                    business_impact=self._determine_business_impact(file_path, violations),
                    migration_difficulty=self._determine_migration_difficulty(file_path, violations)
                )
                
                self.file_analyses.append(file_analysis)
                self.violations.extend(violations)
                
        except Exception as e:
            print(f"⚠️  Error analyzing {file_path}: {e}")
    
    def _check_line_for_violations(self, file_path: Path, line_num: int, 
                                   line: str, full_content: str) -> List[ViolationInstance]:
        """Check a single line for uuid.uuid4() violations."""
        violations = []
        
        # Pattern 1: Direct uuid.uuid4() usage
        if 'uuid.uuid4()' in line:
            violation = ViolationInstance(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=line_num,
                line_content=line.strip(),
                context_function=self._extract_function_context(full_content, line_num),
                context_class=self._extract_class_context(full_content, line_num),
                violation_type='direct_uuid',
                business_priority=self._determine_line_priority(line, file_path)
            )
            violations.append(violation)
        
        # Pattern 2: uuid4().hex[:8] usage
        if re.search(r'uuid\.uuid4\(\)\.hex\[:\d+\]', line):
            violation = ViolationInstance(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=line_num,
                line_content=line.strip(),
                context_function=self._extract_function_context(full_content, line_num),
                context_class=self._extract_class_context(full_content, line_num),
                violation_type='string_format',
                business_priority=self._determine_line_priority(line, file_path)
            )
            violations.append(violation)
        
        # Pattern 3: str(uuid.uuid4()) usage
        if 'str(uuid.uuid4())' in line:
            violation = ViolationInstance(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=line_num,
                line_content=line.strip(),
                context_function=self._extract_function_context(full_content, line_num),
                context_class=self._extract_class_context(full_content, line_num),
                violation_type='method_call',
                business_priority=self._determine_line_priority(line, file_path)
            )
            violations.append(violation)
            
        return violations
    
    def _extract_function_context(self, content: str, line_num: int) -> str:
        """Extract the function context for a violation."""
        lines = content.split('\n')
        
        # Look backwards for function definition
        for i in range(line_num - 1, max(0, line_num - 20), -1):
            line = lines[i].strip()
            if line.startswith('def ') or line.startswith('async def '):
                # Extract function name
                match = re.search(r'def\s+(\w+)', line)
                if match:
                    return match.group(1)
                    
        return 'unknown'
    
    def _extract_class_context(self, content: str, line_num: int) -> str:
        """Extract the class context for a violation."""
        lines = content.split('\n')
        
        # Look backwards for class definition
        for i in range(line_num - 1, max(0, line_num - 50), -1):
            line = lines[i].strip()
            if line.startswith('class '):
                # Extract class name
                match = re.search(r'class\s+(\w+)', line)
                if match:
                    return match.group(1)
                    
        return 'unknown'
    
    def _determine_service_type(self, file_path: Path) -> str:
        """Determine service type based on file path."""
        path_str = str(file_path)
        
        if 'netra_backend' in path_str:
            return 'netra_backend'
        elif 'auth_service' in path_str:
            return 'auth_service'
        elif 'frontend' in path_str:
            return 'frontend'
        elif 'shared' in path_str:
            return 'shared'
        elif 'analytics_service' in path_str:
            return 'analytics_service'
        elif 'test' in path_str.lower():
            return 'tests'
        else:
            return 'unknown'
    
    def _determine_module_category(self, file_path: Path) -> str:
        """Determine module category for prioritization."""
        path_str = str(file_path).lower()
        
        if any(pattern in path_str for pattern in ['websocket', 'ws_']):
            return 'websocket'
        elif any(pattern in path_str for pattern in ['auth', 'session']):
            return 'auth'
        elif any(pattern in path_str for pattern in ['agent', 'supervisor']):
            return 'agents'
        elif 'models.py' in path_str:
            return 'models'
        elif any(pattern in path_str for pattern in ['factory', 'create']):
            return 'factories'
        elif any(pattern in path_str for pattern in ['tool', 'dispatcher']):
            return 'tools'
        elif any(pattern in path_str for pattern in ['test']):
            return 'tests'
        else:
            return 'other'
    
    def _determine_business_impact(self, file_path: Path, violations: List[ViolationInstance]) -> str:
        """Determine business impact level."""
        path_str = str(file_path).lower()
        
        # Critical: WebSocket, auth, core business logic
        if any(pattern in path_str for pattern in ['websocket', 'auth', 'supervisor', 'execution']):
            return 'critical'
        
        # High: Agent system, tools, models
        if any(pattern in path_str for pattern in ['agent', 'tool', 'models', 'factory']):
            return 'high'
        
        # Medium: General backend, shared utilities
        if any(pattern in path_str for pattern in ['netra_backend', 'shared']):
            return 'medium'
        
        # Low: Tests, analytics
        if any(pattern in path_str for pattern in ['test', 'analytics']):
            return 'low'
        
        return 'medium'
    
    def _determine_migration_difficulty(self, file_path: Path, violations: List[ViolationInstance]) -> str:
        """Determine migration difficulty level."""
        # Count different violation types
        violation_types = set(v.violation_type for v in violations)
        
        # Complex: Multiple violation types or models
        if len(violation_types) > 1 or 'models.py' in str(file_path):
            return 'complex'
        
        # Hard: Many violations in single file
        if len(violations) > 10:
            return 'hard'
        
        # Medium: Moderate number of violations
        if len(violations) > 3:
            return 'medium'
        
        # Easy: Few violations
        return 'easy'
    
    def _determine_line_priority(self, line: str, file_path: Path) -> str:
        """Determine priority based on line content and file."""
        line_lower = line.lower()
        
        # Critical: WebSocket connections, user contexts
        if any(pattern in line_lower for pattern in [
            'websocket', 'connection_id', 'client_id', 'user_context', 'execution_context'
        ]):
            return 'critical'
        
        # High: Authentication, session management
        if any(pattern in line_lower for pattern in [
            'session_id', 'user_id', 'auth', 'token', 'agent_id'
        ]):
            return 'high'
        
        # Medium: General ID generation
        if any(pattern in line_lower for pattern in [
            'id =', 'id:', 'generate', 'create'
        ]):
            return 'medium'
        
        return 'low'
    
    def _generate_summary(self) -> Dict[str, any]:
        """Generate comprehensive analysis summary."""
        # Count by service
        service_counts = defaultdict(int)
        for file_analysis in self.file_analyses:
            service_counts[file_analysis.service_type] += file_analysis.violation_count
        
        # Count by module category
        category_counts = defaultdict(int)
        for file_analysis in self.file_analyses:
            category_counts[file_analysis.module_category] += file_analysis.violation_count
        
        # Count by business impact
        impact_counts = defaultdict(int)
        for file_analysis in self.file_analyses:
            impact_counts[file_analysis.business_impact] += file_analysis.violation_count
        
        # Count by migration difficulty
        difficulty_counts = defaultdict(int)
        for file_analysis in self.file_analyses:
            difficulty_counts[file_analysis.migration_difficulty] += file_analysis.violation_count
        
        # Count by violation type
        violation_type_counts = defaultdict(int)
        for violation in self.violations:
            violation_type_counts[violation.violation_type] += 1
        
        # Count by business priority
        priority_counts = defaultdict(int)
        for violation in self.violations:
            priority_counts[violation.business_priority] += 1
        
        return {
            'total_files_with_violations': len(self.file_analyses),
            'total_violations': len(self.violations),
            'service_breakdown': dict(service_counts),
            'category_breakdown': dict(category_counts),
            'impact_breakdown': dict(impact_counts),
            'difficulty_breakdown': dict(difficulty_counts),
            'violation_type_breakdown': dict(violation_type_counts),
            'priority_breakdown': dict(priority_counts)
        }
    
    def generate_remediation_report(self) -> str:
        """Generate detailed remediation report."""
        summary = self._generate_summary()
        
        report = []
        report.append("# Issue #89 UnifiedIDManager Migration - Comprehensive Analysis Report\n")
        report.append(f"**Generated:** {sys.version}")
        report.append(f"**Total Violations:** {summary['total_violations']:,}")
        report.append(f"**Files Affected:** {summary['total_files_with_violations']:,}")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary\n")
        critical_violations = summary['priority_breakdown'].get('critical', 0)
        high_violations = summary['priority_breakdown'].get('high', 0)
        report.append(f"**CRITICAL Priority:** {critical_violations:,} violations affecting $500K+ ARR workflows")
        report.append(f"**HIGH Priority:** {high_violations:,} violations requiring immediate attention")
        report.append("")
        
        # Service Breakdown
        report.append("## Service Impact Analysis\n")
        report.append("| Service | Violations | Impact Level | Priority |")
        report.append("|---------|------------|--------------|----------|")
        
        for service, count in sorted(summary['service_breakdown'].items(), 
                                   key=lambda x: x[1], reverse=True):
            priority = self.service_priorities.get(service, 'medium')
            impact = 'CRITICAL' if priority == 'critical' else priority.upper()
            report.append(f"| {service} | {count:,} | {impact} | Phase {'1' if priority == 'critical' else '2'} |")
        
        report.append("")
        
        # Category Breakdown
        report.append("## Module Category Analysis\n")
        report.append("| Category | Violations | Business Impact | Migration Difficulty |")
        report.append("|----------|------------|-----------------|---------------------|")
        
        category_impact_map = {
            'websocket': ('CRITICAL - Chat Functionality', 'COMPLEX'),
            'auth': ('CRITICAL - User Security', 'HARD'),
            'agents': ('HIGH - AI Workflows', 'MEDIUM'),
            'models': ('HIGH - Data Integrity', 'COMPLEX'),
            'factories': ('MEDIUM - System Architecture', 'HARD'),
            'tools': ('MEDIUM - Feature Support', 'EASY'),
            'tests': ('LOW - Development Quality', 'EASY'),
            'other': ('LOW - General Support', 'EASY')
        }
        
        for category, count in sorted(summary['category_breakdown'].items(), 
                                    key=lambda x: x[1], reverse=True):
            impact, difficulty = category_impact_map.get(category, ('MEDIUM', 'MEDIUM'))
            report.append(f"| {category} | {count:,} | {impact} | {difficulty} |")
        
        report.append("")
        
        # Phase 1 Critical Files
        report.append("## Phase 1 Critical Files (Week 1)\n")
        phase1_files = [f for f in self.file_analyses 
                       if f.business_impact == 'critical' or f.module_category in ['websocket', 'auth']]
        
        phase1_files.sort(key=lambda x: (x.business_impact, x.violation_count), reverse=True)
        
        report.append("| File | Violations | Category | Impact | Difficulty |")
        report.append("|------|------------|----------|---------|------------|")
        
        for file_analysis in phase1_files[:20]:  # Top 20 critical files
            report.append(f"| `{file_analysis.file_path}` | {file_analysis.violation_count} | {file_analysis.module_category} | {file_analysis.business_impact} | {file_analysis.migration_difficulty} |")
        
        if len(phase1_files) > 20:
            report.append(f"| ... | ... | ... | ... | ... |")
            report.append(f"| **Total Phase 1 Files** | **{sum(f.violation_count for f in phase1_files)}** | **{len(phase1_files)} files** | **CRITICAL** | **COMPLEX** |")
        
        report.append("")
        
        # Violation Type Analysis
        report.append("## Violation Pattern Analysis\n")
        report.append("| Pattern | Count | Remediation Strategy |")
        report.append("|---------|-------|---------------------|")
        
        remediation_strategies = {
            'direct_uuid': 'Replace with UnifiedIdGenerator.generate_base_id()',
            'string_format': 'Replace with UnifiedIdGenerator ID format methods',
            'method_call': 'Replace with appropriate UnifiedIdGenerator method'
        }
        
        for vtype, count in sorted(summary['violation_type_breakdown'].items(), 
                                 key=lambda x: x[1], reverse=True):
            strategy = remediation_strategies.get(vtype, 'Custom migration needed')
            report.append(f"| {vtype} | {count:,} | {strategy} |")
        
        report.append("")
        
        # Migration Effort Estimate
        total_critical = sum(f.violation_count for f in self.file_analyses if f.business_impact == 'critical')
        total_high = sum(f.violation_count for f in self.file_analyses if f.business_impact == 'high')
        
        report.append("## Migration Effort Estimate\n")
        report.append(f"- **Phase 1 (Critical):** {total_critical:,} violations - 1 week")
        report.append(f"- **Phase 2 (High):** {total_high:,} violations - 1 week") 
        report.append(f"- **Phase 3 (Medium/Low):** {summary['total_violations'] - total_critical - total_high:,} violations - 2 weeks")
        report.append("")
        report.append("**Total Estimated Effort:** 4 weeks with 2 engineers")
        
        return "\n".join(report)


def main():
    """Main analysis entry point."""
    parser = argparse.ArgumentParser(description="Analyze UUID violations for Issue #89")
    parser.add_argument('--project-root', default='/c/GitHub/netra-apex',
                       help='Project root directory')
    parser.add_argument('--output', default=None,
                       help='Output file for report')
    parser.add_argument('--top-files', type=int, default=50,
                       help='Number of top violating files to show')
    
    args = parser.parse_args()
    
    # Run analysis
    analyzer = UUIDViolationAnalyzer(args.project_root)
    summary = analyzer.analyze_project()
    
    # Generate report
    report = analyzer.generate_remediation_report()
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"📄 Report saved to: {args.output}")
    else:
        print(report)
    
    # Print top violating files
    print(f"\n🔥 Top {args.top_files} Files with Most Violations:")
    print("=" * 80)
    
    top_files = sorted(analyzer.file_analyses, key=lambda x: x.violation_count, reverse=True)
    for i, file_analysis in enumerate(top_files[:args.top_files], 1):
        print(f"{i:2d}. {file_analysis.file_path:<60} {file_analysis.violation_count:3d} violations")
        print(f"    Category: {file_analysis.module_category:<12} Impact: {file_analysis.business_impact:<8} Difficulty: {file_analysis.migration_difficulty}")
        print()


if __name__ == "__main__":
    main()