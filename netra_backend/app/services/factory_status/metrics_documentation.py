"""Documentation quality metrics calculator.

Calculates documentation coverage and quality metrics.
Follows 450-line limit with 25-line function limit.
"""

import subprocess
from netra_backend.app.services.factory_status.metrics_quality_types import DocumentationMetrics, QualityLevel


class DocumentationCalculator:
    """Calculator for documentation quality metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize documentation calculator."""
        self.repo_path = repo_path
    
    def assess_documentation_quality(self) -> DocumentationMetrics:
        """Assess documentation quality."""
        docstring_coverage = self._calculate_docstring_coverage()
        readme_updated = self._check_readme_updated()
        api_docs_updated = self._check_api_docs_updated()
        specs_updated = self._count_spec_updates()
        comment_density = self._calculate_comment_density()
        
        quality = self._determine_doc_quality(
            docstring_coverage, comment_density, specs_updated
        )
        
        return DocumentationMetrics(
            docstring_coverage=docstring_coverage,
            readme_updated=readme_updated,
            api_docs_updated=api_docs_updated,
            spec_files_updated=specs_updated,
            comment_density=comment_density,
            documentation_quality=quality
        )
    
    def _calculate_docstring_coverage(self) -> float:
        """Calculate docstring coverage for Python files."""
        cmd = ["find", ".", "-name", "*.py", "-exec", "grep", "-l", '"""', "{}", ";"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files_with_docstrings = len(result.stdout.strip().split("\n")) if result.stdout else 0
        total_py_files = self._count_python_files()
        
        return (files_with_docstrings / max(total_py_files, 1)) * 100
    
    def _count_python_files(self) -> int:
        """Count Python files."""
        cmd = ["find", ".", "-name", "*.py", "-type", "f"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _check_readme_updated(self) -> bool:
        """Check if README was updated recently."""
        return self._file_updated_recently("README.md", days=30)
    
    def _check_api_docs_updated(self) -> bool:
        """Check if API docs were updated recently."""
        return self._file_updated_recently("docs/API_DOCUMENTATION.md", days=30)
    
    def _file_updated_recently(self, file_path: str, days: int) -> bool:
        """Check if file was updated in last N days."""
        cmd = ["git", "log", "-1", "--since", f"{days} days ago", "--name-only", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return bool(result.stdout.strip())
    
    def _count_spec_updates(self) -> int:
        """Count SPEC file updates in last week."""
        cmd = ["git", "log", "--since", "7 days ago", "--name-only", "SPEC/"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if not result.stdout:
            return 0
        
        spec_files = self._extract_spec_files(result.stdout)
        return len(set(spec_files))
    
    def _extract_spec_files(self, output: str) -> list:
        """Extract SPEC files from git log output."""
        return [line for line in output.split("\n") if "SPEC/" in line]
    
    def _calculate_comment_density(self) -> float:
        """Calculate comment density in code."""
        total_lines = self._count_total_lines()
        comment_lines = self._count_comment_lines()
        
        return (comment_lines / max(total_lines, 1)) * 100
    
    def _count_total_lines(self) -> int:
        """Count total lines of code."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        cmd += ["|", "xargs", "wc", "-l"]
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        
        return self._extract_line_count(result.stdout)
    
    def _extract_line_count(self, output: str) -> int:
        """Extract line count from wc output."""
        if output:
            lines = output.strip().split("\n")
            if lines:
                return int(lines[-1].split()[0])
        return 0
    
    def _count_comment_lines(self) -> int:
        """Count comment lines."""
        py_comments = self._count_python_comments()
        ts_comments = self._count_typescript_comments()
        return py_comments + ts_comments
    
    def _count_python_comments(self) -> int:
        """Count Python comment lines."""
        cmd = ["find", ".", "-name", "*.py", "-exec", "grep", "-c", "^\\s*#", "{}", ";"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        counts = result.stdout.strip().split("\n") if result.stdout else []
        return sum(int(c) for c in counts if c.isdigit())
    
    def _count_typescript_comments(self) -> int:
        """Count TypeScript comment lines."""
        cmd = ["find", ".", "-name", "*.ts", "-o", "-name", "*.tsx"]
        cmd += ["|", "xargs", "grep", "-c", "^\\s*//"]
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        
        return self._extract_ts_comment_counts(result.stdout)
    
    def _extract_ts_comment_counts(self, output: str) -> int:
        """Extract TypeScript comment counts from grep output."""
        if output:
            counts = output.strip().split("\n")
            return sum(int(c.split(":")[-1]) for c in counts 
                      if ":" in c and c.split(":")[-1].isdigit())
        return 0
    
    def _determine_doc_quality(self, docstring_cov: float, 
                              comment_density: float, specs: int) -> QualityLevel:
        """Determine documentation quality level."""
        score = self._calculate_doc_score(docstring_cov, comment_density, specs)
        
        if score >= 80:
            return QualityLevel.EXCELLENT
        elif score >= 60:
            return QualityLevel.GOOD
        elif score >= 40:
            return QualityLevel.ACCEPTABLE
        elif score >= 20:
            return QualityLevel.NEEDS_IMPROVEMENT
        return QualityLevel.POOR
    
    def _calculate_doc_score(self, docstring_cov: float, 
                            comment_density: float, specs: int) -> float:
        """Calculate documentation score."""
        return (docstring_cov * 0.4 + comment_density * 0.3 + min(specs * 10, 30) * 0.3)