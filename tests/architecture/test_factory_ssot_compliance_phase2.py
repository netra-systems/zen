"""
Factory SSOT Compliance Validation - Phase 2
Ensures remaining factories follow SSOT principles.

Business Impact: $500K+ ARR protection through SSOT compliance
Created: 2025-09-15
Purpose: Validate essential factory patterns follow SSOT principles
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestFactorySSotCompliancePhase2(SSotBaseTestCase):
    """Validate SSOT compliance in essential factory patterns."""

    def setUp(self):
        """Set up test environment with codebase paths."""
        super().setUp()
        self.project_root = Path("C:/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1")
        self.source_dirs = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "auth_service",
            self.project_root / "shared",
            self.project_root / "test_framework"
        ]

    def find_factory_implementations(self):
        """Find all factory implementations and categorize by business domain."""
        factory_implementations = defaultdict(list)

        for source_dir in self.source_dirs:
            if not source_dir.exists():
                continue

            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Parse AST to find factory classes and methods
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_name = node.name
                            if ("Factory" in class_name or
                                class_name.endswith("Factory") or
                                "factory" in class_name.lower()):

                                # Skip test factories
                                if "test" in str(py_file).lower():
                                    continue

                                # Categorize by business domain
                                category = self.categorize_factory(class_name, str(py_file))

                                factory_info = {
                                    "name": class_name,
                                    "file": str(py_file.relative_to(self.project_root)),
                                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                                    "imports": self.extract_imports(content),
                                    "dependencies": self.find_factory_dependencies(content, class_name)
                                }

                                factory_implementations[category].append(factory_info)

                except Exception:
                    continue

        return factory_implementations

    def categorize_factory(self, class_name, file_path):
        """Categorize factory by business domain."""
        name_lower = class_name.lower()
        path_lower = file_path.lower()

        if "user" in name_lower and ("context" in name_lower or "execution" in name_lower):
            return "user_isolation"
        elif "websocket" in name_lower or "socket" in name_lower or "emitter" in name_lower:
            return "websocket"
        elif "database" in name_lower or "db" in name_lower or "session" in name_lower:
            return "database"
        elif "auth" in name_lower or "token" in name_lower:
            return "auth"
        elif "tool" in name_lower or "dispatcher" in name_lower:
            return "tools"
        elif "execution" in name_lower or "engine" in name_lower:
            return "execution"
        else:
            return "other"

    def extract_imports(self, content):
        """Extract import statements from file content."""
        imports = []
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
        return imports

    def find_factory_dependencies(self, content, factory_name):
        """Find other factories referenced in this factory."""
        dependencies = []
        # Look for other factory class names in the content
        factory_pattern = r'\b\w*[Ff]actory\w*\b'
        matches = re.findall(factory_pattern, content)
        for match in matches:
            if match != factory_name and match != "Factory":
                dependencies.append(match)
        return list(set(dependencies))

    def test_01_user_isolation_factory_ssot_compliance(self):
        """
        EXPECTED: PASS - Validates essential user isolation factories

        UserExecutionEngine factory patterns are CRITICAL for multi-user
        security and must follow SSOT principles while being preserved.

        SSOT Requirements for User Isolation Factories:
        - Single implementation per isolation pattern
        - Consistent import paths
        - No duplicate user context creation logic
        - Clear separation of user-specific resources
        """
        factory_implementations = self.find_factory_implementations()
        user_isolation_factories = factory_implementations["user_isolation"]

        # Check for SSOT compliance in user isolation
        ssot_violations = []
        duplicate_patterns = defaultdict(list)

        # Group factories by similar functionality
        for factory in user_isolation_factories:
            factory_name = factory["name"]

            # Check for duplicate patterns
            if "UserContext" in factory_name:
                duplicate_patterns["user_context"].append(factory)
            elif "UserExecution" in factory_name:
                duplicate_patterns["user_execution"].append(factory)
            elif "UserWebSocket" in factory_name:
                duplicate_patterns["user_websocket"].append(factory)

        # Check for SSOT violations (multiple implementations of same pattern)
        for pattern, factories in duplicate_patterns.items():
            if len(factories) > 1:
                ssot_violations.append({
                    "pattern": pattern,
                    "factories": factories,
                    "violation_type": "duplicate_implementation"
                })

        # Check import path consistency
        import_violations = []
        for factory in user_isolation_factories:
            factory_name = factory["name"]

            # Check if factory is imported consistently
            import_patterns = []
            for imp in factory["imports"]:
                if factory_name in imp:
                    import_patterns.append(imp)

            if len(set(import_patterns)) > 1:
                import_violations.append({
                    "factory": factory_name,
                    "import_patterns": import_patterns,
                    "violation_type": "inconsistent_imports"
                })

        # Generate report
        report = f"""
