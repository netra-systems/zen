"""
AST Analyzer for Async Test Patterns
Analyzes async testing patterns in Python code using AST
Maximum 300 lines, functions  <= 8 lines
"""

import ast
from typing import List

class AsyncPatternAnalyzer(ast.NodeVisitor):
    """AST analyzer for async test patterns"""
    
    def __init__(self):
        self.issues: List[str] = []
        self.async_functions: List[str] = []
        self.pytest_asyncio_decorators: List[int] = []
        self.async_mocks: List[str] = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check async patterns"""
        if self._is_async_function(node):
            self.async_functions.append(node.name)
            self._check_function_patterns(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions"""
        self.async_functions.append(node.name)
        self._check_async_function_patterns(node)
        self.generic_visit(node)
    
    def _is_async_function(self, node: ast.FunctionDef) -> bool:
        """Check if function is async test function"""
        return (node.name.startswith('test_') and 
                any(isinstance(decorator, ast.Name) and 
                    decorator.id == 'asyncio' for decorator in node.decorator_list))
    
    def _check_function_patterns(self, node: ast.FunctionDef) -> None:
        """Check function-level async patterns"""
        self._check_pytest_asyncio_decorator(node)
        self._check_function_length(node)
    
    def _check_async_function_patterns(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function specific patterns"""
        self._check_await_usage(node)
        self._check_exception_handling(node)
    
    def _check_pytest_asyncio_decorator(self, node: ast.FunctionDef) -> None:
        """Check for redundant pytest.mark.asyncio decorators"""
        for decorator in node.decorator_list:
            if (isinstance(decorator, ast.Attribute) and
                isinstance(decorator.value, ast.Attribute) and
                getattr(decorator.value.attr, 'id', None) == 'mark'):
                self.pytest_asyncio_decorators.append(node.lineno)
    
    def _check_function_length(self, node: ast.FunctionDef) -> None:
        """Check function length compliance ( <= 8 lines)"""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            length = node.end_lineno - node.lineno
            if length > 8:
                self.issues.append(f"Function {node.name} exceeds 8 lines ({length})")
    
    def _check_await_usage(self, node: ast.AsyncFunctionDef) -> None:
        """Check proper await usage in async functions"""
        await_count = sum(1 for _ in ast.walk(node) if isinstance(_, ast.Await))
        if await_count == 0:
            self.issues.append(f"Async function {node.name} has no await statements")
    
    def _check_exception_handling(self, node: ast.AsyncFunctionDef) -> None:
        """Check async exception handling patterns"""
        try_blocks = [n for n in ast.walk(node) if isinstance(n, ast.Try)]
        if len(try_blocks) == 0 and 'error' in node.name.lower():
            self.issues.append(f"Error test {node.name} should have exception handling")
    
    def _check_async_patterns(self, node: ast.AsyncFunctionDef) -> List[str]:
        """Check comprehensive async patterns"""
        issues = []
        issues.extend(self._check_await_patterns(node))
        issues.extend(self._check_exception_patterns(node))
        issues.extend(self._check_resource_patterns(node))
        return issues
    
    def _check_await_patterns(self, node: ast.AsyncFunctionDef) -> List[str]:
        """Check await usage patterns"""
        await_count = sum(1 for _ in ast.walk(node) if isinstance(_, ast.Await))
        if await_count == 0:
            return [f"Async function {node.name} has no await statements"]
        return []
    
    def _check_exception_patterns(self, node: ast.AsyncFunctionDef) -> List[str]:
        """Check exception handling patterns"""
        try_blocks = [n for n in ast.walk(node) if isinstance(n, ast.Try)]
        if len(try_blocks) == 0 and 'error' in node.name.lower():
            return [f"Error test {node.name} should have exception handling"]
        return []
    
    def _check_resource_patterns(self, node: ast.AsyncFunctionDef) -> List[str]:
        """Check resource cleanup patterns"""
        async_with_blocks = [n for n in ast.walk(node) if isinstance(n, ast.AsyncWith)]
        resource_keywords = ['client', 'connection']
        if (len(async_with_blocks) == 0 and 
            any(keyword in node.name.lower() for keyword in resource_keywords)):
            return [f"Resource test {node.name} should use async context managers"]
        return []