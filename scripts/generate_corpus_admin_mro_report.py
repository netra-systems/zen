#!/usr/bin/env python3
"""
Generate MRO (Method Resolution Order) report for Corpus Admin module
As required by CLAUDE.md section 3.6
"""
import ast
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

class CorpusAdminMROAnalyzer:
    def __init__(self):
        self.classes: Dict[str, Dict] = {}
        self.inheritance_map: Dict[str, List[str]] = {}
        self.method_overrides: Dict[str, Dict[str, List[str]]] = {}
        self.files_analyzed = []
        
    def analyze_file(self, filepath: Path):
        """Analyze a Python file for classes and inheritance"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(filepath))
            relative_path = filepath.relative_to(project_root)
            self.files_analyzed.append(str(relative_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = f"{relative_path.stem}.{node.name}"
                    
                    # Extract base classes
                    bases = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            bases.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            bases.append(f"{base.value.id if isinstance(base.value, ast.Name) else '?'}.{base.attr}")
                    
                    # Extract methods
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                    
                    self.classes[class_name] = {
                        'file': str(relative_path),
                        'line': node.lineno,
                        'bases': bases,
                        'methods': methods
                    }
                    
                    self.inheritance_map[class_name] = bases
                    
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
    
    def build_hierarchy(self) -> str:
        """Build inheritance hierarchy visualization"""
        output = []
        output.append("## Current Inheritance Hierarchy\n")
        
        # Find root classes (no bases or only external bases)
        roots = []
        for class_name, info in self.classes.items():
            if not info['bases'] or all('.' not in base for base in info['bases']):
                roots.append(class_name)
        
        # Build tree for each root
        for root in sorted(roots):
            output.append(f"- **{root}** ({self.classes[root]['file']}:{self.classes[root]['line']})")
            self._add_children(root, output, indent=2)
        
        return '\n'.join(output)
    
    def _add_children(self, parent: str, output: List[str], indent: int):
        """Recursively add children to hierarchy"""
        children = []
        parent_simple = parent.split('.')[-1]
        
        for class_name, info in self.classes.items():
            if parent_simple in info['bases'] or parent in info['bases']:
                children.append(class_name)
        
        for child in sorted(children):
            info = self.classes[child]
            overrides = [m for m in info['methods'] if m in self._get_parent_methods(child)]
            override_str = f" (overrides: {', '.join(overrides)})" if overrides else ""
            output.append(f"{' ' * indent}- **{child}**{override_str} ({info['file']}:{info['line']})")
            self._add_children(child, output, indent + 2)
    
    def _get_parent_methods(self, class_name: str) -> Set[str]:
        """Get all methods from parent classes"""
        methods = set()
        info = self.classes.get(class_name, {})
        
        for base in info.get('bases', []):
            # Look for base in our classes
            for cls_name, cls_info in self.classes.items():
                if cls_name.endswith(base) or cls_name == base:
                    methods.update(cls_info['methods'])
                    methods.update(self._get_parent_methods(cls_name))
        
        return methods
    
    def analyze_method_resolution(self) -> str:
        """Analyze method resolution paths"""
        output = []
        output.append("\n## Method Resolution Analysis\n")
        
        # Group classes by common patterns
        handlers = []
        validators = []
        operations = []
        models = []
        others = []
        
        for class_name in self.classes:
            if 'handler' in class_name.lower():
                handlers.append(class_name)
            elif 'validator' in class_name.lower():
                validators.append(class_name)
            elif 'operation' in class_name.lower():
                operations.append(class_name)
            elif 'model' in class_name.lower():
                models.append(class_name)
            else:
                others.append(class_name)
        
        # Analyze each group
        for group_name, group in [
            ("Handlers", handlers),
            ("Validators", validators),
            ("Operations", operations),
            ("Models", models),
            ("Others", others)
        ]:
            if group:
                output.append(f"\n### {group_name}\n")
                for class_name in sorted(group):
                    info = self.classes[class_name]
                    output.append(f"- **{class_name}**")
                    output.append(f"  - Methods: {', '.join(info['methods'][:5])}{'...' if len(info['methods']) > 5 else ''}")
                    if info['bases']:
                        output.append(f"  - Inherits from: {', '.join(info['bases'])}")
        
        return '\n'.join(output)
    
    def identify_issues(self) -> str:
        """Identify potential issues in the inheritance structure"""
        output = []
        output.append("\n## Potential Issues and Refactoring Opportunities\n")
        
        # Check for multiple inheritance (potential diamond problem)
        multiple_inheritance = []
        for class_name, info in self.classes.items():
            if len(info['bases']) > 1:
                multiple_inheritance.append((class_name, info['bases']))
        
        if multiple_inheritance:
            output.append("\n### Multiple Inheritance Detected")
            for class_name, bases in multiple_inheritance:
                output.append(f"- **{class_name}** inherits from: {', '.join(bases)}")
        
        # Check for deep inheritance chains
        deep_chains = []
        for class_name in self.classes:
            depth = self._get_inheritance_depth(class_name)
            if depth > 3:
                deep_chains.append((class_name, depth))
        
        if deep_chains:
            output.append("\n### Deep Inheritance Chains")
            for class_name, depth in sorted(deep_chains, key=lambda x: x[1], reverse=True):
                output.append(f"- **{class_name}** - depth: {depth}")
        
        # Check for method shadowing
        shadowing = []
        for class_name, info in self.classes.items():
            parent_methods = self._get_parent_methods(class_name)
            shadowed = [m for m in info['methods'] if m in parent_methods]
            if shadowed and not shadowed == ['__init__']:
                shadowing.append((class_name, shadowed))
        
        if shadowing:
            output.append("\n### Method Shadowing/Overrides")
            for class_name, methods in shadowing:
                output.append(f"- **{class_name}** overrides: {', '.join(methods)}")
        
        return '\n'.join(output)
    
    def _get_inheritance_depth(self, class_name: str, visited: Set[str] = None) -> int:
        """Calculate inheritance depth for a class"""
        if visited is None:
            visited = set()
        
        if class_name in visited:
            return 0
        
        visited.add(class_name)
        info = self.classes.get(class_name, {})
        
        if not info.get('bases'):
            return 1
        
        max_depth = 0
        for base in info['bases']:
            for cls_name in self.classes:
                if cls_name.endswith(base) or cls_name == base:
                    depth = self._get_inheritance_depth(cls_name, visited)
                    max_depth = max(max_depth, depth)
        
        return max_depth + 1
    
    def generate_report(self) -> str:
        """Generate complete MRO report"""
        output = []
        output.append(f"# MRO Analysis: Corpus Admin Module")
        output.append(f"**Generated:** {datetime.now().isoformat()}")
        output.append(f"**Files Analyzed:** {len(self.files_analyzed)}")
        output.append(f"**Classes Found:** {len(self.classes)}\n")
        
        output.append(self.build_hierarchy())
        output.append(self.analyze_method_resolution())
        output.append(self.identify_issues())
        
        output.append("\n## Refactoring Impact Analysis\n")
        output.append("### Breaking Changes Expected")
        output.append("- All imports from `netra_backend.app.agents.corpus_admin.*` will need updating")
        output.append("- All imports from `netra_backend.app.agents.admin_tool_dispatcher.corpus*` will need updating")
        output.append("- Tool registration patterns may need adjustment")
        output.append("- WebSocket event handlers for corpus operations need validation")
        
        output.append("\n### Migration Strategy")
        output.append("1. Create `netra_backend/app/admin/corpus/` directory")
        output.append("2. Implement `UnifiedCorpusAdminFactory` with user isolation")
        output.append("3. Consolidate all corpus operations into `UnifiedCorpusAdmin` class")
        output.append("4. Implement factory pattern for multi-user isolation")
        output.append("5. Update all imports across the codebase")
        output.append("6. Remove legacy files after validation")
        
        output.append("\n## Files to Consolidate\n")
        for filepath in sorted(self.files_analyzed):
            output.append(f"- `{filepath}`")
        
        return '\n'.join(output)

def main():
    analyzer = CorpusAdminMROAnalyzer()
    
    # Find all corpus admin related files
    corpus_paths = []
    
    # Corpus admin directory
    corpus_admin_dir = project_root / "netra_backend/app/agents/corpus_admin"
    if corpus_admin_dir.exists():
        corpus_paths.extend(corpus_admin_dir.glob("**/*.py"))
    
    # Admin tool dispatcher corpus files
    admin_dispatcher_dir = project_root / "netra_backend/app/agents/admin_tool_dispatcher"
    if admin_dispatcher_dir.exists():
        corpus_paths.extend(admin_dispatcher_dir.glob("corpus*.py"))
    
    # Corpus admin sub agent
    corpus_sub_agent = project_root / "netra_backend/app/agents/corpus_admin_sub_agent.py"
    if corpus_sub_agent.exists():
        corpus_paths.append(corpus_sub_agent)
    
    print(f"Analyzing {len(corpus_paths)} corpus admin files...")
    
    # Analyze each file
    for filepath in corpus_paths:
        analyzer.analyze_file(filepath)
    
    # Generate report
    report = analyzer.generate_report()
    
    # Save report
    report_path = project_root / f"reports/mro_analysis_corpus_admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nMRO Report generated: {report_path}")
    print("\nSummary:")
    print(f"- Files analyzed: {len(analyzer.files_analyzed)}")
    print(f"- Classes found: {len(analyzer.classes)}")
    
    return report_path

if __name__ == "__main__":
    report_path = main()
    # Also print the report
    with open(report_path, 'r') as f:
        print("\n" + "="*80)
        print(f.read())