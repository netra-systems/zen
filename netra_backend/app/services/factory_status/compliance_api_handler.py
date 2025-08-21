"""Compliance API Handler for Factory Status Integration."""

from typing import Dict, List, Any, Optional

from netra_backend.app.services.factory_status.factory_status_reporter import FactoryStatusReporter


class ComplianceAPIHandler:
    """Handles API requests for compliance scoring."""
    
    def __init__(self, reporter: FactoryStatusReporter):
        """Initialize API handler."""
        self.reporter = reporter
    
    async def get_compliance_score(self) -> Dict[str, Any]:
        """Get current compliance scores."""
        report = await self._get_or_generate_report()
        
        return self._extract_score_summary(report)
    
    async def _get_or_generate_report(self) -> Dict[str, Any]:
        """Get cached report or generate new one."""
        report = await self.reporter.get_cached_report()
        
        if not report:
            report = await self.reporter.generate_compliance_report()
        
        return report
    
    def _extract_score_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Extract score summary from report."""
        return {
            "overall_score": report["overall_compliance_score"],
            "module_scores": report["module_scores"],
            "last_updated": report["timestamp"]
        }
    
    async def analyze_modules(self, modules: List[str], use_claude: bool = False) -> Dict[str, Any]:
        """Analyze specific modules."""
        if use_claude:
            return await self.reporter.trigger_claude_review(modules)
        
        return await self._standard_module_analysis(modules)
    
    async def _standard_module_analysis(self, modules: List[str]) -> Dict[str, Any]:
        """Perform standard module analysis."""
        results = {}
        
        for module in modules:
            self._add_analysis_result(results, module, await self._analyze_single_module(module))
        
        return results
    
    def _add_analysis_result(self, results: Dict[str, Any], module: str, 
                           module_result: Optional[Dict[str, Any]]) -> None:
        """Add analysis result to results dict if valid."""
        if module_result:
            results[module] = module_result
    
    async def _analyze_single_module(self, module: str) -> Optional[Dict[str, Any]]:
        """Analyze a single module."""
        module_path = self.reporter.project_root / "app" / module
        if not module_path.exists():
            return None
        
        score = await self.reporter.scorer.score_module(module_path)
        return self.reporter._score_to_dict(score)
    
    async def get_violations(self, severity: Optional[str] = None, 
                           category: Optional[str] = None) -> List[Dict]:
        """Get list of violations with optional filters."""
        report = await self._get_or_generate_report()
        violations = self._collect_all_violations(report)
        
        return self._apply_violation_filters(violations, severity, category)
    
    def _collect_all_violations(self, report: Dict[str, Any]) -> List[Dict]:
        """Collect all violations from report."""
        violations = []
        for module_data in report["module_scores"].values():
            violations.extend(module_data.get("violations", []))
        
        return violations
    
    def _apply_violation_filters(self, violations: List[Dict], 
                               severity: Optional[str], category: Optional[str]) -> List[Dict]:
        """Apply severity and category filters to violations."""
        filtered = self._filter_by_severity(violations, severity)
        
        return self._filter_by_category(filtered, category)
    
    def _filter_by_severity(self, violations: List[Dict], severity: Optional[str]) -> List[Dict]:
        """Filter violations by severity."""
        if not severity:
            return violations
        
        return [v for v in violations if v.get("severity") == severity]
    
    def _filter_by_category(self, violations: List[Dict], category: Optional[str]) -> List[Dict]:
        """Filter violations by category."""
        if not category:
            return violations
        
        return [v for v in violations if v.get("violation_type") == category]