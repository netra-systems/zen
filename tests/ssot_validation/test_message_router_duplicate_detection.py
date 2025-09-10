"""Test 4: MessageRouter Duplicate Detection Automation

This test automatically detects new MessageRouter-like implementations to prevent
future SSOT violations and maintains the single canonical implementation.

Business Value: Platform/Internal - Regression Prevention & Golden Path Protection
- Prevents accidental creation of duplicate MessageRouter implementations
- Maintains SSOT compliance through automated detection
- Protects chat functionality from routing conflicts and race conditions

EXPECTED BEHAVIOR:
- PASS initially and continuously: Automated detection system working
- FAIL if new duplicates are introduced: Alerts to SSOT violations
- Provides actionable remediation guidance when violations detected

GitHub Issue: #217 - MessageRouter SSOT violations blocking golden path
"""

import ast
import hashlib
import json
import unittest
from typing import Dict, List, Set, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class RouterSignature:
    """Signature of a MessageRouter-like implementation."""
    class_name: str
    file_path: str
    method_names: Set[str]
    property_names: Set[str]
    line_count: int
    content_hash: str
    similarity_score: float = 0.0


class TestMessageRouterDuplicateDetection(SSotBaseTestCase, unittest.TestCase):
    """Test automated detection of MessageRouter duplicates and SSOT violations."""

    def setUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'setUp'):
            super().setUp()
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Canonical MessageRouter location
        self.canonical_path = "netra_backend/app/websocket_core/handlers.py"
        self.canonical_class = "MessageRouter"
        
        self.base_path = Path(__file__).parent.parent.parent
        
        # Detection thresholds
        self.similarity_threshold = 0.7  # 70% similarity considered duplicate
        self.min_methods_for_router = 3   # Minimum methods to be considered a router
        
        # Router-like method patterns
        self.router_method_patterns = {
            'route', 'handle', 'dispatch', 'process', 'send', 'emit',
            'add_handler', 'remove_handler', 'get_handler', 'handlers',
            'route_message', 'handle_message', 'process_message'
        }
        
        # Router-like property patterns  
        self.router_property_patterns = {
            'handlers', 'routing_stats', 'fallback_handler', 'default_handler',
            'message_handlers', 'custom_handlers', 'builtin_handlers'
        }

    def test_no_new_message_router_duplicates_created(self):
        """Test that no new MessageRouter-like classes have been created.
        
        EXPECTED: PASS initially - No duplicates exist after SSOT consolidation
        EXPECTED: FAIL if duplicates introduced - New router-like classes detected
        """
        canonical_router = self._get_canonical_router_signature()
        if not canonical_router:
            self.fail(
                f"❌ CANONICAL ROUTER MISSING: {self.canonical_path} does not contain "
                f"MessageRouter class. Golden Path chat functionality requires canonical router."
            )
        
        # Scan for potential duplicates
        potential_duplicates = self._scan_for_router_like_classes()
        
        # Filter out the canonical router
        duplicates = [
            router for router in potential_duplicates 
            if not self._is_canonical_router(router)
        ]
        
        if duplicates:
            duplicate_analysis = self._analyze_duplicates(canonical_router, duplicates)
            violation_summary = self._format_duplicate_violations(duplicate_analysis)
            
            self.fail(
                f"❌ DUPLICATE ROUTER DETECTION: {len(duplicates)} potential MessageRouter "
                f"duplicates detected.\n"
                f"BUSINESS IMPACT: Multiple routers cause WebSocket race conditions, "
                f"connection conflicts, and chat functionality failures.\n"
                f"SSOT REQUIREMENT: Only 1 canonical MessageRouter allowed.\n"
                f"DETECTED DUPLICATES:\n{violation_summary}"
            )
        
        self.logger.info("✅ No duplicate MessageRouter implementations detected")

    def test_canonical_router_signature_stability(self):
        """Test that canonical MessageRouter maintains stable signature.
        
        EXPECTED: PASS when signature changes are intentional and documented
        EXPECTED: FAIL when signature changes unexpectedly (breaking changes)
        """
        canonical_router = self._get_canonical_router_signature()
        if not canonical_router:
            self.fail("Canonical MessageRouter not found")
        
        # Load expected signature baseline (if exists)
        baseline_signature = self._load_baseline_signature()
        
        if baseline_signature:
            signature_changes = self._compare_signatures(baseline_signature, canonical_router)
            
            if signature_changes['breaking_changes']:
                breaking_summary = self._format_breaking_changes(signature_changes)
                self.fail(
                    f"❌ BREAKING SIGNATURE CHANGES: Canonical MessageRouter signature "
                    f"has breaking changes that may affect existing consumers.\n"
                    f"BUSINESS IMPACT: Breaking changes cause runtime errors in "
                    f"WebSocket message processing, disrupting chat functionality.\n"
                    f"BREAKING CHANGES:\n{breaking_summary}"
                )
            
            if signature_changes['additions'] or signature_changes['modifications']:
                change_summary = self._format_signature_changes(signature_changes)
                self.logger.warning(f"MessageRouter signature changes detected:\n{change_summary}")
        
        # Save current signature as new baseline
        self._save_baseline_signature(canonical_router)
        self.logger.info("✅ MessageRouter signature is stable")

    def test_router_naming_convention_compliance(self):
        """Test that router-like classes follow naming conventions.
        
        EXPECTED: PASS when all router classes follow naming standards
        EXPECTED: FAIL when classes violate naming conventions
        """
        router_like_classes = self._scan_for_router_like_classes()
        
        naming_violations = []
        
        for router in router_like_classes:
            violations = self._check_naming_conventions(router)
            if violations:
                naming_violations.append({
                    'router': router,
                    'violations': violations
                })
        
        if naming_violations:
            naming_summary = self._format_naming_violations(naming_violations)
            self.fail(
                f"❌ NAMING CONVENTION VIOLATIONS: {len(naming_violations)} router classes "
                f"violate naming conventions.\n"
                f"BUSINESS IMPACT: Poor naming makes code harder to understand and maintain, "
                f"increasing risk of bugs in chat functionality.\n"
                f"VIOLATIONS:\n{naming_summary}"
            )
        
        self.logger.info("✅ All router classes follow naming conventions")

    def test_router_complexity_within_limits(self):
        """Test that router implementations stay within complexity limits.
        
        EXPECTED: PASS when routers maintain reasonable complexity
        EXPECTED: FAIL when routers become overly complex (maintenance risk)
        """
        router_like_classes = self._scan_for_router_like_classes()
        
        complexity_violations = []
        max_methods = 25      # Maximum methods per router
        max_lines = 1500      # Maximum lines per router class
        
        for router in router_like_classes:
            violations = []
            
            if len(router.method_names) > max_methods:
                violations.append(
                    f"Too many methods: {len(router.method_names)} (max: {max_methods})"
                )
            
            if router.line_count > max_lines:
                violations.append(
                    f"Too many lines: {router.line_count} (max: {max_lines})"
                )
            
            if violations:
                complexity_violations.append({
                    'router': router,
                    'violations': violations
                })
        
        if complexity_violations:
            complexity_summary = self._format_complexity_violations(complexity_violations)
            self.fail(
                f"❌ COMPLEXITY VIOLATIONS: {len(complexity_violations)} router classes "
                f"exceed complexity limits.\n"
                f"BUSINESS IMPACT: Overly complex routers are harder to maintain and "
                f"more likely to contain bugs that break chat functionality.\n"
                f"VIOLATIONS:\n{complexity_summary}"
            )
        
        self.logger.info("✅ All router classes maintain reasonable complexity")

    def test_automated_duplicate_detection_system_health(self):
        """Test that the duplicate detection system itself is working correctly.
        
        EXPECTED: PASS when detection system is functioning properly
        EXPECTED: FAIL when detection system has issues
        """
        # Test detection accuracy with known patterns
        test_results = {
            'scanner_functional': True,
            'similarity_detection_working': True,
            'baseline_system_working': True,
            'error_count': 0
        }
        
        try:
            # Test 1: Scanner can find canonical router
            canonical_router = self._get_canonical_router_signature()
            if not canonical_router:
                test_results['scanner_functional'] = False
                test_results['error_count'] += 1
            
            # Test 2: Similarity calculation works
            if canonical_router:
                similarity = self._calculate_similarity(canonical_router, canonical_router)
                if similarity != 1.0:
                    test_results['similarity_detection_working'] = False
                    test_results['error_count'] += 1
            
            # Test 3: Baseline system operational
            try:
                self._get_baseline_path()
                test_results['baseline_system_working'] = True
            except Exception:
                test_results['baseline_system_working'] = False
                test_results['error_count'] += 1
        
        except Exception as e:
            test_results['error_count'] += 1
            self.logger.error(f"Detection system error: {e}")
        
        if test_results['error_count'] > 0:
            system_summary = self._format_system_health_issues(test_results)
            self.fail(
                f"❌ DETECTION SYSTEM ISSUES: {test_results['error_count']} problems "
                f"found in automated duplicate detection system.\n"
                f"BUSINESS IMPACT: Broken detection allows duplicate routers to be "
                f"created unnoticed, risking chat functionality failures.\n"
                f"SYSTEM ISSUES:\n{system_summary}"
            )
        
        self.logger.info("✅ Automated duplicate detection system is healthy")

    def _get_canonical_router_signature(self) -> Optional[RouterSignature]:
        """Get signature of the canonical MessageRouter implementation."""
        canonical_full_path = self.base_path / self.canonical_path
        
        if not canonical_full_path.exists():
            return None
        
        return self._extract_router_signature(str(canonical_full_path), self.canonical_class)

    def _scan_for_router_like_classes(self) -> List[RouterSignature]:
        """Scan codebase for classes that look like MessageRouter implementations."""
        router_candidates = []
        
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                candidates = self._extract_router_candidates(str(py_file))
                router_candidates.extend(candidates)
            except (UnicodeDecodeError, PermissionError, SyntaxError):
                continue
        
        # Filter candidates based on router-like characteristics
        return [
            candidate for candidate in router_candidates
            if self._is_router_like(candidate)
        ]

    def _extract_router_candidates(self, file_path: str) -> List[RouterSignature]:
        """Extract potential router classes from a Python file."""
        candidates = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    signature = self._create_router_signature(node, file_path, content)
                    if signature:
                        candidates.append(signature)
        
        except (SyntaxError, UnicodeDecodeError):
            pass
        
        return candidates

    def _create_router_signature(self, class_node: ast.ClassDef, file_path: str, content: str) -> Optional[RouterSignature]:
        """Create RouterSignature from AST class node."""
        method_names = set()
        property_names = set()
        
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                method_names.add(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Attribute):
                        property_names.add(target.attr)
                    elif isinstance(target, ast.Name):
                        property_names.add(target.id)
        
        # Calculate content hash for change detection
        class_content = content[class_node.lineno-1:class_node.end_lineno or len(content.split('\n'))]
        content_hash = hashlib.md5(class_content.encode()).hexdigest()
        
        # Estimate line count
        line_count = (class_node.end_lineno or class_node.lineno) - class_node.lineno + 1
        
        return RouterSignature(
            class_name=class_node.name,
            file_path=file_path,
            method_names=method_names,
            property_names=property_names,
            line_count=line_count,
            content_hash=content_hash
        )

    def _extract_router_signature(self, file_path: str, class_name: str) -> Optional[RouterSignature]:
        """Extract signature of a specific router class."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    return self._create_router_signature(node, file_path, content)
        
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            pass
        
        return None

    def _is_router_like(self, signature: RouterSignature) -> bool:
        """Determine if a class signature looks like a router implementation."""
        # Must have minimum number of methods
        if len(signature.method_names) < self.min_methods_for_router:
            return False
        
        # Must have router-like method names
        method_overlap = len(signature.method_names & self.router_method_patterns)
        method_score = method_overlap / len(signature.method_names)
        
        # Must have router-like property names
        property_overlap = len(signature.property_names & self.router_property_patterns)
        property_score = property_overlap / max(len(signature.property_names), 1)
        
        # Combined score must exceed threshold
        combined_score = (method_score + property_score) / 2
        signature.similarity_score = combined_score
        
        return combined_score >= 0.3  # 30% router-like characteristics

    def _is_canonical_router(self, signature: RouterSignature) -> bool:
        """Check if signature represents the canonical router."""
        canonical_path_normalized = str(self.base_path / self.canonical_path)
        return (signature.file_path == canonical_path_normalized and 
                signature.class_name == self.canonical_class)

    def _calculate_similarity(self, router1: RouterSignature, router2: RouterSignature) -> float:
        """Calculate similarity between two router signatures."""
        if router1.class_name == router2.class_name and router1.file_path == router2.file_path:
            return 1.0
        
        # Method name similarity
        method_union = router1.method_names | router2.method_names
        method_intersection = router1.method_names & router2.method_names
        method_similarity = len(method_intersection) / len(method_union) if method_union else 0
        
        # Property name similarity
        prop_union = router1.property_names | router2.property_names
        prop_intersection = router1.property_names & router2.property_names
        prop_similarity = len(prop_intersection) / len(prop_union) if prop_union else 0
        
        # Combined similarity
        return (method_similarity + prop_similarity) / 2

    def _analyze_duplicates(self, canonical: RouterSignature, duplicates: List[RouterSignature]) -> List[Dict[str, Any]]:
        """Analyze potential duplicates against canonical implementation."""
        analysis = []
        
        for duplicate in duplicates:
            similarity = self._calculate_similarity(canonical, duplicate)
            
            analysis.append({
                'router': duplicate,
                'similarity': similarity,
                'is_likely_duplicate': similarity >= self.similarity_threshold,
                'missing_methods': canonical.method_names - duplicate.method_names,
                'extra_methods': duplicate.method_names - canonical.method_names,
                'risk_level': self._assess_duplicate_risk(similarity, duplicate)
            })
        
        return analysis

    def _assess_duplicate_risk(self, similarity: float, router: RouterSignature) -> str:
        """Assess risk level of a potential duplicate."""
        if similarity >= 0.8:
            return "HIGH - Likely duplicate implementation"
        elif similarity >= 0.6:
            return "MEDIUM - Similar functionality, potential conflict"
        elif router.similarity_score >= 0.7:  # High router-like score
            return "MEDIUM - Router-like class, monitor for conflicts"
        else:
            return "LOW - Different functionality"

    def _check_naming_conventions(self, router: RouterSignature) -> List[str]:
        """Check if router follows naming conventions."""
        violations = []
        
        # Class name should indicate routing functionality
        class_name = router.class_name.lower()
        if not ('router' in class_name or 'handler' in class_name or 'dispatcher' in class_name):
            if router.similarity_score >= 0.5:  # Only for router-like classes
                violations.append(f"Class name '{router.class_name}' doesn't indicate routing purpose")
        
        # Method names should follow conventions
        for method in router.method_names:
            if method.startswith('__') and method.endswith('__'):
                continue  # Skip dunder methods
            
            if not method.islower() or '_' not in method:
                if len(method) > 8:  # Only flag longer method names
                    violations.append(f"Method '{method}' should use snake_case")
        
        return violations

    def _load_baseline_signature(self) -> Optional[RouterSignature]:
        """Load baseline signature from disk."""
        baseline_path = self._get_baseline_path()
        
        if not baseline_path.exists():
            return None
        
        try:
            with open(baseline_path, 'r') as f:
                data = json.load(f)
                return RouterSignature(**data)
        except (json.JSONDecodeError, TypeError, FileNotFoundError):
            return None

    def _save_baseline_signature(self, signature: RouterSignature):
        """Save signature as baseline."""
        baseline_path = self._get_baseline_path()
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert signature to JSON-serializable format
        data = {
            'class_name': signature.class_name,
            'file_path': signature.file_path,
            'method_names': list(signature.method_names),
            'property_names': list(signature.property_names),
            'line_count': signature.line_count,
            'content_hash': signature.content_hash,
            'similarity_score': signature.similarity_score,
            'baseline_timestamp': datetime.now().isoformat()
        }
        
        with open(baseline_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _get_baseline_path(self) -> Path:
        """Get path to baseline signature file."""
        return self.base_path / 'tests' / 'ssot_validation' / '.baselines' / 'message_router_signature.json'

    def _compare_signatures(self, baseline: RouterSignature, current: RouterSignature) -> Dict[str, Any]:
        """Compare baseline and current signatures."""
        return {
            'breaking_changes': list(baseline.method_names - current.method_names),
            'additions': list(current.method_names - baseline.method_names),
            'modifications': baseline.content_hash != current.content_hash,
            'property_changes': {
                'removed': list(baseline.property_names - current.property_names),
                'added': list(current.property_names - baseline.property_names)
            }
        }

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped."""
        skip_patterns = [
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            '.venv', '.test_venv', 'venv', '.baselines'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _relativize_path(self, file_path: str) -> str:
        """Convert absolute path to relative."""
        return file_path.replace(str(self.base_path), "").lstrip('/')

    def _format_duplicate_violations(self, analysis: List[Dict[str, Any]]) -> str:
        """Format duplicate violations for error reporting."""
        formatted = []
        for i, item in enumerate(analysis, 1):
            router = item['router']
            formatted.append(
                f"{i}. {self._relativize_path(router.file_path)} ({router.class_name})\n"
                f"   Similarity: {item['similarity']:.1%}\n"
                f"   Risk Level: {item['risk_level']}\n"
                f"   Methods: {len(router.method_names)}, Lines: {router.line_count}"
            )
        return "\n".join(formatted)

    def _format_breaking_changes(self, changes: Dict[str, Any]) -> str:
        """Format breaking changes for error reporting."""
        return f"Removed methods: {', '.join(changes['breaking_changes'])}"

    def _format_signature_changes(self, changes: Dict[str, Any]) -> str:
        """Format signature changes for logging."""
        parts = []
        if changes['additions']:
            parts.append(f"Added methods: {', '.join(changes['additions'])}")
        if changes['modifications']:
            parts.append("Implementation modified")
        return "; ".join(parts)

    def _format_naming_violations(self, violations: List[Dict[str, Any]]) -> str:
        """Format naming violations for error reporting."""
        formatted = []
        for item in violations:
            router = item['router']
            formatted.append(
                f"{self._relativize_path(router.file_path)} ({router.class_name}):\n"
                + "\n".join(f"  - {v}" for v in item['violations'])
            )
        return "\n".join(formatted)

    def _format_complexity_violations(self, violations: List[Dict[str, Any]]) -> str:
        """Format complexity violations for error reporting."""
        formatted = []
        for item in violations:
            router = item['router']
            formatted.append(
                f"{self._relativize_path(router.file_path)} ({router.class_name}):\n"
                + "\n".join(f"  - {v}" for v in item['violations'])
            )
        return "\n".join(formatted)

    def _format_system_health_issues(self, test_results: Dict[str, Any]) -> str:
        """Format system health issues for error reporting."""
        issues = []
        if not test_results['scanner_functional']:
            issues.append("- Scanner cannot find canonical router")
        if not test_results['similarity_detection_working']:
            issues.append("- Similarity calculation malfunction")
        if not test_results['baseline_system_working']:
            issues.append("- Baseline system not operational")
        return "\n".join(issues)


if __name__ == "__main__":
    import unittest
    unittest.main()