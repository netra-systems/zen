#!/usr/bin/env python3
"""
Duplicate and Legacy Code Detection Engine
Uses AST analysis and pattern matching for Python code
"""

import ast
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import difflib
import tokenize
import io


@dataclass
class CodeBlock:
    """Represents a block of code for analysis"""
    file_path: Path
    start_line: int
    end_line: int
    content: str
    ast_hash: str
    semantic_hash: str
    complexity: int
    type: str  # function, class, module
    name: str
    
    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1
    
    def similarity_to(self, other: 'CodeBlock') -> float:
        """Calculate similarity score to another block"""
        # Quick check for identical AST
        if self.ast_hash == other.ast_hash:
            return 1.0
        
        # Semantic similarity
        if self.semantic_hash == other.semantic_hash:
            return 0.95
        
        # Content similarity
        matcher = difflib.SequenceMatcher(None, self.content, other.content)
        return matcher.ratio()


@dataclass
class Duplicate:
    """Represents a detected duplicate"""
    original: CodeBlock
    duplicate: CodeBlock
    similarity: float
    severity: str  # critical, high, medium, low
    can_refactor: bool
    suggested_action: str


@dataclass 
class LegacyPattern:
    """Represents a legacy code pattern"""
    pattern: str
    description: str
    severity: str
    replacement: Optional[str] = None
    file_path: Optional[Path] = None
    line_number: Optional[int] = None


