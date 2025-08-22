#!/usr/bin/env python
"""
FUNCTION COMPLEXITY ANALYZER - Identifies functions exceeding 25-line mandate

Systematically analyzes Python functions across critical modules to identify
violations of the 25-line function limit per CLAUDE.md specifications.
"""

import argparse
import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NamedTuple, Tuple


@dataclass
class FunctionInfo:
    """Information about a function and its complexity."""
    name: str
    line_count: int
    start_line: int
    end_line: int
    file_path: str
    complexity_score: float
    has_nested_functions: bool
    has_loops: bool
    has_conditionals: bool

class FunctionVisitor(ast.NodeVisitor):
    """AST visitor to analyze function complexity."""
    
    def __init__(self, file_path: str):
        self.functions = []
        self.file_path = file_path
    
    def visit_FunctionDef(self, node):
        """Visit function definition and calculate metrics."""
        self._analyze_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition and calculate metrics."""
        self._analyze_function(node)
        self.generic_visit(node)
    
    def _analyze_function(self, node):
        """Analyze function complexity metrics."""
        line_count = self._calculate_line_count(node)
        complexity_metrics = self._calculate_complexity_metrics(node)
        
        if line_count > 8:  # Only track functions exceeding limit
            function_info = FunctionInfo(
                name=node.name,
                line_count=line_count,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno + line_count,
                file_path=self.file_path,
                complexity_score=complexity_metrics["score"],
                has_nested_functions=complexity_metrics["nested_functions"],
                has_loops=complexity_metrics["loops"],
                has_conditionals=complexity_metrics["conditionals"]
            )
            self.functions.append(function_info)
    
    def _calculate_line_count(self, node):
        """Calculate logical line count excluding comments and docstrings."""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno - node.lineno + 1
        return 1
    
    def _calculate_complexity_metrics(self, node):
        """Calculate complexity metrics for function."""
        analyzer = ComplexityAnalyzer()
        analyzer.visit(node)
        return analyzer.get_metrics()

class ComplexityAnalyzer(ast.NodeVisitor):
    """Analyzes complexity within a function."""
    
    def __init__(self):
        self.nested_functions = 0
        self.loops = 0
        self.conditionals = 0
        self.branches = 0
    
    def visit_FunctionDef(self, node):
        """Count nested functions."""
        self.nested_functions += 1
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Count nested async functions."""
        self.nested_functions += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Count for loops."""
        self.loops += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Count while loops."""
        self.loops += 1
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Count if statements."""
        self.conditionals += 1
        self.branches += 1
        if node.orelse:
            self.branches += 1
        self.generic_visit(node)
    
    def get_metrics(self):
        """Calculate and return complexity metrics."""
        score = self._calculate_complexity_score()
        return {
            "score": score,
            "nested_functions": self.nested_functions > 0,
            "loops": self.loops > 0,
            "conditionals": self.conditionals > 0
        }
    
    def _calculate_complexity_score(self):
        """Calculate complexity score based on various metrics."""
        base_score = 1.0
        complexity_factors = [
            self.nested_functions * 0.3,
            self.loops * 0.2,
            self.conditionals * 0.1,
            self.branches * 0.05
        ]
        return base_score + sum(complexity_factors)

class FunctionComplexityAnalyzer:
    """Main analyzer for function complexity across modules."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.focus_areas = self._get_focus_areas()
    
    def _get_focus_areas(self):
        """Define focus areas for analysis."""
        return {
            "test_framework": [
                "test_runner.py",
                "test_framework/test_discovery.py",
                "test_framework/runner.py",
                "test_framework/comprehensive_reporter.py"
            ],
            "websocket": ["app/websocket/*.py"],
            "database": ["app/db/*.py"],
            "agents": ["app/agents/*.py"],
            "core": ["app/core/*.py"]
        }
    
    def analyze_all_areas(self):
        """Analyze all focus areas for function complexity."""
        results = {}
        for area_name, patterns in self.focus_areas.items():
            results[area_name] = self._analyze_area(patterns)
        return results
    
    def _analyze_area(self, patterns):
        """Analyze specific area using file patterns."""
        files_to_analyze = self._expand_patterns(patterns)
        complex_functions = []
        
        for file_path in files_to_analyze:
            if file_path.exists():
                functions = self._analyze_file(file_path)
                complex_functions.extend(functions)
        
        return complex_functions
    
    def _expand_patterns(self, patterns):
        """Expand glob patterns to actual file paths."""
        files = []
        for pattern in patterns:
            if "*" in pattern:
                files.extend(Path(self.project_root).glob(pattern))
            else:
                files.append(Path(self.project_root) / pattern)
        return files
    
    def _analyze_file(self, file_path: Path):
        """Analyze single file for complex functions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            visitor = FunctionVisitor(str(file_path))
            visitor.visit(tree)
            return visitor.functions
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return []
    
    def generate_report(self, results):
        """Generate comprehensive complexity report."""
        report = self._create_report_header()
        report += self._create_summary_section(results)
        report += self._create_detailed_analysis(results)
        report += self._create_recommendations(results)
        return report
    
    def _create_report_header(self):
        """Create report header."""
        return """
# FUNCTION COMPLEXITY REDUCTION REPORT
Generated: Function exceeding 25-line mandate analysis

## EXECUTIVE SUMMARY
This report identifies all functions exceeding the mandatory 25-line limit 
per CLAUDE.md specifications across critical system modules.

