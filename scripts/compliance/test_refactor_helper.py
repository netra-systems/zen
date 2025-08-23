#!/usr/bin/env python3
"""
Test refactoring helper for splitting large test files.

This helper analyzes large test files and suggests intelligent splits based on:
- Test categories (unit, integration, e2e)
- Functionality being tested
- Test classes and groupings
- Dependencies between tests

Features:
- Analyzes large test files and suggests splits
- Groups related tests for extraction
- Maintains test dependencies when splitting
- Generates new file names following conventions
- Preserves imports and test utilities
"""

import argparse
import ast
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path

@dataclass
class TestFunction:
    """Represents a test function"""
    name: str
    line_start: int
    line_end: int
    class_name: Optional[str]
    decorators: List[str]
    dependencies: Set[str]
    category: str  # unit, integration, e2e, fixture, helper
    complexity: int
    content: str

@dataclass
class TestClass:
    """Represents a test class"""
    name: str
    line_start: int
    line_end: int
    methods: List[TestFunction]
    dependencies: Set[str]
    category: str
    content: str

@dataclass
class SplitSuggestion:
    """Represents a suggestion for splitting a file"""
    original_file: str
    new_files: List[Dict]
    strategy: str
    confidence: float
    dependencies: Dict[str, Set[str]]
    warnings: List[str]