class DuplicateDetector:
    """Main duplicate detection engine"""
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.code_blocks: List[CodeBlock] = []
        self.duplicates: List[Duplicate] = []
        self.legacy_patterns: List[LegacyPattern] = []
        self._init_legacy_patterns()
    
    def _init_legacy_patterns(self):
        """Initialize known legacy patterns"""
        self.legacy_rules = [
            {
                "pattern": r"from\s+\.\.",
                "description": "Relative imports detected",
                "severity": "high",
                "replacement": "Use absolute imports"
            },
            {
                "pattern": r"print\s*\([^)]*\)\s*(?!#|$)",
                "description": "Print statements in production code",
                "severity": "medium",
                "replacement": "Use proper logging"
            },
            {
                "pattern": r"except\s*:",
                "description": "Bare except clause",
                "severity": "high",
                "replacement": "Specify exception type"
            },
            {
                "pattern": r"TODO|FIXME|XXX|HACK",
                "description": "Unresolved TODO/FIXME",
                "severity": "low",
                "replacement": "Resolve before commit"
            },
            {
                "pattern": r"time\.sleep",
                "description": "Synchronous sleep in async context",
                "severity": "medium",
                "replacement": "Use asyncio.sleep"
            },
            {
                "pattern": r"os\.system|subprocess\.call\s*\(",
                "description": "Unsafe shell command execution",
                "severity": "critical",
                "replacement": "Use subprocess.run with proper arguments"
            },
            {
                "pattern": r"eval\s*\(|exec\s*\(",
                "description": "Dynamic code execution",
                "severity": "critical",
                "replacement": "Avoid eval/exec"
            },
            {
                "pattern": r"__all__\s*=\s*\[\]",
                "description": "Empty __all__ export",
                "severity": "low",
                "replacement": "Define exports or remove"
            }
        ]
    
    def analyze_file(self, file_path: Path) -> List[CodeBlock]:
        """Analyze a Python file for code blocks"""
        blocks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content, str(file_path))
            
            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    block = self._extract_code_block(node, content, file_path)
                    if block and block.line_count >= 5:  # Ignore tiny blocks
                        blocks.append(block)
                        self.code_blocks.append(block)
            
            # Check for legacy patterns
            self._check_legacy_patterns(content, file_path)
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
        
        return blocks
    
    def _extract_code_block(self, node: ast.AST, source: str, file_path: Path) -> Optional[CodeBlock]:
        """Extract a code block from an AST node"""
        try:
            # Get source lines
            lines = source.split('\n')
            start_line = node.lineno - 1
            end_line = node.end_lineno - 1 if hasattr(node, 'end_lineno') else start_line
            
            # Extract content
            block_lines = lines[start_line:end_line + 1]
            content = '\n'.join(block_lines)
            
            # Generate hashes
            ast_hash = self._hash_ast(node)
            semantic_hash = self._semantic_hash(node)
            
            # Calculate complexity
            complexity = self._calculate_complexity(node)
            
            # Determine type and name
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                block_type = "function"
                name = node.name
            elif isinstance(node, ast.ClassDef):
                block_type = "class"
                name = node.name
            else:
                block_type = "unknown"
                name = "unknown"
            
            return CodeBlock(
                file_path=file_path,
                start_line=start_line + 1,
                end_line=end_line + 1,
                content=content,
                ast_hash=ast_hash,
                semantic_hash=semantic_hash,
                complexity=complexity,
                type=block_type,
                name=name
            )
        except Exception:
            return None
    
    def _hash_ast(self, node: ast.AST) -> str:
        """Generate hash of AST structure"""
        # Remove position info for comparison
        cleaned = self._clean_ast(node)
        ast_str = ast.dump(cleaned)
        return hashlib.md5(ast_str.encode()).hexdigest()
    
    def _clean_ast(self, node: ast.AST) -> ast.AST:
        """Remove position and context info from AST"""
        for field, value in ast.iter_fields(node):
            if field in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset', 'ctx'):
                delattr(node, field)
        for child in ast.iter_child_nodes(node):
            self._clean_ast(child)
        return node
    
    def _semantic_hash(self, node: ast.AST) -> str:
        """Generate semantic hash (structure without names)"""
        # Replace all names with placeholders
        class NameNormalizer(ast.NodeTransformer):
            def visit_Name(self, node):
                node.id = "VAR"
                return node
            def visit_FunctionDef(self, node):
                node.name = "FUNC"
                return self.generic_visit(node)
            def visit_ClassDef(self, node):
                node.name = "CLASS"
                return self.generic_visit(node)
        
        normalized = NameNormalizer().visit(self._clean_ast(ast.parse(ast.unparse(node))))
        return hashlib.md5(ast.dump(normalized).encode()).hexdigest()
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _check_legacy_patterns(self, content: str, file_path: Path):
        """Check for legacy code patterns"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            for rule in self.legacy_rules:
                if re.search(rule["pattern"], line):
                    self.legacy_patterns.append(LegacyPattern(
                        pattern=rule["pattern"],
                        description=rule["description"],
                        severity=rule["severity"],
                        replacement=rule.get("replacement"),
                        file_path=file_path,
                        line_number=i
                    ))
    
    def find_duplicates(self) -> List[Duplicate]:
        """Find all duplicates in analyzed code blocks"""
        self.duplicates = []
        checked_pairs = set()
        
        for i, block1 in enumerate(self.code_blocks):
            for block2 in self.code_blocks[i+1:]:
                # Skip if same file and overlapping
                if block1.file_path == block2.file_path:
                    if (block1.start_line <= block2.end_line and 
                        block2.start_line <= block1.end_line):
                        continue
                
                # Skip if already checked
                pair_key = tuple(sorted([
                    f"{block1.file_path}:{block1.start_line}",
                    f"{block2.file_path}:{block2.start_line}"
                ]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                # Calculate similarity
                similarity = block1.similarity_to(block2)
                
                if similarity >= self.threshold:
                    severity = self._determine_severity(similarity, block1, block2)
                    duplicate = Duplicate(
                        original=block1,
                        duplicate=block2,
                        similarity=similarity,
                        severity=severity,
                        can_refactor=self._can_refactor(block1, block2),
                        suggested_action=self._suggest_action(block1, block2, similarity)
                    )
                    self.duplicates.append(duplicate)
        
        return self.duplicates
    
    def _determine_severity(self, similarity: float, block1: CodeBlock, block2: CodeBlock) -> str:
        """Determine duplicate severity"""
        if similarity >= 0.95 and block1.line_count > 20:
            return "critical"
        elif similarity >= 0.90 or block1.line_count > 30:
            return "high"
        elif similarity >= 0.85 or block1.line_count > 15:
            return "medium"
        else:
            return "low"
    
    def _can_refactor(self, block1: CodeBlock, block2: CodeBlock) -> bool:
        """Check if blocks can be automatically refactored"""
        # Simple heuristic - same type and similar structure
        return (block1.type == block2.type and 
                block1.semantic_hash == block2.semantic_hash)
    
    def _suggest_action(self, block1: CodeBlock, block2: CodeBlock, similarity: float) -> str:
        """Suggest remediation action"""
        if similarity >= 0.95:
            if block1.type == "function":
                return f"Extract common function from {block1.name} and {block2.name}"
            elif block1.type == "class":
                return f"Create base class for {block1.name} and {block2.name}"
            else:
                return "Extract to shared module"
        elif similarity >= 0.85:
            return "Consider refactoring to reduce duplication"
        else:
            return "Review for possible consolidation"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        return {
            "total_blocks": len(self.code_blocks),
            "duplicate_pairs": len(self.duplicates),
            "critical_duplicates": len([d for d in self.duplicates if d.severity == "critical"]),
            "high_duplicates": len([d for d in self.duplicates if d.severity == "high"]),
            "legacy_patterns": len(self.legacy_patterns),
            "critical_legacy": len([p for p in self.legacy_patterns if p.severity == "critical"]),
            "affected_files": len(set(b.file_path for b in self.code_blocks))
        }
    
    def generate_report(self) -> str:
        """Generate markdown report"""
        stats = self.get_statistics()
        
        report = ["# Code Audit Report\n"]
        report.append(f"## Summary")
        report.append(f"- Analyzed {stats['total_blocks']} code blocks in {stats['affected_files']} files")
        report.append(f"- Found {stats['duplicate_pairs']} duplicate pairs")
        report.append(f"- Found {stats['legacy_patterns']} legacy patterns\n")
        
        if self.duplicates:
            report.append("## Duplicates Found\n")
            for i, dup in enumerate(self.duplicates, 1):
                report.append(f"### Duplicate #{i} ({dup.severity.upper()})")
                report.append(f"- **Similarity**: {dup.similarity:.1%}")
                report.append(f"- **Original**: `{dup.original.file_path}:{dup.original.start_line}-{dup.original.end_line}` ({dup.original.name})")
                report.append(f"- **Duplicate**: `{dup.duplicate.file_path}:{dup.duplicate.start_line}-{dup.duplicate.end_line}` ({dup.duplicate.name})")
                report.append(f"- **Lines**: {dup.original.line_count}")
                report.append(f"- **Action**: {dup.suggested_action}")
                report.append("")
        
        if self.legacy_patterns:
            report.append("## Legacy Patterns Found\n")
            
            # Group by severity
            by_severity = defaultdict(list)
            for pattern in self.legacy_patterns:
                by_severity[pattern.severity].append(pattern)
            
            for severity in ["critical", "high", "medium", "low"]:
                if patterns := by_severity.get(severity):
                    report.append(f"### {severity.upper()} Issues")
                    for p in patterns[:10]:  # Limit to 10 per severity
                        report.append(f"- {p.description} at `{p.file_path}:{p.line_number}`")
                        if p.replacement:
                            report.append(f"  - Suggested: {p.replacement}")
                    if len(patterns) > 10:
                        report.append(f"  - ... and {len(patterns) - 10} more")
                    report.append("")
        
        return "\n".join(report)


def analyze_changed_files(detector: DuplicateDetector, base_branch: str = "main") -> List[Path]:
    """Analyze only changed files in current branch"""
    import subprocess
    
    try:
        # Get changed Python files
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_branch}...HEAD", "*.py"],
            capture_output=True,
            text=True
        )
        
        changed_files = []
        for line in result.stdout.strip().split('\n'):
            if line and line.endswith('.py'):
                path = Path(line)
                if path.exists():
                    changed_files.append(path)
                    detector.analyze_file(path)
        
        return changed_files
        
    except Exception as e:
        print(f"Error getting changed files: {e}")
        return []


if __name__ == "__main__":
    # Test the detector
    import sys
    
    detector = DuplicateDetector(threshold=0.85)
    
    if len(sys.argv) > 1:
        for path_str in sys.argv[1:]:
            path = Path(path_str)
            if path.is_file():
                detector.analyze_file(path)
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    if not any(part.startswith('.') for part in py_file.parts):
                        detector.analyze_file(py_file)
    else:
        # Analyze changed files
        analyze_changed_files(detector)
    
    # Find duplicates
    detector.find_duplicates()
    
    # Print report
    print(detector.generate_report())
    
    # Exit with error if critical issues
    stats = detector.get_statistics()
    if stats["critical_duplicates"] > 0 or stats["critical_legacy"] > 0:
        sys.exit(1)