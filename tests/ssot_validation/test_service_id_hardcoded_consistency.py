"""
SSOT Validation Test: SERVICE_ID Hardcoded Consistency Validation

PHASE 2: CREATE PASSING TEST - Validate Hardcoded Consistency

Purpose: This test MUST PASS after SSOT remediation to validate that all
services use the same hardcoded SERVICE_ID constant from a centralized source.

Business Value: Platform/Critical - Ensures all services use identical
SERVICE_ID value preventing cross-service authentication mismatches
that cause $500K+ ARR impact.

Expected Behavior:
- FAIL: Initially with mixed hardcoded values and environment access
- PASS: After SSOT remediation with single hardcoded constant

CRITICAL: This test validates the Golden Path: users login → get AI responses
"""

import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestServiceIdHardcodedConsistency(SSotBaseTestCase):
    """
    Validate that all services use consistent hardcoded SERVICE_ID constant.
    
    This test ensures that after SSOT remediation:
    1. All services import SERVICE_ID from same SSOT constant
    2. The constant has the correct hardcoded value
    3. No variations in SERVICE_ID values exist
    4. Import statements are standardized across services
    
    EXPECTED TO PASS: After SSOT remediation ensures consistency
    """
    
    def setup_method(self, method=None):
        """Setup test environment with hardcoded consistency metrics."""
        super().setup_method(method)
        self.record_metric("test_category", "hardcoded_consistency")
        self.record_metric("business_impact", "prevents_cross_service_auth_mismatches")
        self.record_metric("expected_value", "netra-backend")
        
    def test_ssot_constant_has_correct_hardcoded_value(self):
        """
        PASSING TEST: Validate SSOT constant has correct hardcoded value.
        
        This test validates that the centralized SERVICE_ID constant
        is properly defined with the expected hardcoded value.
        """
        constant_analysis = self._analyze_ssot_constant_definition()
        
        self.record_metric("constant_found", constant_analysis["found"])
        self.record_metric("constant_value", constant_analysis["value"])
        self.record_metric("definition_quality", constant_analysis["quality_score"])
        
        print(f"SSOT CONSTANT ANALYSIS: {constant_analysis}")
        
        # This should PASS after SSOT remediation
        assert constant_analysis["found"], (
            f"SERVICE_ID SSOT constant not found at expected location: "
            f"{constant_analysis['expected_location']}"
        )
        
        assert constant_analysis["value"] == "netra-backend", (
            f"SERVICE_ID SSOT constant has incorrect value: '{constant_analysis['value']}'. "
            f"Expected: 'netra-backend'"
        )
        
        assert constant_analysis["quality_score"] >= 0.9, (
            f"SERVICE_ID SSOT constant definition quality insufficient: "
            f"{constant_analysis['quality_score']} (expected: ≥0.9). "
            f"Issues: {constant_analysis['quality_issues']}"
        )
    
    def test_all_services_import_same_constant(self):
        """
        PASSING TEST: Validate all services import same SSOT constant.
        
        This test ensures that all services that need SERVICE_ID
        import it from the same centralized SSOT location.
        """
        import_analysis = self._analyze_service_imports()
        
        self.record_metric("services_with_imports", len(import_analysis["services"]))
        self.record_metric("unique_import_patterns", len(import_analysis["unique_patterns"]))
        self.record_metric("import_consistency_score", import_analysis["consistency_score"])
        
        for service, import_info in import_analysis["services"].items():
            print(f"SERVICE {service} IMPORTS: {import_info}")
        
        print(f"UNIQUE IMPORT PATTERNS: {import_analysis['unique_patterns']}")
        
        # This should PASS after SSOT remediation (single import pattern)
        assert len(import_analysis["unique_patterns"]) == 1, (
            f"Multiple SERVICE_ID import patterns detected: {import_analysis['unique_patterns']}. "
            f"Expected single SSOT import pattern."
        )
        
        assert import_analysis["consistency_score"] == 1.0, (
            f"SERVICE_ID import consistency failure: {import_analysis['consistency_score']} "
            f"(expected: 1.0). Inconsistent services: {import_analysis['inconsistent_services']}"
        )
    
    def test_no_alternative_service_id_definitions(self):
        """
        PASSING TEST: Validate no alternative SERVICE_ID definitions exist.
        
        This test ensures that after SSOT remediation, no alternative
        or duplicate SERVICE_ID definitions exist in the codebase.
        """
        alternative_definitions = self._scan_for_alternative_definitions()
        
        self.record_metric("alternative_definitions_found", len(alternative_definitions))
        
        for location, definition_info in alternative_definitions.items():
            print(f"ALTERNATIVE DEFINITION: {location} - {definition_info}")
        
        # This should PASS after SSOT remediation (no alternatives)
        assert len(alternative_definitions) == 0, (
            f"Alternative SERVICE_ID definitions found: {list(alternative_definitions.keys())}. "
            f"Only the SSOT constant should define SERVICE_ID."
        )
    
    def test_service_id_value_consistency_across_usage(self):
        """
        PASSING TEST: Validate SERVICE_ID value consistency across all usage.
        
        This test validates that wherever SERVICE_ID is used, it resolves
        to the same consistent value from the SSOT constant.
        """
        usage_analysis = self._analyze_service_id_usage_consistency()
        
        self.record_metric("usage_locations", len(usage_analysis["locations"]))
        self.record_metric("unique_values_found", len(usage_analysis["unique_values"]))
        self.record_metric("value_consistency_score", usage_analysis["consistency_score"])
        
        print(f"USAGE ANALYSIS: {usage_analysis}")
        
        # This should PASS after SSOT remediation (single value)
        assert len(usage_analysis["unique_values"]) == 1, (
            f"Multiple SERVICE_ID values found: {usage_analysis['unique_values']}. "
            f"Expected single consistent value from SSOT constant."
        )
        
        assert "netra-backend" in usage_analysis["unique_values"], (
            f"Expected SERVICE_ID value 'netra-backend' not found. "
            f"Found values: {usage_analysis['unique_values']}"
        )
        
        assert usage_analysis["consistency_score"] == 1.0, (
            f"SERVICE_ID value consistency failure: {usage_analysis['consistency_score']} "
            f"(expected: 1.0). Inconsistent locations: {usage_analysis['inconsistent_locations']}"
        )
    
    def test_cross_service_authentication_uses_same_value(self):
        """
        PASSING TEST: Validate cross-service auth uses consistent SERVICE_ID.
        
        This test specifically validates that cross-service authentication
        components (auth service validation, backend headers) use the same
        SERVICE_ID value from the SSOT constant.
        """
        auth_consistency = self._analyze_cross_service_auth_consistency()
        
        self.record_metric("auth_components_analyzed", len(auth_consistency["components"]))
        self.record_metric("auth_consistency_score", auth_consistency["consistency_score"])
        
        for component, analysis in auth_consistency["components"].items():
            print(f"AUTH COMPONENT {component}: {analysis}")
        
        # This should PASS after SSOT remediation (perfect consistency)
        assert auth_consistency["consistency_score"] == 1.0, (
            f"Cross-service authentication SERVICE_ID consistency failure: "
            f"{auth_consistency['consistency_score']} (expected: 1.0). "
            f"Inconsistent components: {auth_consistency['inconsistent_components']}"
        )
        
        # Validate all components use the expected value
        for component, analysis in auth_consistency["components"].items():
            assert analysis["service_id_value"] == "netra-backend", (
                f"Component {component} uses incorrect SERVICE_ID: "
                f"'{analysis['service_id_value']}' (expected: 'netra-backend')"
            )
    
    def test_import_statement_standardization(self):
        """
        PASSING TEST: Validate standardized import statements.
        
        This test ensures that all SERVICE_ID imports use the same
        standardized import statement format.
        """
        import_standardization = self._analyze_import_standardization()
        
        self.record_metric("import_statements_found", len(import_standardization["statements"]))
        self.record_metric("standardized_statements", import_standardization["standardized_count"])
        self.record_metric("non_standard_statements", import_standardization["non_standard_count"])
        
        print(f"IMPORT STANDARDIZATION: {import_standardization}")
        
        # This should PASS after SSOT remediation (all standardized)
        assert import_standardization["non_standard_count"] == 0, (
            f"Non-standardized SERVICE_ID import statements found: "
            f"{import_standardization['non_standard_count']}. "
            f"All imports should use standardized format: "
            f"'from shared.constants.service_identifiers import SERVICE_ID'"
        )
        
        # Ensure at least one standardized import exists
        assert import_standardization["standardized_count"] > 0, (
            f"No standardized SERVICE_ID imports found. Expected at least one import "
            f"using SSOT pattern."
        )
    
    def _analyze_ssot_constant_definition(self) -> Dict[str, any]:
        """Analyze the SSOT constant definition quality."""
        project_root = Path(__file__).parent.parent.parent
        expected_path = project_root / "shared" / "constants" / "service_identifiers.py"
        
        analysis = {
            "found": False,
            "value": None,
            "quality_score": 0.0,
            "quality_issues": [],
            "expected_location": str(expected_path)
        }
        
        if not expected_path.exists():
            analysis["quality_issues"].append("file_does_not_exist")
            return analysis
        
        try:
            with open(expected_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse file with AST for robust analysis
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == "SERVICE_ID":
                                if isinstance(node.value, ast.Constant):
                                    analysis.update({
                                        "found": True,
                                        "value": node.value.value
                                    })
                                    
                                    # Quality assessment
                                    quality_score = 1.0
                                    
                                    # Check if it's a string constant
                                    if not isinstance(node.value.value, str):
                                        analysis["quality_issues"].append("not_string_constant")
                                        quality_score -= 0.3
                                    
                                    # Check if value is correct
                                    if node.value.value != "netra-backend":
                                        analysis["quality_issues"].append("incorrect_value")
                                        quality_score -= 0.5
                                    
                                    analysis["quality_score"] = max(0.0, quality_score)
                                    return analysis
                
                # If not found with AST, try simple text search
                if 'SERVICE_ID = "netra-backend"' in content:
                    analysis.update({
                        "found": True,
                        "value": "netra-backend",
                        "quality_score": 0.9  # Slightly lower for non-AST parsing
                    })
                elif 'SERVICE_ID' in content:
                    analysis.update({
                        "found": True,
                        "value": "unknown_format",
                        "quality_score": 0.3
                    })
                    analysis["quality_issues"].append("unparseable_definition")
                
            except SyntaxError:
                analysis["quality_issues"].append("syntax_error")
                
        except (FileNotFoundError, PermissionError):
            analysis["quality_issues"].append("file_not_readable")
        
        return analysis
    
    def _analyze_service_imports(self) -> Dict[str, any]:
        """Analyze SERVICE_ID imports across all services."""
        project_root = Path(__file__).parent.parent.parent
        services = ["auth_service", "netra_backend"]
        
        analysis = {
            "services": {},
            "unique_patterns": set(),
            "consistency_score": 0.0,
            "inconsistent_services": []
        }
        
        for service_name in services:
            service_path = project_root / service_name
            
            if not service_path.exists():
                continue
            
            service_imports = self._extract_service_id_imports(service_path)
            analysis["services"][service_name] = service_imports
            
            # Collect unique patterns
            for import_pattern in service_imports["import_patterns"]:
                analysis["unique_patterns"].add(import_pattern)
        
        # Convert set to list for JSON serialization
        analysis["unique_patterns"] = list(analysis["unique_patterns"])
        
        # Calculate consistency score
        if len(analysis["unique_patterns"]) <= 1:
            analysis["consistency_score"] = 1.0
        else:
            analysis["consistency_score"] = 1.0 / len(analysis["unique_patterns"])
            
            # Identify inconsistent services
            if len(analysis["unique_patterns"]) > 1:
                for service, imports in analysis["services"].items():
                    if len(imports["import_patterns"]) > 1:
                        analysis["inconsistent_services"].append(service)
        
        return analysis
    
    def _scan_for_alternative_definitions(self) -> Dict[str, Dict[str, any]]:
        """Scan for alternative SERVICE_ID definitions outside SSOT."""
        project_root = Path(__file__).parent.parent.parent
        ssot_path = project_root / "shared" / "constants" / "service_identifiers.py"
        
        alternatives = {}
        
        for python_file in project_root.rglob("**/*.py"):
            # Skip the SSOT file itself
            if python_file == ssot_path:
                continue
            
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for SERVICE_ID assignments
                definition_info = self._extract_service_id_definitions(content)
                
                if definition_info["has_definitions"]:
                    relative_path = str(python_file.relative_to(project_root))
                    alternatives[relative_path] = definition_info
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return alternatives
    
    def _analyze_service_id_usage_consistency(self) -> Dict[str, any]:
        """Analyze consistency of SERVICE_ID value across all usage."""
        project_root = Path(__file__).parent.parent.parent
        
        analysis = {
            "locations": [],
            "unique_values": set(),
            "consistency_score": 0.0,
            "inconsistent_locations": []
        }
        
        for python_file in project_root.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract SERVICE_ID usage
                usage_info = self._extract_service_id_usage(content)
                
                if usage_info["values"]:
                    relative_path = str(python_file.relative_to(project_root))
                    
                    location_info = {
                        "file": relative_path,
                        "values": usage_info["values"],
                        "usage_types": usage_info["usage_types"]
                    }
                    
                    analysis["locations"].append(location_info)
                    
                    # Collect unique values
                    for value in usage_info["values"]:
                        analysis["unique_values"].add(value)
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        # Convert set to list
        analysis["unique_values"] = list(analysis["unique_values"])
        
        # Calculate consistency score
        if len(analysis["unique_values"]) <= 1:
            analysis["consistency_score"] = 1.0
        else:
            analysis["consistency_score"] = 1.0 / len(analysis["unique_values"])
            
            # Find inconsistent locations
            for location in analysis["locations"]:
                if len(location["values"]) > 1:
                    analysis["inconsistent_locations"].append(location["file"])
        
        return analysis
    
    def _analyze_cross_service_auth_consistency(self) -> Dict[str, any]:
        """Analyze SERVICE_ID consistency in cross-service authentication."""
        project_root = Path(__file__).parent.parent.parent
        
        # Key authentication components to check
        auth_components = {
            "auth_service_validation": project_root / "auth_service" / "auth_core" / "routes" / "auth_routes.py",
            "backend_auth_client": project_root / "netra_backend" / "app" / "clients" / "auth_client_core.py",
            "auth_integration": project_root / "netra_backend" / "app" / "auth_integration" / "auth.py"
        }
        
        analysis = {
            "components": {},
            "consistency_score": 0.0,
            "inconsistent_components": []
        }
        
        service_id_values = set()
        
        for component_name, component_path in auth_components.items():
            if not component_path.exists():
                continue
            
            try:
                with open(component_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract SERVICE_ID usage from component
                component_analysis = {
                    "service_id_value": self._extract_primary_service_id_value(content),
                    "uses_ssot_import": self._has_ssot_import(content),
                    "has_hardcoded": self._has_hardcoded_service_id(content),
                    "uses_environment": self._has_environment_access(content)
                }
                
                analysis["components"][component_name] = component_analysis
                
                # Collect values for consistency check
                if component_analysis["service_id_value"]:
                    service_id_values.add(component_analysis["service_id_value"])
            
            except (FileNotFoundError, PermissionError):
                continue
        
        # Calculate consistency score
        if len(service_id_values) <= 1:
            analysis["consistency_score"] = 1.0
        else:
            analysis["consistency_score"] = 1.0 / len(service_id_values)
            
            # Find inconsistent components
            for component, component_analysis in analysis["components"].items():
                if not component_analysis["uses_ssot_import"]:
                    analysis["inconsistent_components"].append(component)
        
        return analysis
    
    def _analyze_import_standardization(self) -> Dict[str, any]:
        """Analyze standardization of SERVICE_ID import statements."""
        project_root = Path(__file__).parent.parent.parent
        
        standard_pattern = "from shared.constants.service_identifiers import SERVICE_ID"
        
        analysis = {
            "statements": [],
            "standardized_count": 0,
            "non_standard_count": 0,
            "standard_pattern": standard_pattern
        }
        
        for python_file in project_root.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract import statements
                import_statements = self._extract_import_statements(content)
                
                for statement in import_statements:
                    relative_path = str(python_file.relative_to(project_root))
                    
                    statement_info = {
                        "file": relative_path,
                        "statement": statement,
                        "is_standard": statement == standard_pattern
                    }
                    
                    analysis["statements"].append(statement_info)
                    
                    if statement_info["is_standard"]:
                        analysis["standardized_count"] += 1
                    else:
                        analysis["non_standard_count"] += 1
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return analysis
    
    def _extract_service_id_imports(self, service_path: Path) -> Dict[str, any]:
        """Extract SERVICE_ID imports from a service directory."""
        import_patterns = set()
        files_with_imports = []
        
        for python_file in service_path.rglob("**/*.py"):
            if self._should_skip_file(python_file):
                continue
            
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'SERVICE_ID' in content and 'import' in content:
                    # Extract import patterns
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if 'SERVICE_ID' in line and ('import' in line or 'from' in line):
                            import_patterns.add(line)
                            files_with_imports.append(str(python_file.relative_to(service_path)))
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return {
            "import_patterns": list(import_patterns),
            "files_with_imports": files_with_imports
        }
    
    def _extract_service_id_definitions(self, content: str) -> Dict[str, any]:
        """Extract SERVICE_ID definitions from content."""
        import re
        
        definition_patterns = [
            r'SERVICE_ID\s*=\s*["\'][^"\']+["\']',
            r'service_id\s*=\s*["\'][^"\']+["\']'
        ]
        
        definitions = []
        for pattern in definition_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            definitions.extend(matches)
        
        return {
            "has_definitions": len(definitions) > 0,
            "definitions": definitions
        }
    
    def _extract_service_id_usage(self, content: str) -> Dict[str, any]:
        """Extract SERVICE_ID usage patterns and values."""
        import re
        
        values = set()
        usage_types = set()
        
        # Look for quoted service ID values
        quoted_patterns = [
            r'["\']netra-backend["\']',
            r'["\'][^"\']*backend[^"\']*["\']'
        ]
        
        for pattern in quoted_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                values.add(match.strip('\'"'))
                usage_types.add("quoted_literal")
        
        # Look for SERVICE_ID variable usage
        if 'SERVICE_ID' in content:
            usage_types.add("variable_reference")
            # If it's imported, assume it uses the SSOT value
            if 'import' in content and 'SERVICE_ID' in content:
                values.add("netra-backend")  # SSOT value
        
        return {
            "values": list(values),
            "usage_types": list(usage_types)
        }
    
    def _extract_primary_service_id_value(self, content: str) -> Optional[str]:
        """Extract the primary SERVICE_ID value from content."""
        # Look for hardcoded values first
        if '"netra-backend"' in content or "'netra-backend'" in content:
            return "netra-backend"
        
        # Look for environment access
        if 'SERVICE_ID' in content and 'environ' in content:
            return "environment_dependent"
        
        # Look for SSOT import
        if 'from shared.constants' in content and 'SERVICE_ID' in content:
            return "netra-backend"  # SSOT value
        
        return None
    
    def _has_ssot_import(self, content: str) -> bool:
        """Check if content has SSOT import."""
        ssot_patterns = [
            "from shared.constants.service_identifiers import SERVICE_ID",
            "from shared.constants import SERVICE_ID"
        ]
        
        return any(pattern in content for pattern in ssot_patterns)
    
    def _has_hardcoded_service_id(self, content: str) -> bool:
        """Check if content has hardcoded SERVICE_ID."""
        hardcoded_patterns = [
            '"netra-backend"',
            "'netra-backend'"
        ]
        
        return any(pattern in content for pattern in hardcoded_patterns)
    
    def _has_environment_access(self, content: str) -> bool:
        """Check if content accesses SERVICE_ID via environment."""
        env_patterns = [
            "os.environ.get('SERVICE_ID')",
            'os.environ.get("SERVICE_ID")',
            "env.get('SERVICE_ID')",
            'env.get("SERVICE_ID")'
        ]
        
        return any(pattern in content for pattern in env_patterns)
    
    def _extract_import_statements(self, content: str) -> List[str]:
        """Extract SERVICE_ID import statements from content."""
        statements = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'SERVICE_ID' in line and ('import' in line or 'from' in line):
                statements.append(line)
        
        return statements
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            "node_modules", "__pycache__", ".git", ".pytest_cache",
            "google-cloud-sdk", "test_results", "venv", "env"
        ]
        
        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)