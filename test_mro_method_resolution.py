#!/usr/bin/env python3
"""Test Script: Method Resolution Order Issues

This script creates specific test scenarios that demonstrate the method resolution
problems identified in the MRO analysis. It shows how the current multiple inheritance
pattern creates ambiguous method calls and potential runtime issues.

CRITICAL CONTEXT: Spacecraft reliability testing
"""

import sys
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
    from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
    from netra_backend.app.agents.base_agent import BaseSubAgent
    from netra_backend.app.agents.base.interface import BaseExecutionInterface, ExecutionContext
    from netra_backend.app.agents.state import DeepAgentState
    TESTING_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Testing disabled due to import error: {e}")
    TESTING_AVAILABLE = False


class MRORealWorldTester:
    """Tests that demonstrate real-world MRO resolution issues."""
    
    def __init__(self):
        self.test_results = []
    
    def test_websocket_method_resolution(self) -> Dict[str, Any]:
        """Test WebSocket method resolution to show conflicts."""
        if not TESTING_AVAILABLE:
            return {"error": "Testing not available"}
        
        test_results = {
            "test_name": "WebSocket Method Resolution Test",
            "findings": [],
            "critical_issues": []
        }
        
        try:
            # Create agent instances without full initialization
            data_agent = DataSubAgent.__new__(DataSubAgent)
            validation_agent = ValidationSubAgent.__new__(ValidationSubAgent)
            
            # Test 1: Demonstrate emit_thinking method resolution
            emit_thinking_method = getattr(data_agent, 'emit_thinking', None)
            if emit_thinking_method:
                # Get the actual class that provides this method
                method_class = self._get_method_source_class(DataSubAgent, 'emit_thinking')
                test_results["findings"].append({
                    "method": "emit_thinking",
                    "resolved_to": method_class,
                    "expected_source": "BaseSubAgent",
                    "issue": f"Method resolved to {method_class} - potential confusion with BaseExecutionInterface methods"
                })
            
            # Test 2: Demonstrate send_agent_thinking method resolution
            send_thinking_method = getattr(data_agent, 'send_agent_thinking', None)
            if send_thinking_method:
                method_class = self._get_method_source_class(DataSubAgent, 'send_agent_thinking')
                test_results["findings"].append({
                    "method": "send_agent_thinking",
                    "resolved_to": method_class,
                    "expected_source": "BaseExecutionInterface",
                    "issue": f"Similar functionality to emit_thinking but from different class: {method_class}"
                })
            
            # Test 3: Check for method signature differences
            emit_params = self._get_method_parameters(data_agent, 'emit_thinking')
            send_params = self._get_method_parameters(data_agent, 'send_agent_thinking')
            
            if emit_params != send_params:
                test_results["critical_issues"].append({
                    "issue": "WebSocket method signature mismatch",
                    "emit_thinking_params": emit_params,
                    "send_agent_thinking_params": send_params,
                    "risk": "Different WebSocket methods have different interfaces"
                })
            
            # Test 4: Demonstrate method availability confusion
            websocket_methods = ['emit_thinking', 'emit_agent_started', 'send_agent_thinking', 'send_status_update']
            method_sources = {}
            
            for method_name in websocket_methods:
                if hasattr(data_agent, method_name):
                    source_class = self._get_method_source_class(DataSubAgent, method_name)
                    method_sources[method_name] = source_class
            
            # Group methods by source class
            class_groups = {}
            for method, source in method_sources.items():
                if source not in class_groups:
                    class_groups[source] = []
                class_groups[source].append(method)
            
            if len(class_groups) > 1:
                test_results["critical_issues"].append({
                    "issue": "WebSocket methods come from multiple classes",
                    "method_sources": class_groups,
                    "risk": "Inconsistent WebSocket behavior across method calls"
                })
        
        except Exception as e:
            test_results["critical_issues"].append({
                "issue": "Test execution failed",
                "error": str(e),
                "risk": "Cannot determine method resolution behavior"
            })
        
        return test_results
    
    def test_initialization_order_issues(self) -> Dict[str, Any]:
        """Test initialization order to show super() call problems."""
        if not TESTING_AVAILABLE:
            return {"error": "Testing not available"}
        
        test_results = {
            "test_name": "Initialization Order Test",
            "findings": [],
            "super_call_issues": []
        }
        
        try:
            # Test 1: Analyze initialization chain
            mro_chain = DataSubAgent.__mro__
            init_classes = []
            
            for cls in mro_chain:
                if hasattr(cls, '__init__') and cls.__init__ != object.__init__:
                    init_classes.append({
                        "class": cls.__name__,
                        "mro_position": mro_chain.index(cls),
                        "has_custom_init": True
                    })
            
            test_results["findings"].append({
                "initialization_chain": init_classes,
                "chain_length": len(init_classes),
                "complexity": "HIGH" if len(init_classes) > 3 else "MEDIUM"
            })
            
            # Test 2: Check for super() usage patterns
            for cls_info in init_classes[:3]:  # Check first 3 classes
                cls_name = cls_info["class"]
                cls_obj = next(c for c in mro_chain if c.__name__ == cls_name)
                
                has_super_call = self._check_super_usage(cls_obj, '__init__')
                if has_super_call:
                    test_results["findings"].append({
                        "class": cls_name,
                        "uses_super": True,
                        "position_in_mro": cls_info["mro_position"]
                    })
            
            # Test 3: Identify potential initialization conflicts
            # Check if both BaseSubAgent and BaseExecutionInterface have __init__
            base_sub_init = hasattr(BaseSubAgent, '__init__')
            base_exec_init = hasattr(BaseExecutionInterface, '__init__')
            
            if base_sub_init and base_exec_init:
                test_results["super_call_issues"].append({
                    "issue": "Multiple base classes with __init__",
                    "classes": ["BaseSubAgent", "BaseExecutionInterface"],
                    "risk": "super() call order ambiguity in multiple inheritance"
                })
            
            # Test 4: Parameter signature conflicts
            try:
                # Get init signatures (if available)
                data_agent_init = DataSubAgent.__init__
                base_sub_init_method = BaseSubAgent.__init__
                
                data_params = self._get_method_parameters_from_func(data_agent_init)
                base_params = self._get_method_parameters_from_func(base_sub_init_method)
                
                test_results["findings"].append({
                    "parameter_analysis": {
                        "DataSubAgent_init_params": data_params,
                        "BaseSubAgent_init_params": base_params,
                        "signature_compatible": data_params == base_params
                    }
                })
            
            except Exception as e:
                test_results["super_call_issues"].append({
                    "issue": "Could not analyze parameter signatures",
                    "error": str(e)
                })
        
        except Exception as e:
            test_results["super_call_issues"].append({
                "issue": "Initialization analysis failed",
                "error": str(e),
                "risk": "Cannot predict initialization behavior"
            })
        
        return test_results
    
    def test_method_override_confusion(self) -> Dict[str, Any]:
        """Test method override behavior to show resolution confusion."""
        if not TESTING_AVAILABLE:
            return {"error": "Testing not available"}
        
        test_results = {
            "test_name": "Method Override Confusion Test",
            "override_conflicts": [],
            "execution_path_issues": []
        }
        
        try:
            # Test 1: Check execute_core_logic implementations
            execute_implementations = []
            for cls in DataSubAgent.__mro__:
                if hasattr(cls, 'execute_core_logic') and 'execute_core_logic' in cls.__dict__:
                    execute_implementations.append({
                        "class": cls.__name__,
                        "mro_position": DataSubAgent.__mro__.index(cls),
                        "is_abstract": getattr(cls.__dict__['execute_core_logic'], '__isabstractmethod__', False)
                    })
            
            if len(execute_implementations) > 1:
                test_results["override_conflicts"].append({
                    "method": "execute_core_logic",
                    "implementations": execute_implementations,
                    "resolved_to": execute_implementations[0]["class"],
                    "risk": "Multiple implementations may cause execution confusion"
                })
            
            # Test 2: Check validate_preconditions implementations
            validate_implementations = []
            for cls in DataSubAgent.__mro__:
                if hasattr(cls, 'validate_preconditions') and 'validate_preconditions' in cls.__dict__:
                    validate_implementations.append({
                        "class": cls.__name__,
                        "mro_position": DataSubAgent.__mro__.index(cls),
                        "is_abstract": getattr(cls.__dict__['validate_preconditions'], '__isabstractmethod__', False)
                    })
            
            if len(validate_implementations) > 1:
                test_results["override_conflicts"].append({
                    "method": "validate_preconditions",
                    "implementations": validate_implementations,
                    "resolved_to": validate_implementations[0]["class"],
                    "risk": "Validation logic may be bypassed or inconsistent"
                })
            
            # Test 3: Check for execution path confusion
            data_agent = DataSubAgent.__new__(DataSubAgent)
            
            # Try to trace which execute method would actually be called
            execute_method = getattr(data_agent, 'execute', None)
            execute_core_method = getattr(data_agent, 'execute_core_logic', None)
            
            if execute_method and execute_core_method:
                execute_source = self._get_method_source_class(DataSubAgent, 'execute')
                execute_core_source = self._get_method_source_class(DataSubAgent, 'execute_core_logic')
                
                test_results["execution_path_issues"].append({
                    "issue": "Multiple execution entry points",
                    "execute_source": execute_source,
                    "execute_core_logic_source": execute_core_source,
                    "risk": "Unclear which execution path will be taken"
                })
        
        except Exception as e:
            test_results["execution_path_issues"].append({
                "issue": "Method override analysis failed",
                "error": str(e),
                "risk": "Cannot predict method resolution behavior"
            })
        
        return test_results
    
    def test_performance_degradation(self) -> Dict[str, Any]:
        """Test performance impact of complex MRO."""
        if not TESTING_AVAILABLE:
            return {"error": "Testing not available"}
        
        test_results = {
            "test_name": "Performance Degradation Test",
            "method_lookup_times": [],
            "memory_overhead": [],
            "comparison_metrics": []
        }
        
        try:
            # Create test instances
            data_agent = DataSubAgent.__new__(DataSubAgent)
            
            # Test method lookup performance for common methods
            test_methods = ['emit_thinking', 'execute_core_logic', 'validate_preconditions', 'send_agent_thinking']
            
            for method_name in test_methods:
                if hasattr(data_agent, method_name):
                    # Time 1000 attribute lookups
                    start_time = time.perf_counter()
                    for _ in range(1000):
                        getattr(data_agent, method_name)
                    end_time = time.perf_counter()
                    
                    lookup_time = (end_time - start_time) * 1000  # Convert to milliseconds
                    mro_position = self._get_method_mro_position(DataSubAgent, method_name)
                    
                    test_results["method_lookup_times"].append({
                        "method": method_name,
                        "total_time_ms": lookup_time,
                        "average_per_lookup_us": (lookup_time * 1000) / 1000,  # microseconds
                        "mro_position": mro_position,
                        "mro_depth": len(DataSubAgent.__mro__)
                    })
            
            # Calculate memory overhead estimation
            mro_depth = len(DataSubAgent.__mro__)
            total_methods = len([name for name in dir(DataSubAgent) if callable(getattr(DataSubAgent, name))])
            
            # Rough memory estimation
            estimated_per_class_overhead = 64  # bytes per class in MRO
            estimated_method_table_overhead = total_methods * 8  # bytes per method pointer
            total_estimated_overhead = (mro_depth * estimated_per_class_overhead) + estimated_method_table_overhead
            
            test_results["memory_overhead"].append({
                "mro_depth": mro_depth,
                "total_methods": total_methods,
                "estimated_class_overhead_bytes": mro_depth * estimated_per_class_overhead,
                "estimated_method_table_bytes": estimated_method_table_overhead,
                "total_estimated_bytes": total_estimated_overhead
            })
            
            # Comparison with ideal single inheritance
            ideal_mro_depth = 3  # Agent -> BaseAgent -> object
            ideal_overhead = (ideal_mro_depth * estimated_per_class_overhead) + estimated_method_table_overhead
            
            test_results["comparison_metrics"].append({
                "current_mro_depth": mro_depth,
                "ideal_mro_depth": ideal_mro_depth,
                "overhead_multiplier": mro_depth / ideal_mro_depth,
                "current_estimated_bytes": total_estimated_overhead,
                "ideal_estimated_bytes": ideal_overhead,
                "memory_waste_bytes": total_estimated_overhead - ideal_overhead,
                "efficiency_loss_percent": ((total_estimated_overhead - ideal_overhead) / ideal_overhead) * 100
            })
        
        except Exception as e:
            test_results["method_lookup_times"].append({
                "error": str(e),
                "test": "Performance test failed"
            })
        
        return test_results
    
    def _get_method_source_class(self, cls, method_name: str) -> str:
        """Get the class that actually provides a method."""
        for mro_cls in cls.__mro__:
            if method_name in mro_cls.__dict__:
                return mro_cls.__name__
        return "Unknown"
    
    def _get_method_mro_position(self, cls, method_name: str) -> int:
        """Get the MRO position where a method is first defined."""
        for i, mro_cls in enumerate(cls.__mro__):
            if method_name in mro_cls.__dict__:
                return i
        return -1
    
    def _get_method_parameters(self, obj, method_name: str) -> List[str]:
        """Get method parameter names."""
        try:
            import inspect
            method = getattr(obj, method_name, None)
            if method:
                sig = inspect.signature(method)
                return list(sig.parameters.keys())
        except (TypeError, ValueError):
            pass
        return []
    
    def _get_method_parameters_from_func(self, func) -> List[str]:
        """Get function parameter names."""
        try:
            import inspect
            sig = inspect.signature(func)
            return list(sig.parameters.keys())
        except (TypeError, ValueError):
            pass
        return []
    
    def _check_super_usage(self, cls, method_name: str) -> bool:
        """Check if a method uses super() calls."""
        try:
            import inspect
            method = getattr(cls, method_name, None)
            if method:
                source = inspect.getsource(method)
                return 'super()' in source
        except (OSError, TypeError):
            pass
        return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all MRO tests and return comprehensive results."""
        results = {
            "test_timestamp": __import__('datetime').datetime.now().isoformat(),
            "testing_available": TESTING_AVAILABLE,
            "test_results": {}
        }
        
        if not TESTING_AVAILABLE:
            results["error"] = "Testing not available - import errors detected"
            return results
        
        print("=== RUNNING MRO METHOD RESOLUTION TESTS ===")
        
        # Define all tests
        tests = [
            ("websocket_method_resolution", self.test_websocket_method_resolution),
            ("initialization_order_issues", self.test_initialization_order_issues),
            ("method_override_confusion", self.test_method_override_confusion),
            ("performance_degradation", self.test_performance_degradation)
        ]
        
        # Run each test
        for test_name, test_func in tests:
            print(f"Running {test_name}...")
            try:
                results["test_results"][test_name] = test_func()
                print(f"+ {test_name} completed")
            except Exception as e:
                print(f"- {test_name} failed: {e}")
                results["test_results"][test_name] = {
                    "error": str(e)
                }
        
        return results


def main():
    """Main test execution."""
    print("=== MRO METHOD RESOLUTION TESTING ===")
    print("Testing method resolution order issues in agent inheritance...")
    
    tester = MRORealWorldTester()
    results = tester.run_all_tests()
    
    # Save results to JSON for analysis
    import json
    with open("mro_method_resolution_test.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nTesting complete. Results saved to mro_method_resolution_test.json")
    print(f"Testing available: {results['testing_available']}")
    
    if results["testing_available"]:
        print("\n=== TEST SUMMARY ===")
        for test_name, test_result in results["test_results"].items():
            print(f"\n{test_name}:")
            if isinstance(test_result, dict) and "error" not in test_result:
                # Count findings
                findings = test_result.get("findings", [])
                issues = test_result.get("critical_issues", []) + test_result.get("super_call_issues", [])
                conflicts = test_result.get("override_conflicts", [])
                
                if findings:
                    print(f"  - Findings: {len(findings)}")
                if issues:
                    print(f"  - Critical Issues: {len(issues)}")
                if conflicts:
                    print(f"  - Override Conflicts: {len(conflicts)}")
                
                # Show key metrics for performance test
                if "method_lookup_times" in test_result:
                    lookup_times = test_result["method_lookup_times"]
                    if lookup_times:
                        avg_time = sum(lt.get("total_time_ms", 0) for lt in lookup_times) / len(lookup_times)
                        print(f"  - Average Method Lookup: {avg_time:.3f}ms per 1000 calls")
            else:
                print(f"  - Test failed or not available")
    
    return results


if __name__ == "__main__":
    results = main()