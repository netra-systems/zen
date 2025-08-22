#!/usr/bin/env python3
"""
Core AST Scanner for String Literals
Pure scanning logic for extracting string literals from Python source code.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class RawLiteral:
    """Raw string literal extracted from source code."""
    value: str
    file: str
    line: int
    class_context: Optional[str] = None
    function_context: Optional[str] = None
    
    @property
    def context(self) -> str:
        """Generate context string from class and function contexts."""
        parts = []
        if self.class_context:
            parts.append(f"class:{self.class_context}")
        if self.function_context:
            parts.append(f"func:{self.function_context}")
        return '.'.join(parts) if parts else 'module'


class StringLiteralScanner(ast.NodeVisitor):
    """AST visitor to extract string literals with context information."""
    
    def __init__(self, filepath: str):
        """Initialize scanner for a specific file.
        
        Args:
            filepath: Path to the file being scanned (for reference in results)
        """
        self.filepath = filepath
        self.literals: List[RawLiteral] = []
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition, tracking class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition, tracking function context."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_Constant(self, node: ast.Constant) -> None:
        """Visit constant node, extracting string literals."""
        if isinstance(node.value, str) and node.value:
            # Skip potential docstrings (string constants at column 0 inside functions)
            if not (self.current_function and node.col_offset == 0):
                literal = RawLiteral(
                    value=node.value,
                    file=self.filepath,
                    line=node.lineno,
                    class_context=self.current_class,
                    function_context=self.current_function
                )
                self.literals.append(literal)
        
        self.generic_visit(node)


def scan_file(filepath: Path, root_dir: Optional[Path] = None) -> List[RawLiteral]:
    """Scan a single Python file for string literals.
    
    Args:
        filepath: Path to the Python file to scan
        root_dir: Root directory for relative path calculation (optional)
        
    Returns:
        List of RawLiteral objects found in the file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        SyntaxError: If the file contains invalid Python syntax
        UnicodeDecodeError: If the file cannot be decoded as UTF-8
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    if not filepath.suffix == '.py':
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"Cannot decode file {filepath}: {e}")
        
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in {filepath}: {e}")
    
    # Use relative path if root_dir provided, otherwise use absolute path
    if root_dir:
        try:
            relative_path = str(filepath.relative_to(root_dir))
        except ValueError:
            # File is not under root_dir, use absolute path
            relative_path = str(filepath)
    else:
        relative_path = str(filepath)
    
    scanner = StringLiteralScanner(relative_path)
    scanner.visit(tree)
    return scanner.literals


def scan_directory(
    directory: Path, 
    root_dir: Optional[Path] = None,
    exclude_dirs: Optional[set] = None
) -> List[RawLiteral]:
    """Recursively scan directory for string literals in Python files.
    
    Args:
        directory: Directory to scan
        root_dir: Root directory for relative path calculation (optional)
        exclude_dirs: Set of directory names to exclude from scanning
        
    Returns:
        List of all RawLiteral objects found in the directory tree
    """
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.pytest_cache'}
    
    if root_dir is None:
        root_dir = directory
        
    all_literals = []
    
    for item in directory.iterdir():
        if item.is_dir():
            if item.name not in exclude_dirs:
                dir_literals = scan_directory(item, root_dir, exclude_dirs)
                all_literals.extend(dir_literals)
        elif item.suffix == '.py':
            try:
                file_literals = scan_file(item, root_dir)
                all_literals.extend(file_literals)
            except (FileNotFoundError, SyntaxError, UnicodeDecodeError) as e:
                # Log error but continue scanning
                print(f"Warning: Error scanning {item}: {e}")
                continue
    
    return all_literals