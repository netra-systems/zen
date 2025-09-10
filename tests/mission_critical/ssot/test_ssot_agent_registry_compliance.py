"""P1 Agent Registry SSOT Compliance Test - Mission Critical

Business Impact: Ensures proper agent execution coordination for chat functionality.
This test protects the agent coordination system that enables $500K+ ARR chat features.

CRITICAL VIOLATIONS DETECTED:
- Agent routing failures leading to broken chat functionality  
- Duplicate agent instances causing resource conflicts
- Agent discovery failures preventing proper workflow execution
- Inconsistent agent state management across the platform
- Non-canonical agent creation patterns bypassing registry

SSOT COMPLIANCE: Validates that all agent registration and discovery uses
the canonical AgentRegistry implementation with proper user isolation.

P1 Priority: Agent Registry failures directly impact core business value delivery
through chat interactions and multi-agent workflow execution.
"""

import ast
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

logger = __import__('logging').getLogger(__name__)


@pytest.mark.mission_critical
@pytest.mark.ssot
class TestAgentRegistrySSot(SSotBaseTestCase):
    """P1: Agent Registry SSOT compliance testing.
    
    Business Impact: Ensures proper agent execution coordination.
    Violations in Agent Registry SSOT can cause:
    - Agent routing failures leading to broken chat functionality
    - Duplicate agent instances causing resource conflicts
    - Agent discovery failures preventing proper workflow execution
    - Inconsistent agent state management across the platform
    - Factory pattern violations breaking user isolation
    
    This test scans the codebase for agent registry violations and ensures
    all agent coordination follows canonical patterns.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        env = get_env()
        self.working_dir = Path(env.get("WORKING_DIR", os.getcwd()))
        self.violations: List[Dict[str, Any]] = []
        self.severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        # Canonical agent registry location
        self.canonical_registry_path = self.working_dir / "netra_backend" / "app" / "agents" / "supervisor" / "agent_registry.py"
        self.universal_registry_path = self.working_dir / "netra_backend" / "app" / "core" / "registry" / "universal_registry.py"
        
        logger.info("🔍 Starting Agent Registry SSOT compliance scan...")

    def test_no_duplicate_agent_registries(self):
        """Test: Detect multiple AgentRegistry class definitions.
        
        CRITICAL: Only one canonical AgentRegistry implementation should exist.
        Multiple registries cause agent routing confusion and execution failures.
        """
        logger.info("🔍 Scanning for duplicate AgentRegistry class definitions...")
        
        registry_classes = self._find_agent_registry_classes()
        
        # Should have exactly one canonical AgentRegistry implementation
        canonical_registries = [r for r in registry_classes if "supervisor" in r['file'] and "agent_registry.py" in r['file']]
        
        if len(canonical_registries) != 1:
            self._add_violation(
                "CRITICAL",
                "Missing or duplicate canonical AgentRegistry",
                f"Expected 1 canonical AgentRegistry, found {len(canonical_registries)}",
                registry_classes,
                "Ensure exactly one AgentRegistry exists in netra_backend/app/agents/supervisor/agent_registry.py"
            )
        
        # Check for forbidden duplicate implementations
        # Allow BaseAgentRegistry in universal_registry.py but not other AgentRegistry classes
        non_canonical_registries = [r for r in registry_classes if not ("supervisor" in r['file'] and "agent_registry.py" in r['file'])]
        forbidden_registries = []
        for r in non_canonical_registries:
            # Allow BaseAgentRegistry or AgentRegistry as a generic type in universal_registry.py
            if "universal_registry.py" in r['file'] and ('BaseAgentRegistry' in str(r.get('bases', [])) or 'Generic' in str(r.get('bases', []))):
                continue  # This is likely the generic registry base class
            else:
                forbidden_registries.append(r)
        
        if forbidden_registries:
            self._add_violation(
                "CRITICAL", 
                "Duplicate AgentRegistry implementations found",
                f"Found {len(forbidden_registries)} forbidden AgentRegistry classes",
                forbidden_registries,
                "Remove duplicate AgentRegistry classes - use canonical implementation only"
            )
        
        # Report results
        total_registries = len(registry_classes)
        if total_registries == 1 and canonical_registries:
            logger.info("✅ Agent Registry SSOT compliance: Single canonical implementation found")
        else:
            logger.error(f"❌ Agent Registry SSOT violation: {total_registries} implementations found")
            
        assert len(canonical_registries) == 1, f"Must have exactly 1 canonical AgentRegistry, found {len(canonical_registries)}"
        assert len(non_canonical_registries) == 0, f"Found {len(non_canonical_registries)} forbidden duplicate AgentRegistry implementations"

    def test_canonical_agent_registration_patterns(self):
        """Test: Ensure all agent registration uses canonical registry.
        
        HIGH: All agent registration must go through the canonical AgentRegistry
        to ensure proper coordination and prevent routing failures.
        """
        logger.info("🔍 Scanning for non-canonical agent registration patterns...")
        
        registration_violations = self._find_non_canonical_registration()
        
        for violation in registration_violations:
            self._add_violation(
                "HIGH",
                "Non-canonical agent registration pattern",
                f"Agent registration bypasses canonical registry: {violation['pattern']}",
                violation,
                "Use canonical AgentRegistry.register() or AgentRegistry.register_factory() methods"
            )
        
        if not registration_violations:
            logger.info("✅ All agent registration uses canonical patterns")
        else:
            logger.error(f"❌ Found {len(registration_violations)} non-canonical registration patterns")
            
        assert len(registration_violations) == 0, f"Found {len(registration_violations)} non-canonical agent registration patterns"

    def test_no_direct_agent_instantiation(self):
        """Test: Detect agent creation bypassing registry.
        
        HIGH: Direct agent instantiation bypasses user isolation and factory patterns,
        causing memory leaks and concurrent execution conflicts.
        """
        logger.info("🔍 Scanning for direct agent instantiation violations...")
        
        direct_instantiation_violations = self._find_direct_agent_instantiation()
        
        for violation in direct_instantiation_violations:
            severity = "HIGH" if "supervisor" in violation['pattern'].lower() or "agent" in violation['pattern'].lower() else "MEDIUM"
            self._add_violation(
                severity,
                "Direct agent instantiation detected",
                f"Agent created without registry: {violation['pattern']}",
                violation,
                "Use AgentRegistry.get_agent() or AgentRegistry.create_agent_for_user() instead"
            )
        
        critical_violations = [v for v in direct_instantiation_violations if "supervisor" in v['pattern'].lower()]
        
        if not direct_instantiation_violations:
            logger.info("✅ No direct agent instantiation violations found")
        else:
            logger.warning(f"⚠️ Found {len(direct_instantiation_violations)} direct instantiation patterns")
            
        # Critical agents should never be instantiated directly
        assert len(critical_violations) == 0, f"Found {len(critical_violations)} critical direct agent instantiations"

    def test_agent_routing_ssot_compliance(self):
        """Test: Validate agent routing through canonical mechanisms.
        
        HIGH: Agent routing must use canonical registry methods to ensure
        proper agent discovery and execution coordination.
        """
        logger.info("🔍 Scanning for agent routing SSOT compliance...")
        
        routing_violations = self._find_agent_routing_violations()
        
        for violation in routing_violations:
            self._add_violation(
                "HIGH",
                "Non-canonical agent routing detected",
                f"Agent routing bypasses canonical mechanisms: {violation['pattern']}",
                violation,
                "Use AgentRegistry.get_agent() or registry-based agent discovery methods"
            )
        
        if not routing_violations:
            logger.info("✅ All agent routing uses canonical mechanisms")
        else:
            logger.error(f"❌ Found {len(routing_violations)} agent routing violations")
            
        assert len(routing_violations) == 0, f"Found {len(routing_violations)} agent routing SSOT violations"

    def test_agent_factory_pattern_compliance(self):
        """Test: Verify proper agent factory pattern usage.
        
        MEDIUM: Factory patterns are essential for user isolation and proper
        resource management in the multi-user system.
        """
        logger.info("🔍 Scanning for agent factory pattern compliance...")
        
        factory_violations = self._find_factory_pattern_violations()
        
        for violation in factory_violations:
            self._add_violation(
                "MEDIUM",
                "Agent factory pattern violation",
                f"Improper factory usage: {violation['pattern']}",
                violation,
                "Use AgentRegistry.register_factory() for proper user isolation"
            )
        
        if not factory_violations:
            logger.info("✅ Agent factory patterns properly implemented")
        else:
            logger.warning(f"⚠️ Found {len(factory_violations)} factory pattern violations")
            
        # Factory violations should be minimized for system stability
        assert len(factory_violations) <= 10, f"Too many factory violations: {len(factory_violations)} (max 10 allowed)"

    def test_universal_registry_integration_compliance(self):
        """Test: Verify AgentRegistry properly extends UniversalRegistry.
        
        HIGH: The AgentRegistry must properly inherit from UniversalRegistry
        to maintain SSOT compliance and interface contracts.
        """
        logger.info("🔍 Validating UniversalRegistry integration compliance...")
        
        if not self.canonical_registry_path.exists():
            self._add_violation(
                "CRITICAL",
                "Canonical AgentRegistry file not found",
                f"Missing canonical registry at {self.canonical_registry_path}",
                {"file": str(self.canonical_registry_path)},
                "Ensure canonical AgentRegistry exists"
            )
            pytest.fail("Canonical AgentRegistry file not found")
        
        # Check inheritance from UniversalRegistry
        inheritance_violations = self._check_universal_registry_inheritance()
        
        for violation in inheritance_violations:
            self._add_violation(
                "HIGH",
                "UniversalRegistry inheritance violation",
                violation['message'],
                violation,
                "Ensure AgentRegistry properly inherits from BaseAgentRegistry/UniversalRegistry"
            )
        
        if not inheritance_violations:
            logger.info("✅ AgentRegistry properly integrates with UniversalRegistry")
        else:
            logger.error(f"❌ Found {len(inheritance_violations)} inheritance violations")
            
        assert len(inheritance_violations) == 0, f"Found {len(inheritance_violations)} UniversalRegistry integration violations"

    def test_websocket_integration_ssot_compliance(self):
        """Test: Verify WebSocket integration follows SSOT patterns.
        
        HIGH: WebSocket integration is critical for chat functionality and must
        follow canonical patterns to prevent silent failures.
        """
        logger.info("🔍 Scanning WebSocket integration SSOT compliance...")
        
        websocket_violations = self._find_websocket_integration_violations()
        
        for violation in websocket_violations:
            self._add_violation(
                "HIGH",
                "WebSocket integration SSOT violation",
                f"Non-canonical WebSocket integration: {violation['pattern']}",
                violation,
                "Use canonical AgentRegistry.set_websocket_manager() methods"
            )
        
        if not websocket_violations:
            logger.info("✅ WebSocket integration follows SSOT patterns")
        else:
            logger.error(f"❌ Found {len(websocket_violations)} WebSocket integration violations")
            
        assert len(websocket_violations) == 0, f"Found {len(websocket_violations)} WebSocket integration SSOT violations"

    def test_get_agent_registry_function_usage(self):
        """Test: Verify get_agent_registry function usage patterns.
        
        MEDIUM: The get_agent_registry function should be used consistently
        for registry access to maintain SSOT compliance.
        """
        logger.info("🔍 Scanning get_agent_registry function usage...")
        
        usage_violations = self._find_get_agent_registry_violations()
        
        for violation in usage_violations:
            self._add_violation(
                "MEDIUM",
                "get_agent_registry usage violation",
                f"Inconsistent registry access: {violation['pattern']}",
                violation,
                "Use canonical get_agent_registry() function for registry access"
            )
        
        if not usage_violations:
            logger.info("✅ get_agent_registry function used consistently")
        else:
            logger.warning(f"⚠️ Found {len(usage_violations)} usage pattern violations")

    # ===================== HELPER METHODS =====================

    def _find_agent_registry_classes(self) -> List[Dict[str, Any]]:
        """Find all AgentRegistry class definitions in the codebase."""
        registry_classes = []
        
        for py_file in self._get_python_files():
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef) and node.name == "AgentRegistry":
                            registry_classes.append({
                                "file": str(py_file),
                                "class_name": node.name,
                                "line": node.lineno,
                                "bases": [self._get_base_name(base) for base in node.bases]
                            })
                except SyntaxError:
                    # Skip files with syntax errors
                    continue
                    
            except Exception as e:
                logger.debug(f"Error reading {py_file}: {e}")
                continue
        
        return registry_classes

    def _find_non_canonical_registration(self) -> List[Dict[str, Any]]:
        """Find non-canonical agent registration patterns."""
        violations = []
        
        forbidden_patterns = [
            r'agents\s*=\s*\{',  # Direct agent dictionaries
            r'register_agent\s*\(',  # Non-canonical registration
            r'\.agents\[',  # Direct agent dictionary access
            r'agent_map\s*=',  # Agent mapping variables
        ]
        
        for py_file in self._get_python_files():
            if self._is_test_file(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in forbidden_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        violations.append({
                            "file": str(py_file),
                            "line": line_num,
                            "pattern": match.group(0),
                            "line_content": line_content,
                            "violation_type": "non_canonical_registration"
                        })
                        
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
                continue
        
        return violations

    def _find_direct_agent_instantiation(self) -> List[Dict[str, Any]]:
        """Find direct agent instantiation violations."""
        violations = []
        
        agent_patterns = [
            r'SupervisorAgent\s*\(',
            r'TriageAgent\s*\(',
            r'DataAgent\s*\(',
            r'OptimizationAgent\s*\(',
            r'UnifiedTriageAgent\s*\(',
            r'UnifiedDataAgent\s*\(',
            r'[A-Z]\w*Agent\s*\(',  # Generic Agent classes
        ]
        
        for py_file in self._get_python_files():
            if self._is_test_file(py_file) or "test_" in py_file.name:
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in agent_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        # Skip if it's within a factory function or registry
                        if any(keyword in line_content.lower() for keyword in ['def create_', 'def factory', 'register_factory', 'return ']):
                            continue
                            
                        violations.append({
                            "file": str(py_file),
                            "line": line_num,
                            "pattern": match.group(0),
                            "line_content": line_content,
                            "violation_type": "direct_instantiation"
                        })
                        
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
                continue
        
        return violations

    def _find_agent_routing_violations(self) -> List[Dict[str, Any]]:
        """Find agent routing SSOT violations."""
        violations = []
        
        routing_patterns = [
            r'agents\[.*\]',  # Direct agent dictionary access
            r'get_agent_by_name\s*\(',  # Non-canonical routing
            r'find_agent\s*\(',  # Non-canonical discovery
            r'agent_lookup\s*\(',  # Custom lookup methods
        ]
        
        for py_file in self._get_python_files():
            if self._is_test_file(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in routing_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        violations.append({
                            "file": str(py_file),
                            "line": line_num,
                            "pattern": match.group(0),
                            "line_content": line_content,
                            "violation_type": "routing_violation"
                        })
                        
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
                continue
        
        return violations

    def _find_factory_pattern_violations(self) -> List[Dict[str, Any]]:
        """Find agent factory pattern violations."""
        violations = []
        
        violation_patterns = [
            r'singleton.*agent',  # Singleton patterns
            r'cached_agent',  # Cached instances
            r'global.*agent',  # Global agent variables
            r'shared_agent',  # Shared agent instances
        ]
        
        for py_file in self._get_python_files():
            if self._is_test_file(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in violation_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        violations.append({
                            "file": str(py_file),
                            "line": line_num,
                            "pattern": match.group(0),
                            "line_content": line_content,
                            "violation_type": "factory_violation"
                        })
                        
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
                continue
        
        return violations

    def _check_universal_registry_inheritance(self) -> List[Dict[str, Any]]:
        """Check AgentRegistry inheritance from UniversalRegistry."""
        violations = []
        
        try:
            content = self.canonical_registry_path.read_text(encoding='utf-8')
            
            # Check for proper inheritance
            if "class AgentRegistry(BaseAgentRegistry)" not in content:
                violations.append({
                    "file": str(self.canonical_registry_path),
                    "message": "AgentRegistry does not inherit from BaseAgentRegistry",
                    "violation_type": "inheritance_violation"
                })
            
            # Check for proper imports
            if "from netra_backend.app.core.registry.universal_registry import" not in content:
                violations.append({
                    "file": str(self.canonical_registry_path),
                    "message": "Missing UniversalRegistry import",
                    "violation_type": "import_violation"
                })
                
        except Exception as e:
            violations.append({
                "file": str(self.canonical_registry_path),
                "message": f"Error reading canonical registry: {e}",
                "violation_type": "read_error"
            })
        
        return violations

    def _find_websocket_integration_violations(self) -> List[Dict[str, Any]]:
        """Find WebSocket integration SSOT violations."""
        violations = []
        
        violation_patterns = [
            r'websocket_manager\s*=\s*[^A]',  # Direct assignment
            r'set_websocket\w*\(',  # Non-canonical setter patterns
            r'websocket.*bridge.*=',  # Direct bridge assignment
        ]
        
        for py_file in self._get_python_files():
            if self._is_test_file(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in violation_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        # Skip if it's within canonical AgentRegistry methods
                        if "agent_registry.py" in str(py_file) and any(method in line_content for method in ['def set_websocket', 'self.websocket']):
                            continue
                            
                        violations.append({
                            "file": str(py_file),
                            "line": line_num,
                            "pattern": match.group(0),
                            "line_content": line_content,
                            "violation_type": "websocket_violation"
                        })
                        
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
                continue
        
        return violations

    def _find_get_agent_registry_violations(self) -> List[Dict[str, Any]]:
        """Find get_agent_registry function usage violations."""
        violations = []
        
        # Look for inconsistent registry access patterns
        inconsistent_patterns = [
            r'AgentRegistry\s*\(',  # Direct constructor usage
            r'registry\s*=\s*AgentRegistry',  # Direct assignment
            r'new\s+AgentRegistry',  # New instance creation
        ]
        
        for py_file in self._get_python_files():
            if self._is_test_file(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                
                for pattern in inconsistent_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        # Skip if it's in the canonical registry file itself
                        if "agent_registry.py" in str(py_file):
                            continue
                            
                        violations.append({
                            "file": str(py_file),
                            "line": line_num,
                            "pattern": match.group(0),
                            "line_content": line_content,
                            "violation_type": "usage_violation"
                        })
                        
            except Exception as e:
                logger.debug(f"Error scanning {py_file}: {e}")
                continue
        
        return violations

    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the project."""
        python_files = []
        
        for root in [self.working_dir / "netra_backend", self.working_dir / "auth_service"]:
            if root.exists():
                python_files.extend(root.rglob("*.py"))
        
        return python_files

    def _is_test_file(self, file_path: Path) -> bool:
        """Check if file is a test file."""
        return any(part.startswith("test") for part in file_path.parts) or file_path.name.startswith("test_")

    def _get_base_name(self, base_node) -> str:
        """Get base class name from AST node."""
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            return f"{self._get_base_name(base_node.value)}.{base_node.attr}"
        else:
            return str(base_node)

    def _add_violation(self, severity: str, violation_type: str, description: str, details: Any, remediation: str):
        """Add a violation to the violations list."""
        violation = {
            "severity": severity,
            "type": violation_type,
            "description": description,
            "details": details,
            "remediation": remediation,
            "timestamp": datetime.now().isoformat()
        }
        
        self.violations.append(violation)
        self.severity_counts[severity] += 1
        
        logger.warning(f"⚠️ {severity}: {violation_type} - {description}")

    def teardown_method(self, method=None):
        """Generate compliance report after tests."""
        super().teardown_method(method)
        
        # Generate final compliance report
        total_violations = len(self.violations)
        critical_violations = self.severity_counts["CRITICAL"]
        high_violations = self.severity_counts["HIGH"]
        
        logger.info("\n" + "="*80)
        logger.info("🔍 AGENT REGISTRY SSOT COMPLIANCE REPORT")
        logger.info("="*80)
        logger.info(f"Total Violations: {total_violations}")
        logger.info(f"Critical: {critical_violations}, High: {high_violations}, Medium: {self.severity_counts['MEDIUM']}, Low: {self.severity_counts['LOW']}")
        
        if total_violations == 0:
            logger.info("✅ AGENT REGISTRY SSOT COMPLIANCE: PASSED")
            logger.info("🎯 All agent coordination follows canonical patterns")
            logger.info("🔐 User isolation and factory patterns properly implemented")
            logger.info("🌐 WebSocket integration follows SSOT standards")
        else:
            logger.error("❌ AGENT REGISTRY SSOT COMPLIANCE: VIOLATIONS DETECTED")
            logger.error("🚨 Agent coordination system has SSOT violations")
            logger.error("💡 Review violations above for remediation guidance")
        
        logger.info("="*80)
        
        # Business impact summary
        if critical_violations > 0:
            logger.error("🚨 CRITICAL BUSINESS IMPACT: Agent Registry failures can break $500K+ ARR chat functionality")
        elif high_violations > 0:
            logger.warning("⚠️ HIGH BUSINESS IMPACT: Agent coordination issues may cause execution failures")
        else:
            logger.info("✅ LOW BUSINESS IMPACT: Agent Registry SSOT compliance maintained")