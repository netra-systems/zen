#!/usr/bin/env python3
"""
Automated Function Decomposition Tool
Automatically refactors functions exceeding the 25-line boundary.
Follows CLAUDE.md requirements: intelligent decomposition strategies.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FunctionDecomposition:
    """Function decomposition suggestion."""
    file_path: str
    function_name: str
    current_lines: int
    suggested_functions: List[Dict[str, Any]]
    decomposition_strategy: str
    confidence: float

class FunctionDecomposer:
    """Intelligent function decomposition utility."""
    
    def __init__(self, project_root: str = "."):
        """Initialize function decomposer."""
        self.project_root = Path(project_root)
        self.max_lines = 8
    
    def analyze_function_for_decomposition(self, file_path: Path, function_node: ast.FunctionDef, source_lines: List[str]) -> Optional[FunctionDecomposition]:
        """Analyze function for decomposition opportunities."""
        function_lines = self._count_function_lines(function_node)
        
        if function_lines <= self.max_lines:
            return None
        
        # Extract function source
        start_line = function_node.lineno - 1  # Convert to 0-based
        end_line = getattr(function_node, 'end_lineno', start_line + function_lines) - 1
        function_source = '\n'.join(source_lines[start_line:end_line + 1])
        
        # Analyze function structure
        decomposition = self._analyze_function_structure(
            file_path, function_node, function_source, function_lines
        )
        
        return decomposition
    
    def _count_function_lines(self, node: ast.FunctionDef) -> int:
        """Count actual code lines in function (excluding docstrings)."""
        if not node.body:
            return 0
        
        # Skip docstring if present
        start_idx = 0
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            start_idx = 1
        
        if start_idx >= len(node.body):
            return 0
        
        # Count lines from first real statement to last
        first_line = node.body[start_idx].lineno
        last_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else node.body[-1].lineno
        return last_line - first_line + 1
    
    def _analyze_function_structure(self, file_path: Path, node: ast.FunctionDef, source: str, lines: int) -> FunctionDecomposition:
        """Analyze function structure to suggest decomposition."""
        
        # Strategy 1: Extract logical blocks
        logical_blocks = self._identify_logical_blocks(node)
        if len(logical_blocks) >= 2:
            return self._suggest_logical_decomposition(file_path, node, logical_blocks, lines)
        
        # Strategy 2: Extract conditional branches
        conditionals = self._identify_conditional_branches(node)
        if len(conditionals) >= 2:
            return self._suggest_conditional_decomposition(file_path, node, conditionals, lines)
        
        # Strategy 3: Extract validation and processing
        validation_processing = self._identify_validation_processing(node)
        if validation_processing:
            return self._suggest_validation_processing_decomposition(file_path, node, validation_processing, lines)
        
        # Strategy 4: Extract error handling
        error_handling = self._identify_error_handling(node)
        if error_handling:
            return self._suggest_error_handling_decomposition(file_path, node, error_handling, lines)
        
        # Strategy 5: Simple splitting
        return self._suggest_simple_decomposition(file_path, node, lines)
    
    def _identify_logical_blocks(self, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Identify logical blocks within function."""
        blocks = []
        current_block = []
        
        for i, stmt in enumerate(node.body):
            # Skip initial docstring
            if i == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant, ast.Str)):
                continue
            
            current_block.append(stmt)
            
            # Block boundaries: assignments followed by usage
            if isinstance(stmt, ast.Assign) and i < len(node.body) - 1:
                next_stmt = node.body[i + 1]
                if not isinstance(next_stmt, ast.Assign):
                    blocks.append({
                        "type": "assignment_block",
                        "statements": current_block.copy(),
                        "start_line": current_block[0].lineno,
                        "end_line": stmt.lineno
                    })
                    current_block = []
        
        # Add remaining statements as final block
        if current_block:
            blocks.append({
                "type": "final_block",
                "statements": current_block,
                "start_line": current_block[0].lineno,
                "end_line": current_block[-1].lineno
            })
        
        return blocks
    
    def _identify_conditional_branches(self, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Identify conditional branches that can be extracted."""
        conditionals = []
        
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.If):
                # Check if branch is substantial enough to extract
                branch_lines = self._count_statement_lines(stmt)
                if branch_lines >= 3:
                    conditionals.append({
                        "type": "if_branch",
                        "node": stmt,
                        "lines": branch_lines,
                        "start_line": stmt.lineno
                    })
        
        return conditionals
    
    def _identify_validation_processing(self, node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Identify validation and processing sections."""
        validation_statements = []
        processing_statements = []
        
        in_validation = True
        
        for stmt in node.body[1:]:  # Skip docstring
            # Validation typically involves checks, raises, early returns
            if (isinstance(stmt, ast.If) and self._is_validation_check(stmt)) or \
               isinstance(stmt, ast.Raise) or \
               (isinstance(stmt, ast.Return) and in_validation):
                validation_statements.append(stmt)
            else:
                in_validation = False
                processing_statements.append(stmt)
        
        if len(validation_statements) >= 2 and len(processing_statements) >= 2:
            return {
                "validation": validation_statements,
                "processing": processing_statements
            }
        
        return None
    
    def _identify_error_handling(self, node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Identify error handling that can be extracted."""
        try_blocks = []
        
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Try):
                # Check if try block is substantial
                try_lines = self._count_statement_lines(stmt)
                if try_lines >= 4:
                    try_blocks.append({
                        "node": stmt,
                        "lines": try_lines,
                        "start_line": stmt.lineno
                    })
        
        return {"try_blocks": try_blocks} if try_blocks else None
    
    def _is_validation_check(self, stmt: ast.If) -> bool:
        """Check if IF statement is a validation check."""
        # Look for common validation patterns
        if isinstance(stmt.test, ast.UnaryOp) and isinstance(stmt.test.op, ast.Not):
            return True
        
        if isinstance(stmt.test, ast.Compare):
            # Check for None comparisons, type checks, etc.
            for comparator in stmt.test.comparators:
                if isinstance(comparator, ast.Constant) and comparator.value is None:
                    return True
        
        return False
    
    def _count_statement_lines(self, stmt: ast.AST) -> int:
        """Count lines in a statement."""
        if hasattr(stmt, 'end_lineno') and hasattr(stmt, 'lineno'):
            return stmt.end_lineno - stmt.lineno + 1
        return 1
    
    def _suggest_logical_decomposition(self, file_path: Path, node: ast.FunctionDef, blocks: List[Dict], lines: int) -> FunctionDecomposition:
        """Suggest decomposition based on logical blocks."""
        suggested_functions = []
        
        for i, block in enumerate(blocks):
            suggested_functions.append({
                "name": f"_{node.name}_{block['type']}_{i+1}",
                "purpose": f"Handle {block['type']} logic",
                "lines": block['end_line'] - block['start_line'] + 1,
                "parameters": self._extract_block_parameters(block, node),
                "return_type": "result data" if i == len(blocks) - 1 else "processed data"
            })
        
        return FunctionDecomposition(
            file_path=str(file_path),
            function_name=node.name,
            current_lines=lines,
            suggested_functions=suggested_functions,
            decomposition_strategy="logical_blocks",
            confidence=0.8
        )
    
    def _suggest_conditional_decomposition(self, file_path: Path, node: ast.FunctionDef, conditionals: List[Dict], lines: int) -> FunctionDecomposition:
        """Suggest decomposition based on conditional branches."""
        suggested_functions = []
        
        for i, conditional in enumerate(conditionals):
            suggested_functions.append({
                "name": f"_{node.name}_branch_{i+1}",
                "purpose": f"Handle conditional branch {i+1}",
                "lines": conditional['lines'],
                "parameters": self._extract_conditional_parameters(conditional, node),
                "return_type": "branch result"
            })
        
        # Add main coordination function
        suggested_functions.append({
            "name": node.name,
            "purpose": "Coordinate conditional logic",
            "lines": 5,
            "parameters": self._extract_function_parameters(node),
            "return_type": "final result"
        })
        
        return FunctionDecomposition(
            file_path=str(file_path),
            function_name=node.name,
            current_lines=lines,
            suggested_functions=suggested_functions,
            decomposition_strategy="conditional_branches",
            confidence=0.7
        )
    
    def _suggest_validation_processing_decomposition(self, file_path: Path, node: ast.FunctionDef, validation_processing: Dict, lines: int) -> FunctionDecomposition:
        """Suggest validation + processing decomposition."""
        suggested_functions = [
            {
                "name": f"_validate_{node.name}_input",
                "purpose": "Validate input parameters",
                "lines": len(validation_processing['validation']),
                "parameters": self._extract_function_parameters(node),
                "return_type": "validated data"
            },
            {
                "name": f"_process_{node.name}",
                "purpose": "Process validated data",
                "lines": len(validation_processing['processing']),
                "parameters": ["validated_data"],
                "return_type": "processed result"
            },
            {
                "name": node.name,
                "purpose": "Coordinate validation and processing",
                "lines": 4,
                "parameters": self._extract_function_parameters(node),
                "return_type": "final result"
            }
        ]
        
        return FunctionDecomposition(
            file_path=str(file_path),
            function_name=node.name,
            current_lines=lines,
            suggested_functions=suggested_functions,
            decomposition_strategy="validation_processing",
            confidence=0.9
        )
    
    def _suggest_error_handling_decomposition(self, file_path: Path, node: ast.FunctionDef, error_handling: Dict, lines: int) -> FunctionDecomposition:
        """Suggest error handling decomposition."""
        suggested_functions = []
        
        for i, try_block in enumerate(error_handling['try_blocks']):
            suggested_functions.append({
                "name": f"_{node.name}_safe_operation_{i+1}",
                "purpose": f"Safe operation {i+1} with error handling",
                "lines": try_block['lines'],
                "parameters": self._extract_function_parameters(node),
                "return_type": "operation result"
            })
        
        # Add main coordination function
        suggested_functions.append({
            "name": node.name,
            "purpose": "Coordinate safe operations",
            "lines": 6,
            "parameters": self._extract_function_parameters(node),
            "return_type": "final result"
        })
        
        return FunctionDecomposition(
            file_path=str(file_path),
            function_name=node.name,
            current_lines=lines,
            suggested_functions=suggested_functions,
            decomposition_strategy="error_handling",
            confidence=0.6
        )
    
    def _suggest_simple_decomposition(self, file_path: Path, node: ast.FunctionDef, lines: int) -> FunctionDecomposition:
        """Suggest simple decomposition when no clear patterns found."""
        num_functions = (lines + self.max_lines - 1) // self.max_lines
        
        suggested_functions = []
        for i in range(num_functions):
            suggested_functions.append({
                "name": f"_{node.name}_part_{i+1}",
                "purpose": f"Part {i+1} of {node.name}",
                "lines": min(self.max_lines, lines - i * self.max_lines),
                "parameters": self._extract_function_parameters(node),
                "return_type": "partial result" if i < num_functions - 1 else "final result"
            })
        
        return FunctionDecomposition(
            file_path=str(file_path),
            function_name=node.name,
            current_lines=lines,
            suggested_functions=suggested_functions,
            decomposition_strategy="simple_split",
            confidence=0.3
        )
    
    def _extract_function_parameters(self, node: ast.FunctionDef) -> List[str]:
        """Extract function parameters."""
        return [arg.arg for arg in node.args.args]
    
    def _extract_block_parameters(self, block: Dict, node: ast.FunctionDef) -> List[str]:
        """Extract parameters needed for a logical block."""
        # Simplified - would need more sophisticated analysis
        return self._extract_function_parameters(node)
    
    def _extract_conditional_parameters(self, conditional: Dict, node: ast.FunctionDef) -> List[str]:
        """Extract parameters needed for conditional branch."""
        # Simplified - would need more sophisticated analysis
        return self._extract_function_parameters(node)
    
    def scan_for_complex_functions(self) -> List[FunctionDecomposition]:
        """Scan project for functions exceeding complexity limits."""
        complex_functions = []
        patterns = ['app/**/*.py', 'scripts/**/*.py']
        
        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                if self._should_skip_file(file_path):
                    continue
                
                decompositions = self._analyze_file_functions(file_path)
                complex_functions.extend(decompositions)
        
        return complex_functions
    
    def _analyze_file_functions(self, file_path: Path) -> List[FunctionDecomposition]:
        """Analyze all functions in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            tree = ast.parse(content)
            decompositions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    decomposition = self.analyze_function_for_decomposition(file_path, node, lines)
                    if decomposition:
                        decompositions.append(decomposition)
            
            return decompositions
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return []
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '__pycache__', 'test_', 'migrations', 'venv', '.venv'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def generate_decomposition_report(self) -> str:
        """Generate comprehensive decomposition report."""
        decompositions = self.scan_for_complex_functions()
        
        if not decompositions:
            return "No functions exceed the 25-line boundary. Excellent compliance!"
        
        report = ["FUNCTION DECOMPOSITION ANALYSIS", "=" * 50, ""]
        
        for decomp in decompositions:
            report.append(f"FUNCTION: {decomp.function_name} ({decomp.file_path})")
            report.append(f"CURRENT LINES: {decomp.current_lines}")
            report.append(f"STRATEGY: {decomp.decomposition_strategy}")
            report.append(f"CONFIDENCE: {decomp.confidence:.1%}")
            report.append("SUGGESTED DECOMPOSITION:")
            
            for func in decomp.suggested_functions:
                report.append(f"  [U+2022] {func['name']}() - {func['purpose']}")
                report.append(f"    Parameters: {', '.join(func['parameters'])}")
                report.append(f"    Expected lines: {func['lines']}")
            
            report.append("")
        
        report.extend([
            "RECOMMENDATIONS:",
            "1. Start with validation_processing strategy (highest confidence)",
            "2. Extract error handling into separate functions",
            "3. Break logical blocks into focused helpers",
            "4. Test each decomposed function independently",
            ""
        ])
        
        return "\n".join(report)

def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Automated function decomposition for boundary compliance'
    )
    parser.add_argument('--scan', action='store_true', help='Scan for complex functions')
    parser.add_argument('--report', action='store_true', help='Generate decomposition report')
    parser.add_argument('--file', help='Analyze specific file')
    
    args = parser.parse_args()
    
    decomposer = FunctionDecomposer()
    
    if args.report or args.scan:
        report = decomposer.generate_decomposition_report()
        print(report)
    elif args.file:
        file_path = Path(args.file)
        decompositions = decomposer._analyze_file_functions(file_path)
        if decompositions:
            print(f"Complex functions in {file_path}:")
            for decomp in decompositions:
                print(f"  {decomp.function_name}: {decomp.current_lines} lines -> {len(decomp.suggested_functions)} functions")
        else:
            print(f"No complex functions found in {file_path}")
    else:
        print("Use --scan, --report, or --file <path> to analyze functions")

if __name__ == "__main__":
    main()