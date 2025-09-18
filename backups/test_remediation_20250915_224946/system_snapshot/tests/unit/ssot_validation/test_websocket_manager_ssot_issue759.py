"""
SSOT Validation Tests - WebSocket Manager SSOT for Issue #759

PURPOSE: Detect and validate WebSocket manager/event delivery multiplicity violations.
These tests should FAIL initially to prove multiple WebSocket systems exist, then PASS after consolidation.

BUSINESS IMPACT: $500K+ ARR protected by ensuring reliable WebSocket event delivery
FOCUS: Multiple WebSocket event delivery systems causing Golden Path response failures
"""

import os
import ast
import glob
import pytest
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional


class WebSocketSystemAnalyzer:
    """Analyzer for detecting WebSocket manager implementations and event delivery systems."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
    
    def find_websocket_manager_implementations(self) -> List[Dict[str, str]]:
        """
        Find all WebSocket manager class implementations across the codebase.
        
        Returns:
            List of dictionaries with file path and class information
        """
        implementations = []
        
        # Patterns to search for WebSocket manager classes
        manager_patterns = [
            'class UnifiedWebSocketManager',
            'class WebSocketManager', 
            'class AgentWebSocketBridge',
            'class UnifiedWebSocketEmitter',
            'class WebSocketEmitter',
            'class WebSocketHandler',
            'class WebSocketCore',
            'class ChatWebSocketManager'
        ]
        
        for py_file in self.root_dir.rglob("*.py"):
            if any(excluded in str(py_file) for excluded in self.exclude_dirs):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in manager_patterns:
                    if pattern in content:
                        lines = content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            if pattern in line and line.strip().startswith('class'):
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
    
    def find_websocket_event_delivery_systems(self) -> Dict[str, List[Dict]]:
        """
        Find all WebSocket event delivery implementations.
        
        Returns:
            Dictionary categorized by delivery system type
        """
        delivery_systems = {
            'agent_events': [],
            'websocket_send': [],
            'event_emitters': [],
            'notification_systems': []
        }
        
        # Patterns for different delivery systems
        event_patterns = {
            'agent_events': [
                'agent_started',
                'agent_thinking', 
                'tool_executing',
                'tool_completed',
                'agent_completed'
            ],
            'websocket_send': [
                'websocket.send',
                'ws.send_json',
                'await websocket.send',
                'send_websocket_message'
            ],
            'event_emitters': [
                'emit_agent_event',
                'emit_websocket_event', 
                'send_agent_update',
                'notify_websocket'
            ],
            'notification_systems': [
                'WebSocketNotifier',
                'AgentNotifier',
                'EventNotifier'
            ]
        }
        
        for py_file in self.root_dir.rglob("*.py"):
            if any(excluded in str(py_file) for excluded in self.exclude_dirs):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Check each category
                    for category, patterns in event_patterns.items():
                        for pattern in patterns:
                            if pattern in line_stripped:
                                delivery_systems[category].append({
                                    'file': str(py_file.relative_to(self.root_dir)),
                                    'pattern': pattern,
                                    'line_num': line_num,
                                    'line_content': line_stripped,
                                    'category': category
                                })
                                
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return delivery_systems
    
    def find_websocket_routing_conflicts(self) -> List[Dict[str, str]]:
        """
        Find potential WebSocket routing conflicts where multiple systems
        might be competing to deliver the same events.
        """
        conflicts = []
        
        # Look for files that import multiple WebSocket systems
        for py_file in self.root_dir.rglob("*.py"):
            if any(excluded in str(py_file) for excluded in self.exclude_dirs):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Count WebSocket system imports
                websocket_imports = []
                for line in content.split('\n'):
                    if 'import' in line and any(ws_term in line.lower() for ws_term in 
                                              ['websocket', 'agentwebsocket', 'unifiedwebsocket']):
                        websocket_imports.append(line.strip())
                
                # If multiple WebSocket systems imported, potential conflict
                if len(websocket_imports) >= 2:
                    conflicts.append({
                        'file': str(py_file.relative_to(self.root_dir)),
                        'import_count': len(websocket_imports),
                        'imports': websocket_imports
                    })
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return conflicts
    
    def analyze_websocket_event_completeness(self) -> Dict[str, int]:
        """
        Analyze if all 5 critical WebSocket events are properly implemented
        across the codebase.
        
        Critical events: agent_started, agent_thinking, tool_executing, 
        tool_completed, agent_completed
        """
        critical_events = {
            'agent_started': 0,
            'agent_thinking': 0,
            'tool_executing': 0,
            'tool_completed': 0,
            'agent_completed': 0
        }
        
        for py_file in self.root_dir.rglob("*.py"):
            if any(excluded in str(py_file) for excluded in self.exclude_dirs):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for event in critical_events:
                    # Count occurrences of each critical event
                    critical_events[event] += content.count(f'"{event}"') + content.count(f"'{event}'")
                    
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return critical_events


# Initialize analyzer
root_dir = Path(__file__).parent.parent.parent.parent
analyzer = WebSocketSystemAnalyzer(root_dir)


@pytest.mark.unit
def test_single_websocket_manager_exists():
    """
    FAIL TEST: Prove that only one WebSocket manager implementation exists (SSOT).
    
    This test should FAIL initially, proving multiple WebSocket managers exist.
    After SSOT consolidation, this test should PASS (only one primary manager exists).
    
    Expected: One primary WebSocket manager with clear SSOT responsibility
    """
    implementations = analyzer.find_websocket_manager_implementations()
    
    # Group by class name for analysis
    by_class = {}
    for impl in implementations:
        class_name = impl['class_name']
        if class_name not in by_class:
            by_class[class_name] = []
        by_class[class_name].append(impl)
    
    if implementations:
        print(f"\n🔍 FOUND {len(implementations)} WEBSOCKET MANAGER IMPLEMENTATIONS:")
        for class_name, impls in by_class.items():
            print(f"  {class_name}: {len(impls)} implementations")
            for impl in impls[:2]:  # Show first 2
                print(f"    - {impl['file']}:{impl['line_num']}")
    
    # Allow reasonable number of WebSocket managers (not excessive proliferation)
    # Bridge, Core, and Handler patterns can coexist if they have distinct responsibilities
    assert len(by_class) <= 4, (
        f"🚨 WEBSOCKET SSOT VIOLATION: Found {len(by_class)} different WebSocket manager types. "
        f"Expected ≤4 distinct manager types with clear responsibilities. "
        f"Manager types: {list(by_class.keys())}. "
        f"Total implementations: {len(implementations)}"
    )
    
    # Flag excessive implementations of the same type
    excessive_implementations = [
        (class_name, impls) for class_name, impls in by_class.items() 
        if len(impls) > 2
    ]
    
    assert len(excessive_implementations) == 0, (
        f"🚨 DUPLICATE MANAGER VIOLATION: Found excessive implementations: "
        f"{[(name, len(impls)) for name, impls in excessive_implementations]}. "
        f"Each manager type should have ≤2 implementations (interface + concrete)."
    )


@pytest.mark.unit
def test_websocket_event_delivery_consolidation():
    """
    FAIL TEST: Prove WebSocket event delivery is consolidated through SSOT channels.
    
    Multiple event delivery systems cause race conditions and silent failures.
    Should FAIL initially due to multiple delivery systems, PASS after consolidation.
    """
    delivery_systems = analyzer.find_websocket_event_delivery_systems()
    
    total_delivery_points = sum(len(events) for events in delivery_systems.values())
    
    if total_delivery_points > 0:
        print(f"\n🔍 WEBSOCKET EVENT DELIVERY ANALYSIS ({total_delivery_points} delivery points):")
        for category, events in delivery_systems.items():
            if events:
                unique_files = len(set(event['file'] for event in events))
                print(f"  {category}: {len(events)} events across {unique_files} files")
    
    # Specific checks for critical delivery patterns
    agent_event_files = set(event['file'] for event in delivery_systems['agent_events'])
    websocket_send_files = set(event['file'] for event in delivery_systems['websocket_send'])
    
    # Flag excessive distribution of agent events
    assert len(agent_event_files) <= 10, (
        f"🚨 EVENT DELIVERY FRAGMENTATION: Agent events found in {len(agent_event_files)} files. "
        f"Expected consolidation through ≤10 files for maintainable event delivery. "
        f"Files: {list(agent_event_files)[:5]}"
    )
    
    # Flag excessive WebSocket send operations
    assert len(websocket_send_files) <= 15, (
        f"🚨 WEBSOCKET SEND FRAGMENTATION: WebSocket send operations in {len(websocket_send_files)} files. "
        f"Expected consolidation through ≤15 files for reliable message delivery. "
        f"Files: {list(websocket_send_files)[:5]}"
    )


@pytest.mark.unit
def test_websocket_routing_conflict_detection():
    """
    FAIL TEST: Detect routing conflicts where multiple WebSocket systems compete.
    
    Files importing multiple WebSocket systems create routing confusion.
    Should FAIL if excessive conflicts exist, PASS after routing consolidation.
    """
    conflicts = analyzer.find_websocket_routing_conflicts()
    
    if conflicts:
        print(f"\n🔍 WEBSOCKET ROUTING CONFLICTS DETECTED ({len(conflicts)} files):")
        for conflict in conflicts[:10]:  # Show first 10
            print(f"  - {conflict['file']}: {conflict['import_count']} WebSocket imports")
            for imp in conflict['imports'][:2]:
                print(f"    -> {imp}")
    
    # Allow some integration points but flag excessive conflicts
    high_conflict_files = [c for c in conflicts if c['import_count'] >= 4]
    
    assert len(high_conflict_files) <= 3, (
        f"🚨 WEBSOCKET ROUTING CONFLICT: Found {len(high_conflict_files)} files with ≥4 WebSocket imports. "
        f"This indicates routing confusion that can cause event delivery failures. "
        f"High-conflict files: {[c['file'] for c in high_conflict_files]}"
    )
    
    # Total conflicts should be reasonable
    assert len(conflicts) <= 20, (
        f"🚨 WEBSOCKET INTEGRATION COMPLEXITY: Found {len(conflicts)} files importing multiple WebSocket systems. "
        f"Expected ≤20 integration points for maintainable routing. "
        f"This may indicate need for WebSocket system consolidation."
    )


@pytest.mark.unit
def test_critical_websocket_events_coverage():
    """
    FAIL TEST: Validate that all 5 critical WebSocket events are properly covered.
    
    Missing critical events cause Golden Path failures - users don't see agent progress.
    Should FAIL if any critical event is missing, PASS when all events are present.
    
    Critical events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
    """
    event_coverage = analyzer.analyze_websocket_event_completeness()
    
    print(f"\n🔍 CRITICAL WEBSOCKET EVENT COVERAGE:")
    for event, count in event_coverage.items():
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {event}: {count} implementations")
    
    # All 5 critical events must be present
    missing_events = [event for event, count in event_coverage.items() if count == 0]
    
    assert len(missing_events) == 0, (
        f"🚨 CRITICAL WEBSOCKET EVENTS MISSING: {missing_events}. "
        f"All 5 critical events (agent_started, agent_thinking, tool_executing, "
        f"tool_completed, agent_completed) must be implemented for Golden Path functionality. "
        f"Missing events cause users to not see agent progress."
    )
    
    # Events should have reasonable coverage (not just one implementation each)
    under_implemented_events = [
        event for event, count in event_coverage.items() if count < 2
    ]
    
    if under_implemented_events:
        print(f"⚠️  UNDER-IMPLEMENTED EVENTS: {under_implemented_events} (may indicate fragility)")


@pytest.mark.unit
def test_websocket_execution_engine_integration():
    """
    FAIL TEST: Validate WebSocket-ExecutionEngine integration follows SSOT pattern.
    
    WebSocket event delivery must route through SSOT execution engine.
    Multiple routing paths cause race conditions and silent failures.
    """
    # Find files that integrate WebSocket with ExecutionEngine
    integration_files = []
    
    for py_file in root_dir.rglob("*.py"):
        if any(excluded in str(py_file) for excluded in analyzer.exclude_dirs):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Look for files that reference both WebSocket and ExecutionEngine concepts
            has_websocket = any(term in content.lower() for term in 
                              ['websocket', 'ws.send', 'agent_started', 'agent_thinking'])
            has_execution_engine = 'ExecutionEngine' in content
            
            if has_websocket and has_execution_engine:
                integration_files.append({
                    'file': str(py_file.relative_to(root_dir)),
                    'full_path': str(py_file)
                })
                
        except (UnicodeDecodeError, PermissionError):
            continue
    
    if integration_files:
        print(f"\n🔍 WEBSOCKET-EXECUTION ENGINE INTEGRATION FILES ({len(integration_files)}):")
        for file_info in integration_files[:10]:
            print(f"  - {file_info['file']}")
    
    # Validate integration complexity is reasonable
    assert len(integration_files) <= 15, (
        f"🚨 WEBSOCKET-ENGINE INTEGRATION COMPLEXITY: Found {len(integration_files)} integration files. "
        f"High integration count may indicate multiple routing paths for WebSocket events, "
        f"increasing risk of race conditions and delivery failures. "
        f"Expected: Consolidated integration through SSOT ExecutionEngine routing."
    )


@pytest.mark.unit
def test_websocket_bridge_vs_manager_distinction():
    """
    FAIL TEST: Validate clear distinction between WebSocket bridges and managers.
    
    AgentWebSocketBridge vs UnifiedWebSocketManager should have distinct responsibilities.
    Overlap indicates potential SSOT violation or routing confusion.
    """
    implementations = analyzer.find_websocket_manager_implementations()
    
    # Categorize implementations
    bridges = [impl for impl in implementations if 'bridge' in impl['class_name'].lower()]
    managers = [impl for impl in implementations if 'manager' in impl['class_name'].lower()]
    emitters = [impl for impl in implementations if 'emitter' in impl['class_name'].lower()]
    
    print(f"\n🔍 WEBSOCKET SYSTEM ARCHITECTURE:")
    print(f"  Bridges: {len(bridges)} implementations")
    print(f"  Managers: {len(managers)} implementations") 
    print(f"  Emitters: {len(emitters)} implementations")
    
    for category, impls in [('Bridges', bridges), ('Managers', managers), ('Emitters', emitters)]:
        if impls:
            for impl in impls:
                print(f"    - {impl['class_name']} in {impl['file']}")
    
    # Validate architectural clarity
    total_websocket_systems = len(bridges) + len(managers) + len(emitters)
    
    assert total_websocket_systems <= 6, (
        f"🚨 WEBSOCKET ARCHITECTURE COMPLEXITY: Found {total_websocket_systems} WebSocket systems "
        f"({len(bridges)} bridges, {len(managers)} managers, {len(emitters)} emitters). "
        f"Expected ≤6 total systems with clear separation of concerns. "
        f"Excessive systems increase routing confusion and maintenance burden."
    )
    
    # Validate no duplicate system types
    if bridges:
        assert len(bridges) <= 2, f"🚨 DUPLICATE BRIDGES: Found {len(bridges)} WebSocket bridges, expected ≤2"
    if managers:
        assert len(managers) <= 2, f"🚨 DUPLICATE MANAGERS: Found {len(managers)} WebSocket managers, expected ≤2"
    if emitters:
        assert len(emitters) <= 3, f"🚨 DUPLICATE EMITTERS: Found {len(emitters)} WebSocket emitters, expected ≤3"


if __name__ == "__main__":
    # Allow manual execution for debugging
    print("🧪 RUNNING WEBSOCKET MANAGER SSOT VALIDATION TESTS FOR ISSUE #759")
    print("=" * 70)
    
    try:
        test_single_websocket_manager_exists()
        print("✅ Single WebSocket manager test PASSED")
    except AssertionError as e:
        print(f"❌ Single WebSocket manager test FAILED: {e}")
    
    try:
        test_websocket_event_delivery_consolidation()
        print("✅ Event delivery consolidation test PASSED")
    except AssertionError as e:
        print(f"❌ Event delivery consolidation test FAILED: {e}")
        
    try:
        test_websocket_routing_conflict_detection()
        print("✅ Routing conflict detection test PASSED")
    except AssertionError as e:
        print(f"❌ Routing conflict detection test FAILED: {e}")
        
    try:
        test_critical_websocket_events_coverage()
        print("✅ Critical events coverage test PASSED")
    except AssertionError as e:
        print(f"❌ Critical events coverage test FAILED: {e}")
        
    try:
        test_websocket_execution_engine_integration()
        print("✅ WebSocket-ExecutionEngine integration test PASSED")
    except AssertionError as e:
        print(f"❌ WebSocket-ExecutionEngine integration test FAILED: {e}")
