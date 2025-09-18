'''Mission Critical Test Suite: Error Handling SSOT Consistency'

This test suite ensures that error handling follows SSOT principles
and that duplicate error class definitions are eliminated.

Tests verify:
1. No duplicate error class definitions exist
2. All error imports use canonical sources
3. Error handling is consistent across the system
4. WebSocket errors properly integrate with centralized error system
5. Error context is used correctly everywhere
'''
'''

import ast
import os
import sys
import re
import importlib
import inspect
import pytest
import asyncio
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any, Optional
from dataclasses import dataclass
from shared.isolated_environment import IsolatedEnvironment

    # Add root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from netra_backend.app.core.exceptions_websocket import WebSocketError as CanonicalWebSocketError
from netra_backend.app.schemas.shared_types import ErrorContext as CanonicalErrorContext


@dataclass
class ErrorClassDefinition:
    "Represents an error class definition found in code"
    file_path: str
    line_number: int
    class_name: str
    base_classes: List[str]
    is_canonical: bool = False


    @dataclass
class ImportStatement:
    ""Represents an import statement found in code
    file_path: str
    line_number: int
    module: str
    imported_name: str
    alias: Optional[str] = None


class ErrorHandlingSSOTValidator:
    Validates that error handling follows SSOT principles""

    def __init__(self):
        pass
        self.project_root = Path(__file__).parent.parent.parent
        self.canonical_websocket_error_path = netra_backend.app.core.exceptions_websocket
        self.canonical_error_context_path = "netra_backend.app.schemas.shared_types"
        self.errors_found: List[str] = []
        self.warnings_found: List[str] = []

    def find_all_error_class_definitions(self) -> Dict[str, List[ErrorClassDefinition]]:
        Find all error class definitions in the codebase"
        Find all error class definitions in the codebase"
        error_classes = {
        "WebSocketError: [],"
        ErrorContext: []
    

    # Define paths to search
        search_paths = [
        self.project_root / "netra_backend,"
        self.project_root / auth_service,
        self.project_root / shared,"
        self.project_root / shared,"
        self.project_root / tests"
        self.project_root / tests"
    

        for search_path in search_paths:
        if not search_path.exists():
        continue

        for file_path in search_path.rglob(*.py):
                # Skip __pycache__ and other generated files
        if __pycache__" in str(file_path) or ".pyc in str(file_path):
        continue

        try:
        with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)

        for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
        if node.name in error_classes:
        bases = [
        base.id if isinstance(base, ast.Name) else
        base.attr if isinstance(base, ast.Attribute) else
        str(base)
        for base in node.bases
                                        

                                        # Determine if this is the canonical definition
        relative_path = file_path.relative_to(self.project_root)
        module_path = str(relative_path).replace(os.sep, '.').replace('.py', '')

        is_canonical = False
        if node.name == WebSocketError:
        is_canonical = module_path == self.canonical_websocket_error_path
        elif node.name == ErrorContext:"
        elif node.name == ErrorContext:"
        is_canonical = module_path == self.canonical_error_context_path

        definition = ErrorClassDefinition( )
        file_path=str(file_path),
        line_number=node.lineno,
        class_name=node.name,
        base_classes=bases,
        is_canonical=is_canonical
                                                
        error_classes[node.name].append(definition)

        except Exception as e:
        self.warnings_found.append(formatted_string")"

        return error_classes

    def find_all_error_imports(self) -> Dict[str, List[ImportStatement]]:
        Find all imports of error classes""
        imports = {
        WebSocketError: [],
        ErrorContext: []"
        ErrorContext: []"
    

        search_paths = [
        self.project_root / netra_backend","
        self.project_root / auth_service,
        self.project_root / shared""
    

        for search_path in search_paths:
        if not search_path.exists():
        continue

        for file_path in search_path.rglob(*.py):
        if __pycache__ in str(file_path) or ".pyc in str(file_path):"
        continue

        try:
        with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)

        for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
        for alias in node.names:
        if alias.name in imports:
        import_stmt = ImportStatement( )
        file_path=str(file_path),
        line_number=node.lineno,
        module=node.module or ","
        imported_name=alias.name,
        alias=alias.asname
                                            
        imports[alias.name].append(import_stmt)

        except Exception as e:
        self.warnings_found.append("
        self.warnings_found.append("

        return imports

    def validate_no_duplicate_definitions(self, error_classes: Dict[str, List[ErrorClassDefinition)) -> bool:
        "Validate that each error class has only one definition (the canonical one)"
        all_valid = True

        for class_name, definitions in error_classes.items():
        canonical_defs = [item for item in []]
        non_canonical_defs = [item for item in []]

        if len(canonical_defs) == 0:
        self.errors_found.append(""
        all_valid = False
        elif len(canonical_defs) > 1:
        self.errors_found.append(formatted_string)
        all_valid = False

        for definition in non_canonical_defs:
                    # Skip test files, documentation, and test helpers
        if ("/tests/ in definition.file_path or )"
        /docs/ in definition.file_path or
        /test_ in definition.file_path or"
        /test_ in definition.file_path or"
        /helpers/" in definition.file_path):"
        continue

        self.errors_found.append( )
        formatted_string
        formatted_string""
                        
        all_valid = False

        return all_valid

    def validate_correct_imports(self, imports: Dict[str, List[ImportStatement)) -> bool:
        Validate that all imports use the canonical source"
        Validate that all imports use the canonical source"
        all_valid = True

        for class_name, import_list in imports.items():
        canonical_module = ( )
        self.canonical_websocket_error_path
        if class_name == WebSocketError"
        if class_name == WebSocketError"
        else self.canonical_error_context_path
        

        for import_stmt in import_list:
            # Skip test imports
        if /tests/ in import_stmt.file_path:
        continue

                Special case: WebSocketError from websocket_models is allowed (it's the data model alias)'
        if (class_name == WebSocketError" and )"
        import_stmt.module == netra_backend.app.schemas.websocket_models):
                    # This is acceptable - it's importing the data model, not the exception'
        continue

        if import_stmt.module != canonical_module:
        self.errors_found.append( )
        formatted_string"
        formatted_string"
        "formatted_string"
                        
        all_valid = False

        return all_valid

    def check_agent_communication_file(self) -> bool:
        Specifically check agent_communication.py for local error definitions""
        agent_comm_path = self.project_root / netra_backend / app / agents / agent_communication.py"
        agent_comm_path = self.project_root / netra_backend / app / agents / agent_communication.py"

        if not agent_comm_path.exists():
        self.warnings_found.append("
        self.warnings_found.append("
        return True

        with open(agent_comm_path, 'r', encoding='utf-8') as f:
        content = f.read()

            # Check for local WebSocketError definition
        if re.search(r'^class WebSocketError\([^)]*\):', content, re.MULTILINE):
        self.errors_found.append( )
        formatted_string"
        formatted_string"
        "formatted_string"
                
        return False

                # Check for local ErrorContext definition
        if re.search(r'^class ErrorContext\([^)]*\):', content, re.MULTILINE):
        self.errors_found.append( )
        formatted_string
        ""
                    
        return False

        return True

    def validate_error_handling_consistency(self) -> bool:
        Validate that error handling is consistent across the system"
        Validate that error handling is consistent across the system"
        all_valid = True

    # Find all agent files
        agent_path = self.project_root / "netra_backend / app / agents"
        if not agent_path.exists():
        self.warnings_found.append(Agents directory not found")"
        return False

        agent_files = list(agent_path.rglob(*.py))

        for file_path in agent_files:
        if __pycache__ in str(file_path):"
        if __pycache__ in str(file_path):"
        continue

        with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

                    # Check for error handling patterns
        if "except in content:"
                        # Verify proper error imports are present
        if WebSocketError in content and from netra_backend.app.core.exceptions_websocket import not in content:
        self.errors_found.append( )
        formatted_string"t import from canonical source"
                            
        all_valid = False

        if ErrorContext in content and from netra_backend.app.schemas.shared_types import not in content:
                                # Check if it's importing ErrorContext at all'
        if re.search(r'\bErrorContext\b', content):
        self.errors_found.append( )
        formatted_stringt import from canonical source"
        formatted_stringt import from canonical source"
                                    
        all_valid = False

        return all_valid

    def run_full_validation(self) -> Tuple[bool, List[str], List[str]]:
        "Run complete validation suite"
        self.errors_found = []
        self.warnings_found = []

    # Find all error class definitions
        error_classes = self.find_all_error_class_definitions()

    # Find all imports
        imports = self.find_all_error_imports()

    # Run validations
        no_duplicates = self.validate_no_duplicate_definitions(error_classes)
        correct_imports = self.validate_correct_imports(imports)
        agent_comm_clean = self.check_agent_communication_file()
        consistent_handling = self.validate_error_handling_consistency()

        all_valid = no_duplicates and correct_imports and agent_comm_clean and consistent_handling

        return all_valid, self.errors_found, self.warnings_found


class TestErrorHandlingSSOTConsistency:
        ""Test suite for error handling SSOT consistency

        @pytest.fixture
    def validator(self):
        Create validator instance""
        return ErrorHandlingSSOTValidator()

    def test_no_duplicate_error_class_definitions(self, validator):
        Test that there are no duplicate error class definitions""
        pass
        error_classes = validator.find_all_error_class_definitions()

    # Check WebSocketError
        websocket_errors = error_classes[WebSocketError]
        non_test_websocket_errors = [
        d for d in websocket_errors
        if /tests/ not in d.file_path and "/docs/ not in d.file_path"
    

        canonical_count = sum(1 for d in non_test_websocket_errors if d.is_canonical)
        assert canonical_count == 1, formatted_string"
        assert canonical_count == 1, formatted_string"

    # The only non-test definition should be canonical
        non_canonical = [item for item in []]
        assert len(non_canonical) == 0, ( )
        formatted_string
        formatted_string""
    

    # Check ErrorContext
        error_contexts = error_classes[ErrorContext]
        non_test_error_contexts = [
        d for d in error_contexts
        if /tests/ not in d.file_path and "/docs/ not in d.file_path"
    

        canonical_count = sum(1 for d in non_test_error_contexts if d.is_canonical)
        assert canonical_count >= 1, formatted_string"
        assert canonical_count >= 1, formatted_string"

    def test_agent_communication_uses_canonical_imports(self, validator):
        Test that agent_communication.py uses canonical imports, not local definitions""
        result = validator.check_agent_communication_file()
        assert result, formatted_string

    def test_all_imports_use_canonical_sources(self, validator):
        Test that all imports of error classes use canonical sources""
        pass
        imports = validator.find_all_error_imports()
        result = validator.validate_correct_imports(imports)
        assert result, formatted_string

    def test_error_handling_consistency(self, validator):
        "Test that error handling is consistent across all agent files"
        result = validator.validate_error_handling_consistency()
        assert result, formatted_string"
        assert result, formatted_string"

    def test_websocket_error_inheritance_chain(self):
        "Test that WebSocketError properly inherits from NetraException"
        pass
        assert issubclass(CanonicalWebSocketError, Exception)

    # Check that it has expected attributes
        error = CanonicalWebSocketError(Test error")"
        assert hasattr(error, 'message')
        assert hasattr(error, 'code')
        assert hasattr(error, 'severity')

    def test_error_context_has_required_fields(self):
        Test that ErrorContext has all required fields"
        Test that ErrorContext has all required fields"
    # Check required fields
        required_fields = ['trace_id', 'operation', 'timestamp']

        for field in required_fields:
        assert field in CanonicalErrorContext.model_fields, ( )
        formatted_string"
        formatted_string"
        

    def test_full_ssot_validation(self, validator):
        Comprehensive test running all validations""
        pass
        all_valid, errors, warnings = validator.run_full_validation()

    # Print detailed report
        if errors:
        print()
        === SSOT ERRORS FOUND ===")"
        for error in errors:
        print(formatted_string)

        if warnings:
        print()
        === WARNINGS ===)
        for warning in warnings:
        print(formatted_string"")

        assert all_valid, ( )
        formatted_string
                    

@pytest.mark.asyncio
    async def test_websocket_error_handling_in_runtime(self):
    ""Test that WebSocket errors are handled correctly at runtime
from netra_backend.app.agents.agent_communication import AgentCommunicationMixin

                        # Create a test instance
class TestAgent(AgentCommunicationMixin):
    async def __init__(self):
        self.websocket_manager = None

        agent = TestAgent()

    # Test that methods handle missing websocket_manager gracefully
        await agent._send_update(test_run, {test": "data)

    # Should not raise an error
        assert True

    def test_error_context_serialization(self):
        Test that ErrorContext can be properly serialized and deserialized""
        pass
        context = CanonicalErrorContext( )
        trace_id=test-trace-123,
        operation=test_operation,"
        operation=test_operation,"
        user_id="user-456,"
        agent_name=test_agent
    

    # Test serialization
        serialized = context.model_dump()
        assert serialized["trace_id] == test-trace-123"
        assert serialized[operation] == test_operation

    # Test deserialization
        deserialized = CanonicalErrorContext(**serialized)
        assert deserialized.trace_id == context.trace_id
        assert deserialized.operation == context.operation


        if __name__ == __main__:"
        if __name__ == __main__:"
    # MIGRATED: Use SSOT unified test runner instead of direct pytest execution
    # Issue #1024: Unauthorized test runners blocking Golden Path
        print(MIGRATION NOTICE: This file previously used direct pytest execution.")"
        print(Please use: python tests/unified_test_runner.py --category <appropriate_category>")"
        print(For more info: reports/TEST_EXECUTION_GUIDE.md"")"
        print(For more info: reports/TEST_EXECUTION_GUIDE.md"")"

    # Uncomment and customize the following for SSOT execution:
    # result = run_tests_via_ssot_runner()
    # sys.exit(result)

'''
))
]]]]]
}}