USER ISOLATION FACTORY SSOT COMPLIANCE
======================================

User Isolation Factories Found: {len(user_isolation_factories)}
Business Criticality: ESSENTIAL (Required for $500K+ ARR multi-user security)

"""

        if user_isolation_factories:
            report += "USER ISOLATION FACTORIES:\n"
            for factory in user_isolation_factories:
                report += f"- {factory['name']} ({factory['file']})\n"
                if factory['dependencies']:
                    report += f"  Dependencies: {', '.join(factory['dependencies'])}\n"

        # Report SSOT violations
        if ssot_violations:
            report += f"\n✗ SSOT VIOLATIONS DETECTED ({len(ssot_violations)}):\n"
            for violation in ssot_violations:
                report += f"\nPattern: {violation['pattern']}\n"
                report += f"Duplicate Implementations: {len(violation['factories'])}\n"
                for factory in violation["factories"]:
                    report += f"  - {factory['name']} ({factory['file']})\n"
                report += f"Recommendation: Consolidate to single SSOT implementation\n"

        if import_violations:
            report += f"\n✗ IMPORT PATH VIOLATIONS ({len(import_violations)}):\n"
            for violation in import_violations:
                report += f"\nFactory: {violation['factory']}\n"
                report += f"Inconsistent Import Patterns:\n"
                for pattern in violation["import_patterns"]:
                    report += f"  - {pattern}\n"

        if not ssot_violations and not import_violations:
            report += "\n✓ SSOT COMPLIANCE: All user isolation factories follow SSOT principles\n"
            report += "✓ BUSINESS PROTECTION: Multi-user security patterns preserved\n"

        print(report)

        # User isolation factories are CRITICAL - this should PASS
        if ssot_violations or import_violations:
            self.fail(f"User isolation factory SSOT violations detected: "
                     f"{len(ssot_violations)} duplicate patterns, {len(import_violations)} import issues. "
                     f"These are CRITICAL for business security and must be fixed while preserving functionality.")

        # If no violations, this is good (test passes)
        self.assertTrue(True, "User isolation factories comply with SSOT principles")

    def test_02_websocket_factory_ssot_consolidation(self):
        """
        EXPECTED: INITIALLY FAIL, then PASS after consolidation

        WebSocket factory patterns should be consolidated to single
        implementations per service following SSOT principles.

        SSOT Requirements for WebSocket Factories:
        - Single WebSocket manager factory per service
        - Single event emitter factory per service
        - No duplicate WebSocket creation logic
        - Consistent factory interfaces across services
        """
        factory_implementations = self.find_factory_implementations()
        websocket_factories = factory_implementations["websocket"]

        # Analyze WebSocket factory patterns
        websocket_patterns = defaultdict(list)
        ssot_violations = []

        for factory in websocket_factories:
            factory_name = factory["name"]

            # Categorize WebSocket factories by pattern
            if "Manager" in factory_name:
                websocket_patterns["manager"].append(factory)
            elif "Emitter" in factory_name:
                websocket_patterns["emitter"].append(factory)
            elif "Bridge" in factory_name:
                websocket_patterns["bridge"].append(factory)
            elif "Factory" in factory_name:
                websocket_patterns["factory"].append(factory)

        # Check for SSOT violations (should be max 1 per service per pattern)
        services = ["netra_backend", "auth_service", "shared"]

        for pattern, factories in websocket_patterns.items():
            service_factories = defaultdict(list)

            for factory in factories:
                service = "shared"
                if "netra_backend" in factory["file"]:
                    service = "netra_backend"
                elif "auth_service" in factory["file"]:
                    service = "auth_service"

                service_factories[service].append(factory)

            # Check for multiple factories per service per pattern
            for service, service_factory_list in service_factories.items():
                if len(service_factory_list) > 1:
                    ssot_violations.append({
                        "service": service,
                        "pattern": pattern,
                        "factories": service_factory_list,
                        "violation_type": "multiple_per_service"
                    })

        # Check for cross-service dependencies (should be minimal)
        cross_service_deps = []
        for factory in websocket_factories:
            for dep in factory["dependencies"]:
                factory_service = self.get_service_from_path(factory["file"])
                # This is a simplified check - in real implementation would be more thorough
                if "Factory" in dep and factory_service:
                    cross_service_deps.append({
                        "factory": factory["name"],
                        "service": factory_service,
                        "dependency": dep
                    })

        # Generate report
        report = f"""
