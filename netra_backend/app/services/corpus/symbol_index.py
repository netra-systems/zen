"""
Symbol Index Builder and Navigation System
Provides comprehensive symbol indexing, Go to Definition, and Find References capabilities
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
import json
import hashlib
from collections import defaultdict

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.corpus.symbol_extractor import Symbol, SymbolExtractor, SymbolType
from netra_backend.app.database import get_clickhouse_client


@dataclass
class SymbolIndex:
    """In-memory symbol index for fast navigation"""
    # Symbol name -> List of symbols with that name
    symbols_by_name: Dict[str, List[Symbol]] = field(default_factory=lambda: defaultdict(list))
    
    # File path -> List of symbols in that file
    symbols_by_file: Dict[str, List[Symbol]] = field(default_factory=lambda: defaultdict(list))
    
    # Qualified name -> Symbol (for unique lookups)
    symbols_by_qualified_name: Dict[str, Symbol] = field(default_factory=dict)
    
    # Symbol type -> List of symbols of that type
    symbols_by_type: Dict[SymbolType, List[Symbol]] = field(default_factory=lambda: defaultdict(list))
    
    # Reference tracking: symbol qualified name -> list of (file, line) references
    references: Dict[str, List[Tuple[str, int]]] = field(default_factory=lambda: defaultdict(list))
    
    # File hashes for change detection
    file_hashes: Dict[str, str] = field(default_factory=dict)
    
    # Statistics
    total_symbols: int = 0
    total_files: int = 0
    
    def add_symbol(self, symbol: Symbol):
        """Add a symbol to the index"""
        self.symbols_by_name[symbol.name].append(symbol)
        
        if symbol.file_path:
            self.symbols_by_file[symbol.file_path].append(symbol)
        
        self.symbols_by_qualified_name[symbol.full_name] = symbol
        
        if isinstance(symbol.type, SymbolType):
            self.symbols_by_type[symbol.type].append(symbol)
        
        self.total_symbols += 1
    
    def add_reference(self, symbol_name: str, file_path: str, line: int):
        """Add a reference to a symbol"""
        self.references[symbol_name].append((file_path, line))
    
    def get_symbol_at_position(self, file_path: str, line: int, column: Optional[int] = None) -> Optional[Symbol]:
        """Get symbol at a specific position in a file"""
        file_symbols = self.symbols_by_file.get(file_path, [])
        
        for symbol in file_symbols:
            # Check if position is within symbol's range
            if symbol.line <= line:
                if symbol.line_end and line <= symbol.line_end:
                    if column is not None and symbol.column_start and symbol.column_end:
                        if symbol.column_start <= column <= symbol.column_end:
                            return symbol
                    else:
                        return symbol
                elif not symbol.line_end and symbol.line == line:
                    return symbol
        
        return None
    
    def find_symbols(
        self, 
        name: Optional[str] = None,
        symbol_type: Optional[SymbolType] = None,
        file_path: Optional[str] = None,
        parent: Optional[str] = None
    ) -> List[Symbol]:
        """Find symbols matching criteria"""
        results = []
        
        if name:
            results = self.symbols_by_name.get(name, [])
        elif symbol_type:
            results = self.symbols_by_type.get(symbol_type, [])
        elif file_path:
            results = self.symbols_by_file.get(file_path, [])
        else:
            # Return all symbols
            results = list(self.symbols_by_qualified_name.values())
        
        # Apply additional filters
        if parent is not None:
            results = [s for s in results if s.parent == parent]
        
        return results
    
    def get_references(self, symbol_name: str) -> List[Tuple[str, int]]:
        """Get all references to a symbol"""
        return self.references.get(symbol_name, [])


class SymbolIndexBuilder:
    """Builds and maintains symbol index for the Netra codebase"""
    
    def __init__(self):
        self.extractor = SymbolExtractor()
        self.index = SymbolIndex()
        self.supported_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}
    
    async def build_index_for_directory(self, directory: Union[str, Path]) -> SymbolIndex:
        """Build symbol index for all supported files in a directory"""
        directory = Path(directory)
        
        if not directory.exists() or not directory.is_dir():
            central_logger.error(f"Directory does not exist: {directory}")
            return self.index
        
        # Find all supported files
        files = self._find_supported_files(directory)
        central_logger.info(f"Found {len(files)} files to index in {directory}")
        
        # Process files in parallel batches
        batch_size = 10
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            await asyncio.gather(*[self._index_file(f) for f in batch])
        
        # Build reference graph
        await self._build_reference_graph()
        
        self.index.total_files = len(files)
        central_logger.info(f"Indexed {self.index.total_symbols} symbols from {self.index.total_files} files")
        
        return self.index
    
    def _find_supported_files(self, directory: Path) -> List[Path]:
        """Find all supported files in directory recursively"""
        files = []
        
        # Skip common directories
        skip_dirs = {'node_modules', '.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'dist', 'build'}
        
        for file_path in directory.rglob('*'):
            # Skip if in excluded directory
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue
            
            if file_path.is_file() and file_path.suffix in self.supported_extensions:
                files.append(file_path)
        
        return files
    
    async def _index_file(self, file_path: Path):
        """Index symbols from a single file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Calculate file hash for change detection
            file_hash = hashlib.md5(content.encode()).hexdigest()
            self.index.file_hashes[str(file_path)] = file_hash
            
            # Extract symbols
            symbols = self.extractor.extract_symbols(content, str(file_path))
            
            # Add symbols to index
            for symbol in symbols:
                # Ensure file_path is set
                if not symbol.file_path:
                    symbol.file_path = str(file_path)
                self.index.add_symbol(symbol)
            
            central_logger.debug(f"Indexed {len(symbols)} symbols from {file_path}")
            
        except Exception as e:
            central_logger.warning(f"Failed to index file {file_path}: {e}")
    
    async def _build_reference_graph(self):
        """Build reference graph by analyzing symbol usage"""
        # This is a simplified version - a full implementation would use AST visitors
        # to track actual symbol usage and imports
        
        for file_path, symbols in self.index.symbols_by_file.items():
            try:
                content = Path(file_path).read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for symbol in self.index.symbols_by_name.values():
                    for sym in symbol:
                        # Simple text search for references (can be enhanced with AST)
                        for i, line in enumerate(lines, 1):
                            if sym.name in line and i != sym.line:
                                self.index.add_reference(sym.full_name, file_path, i)
                
            except Exception as e:
                central_logger.debug(f"Could not analyze references in {file_path}: {e}")
    
    async def update_file(self, file_path: Union[str, Path]):
        """Update index for a single file"""
        file_path = Path(file_path)
        
        if not file_path.exists() or file_path.suffix not in self.supported_extensions:
            return
        
        # Remove old symbols from this file
        str_path = str(file_path)
        if str_path in self.index.symbols_by_file:
            old_symbols = self.index.symbols_by_file[str_path]
            for symbol in old_symbols:
                # Remove from other indexes
                if symbol.name in self.index.symbols_by_name:
                    self.index.symbols_by_name[symbol.name].remove(symbol)
                if symbol.full_name in self.index.symbols_by_qualified_name:
                    del self.index.symbols_by_qualified_name[symbol.full_name]
                if isinstance(symbol.type, SymbolType) and symbol in self.index.symbols_by_type[symbol.type]:
                    self.index.symbols_by_type[symbol.type].remove(symbol)
            
            del self.index.symbols_by_file[str_path]
        
        # Re-index the file
        await self._index_file(file_path)


