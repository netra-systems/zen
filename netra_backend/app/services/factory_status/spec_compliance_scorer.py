"""SPEC Compliance Scoring Module - Analyzes code compliance with specifications."""

from pathlib import Path
from typing import Dict, Any

from netra_backend.app.spec_analyzer_core import SpecLoader, ComplianceScore, SpecViolation, ViolationSeverity
from netra_backend.app.architecture_analyzer import ArchitectureAnalyzer
from netra_backend.app.type_safety_analyzer import TypeSafetyAnalyzer
from netra_backend.app.claude_cli_runner import ClaudeCLIRunner
from netra_backend.app.score_calculator import ScoreCalculator


class SpecComplianceScorer:
    """Main class for SPEC compliance scoring."""
    
    def __init__(self, spec_dir: Path, enable_claude: bool = False):
        """Initialize compliance scorer."""
        self.spec_loader = SpecLoader(spec_dir)
        self.architecture_analyzer = ArchitectureAnalyzer(self.spec_loader)
        self.type_analyzer = TypeSafetyAnalyzer(self.spec_loader)
        self.claude_runner = ClaudeCLIRunner(enable_claude)
        self.calculator = ScoreCalculator()
    
    async def score_module(self, module_path: Path) -> ComplianceScore:
        """Score a single module for compliance."""
        await self.spec_loader.load_all_specs()
        analysis_results = await self._run_module_analyses(module_path)
        metrics = self._build_module_metrics(module_path, analysis_results)
        return self.calculator.calculate_module_score(metrics)
    
    async def _run_module_analyses(self, module_path: Path) -> Dict[str, Any]:
        """Run all compliance analyses on module."""
        arch_score, arch_violations = await self.architecture_analyzer.analyze_architecture(module_path)
        type_score, type_violations = await self.type_analyzer.analyze_type_safety(module_path)
        claude_result = await self.claude_runner.run_compliance_review(module_path)
        return self._package_analysis_results(arch_score, arch_violations, type_score, type_violations, claude_result)
    
    def _package_analysis_results(self, arch_score: float, arch_violations: list, 
                                type_score: float, type_violations: list, claude_result: Any) -> Dict[str, Any]:
        """Package analysis results into dictionary."""
        arch_data = self._package_arch_data(arch_score, arch_violations)
        type_data = self._package_type_data(type_score, type_violations)
        return {**arch_data, **type_data, "claude_result": claude_result}
    
    def _package_arch_data(self, arch_score: float, arch_violations: list) -> Dict[str, Any]:
        """Package architecture analysis data."""
        return {"arch_score": arch_score, "arch_violations": arch_violations}
    
    def _package_type_data(self, type_score: float, type_violations: list) -> Dict[str, Any]:
        """Package type safety analysis data."""
        return {"type_score": type_score, "type_violations": type_violations}
    
    def _build_module_metrics(self, module_path: Path, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Build metrics dictionary for module scoring."""
        claude_score = self._extract_claude_score(analysis_results["claude_result"])
        scores = self._build_score_dict(analysis_results, claude_score)
        violations = self._combine_violations(analysis_results)
        return {"name": module_path.name, "scores": scores, "violations": violations}
    
    def _extract_claude_score(self, claude_result: Any) -> float:
        """Extract score from Claude result."""
        return claude_result["score"] if claude_result else 80
    
    def _build_score_dict(self, analysis_results: Dict[str, Any], claude_score: float) -> Dict[str, float]:
        """Build scores dictionary."""
        base_scores = self._get_base_scores(analysis_results, claude_score)
        placeholder_scores = self._get_placeholder_scores()
        return {**base_scores, **placeholder_scores}
    
    def _get_base_scores(self, analysis_results: Dict[str, Any], claude_score: float) -> Dict[str, float]:
        """Get base analysis scores."""
        return {
            "architecture": analysis_results["arch_score"],
            "type_safety": analysis_results["type_score"],
            "spec_alignment": claude_score
        }
    
    def _get_placeholder_scores(self) -> Dict[str, float]:
        """Get placeholder scores for incomplete metrics."""
        return {
            "test_coverage": 75,
            "documentation": 70
        }
    
    def _combine_violations(self, analysis_results: Dict[str, Any]) -> list:
        """Combine all violations into single list."""
        arch_violations = analysis_results["arch_violations"]
        type_violations = analysis_results["type_violations"]
        return [v.__dict__ for v in arch_violations + type_violations]
    
    async def score_all_modules(self, base_path: Path) -> Dict[str, ComplianceScore]:
        """Score all modules in the codebase."""
        scores: Dict[str, ComplianceScore] = {}
        for module_dir in base_path.iterdir():
            scores = await self._process_module_dir(module_dir, scores)
        return scores
    
    async def _process_module_dir(self, module_dir: Path, scores: Dict[str, ComplianceScore]) -> Dict[str, ComplianceScore]:
        """Process a single module directory."""
        if self._is_valid_module_dir(module_dir):
            score = await self.score_module(module_dir)
            scores[module_dir.name] = score
        return scores
    
    def _is_valid_module_dir(self, module_dir: Path) -> bool:
        """Check if directory is a valid module to score."""
        return module_dir.is_dir() and not module_dir.name.startswith('.')