class TestRefactorHelper:
    """Helps refactor large test files into smaller, focused modules"""
    
    def __init__(self, root_path: Path = None):
        self.root_path = root_path or PROJECT_ROOT
        
    def analyze_file_for_splitting(self, file_path: Path) -> Dict:
        """Analyze a test file and suggest optimal splitting strategies"""
        print(f"Analyzing {file_path} for splitting opportunities...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "suggestions": []}
        
        # Extract components
        imports = self._extract_imports(tree)
        functions = self._extract_functions(tree, lines)
        classes = self._extract_classes(tree, lines)
        fixtures = self._extract_fixtures(tree, lines)
        
        # Analyze dependencies
        dependencies = self._analyze_dependencies(functions, classes, content)
        
        # Generate splitting strategies
        strategies = self._generate_splitting_strategies(
            file_path, functions, classes, fixtures, dependencies, imports
        )
        
        return {
            "file_path": str(file_path),
            "total_lines": len(lines),
            "functions": len(functions),
            "classes": len(classes),
            "fixtures": len(fixtures),
            "imports": imports,
            "dependencies": dependencies,
            "strategies": strategies
        }
    
    def _extract_imports(self, tree: ast.AST) -> Dict[str, List[str]]:
        """Extract import statements"""
        imports = {
            "standard": [],
            "third_party": [],
            "local": []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._categorize_import(alias.name, imports)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._categorize_import(node.module, imports)
        
        return imports
    
    def _categorize_import(self, module_name: str, imports: Dict):
        """Categorize an import as standard, third-party, or local"""
        if module_name.startswith('.') or 'app.' in module_name:
            imports["local"].append(module_name)
        elif module_name in ['os', 'sys', 'json', 'time', 'datetime', 'unittest', 'asyncio']:
            imports["standard"].append(module_name)
        else:
            imports["third_party"].append(module_name)
    
    def _extract_functions(self, tree: ast.AST, lines: List[str]) -> List[TestFunction]:
        """Extract test functions with metadata"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func = self._analyze_function(node, lines)
                if func:
                    functions.append(func)
        
        return functions
    
    def _analyze_function(self, node: ast.FunctionDef, lines: List[str]) -> Optional[TestFunction]:
        """Analyze a single function"""
        line_start = node.lineno - 1
        line_end = getattr(node, 'end_lineno', line_start + 10) - 1
        
        # Get content
        content = '\n'.join(lines[line_start:line_end + 1])
        
        # Determine category
        category = self._determine_function_category(node, content)
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(f"{decorator.value.id}.{decorator.attr}")
        
        # Analyze dependencies
        dependencies = self._extract_function_dependencies(content)
        
        # Estimate complexity
        complexity = self._estimate_function_complexity(node)
        
        return TestFunction(
            name=node.name,
            line_start=line_start,
            line_end=line_end,
            class_name=None,  # Will be set if inside a class
            decorators=decorators,
            dependencies=dependencies,
            category=category,
            complexity=complexity,
            content=content
        )
    
    def _determine_function_category(self, node: ast.FunctionDef, content: str) -> str:
        """Determine the category of a function"""
        name = node.name.lower()
        
        # Fixtures
        if any(dec.id == 'fixture' for dec in node.decorator_list 
               if isinstance(dec, ast.Name)):
            return 'fixture'
        
        # Test functions
        if name.startswith('test_'):
            if any(keyword in content.lower() for keyword in 
                   ['integration', 'e2e', 'end_to_end', 'full_', 'complete_']):
                return 'integration'
            elif any(keyword in content.lower() for keyword in 
                     ['unit', 'mock', 'patch', 'isolated']):
                return 'unit'
            else:
                return 'test'
        
        # Helper functions
        if name.startswith('_') or name.endswith('_helper'):
            return 'helper'
        
        # Setup/teardown
        if name in ['setup', 'teardown', 'setUp', 'tearDown', 'setup_method', 'teardown_method']:
            return 'setup'
        
        return 'other'
    
    def _extract_function_dependencies(self, content: str) -> Set[str]:
        """Extract function dependencies from content"""
        dependencies = set()
        
        # Look for function calls
        function_calls = re.findall(r'(\w+)\s*\(', content)
        dependencies.update(function_calls)
        
        # Look for variable references
        var_refs = re.findall(r'self\.(\w+)', content)
        dependencies.update(var_refs)
        
        # Look for fixture dependencies
        fixture_deps = re.findall(r'@pytest\.fixture.*?\ndef\s+(\w+)', content)
        dependencies.update(fixture_deps)
        
        return dependencies
    
    def _estimate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Estimate cyclomatic complexity"""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.With)):
                complexity += 1
            elif isinstance(child, ast.Try):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _extract_classes(self, tree: ast.AST, lines: List[str]) -> List[TestClass]:
        """Extract test classes"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and self._is_test_class(node):
                cls = self._analyze_class(node, lines)
                classes.append(cls)
        
        return classes
    
    def _is_test_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a test class"""
        return (node.name.startswith('Test') or
                'test' in node.name.lower())
    
    def _analyze_class(self, node: ast.ClassDef, lines: List[str]) -> TestClass:
        """Analyze a test class"""
        line_start = node.lineno - 1
        line_end = getattr(node, 'end_lineno', line_start + 20) - 1
        
        content = '\n'.join(lines[line_start:line_end + 1])
        
        # Extract methods
        methods = []
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                method = self._analyze_function(child, lines)
                if method:
                    method.class_name = node.name
                    methods.append(method)
        
        # Determine category based on methods
        categories = [m.category for m in methods]
        if 'integration' in categories:
            category = 'integration'
        elif 'unit' in categories:
            category = 'unit'
        else:
            category = 'test'
        
        # Extract dependencies
        dependencies = set()
        for method in methods:
            dependencies.update(method.dependencies)
        
        return TestClass(
            name=node.name,
            line_start=line_start,
            line_end=line_end,
            methods=methods,
            dependencies=dependencies,
            category=category,
            content=content
        )
    
    def _extract_fixtures(self, tree: ast.AST, lines: List[str]) -> List[TestFunction]:
        """Extract pytest fixtures"""
        fixtures = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for @pytest.fixture decorator
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Attribute) and 
                        isinstance(decorator.value, ast.Name) and
                        decorator.value.id == 'pytest' and 
                        decorator.attr == 'fixture'):
                        func = self._analyze_function(node, lines)
                        if func:
                            func.category = 'fixture'
                            fixtures.append(func)
                        break
        
        return fixtures
    
    def _analyze_dependencies(self, functions: List[TestFunction], 
                            classes: List[TestClass], content: str) -> Dict:
        """Analyze dependencies between components"""
        dependencies = {
            "function_to_function": defaultdict(set),
            "function_to_fixture": defaultdict(set),
            "class_to_function": defaultdict(set),
            "shared_utilities": set()
        }
        
        # Analyze function dependencies
        for func in functions:
            for other_func in functions:
                if other_func.name in func.dependencies and func.name != other_func.name:
                    dependencies["function_to_function"][func.name].add(other_func.name)
        
        # Analyze fixture dependencies
        fixtures = [f for f in functions if f.category == 'fixture']
        for func in functions:
            for fixture in fixtures:
                if fixture.name in func.dependencies:
                    dependencies["function_to_fixture"][func.name].add(fixture.name)
        
        # Find shared utilities (functions called by many tests)
        function_usage = defaultdict(int)
        for func in functions:
            for dep in func.dependencies:
                function_usage[dep] += 1
        
        # Functions used by 3+ tests are considered shared utilities
        dependencies["shared_utilities"] = {
            func for func, count in function_usage.items() if count >= 3
        }
        
        return dependencies
    
    def _generate_splitting_strategies(self, file_path: Path, functions: List[TestFunction],
                                     classes: List[TestClass], fixtures: List[TestFunction],
                                     dependencies: Dict, imports: Dict) -> List[SplitSuggestion]:
        """Generate various splitting strategies"""
        strategies = []
        
        # Strategy 1: Split by category (unit/integration/e2e)
        category_split = self._strategy_split_by_category(
            file_path, functions, classes, fixtures, dependencies, imports
        )
        if category_split:
            strategies.append(category_split)
        
        # Strategy 2: Split by test class
        class_split = self._strategy_split_by_class(
            file_path, functions, classes, fixtures, dependencies, imports
        )
        if class_split:
            strategies.append(class_split)
        
        # Strategy 3: Split by feature/functionality
        feature_split = self._strategy_split_by_feature(
            file_path, functions, classes, fixtures, dependencies, imports
        )
        if feature_split:
            strategies.append(feature_split)
        
        # Strategy 4: Extract utilities
        utilities_split = self._strategy_extract_utilities(
            file_path, functions, classes, fixtures, dependencies, imports
        )
        if utilities_split:
            strategies.append(utilities_split)
        
        return strategies
    
    def _strategy_split_by_category(self, file_path: Path, functions: List[TestFunction],
                                  classes: List[TestClass], fixtures: List[TestFunction],
                                  dependencies: Dict, imports: Dict) -> Optional[SplitSuggestion]:
        """Strategy: Split by test category (unit/integration/e2e)"""
        
        # Group functions by category
        categories = defaultdict(list)
        for func in functions:
            categories[func.category].append(func)
        
        # Group classes by category
        for cls in classes:
            categories[cls.category].extend(cls.methods)
        
        # Only suggest if we have multiple categories
        if len(categories) < 2:
            return None
        
        new_files = []
        base_name = file_path.stem
        
        for category, items in categories.items():
            if category in ['unit', 'integration', 'e2e', 'test']:
                new_file_name = f"{base_name}_{category}.py"
                new_files.append({
                    "name": new_file_name,
                    "category": category,
                    "functions": [item.name for item in items],
                    "estimated_lines": sum(item.line_end - item.line_start + 1 for item in items)
                })
        
        # Always include fixtures and helpers in a utilities file
        utilities = [f for f in functions if f.category in ['fixture', 'helper']]
        if utilities:
            new_files.append({
                "name": f"{base_name}_fixtures.py",
                "category": "utilities",
                "functions": [f.name for f in utilities],
                "estimated_lines": sum(f.line_end - f.line_start + 1 for f in utilities)
            })
        
        return SplitSuggestion(
            original_file=str(file_path),
            new_files=new_files,
            strategy="split_by_category",
            confidence=0.8,
            dependencies=dependencies,
            warnings=["Review shared fixtures and utilities"]
        )
    
    def _strategy_split_by_class(self, file_path: Path, functions: List[TestFunction],
                               classes: List[TestClass], fixtures: List[TestFunction],
                               dependencies: Dict, imports: Dict) -> Optional[SplitSuggestion]:
        """Strategy: Split by test class"""
        
        if not classes or len(classes) < 2:
            return None
        
        new_files = []
        base_name = file_path.stem
        
        for cls in classes:
            new_file_name = f"{base_name}_{cls.name.lower()}.py"
            new_files.append({
                "name": new_file_name,
                "category": "class_based",
                "classes": [cls.name],
                "functions": [m.name for m in cls.methods],
                "estimated_lines": cls.line_end - cls.line_start + 1
            })
        
        # Include standalone functions
        standalone = [f for f in functions if not f.class_name]
        if standalone:
            new_files.append({
                "name": f"{base_name}_functions.py",
                "category": "standalone",
                "functions": [f.name for f in standalone],
                "estimated_lines": sum(f.line_end - f.line_start + 1 for f in standalone)
            })
        
        return SplitSuggestion(
            original_file=str(file_path),
            new_files=new_files,
            strategy="split_by_class",
            confidence=0.7,
            dependencies=dependencies,
            warnings=["Check for inter-class dependencies"]
        )
    
    def _strategy_split_by_feature(self, file_path: Path, functions: List[TestFunction],
                                 classes: List[TestClass], fixtures: List[TestFunction],
                                 dependencies: Dict, imports: Dict) -> Optional[SplitSuggestion]:
        """Strategy: Split by feature/functionality being tested"""
        
        # Analyze function names to identify features
        features = self._identify_features(functions, classes)
        
        if len(features) < 2:
            return None
        
        new_files = []
        base_name = file_path.stem
        
        for feature, items in features.items():
            new_file_name = f"{base_name}_{feature}.py"
            new_files.append({
                "name": new_file_name,
                "category": "feature_based",
                "feature": feature,
                "functions": [item.name for item in items],
                "estimated_lines": sum(item.line_end - item.line_start + 1 for item in items)
            })
        
        return SplitSuggestion(
            original_file=str(file_path),
            new_files=new_files,
            strategy="split_by_feature",
            confidence=0.6,
            dependencies=dependencies,
            warnings=["Feature grouping is heuristic - review carefully"]
        )
    
    def _identify_features(self, functions: List[TestFunction], 
                          classes: List[TestClass]) -> Dict[str, List]:
        """Identify features being tested based on naming patterns"""
        features = defaultdict(list)
        
        # Common patterns in test names
        patterns = [
            r'test_(\w+)_',  # test_auth_login, test_user_create
            r'test_.*?(\w+)_\w+$',  # test_something_auth, test_something_user
        ]
        
        for func in functions:
            if func.category == 'test':
                feature = self._extract_feature_from_name(func.name)
                features[feature].append(func)
        
        for cls in classes:
            if cls.name.startswith('Test'):
                feature = cls.name[4:].lower()  # Remove 'Test' prefix
                features[feature].extend(cls.methods)
        
        # Remove features with only 1 item
        return {k: v for k, v in features.items() if len(v) > 1}
    
    def _extract_feature_from_name(self, name: str) -> str:
        """Extract feature name from test function name"""
        # Remove test_ prefix
        if name.startswith('test_'):
            name = name[5:]
        
        # Split by underscore and take first meaningful part
        parts = name.split('_')
        if len(parts) > 1:
            return parts[0]
        
        return 'misc'
    
    def _strategy_extract_utilities(self, file_path: Path, functions: List[TestFunction],
                                  classes: List[TestClass], fixtures: List[TestFunction],
                                  dependencies: Dict, imports: Dict) -> Optional[SplitSuggestion]:
        """Strategy: Extract utilities and shared code"""
        
        utilities = []
        utilities.extend([f for f in functions if f.category in ['fixture', 'helper']])
        utilities.extend([f for f in functions if f.name in dependencies["shared_utilities"]])
        
        if not utilities:
            return None
        
        new_files = [{
            "name": f"{file_path.stem}_utilities.py",
            "category": "utilities",
            "functions": [f.name for f in utilities],
            "estimated_lines": sum(f.line_end - f.line_start + 1 for f in utilities)
        }]
        
        return SplitSuggestion(
            original_file=str(file_path),
            new_files=new_files,
            strategy="extract_utilities",
            confidence=0.9,
            dependencies=dependencies,
            warnings=["Verify all dependencies are preserved"]
        )
    
    def generate_split_files(self, suggestion: SplitSuggestion, dry_run: bool = True) -> Dict:
        """Generate the actual split files (dry run by default)"""
        results = {
            "original_file": suggestion.original_file,
            "strategy": suggestion.strategy,
            "generated_files": [],
            "warnings": suggestion.warnings.copy(),
            "dry_run": dry_run
        }
        
        if not dry_run:
            results["warnings"].append("Actual file generation not yet implemented")
            results["warnings"].append("This would require careful AST manipulation")
        
        # For now, just return the plan
        for new_file in suggestion.new_files:
            results["generated_files"].append({
                "name": new_file["name"],
                "content_preview": f"# Generated from {suggestion.original_file}",
                "estimated_lines": new_file.get("estimated_lines", 0)
            })
        
        return results
    
    def validate_split(self, suggestion: SplitSuggestion) -> Dict:
        """Validate a splitting suggestion"""
        validation = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check for circular dependencies
        deps = suggestion.dependencies
        if self._has_circular_dependencies(deps):
            validation["warnings"].append("Potential circular dependencies detected")
        
        # Check file size distribution
        total_estimated = sum(f.get("estimated_lines", 0) for f in suggestion.new_files)
        for new_file in suggestion.new_files:
            if new_file.get("estimated_lines", 0) > 300:
                validation["warnings"].append(
                    f"{new_file['name']} may still exceed line limits"
                )
        
        # Check for orphaned functions
        if suggestion.strategy != "extract_utilities":
            all_functions = set()
            for new_file in suggestion.new_files:
                all_functions.update(new_file.get("functions", []))
            
            # This would need the original function list to validate
            validation["recommendations"].append(
                "Verify all functions are included in the split"
            )
        
        return validation
    
    def _has_circular_dependencies(self, deps: Dict) -> bool:
        """Check for circular dependencies"""
        # Simplified check - would need more sophisticated graph analysis
        func_deps = deps.get("function_to_function", {})
        
        for func, dependencies in func_deps.items():
            for dep in dependencies:
                if func in func_deps.get(dep, set()):
                    return True
        
        return False

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Test refactoring helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_refactor_helper.py analyze app/tests/test_large.py
  python test_refactor_helper.py suggest app/tests/test_large.py --strategy category
  python test_refactor_helper.py validate app/tests/test_large.py
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze file for splitting")
    analyze_parser.add_argument("file", help="Test file to analyze")
    analyze_parser.add_argument("--format", choices=["text", "json"], default="text")
    
    # Suggest command
    suggest_parser = subparsers.add_parser("suggest", help="Generate splitting suggestions")
    suggest_parser.add_argument("file", help="Test file to analyze")
    suggest_parser.add_argument("--strategy", choices=["category", "class", "feature", "utilities"],
                               help="Preferred splitting strategy")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate splitting suggestion")
    validate_parser.add_argument("file", help="Test file to validate")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    helper = TestRefactorHelper()
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist")
        return
    
    if args.command == "analyze":
        result = helper.analyze_file_for_splitting(file_path)
        if args.format == "json":
            import json
            print(json.dumps(result, indent=2))
        else:
            print(f"Analysis for {file_path}:")
            print(f"  Total lines: {result['total_lines']}")
            print(f"  Functions: {result['functions']}")
            print(f"  Classes: {result['classes']}")
            print(f"  Fixtures: {result['fixtures']}")
            print(f"  Strategies: {len(result['strategies'])}")
    
    elif args.command == "suggest":
        result = helper.analyze_file_for_splitting(file_path)
        strategies = result['strategies']
        
        if args.strategy:
            strategies = [s for s in strategies if s.strategy == f"split_by_{args.strategy}"]
        
        print(f"Splitting suggestions for {file_path}:")
        for i, strategy in enumerate(strategies, 1):
            print(f"\n{i}. {strategy.strategy.replace('_', ' ').title()}")
            print(f"   Confidence: {strategy.confidence:.1%}")
            print(f"   New files: {len(strategy.new_files)}")
            for new_file in strategy.new_files:
                print(f"     - {new_file['name']} (~{new_file.get('estimated_lines', '?')} lines)")
    
    elif args.command == "validate":
        result = helper.analyze_file_for_splitting(file_path)
        for strategy in result['strategies']:
            validation = helper.validate_split(strategy)
            print(f"Validation for {strategy.strategy}:")
            print(f"  Valid: {validation['valid']}")
            if validation['warnings']:
                print("  Warnings:")
                for warning in validation['warnings']:
                    print(f"    - {warning}")

if __name__ == "__main__":
    main()