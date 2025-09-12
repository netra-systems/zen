"""MRO Analysis for SupervisorAgent

This script analyzes the Method Resolution Order and inheritance patterns
for the SupervisorAgent to ensure proper golden pattern compliance.
"""

import inspect
import importlib
from datetime import datetime
from typing import Dict, List, Set, Any

# Import the SupervisorAgent and BaseAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.base_agent import BaseAgent


def analyze_mro(cls) -> Dict[str, Any]:
    """Analyze the Method Resolution Order for a class."""
    mro = inspect.getmro(cls)
    
    # Get all methods and their origins
    methods = {}
    overridden_methods = {}
    
    for method_name in dir(cls):
        if not method_name.startswith('_'):
            try:
                method = getattr(cls, method_name)
                if callable(method):
                    # Find which class in MRO defines this method
                    for base in mro:
                        if method_name in base.__dict__:
                            methods[method_name] = base.__name__
                            # Check if it's overridden
                            if base != cls and method_name in cls.__dict__:
                                overridden_methods[method_name] = {
                                    'original': base.__name__,
                                    'overridden_in': cls.__name__
                                }
                            break
            except:
                pass
    
    # Get private methods that are important
    important_private = ['__init__', '_init_business_components', 
                         '_init_legacy_compatibility_components', 
                         '_run_supervisor_workflow', '_run_hooks']
    
    private_methods = {}
    for method_name in important_private:
        if hasattr(cls, method_name):
            for base in mro:
                if method_name in base.__dict__:
                    private_methods[method_name] = base.__name__
                    break
    
    return {
        'class_name': cls.__name__,
        'mro': [c.__name__ for c in mro],
        'public_methods': methods,
        'overridden_methods': overridden_methods,
        'private_methods': private_methods,
        'total_methods': len(methods),
        'total_overridden': len(overridden_methods)
    }


def check_method_shadowing(cls) -> List[str]:
    """Check for potential method shadowing issues."""
    issues = []
    mro = inspect.getmro(cls)
    
    # Check for methods that might shadow important base methods
    critical_methods = [
        'execute', 'execute_modern', 'execute_core_logic',
        'validate_preconditions', 'emit_thinking', 'emit_progress',
        'emit_tool_executing', 'emit_tool_completed'
    ]
    
    for method in critical_methods:
        if hasattr(cls, method):
            # Check if it's defined in cls or inherited
            if method in cls.__dict__:
                # Method is overridden in cls
                for base in mro[1:]:  # Skip cls itself
                    if method in base.__dict__:
                        issues.append(f"Method '{method}' shadows {base.__name__}.{method}")
                        break
    
    return issues


def analyze_websocket_patterns(cls) -> Dict[str, Any]:
    """Analyze WebSocket event emission patterns."""
    source_code = inspect.getsource(cls)
    
    patterns = {
        'uses_emit_methods': False,
        'uses_direct_bridge': False,
        'emit_calls': [],
        'bridge_calls': []
    }
    
    # Check for emit method usage
    emit_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing', 
                   'emit_tool_completed', 'emit_error']
    
    for method in emit_methods:
        if f'self.{method}' in source_code:
            patterns['uses_emit_methods'] = True
            patterns['emit_calls'].append(method)
    
    # Check for direct bridge usage
    bridge_patterns = ['bridge.notify', 'websocket_bridge.notify', 
                       'self.websocket_bridge.notify']
    
    for pattern in bridge_patterns:
        if pattern in source_code:
            patterns['uses_direct_bridge'] = True
            patterns['bridge_calls'].append(pattern)
    
    return patterns


