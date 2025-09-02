#!/usr/bin/env python3
"""Simple MRO analysis script for BaseAgent hierarchy"""

import inspect
import sys
import os
from typing import Type, Any, List, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def get_mro_analysis():
    """Get MRO analysis for BaseAgent and its subclasses"""
    try:
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Get BaseAgent MRO
        print("=== BaseAgent MRO ===")
        mro = inspect.getmro(BaseAgent)
        for i, cls in enumerate(mro):
            print(f"{i}: {cls.__module__}.{cls.__name__}")
        print()
        
        # Get all BaseAgent methods
        base_methods = {}
        for name in dir(BaseAgent):
            if not name.startswith('__'):
                method = getattr(BaseAgent, name)
                if callable(method):
                    base_methods[name] = method
        
        print("=== BaseAgent Public Methods ===")
        for method_name in sorted(base_methods.keys()):
            print(f"- {method_name}")
        print()
        
        # Try to analyze specific subclasses
        subclasses_to_analyze = [
            ("SupervisorAgent", "netra_backend.app.agents.supervisor_consolidated", "SupervisorAgent"),
            ("ValidatorAgent", "netra_backend.app.agents.validator", "ValidatorAgent"), 
            ("AnalystAgent", "netra_backend.app.agents.analyst", "AnalystAgent"),
            ("SyntheticDataSubAgent", "netra_backend.app.agents.synthetic_data_sub_agent", "SyntheticDataSubAgent")
        ]
        
        for class_name, module_name, class_attr in subclasses_to_analyze:
            try:
                print(f"=== {class_name} Analysis ===")
                module = __import__(module_name, fromlist=[class_attr])
                cls = getattr(module, class_attr)
                
                # Get MRO
                print("MRO:")
                mro = inspect.getmro(cls)
                for i, base in enumerate(mro):
                    print(f"  {i}: {base.__module__}.{base.__name__}")
                
                # Check for method overrides
                print("Method overrides:")
                overrides = []
                for name in dir(cls):
                    if name in base_methods and not name.startswith('_'):
                        cls_method = getattr(cls, name)
                        base_method = base_methods[name]
                        if cls_method != base_method and callable(cls_method):
                            overrides.append(name)
                
                if overrides:
                    for override in sorted(overrides):
                        print(f"  - {override}")
                else:
                    print("  - No method overrides detected")
                print()
                
            except Exception as e:
                print(f"Failed to analyze {class_name}: {e}")
                print()
                continue
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = get_mro_analysis()
    sys.exit(0 if success else 1)