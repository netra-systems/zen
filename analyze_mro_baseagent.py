#!/usr/bin/env python3
"""MRO Analysis Script for BaseAgent inheritance patterns

CRITICAL: Generate comprehensive Method Resolution Order analysis for BaseAgent refactoring
"""

import inspect
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import os

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_all_baseagent_subclasses():
    """Find all classes that inherit from BaseAgent"""
    
    # Import BaseAgent first
    from netra_backend.app.agents.base_agent import BaseAgent
    
    # List of known agent modules based on our grep results
    agent_modules = [
        'netra_backend.app.agents.actions_to_meet_goals_sub_agent',
        'netra_backend.app.agents.analyst', 
        'netra_backend.app.agents.data_helper_agent',
        'netra_backend.app.agents.example_message_processor',
        'netra_backend.app.agents.enhanced_execution_agent',
        'netra_backend.app.agents.data_sub_agent.agent',
        'netra_backend.app.agents.corpus_admin.agent',
        'netra_backend.app.agents.data_sub_agent.agent_core',
        'netra_backend.app.agents.demo_service.core',
        'netra_backend.app.agents.demo_service.reporting',
        'netra_backend.app.agents.demo_service.triage',
        'netra_backend.app.agents.domain_experts.base_expert',
        'netra_backend.app.agents.github_analyzer.agent',
        'netra_backend.app.agents.optimizations_core_sub_agent',
        'netra_backend.app.agents.reporting_sub_agent',
        'netra_backend.app.agents.synthetic_data_sub_agent',
        'netra_backend.app.agents.data_sub_agent.data_sub_agent',
        'netra_backend.app.agents.supply_researcher.agent',
        'netra_backend.app.agents.synthetic_data_sub_agent_modern',
        'netra_backend.app.agents.supervisor_consolidated',
        'netra_backend.app.agents.triage_sub_agent',
        'netra_backend.app.agents.validation_sub_agent',
        'netra_backend.app.agents.triage_sub_agent.agent',
        'netra_backend.app.agents.validator',
    ]
    
    agent_classes = []
    failed_imports = []
    
    for module_path in agent_modules:
        try:
            module = importlib.import_module(module_path)
            # Find all classes in the module that inherit from BaseAgent
            for name in dir(module):
                obj = getattr(module, name)
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseAgent) and 
                    obj != BaseAgent):
                    agent_classes.append((obj, module_path))
        except Exception as e:
            failed_imports.append((module_path, str(e)))
    
    return agent_classes, failed_imports

def analyze_mro_for_class(cls) -> Dict[str, Any]:
    """Analyze Method Resolution Order for a given class"""
    mro = inspect.getmro(cls)
    
    analysis = {
        'class_name': cls.__name__,
        'module': cls.__module__,
        'mro_chain': [c.__name__ for c in mro],
        'mro_modules': [c.__module__ for c in mro],
        'base_classes': [base.__name__ for base in cls.__bases__],
        'methods_defined': {},
        'method_resolution_paths': {},
        'potential_conflicts': []
    }
    
    # Analyze methods defined at each level
    for base in mro:
        methods_at_level = []
        for name in dir(base):
            if (not name.startswith('_') and 
                callable(getattr(base, name)) and 
                name in base.__dict__):  # Only methods defined in this class
                methods_at_level.append(name)
        analysis['methods_defined'][base.__name__] = methods_at_level
    
    # Check for method conflicts/shadowing
    all_methods = set()
    for base in reversed(mro):  # Start from most base class
        for method_name in dir(base):
            if (not method_name.startswith('_') and 
                callable(getattr(base, method_name)) and
                method_name in base.__dict__):
                
                if method_name in all_methods:
                    # This method shadows a parent method
                    resolution_path = []
                    for check_base in mro:
                        if method_name in check_base.__dict__:
                            resolution_path.append(check_base.__name__)
                    
                    analysis['method_resolution_paths'][method_name] = resolution_path
                    
                    if len(resolution_path) > 1:
                        analysis['potential_conflicts'].append({
                            'method': method_name,
                            'resolution_path': resolution_path,
                            'resolved_to': resolution_path[0]
                        })
                
                all_methods.add(method_name)
    
    return analysis

