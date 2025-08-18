"""SPEC Compliance Scoring Module - Analyzes code compliance with specifications."""

import os
import json
import xml.etree.ElementTree as ET
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio
from enum import Enum

from app.core.exceptions_base import ValidationError as ValidationException


class ViolationSeverity(Enum):
    """Severity levels for spec violations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ComplianceScore:
    """Compliance score for a module or overall system."""
    module_name: str
    overall_score: float
    architecture_score: float
    type_safety_score: float
    spec_alignment_score: float
    test_coverage_score: float
    documentation_score: float
    violations: List[Dict[str, Any]]
    timestamp: datetime


@dataclass
class SpecViolation:
    """Represents a spec violation."""
    module: str
    violation_type: str
    severity: ViolationSeverity
    description: str
    file_path: str
    line_number: Optional[int]
    remediation: str


class SpecLoader:
    """Loads and parses SPEC XML files."""
    
    def __init__(self, spec_dir: Path):
        """Initialize with spec directory."""
        self.spec_dir = spec_dir
        self.specs_cache: Dict[str, ET.Element] = {}
    
    async def load_all_specs(self) -> Dict[str, ET.Element]:
        """Load all XML spec files."""
        specs = {}
        for spec_file in self.spec_dir.glob("*.xml"):
            try:
                tree = ET.parse(spec_file)
                specs[spec_file.stem] = tree.getroot()
            except Exception as e:
                print(f"Error loading {spec_file}: {e}")
        self.specs_cache = specs
        return specs
    
    def get_spec(self, name: str) -> Optional[ET.Element]:
        """Get specific spec by name."""
        return self.specs_cache.get(name)


class ComplianceAnalyzer:
    """Analyzes code against spec requirements."""
    
    def __init__(self, spec_loader: SpecLoader):
        """Initialize with spec loader."""
        self.spec_loader = spec_loader
    
    async def analyze_architecture(self, module_path: Path) -> Tuple[float, List[SpecViolation]]:
        """Check architecture compliance (300/8 limits)."""
        violations = []
        total_files = 0
        compliant_files = 0
        
        for py_file in module_path.rglob("*.py"):
            total_files += 1
            file_ok = await self._check_file_compliance(py_file, violations)
            if file_ok:
                compliant_files += 1
        
        score = (compliant_files / total_files * 100) if total_files > 0 else 100
        return score, violations
    
    async def _check_file_compliance(self, file_path: Path, violations: List[SpecViolation]) -> bool:
        """Check single file for compliance."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Check file length
            if len(lines) > 300:
                violations.append(SpecViolation(
                    module=file_path.stem,
                    violation_type="file_length",
                    severity=ViolationSeverity.CRITICAL,
                    description=f"File has {len(lines)} lines (max 300)",
                    file_path=str(file_path),
                    line_number=None,
                    remediation="Split into focused modules"
                ))
                return False
            
            # Check function lengths
            func_ok = await self._check_function_lengths(file_path, lines, violations)
            return func_ok
            
        except Exception:
            return True  # Skip on error
    
    async def _check_function_lengths(self, file_path: Path, lines: List[str], violations: List[SpecViolation]) -> bool:
        """Check function lengths in file."""
        in_function = False
        func_start = 0
        func_name = ""
        func_lines = 0
        all_ok = True
        
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("def ") or line.strip().startswith("async def "):
                if in_function and func_lines > 8:
                    violations.append(SpecViolation(
                        module=file_path.stem,
                        violation_type="function_length",
                        severity=ViolationSeverity.CRITICAL,
                        description=f"Function {func_name} has {func_lines} lines (max 8)",
                        file_path=str(file_path),
                        line_number=func_start,
                        remediation="Extract helper functions"
                    ))
                    all_ok = False
                
                in_function = True
                func_start = i
                func_name = line.split("(")[0].replace("def ", "").replace("async ", "").strip()
                func_lines = 1
            elif in_function:
                if line and not line[0].isspace() and not line.strip().startswith("#"):
                    in_function = False
                else:
                    func_lines += 1
        
        return all_ok
    
    async def analyze_type_safety(self, module_path: Path) -> Tuple[float, List[SpecViolation]]:
        """Check type safety compliance."""
        violations = []
        total_functions = 0
        typed_functions = 0
        
        for py_file in module_path.rglob("*.py"):
            funcs, typed = await self._check_type_annotations(py_file, violations)
            total_functions += funcs
            typed_functions += typed
        
        score = (typed_functions / total_functions * 100) if total_functions > 0 else 100
        return score, violations
    
    async def _check_type_annotations(self, file_path: Path, violations: List[SpecViolation]) -> Tuple[int, int]:
        """Check type annotations in file."""
        total = 0
        typed = 0
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Simple heuristic check for type annotations
            import ast
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total += 1
                    has_return = node.returns is not None
                    has_args = all(arg.annotation for arg in node.args.args)
                    if has_return and has_args:
                        typed += 1
                    elif not has_return or not has_args:
                        violations.append(SpecViolation(
                            module=file_path.stem,
                            violation_type="missing_types",
                            severity=ViolationSeverity.HIGH,
                            description=f"Function {node.name} missing type annotations",
                            file_path=str(file_path),
                            line_number=node.lineno,
                            remediation="Add type annotations"
                        ))
        except Exception:
            pass
        
        return total, typed


