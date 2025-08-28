"""
Symbol Extraction Service - Extracts symbols from code files for Go to Symbol functionality
Supports Python, JavaScript, and TypeScript files
"""

import ast
import re
from typing import Dict, List, Optional
from pathlib import Path

from netra_backend.app.logging_config import central_logger


class SymbolType:
    """Symbol type constants"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    INTERFACE = "interface"
    TYPE = "type"
    ENUM = "enum"
    CONST = "const"


class Symbol:
    """Represents a code symbol"""
    
    def __init__(self, name: str, symbol_type: str, line: int, 
                 parent: Optional[str] = None, signature: Optional[str] = None):
        self.name = name
        self.type = symbol_type
        self.line = line
        self.parent = parent
        self.signature = signature
        self.full_name = f"{parent}.{name}" if parent else name
    
    def to_dict(self) -> Dict:
        """Convert symbol to dictionary"""
        return {
            "name": self.name,
            "type": self.type,
            "line": self.line,
            "parent": self.parent,
            "signature": self.signature,
            "full_name": self.full_name
        }


class PythonSymbolExtractor:
    """Extracts symbols from Python files using AST"""
    
    def extract(self, content: str, filename: str) -> List[Symbol]:
        """Extract symbols from Python code"""
        try:
            tree = ast.parse(content, filename=filename)
            symbols = []
            self._visit_node(tree, symbols, parent=None)
            return symbols
        except SyntaxError as e:
            central_logger.warning(f"Failed to parse Python file {filename}: {e}")
            return []
    
    def _visit_node(self, node, symbols: List[Symbol], parent: Optional[str] = None):
        """Recursively visit AST nodes to extract symbols"""
        for item in node.body if hasattr(node, 'body') else []:
            if isinstance(item, ast.ClassDef):
                symbol = Symbol(
                    name=item.name,
                    symbol_type=SymbolType.CLASS,
                    line=item.lineno,
                    parent=parent
                )
                symbols.append(symbol)
                # Visit class methods
                for subitem in item.body:
                    if isinstance(subitem, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method = Symbol(
                            name=subitem.name,
                            symbol_type=SymbolType.METHOD,
                            line=subitem.lineno,
                            parent=item.name,
                            signature=self._get_function_signature(subitem)
                        )
                        symbols.append(method)
            
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and parent is None:
                symbol = Symbol(
                    name=item.name,
                    symbol_type=SymbolType.FUNCTION,
                    line=item.lineno,
                    signature=self._get_function_signature(item)
                )
                symbols.append(symbol)
            
            elif isinstance(item, ast.Assign) and parent is None:
                # Extract top-level variables
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        symbol = Symbol(
                            name=target.id,
                            symbol_type=SymbolType.VARIABLE,
                            line=item.lineno
                        )
                        symbols.append(symbol)
    
    def _get_function_signature(self, func_node) -> str:
        """Extract function signature from FunctionDef or AsyncFunctionDef"""
        args = []
        for arg in func_node.args.args:
            args.append(arg.arg)
        return f"({', '.join(args)})"


class JavaScriptSymbolExtractor:
    """Extracts symbols from JavaScript/TypeScript files using regex"""
    
    def __init__(self):
        # Regex patterns for JavaScript/TypeScript symbols
        self.patterns = {
            SymbolType.CLASS: re.compile(r'^\s*(?:export\s+)?class\s+(\w+)', re.MULTILINE),
            SymbolType.FUNCTION: re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', re.MULTILINE),
            SymbolType.CONST: re.compile(r'^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]*)=>', re.MULTILINE),
            SymbolType.INTERFACE: re.compile(r'^\s*(?:export\s+)?interface\s+(\w+)', re.MULTILINE),
            SymbolType.TYPE: re.compile(r'^\s*(?:export\s+)?type\s+(\w+)', re.MULTILINE),
            SymbolType.ENUM: re.compile(r'^\s*(?:export\s+)?enum\s+(\w+)', re.MULTILINE),
        }
        
        # Pattern for class methods
        self.method_pattern = re.compile(r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{', re.MULTILINE)
    
    def extract(self, content: str, filename: str) -> List[Symbol]:
        """Extract symbols from JavaScript/TypeScript code"""
        symbols = []
        lines = content.split('\n')
        
        # Extract classes and track their line ranges
        class_ranges = self._extract_class_ranges(content, lines)
        
        # Extract all symbols
        for symbol_type, pattern in self.patterns.items():
            for match in pattern.finditer(content):
                name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1
                
                # Check if symbol is inside a class
                parent_class = self._find_parent_class(line_num, class_ranges)
                
                symbol = Symbol(
                    name=name,
                    symbol_type=symbol_type,
                    line=line_num,
                    parent=parent_class
                )
                symbols.append(symbol)
        
        # Extract methods from classes
        for class_name, (start_line, end_line) in class_ranges.items():
            class_content = '\n'.join(lines[start_line-1:end_line])
            for match in self.method_pattern.finditer(class_content):
                method_name = match.group(1)
                if method_name not in ['constructor', 'if', 'for', 'while', 'switch']:
                    relative_line = class_content[:match.start()].count('\n')
                    actual_line = start_line + relative_line
                    
                    symbol = Symbol(
                        name=method_name,
                        symbol_type=SymbolType.METHOD,
                        line=actual_line,
                        parent=class_name
                    )
                    symbols.append(symbol)
        
        return symbols
    
    def _extract_class_ranges(self, content: str, lines: List[str]) -> Dict[str, tuple]:
        """Extract class names and their line ranges"""
        class_ranges = {}
        class_pattern = re.compile(r'^\s*(?:export\s+)?class\s+(\w+)', re.MULTILINE)
        
        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            start_line = content[:match.start()].count('\n') + 1
            
            # Find end of class by counting braces
            brace_count = 0
            found_start = False
            end_line = start_line
            
            for i in range(start_line - 1, len(lines)):
                line = lines[i]
                for char in line:
                    if char == '{':
                        brace_count += 1
                        found_start = True
                    elif char == '}':
                        brace_count -= 1
                
                if found_start and brace_count == 0:
                    end_line = i + 1
                    break
            
            class_ranges[class_name] = (start_line, end_line)
        
        return class_ranges
    
    def _find_parent_class(self, line_num: int, class_ranges: Dict[str, tuple]) -> Optional[str]:
        """Find if a line number is inside a class"""
        for class_name, (start, end) in class_ranges.items():
            if start <= line_num <= end:
                return class_name
        return None


class SymbolExtractor:
    """Main symbol extraction service"""
    
    def __init__(self):
        self.python_extractor = PythonSymbolExtractor()
        self.js_extractor = JavaScriptSymbolExtractor()
    
    def extract_symbols(self, content: str, filename: str) -> List[Symbol]:
        """Extract symbols based on file type"""
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        if extension in ['.py']:
            return self.python_extractor.extract(content, filename)
        elif extension in ['.js', '.jsx', '.ts', '.tsx', '.mjs']:
            return self.js_extractor.extract(content, filename)
        else:
            central_logger.debug(f"Unsupported file type for symbol extraction: {extension}")
            return []
    
    def extract_symbols_from_dict(self, document: Dict) -> List[Dict]:
        """Extract symbols from a document dictionary"""
        filename = document.get("filename", "")
        content = document.get("content", "")
        
        if not filename or not content:
            return []
        
        symbols = self.extract_symbols(content, filename)
        return [s.to_dict() for s in symbols]


# Singleton instance
symbol_extractor = SymbolExtractor()