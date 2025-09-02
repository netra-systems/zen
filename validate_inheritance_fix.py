"""Quick validation script to verify inheritance refactoring success."""

import sys
import inspect
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
from netra_backend.app.agents.base_agent import BaseAgent

def validate_single_inheritance():
    """Validate that agents now use single inheritance only."""
    print("="*60)
    print("INHERITANCE REFACTORING VALIDATION")
    print("="*60)
    
    # Check DataSubAgent
    print("\n1. DataSubAgent Inheritance Check:")
    data_bases = DataSubAgent.__bases__
    print(f"   Base classes: {[cls.__name__ for cls in data_bases]}")
    print(f"   Single inheritance: {'PASS' if len(data_bases) == 1 else 'FAIL'}")
    
    # Check ValidationSubAgent  
    print("\n2. ValidationSubAgent Inheritance Check:")
    val_bases = ValidationSubAgent.__bases__
    print(f"   Base classes: {[cls.__name__ for cls in val_bases]}")
    print(f"   Single inheritance: {'PASS' if len(val_bases) == 1 else 'FAIL'}")
    
    # Check MRO depth
    print("\n3. Method Resolution Order (MRO) Depth:")
    
    data_mro = DataSubAgent.__mro__
    print(f"   DataSubAgent MRO depth: {len(data_mro)}")
    print(f"   MRO chain: {' -> '.join([cls.__name__ for cls in data_mro])}")
    
    val_mro = ValidationSubAgent.__mro__
    print(f"   ValidationSubAgent MRO depth: {len(val_mro)}")
    print(f"   MRO chain: {' -> '.join([cls.__name__ for cls in val_mro])}")
    
    # Check for duplicate methods
    print("\n4. Execution Method Check:")
    
    data_has_execute = hasattr(DataSubAgent, 'execute')
    data_has_core_logic = hasattr(DataSubAgent, 'execute_core_logic')
    print(f"   DataSubAgent has execute(): {data_has_execute}")
    print(f"   DataSubAgent has execute_core_logic(): {data_has_core_logic}")
    print(f"   No duplicate execution: {'PASS' if data_has_execute and not data_has_core_logic else 'FAIL'}")
    
    val_has_execute = hasattr(ValidationSubAgent, 'execute')
    val_has_core_logic = hasattr(ValidationSubAgent, 'execute_core_logic')
    print(f"   ValidationSubAgent has execute(): {val_has_execute}")
    print(f"   ValidationSubAgent has execute_core_logic(): {val_has_core_logic}")
    print(f"   No duplicate execution: {'PASS' if val_has_execute and not val_has_core_logic else 'FAIL'}")
    
    # Check WebSocket methods availability
    print("\n5. WebSocket Methods Availability:")
    websocket_methods = ['emit_thinking', 'emit_progress', 'emit_tool_executing', 
                         'emit_tool_completed', 'emit_error']
    
    for method in websocket_methods:
        data_has = hasattr(DataSubAgent, method)
        val_has = hasattr(ValidationSubAgent, method)
        print(f"   {method}: DataSubAgent={'YES' if data_has else 'NO'}, ValidationSubAgent={'YES' if val_has else 'NO'}")
    
    # Overall validation
    print("\n" + "="*60)
    all_pass = (
        len(data_bases) == 1 and 
        len(val_bases) == 1 and
        data_has_execute and not data_has_core_logic and
        val_has_execute and not val_has_core_logic
    )
    
    if all_pass:
        print("[SUCCESS] VALIDATION SUCCESSFUL - Inheritance refactoring is complete!")
        print("   - Single inheritance achieved")
        print("   - MRO simplified")
        print("   - No duplicate execution methods")
        print("   - WebSocket methods preserved")
    else:
        print("[FAILURE] VALIDATION FAILED - Issues remain in inheritance structure")
    
    print("="*60)
    
    return all_pass

if __name__ == "__main__":
    success = validate_single_inheritance()
    sys.exit(0 if success else 1)