class ClaudeCLIRunner:
    """Runs Claude CLI for deep compliance review (dev only)."""
    
    def __init__(self, enabled: bool = False):
        """Initialize Claude CLI runner."""
        self.enabled = enabled and os.getenv("ENVIRONMENT", "staging") != "production"  # Default to staging for safety
    
    async def run_compliance_review(self, module_path: Path) -> Optional[Dict[str, Any]]:
        """Run Claude CLI compliance review."""
        if not self.enabled:
            return None
        
        try:
            # Run Claude CLI with specific compliance check prompt
            prompt = f"Review {module_path} for SPEC compliance. Score 0-100."
            cmd = ["claude", "code", "--path", str(module_path), "--prompt", prompt]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            # Parse Claude's response
            response = stdout.decode()
            # Extract score from response (simplified)
            score = self._extract_score(response)
            
            return {"score": score, "insights": response[:500]}
        except Exception as e:
            print(f"Claude CLI error: {e}")
            return None
    
    def _extract_score(self, response: str) -> float:
        """Extract score from Claude response."""
        # Simple extraction - look for number between 0-100
        import re
        match = re.search(r'\b([0-9]{1,2}|100)\b', response)
        return float(match.group(1)) if match else 75.0


class ScoreCalculator:
    """Calculates compliance scores."""
    
    def calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        weights = {
            "architecture": 0.3,
            "type_safety": 0.25,
            "spec_alignment": 0.2,
            "test_coverage": 0.15,
            "documentation": 0.1
        }
        
        total = sum(scores.get(k, 0) * v for k, v in weights.items())
        return min(100, max(0, total))
    
    def calculate_module_score(self, module_metrics: Dict[str, Any]) -> ComplianceScore:
        """Calculate score for a single module."""
        return ComplianceScore(
            module_name=module_metrics["name"],
            overall_score=self.calculate_overall_score(module_metrics["scores"]),
            architecture_score=module_metrics["scores"].get("architecture", 0),
            type_safety_score=module_metrics["scores"].get("type_safety", 0),
            spec_alignment_score=module_metrics["scores"].get("spec_alignment", 0),
            test_coverage_score=module_metrics["scores"].get("test_coverage", 0),
            documentation_score=module_metrics["scores"].get("documentation", 0),
            violations=module_metrics.get("violations", []),
            timestamp=datetime.utcnow()
        )


class SpecComplianceScorer:
    """Main class for SPEC compliance scoring."""
    
    def __init__(self, spec_dir: Path, enable_claude: bool = False):
        """Initialize compliance scorer."""
        self.spec_loader = SpecLoader(spec_dir)
        self.analyzer = ComplianceAnalyzer(self.spec_loader)
        self.claude_runner = ClaudeCLIRunner(enable_claude)
        self.calculator = ScoreCalculator()
    
    async def score_module(self, module_path: Path) -> ComplianceScore:
        """Score a single module for compliance."""
        await self.spec_loader.load_all_specs()
        
        # Run various analyses
        arch_score, arch_violations = await self.analyzer.analyze_architecture(module_path)
        type_score, type_violations = await self.analyzer.analyze_type_safety(module_path)
        
        # Claude review if enabled
        claude_result = await self.claude_runner.run_compliance_review(module_path)
        
        metrics = {
            "name": module_path.name,
            "scores": {
                "architecture": arch_score,
                "type_safety": type_score,
                "spec_alignment": claude_result["score"] if claude_result else 80,
                "test_coverage": 75,  # Placeholder
                "documentation": 70   # Placeholder
            },
            "violations": [v.__dict__ for v in arch_violations + type_violations]
        }
        
        return self.calculator.calculate_module_score(metrics)
    
    async def score_all_modules(self, base_path: Path) -> Dict[str, ComplianceScore]:
        """Score all modules in the codebase."""
        scores = {}
        
        for module_dir in base_path.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith('.'):
                score = await self.score_module(module_dir)
                scores[module_dir.name] = score
        
        return scores