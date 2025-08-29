"""
Symbol Extraction Service - Extracts symbols from code files for Go to Symbol functionality
Supports Python, JavaScript, and TypeScript files
Enhanced with advanced symbol extraction, reference tracking, and navigation capabilities
"""

import ast
import re
from typing import Dict, List, Optional, Tuple, Set, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger


class SymbolType(Enum):
    """Enhanced symbol type constants"""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    INTERFACE = "interface"
    TYPE = "type"
    ENUM = "enum"
    CONST = "const"
    PROPERTY = "property"
    DECORATOR = "decorator"
    PARAMETER = "parameter"
    IMPORT = "import"
    EXPORT = "export"
    MODULE = "module"
    NAMESPACE = "namespace"


@dataclass
class Symbol:
    """Enhanced code symbol with full metadata"""
    name: str
    type: Union[SymbolType, str]
    line: int
    parent: Optional[str] = None
    signature: Optional[str] = None
    file_path: Optional[str] = None
    line_end: Optional[int] = None
    column_start: Optional[int] = None
    column_end: Optional[int] = None
    docstring: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    references: List[Tuple[str, int]] = field(default_factory=list)
    children: List['Symbol'] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    @property
    def full_name(self) -> str:
        """Get fully qualified name including parent context"""
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name
    
    @property
    def location(self) -> str:
        """Get file:line location string"""
        if self.file_path:
            return f"{self.file_path}:{self.line}"
        return str(self.line)
    
    def to_dict(self) -> Dict:
        """Convert symbol to dictionary"""
        return {
            "name": self.name,
            "type": self.type.value if isinstance(self.type, SymbolType) else self.type,
            "line": self.line,
            "line_end": self.line_end,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "parent": self.parent,
            "signature": self.signature,
            "full_name": self.full_name,
            "file_path": self.file_path,
            "docstring": self.docstring,
            "modifiers": self.modifiers,
            "references": self.references,
            "metadata": self.metadata,
            "location": self.location
        }