WEBSOCKET FACTORY SSOT CONSOLIDATION
====================================

WebSocket Factories Found: {len(websocket_factories)}
Business Criticality: HIGH (Required for real-time chat functionality)

Pattern Distribution:
"""

        for pattern, factories in websocket_patterns.items():
            report += f"- {pattern.title()}: {len(factories)} factories\n"

        if websocket_factories:
            report += f"\nWEBSOCKET FACTORIES BY SERVICE:\n"
            for service in services:
                service_factories = [f for f in websocket_factories
                                   if service in f["file"]]
                if service_factories:
                    report += f"\n{service.upper()}:\n"
                    for factory in service_factories:
                        report += f"  - {factory['name']} ({factory['file']})\n"

        # Report SSOT violations
        if ssot_violations:
            report += f"\n✗ SSOT VIOLATIONS DETECTED ({len(ssot_violations)}):\n"
            for violation in ssot_violations:
                report += f"\nService: {violation['service']}\n"
                report += f"Pattern: {violation['pattern']}\n"
                report += f"Multiple Implementations: {len(violation['factories'])}\n"
                for factory in violation["factories"]:
                    report += f"  - {factory['name']} ({factory['file']})\n"
                report += f"Recommendation: Consolidate to single {violation['pattern']} factory per service\n"

        if cross_service_deps:
            report += f"\n⚠️ CROSS-SERVICE DEPENDENCIES ({len(cross_service_deps)}):\n"
            for dep in cross_service_deps:
                report += f"- {dep['factory']} ({dep['service']}) depends on {dep['dependency']}\n"

        if not ssot_violations:
            report += "\n✓ SSOT COMPLIANCE: WebSocket factories properly consolidated\n"

        print(report)

        # This test should initially FAIL, then PASS after consolidation
        if ssot_violations:
            self.fail(f"WebSocket factory SSOT violations detected: {len(ssot_violations)} patterns "
                     f"have multiple implementations per service. Consolidation required for SSOT compliance.")

        # If no violations, consolidation is complete
        self.assertTrue(True, "WebSocket factories properly consolidated following SSOT principles")

    def test_03_database_connection_factory_ssot_validation(self):
        """
        EXPECTED: PASS - Validates essential database connection patterns

        Database connection factories that provide genuine value
        (connection pooling, transaction management) should be preserved.

        SSOT Requirements for Database Factories:
        - Single connection factory per database type (PostgreSQL, ClickHouse, Redis)
        - Single session factory per ORM/database
        - No duplicate connection logic
        - Clear separation of database-specific patterns
        """
        factory_implementations = self.find_factory_implementations()
        database_factories = factory_implementations["database"]

        # Categorize database factories by type
        db_patterns = {
            "postgres": [],
            "clickhouse": [],
            "redis": [],
            "session": [],
            "connection": []
        }

        for factory in database_factories:
            factory_name_lower = factory["name"].lower()

            if "postgres" in factory_name_lower:
                db_patterns["postgres"].append(factory)
            elif "clickhouse" in factory_name_lower:
                db_patterns["clickhouse"].append(factory)
            elif "redis" in factory_name_lower:
                db_patterns["redis"].append(factory)
            elif "session" in factory_name_lower:
                db_patterns["session"].append(factory)
            elif "connection" in factory_name_lower:
                db_patterns["connection"].append(factory)

        # Check for SSOT violations (should be 1 factory per database type)
        ssot_violations = []
        for db_type, factories in db_patterns.items():
            if len(factories) > 1:
                ssot_violations.append({
                    "db_type": db_type,
                    "factories": factories,
                    "violation_type": "multiple_implementations"
                })

        # Validate essential database patterns are preserved
        essential_patterns = ["connection", "session"]
        missing_patterns = []
        for pattern in essential_patterns:
            if not db_patterns[pattern]:
                missing_patterns.append(pattern)

        # Generate report
        report = f"""