def check_for_diamond_inheritance(agent_classes):
    """Check for diamond inheritance patterns"""
    diamond_patterns = []
    
    for cls, module_path in agent_classes:
        mro = inspect.getmro(cls)
        
        # Look for repeated base classes that aren't object
        seen_classes = set()
        for base in mro:
            if base != object:
                if base in seen_classes:
                    diamond_patterns.append({
                        'agent': cls.__name__,
                        'repeated_class': base.__name__,
                        'mro': [c.__name__ for c in mro]
                    })
                seen_classes.add(base)
    
    return diamond_patterns

def analyze_websocket_integration():
    """Analyze WebSocket integration patterns"""
    from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
    
    # Check if WebSocketBridgeAdapter uses inheritance
    mro = inspect.getmro(WebSocketBridgeAdapter)
    
    analysis = {
        'websocket_adapter_mro': [c.__name__ for c in mro],
        'is_composition': len(mro) == 2,  # Should just be WebSocketBridgeAdapter + object
        'integration_pattern': 'composition' if len(mro) == 2 else 'inheritance'
    }
    
    return analysis

def generate_mro_report():
    """Generate comprehensive MRO report"""
    print("Starting BaseAgent MRO Analysis...")
    
    # Get all BaseAgent subclasses
    agent_classes, failed_imports = get_all_baseagent_subclasses()
    
    print(f"Found {len(agent_classes)} agent classes")
    if failed_imports:
        print(f"Failed to import {len(failed_imports)} modules")
    
    # Analyze each class
    all_analyses = []
    for cls, module_path in agent_classes:
        try:
            analysis = analyze_mro_for_class(cls)
            all_analyses.append(analysis)
        except Exception as e:
            print(f"Failed to analyze {cls.__name__}: {e}")
    
    # Check for diamond inheritance
    diamond_patterns = check_for_diamond_inheritance(agent_classes)
    
    # Analyze WebSocket integration
    websocket_analysis = analyze_websocket_integration()
    
    return {
        'total_classes': len(agent_classes),
        'failed_imports': failed_imports,
        'class_analyses': all_analyses,
        'diamond_patterns': diamond_patterns,
        'websocket_integration': websocket_analysis,
        'summary': {
            'uses_single_inheritance': all(len(analysis['base_classes']) == 1 for analysis in all_analyses),
            'common_base': 'BaseAgent',
            'inheritance_depth': max(len(analysis['mro_chain']) for analysis in all_analyses),
            'total_conflicts': sum(len(analysis['potential_conflicts']) for analysis in all_analyses)
        }
    }

if __name__ == "__main__":
    try:
        report = generate_mro_report()
        
        print("\n" + "="*80)
        print("BASEAGENT MRO ANALYSIS REPORT")
        print("="*80)
        
        print(f"\nTotal Classes Analyzed: {report['total_classes']}")
        print(f"Failed Imports: {len(report['failed_imports'])}")
        print(f"Uses Single Inheritance: {report['summary']['uses_single_inheritance']}")
        print(f"Maximum Inheritance Depth: {report['summary']['inheritance_depth']}")
        print(f"Total Method Conflicts: {report['summary']['total_conflicts']}")
        
        if report['failed_imports']:
            print("\nFAILED IMPORTS:")
            for module, error in report['failed_imports']:
                print(f"  - {module}: {error}")
        
        print(f"\nDiamond Patterns Found: {len(report['diamond_patterns'])}")
        for pattern in report['diamond_patterns']:
            print(f"  - {pattern}")
        
        print(f"\nWebSocket Integration: {report['websocket_integration']['integration_pattern']}")
        
        print("\nCLASS DETAILS:")
        for analysis in report['class_analyses']:
            print(f"\n{analysis['class_name']} (from {analysis['module']}):")
            print(f"  MRO: {' -> '.join(analysis['mro_chain'])}")
            print(f"  Base Classes: {analysis['base_classes']}")
            
            if analysis['potential_conflicts']:
                print(f"  Method Conflicts: {len(analysis['potential_conflicts'])}")
                for conflict in analysis['potential_conflicts']:
                    print(f"    - {conflict['method']}: {' -> '.join(conflict['resolution_path'])}")
        
        # Save detailed report to a variable for external access
        import json
        with open('mro_analysis_raw.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\nDetailed JSON report saved to: mro_analysis_raw.json")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()