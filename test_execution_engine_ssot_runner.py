#!/usr/bin/env python3
"""Simple test runner for ExecutionEngine SSOT validation tests.

This runner demonstrates the tests created for Issue #874 ExecutionEngine SSOT 
consolidation by running a subset of the validation tests directly.
"""

import sys
import os
import unittest
import asyncio
from pathlib import Path

# Add the codebase root to Python path
codebase_root = Path(__file__).parent
sys.path.insert(0, str(codebase_root))

def demonstrate_ssot_fragmentation():
    """Demonstrate ExecutionEngine fragmentation issues through simple analysis."""
    print("🔍 DEMONSTRATING EXECUTIONENGINE SSOT FRAGMENTATION")
    print("=" * 60)
    
    codebase_root = Path(__file__).parent
    violations_found = []
    
    # Simple scan for ExecutionEngine class definitions
    execution_engine_classes = []
    for py_file in codebase_root.rglob("*.py"):
        if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'node_modules', 'venv']):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                if line.strip().startswith('class ') and 'ExecutionEngine' in line:
                    class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                    if class_name:
                        execution_engine_classes.append((str(py_file), line_num, class_name))
        
        except (UnicodeDecodeError, IOError):
            continue
    
    print(f"Found {len(execution_engine_classes)} ExecutionEngine class definitions:")
    
    canonical_classes = []
    non_canonical_classes = []
    
    for file_path, line_num, class_name in execution_engine_classes:
        print(f"  - {class_name} in {file_path}:{line_num}")
        
        # Check if this is the canonical UserExecutionEngine
        if (class_name == "UserExecutionEngine" and 
            "netra_backend/app/agents/supervisor/user_execution_engine.py" in file_path):
            canonical_classes.append((file_path, class_name))
        else:
            non_canonical_classes.append((file_path, class_name))
    
    print(f"\n📊 ANALYSIS RESULTS:")
    print(f"  ✅ Canonical ExecutionEngine classes: {len(canonical_classes)}")
    print(f"  ❌ Non-canonical ExecutionEngine classes: {len(non_canonical_classes)}")
    
    # Check for import violations
    legacy_imports = []
    for py_file in codebase_root.rglob("*.py"):
        if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'node_modules', 'venv']):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                # Look for legacy import patterns
                if ('from' in line_stripped and 'import' in line_stripped and 
                    'ExecutionEngine' in line_stripped and 
                    'user_execution_engine' not in line_stripped):
                    legacy_imports.append((str(py_file), line_num, line_stripped))
        
        except (UnicodeDecodeError, IOError):
            continue
    
    print(f"  ⚠️ Legacy ExecutionEngine imports: {len(legacy_imports)}")
    
    # Demonstrate fragmentation evidence
    fragmentation_score = len(non_canonical_classes) + (len(legacy_imports) // 2)
    
    print(f"\n📈 FRAGMENTATION ASSESSMENT:")
    print(f"  Fragmentation Score: {fragmentation_score}")
    
    if fragmentation_score > 10:
        severity = "CRITICAL"
        description = "Severe ExecutionEngine fragmentation detected"
    elif fragmentation_score > 5:
        severity = "HIGH" 
        description = "Significant ExecutionEngine fragmentation detected"
    elif fragmentation_score > 2:
        severity = "MEDIUM"
        description = "Moderate ExecutionEngine fragmentation detected"
    else:
        severity = "LOW"
        description = "Minor ExecutionEngine fragmentation detected"
    
    print(f"  Severity: {severity}")
    print(f"  Description: {description}")
    
    print(f"\n🎯 SSOT CONSOLIDATION NEEDED:")
    print(f"  - Consolidate {len(non_canonical_classes)} duplicate ExecutionEngine classes")
    print(f"  - Migrate {len(legacy_imports)} legacy import statements") 
    print(f"  - Establish UserExecutionEngine as canonical SSOT")
    print(f"  - Implement factory pattern consolidation")
    
    return fragmentation_score > 0

def demonstrate_factory_pattern_issues():
    """Demonstrate ExecutionEngine factory pattern issues."""
    print("\n🏭 DEMONSTRATING FACTORY PATTERN FRAGMENTATION")
    print("=" * 60)
    
    codebase_root = Path(__file__).parent
    factory_classes = []
    direct_instantiations = []
    
    # Find factory class definitions
    for py_file in codebase_root.rglob("*.py"):
        if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'node_modules', 'venv']):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                # Find factory classes
                if (line.strip().startswith('class ') and 
                    ('ExecutionEngineFactory' in line or 'EngineFactory' in line)):
                    class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                    factory_classes.append((str(py_file), line_num, class_name))
                
                # Find direct ExecutionEngine instantiation
                if ('ExecutionEngine(' in line and 
                    'UserExecutionEngine(' not in line and
                    'ExecutionEngineFactory(' not in line and
                    not line.strip().startswith('#')):
                    direct_instantiations.append((str(py_file), line_num, line.strip()))
        
        except (UnicodeDecodeError, IOError):
            continue
    
    print(f"Found {len(factory_classes)} ExecutionEngineFactory implementations:")
    for file_path, line_num, class_name in factory_classes:
        canonical_indicator = "✅ CANONICAL" if "execution_engine_factory.py" in file_path else "❌ DUPLICATE"
        print(f"  - {canonical_indicator}: {class_name} in {Path(file_path).name}:{line_num}")
    
    print(f"\nFound {len(direct_instantiations)} direct ExecutionEngine instantiations:")
    for file_path, line_num, line_content in direct_instantiations[:5]:  # Show first 5
        print(f"  - {Path(file_path).name}:{line_num}: {line_content[:60]}...")
    
    if len(direct_instantiations) > 5:
        print(f"  ... and {len(direct_instantiations) - 5} more direct instantiations")
    
    # Assessment
    canonical_factories = [f for f in factory_classes if "execution_engine_factory.py" in f[0]]
    duplicate_factories = [f for f in factory_classes if "execution_engine_factory.py" not in f[0]]
    
    print(f"\n📊 FACTORY PATTERN ANALYSIS:")
    print(f"  ✅ Canonical factories: {len(canonical_factories)}")
    print(f"  ❌ Duplicate factories: {len(duplicate_factories)}")
    print(f"  ⚠️ Direct instantiations (bypassing factory): {len(direct_instantiations)}")
    
    factory_violations = len(duplicate_factories) + len(direct_instantiations)
    print(f"  Factory Pattern Violations: {factory_violations}")
    
    return factory_violations > 0