DATABASE CONNECTION FACTORY SSOT VALIDATION
===========================================

Database Factories Found: {len(database_factories)}
Business Criticality: HIGH (Required for data persistence and performance)

Database Type Distribution:
"""

        for db_type, factories in db_patterns.items():
            status = "✓" if len(factories) <= 1 else f"✗ ({len(factories)} implementations)"
            report += f"- {db_type.title()}: {len(factories)} factories {status}\n"

        if database_factories:
            report += f"\nDATABASE FACTORIES:\n"
            for factory in database_factories:
                report += f"- {factory['name']} ({factory['file']})\n"
                if factory["methods"]:
                    key_methods = [m for m in factory["methods"] if not m.startswith('_')][:3]
                    report += f"  Key Methods: {', '.join(key_methods)}\n"

        # Report SSOT violations
        if ssot_violations:
            report += f"\n✗ SSOT VIOLATIONS DETECTED ({len(ssot_violations)}):\n"
            for violation in ssot_violations:
                report += f"\nDatabase Type: {violation['db_type']}\n"
                report += f"Multiple Implementations: {len(violation['factories'])}\n"
                for factory in violation["factories"]:
                    report += f"  - {factory['name']} ({factory['file']})\n"
                report += f"Recommendation: Consolidate to single factory per database type\n"

        if missing_patterns:
            report += f"\n⚠️ MISSING ESSENTIAL PATTERNS: {', '.join(missing_patterns)}\n"
            report += "Recommendation: Ensure essential database patterns are preserved\n"

        if not ssot_violations and not missing_patterns:
            report += "\n✓ SSOT COMPLIANCE: Database factories properly consolidated\n"
            report += "✓ ESSENTIAL PATTERNS: All critical database patterns preserved\n"

        print(report)

        # Database factories should follow SSOT principles while being preserved
        if ssot_violations:
            self.fail(f"Database factory SSOT violations detected: {len(ssot_violations)} database types "
                     f"have multiple implementations. Consolidation required while preserving functionality.")

        if missing_patterns:
            self.fail(f"Essential database patterns missing: {', '.join(missing_patterns)}. "
                     f"These are critical for business functionality and must be preserved.")

        # If no violations, database factories are properly structured
        self.assertTrue(True, "Database factories follow SSOT principles and preserve essential patterns")

    def test_04_auth_token_factory_ssot_compliance(self):
        """
        EXPECTED: PASS - Validates security-critical auth factories

        Auth token factories are CRITICAL for security and must follow
        SSOT principles while being preserved.

        SSOT Requirements for Auth Factories:
        - Single JWT token factory
        - Single session factory per service
        - Single auth validation factory
        - No duplicate auth logic across services
        """
        factory_implementations = self.find_factory_implementations()
        auth_factories = factory_implementations["auth"]

        # Categorize auth factories by pattern
        auth_patterns = {
            "token": [],
            "jwt": [],
            "session": [],
            "validation": [],
            "user": []
        }

        for factory in auth_factories:
            factory_name_lower = factory["name"].lower()

            if "jwt" in factory_name_lower:
                auth_patterns["jwt"].append(factory)
            elif "token" in factory_name_lower:
                auth_patterns["token"].append(factory)
            elif "session" in factory_name_lower:
                auth_patterns["session"].append(factory)
            elif "validation" in factory_name_lower or "validator" in factory_name_lower:
                auth_patterns["validation"].append(factory)
            elif "user" in factory_name_lower:
                auth_patterns["user"].append(factory)

        # Check for SSOT violations (should be 1 factory per auth pattern globally)
        ssot_violations = []
        for pattern, factories in auth_patterns.items():
            if len(factories) > 1:
                ssot_violations.append({
                    "pattern": pattern,
                    "factories": factories,
                    "violation_type": "multiple_implementations"
                })

        # Check for auth service SSOT compliance (auth should be centralized)
        auth_service_factories = [f for f in auth_factories if "auth_service" in f["file"]]
        non_auth_service_factories = [f for f in auth_factories if "auth_service" not in f["file"]]

        auth_centralization_violations = []
        if non_auth_service_factories:
            for factory in non_auth_service_factories:
                auth_centralization_violations.append({
                    "factory": factory,
                    "violation_type": "auth_logic_outside_auth_service"
                })

        # Generate report
        report = f"""
