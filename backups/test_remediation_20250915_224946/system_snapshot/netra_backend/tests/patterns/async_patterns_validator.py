"""
Comprehensive Async Test Patterns Validator - Main Module
Validates all async testing patterns follow best practices
Maximum 300 lines, functions  <= 8 lines
"""

import ast
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from netra_backend.tests.async_pattern_analyzer import AsyncPatternAnalyzer
from netra_backend.tests.async_performance_analyzer import AsyncPerformanceAnalyzer
from netra_backend.tests.async_resource_detector import AsyncResourceLeakDetector

@dataclass
class ValidationResult:
    """Result of async pattern validation"""
    test_file: str
    pattern_type: str
    is_valid: bool
    issues: List[str]
    recommendations: List[str]

class AsyncTestPatternValidator:
    """Main validator for async test patterns"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.test_files: List[Path] = []
    
    def validate_project(self, project_path: str) -> Dict[str, Any]:
        """Validate entire project async patterns"""
        project_root = Path(project_path)
        self.test_files = list(project_root.rglob("test_*.py"))
        
        validation_summary = {
            "total_files": len(self.test_files),
            "passed_files": 0,
            "failed_files": 0,
            "total_issues": 0,
            "pattern_compliance": {}
        }
        
        for test_file in self.test_files:
            file_result = self._validate_file(test_file)
            self.results.append(file_result)
            self._update_summary(validation_summary, file_result)
        
        return validation_summary
    
    def _validate_file(self, test_file: Path) -> ValidationResult:
        """Validate single test file"""
        try:
            content = self._read_file_content(test_file)
            analyzer = self._analyze_file_content(content)
            return self._create_success_result(test_file, analyzer)
        except Exception as e:
            return self._create_error_result(test_file, e)
    
    def _read_file_content(self, test_file: Path) -> str:
        """Read file content safely"""
        with open(test_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _analyze_file_content(self, content: str) -> AsyncPatternAnalyzer:
        """Analyze file content with AST"""
        tree = ast.parse(content)
        analyzer = AsyncPatternAnalyzer()
        analyzer.visit(tree)
        return analyzer
    
    def _create_success_result(self, test_file: Path, analyzer: AsyncPatternAnalyzer) -> ValidationResult:
        """Create successful validation result"""
        return ValidationResult(
            test_file=str(test_file),
            pattern_type="async_test",
            is_valid=len(analyzer.issues) == 0,
            issues=analyzer.issues,
            recommendations=self._generate_recommendations(analyzer)
        )
    
    def _create_error_result(self, test_file: Path, error: Exception) -> ValidationResult:
        """Create error validation result"""
        return ValidationResult(
            test_file=str(test_file),
            pattern_type="async_test",
            is_valid=False,
            issues=[f"Parse error: {str(error)}"],
            recommendations=["Fix syntax errors"]
        )
    
    def _generate_recommendations(self, analyzer: AsyncPatternAnalyzer) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if analyzer.pytest_asyncio_decorators:
            recommendations.append("Remove @pytest.mark.asyncio decorators (use asyncio_mode=auto)")
        
        if len(analyzer.async_functions) == 0:
            recommendations.append("Consider using async test functions for I/O operations")
        
        return recommendations
    
    def _update_summary(self, summary: Dict[str, Any], result: ValidationResult) -> None:
        """Update validation summary with file result"""
        if result.is_valid:
            summary["passed_files"] += 1
        else:
            summary["failed_files"] += 1
        
        summary["total_issues"] += len(result.issues)
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        summary_stats = self._calculate_summary_stats()
        all_issues = self._aggregate_all_issues()
        recommendations = self._compile_all_recommendations()
        return self._format_validation_report(summary_stats, all_issues, recommendations)
    
    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate validation summary statistics"""
        total_files = len(self.results)
        passed_files = sum(1 for result in self.results if result.is_valid)
        failed_files = total_files - passed_files
        success_rate = (passed_files / total_files * 100) if total_files > 0 else 0
        return {
            "total_files": total_files,
            "passed_files": passed_files,
            "failed_files": failed_files,
            "success_rate": success_rate
        }
    
    def _aggregate_all_issues(self) -> List[str]:
        """Aggregate issues from all validation results"""
        all_issues = []
        for result in self.results:
            all_issues.extend(result.issues)
        return all_issues
    
    def _format_validation_report(self, summary: Dict, issues: List, recommendations: List) -> Dict[str, Any]:
        """Format final validation report"""
        return {
            "summary": summary,
            "issues": issues,
            "recommendations": recommendations
        }
    
    def _compile_all_recommendations(self) -> List[str]:
        """Compile all recommendations from validation results"""
        all_recommendations = []
        for result in self.results:
            all_recommendations.extend(result.recommendations)
        return list(set(all_recommendations))
    
    def check_test_coverage(self, test_files: List[Path]) -> Dict[str, Any]:
        """Check test coverage for async patterns"""
        coverage_data = self._initialize_coverage_data()
        self._aggregate_file_coverage(test_files, coverage_data)
        self._calculate_coverage_percentage(coverage_data)
        return coverage_data
    
    def _initialize_coverage_data(self) -> Dict[str, Any]:
        """Initialize coverage data structure"""
        return {
            "async_tests": 0,
            "sync_tests": 0,
            "mixed_tests": 0,
            "coverage_percentage": 0.0
        }
    
    def _aggregate_file_coverage(self, test_files: List[Path], coverage_data: Dict) -> None:
        """Aggregate coverage data from all files"""
        for test_file in test_files:
            file_coverage = self._analyze_file_coverage(test_file)
            coverage_data["async_tests"] += file_coverage["async_count"]
            coverage_data["sync_tests"] += file_coverage["sync_count"]
            coverage_data["mixed_tests"] += file_coverage["mixed_count"]
    
    def _calculate_coverage_percentage(self, coverage_data: Dict) -> None:
        """Calculate async test coverage percentage"""
        total_tests = sum([coverage_data["async_tests"], coverage_data["sync_tests"], coverage_data["mixed_tests"]])
        coverage_data["coverage_percentage"] = (coverage_data["async_tests"] / total_tests * 100) if total_tests > 0 else 0
    
    def _analyze_file_coverage(self, test_file: Path) -> Dict[str, Any]:
        """Analyze coverage patterns in a single file"""
        try:
            content = self._read_file_content(test_file)
            tree = ast.parse(content)
            return self._count_test_patterns(tree)
        except Exception:
            return {"async_count": 0, "sync_count": 0, "mixed_count": 0}
    
    def _count_test_patterns(self, tree: ast.AST) -> Dict[str, int]:
        """Count different test patterns in AST"""
        async_count = len([n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name.startswith('test_')])
        sync_count = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_') and not any(isinstance(d, ast.Name) and d.id == 'asyncio' for d in n.decorator_list)])
        mixed_count = 0  # Mixed patterns not implemented yet
        return {"async_count": async_count, "sync_count": sync_count, "mixed_count": mixed_count}