def demonstrate_import_violations():
    """Demonstrate ExecutionEngine import violations."""
    print("\n📦 DEMONSTRATING IMPORT PATTERN VIOLATIONS")
    print("=" * 60)
    
    codebase_root = Path(__file__).parent
    import_violations = []
    missing_canonical_imports = []
    
    # Analyze import patterns
    for py_file in codebase_root.rglob("*.py"):
        if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'node_modules', 'venv']):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            has_execution_engine_usage = False
            has_canonical_import = False
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for ExecutionEngine usage
                if 'ExecutionEngine' in line_stripped and not line_stripped.startswith('#'):
                    has_execution_engine_usage = True
                
                # Check for canonical imports
                if 'netra_backend.app.agents.supervisor.user_execution_engine' in line_stripped:
                    has_canonical_import = True
                
                # Check for deprecated import patterns
                deprecated_patterns = [
                    'from netra_backend.app.agents.supervisor.execution_engine import',
                    'import netra_backend.app.agents.supervisor.execution_engine',
                    'from netra_backend.app.agents.execution_engine import'
                ]
                
                for pattern in deprecated_patterns:
                    if pattern in line_stripped:
                        import_violations.append((str(py_file), line_num, line_stripped, "deprecated_import"))
            
            # Check for missing canonical imports
            if has_execution_engine_usage and not has_canonical_import:
                if 'ExecutionEngine' in content and 'test' not in str(py_file).lower():
                    missing_canonical_imports.append((str(py_file), "Should import UserExecutionEngine"))
        
        except (UnicodeDecodeError, IOError):
            continue
    
    print(f"Found {len(import_violations)} deprecated import patterns:")
    for file_path, line_num, line_content, violation_type in import_violations[:3]:
        print(f"  - {Path(file_path).name}:{line_num}: {line_content}")
    if len(import_violations) > 3:
        print(f"  ... and {len(import_violations) - 3} more deprecated imports")
    
    print(f"\nFound {len(missing_canonical_imports)} files missing canonical imports:")
    for file_path, reason in missing_canonical_imports[:3]:
        print(f"  - {Path(file_path).name}: {reason}")
    if len(missing_canonical_imports) > 3:
        print(f"  ... and {len(missing_canonical_imports) - 3} more files")
    
    total_import_issues = len(import_violations) + len(missing_canonical_imports)
    print(f"\n📊 IMPORT PATTERN ANALYSIS:")
    print(f"  ❌ Total import violations: {total_import_issues}")
    print(f"  ⚠️ Deprecated imports: {len(import_violations)}")
    print(f"  ⚠️ Missing canonical imports: {len(missing_canonical_imports)}")
    
    return total_import_issues > 0

def main():
    """Run ExecutionEngine SSOT fragmentation demonstration."""
    print("🚀 EXECUTIONENGINE SSOT CONSOLIDATION VALIDATION")
    print("Issue #874: ExecutionEngine SSOT consolidation compliance testing")
    print("=" * 80)
    
    # Run demonstrations
    fragmentation_detected = demonstrate_ssot_fragmentation()
    factory_issues_detected = demonstrate_factory_pattern_issues()
    import_issues_detected = demonstrate_import_violations()
    
    # Summary
    print(f"\n🎯 COMPREHENSIVE SSOT VIOLATION SUMMARY")
    print("=" * 60)
    
    total_issues = sum([fragmentation_detected, factory_issues_detected, import_issues_detected])
    
    print(f"SSOT Fragmentation Detected: {'YES' if fragmentation_detected else 'NO'}")
    print(f"Factory Pattern Issues: {'YES' if factory_issues_detected else 'NO'}")
    print(f"Import Pattern Issues: {'YES' if import_issues_detected else 'NO'}")
    
    if total_issues > 0:
        print(f"\n❌ RESULT: SSOT CONSOLIDATION NEEDED")
        print(f"   Found issues in {total_issues}/3 categories")
        print(f"   ExecutionEngine fragmentation requires consolidation to UserExecutionEngine SSOT")
        print(f"   Business Impact: Threatens $500K+ ARR chat functionality reliability")
        
        print(f"\n📋 RECOMMENDED ACTIONS:")
        print(f"   1. Consolidate all ExecutionEngine classes to UserExecutionEngine")
        print(f"   2. Migrate all imports to use canonical module paths")
        print(f"   3. Implement factory pattern consolidation")
        print(f"   4. Establish SSOT compliance enforcement")
        print(f"   5. Run comprehensive SSOT migration")
        
        return 1  # Indicate issues found
    else:
        print(f"\n✅ RESULT: SSOT COMPLIANCE ACHIEVED")
        print(f"   No major fragmentation detected")
        print(f"   ExecutionEngine SSOT consolidation is complete")
        
        return 0  # Indicate success

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)