class PythonSymbolExtractor:
    """Extracts symbols from Python files using AST"""
    
    def extract(self, content: str, filename: str) -> List[Symbol]:
        """Extract symbols from Python code with enhanced metadata"""
        try:
            tree = ast.parse(content, filename=filename)
            symbols = []
            self._visit_node(tree, symbols, parent=None, filename=filename)
            return symbols
        except SyntaxError as e:
            central_logger.warning(f"Failed to parse Python file {filename}: {e}")
            return []
    
    def _visit_node(self, node, symbols: List[Symbol], parent: Optional[str] = None, filename: Optional[str] = None):
        """Recursively visit AST nodes to extract enhanced symbols"""
        for item in node.body if hasattr(node, 'body') else []:
            if isinstance(item, ast.ClassDef):
                # Extract decorators
                decorators = self._get_decorators(item)
                
                symbol = Symbol(
                    name=item.name,
                    type=SymbolType.CLASS,
                    line=item.lineno,
                    line_end=getattr(item, 'end_lineno', item.lineno),
                    column_start=item.col_offset,
                    column_end=getattr(item, 'end_col_offset', item.col_offset),
                    parent=parent,
                    file_path=filename,
                    docstring=ast.get_docstring(item),
                    modifiers=decorators,
                    signature=self._get_class_signature(item)
                )
                symbols.append(symbol)
                
                # Visit class body
                for subitem in item.body:
                    if isinstance(subitem, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_modifiers = self._get_decorators(subitem)
                        if isinstance(subitem, ast.AsyncFunctionDef):
                            method_modifiers.append("async")
                        
                        method = Symbol(
                            name=subitem.name,
                            type=SymbolType.METHOD,
                            line=subitem.lineno,
                            line_end=getattr(subitem, 'end_lineno', subitem.lineno),
                            column_start=subitem.col_offset,
                            column_end=getattr(subitem, 'end_col_offset', subitem.col_offset),
                            parent=item.name,
                            file_path=filename,
                            signature=self._get_function_signature(subitem),
                            docstring=ast.get_docstring(subitem),
                            modifiers=method_modifiers
                        )
                        symbols.append(method)
                    elif isinstance(subitem, ast.Assign):
                        # Class properties
                        for target in subitem.targets:
                            if isinstance(target, ast.Name):
                                prop = Symbol(
                                    name=target.id,
                                    type=SymbolType.PROPERTY,
                                    line=subitem.lineno,
                                    parent=item.name,
                                    file_path=filename
                                )
                                symbols.append(prop)
            
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and parent is None:
                func_modifiers = self._get_decorators(item)
                if isinstance(item, ast.AsyncFunctionDef):
                    func_modifiers.append("async")
                
                symbol = Symbol(
                    name=item.name,
                    type=SymbolType.FUNCTION,
                    line=item.lineno,
                    line_end=getattr(item, 'end_lineno', item.lineno),
                    column_start=item.col_offset,
                    column_end=getattr(item, 'end_col_offset', item.col_offset),
                    file_path=filename,
                    signature=self._get_function_signature(item),
                    docstring=ast.get_docstring(item),
                    modifiers=func_modifiers
                )
                symbols.append(symbol)
                
                # Extract parameters
                for arg in item.args.args:
                    param = Symbol(
                        name=arg.arg,
                        type=SymbolType.PARAMETER,
                        line=getattr(arg, 'lineno', item.lineno),
                        parent=item.name,
                        file_path=filename
                    )
                    symbols.append(param)
            
            elif isinstance(item, ast.Assign) and parent is None:
                # Extract top-level variables/constants
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        # Check if it's a constant (UPPER_CASE convention)
                        is_const = target.id.isupper() and '_' in target.id
                        
                        symbol = Symbol(
                            name=target.id,
                            type=SymbolType.CONST if is_const else SymbolType.VARIABLE,
                            line=item.lineno,
                            file_path=filename
                        )
                        symbols.append(symbol)
            
            elif isinstance(item, (ast.Import, ast.ImportFrom)):
                # Extract imports
                for alias in item.names:
                    import_name = alias.asname or alias.name
                    symbol = Symbol(
                        name=import_name,
                        type=SymbolType.IMPORT,
                        line=item.lineno,
                        file_path=filename,
                        metadata={
                            "module": getattr(item, 'module', alias.name),
                            "original_name": alias.name
                        }
                    )
                    symbols.append(symbol)
    
    def _get_function_signature(self, func_node) -> str:
        """Extract enhanced function signature from FunctionDef or AsyncFunctionDef"""
        args = []
        for arg in func_node.args.args:
            args.append(arg.arg)
        
        signature = f"({', '.join(args)})"
        
        # Add return type if available
        if hasattr(func_node, 'returns') and func_node.returns:
            signature += " -> ..."
            
        return signature
    
    def _get_decorators(self, node) -> List[str]:
        """Extract decorator names from a node"""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(decorator.attr)
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator.func, ast.Attribute):
                    decorators.append(decorator.func.attr)
        return decorators
    
    def _get_class_signature(self, node) -> str:
        """Generate class signature with base classes"""
        if node.bases:
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            return f"({', '.join(bases)})"
        return ""


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
        """Extract enhanced symbols from JavaScript/TypeScript code"""
        symbols = []
        lines = content.split('\n')
        
        # Extract classes and track their line ranges
        class_ranges = self._extract_class_ranges(content, lines)
        
        # Extract all symbols with enhanced metadata
        for symbol_type, pattern in self.patterns.items():
            for match in pattern.finditer(content):
                name = match.group(1)
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                
                # Check if symbol is inside a class
                parent_class = self._find_parent_class(line_num, class_ranges)
                
                # Extract modifiers (export, async, etc.)
                modifiers = []
                if 'export' in line_content:
                    modifiers.append('export')
                if 'async' in line_content:
                    modifiers.append('async')
                if 'static' in line_content:
                    modifiers.append('static')
                if 'private' in line_content:
                    modifiers.append('private')
                if 'protected' in line_content:
                    modifiers.append('protected')
                if 'readonly' in line_content:
                    modifiers.append('readonly')
                
                symbol = Symbol(
                    name=name,
                    type=symbol_type,
                    line=line_num,
                    parent=parent_class,
                    file_path=filename,
                    modifiers=modifiers,
                    column_start=match.start() - content.rfind('\n', 0, match.start()) - 1
                )
                symbols.append(symbol)
        
        # Extract methods from classes with signatures
        for class_name, (start_line, end_line) in class_ranges.items():
            class_content = '\n'.join(lines[start_line-1:end_line])
            for match in self.method_pattern.finditer(class_content):
                method_name = match.group(1)
                if method_name not in ['constructor', 'if', 'for', 'while', 'switch', 'try', 'catch']:
                    relative_line = class_content[:match.start()].count('\n')
                    actual_line = start_line + relative_line
                    
                    # Extract method signature
                    method_line = lines[actual_line - 1] if actual_line <= len(lines) else ""
                    signature = self._extract_js_function_signature(method_line)
                    
                    # Check for async/static modifiers
                    modifiers = []
                    if 'async' in method_line:
                        modifiers.append('async')
                    if 'static' in method_line:
                        modifiers.append('static')
                    if 'private' in method_line:
                        modifiers.append('private')
                    if 'protected' in method_line:
                        modifiers.append('protected')
                    
                    symbol = Symbol(
                        name=method_name,
                        type=SymbolType.METHOD,
                        line=actual_line,
                        parent=class_name,
                        file_path=filename,
                        signature=signature,
                        modifiers=modifiers
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
    
    def _extract_js_function_signature(self, line: str) -> str:
        """Extract function/method signature from a JavaScript/TypeScript line"""
        # Match function signature pattern
        sig_match = re.search(r'\(([^)]*)\)', line)
        if sig_match:
            params = sig_match.group(1)
            # Check for return type (TypeScript)
            ret_match = re.search(r'\)\s*:\s*(\w+)', line)
            if ret_match:
                return f"({params}): {ret_match.group(1)}"
            return f"({params})"
        return "()"


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