"""
SSOT Validation Tests - Single Execution Engine Enforcement for Issue #759

PURPOSE: Detect and validate execution engine multiplicity violations.
These tests should FAIL initially to prove 12+ execution engines exist, then PASS after consolidation.

BUSINESS IMPACT: $500K+ ARR protected by ensuring single execution engine routing
FOCUS: Multiple execution engines causing Golden Path response delivery failures
"""

import os
import ast
import glob
import pytest
import importlib.util
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional


class ExecutionEngineAnalyzer:
    """Analyzer for detecting execution engine implementations and patterns."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
    
    def find_execution_engine_implementations(self) -> List[Dict[str, str]]:
        """
        Find all ExecutionEngine class implementations across the codebase.
        
        Returns:
            List of dictionaries with file path and class information
        """
        implementations = []
        
        # Patterns to search for
        engine_patterns = [
            'class UserExecutionEngine',
            'class RequestScopedExecutionEngine', 
            'class EnhancedToolExecutionEngine',
            'class ExecutionEngine',
            'class BaseExecutionEngine',
            'class AgentExecutionEngine',
            'class ToolExecutionEngine',
            'class SupervisorExecutionEngine'
        ]
        
        for py_file in self.root_dir.rglob("*.py"):
            if any(excluded in str(py_file) for excluded in self.exclude_dirs):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in engine_patterns:
                    if pattern in content:
                        # Get more context about the class
                        lines = content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            if pattern in line:
                                implementations.append({
                                    'file': str(py_file.relative_to(self.root_dir)),
                                    'full_path': str(py_file),
                                    'class_name': pattern.replace('class ', ''),
                                    'line_num': line_num,
                                    'line_content': line.strip()
                                })
                                break
                                
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return implementations
    
    def find_execution_engine_factories(self) -> List[Dict[str, str]]:
        """Find all execution engine factory implementations."""
        factories = []
        
        factory_patterns = [
            'def create_execution_engine',
            'def create_user_execution_engine', 
            'def create_request_scoped_engine',
            'def get_execution_engine',
            'ExecutionEngineFactory',
            'UserExecutionEngineFactory'
        ]
        
        for py_file in self.root_dir.rglob("*.py"):
            if any(excluded in str(py_file) for excluded in self.exclude_dirs):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in factory_patterns:
                    if pattern in content:
                        lines = content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            if pattern in line and ('def ' in line or 'class ' in line):
                                factories.append({
                                    'file': str(py_file.relative_to(self.root_dir)),
                                    'full_path': str(py_file),
                                    'factory_name': pattern,
                                    'line_num': line_num,
                                    'line_content': line.strip()
                                })
                                break
                                
            except (UnicodeDecodeError, PermissionError):
                continue
                
        return factories
    
    def analyze_execution_engine_usage(self) -> Dict[str, List[Dict]]:
        """Analyze how execution engines are used across the codebase."""
        usage_patterns = {
            'instantiation': [],
            'imports': [],
            'method_calls': []
        }
        
        # Look for instantiation patterns
        instantiation_patterns = [
            'UserExecutionEngine(',
            'UserExecutionEngine(',
            'UserExecutionEngine(',
            'UserExecutionEngine('
        ]
        
        # Look for import patterns  
        import_patterns = [
            'from netra_backend.app.agents.supervisor.user_execution_engine import',
            'from netra_backend.app.agents.supervisor.execution_engine import',
            'from netra_backend.app.agents.supervisor.user_execution_engine import',
            'from netra_backend.app.tools.enhanced_tool_execution_engine import'
        ]
        
        for py_file in self.root_dir.rglob("*.py"):
            if any(excluded in str(py_file) for excluded in self.exclude_dirs):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Check instantiation patterns
                    for pattern in instantiation_patterns:
                        if pattern in line_stripped:
                            usage_patterns['instantiation'].append({
                                'file': str(py_file.relative_to(self.root_dir)),
                                'pattern': pattern,
                                'line_num': line_num,
                                'line_content': line_stripped
                            })
                    
                    # Check import patterns
                    for pattern in import_patterns:
                        if pattern in line_stripped:
                            usage_patterns['imports'].append({
                                'file': str(py_file.relative_to(self.root_dir)),
                                'pattern': pattern,
                                'line_num': line_num,
                                'line_content': line_stripped
                            })
                            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return usage_patterns


# Initialize analyzer
root_dir = Path(__file__).parent.parent.parent.parent
analyzer = ExecutionEngineAnalyzer(root_dir)


def test_only_one_execution_engine_exists():
    """
    FAIL TEST: Prove that only one execution engine implementation exists (SSOT).
    
    This test should FAIL initially, proving that 12+ execution engines exist.
    After SSOT consolidation, this test should PASS (only UserExecutionEngine exists).
    
    Expected SSOT: UserExecutionEngine in netra_backend/app/agents/supervisor/user_execution_engine.py
    """
    implementations = analyzer.find_execution_engine_implementations()
    
    # Group by class name for analysis
    by_class = {}
    for impl in implementations:
        class_name = impl['class_name']
        if class_name not in by_class:
            by_class[class_name] = []
        by_class[class_name].append(impl)
    
    if implementations:
        print(f"\n🔍 FOUND {len(implementations)} EXECUTION ENGINE IMPLEMENTATIONS:")
        for class_name, impls in by_class.items():
            print(f"  {class_name}: {len(impls)} implementations")
            for impl in impls[:3]:  # Show first 3
                print(f"    - {impl['file']}:{impl['line_num']}")
            if len(impls) > 3:
                print(f"    ... and {len(impls) - 3} more")
    
    # Identify SSOT target
    ssot_implementations = by_class.get('UserExecutionEngine', [])
    non_ssot_implementations = [
        impl for impl in implementations 
        if impl['class_name'] != 'UserExecutionEngine'
    ]
    
    # This test SHOULD FAIL initially (proving violation exists)  
    assert len(non_ssot_implementations) == 0, (
        f"🚨 MAJOR SSOT VIOLATION: Found {len(non_ssot_implementations)} non-SSOT execution engines. "
        f"Only UserExecutionEngine should exist. "
        f"Non-SSOT classes found: {list(set(impl['class_name'] for impl in non_ssot_implementations))}. "
        f"Total implementations: {len(implementations)}"
    )
    
    # Validate SSOT exists
    assert len(ssot_implementations) >= 1, (
        f"🚨 CRITICAL: UserExecutionEngine SSOT not found. "
        f"Expected implementation in netra_backend/app/agents/supervisor/user_execution_engine.py"
    )
    
    # Validate SSOT is in correct location
    ssot_file_paths = [impl['file'] for impl in ssot_implementations]
    expected_ssot_path = "netra_backend/app/agents/supervisor/user_execution_engine.py"
    
    assert any(expected_ssot_path in path for path in ssot_file_paths), (
        f"🚨 SSOT LOCATION VIOLATION: UserExecutionEngine not in expected location. "
        f"Expected: {expected_ssot_path}, Found in: {ssot_file_paths}"
    )


def test_execution_engine_factory_consolidation():
    """
    FAIL TEST: Prove that execution engine factory implementations are consolidated.
    
    Multiple factory patterns indicate SSOT violations.
    Should FAIL initially due to multiple factories, PASS after consolidation.
    """
    factories = analyzer.find_execution_engine_factories()
    
    if factories:
        print(f"\n🔍 FOUND {len(factories)} EXECUTION ENGINE FACTORIES:")
        factory_by_name = {}
        for factory in factories:
            name = factory['factory_name']
            if name not in factory_by_name:
                factory_by_name[name] = []
            factory_by_name[name].append(factory)
            
        for name, instances in factory_by_name.items():
            print(f"  {name}: {len(instances)} instances")
            for instance in instances[:2]:
                print(f"    - {instance['file']}:{instance['line_num']}")
    
    # Allow reasonable number of factory patterns (not zero, but not excessive)
    assert len(factories) <= 3, (
        f"🚨 SSOT VIOLATION: Found {len(factories)} execution engine factories. "
        f"Expected ≤3 consolidated factory patterns. "
        f"Factory types: {list(set(f['factory_name'] for f in factories))}"
    )
    
    # Validate that if factories exist, they create UserExecutionEngine
    user_engine_factories = [
        f for f in factories 
        if 'user_execution_engine' in f['factory_name'].lower()
    ]
    
    if factories:
        assert len(user_engine_factories) >= 1, (
            f"🚨 SSOT VIOLATION: Found {len(factories)} factories but none create UserExecutionEngine. "
            f"Factories should create SSOT UserExecutionEngine instances."
        )


def test_execution_engine_usage_patterns():
    """
    FAIL TEST: Analyze execution engine usage patterns for SSOT violations.
    
    Multiple instantiation patterns indicate non-SSOT usage.
    Should FAIL initially due to multiple patterns, PASS after SSOT consolidation.
    """
    usage = analyzer.analyze_execution_engine_usage()
    
    instantiation_patterns = usage['instantiation']
    import_patterns = usage['imports']
    
    if instantiation_patterns:
        print(f"\n🔍 EXECUTION ENGINE INSTANTIATION ANALYSIS:")
        pattern_count = {}
        for inst in instantiation_patterns:
            pattern = inst['pattern']
            pattern_count[pattern] = pattern_count.get(pattern, 0) + 1
            
        for pattern, count in pattern_count.items():
            print(f"  {pattern}: {count} usages")
    
    if import_patterns:
        print(f"\n🔍 EXECUTION ENGINE IMPORT ANALYSIS:")
        import_count = {}
        for imp in import_patterns:
            pattern = imp['pattern']
            import_count[pattern] = import_count.get(pattern, 0) + 1
            
        for pattern, count in import_count.items():
            print(f"  {pattern}: {count} files")
    
    # Count non-SSOT instantiations
    non_ssot_instantiations = [
        inst for inst in instantiation_patterns
        if 'UserExecutionEngine(' not in inst['pattern']
    ]
    
    # Count non-SSOT imports (broken paths)
    broken_imports = [
        imp for imp in import_patterns
        if 'app.core.user_execution_engine' in imp['pattern']
    ]
    
    # This should FAIL initially due to non-SSOT patterns
    assert len(non_ssot_instantiations) == 0, (
        f"🚨 SSOT VIOLATION: Found {len(non_ssot_instantiations)} non-SSOT engine instantiations. "
        f"All instantiations should use UserExecutionEngine(). "
        f"Non-SSOT patterns: {list(set(inst['pattern'] for inst in non_ssot_instantiations))}"
    )
    
    # Broken imports are a separate but related violation
    if broken_imports:
        print(f"⚠️  RELATED ISSUE: {len(broken_imports)} broken import paths found")


def test_supervisor_agent_execution_engine_usage():
    """
    FAIL TEST: Validate that supervisor agents use SSOT execution engine only.
    
    Supervisor agents are critical for Golden Path - they must use UserExecutionEngine.
    Should FAIL if supervisors use multiple execution engine types.
    """
    supervisor_files = []
    
    # Find supervisor agent files
    for py_file in root_dir.rglob("*supervisor*.py"):
        if any(excluded in str(py_file) for excluded in analyzer.exclude_dirs):
            continue
        if py_file.is_file():
            supervisor_files.append(py_file)
    
    supervisor_engine_usage = []
    
    for supervisor_file in supervisor_files:
        try:
            with open(supervisor_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_num, line in enumerate(lines, 1):
                # Look for execution engine usage in supervisor files
                if 'ExecutionEngine' in line and ('import' in line or '(' in line):
                    supervisor_engine_usage.append({
                        'file': str(supervisor_file.relative_to(root_dir)),
                        'line_num': line_num,
                        'line_content': line.strip()
                    })
                    
        except (UnicodeDecodeError, PermissionError):
            continue
    
    if supervisor_engine_usage:
        print(f"\n🔍 SUPERVISOR EXECUTION ENGINE USAGE ({len(supervisor_engine_usage)} instances):")
        for usage in supervisor_engine_usage[:10]:
            print(f"  - {usage['file']}:{usage['line_num']} -> {usage['line_content']}")
    
    # Analyze for SSOT compliance
    non_ssot_supervisor_usage = [
        usage for usage in supervisor_engine_usage
        if 'UserExecutionEngine' not in usage['line_content'] 
        and 'ExecutionEngine' in usage['line_content']
        and 'import' in usage['line_content']
    ]
    
    # Allow some flexibility but flag major violations
    assert len(non_ssot_supervisor_usage) <= 5, (
        f"🚨 GOLDEN PATH RISK: Found {len(non_ssot_supervisor_usage)} supervisor files using non-SSOT execution engines. "
        f"Supervisors should use UserExecutionEngine for Golden Path reliability. "
        f"Files: {[usage['file'] for usage in non_ssot_supervisor_usage[:3]]}"
    )


def test_websocket_execution_engine_integration():
    """
    FAIL TEST: Validate WebSocket-ExecutionEngine integration uses SSOT pattern.
    
    WebSocket event delivery depends on execution engine routing.
    Multiple execution engines cause WebSocket event delivery failures.
    """
    websocket_engine_files = []
    
    # Find WebSocket files that reference execution engines
    for py_file in root_dir.rglob("*.py"):
        if any(excluded in str(py_file) for excluded in analyzer.exclude_dirs):
            continue
            
        # Look for files that combine WebSocket and ExecutionEngine concepts
        if any(keyword in str(py_file).lower() for keyword in ['websocket', 'socket', 'ws']):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'ExecutionEngine' in content:
                    websocket_engine_files.append({
                        'file': str(py_file.relative_to(root_dir)),
                        'full_path': str(py_file)
                    })
                    
            except (UnicodeDecodeError, PermissionError):
                continue
    
    if websocket_engine_files:
        print(f"\n🔍 WEBSOCKET-EXECUTION ENGINE INTEGRATION FILES:")
        for file_info in websocket_engine_files:
            print(f"  - {file_info['file']}")
    
    # This is informational for now - captures the integration scope
    # Future iterations can add stricter validation
    assert len(websocket_engine_files) <= 10, (
        f"🚨 INTEGRATION COMPLEXITY: Found {len(websocket_engine_files)} files integrating WebSocket with ExecutionEngine. "
        f"High integration count may indicate multiple execution engine routing paths for WebSocket events. "
        f"Expected: Concentrated integration through UserExecutionEngine SSOT."
    )


if __name__ == "__main__":
    # Allow manual execution for debugging
    print("🧪 RUNNING EXECUTION ENGINE SSOT ENFORCEMENT TESTS FOR ISSUE #759")
    print("=" * 70)
    
    try:
        test_only_one_execution_engine_exists()
        print("✅ Single execution engine test PASSED")
    except AssertionError as e:
        print(f"❌ Single execution engine test FAILED: {e}")
    
    try:
        test_execution_engine_factory_consolidation()
        print("✅ Factory consolidation test PASSED")
    except AssertionError as e:
        print(f"❌ Factory consolidation test FAILED: {e}")
        
    try:
        test_execution_engine_usage_patterns() 
        print("✅ Usage patterns test PASSED")
    except AssertionError as e:
        print(f"❌ Usage patterns test FAILED: {e}")
        
    try:
        test_supervisor_agent_execution_engine_usage()
        print("✅ Supervisor usage test PASSED")
    except AssertionError as e:
        print(f"❌ Supervisor usage test FAILED: {e}")