class SymbolNavigator:
    """Provides Go to Definition and Find References functionality"""
    
    def __init__(self, index: SymbolIndex):
        self.index = index
    
    def go_to_definition(self, symbol_name: str, context_file: Optional[str] = None) -> Optional[Symbol]:
        """Find the definition of a symbol"""
        
        # Try exact match first
        if symbol_name in self.index.symbols_by_qualified_name:
            return self.index.symbols_by_qualified_name[symbol_name]
        
        # Try by simple name
        candidates = self.index.symbols_by_name.get(symbol_name, [])
        
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0]
        
        # If multiple candidates, try to resolve using context
        if context_file:
            # Prefer symbols in the same file
            same_file = [s for s in candidates if s.file_path == context_file]
            if same_file:
                return same_file[0]
            
            # Prefer symbols in nearby files (same directory)
            context_dir = Path(context_file).parent
            same_dir = [s for s in candidates if s.file_path and Path(s.file_path).parent == context_dir]
            if same_dir:
                return same_dir[0]
        
        # Return the first candidate
        return candidates[0]
    
    def find_references(self, symbol: Union[str, Symbol]) -> List[Dict]:
        """Find all references to a symbol"""
        
        if isinstance(symbol, Symbol):
            symbol_name = symbol.full_name
        else:
            symbol_name = symbol
        
        # Get direct references from index
        refs = self.index.get_references(symbol_name)
        
        # Format results
        results = []
        for file_path, line in refs:
            results.append({
                "file": file_path,
                "line": line,
                "type": "reference"
            })
        
        # Also include the definition itself
        if symbol_name in self.index.symbols_by_qualified_name:
            def_symbol = self.index.symbols_by_qualified_name[symbol_name]
            results.insert(0, {
                "file": def_symbol.file_path,
                "line": def_symbol.line,
                "type": "definition",
                "symbol": def_symbol.to_dict()
            })
        
        return results
    
    def get_symbol_hierarchy(self, file_path: str) -> Dict:
        """Get hierarchical view of symbols in a file"""
        symbols = self.index.symbols_by_file.get(file_path, [])
        
        # Build hierarchy
        hierarchy = {
            "file": file_path,
            "classes": [],
            "functions": [],
            "variables": [],
            "imports": [],
            "other": []
        }
        
        # Group symbols by type and parent
        classes = {}
        
        for symbol in symbols:
            if symbol.type == SymbolType.CLASS:
                classes[symbol.name] = {
                    "symbol": symbol.to_dict(),
                    "methods": [],
                    "properties": []
                }
            elif symbol.type == SymbolType.METHOD and symbol.parent in classes:
                classes[symbol.parent]["methods"].append(symbol.to_dict())
            elif symbol.type == SymbolType.PROPERTY and symbol.parent in classes:
                classes[symbol.parent]["properties"].append(symbol.to_dict())
            elif symbol.type == SymbolType.FUNCTION:
                hierarchy["functions"].append(symbol.to_dict())
            elif symbol.type in [SymbolType.VARIABLE, SymbolType.CONST]:
                hierarchy["variables"].append(symbol.to_dict())
            elif symbol.type == SymbolType.IMPORT:
                hierarchy["imports"].append(symbol.to_dict())
            else:
                hierarchy["other"].append(symbol.to_dict())
        
        hierarchy["classes"] = list(classes.values())
        
        return hierarchy
    
    def search_symbols(
        self,
        query: str,
        symbol_types: Optional[List[SymbolType]] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Search for symbols matching a query with ranking"""
        
        results = []
        query_lower = query.lower()
        
        # Search all symbols
        for symbol in self.index.symbols_by_qualified_name.values():
            # Filter by type if specified
            if symbol_types and symbol.type not in symbol_types:
                continue
            
            # Calculate relevance score
            score = 0
            name_lower = symbol.name.lower()
            
            # Exact match
            if name_lower == query_lower:
                score = 100
            # Starts with query
            elif name_lower.startswith(query_lower):
                score = 80
            # Contains query
            elif query_lower in name_lower:
                score = 60
            # Fuzzy match (simple)
            elif self._fuzzy_match(query_lower, name_lower):
                score = 40
            else:
                continue
            
            # Boost score based on symbol type
            if symbol.type == SymbolType.CLASS:
                score += 10
            elif symbol.type == SymbolType.FUNCTION:
                score += 5
            
            results.append({
                "symbol": symbol.to_dict(),
                "score": score
            })
        
        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:limit]
    
    def _fuzzy_match(self, query: str, text: str) -> bool:
        """Simple fuzzy matching"""
        # Check if all characters in query appear in order in text
        query_idx = 0
        for char in text:
            if query_idx < len(query) and char == query[query_idx]:
                query_idx += 1
        return query_idx == len(query)


# Singleton instances
_symbol_index: Optional[SymbolIndex] = None
_index_builder: Optional[SymbolIndexBuilder] = None
_navigator: Optional[SymbolNavigator] = None


async def get_symbol_index() -> SymbolIndex:
    """Get or create the global symbol index"""
    global _symbol_index, _index_builder
    
    if _symbol_index is None:
        _index_builder = SymbolIndexBuilder()
        # Build index for the Netra backend
        backend_path = Path(__file__).parent.parent.parent.parent  # Go up to netra_backend
        _symbol_index = await _index_builder.build_index_for_directory(backend_path)
    
    return _symbol_index


async def get_symbol_navigator() -> SymbolNavigator:
    """Get or create the global symbol navigator"""
    global _navigator
    
    if _navigator is None:
        index = await get_symbol_index()
        _navigator = SymbolNavigator(index)
    
    return _navigator