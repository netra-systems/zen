#!/usr/bin/env python3
"""
Autonomous Test Review System - Ultra Thinking Analyzer
Deep semantic analysis capabilities for understanding testing needs
"""

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set


class UltraThinkingAnalyzer:
    """Ultra-thinking capabilities for deep test analysis"""
    
    def __init__(self):
        self.ast_cache = {}
        self.dependency_graph = defaultdict(set)
        self.semantic_model = {}
        
    async def analyze_code_semantics(self, file_path: Path) -> Dict[str, Any]:
        """Deep semantic analysis of code to understand testing needs"""
        if not file_path.exists():
            return {}
            
        content = file_path.read_text(encoding='utf-8', errors='replace')
        
        # Parse AST
        try:
            tree = ast.parse(content)
            self.ast_cache[str(file_path)] = tree
        except SyntaxError:
            return {}
        
        # Extract semantic information
        semantics = {
            "functions": [],
            "classes": [],
            "complexity": 0,
            "dependencies": [],
            "business_logic": [],
            "critical_paths": [],
            "error_handlers": [],
            "data_validators": []
        }
        
        # Analyze AST nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = self._analyze_function(node)
                semantics["functions"].append(func_info)
                semantics["complexity"] += func_info["complexity"]
                
            elif isinstance(node, ast.ClassDef):
                class_info = self._analyze_class(node)
                semantics["classes"].append(class_info)
                
            elif isinstance(node, ast.Try):
                semantics["error_handlers"].append(self._extract_error_handler(node))
                
            elif isinstance(node, ast.If):
                # Detect validation patterns
                if self._is_validation_pattern(node):
                    semantics["data_validators"].append(self._extract_validator(node))
        
        # Identify critical paths
        semantics["critical_paths"] = self._identify_critical_paths(tree)
        
        # Extract business logic from comments and docstrings
        semantics["business_logic"] = self._extract_business_logic(content)
        
        return semantics
    
    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a function node for testing requirements"""
        return {
            "name": node.name,
            "args": [arg.arg for arg in node.args.args],
            "complexity": self._calculate_complexity(node),
            "has_return": any(isinstance(n, ast.Return) for n in ast.walk(node)),
            "has_side_effects": self._has_side_effects(node),
            "test_priority": self._calculate_test_priority(node)
        }
    
    def _analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Analyze a class node for testing requirements"""
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        return {
            "name": node.name,
            "methods": [m.name for m in methods],
            "inherits": [base.id for base in node.bases if hasattr(base, 'id')],
            "test_complexity": len(methods) * 2
        }
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _has_side_effects(self, node: ast.AST) -> bool:
        """Check if function has side effects"""
        for child in ast.walk(node):
            if isinstance(child, (ast.Assign, ast.AugAssign, ast.Delete)):
                return True
            if isinstance(child, ast.Call):
                # Check for common side-effect functions
                if hasattr(child.func, 'id') and child.func.id in ['print', 'write', 'send', 'save', 'delete']:
                    return True
        return False
    
    def _calculate_test_priority(self, node: ast.FunctionDef) -> int:
        """Calculate testing priority based on various factors"""
        priority = 0
        
        # Public functions have higher priority
        if not node.name.startswith('_'):
            priority += 3
            
        # Complex functions need more testing
        priority += self._calculate_complexity(node)
        
        # Functions with error handling are critical
        if any(isinstance(n, ast.Try) for n in ast.walk(node)):
            priority += 2
            
        # Functions with returns need output validation
        if any(isinstance(n, ast.Return) for n in ast.walk(node)):
            priority += 1
            
        return priority
    
    def _is_validation_pattern(self, node: ast.If) -> bool:
        """Detect if an if statement is a validation pattern"""
        # Look for common validation patterns
        if hasattr(node.test, 'ops'):
            for op in node.test.ops:
                if isinstance(op, (ast.Is, ast.IsNot, ast.In, ast.NotIn)):
                    return True
        return False
    
    def _extract_validator(self, node: ast.If) -> str:
        """Extract validation logic description"""
        return f"Validation at line {node.lineno}"
    
    def _extract_error_handler(self, node: ast.Try) -> str:
        """Extract error handling information"""
        handlers = []
        for handler in node.handlers:
            if handler.type:
                handlers.append(ast.unparse(handler.type) if hasattr(ast, 'unparse') else str(handler.type))
        return f"Error handling for: {', '.join(handlers)}"
    
    def _identify_critical_paths(self, tree: ast.AST) -> List[str]:
        """Identify critical execution paths that must be tested"""
        critical = []
        
        # Find main entry points
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # API endpoints, main functions, etc.
                if node.name in ['main', 'run', 'execute', 'process', 'handle']:
                    critical.append(f"Entry point: {node.name}")
                    
                # Authentication/security functions
                if any(keyword in node.name.lower() for keyword in ['auth', 'login', 'security', 'validate', 'verify']):
                    critical.append(f"Security function: {node.name}")
                    
                # Data manipulation
                if any(keyword in node.name.lower() for keyword in ['save', 'delete', 'update', 'create']):
                    critical.append(f"Data operation: {node.name}")
                    
        return critical
    
    def _extract_business_logic(self, content: str) -> List[str]:
        """Extract business logic from comments and docstrings"""
        logic = []
        
        # Extract from docstrings
        docstring_pattern = r'"""(.*?)"""'
        docstrings = re.findall(docstring_pattern, content, re.DOTALL)
        for doc in docstrings:
            if any(keyword in doc.lower() for keyword in ['business', 'requirement', 'rule', 'must', 'should']):
                logic.append(doc.strip()[:100])  # First 100 chars
                
        # Extract from comments
        comment_lines = [line.strip() for line in content.split('\n') if line.strip().startswith('#')]
        for comment in comment_lines:
            if any(keyword in comment.lower() for keyword in ['todo', 'fixme', 'important', 'critical']):
                logic.append(comment[1:].strip())
                
        return logic