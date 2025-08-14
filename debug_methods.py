#!/usr/bin/env python3

"""Debug script to test DataSubAgent method availability."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.agents.data_sub_agent.agent import DataSubAgent
    print("SUCCESS: DataSubAgent imported successfully")
    print(f"DataSubAgent file location: {DataSubAgent.__module__}")
    
    # Check the actual file being loaded
    import inspect
    source_file = inspect.getfile(DataSubAgent)
    print(f"Source file: {source_file}")
    
    # Get source lines
    source_lines, start_line = inspect.getsourcelines(DataSubAgent)
    print(f"Class starts at line {start_line}, has {len(source_lines)} lines")
    print(f"Last few lines of class:")
    for i, line in enumerate(source_lines[-10:], start=len(source_lines)-9):
        print(f"  Line {start_line + i - 1}: {line.rstrip()}")
    
    # Create instance  
    agent = DataSubAgent(None, None)
    print("SUCCESS: DataSubAgent instantiated successfully")
    
    # Check methods
    methods = dir(agent)
    print(f"\nTotal methods available: {len(methods)}")
    print("All methods:")
    for method in sorted(methods):
        if not method.startswith('__'):
            print(f"  {method}")
    
    print("\nMethods containing 'handle_supervisor' or '_analyze_performance':")
    
    supervisor_methods = [m for m in methods if 'handle_supervisor' in m]
    analyze_methods = [m for m in methods if '_analyze_performance' in m]
    
    print(f"Supervisor methods: {supervisor_methods}")
    print(f"Analyze performance methods: {analyze_methods}")
    
    # Also check methods that start with analyze
    analyze_any = [m for m in methods if 'analyze' in m.lower()]
    print(f"Any analyze methods: {analyze_any}")
    
    # Check methods that contain 'performance'
    performance_methods = [m for m in methods if 'performance' in m.lower()]
    print(f"Any performance methods: {performance_methods}")
    
    # Check methods that contain 'handle'
    handle_methods = [m for m in methods if 'handle' in m.lower()]
    print(f"Any handle methods: {handle_methods}")
    
    # Test the methods exist
    if hasattr(agent, 'handle_supervisor_request'):
        print("SUCCESS: handle_supervisor_request method exists")
        print(f"Method type: {type(getattr(agent, 'handle_supervisor_request'))}")
    else:
        print("ERROR: handle_supervisor_request method NOT found")
        
    if hasattr(agent, '_analyze_performance'):
        print("SUCCESS: _analyze_performance method exists")
        print(f"Method type: {type(getattr(agent, '_analyze_performance'))}")
    else:
        print("ERROR: _analyze_performance method NOT found")
        
    if hasattr(agent, '_analyze_performance_metrics'):
        print("SUCCESS: _analyze_performance_metrics method exists")
        print(f"Method type: {type(getattr(agent, '_analyze_performance_metrics'))}")
    else:
        print("ERROR: _analyze_performance_metrics method NOT found")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()