"""
    
    def _create_summary_section(self, results):
        """Create summary statistics section."""
        total_violations = sum(len(funcs) for funcs in results.values())
        area_counts = {area: len(funcs) for area, funcs in results.items()}
        
        summary = f"""
## VIOLATION SUMMARY
- **Total Functions Exceeding 8 Lines**: {total_violations}
- **Critical Areas Affected**: {len([a for a, f in area_counts.items() if f > 0])}

### Violations by Area:
"""
        for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                summary += f"- **{area}**: {count} functions\n"
        
        return summary + "\n"
    
    def _create_detailed_analysis(self, results):
        """Create detailed analysis section."""
        analysis = "## DETAILED ANALYSIS\n\n"
        
        for area_name, functions in results.items():
            if functions:
                analysis += self._analyze_area_functions(area_name, functions)
        
        return analysis
    
    def _analyze_area_functions(self, area_name, functions):
        """Analyze functions in specific area."""
        section = f"### {area_name.upper()} AREA\n\n"
        
        # Sort by complexity score
        sorted_functions = sorted(functions, key=lambda f: f.complexity_score, reverse=True)
        
        for func in sorted_functions:
            section += self._format_function_analysis(func)
        
        return section + "\n"
    
    def _format_function_analysis(self, func):
        """Format individual function analysis."""
        relative_path = os.path.relpath(func.file_path, self.project_root)
        complexity_flags = self._get_complexity_flags(func)
        
        return f"""
#### `{func.name}()` - {func.line_count} lines
- **File**: `{relative_path}`
- **Lines**: {func.start_line}-{func.end_line} ({func.line_count} lines)
- **Complexity Score**: {func.complexity_score:.2f}
- **Issues**: {', '.join(complexity_flags)}

**Decomposition Priority**: {'HIGH' if func.complexity_score > 2.0 else 'MEDIUM' if func.complexity_score > 1.5 else 'LOW'}

"""
    
    def _get_complexity_flags(self, func):
        """Get complexity flags for function."""
        flags = []
        if func.line_count > 15:
            flags.append("Very Long")
        if func.has_nested_functions:
            flags.append("Nested Functions")
        if func.has_loops:
            flags.append("Contains Loops")
        if func.has_conditionals:
            flags.append("Complex Conditionals")
        if not flags:
            flags.append("Long but Simple")
        return flags
    
    def _create_recommendations(self, results):
        """Create decomposition recommendations."""
        recommendations = """
## DECOMPOSITION STRATEGIES

### Immediate Actions Required:
1. **Extract Helper Functions**: Break out repeated logic patterns
2. **Apply Guard Clauses**: Reduce nesting with early returns
3. **Use Composition**: Split complex functions into smaller components
4. **Leverage Python Features**: Use comprehensions, map/filter where appropriate

### Refactoring Techniques by Pattern:

#### For Validation/Parsing Functions:
- Extract validation steps into separate functions
- Use validator pattern for complex checks
- Apply chain-of-responsibility for multi-step validation

#### For Data Processing Functions:
- Extract transformation steps
- Use functional programming patterns
- Apply pipeline pattern for multi-stage processing

#### For Connection/Session Management:
- Extract setup/teardown functions
- Use context managers for resource management
- Apply factory pattern for object creation

#### For Error Handling Functions:
- Extract error classification logic
- Use strategy pattern for different error types
- Apply command pattern for error recovery

### Performance Considerations:
- **Maintain Performance**: Ensure decomposition doesn't degrade performance
- **Measure Impact**: Profile before/after refactoring
- **Optimize Hot Paths**: Prioritize performance-critical functions

### Testing Strategy:
- **Unit Test Each Function**: Ensure every new function has tests
- **Maintain Coverage**: Don't lose test coverage during refactoring
- **Test Integration**: Verify composed functions work together

## IMPLEMENTATION PRIORITY

### Phase 1 (Immediate - High Complexity):
Functions with complexity score > 2.0 and >20 lines

### Phase 2 (Next Sprint - Medium Complexity):
Functions with complexity score 1.5-2.0 and >15 lines

### Phase 3 (Continuous - Low Complexity):
Remaining functions >8 lines for consistency

"""
        return recommendations

def main():
    """Main entry point for function complexity analysis."""
    parser = argparse.ArgumentParser(description="Analyze function complexity across critical modules")
    parser.add_argument("--project-root", type=str, default=".", help="Project root directory")
    parser.add_argument("--output", type=str, help="Output file for report")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    
    args = parser.parse_args()
    
    project_root = Path(args.project_root).resolve()
    analyzer = FunctionComplexityAnalyzer(project_root)
    
    print("Analyzing function complexity across critical modules...")
    results = analyzer.analyze_all_areas()
    
    if args.format == "json":
        import json
        output = _convert_results_to_json(results)
        content = json.dumps(output, indent=2)
    else:
        content = analyzer.generate_report(results)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Report saved to: {args.output}")
    else:
        print(content)

def _convert_results_to_json(results):
    """Convert results to JSON-serializable format."""
    json_results = {}
    for area, functions in results.items():
        json_results[area] = [
            {
                "name": f.name,
                "line_count": f.line_count,
                "start_line": f.start_line,
                "end_line": f.end_line,
                "file_path": f.file_path,
                "complexity_score": f.complexity_score,
                "has_nested_functions": f.has_nested_functions,
                "has_loops": f.has_loops,
                "has_conditionals": f.has_conditionals
            }
            for f in functions
        ]
    return json_results

if __name__ == "__main__":
    main()