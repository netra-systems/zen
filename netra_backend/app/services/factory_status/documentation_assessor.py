"""Documentation quality assessment module.

Assesses documentation coverage and quality.
Follows 450-line limit with 25-line function limit.
"""

import subprocess
from typing import List

from netra_backend.app.services.factory_status.quality_models import (
    DocumentationMetrics,
    QualityLevel,
)


class DocumentationAssessor:
    """Assessor for documentation quality."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize documentation assessor."""
        self.repo_path = repo_path
    
    def assess_quality(self) -> DocumentationMetrics:
        """Assess documentation quality."""
        docstring_cov = self._calculate_docstring_coverage()
        readme_updated = self._check_readme_updated()
        api_docs_updated = self._check_api_docs_updated()
        specs_updated = self._count_spec_updates()
        comment_density = self._calculate_comment_density()
        quality = self._determine_quality(
            docstring_cov, comment_density, specs_updated
        )
        
        return DocumentationMetrics(
            docstring_coverage=docstring_cov,
            readme_updated=readme_updated,
            api_docs_updated=api_docs_updated,
            spec_files_updated=specs_updated,
            comment_density=comment_density,
            documentation_quality=quality
        )
    
    def _calculate_docstring_coverage(self) -> float:
        """Calculate docstring coverage for Python files."""
        files_with_docstrings = self._count_files_with_docstrings()
        total_py_files = self._count_python_files()
        return self._calculate_coverage_percentage(
            files_with_docstrings, total_py_files
        )
    
    def _count_files_with_docstrings(self) -> int:
        """Count Python files with docstrings."""
        cmd = ["find", ".", "-name", "*.py", "-exec", "grep", "-l", '"""', "{}", ";"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_output_lines(result.stdout)
    
    def _count_python_files(self) -> int:
        """Count Python files."""
        cmd = ["find", ".", "-name", "*.py", "-type", "f"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_output_lines(result.stdout)
    
    def _count_output_lines(self, output: str) -> int:
        """Count non-empty lines in command output."""
        if not output:
            return 0
        lines = output.strip().split("\n")
        return len([line for line in lines if line.strip()])
    
    def _calculate_coverage_percentage(self, covered: int, total: int) -> float:
        """Calculate coverage percentage."""
        if total == 0:
            return 0.0
        return (covered / total) * 100
    
    def _check_readme_updated(self) -> bool:
        """Check if README was updated recently."""
        return self._file_updated_recently("README.md", 30)
    
    def _check_api_docs_updated(self) -> bool:
        """Check if API docs were updated recently."""
        return self._file_updated_recently("docs/API_DOCUMENTATION.md", 30)
    
    def _file_updated_recently(self, file_path: str, days: int) -> bool:
        """Check if file was updated in last N days."""
        cmd = ["git", "log", "-1", "--since", f"{days} days ago", "--name-only", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return bool(result.stdout.strip())
    
    def _count_spec_updates(self) -> int:
        """Count SPEC file updates in last week."""
        cmd = ["git", "log", "--since", "7 days ago", "--name-only", "SPEC/"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._count_unique_spec_files(result.stdout)
    
    def _count_unique_spec_files(self, output: str) -> int:
        """Count unique SPEC files from git output."""
        if not output:
            return 0
        spec_files = [line for line in output.split("\n") if "SPEC/" in line]
        return len(set(spec_files))
    
    def _calculate_comment_density(self) -> float:
        """Calculate comment density in code."""
        total_lines = self._count_total_lines()
        comment_lines = self._count_comment_lines()
        return self._calculate_coverage_percentage(comment_lines, total_lines)
    
    def _count_total_lines(self) -> int:
        """Count total lines of code."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        cmd += ["|", "xargs", "wc", "-l"]
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        return self._extract_total_lines(result.stdout)
    
    def _extract_total_lines(self, output: str) -> int:
        """Extract total line count from wc output."""
        if not output:
            return 0
        lines = output.strip().split("\n")
        if lines and lines[-1]:
            parts = lines[-1].split()
            if parts and parts[0].isdigit():
                return int(parts[0])
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
        return self._sum_counts_from_output(result.stdout)
    
    def _count_typescript_comments(self) -> int:
        """Count TypeScript comment lines."""
        cmd = ["find", ".", "-name", "*.ts", "-o", "-name", "*.tsx"]
        cmd += ["|", "xargs", "grep", "-c", "^\\s*//"]
        result = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        return self._sum_typescript_counts(result.stdout)
    
    def _sum_counts_from_output(self, output: str) -> int:
        """Sum numeric counts from command output."""
        if not output:
            return 0
        counts = output.strip().split("\n")
        return sum(int(c) for c in counts if c.isdigit())
    
    def _sum_typescript_counts(self, output: str) -> int:
        """Sum TypeScript comment counts from grep output."""
        if not output:
            return 0
        counts = output.strip().split("\n")
        total = 0
        for count_line in counts:
            if ":" in count_line:
                count_str = count_line.split(":")[-1]
                if count_str.isdigit():
                    total += int(count_str)
        return total
    
    def _determine_quality(self, docstring_cov: float,
                          comment_density: float, specs: int) -> QualityLevel:
        """Determine documentation quality level."""
        score = self._calculate_doc_score(docstring_cov, comment_density, specs)
        return self._score_to_quality_level(score)
    
    def _calculate_doc_score(self, docstring_cov: float,
                           comment_density: float, specs: int) -> float:
        """Calculate documentation score."""
        spec_score = min(specs * 10, 30)
        return (docstring_cov * 0.4 + comment_density * 0.3 + spec_score * 0.3)
    
    def _score_to_quality_level(self, score: float) -> QualityLevel:
        """Convert score to quality level."""
        if score >= 80:
            return QualityLevel.EXCELLENT
        elif score >= 60:
            return QualityLevel.GOOD
        elif score >= 40:
            return QualityLevel.ACCEPTABLE
        elif score >= 20:
            return QualityLevel.NEEDS_IMPROVEMENT
        return QualityLevel.POOR
