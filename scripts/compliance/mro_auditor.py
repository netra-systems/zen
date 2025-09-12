#!/usr/bin/env python3
"""
MRO (Method Resolution Order) Auditor for Architecture Compliance
Analyzes inheritance complexity, method shadowing, and diamond patterns.

CRITICAL: Per CLAUDE.md 3.6 - Required for complex refactoring validation
"""

import ast
import inspect
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from scripts.compliance.core import Violation


@dataclass
class MROAnalysisResult:
    """Result of MRO analysis for a single class"""
    class_name: str
    file_path: str
    mro_depth: int
    parent_classes: List[str]
    method_shadows: Dict[str, List[str]]  # method -> [shadowed_classes]
    diamond_patterns: List[str]
    complexity_score: float
    violations: List[Violation]


class MROAuditor:
    """Audits Method Resolution Order complexity in Python codebases"""
    
    # Thresholds per CLAUDE.md
    MAX_MRO_DEPTH = 5  # Deep inheritance is code smell
    MAX_PARENT_CLASSES = 3  # Multiple inheritance complexity
    MAX_METHOD_SHADOWS = 5  # Method override complexity
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.analysis_cache = {}
        self.violations = []
        
    def audit_file(self, file_path: Path) -> List[MROAnalysisResult]:
        """Audit a Python file for MRO complexity"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, str(file_path))
            return self._analyze_ast(tree, file_path)
        except Exception as e:
            # Return empty list on parse errors
            return []
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path) -> List[MROAnalysisResult]:
        """Analyze AST for class definitions and their MRO"""
        results = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                result = self._analyze_class(node, file_path)
                if result:
                    results.append(result)
        
        return results
    
    def _analyze_class(self, node: ast.ClassDef, file_path: Path) -> Optional[MROAnalysisResult]:
        """Analyze a single class definition"""
        class_name = node.name
        parent_classes = self._extract_parents(node)
        
        # Extract methods from this class
        methods = self._extract_methods(node)
        
        # Calculate MRO depth (approximation from AST)
        mro_depth = self._estimate_mro_depth(parent_classes)
        
        # Detect method shadowing
        method_shadows = self._detect_shadows(methods, parent_classes)
        
        # Detect diamond patterns
        diamond_patterns = self._detect_diamonds(parent_classes)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(
            mro_depth, len(parent_classes), len(method_shadows), len(diamond_patterns)
        )
        
        # Generate violations
        violations = self._generate_violations(
            class_name, file_path, mro_depth, parent_classes, 
            method_shadows, diamond_patterns, complexity_score
        )
        
        return MROAnalysisResult(
            class_name=class_name,
            file_path=str(file_path),
            mro_depth=mro_depth,
            parent_classes=parent_classes,
            method_shadows=method_shadows,
            diamond_patterns=diamond_patterns,
            complexity_score=complexity_score,
            violations=violations
        )
    
    def _extract_parents(self, node: ast.ClassDef) -> List[str]:
        """Extract parent class names from ClassDef"""
        parents = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                parents.append(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle module.ClassName
                parts = []
                current = base
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                parents.append('.'.join(reversed(parts)))
        return parents
    
    def _extract_methods(self, node: ast.ClassDef) -> Set[str]:
        """Extract method names from class definition"""
        methods = set()
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.add(item.name)
        return methods
    
    def _estimate_mro_depth(self, parent_classes: List[str]) -> int:
        """Estimate MRO depth from parent classes"""
        # Base estimate: 1 for object, 1 for self, + parents
        base_depth = 2
        
        # Known deep hierarchies in the codebase
        deep_bases = {
            'BaseAgent': 3,
            'BaseAgent': 4,
            'AgentLifecycleMixin': 2,
            'WebSocketBridgeAdapter': 2
        }
        
        max_parent_depth = 0
        for parent in parent_classes:
            parent_name = parent.split('.')[-1]
            max_parent_depth = max(max_parent_depth, deep_bases.get(parent_name, 1))
        
        return base_depth + max_parent_depth
    
    def _detect_shadows(self, methods: Set[str], parents: List[str]) -> Dict[str, List[str]]:
        """Detect potential method shadowing"""
        # Common methods that are likely overridden
        common_overrides = {
            '__init__', '__str__', '__repr__', 'execute', 'process',
            'validate', 'setup', 'teardown', 'cleanup'
        }
        
        shadows = {}
        for method in methods:
            if method in common_overrides and parents:
                # Assume shadowing if method is common and has parents
                shadows[method] = parents[:2]  # First 2 parents most likely
        
        return shadows
    
    def _detect_diamonds(self, parents: List[str]) -> List[str]:
        """Detect potential diamond inheritance patterns"""
        diamonds = []
        
        # Known diamond patterns in the codebase
        if len(parents) >= 2:
            # Check for common base classes that create diamonds
            common_bases = {'BaseAgent', 'BaseAgent'}
            parent_names = {p.split('.')[-1] for p in parents}
            
            if len(parent_names & common_bases) >= 2:
                diamonds.append(f"Multiple inheritance from: {', '.join(parent_names & common_bases)}")
        
        return diamonds
    
    def _calculate_complexity(self, mro_depth: int, parent_count: int, 
                             shadow_count: int, diamond_count: int) -> float:
        """Calculate overall MRO complexity score (0-100)"""
        # Weighted scoring
        depth_score = min(mro_depth / self.MAX_MRO_DEPTH, 1.0) * 30
        parent_score = min(parent_count / self.MAX_PARENT_CLASSES, 1.0) * 25
        shadow_score = min(shadow_count / self.MAX_METHOD_SHADOWS, 1.0) * 25
        diamond_score = min(diamond_count, 1.0) * 20
        
        return depth_score + parent_score + shadow_score + diamond_score
    
    def _generate_violations(self, class_name: str, file_path: Path,
                           mro_depth: int, parents: List[str],
                           shadows: Dict[str, List[str]], 
                           diamonds: List[str],
                           complexity: float) -> List[Violation]:
        """Generate violations based on analysis"""
        violations = []
        
        # Check MRO depth
        if mro_depth > self.MAX_MRO_DEPTH:
            violations.append(Violation(
                file_path=str(file_path),
                violation_type="mro_depth_exceeded",
                severity="high",
                actual_value=mro_depth,
                expected_value=self.MAX_MRO_DEPTH,
                description=f"Class {class_name} has MRO depth of {mro_depth}",
                fix_suggestion="Reduce inheritance depth by composing instead of inheriting",
                business_impact="Deep inheritance makes code harder to maintain and debug",
                category="inheritance_complexity"
            ))
        
        # Check multiple inheritance
        if len(parents) > self.MAX_PARENT_CLASSES:
            violations.append(Violation(
                file_path=str(file_path),
                violation_type="multiple_inheritance_complexity",
                severity="high" if len(parents) > 4 else "medium",
                actual_value=len(parents),
                expected_value=self.MAX_PARENT_CLASSES,
                description=f"Class {class_name} inherits from {len(parents)} parents",
                fix_suggestion="Use composition or mixins instead of multiple inheritance",
                business_impact="Multiple inheritance increases complexity and potential for bugs",
                category="inheritance_complexity"
            ))
        
        # Check method shadowing
        if len(shadows) > self.MAX_METHOD_SHADOWS:
            violations.append(Violation(
                file_path=str(file_path),
                violation_type="excessive_method_shadowing",
                severity="medium",
                actual_value=len(shadows),
                expected_value=self.MAX_METHOD_SHADOWS,
                description=f"Class {class_name} shadows {len(shadows)} methods",
                fix_suggestion="Review method overrides, ensure super() calls are correct",
                business_impact="Method shadowing can cause unexpected behavior",
                category="inheritance_complexity"
            ))
        
        # Check diamond patterns
        if diamonds:
            violations.append(Violation(
                file_path=str(file_path),
                violation_type="diamond_inheritance_pattern",
                severity="critical",
                description=f"Class {class_name} has diamond inheritance: {diamonds[0]}",
                fix_suggestion="Refactor to avoid diamond pattern, use composition",
                business_impact="Diamond inheritance causes method resolution ambiguity",
                category="inheritance_complexity"
            ))
        
        # High complexity warning
        if complexity > 70:
            violations.append(Violation(
                file_path=str(file_path),
                violation_type="high_mro_complexity",
                severity="high" if complexity > 85 else "medium",
                actual_value=int(complexity),
                expected_value=70,
                description=f"Class {class_name} has high MRO complexity score",
                fix_suggestion="Consider refactoring to reduce inheritance complexity",
                business_impact="Complex inheritance hierarchies are hard to maintain",
                category="inheritance_complexity"
            ))
        
        return violations
    
    def audit_module(self, module_path: Path) -> Dict[str, Any]:
        """Audit an entire module for MRO issues"""
        all_results = []
        all_violations = []
        
        # Find all Python files
        py_files = list(module_path.rglob("*.py"))
        
        for py_file in py_files:
            if "__pycache__" not in str(py_file):
                results = self.audit_file(py_file)
                all_results.extend(results)
                for result in results:
                    all_violations.extend(result.violations)
        
        # Generate summary
        summary = {
            "total_classes_analyzed": len(all_results),
            "total_violations": len(all_violations),
            "critical_violations": len([v for v in all_violations if v.severity == "critical"]),
            "high_violations": len([v for v in all_violations if v.severity == "high"]),
            "medium_violations": len([v for v in all_violations if v.severity == "medium"]),
            "classes_with_issues": [r.class_name for r in all_results if r.violations],
            "diamond_patterns": sum(len(r.diamond_patterns) for r in all_results),
            "average_complexity": sum(r.complexity_score for r in all_results) / len(all_results) if all_results else 0
        }
        
        return {
            "summary": summary,
            "results": all_results,
            "violations": all_violations
        }
    
    def generate_report(self, results: List[MROAnalysisResult]) -> str:
        """Generate human-readable MRO audit report"""
        lines = ["# MRO Complexity Audit Report\n"]
        
        if not results:
            lines.append("No classes analyzed.\n")
            return "\n".join(lines)
        
        # Summary stats
        total_violations = sum(len(r.violations) for r in results)
        critical_count = sum(1 for r in results for v in r.violations if v.severity == "critical")
        high_count = sum(1 for r in results for v in r.violations if v.severity == "high")
        
        lines.append("## Summary\n")
        lines.append(f"- Classes Analyzed: {len(results)}")
        lines.append(f"- Total Violations: {total_violations}")
        lines.append(f"- Critical Issues: {critical_count}")
        lines.append(f"- High Severity Issues: {high_count}\n")
        
        # Critical issues first
        if critical_count > 0:
            lines.append("## [U+1F534] Critical Issues\n")
            for result in results:
                for violation in result.violations:
                    if violation.severity == "critical":
                        lines.append(f"- **{result.class_name}** ({result.file_path})")
                        lines.append(f"  - {violation.description}")
                        lines.append(f"  - Fix: {violation.fix_suggestion}\n")
        
        # High complexity classes
        high_complexity = [r for r in results if r.complexity_score > 70]
        if high_complexity:
            lines.append("##  WARNING: [U+FE0F] High Complexity Classes\n")
            for result in sorted(high_complexity, key=lambda x: x.complexity_score, reverse=True)[:10]:
                lines.append(f"- **{result.class_name}** (Score: {result.complexity_score:.1f})")
                lines.append(f"  - MRO Depth: {result.mro_depth}")
                lines.append(f"  - Parents: {', '.join(result.parent_classes)}")
                if result.diamond_patterns:
                    lines.append(f"  -  WARNING: [U+FE0F] Diamond Pattern Detected")
                lines.append("")
        
        return "\n".join(lines)