#!/usr/bin/env python3
"""MRO Complexity Analysis Script

Analyzes Method Resolution Order complexity in DataSubAgent and ValidationSubAgent
to identify inheritance conflicts, method shadowing, and performance implications.

CRITICAL CONTEXT: Spacecraft system reliability analysis
"""

import ast
import inspect
import sys
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Any, Optional
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Import the actual classes for runtime analysis
    from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
    from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
    from netra_backend.app.agents.base_agent import BaseSubAgent
    from netra_backend.app.agents.base.interface import BaseExecutionInterface
    from netra_backend.app.agents.agent_lifecycle import AgentLifecycleMixin
    from netra_backend.app.agents.agent_communication import AgentCommunicationMixin
    from netra_backend.app.agents.agent_state import AgentStateMixin
    from netra_backend.app.agents.agent_observability import AgentObservabilityMixin
    from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
    RUNTIME_ANALYSIS = True
except ImportError as e:
    print(f"WARNING: Runtime analysis disabled due to import error: {e}")
    RUNTIME_ANALYSIS = False


class MROComplexityAnalyzer:
    """Analyzes Method Resolution Order complexity in agent inheritance hierarchy."""
    
    def __init__(self):
        self.analysis_results = {}
        self.method_conflicts = defaultdict(list)
        self.diamond_patterns = []
        self.super_call_chains = {}
        self.performance_metrics = {}
        
    def analyze_class_mro(self, cls) -> Dict[str, Any]:
        """Analyze Method Resolution Order for a specific class."""
        if not RUNTIME_ANALYSIS:
            return {"error": "Runtime analysis not available"}
            
        mro = cls.__mro__
        
        analysis = {
            "class_name": cls.__name__,
            "mro_length": len(mro),
            "mro_chain": [c.__name__ for c in mro],
            "method_sources": {},
            "attribute_sources": {},
            "conflicts": [],
            "diamonds": [],
            "super_chains": []
        }
        
        # Analyze method sources and conflicts
        methods_seen = set()
        for i, klass in enumerate(mro):
            for name, method in inspect.getmembers(klass, predicate=inspect.ismethod):
                if name not in methods_seen:
                    analysis["method_sources"][name] = {
                        "source_class": klass.__name__,
                        "mro_position": i,
                        "is_abstract": getattr(method, '__isabstractmethod__', False)
                    }
                    methods_seen.add(name)
                else:
                    # Method conflict detected
                    analysis["conflicts"].append({
                        "method_name": name,
                        "shadowed_class": klass.__name__,
                        "mro_position": i,
                        "resolved_to": analysis["method_sources"][name]["source_class"]
                    })
        
        # Analyze function methods (unbound methods)
        functions_seen = set()
        for i, klass in enumerate(mro):
            for name, func in inspect.getmembers(klass, predicate=inspect.isfunction):
                if name not in functions_seen:
                    analysis["method_sources"][name] = {
                        "source_class": klass.__name__,
                        "mro_position": i,
                        "is_abstract": getattr(func, '__isabstractmethod__', False),
                        "type": "function"
                    }
                    functions_seen.add(name)
                elif name not in analysis["method_sources"]:
                    # Function conflict detected
                    analysis["conflicts"].append({
                        "method_name": name,
                        "shadowed_class": klass.__name__,
                        "mro_position": i,
                        "resolved_to": "Not resolved - function shadowing"
                    })
        
        # Analyze attribute sources
        attributes_seen = set()
        for i, klass in enumerate(mro):
            for name in dir(klass):
                if not name.startswith('_') and not callable(getattr(klass, name, None)):
                    if name not in attributes_seen:
                        analysis["attribute_sources"][name] = {
                            "source_class": klass.__name__,
                            "mro_position": i
                        }
                        attributes_seen.add(name)
        
        # Detect diamond inheritance patterns
        analysis["diamonds"] = self._detect_diamond_patterns(mro)
        
        # Analyze super() call chains
        analysis["super_chains"] = self._analyze_super_chains(cls)
        
        return analysis
    
    def _detect_diamond_patterns(self, mro: Tuple) -> List[Dict[str, Any]]:
        """Detect diamond inheritance patterns in the MRO."""
        diamonds = []
        
        # Track which classes appear multiple times in the inheritance tree
        class_counts = defaultdict(int)
        for cls in mro:
            # Check all base classes
            for base in cls.__bases__:
                class_counts[base] += 1
        
        # Identify diamond patterns
        for cls, count in class_counts.items():
            if count > 1:
                diamonds.append({
                    "diamond_root": cls.__name__,
                    "occurrence_count": count,
                    "mro_positions": [i for i, c in enumerate(mro) if c == cls]
                })
        
        return diamonds
    
    def _analyze_super_chains(self, cls) -> List[Dict[str, Any]]:
        """Analyze super() call chains for potential issues."""
        chains = []
        
        if not RUNTIME_ANALYSIS:
            return chains
        
        # Look for __init__ method chains
        if hasattr(cls, '__init__'):
            try:
                source_lines = inspect.getsource(cls.__init__)
                if 'super()' in source_lines or '.super()' in source_lines:
                    chains.append({
                        "method": "__init__",
                        "has_super_calls": True,
                        "analysis": "Complex initialization chain detected"
                    })
            except (OSError, TypeError):
                pass
        
        return chains
    
    def generate_mro_visualization(self, cls) -> str:
        """Generate ASCII visualization of MRO chain."""
        if not RUNTIME_ANALYSIS:
            return "MRO visualization not available (runtime analysis disabled)"
            
        mro = cls.__mro__
        visualization = f"\n=== MRO for {cls.__name__} ===\n"
        
        for i, klass in enumerate(mro):
            indent = "  " * i
            arrow = "└─ " if i > 0 else "┌─ "
            visualization += f"{indent}{arrow}{klass.__name__}\n"
            
            # Show key methods for each class
            key_methods = []
            for name, method in inspect.getmembers(klass, predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x)):
                if not name.startswith('_') or name in ['__init__', '__call__']:
                    key_methods.append(name)
            
            if key_methods and i < len(mro) - 2:  # Skip 'object' class
                method_str = ", ".join(key_methods[:5])  # Limit to first 5
                if len(key_methods) > 5:
                    method_str += f" ... (+{len(key_methods) - 5} more)"
                visualization += f"{indent}    Methods: {method_str}\n"
        
        return visualization
    
    def calculate_complexity_metrics(self, cls) -> Dict[str, Any]:
        """Calculate complexity metrics for the class hierarchy."""
        if not RUNTIME_ANALYSIS:
            return {"error": "Metrics not available (runtime analysis disabled)"}
            
        mro = cls.__mro__
        
        metrics = {
            "mro_depth": len(mro),
            "method_count": 0,
            "abstract_method_count": 0,
            "conflict_count": 0,
            "diamond_count": 0,
            "complexity_score": 0
        }
        
        # Count methods and conflicts
        method_names = set()
        for klass in mro:
            for name, method in inspect.getmembers(klass, predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x)):
                if name in method_names:
                    metrics["conflict_count"] += 1
                else:
                    method_names.add(name)
                    metrics["method_count"] += 1
                    
                if getattr(method, '__isabstractmethod__', False):
                    metrics["abstract_method_count"] += 1
        
        # Count diamond patterns
        metrics["diamond_count"] = len(self._detect_diamond_patterns(mro))
        
        # Calculate complexity score
        # Higher score = more complex
        metrics["complexity_score"] = (
            metrics["mro_depth"] * 2 +
            metrics["conflict_count"] * 10 +
            metrics["diamond_count"] * 20 +
            (metrics["method_count"] // 10)  # Methods contribute to complexity
        )
        
        return metrics
    
    def demonstrate_method_resolution_issues(self, cls) -> Dict[str, Any]:
        """Create test scenarios that demonstrate MRO issues."""
        demonstrations = {
            "class_name": cls.__name__,
            "issues": [],
            "test_scenarios": []
        }
        
        if not RUNTIME_ANALYSIS:
            demonstrations["error"] = "Demonstrations not available (runtime analysis disabled)"
            return demonstrations
        
        try:
            # Test method resolution ambiguity
            instance = cls.__new__(cls)  # Create without calling __init__
            
            # Look for WebSocket method conflicts
            websocket_methods = [
                'emit_thinking', 'emit_agent_started', 'emit_tool_executing',
                'send_agent_thinking', 'send_status_update', 'send_tool_executing'
            ]
            
            for method_name in websocket_methods:
                if hasattr(instance, method_name):
                    method = getattr(instance, method_name)
                    source_class = method.__qualname__.split('.')[0] if hasattr(method, '__qualname__') else "Unknown"
                    
                    demonstrations["test_scenarios"].append({
                        "method": method_name,
                        "resolved_to": source_class,
                        "issue": "Multiple WebSocket event methods with similar functionality"
                    })
            
            # Test initialization complexity
            try:
                # Count number of __init__ methods in MRO
                init_methods = []
                for klass in cls.__mro__:
                    if hasattr(klass, '__init__') and klass.__init__ != object.__init__:
                        init_methods.append(klass.__name__)
                
                if len(init_methods) > 3:  # More than 3 init methods suggests complexity
                    demonstrations["issues"].append({
                        "type": "initialization_complexity",
                        "description": f"Complex initialization chain: {' -> '.join(init_methods)}",
                        "severity": "HIGH"
                    })
            except Exception as e:
                demonstrations["issues"].append({
                    "type": "initialization_analysis_error",
                    "description": str(e),
                    "severity": "MEDIUM"
                })
        
        except Exception as e:
            demonstrations["error"] = f"Could not create test instance: {e}"
        
        return demonstrations
    
    def analyze_performance_implications(self, cls) -> Dict[str, Any]:
        """Analyze performance implications of complex MRO."""
        if not RUNTIME_ANALYSIS:
            return {"error": "Performance analysis not available"}
            
        mro = cls.__mro__
        performance = {
            "mro_lookup_cost": len(mro),
            "method_resolution_cost": 0,
            "attribute_access_cost": 0,
            "memory_overhead": 0,
            "recommendations": []
        }
        
        # Method resolution cost increases with MRO length
        performance["method_resolution_cost"] = len(mro) * 2
        
        # Count total methods across all classes
        total_methods = 0
        for klass in mro:
            total_methods += len([name for name, _ in inspect.getmembers(klass, predicate=inspect.ismethod)])
        
        performance["attribute_access_cost"] = total_methods // 10  # Rough estimate
        
        # Memory overhead estimation
        performance["memory_overhead"] = len(mro) * 100  # Rough bytes estimate per class
        
        # Generate recommendations
        if len(mro) > 8:
            performance["recommendations"].append("Consider reducing inheritance depth")
        
        if performance["method_resolution_cost"] > 15:
            performance["recommendations"].append("High method resolution cost - consider composition over inheritance")
        
        if len(self._detect_diamond_patterns(mro)) > 0:
            performance["recommendations"].append("Diamond inheritance detected - review for unnecessary complexity")
        
        return performance
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive MRO analysis on both agent classes."""
        results = {
            "analysis_timestamp": __import__('datetime').datetime.now().isoformat(),
            "runtime_analysis_available": RUNTIME_ANALYSIS,
            "classes_analyzed": [],
            "summary": {},
            "detailed_results": {}
        }
        
        if not RUNTIME_ANALYSIS:
            results["error"] = "Runtime analysis not available - import errors detected"
            return results
        
        # Analyze DataSubAgent and ValidationSubAgent
        classes_to_analyze = [DataSubAgent, ValidationSubAgent]
        
        for cls in classes_to_analyze:
            class_name = cls.__name__
            results["classes_analyzed"].append(class_name)
            
            # Comprehensive analysis for each class
            class_analysis = {
                "mro_analysis": self.analyze_class_mro(cls),
                "visualization": self.generate_mro_visualization(cls),
                "complexity_metrics": self.calculate_complexity_metrics(cls),
                "resolution_issues": self.demonstrate_method_resolution_issues(cls),
                "performance_implications": self.analyze_performance_implications(cls)
            }
            
            results["detailed_results"][class_name] = class_analysis
        
        # Generate summary comparison
        if len(results["detailed_results"]) >= 2:
            results["summary"] = self._generate_comparative_summary(results["detailed_results"])
        
        return results
    
    def _generate_comparative_summary(self, detailed_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comparative summary between classes."""
        summary = {
            "total_classes_analyzed": len(detailed_results),
            "complexity_comparison": {},
            "common_issues": [],
            "recommendations": []
        }
        
        # Compare complexity metrics
        for class_name, analysis in detailed_results.items():
            if "complexity_metrics" in analysis and "error" not in analysis["complexity_metrics"]:
                metrics = analysis["complexity_metrics"]
                summary["complexity_comparison"][class_name] = {
                    "complexity_score": metrics.get("complexity_score", 0),
                    "mro_depth": metrics.get("mro_depth", 0),
                    "conflict_count": metrics.get("conflict_count", 0),
                    "diamond_count": metrics.get("diamond_count", 0)
                }
        
        # Identify common issues
        all_issues = []
        for analysis in detailed_results.values():
            if "resolution_issues" in analysis and "issues" in analysis["resolution_issues"]:
                all_issues.extend(analysis["resolution_issues"]["issues"])
        
        # Find patterns in issues
        issue_types = defaultdict(int)
        for issue in all_issues:
            issue_types[issue.get("type", "unknown")] += 1
        
        for issue_type, count in issue_types.items():
            if count > 1:  # Common across multiple classes
                summary["common_issues"].append({
                    "type": issue_type,
                    "occurrence_count": count
                })
        
        # Generate recommendations
        high_complexity_classes = []
        for class_name, metrics in summary["complexity_comparison"].items():
            if metrics["complexity_score"] > 30:  # Arbitrary threshold
                high_complexity_classes.append(class_name)
        
        if high_complexity_classes:
            summary["recommendations"].append({
                "priority": "HIGH",
                "description": f"Reduce complexity in: {', '.join(high_complexity_classes)}",
                "action": "Consider single inheritance pattern with mixins"
            })
        
        if any(metrics["diamond_count"] > 0 for metrics in summary["complexity_comparison"].values()):
            summary["recommendations"].append({
                "priority": "MEDIUM", 
                "description": "Diamond inheritance patterns detected",
                "action": "Review inheritance hierarchy for unnecessary multiple inheritance"
            })
        
        return summary


def main():
    """Main analysis execution."""
    print("=== MRO COMPLEXITY ANALYSIS ===")
    print("Analyzing DataSubAgent and ValidationSubAgent inheritance complexity...")
    
    analyzer = MROComplexityAnalyzer()
    results = analyzer.run_comprehensive_analysis()
    
    # Save results to JSON for detailed analysis
    import json
    with open("mro_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Analysis complete. Results saved to mro_analysis_results.json")
    print(f"Runtime analysis available: {results['runtime_analysis_available']}")
    
    if results["runtime_analysis_available"]:
        print(f"Classes analyzed: {', '.join(results['classes_analyzed'])}")
        
        # Print summary
        if "summary" in results and results["summary"]:
            print("\n=== COMPLEXITY COMPARISON ===")
            for class_name, metrics in results["summary"].get("complexity_comparison", {}).items():
                print(f"{class_name}: Complexity Score = {metrics['complexity_score']}, MRO Depth = {metrics['mro_depth']}")
    else:
        print("WARNING: Runtime analysis failed - check import dependencies")
    
    return results


if __name__ == "__main__":
    results = main()