AUTH TOKEN FACTORY SSOT COMPLIANCE
==================================

Auth Factories Found: {len(auth_factories)}
Business Criticality: CRITICAL (Required for security and compliance)

Auth Pattern Distribution:
"""

        for pattern, factories in auth_patterns.items():
            status = "✓" if len(factories) <= 1 else f"✗ ({len(factories)} implementations)"
            report += f"- {pattern.title()}: {len(factories)} factories {status}\n"

        # Service distribution
        report += f"\nAUTH FACTORIES BY SERVICE:\n"
        report += f"- Auth Service: {len(auth_service_factories)} factories (RECOMMENDED)\n"
        report += f"- Other Services: {len(non_auth_service_factories)} factories (REVIEW NEEDED)\n"

        if auth_factories:
            report += f"\nAUTH FACTORIES:\n"
            for factory in auth_factories:
                service_marker = "🏢 AUTH_SERVICE" if "auth_service" in factory["file"] else "⚠️ OTHER_SERVICE"
                report += f"- {factory['name']} ({factory['file']}) {service_marker}\n"

        # Report SSOT violations
        if ssot_violations:
            report += f"\n✗ SSOT VIOLATIONS DETECTED ({len(ssot_violations)}):\n"
            for violation in ssot_violations:
                report += f"\nAuth Pattern: {violation['pattern']}\n"
                report += f"Multiple Implementations: {len(violation['factories'])}\n"
                for factory in violation["factories"]:
                    report += f"  - {factory['name']} ({factory['file']})\n"
                report += f"Recommendation: Consolidate to single {violation['pattern']} factory\n"

        if auth_centralization_violations:
            report += f"\n⚠️ AUTH CENTRALIZATION VIOLATIONS ({len(auth_centralization_violations)}):\n"
            for violation in auth_centralization_violations:
                factory = violation["factory"]
                report += f"- {factory['name']} ({factory['file']})\n"
            report += "Recommendation: Centralize all auth logic in auth_service\n"

        if not ssot_violations and not auth_centralization_violations:
            report += "\n✓ SSOT COMPLIANCE: Auth factories properly consolidated\n"
            report += "✓ SECURITY PATTERN: Auth logic properly centralized\n"

        print(report)

        # Auth factories are CRITICAL for security - violations must be fixed
        if ssot_violations:
            self.fail(f"Auth factory SSOT violations detected: {len(ssot_violations)} auth patterns "
                     f"have multiple implementations. This creates security risks and must be consolidated.")

        if auth_centralization_violations:
            self.fail(f"Auth centralization violations detected: {len(auth_centralization_violations)} "
                     f"auth factories exist outside auth_service. This violates security architecture.")

        # If no violations, auth factories are properly secured
        self.assertTrue(True, "Auth factories follow SSOT principles and maintain security compliance")

    def get_service_from_path(self, file_path):
        """Extract service name from file path."""
        if "netra_backend" in file_path:
            return "netra_backend"
        elif "auth_service" in file_path:
            return "auth_service"
        elif "shared" in file_path:
            return "shared"
        else:
            return "unknown"


if __name__ == "__main__":
    import unittest
    unittest.main()