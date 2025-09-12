#!/usr/bin/env python3
"""Generate Method Resolution Order (MRO) Report for Registry Patterns.

This script analyzes all registry implementations in the codebase to identify:
- Inheritance hierarchies
- Method overrides and their resolution paths
- Potential consolidation opportunities
- SSOT violations
"""

import ast
import inspect
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Tuple
import importlib.util

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class RegistryAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze registry class patterns."""
    
    def __init__(self):
        self.registry_classes = {}
        self.current_file = None
        
    def visit_ClassDef(self, node):
        """Extract registry class definitions."""
        if 'Registry' in node.name:
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(f"{base.attr}")
            
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append({
                        'name': item.name,
                        'args': [arg.arg for arg in item.args.args],
                        'is_async': isinstance(item, ast.AsyncFunctionDef)
                    })
            
            self.registry_classes[node.name] = {
                'file': self.current_file,
                'bases': bases,
                'methods': methods,
                'line': node.lineno,
                'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
            }
        
        self.generic_visit(node)
    
    def _get_decorator_name(self, decorator):
        """Extract decorator name."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        return str(decorator)


def analyze_registry_files(root_path: Path) -> Dict:
    """Analyze all Python files for registry patterns."""
    analyzer = RegistryAnalyzer()
    registry_files = []
    
    # Find all Python files
    for py_file in root_path.rglob("*.py"):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'Registry' in content:
                    tree = ast.parse(content, filename=str(py_file))
                    analyzer.current_file = str(py_file.relative_to(root_path))
                    analyzer.visit(tree)
                    registry_files.append(str(py_file.relative_to(root_path)))
        except Exception as e:
            print(f"Error analyzing {py_file}: {e}")
    
    return analyzer.registry_classes, registry_files