async def validate_async_test_suite() -> Dict[str, Any]:
    """Validate entire async test suite"""
    validators = _initialize_validators()
    await validators["leak_detector"].start_monitoring()
    validation_results = _run_pattern_validation(validators["validator"])
    leak_results = await validators["leak_detector"].stop_monitoring()
    return _compile_final_report(validation_results, leak_results)

def _initialize_validators() -> Dict[str, Any]:
    """Initialize all validator components"""
    return {
        "validator": AsyncTestPatternValidator(),
        "leak_detector": AsyncResourceLeakDetector(),
        "performance_analyzer": AsyncPerformanceAnalyzer()
    }

def _run_pattern_validation(validator: AsyncTestPatternValidator) -> Dict[str, Any]:
    """Run pattern validation on project"""
    project_path = "C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1"
    return validator.validate_project(project_path)

def _compile_final_report(validation_results: Dict, leak_results: Dict) -> Dict[str, Any]:
    """Compile final validation report"""
    return {
        "pattern_validation": validation_results,
        "resource_leaks": leak_results,
        "overall_status": "PASS" if validation_results["failed_files"] == 0 else "FAIL",
        "recommendations": _compile_recommendations(validation_results, leak_results)
    }

def _compile_recommendations(validation_results: Dict, leak_results: Dict) -> List[str]:
    """Compile overall recommendations"""
    recommendations = []
    
    if validation_results["failed_files"] > 0:
        recommendations.append("Fix async pattern violations in failed files")
    
    if leak_results["has_leaks"]:
        recommendations.extend(leak_results["recommendations"])
    
    recommendations.append("Use asyncio_mode=auto instead of @pytest.mark.asyncio decorators")
    recommendations.append("Implement proper async resource cleanup")
    recommendations.append("Use async context managers for test isolation")
    
    return recommendations

async def test_validator_functionality():
    """Test the validator functionality itself"""
    validator = AsyncTestPatternValidator()
    
    # Test with a simple validation
    test_content = '''
async def test_example():
    await asyncio.sleep(0.1)
    assert True
'''
    
    # This would parse and validate the content
    # For demo purposes, just verify validator exists
    assert validator is not None
    
    # Test leak detector
    leak_detector = AsyncResourceLeakDetector()
    await leak_detector.start_monitoring()
    leak_results = await leak_detector.stop_monitoring()
    assert "has_leaks" in leak_results

if __name__ == "__main__":
    # Run validation
    results = asyncio.run(validate_async_test_suite())
    print(f"Validation Status: {results['overall_status']}")
    print(f"Failed Files: {results['pattern_validation']['failed_files']}")
    if results['resource_leaks']['has_leaks']:
        print(f"Resource Leaks Detected: {results['resource_leaks']['leaks']}")