def generate_report():
    """Generate comprehensive MRO analysis report."""
    report = []
    report.append("# MRO Analysis Report: SupervisorAgent")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n---\n")
    
    # Analyze SupervisorAgent
    supervisor_analysis = analyze_mro(SupervisorAgent)
    
    report.append("## 1. Inheritance Hierarchy\n")
    report.append("### Method Resolution Order (MRO):")
    for i, cls_name in enumerate(supervisor_analysis['mro']):
        indent = "  " * i
        report.append(f"{indent}- {cls_name}")
    
    report.append(f"\n**Total Classes in MRO:** {len(supervisor_analysis['mro'])}")
    
    # Method Analysis
    report.append("\n## 2. Method Analysis\n")
    report.append(f"**Total Public Methods:** {supervisor_analysis['total_methods']}")
    report.append(f"**Overridden Methods:** {supervisor_analysis['total_overridden']}")
    
    if supervisor_analysis['overridden_methods']:
        report.append("\n### Overridden Methods:")
        for method, info in supervisor_analysis['overridden_methods'].items():
            report.append(f"- `{method}`: {info['original']}  ->  {info['overridden_in']}")
    
    # Critical Methods
    report.append("\n### Critical Method Locations:")
    critical = ['execute', 'execute_modern', 'execute_core_logic', 
                'validate_preconditions', 'run']
    
    for method in critical:
        if method in supervisor_analysis['public_methods']:
            report.append(f"- `{method}`: {supervisor_analysis['public_methods'][method]}")
    
    # WebSocket Pattern Analysis
    report.append("\n## 3. WebSocket Event Pattern Analysis\n")
    ws_patterns = analyze_websocket_patterns(SupervisorAgent)
    
    report.append(f"**Uses BaseAgent emit methods:** {' PASS:  Yes' if ws_patterns['uses_emit_methods'] else ' FAIL:  No'}")
    report.append(f"**Uses direct bridge calls:** {' FAIL:  Yes (VIOLATION)' if ws_patterns['uses_direct_bridge'] else ' PASS:  No'}")
    
    if ws_patterns['emit_calls']:
        report.append("\n### Emit Methods Used:")
        for method in ws_patterns['emit_calls']:
            report.append(f"- `{method}()`")
    
    if ws_patterns['bridge_calls']:
        report.append("\n### Direct Bridge Calls (VIOLATIONS):")
        for call in ws_patterns['bridge_calls']:
            report.append(f"- `{call}`  WARNING: [U+FE0F]")
    
    # Method Shadowing Check
    report.append("\n## 4. Method Shadowing Analysis\n")
    shadowing_issues = check_method_shadowing(SupervisorAgent)
    
    if shadowing_issues:
        report.append("###  WARNING: [U+FE0F] Potential Shadowing Issues:")
        for issue in shadowing_issues:
            report.append(f"- {issue}")
    else:
        report.append(" PASS:  No method shadowing issues detected")
    
    # Private Method Analysis
    report.append("\n## 5. Important Private Methods\n")
    for method, location in supervisor_analysis['private_methods'].items():
        report.append(f"- `{method}`: {location}")
    
    # Compliance Summary
    report.append("\n## 6. Golden Pattern Compliance\n")
    
    compliance_checks = {
        "Inherits from BaseAgent": "BaseAgent" in supervisor_analysis['mro'],
        "Uses emit methods": ws_patterns['uses_emit_methods'],
        "No direct bridge calls": not ws_patterns['uses_direct_bridge'],
        "Implements execute_core_logic": 'execute_core_logic' in supervisor_analysis['public_methods'],
        "Implements validate_preconditions": 'validate_preconditions' in supervisor_analysis['public_methods'],
        "No critical shadowing": len(shadowing_issues) == 0
    }
    
    compliance_score = sum(1 for v in compliance_checks.values() if v) / len(compliance_checks) * 100
    
    report.append(f"\n**Overall Compliance Score: {compliance_score:.1f}%**\n")
    
    for check, passed in compliance_checks.items():
        status = " PASS: " if passed else " FAIL: "
        report.append(f"- {status} {check}")
    
    # Recommendations
    report.append("\n## 7. Recommendations\n")
    
    if not ws_patterns['uses_emit_methods']:
        report.append("- **CRITICAL:** Implement WebSocket events using BaseAgent emit methods")
    
    if ws_patterns['uses_direct_bridge']:
        report.append("- **CRITICAL:** Remove all direct bridge notifications")
    
    if shadowing_issues:
        report.append("- **WARNING:** Review method shadowing for potential issues")
    
    if supervisor_analysis['total_overridden'] > 5:
        report.append("- **INFO:** Consider reducing method overrides for simpler inheritance")
    
    report.append("\n---\n")
    report.append(f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(report)


if __name__ == "__main__":
    report = generate_report()
    
    # Save report to file
    report_file = "SUPERVISOR_MRO_ANALYSIS_REPORT.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"MRO Analysis Report generated: {report_file}")
    print("\nSummary:")
    print("=" * 50)
    
    # Quick summary
    supervisor_analysis = analyze_mro(SupervisorAgent)
    ws_patterns = analyze_websocket_patterns(SupervisorAgent)
    
    print(f"MRO Chain Length: {len(supervisor_analysis['mro'])}")
    print(f"Total Methods: {supervisor_analysis['total_methods']}")
    print(f"Overridden Methods: {supervisor_analysis['total_overridden']}")
    print(f"Uses Emit Methods: {'Yes' if ws_patterns['uses_emit_methods'] else 'No'}")
    print(f"Uses Direct Bridge: {'No' if ws_patterns['uses_direct_bridge'] else 'Yes'}")