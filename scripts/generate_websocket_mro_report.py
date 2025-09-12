#!/usr/bin/env python
"""Generate MRO (Method Resolution Order) report for WebSocket classes."""

import sys
import os
import inspect
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
from typing import Dict, List, Set, Tuple

# WebSocket classes to analyze
WEBSOCKET_CLASSES = [
    ("netra_backend.app.websocket_core.unified_manager", "UnifiedWebSocketManager"),
    ("netra_backend.app.websocket_core.unified_manager", "WebSocketConnection"),
    ("netra_backend.app.websocket_core.unified_emitter", "UnifiedWebSocketEmitter"),
    ("netra_backend.app.websocket_core.unified_emitter", "WebSocketEmitterFactory"),
    ("netra_backend.app.websocket_core.unified_emitter", "WebSocketEmitterPool"),
    ("netra_backend.app.agents.supervisor.agent_instance_factory", "UserWebSocketEmitter"),
    ("netra_backend.app.services.agent_websocket_bridge", "AgentWebSocketBridge"),
]

def get_class_methods(cls) -> Dict[str, str]:
    """Get all methods of a class with their defining class."""
    methods = {}
    for name, method in inspect.getmembers(cls, predicate=inspect.ismethod):
        if not name.startswith('_'):  # Public methods only
            defining_class = method.__self__.__class__.__name__ if hasattr(method, '__self__') else cls.__name__
            methods[name] = defining_class
    
    # Also get unbound methods and functions
    for name, func in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('__') or name in ['__init__', '__new__']:
            methods[name] = cls.__name__
    
    return methods

def get_class_attributes(cls) -> List[str]:
    """Get class attributes (excluding methods)."""
    attributes = []
    for name in dir(cls):
        if not name.startswith('_') and not callable(getattr(cls, name, None)):
            attributes.append(name)
    return attributes

def analyze_inheritance(module_path: str, class_name: str) -> Dict:
    """Analyze inheritance for a specific class."""
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        
        # Get MRO
        mro = inspect.getmro(cls)
        mro_names = [c.__name__ for c in mro]
        
        # Get methods
        methods = get_class_methods(cls)
        
        # Get attributes
        attributes = get_class_attributes(cls)
        
        # Count overridden methods
        overridden = []
        for base in mro[1:]:  # Skip the class itself
            base_methods = set(dir(base))
            for method in methods:
                if method in base_methods:
                    overridden.append((method, base.__name__))
        
        return {
            "module": module_path,
            "class": class_name,
            "mro": mro_names,
            "methods": methods,
            "attributes": attributes,
            "overridden": overridden,
            "base_classes": [c.__name__ for c in cls.__bases__] if hasattr(cls, '__bases__') else [],
        }
    except Exception as e:
        return {
            "module": module_path,
            "class": class_name,
            "error": str(e)
        }

def generate_mro_report():
    """Generate comprehensive MRO report for WebSocket classes."""
    report = []
    report.append("# WebSocket Classes MRO Analysis Report")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("\n## Executive Summary")
    report.append("This report analyzes the Method Resolution Order (MRO) of WebSocket classes ")
    report.append("to identify consolidation opportunities and prevent method shadowing issues.\n")
    
    # Analyze each class
    analysis_results = []
    for module_path, class_name in WEBSOCKET_CLASSES:
        result = analyze_inheritance(module_path, class_name)
        analysis_results.append(result)
    
    # Generate detailed analysis
    report.append("## Detailed Class Analysis\n")
    
    for result in analysis_results:
        if "error" in result:
            report.append(f"###  FAIL:  {result['class']}")
            report.append(f"- **Error**: {result['error']}\n")
            continue
        
        report.append(f"### {result['class']}")
        report.append(f"- **Module**: `{result['module']}`")
        report.append(f"- **Direct Base Classes**: {', '.join(result['base_classes']) if result['base_classes'] else 'None (object)'}")
        report.append(f"- **MRO**: {'  ->  '.join(result['mro'])}")
        report.append(f"- **Method Count**: {len(result['methods'])}")
        report.append(f"- **Attribute Count**: {len(result['attributes'])}")
        
        if result['overridden']:
            report.append(f"- **Overridden Methods**: {len(result['overridden'])}")
            for method, base in result['overridden'][:5]:  # Show first 5
                report.append(f"  - `{method}` (from {base})")
        
        # Show key methods
        if result['methods']:
            report.append("- **Key Methods**:")
            critical_methods = ['emit_critical_event', 'send_agent_update', 'notify_agent_started',
                              'emit_agent_started', 'emit_agent_thinking', 'emit_tool_executing',
                              'emit_tool_completed', 'emit_agent_completed']
            
            for method in critical_methods:
                if method in result['methods']:
                    report.append(f"  -  PASS:  `{method}`")
        
        report.append("")
    
    # Consolidation opportunities
    report.append("## Consolidation Opportunities\n")
    
    # Find duplicate method patterns
    all_methods = {}
    for result in analysis_results:
        if "error" not in result:
            for method in result.get('methods', {}):
                if method not in all_methods:
                    all_methods[method] = []
                all_methods[method].append(result['class'])
    
    duplicates = {m: classes for m, classes in all_methods.items() if len(classes) > 1}
    
    if duplicates:
        report.append("### Duplicate Method Patterns")
        report.append("These methods appear in multiple classes (consolidation candidates):\n")
        for method, classes in sorted(duplicates.items()):
            if not method.startswith('__'):  # Skip magic methods
                report.append(f"- `{method}`: {', '.join(classes)}")
    
    # Check for critical events
    report.append("\n### Critical Event Implementation Status")
    critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 
                      'tool_completed', 'agent_completed']
    
    for event in critical_events:
        emit_method = f"emit_{event}"
        notify_method = f"notify_{event}"
        classes_with_event = []
        
        for result in analysis_results:
            if "error" not in result:
                methods = result.get('methods', {})
                if emit_method in methods or notify_method in methods:
                    classes_with_event.append(result['class'])
        
        if classes_with_event:
            report.append(f"-  PASS:  `{event}`: {', '.join(classes_with_event)}")
        else:
            report.append(f"-  FAIL:  `{event}`: NOT FOUND")
    
    # Recommendations
    report.append("\n## Recommendations\n")
    report.append("1. **UnifiedWebSocketManager** is the SSOT for WebSocket management")
    report.append("2. **UnifiedWebSocketEmitter** is the SSOT for event emission")
    report.append("3. **UserWebSocketEmitter** in agent_instance_factory should delegate to UnifiedWebSocketEmitter")
    report.append("4. **AgentWebSocketBridge** correctly uses the bridge pattern for integration")
    report.append("5. All 5 critical events MUST be preserved during consolidation")
    
    return "\n".join(report)

if __name__ == "__main__":
    report = generate_mro_report()
    
    # Save report
    report_path = Path(__file__).parent.parent / "reports" / f"websocket_mro_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"MRO Report generated: {report_path}")
    print("\nReport Preview:")
    print("=" * 80)
    print(report[:2000].encode('ascii', errors='ignore').decode())  # Show first 2000 chars