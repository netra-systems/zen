import ast
import os
from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict

def count_function_lines(node: ast.FunctionDef) -> int:
    """Count the actual lines of code in a function."""
    if not node.body:
        return 0
    
    body_start = node.body[0].lineno if node.body else node.lineno
    body_end = node.end_lineno or node.lineno
    return body_end - body_start + 1

def find_violations_in_file(filepath: Path, max_lines: int = 8) -> List[Tuple[str, int, int]]:
    """Find all functions exceeding max_lines in a file."""
    violations = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(filepath))
        
        class FunctionVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                lines = count_function_lines(node)
                if lines > max_lines:
                    violations.append((node.name, node.lineno, lines))
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node):
                lines = count_function_lines(node)
                if lines > max_lines:
                    violations.append((node.name, node.lineno, lines))
                self.generic_visit(node)
        
        visitor = FunctionVisitor()
        visitor.visit(tree)
        
    except Exception:
        pass
    
    return violations

def categorize_violations() -> Dict[str, Dict]:
    """Categorize violations by top-level directory."""
    directories = [
        Path("backend"),
        Path("clients"), 
        Path("config"),
        Path("security"),
        Path("monitoring"),
        Path("data"),
        Path("alembic"),
        Path("netra_mcp"),
        Path("app")
    ]
    
    category_stats = defaultdict(lambda: {"files": 0, "violations": 0, "priority_files": []})
    
    for directory in directories:
        if not directory.exists():
            continue
            
        for py_file in directory.rglob("*.py"):
            # Skip test files
            if "test" in str(py_file).lower() or "__pycache__" in str(py_file):
                continue
                
            violations = find_violations_in_file(py_file, max_lines=8)
            if violations:
                # Categorize by subdirectory
                parts = py_file.parts
                if "app" in parts:
                    idx = parts.index("app")
                    if idx + 1 < len(parts):
                        subdir = parts[idx + 1]
                        category = f"app/{subdir}"
                    else:
                        category = "app"
                else:
                    category = str(directory)
                
                category_stats[category]["files"] += 1
                category_stats[category]["violations"] += len(violations)
                
                # Track files with most violations
                if len(violations) >= 5:
                    category_stats[category]["priority_files"].append({
                        "file": str(py_file),
                        "count": len(violations)
                    })
    
    return dict(category_stats)

def main():
    stats = categorize_violations()
    
    # Sort by violation count
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["violations"], reverse=True)
    
    print("=" * 80)
    print("FUNCTION VIOLATIONS BY DIRECTORY (8-line limit)")
    print("=" * 80)
    print()
    
    total_violations = 0
    total_files = 0
    
    for category, data in sorted_stats[:15]:  # Show top 15
        if data["violations"] > 0:
            print(f"{category:30s} | Files: {data['files']:4d} | Violations: {data['violations']:5d}")
            total_violations += data["violations"]
            total_files += data["files"]
            
            # Show priority files
            if data["priority_files"]:
                priority_sorted = sorted(data["priority_files"], key=lambda x: x["count"], reverse=True)
                for pf in priority_sorted[:3]:
                    file_short = pf["file"].replace("\\", "/").split("/")[-1]
                    print(f"  > {file_short}: {pf['count']} violations")
    
    print()
    print("=" * 80)
    print(f"TOTAL: {total_files} files with {total_violations} violations")
    print("=" * 80)
    print()
    print("RECOMMENDED FIX ORDER:")
    print("1. Core business logic (app/agents, app/services)")
    print("2. Database and monitoring (app/db, app/monitoring)")
    print("3. WebSocket and middleware (app/websocket, app/middleware)")
    print("4. Supporting modules (remaining)")

if __name__ == "__main__":
    main()