def generate_mro_report(registry_classes: Dict) -> str:
    """Generate comprehensive MRO report."""
    report = []
    report.append("# Registry Pattern MRO Analysis Report")
    report.append(f"\nGenerated: {datetime.now(timezone.utc).isoformat()}")
    report.append(f"\n## Summary")
    report.append(f"- Total Registry Classes Found: {len(registry_classes)}")
    report.append(f"- Unique File Locations: {len(set(c['file'] for c in registry_classes.values()))}")
    
    # Group by functionality
    agent_registries = []
    tool_registries = []
    service_registries = []
    other_registries = []
    
    for name, info in registry_classes.items():
        if 'Agent' in name:
            agent_registries.append(name)
        elif 'Tool' in name:
            tool_registries.append(name)
        elif 'Service' in name:
            service_registries.append(name)
        else:
            other_registries.append(name)
    
    report.append(f"\n### Registry Categories:")
    report.append(f"- Agent Registries: {len(agent_registries)}")
    report.append(f"- Tool Registries: {len(tool_registries)}")
    report.append(f"- Service Registries: {len(service_registries)}")
    report.append(f"- Other Registries: {len(other_registries)}")
    
    # Detailed class analysis
    report.append(f"\n## Detailed Registry Analysis")
    
    for category, names in [
        ("Agent Registries", agent_registries),
        ("Tool Registries", tool_registries),
        ("Service Registries", service_registries),
        ("Other Registries", other_registries)
    ]:
        if not names:
            continue
            
        report.append(f"\n### {category}")
        for name in sorted(names):
            info = registry_classes[name]
            report.append(f"\n#### {name}")
            report.append(f"- **Location**: `{info['file']}:{info['line']}`")
            report.append(f"- **Base Classes**: {', '.join(info['bases']) if info['bases'] else 'None'}")
            report.append(f"- **Decorators**: {', '.join(info['decorators']) if info['decorators'] else 'None'}")
            
            # Method analysis
            core_methods = ['register', 'get', 'list', 'remove', 'has', 'clear']
            thread_methods = ['lock', '_lock', 'RLock']
            factory_methods = ['create', 'factory', 'instance']
            
            methods = info['methods']
            method_names = [m['name'] for m in methods]
            
            report.append(f"- **Total Methods**: {len(methods)}")
            report.append(f"- **Core Registry Methods**: {[m for m in core_methods if any(m in mn for mn in method_names)]}")
            report.append(f"- **Thread Safety**: {'Yes' if any(tm in str(methods) for tm in thread_methods) else 'Unknown'}")
            report.append(f"- **Factory Support**: {'Yes' if any(fm in m for fm in factory_methods for m in method_names) else 'No'}")
            
            # List key methods
            key_methods = [m for m in methods if not m['name'].startswith('_') or m['name'] == '__init__'][:10]
            if key_methods:
                report.append("- **Key Methods**:")
                for method in key_methods:
                    async_prefix = "async " if method['is_async'] else ""
                    args_str = ", ".join(method['args'][:3]) + ("..." if len(method['args']) > 3 else "")
                    report.append(f"  - {async_prefix}`{method['name']}({args_str})`")
    
    # Identify duplication patterns
    report.append(f"\n## Duplication Analysis")
    
    # Find similar method signatures
    method_signatures = {}
    for name, info in registry_classes.items():
        for method in info['methods']:
            sig = (method['name'], tuple(method['args']))
            if sig not in method_signatures:
                method_signatures[sig] = []
            method_signatures[sig].append(name)
    
    common_methods = {sig: classes for sig, classes in method_signatures.items() if len(classes) > 1}
    
    if common_methods:
        report.append("\n### Common Method Patterns:")
        for (method_name, args), classes in sorted(common_methods.items(), key=lambda x: -len(x[1]))[:10]:
            if method_name.startswith('_') and method_name != '__init__':
                continue
            report.append(f"- `{method_name}({', '.join(args)})`: Found in {len(classes)} registries")
            for cls in classes[:5]:
                report.append(f"  - {cls}")
            if len(classes) > 5:
                report.append(f"  - ... and {len(classes) - 5} more")
    
    # Consolidation opportunities
    report.append(f"\n## Consolidation Opportunities")
    
    report.append("\n### Potential Generic Base Class Structure:")
    report.append("```python")
    report.append("class UniversalRegistry[T](Generic[T]):")
    report.append("    def __init__(self, registry_name: str):")
    report.append("        self.name = registry_name")
    report.append("        self._items: Dict[str, T] = {}")
    report.append("        self._factories: Dict[str, Callable] = {}")
    report.append("        self._lock = threading.RLock()")
    report.append("    ")
    report.append("    def register(self, key: str, item: T) -> None")
    report.append("    def register_factory(self, key: str, factory: Callable) -> None")
    report.append("    def get(self, key: str, context: Optional[Context] = None) -> T")
    report.append("    def has(self, key: str) -> bool")
    report.append("    def list(self) -> List[str]")
    report.append("    def remove(self, key: str) -> bool")
    report.append("```")
    
    report.append("\n### Recommended Consolidation:")
    report.append("1. **Create UniversalRegistry[T]** - Generic base class")
    report.append("2. **AgentRegistry extends UniversalRegistry[BaseAgent]**")
    report.append("3. **ToolRegistry extends UniversalRegistry[BaseTool]**")
    report.append("4. **ServiceRegistry extends UniversalRegistry[Service]**")
    report.append("5. **Remove all duplicate registry implementations**")
    
    # SSOT violations
    report.append(f"\n## SSOT Violations")
    
    # Group by similar names
    similar_groups = {}
    for name in registry_classes.keys():
        base_name = name.replace('Unified', '').replace('Global', '').replace('Class', '')
        if base_name not in similar_groups:
            similar_groups[base_name] = []
        similar_groups[base_name].append(name)
    
    violations = {k: v for k, v in similar_groups.items() if len(v) > 1}
    
    if violations:
        report.append("\n### Multiple Implementations of Same Concept:")
        for concept, implementations in violations.items():
            report.append(f"\n- **{concept}**: {len(implementations)} implementations")
            for impl in implementations:
                report.append(f"  - {impl} (`{registry_classes[impl]['file']}`)")
    
    return "\n".join(report)


def main():
    """Generate registry MRO report."""
    print("Analyzing registry patterns...")
    
    # Analyze codebase
    registry_classes, registry_files = analyze_registry_files(project_root)
    
    print(f"Found {len(registry_classes)} registry classes in {len(registry_files)} files")
    
    # Generate report
    report = generate_mro_report(registry_classes)
    
    # Save report
    report_path = project_root / "reports" / f"mro_analysis_registry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report saved to: {report_path}")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total Registry Classes: {len(registry_classes)}")
    print(f"Agent Registries: {len([n for n in registry_classes if 'Agent' in n])}")
    print(f"Tool Registries: {len([n for n in registry_classes if 'Tool' in n])}")
    print(f"Service Registries: {len([n for n in registry_classes if 'Service' in n])}")
    
    # Show top duplications
    print("\n=== Key Findings ===")
    agent_registries = [n for n in registry_classes if 'Agent' in n]
    if len(agent_registries) > 1:
        print(f" WARNING: [U+FE0F]  Multiple Agent Registry implementations found: {agent_registries}")
    
    tool_registries = [n for n in registry_classes if 'Tool' in n]
    if len(tool_registries) > 1:
        print(f" WARNING: [U+FE0F]  Multiple Tool Registry implementations found: {tool_registries}")


if __name__ == "__main__":
    main()