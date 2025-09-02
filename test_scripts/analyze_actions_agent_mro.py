#!/usr/bin/env python3
"""
MRO Analysis Script for ActionsAgent Golden Alignment

This script performs comprehensive Method Resolution Order analysis for:
- ActionsToMeetGoalsSubAgent
- BaseAgent hierarchy
- Related infrastructure components

Generated for: CRITICAL_REMEDIATION_20250823
Date: 2025-09-02
"""

import sys
import os
import inspect
from typing import Dict, List, Any, Set
import importlib.util

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def load_module_from_file(file_path: str, module_name: str):
    """Load a module from file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def get_mro_hierarchy(cls) -> Dict[str, Any]:
    """Get comprehensive MRO information for a class"""
    mro = inspect.getmro(cls)
    hierarchy = {
        'class_name': cls.__name__,
        'module': getattr(cls, '__module__', 'unknown'),
        'mro_chain': [c.__name__ for c in mro],
        'mro_modules': [getattr(c, '__module__', 'unknown') for c in mro],
        'method_overrides': {},
        'property_overrides': {},
        'inheritance_depth': len(mro)
    }
    
    # Analyze method overrides
    for i, base_cls in enumerate(mro[1:], 1):  # Skip the class itself
        for name, method in inspect.getmembers(base_cls, predicate=inspect.ismethod):
            if hasattr(cls, name) and name not in hierarchy['method_overrides']:
                hierarchy['method_overrides'][name] = {
                    'defined_in': base_cls.__name__,
                    'overridden_at_level': i,
                    'source_module': getattr(base_cls, '__module__', 'unknown')
                }
    
    # Analyze function overrides (unbound methods)
    for i, base_cls in enumerate(mro[1:], 1):
        for name, func in inspect.getmembers(base_cls, predicate=inspect.isfunction):
            if hasattr(cls, name) and name not in hierarchy['method_overrides']:
                hierarchy['method_overrides'][name] = {
                    'defined_in': base_cls.__name__,
                    'overridden_at_level': i,
                    'source_module': getattr(base_cls, '__module__', 'unknown')
                }
    
    # Analyze property overrides
    for i, base_cls in enumerate(mro[1:], 1):
        for name, prop in inspect.getmembers(base_cls):
            if isinstance(prop, property) and hasattr(cls, name) and name not in hierarchy['property_overrides']:
                hierarchy['property_overrides'][name] = {
                    'defined_in': base_cls.__name__,
                    'overridden_at_level': i,
                    'source_module': getattr(base_cls, '__module__', 'unknown')
                }
    
    return hierarchy

def analyze_method_resolution_paths(cls, methods_of_interest: List[str]) -> Dict[str, Dict]:
    """Analyze specific method resolution paths"""
    resolution_paths = {}
    
    for method_name in methods_of_interest:
        if hasattr(cls, method_name):
            method = getattr(cls, method_name)
            resolution_paths[method_name] = {
                'resolved_to': None,
                'resolution_path': [],
                'is_overridden': False,
                'source_class': None,
                'source_module': None
            }
            
            # Walk the MRO to find where this method is defined
            for mro_class in inspect.getmro(cls):
                if method_name in mro_class.__dict__:
                    resolution_paths[method_name]['resolved_to'] = mro_class.__name__
                    resolution_paths[method_name]['source_class'] = mro_class.__name__
                    resolution_paths[method_name]['source_module'] = getattr(mro_class, '__module__', 'unknown')
                    resolution_paths[method_name]['is_overridden'] = (mro_class != cls)
                    break
            
            # Build resolution path
            for mro_class in inspect.getmro(cls):
                if hasattr(mro_class, method_name):
                    resolution_paths[method_name]['resolution_path'].append({
                        'class': mro_class.__name__,
                        'module': getattr(mro_class, '__module__', 'unknown'),
                        'has_method': method_name in mro_class.__dict__
                    })
    
    return resolution_paths

def find_duplicate_methods(classes: List[type]) -> Dict[str, List[Dict]]:
    """Find duplicate method implementations across classes"""
    method_implementations = {}
    duplicates = {}
    
    for cls in classes:
        class_methods = inspect.getmembers(cls, predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x))
        for method_name, method in class_methods:
            if method_name.startswith('_') and not method_name.startswith('__'):
                # Focus on protected methods that might be duplicated
                continue
            
            if method_name not in method_implementations:
                method_implementations[method_name] = []
            
            # Get method source if possible
            try:
                source = inspect.getsource(method)
                source_hash = hash(source.strip())
            except (OSError, TypeError):
                source = "Source not available"
                source_hash = None
            
            method_implementations[method_name].append({
                'class': cls.__name__,
                'module': getattr(cls, '__module__', 'unknown'),
                'source_hash': source_hash,
                'source_preview': source[:200] + "..." if len(source) > 200 else source
            })
    
    # Find duplicates
    for method_name, implementations in method_implementations.items():
        if len(implementations) > 1:
            # Check for potential duplicates by source hash
            hash_groups = {}
            for impl in implementations:
                if impl['source_hash']:
                    if impl['source_hash'] not in hash_groups:
                        hash_groups[impl['source_hash']] = []
                    hash_groups[impl['source_hash']].append(impl)
            
            for hash_value, group in hash_groups.items():
                if len(group) > 1:
                    if method_name not in duplicates:
                        duplicates[method_name] = []
                    duplicates[method_name].extend(group)
    
    return duplicates

def main():
    """Main analysis function"""
    print("=== MRO Analysis for ActionsAgent Golden Alignment ===\n")
    
    try:
        # Import the classes
        sys.path.insert(0, os.path.join(project_root, 'netra_backend'))
        
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        from netra_backend.app.agents.base_agent import BaseAgent
        
        print("SUCCESS: Successfully imported ActionsToMeetGoalsSubAgent and BaseAgent\n")
        
        # 1. Analyze ActionsToMeetGoalsSubAgent MRO
        print("=== 1. ACTIONSAGENT MRO HIERARCHY ===")
        actions_hierarchy = get_mro_hierarchy(ActionsToMeetGoalsSubAgent)
        
        print(f"Class: {actions_hierarchy['class_name']}")
        print(f"Module: {actions_hierarchy['module']}")
        print(f"Inheritance Depth: {actions_hierarchy['inheritance_depth']}")
        print("\nMRO Chain:")
        for i, (cls_name, module) in enumerate(zip(actions_hierarchy['mro_chain'], actions_hierarchy['mro_modules'])):
            print(f"  {i}: {cls_name} ({module})")
        
        print(f"\nMethod Overrides ({len(actions_hierarchy['method_overrides'])}):")
        for method, info in sorted(actions_hierarchy['method_overrides'].items()):
            print(f"  - {method}: from {info['defined_in']} (level {info['overridden_at_level']})")
        
        print(f"\nProperty Overrides ({len(actions_hierarchy['property_overrides'])}):")
        for prop, info in sorted(actions_hierarchy['property_overrides'].items()):
            print(f"  - {prop}: from {info['defined_in']} (level {info['overridden_at_level']})")
        
        # 2. Analyze BaseAgent MRO
        print("\n=== 2. BASEAGENT MRO HIERARCHY ===")
        base_hierarchy = get_mro_hierarchy(BaseAgent)
        
        print(f"Class: {base_hierarchy['class_name']}")
        print(f"Module: {base_hierarchy['module']}")
        print(f"Inheritance Depth: {base_hierarchy['inheritance_depth']}")
        print("\nMRO Chain:")
        for i, (cls_name, module) in enumerate(zip(base_hierarchy['mro_chain'], base_hierarchy['mro_modules'])):
            print(f"  {i}: {cls_name} ({module})")
        
        # 3. Analyze critical method resolution paths
        print("\n=== 3. CRITICAL METHOD RESOLUTION PATHS ===")
        critical_methods = [
            'execute', 'execute_core_logic', 'validate_preconditions',
            'emit_thinking', 'emit_tool_executing', 'emit_tool_completed',
            'emit_agent_started', 'emit_agent_completed', 'emit_progress',
            'send_status_update', '_send_update', 'set_websocket_bridge',
            'get_health_status', 'shutdown', 'execute_with_reliability'
        ]
        
        resolution_paths = analyze_method_resolution_paths(ActionsToMeetGoalsSubAgent, critical_methods)
        
        for method_name, path_info in resolution_paths.items():
            print(f"\n{method_name}:")
            print(f"  Resolved to: {path_info['resolved_to']} ({path_info['source_module']})")
            print(f"  Overridden: {path_info['is_overridden']}")
            if path_info['resolution_path']:
                print("  Resolution path:")
                for step in path_info['resolution_path']:
                    marker = "YES" if step['has_method'] else "NO "
                    print(f"    {marker} {step['class']} ({step['module']})")
        
        # 4. Find SSOT violations
        print("\n=== 4. POTENTIAL SSOT VIOLATIONS ===")
        
        # Check for duplicate infrastructure code
        infrastructure_methods = [
            '_send_update', 'send_status_update', 'emit_thinking', 'emit_progress',
            'get_health_status', 'execute_with_reliability', '_create_reliability_manager',
            '_setup_modern_execution_infrastructure', '_execute_with_modern_pattern'
        ]
        
        for method in infrastructure_methods:
            if hasattr(ActionsToMeetGoalsSubAgent, method):
                method_obj = getattr(ActionsToMeetGoalsSubAgent, method)
                # Check if it's defined in ActionsToMeetGoalsSubAgent vs BaseAgent
                for cls in inspect.getmro(ActionsToMeetGoalsSubAgent):
                    if method in cls.__dict__:
                        if cls == ActionsToMeetGoalsSubAgent and cls != BaseAgent:
                            print(f"WARNING SSOT VIOLATION: '{method}' implemented in ActionsToMeetGoalsSubAgent")
                            print(f"    Should inherit from BaseAgent infrastructure")
                        break
        
        # 5. WebSocket Integration Analysis
        print("\n=== 5. WEBSOCKET INTEGRATION ANALYSIS ===")
        websocket_methods = [
            'emit_thinking', 'emit_tool_executing', 'emit_tool_completed',
            'emit_agent_started', 'emit_agent_completed', 'emit_progress',
            'emit_error', 'set_websocket_bridge', 'has_websocket_context'
        ]
        
        websocket_resolution = analyze_method_resolution_paths(ActionsToMeetGoalsSubAgent, websocket_methods)
        
        print("WebSocket Methods Resolution:")
        for method_name, path_info in websocket_resolution.items():
            source = path_info.get('resolved_to', 'NOT_FOUND')
            if source == 'BaseAgent':
                status = "COMPLIANT"
            elif source == 'ActionsToMeetGoalsSubAgent':
                status = "WARNING POTENTIAL VIOLATION"
            else:
                status = "ERROR MISSING"
            print(f"  {method_name}: {source} - {status}")
        
        print(f"\n=== ANALYSIS COMPLETE ===")
        print(f"Analyzed {actions_hierarchy['inheritance_depth']} classes in MRO")
        print(f"Found {len(actions_hierarchy['method_overrides'])} method overrides")
        print(f"Found {len(actions_hierarchy['property_overrides'])} property overrides")
        
        return {
            'actions_hierarchy': actions_hierarchy,
            'base_hierarchy': base_hierarchy,
            'resolution_paths': resolution_paths,
            'websocket_resolution': websocket_resolution
        }
        
    except ImportError as e:
        print(f"ERROR Import Error: {e}")
        print("Could not import required classes. Check PYTHONPATH and dependencies.")
        return None
    except Exception as e:
        print(f"ERROR Analysis Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = main()