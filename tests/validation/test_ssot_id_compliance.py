"""
SSOT ID Management Compliance Tests

This test suite validates that all ID generation across the system uses 
the Single Source of Truth (SSOT) UnifiedIdGenerator and prevents 
regression to scattered UUID patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal (Infrastructure)
- Business Goal: Security and multi-user isolation integrity
- Value Impact: Prevents ID collisions and cross-user data contamination
- Strategic Impact: CRITICAL - Maintains system security and reliability
"""

import ast
import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

import pytest

from shared.id_generation import UnifiedIdGenerator, generate_uuid_replacement


class TestSSOTCompliance:
    """Test suite for SSOT ID generation compliance."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent
    
    def get_python_files(self, project_root: Path, exclude_patterns: List[str] = None) -> List[Path]:
        """Get all Python files in the project, excluding specified patterns."""
        if exclude_patterns is None:
            exclude_patterns = [
                "**/test_ssot_id_compliance.py",  # Exclude this test file
                "**/__pycache__/**",
                "**/node_modules/**",
                "**/venv/**",
                "**/env/**",
                "**/.git/**"
            ]
        
        python_files = []
        for pattern in ["**/*.py"]:
            for file_path in project_root.rglob(pattern):
                # Check if file should be excluded
                should_exclude = False
                for exclude_pattern in exclude_patterns:
                    if file_path.match(exclude_pattern):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    python_files.append(file_path)
        
        return python_files
    
    def find_uuid_violations(self, file_path: Path) -> List[Tuple[int, str]]:
        """Find UUID generation violations in a Python file."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except (UnicodeDecodeError, IOError):
            return violations
        
        # Patterns that indicate SSOT violations
        violation_patterns = [
            r'uuid\.uuid4\(\)\.hex\[:\d+\]',  # uuid.uuid4().hex[:8]
            r'uuid\.uuid4\(\)\.hex',          # uuid.uuid4().hex
            r'str\(uuid\.uuid4\(\)\)',        # str(uuid.uuid4())
            r'uuid4\(\)\.hex',                # uuid4().hex (if imported as uuid4)
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern in violation_patterns:
                if re.search(pattern, line):
                    # Skip lines that are comments explaining the violation
                    if not line.strip().startswith('#'):
                        violations.append((line_num, line.strip()))
        
        return violations
    
    def test_no_scattered_uuid_patterns(self, project_root: Path):
        """Test that no scattered UUID patterns exist in production code."""
        python_files = self.get_python_files(project_root)
        
        all_violations = {}
        total_violations = 0
        
        # Focus on critical production code paths
        critical_paths = [
            "netra_backend/app/",
            "shared/",
            "test_framework/",
            "auth_service/"
        ]
        
        for file_path in python_files:
            # Only check critical production paths
            if any(str(file_path).replace('\\', '/').find(path) != -1 for path in critical_paths):
                violations = self.find_uuid_violations(file_path)
                if violations:
                    relative_path = file_path.relative_to(project_root)
                    all_violations[str(relative_path)] = violations
                    total_violations += len(violations)
        
        # Generate detailed error message if violations found
        if all_violations:
            error_msg = f"Found {total_violations} SSOT violations in {len(all_violations)} files:\n\n"
            
            for file_path, violations in all_violations.items():
                error_msg += f"📁 {file_path}:\n"
                for line_num, line in violations:
                    error_msg += f"  Line {line_num}: {line}\n"
                error_msg += "\n"
            
            error_msg += "🔧 REMEDIATION:\n"
            error_msg += "Replace scattered UUID patterns with SSOT methods:\n\n"
            error_msg += "❌ BAD: str(uuid.uuid4())\n"
            error_msg += "✅ GOOD: UnifiedIdGenerator.generate_base_id('prefix')\n\n"
            error_msg += "❌ BAD: uuid.uuid4().hex[:8]\n"
            error_msg += "✅ GOOD: generate_uuid_replacement()\n\n"
            error_msg += "❌ BAD: f'conn_{uuid.uuid4().hex[:8]}'\n"
            error_msg += "✅ GOOD: UnifiedIdGenerator.generate_websocket_connection_id(user_id)\n\n"
            error_msg += "See SSOT_UNIFIED_ID_MANAGER_AUDIT_REPORT.md for complete remediation guide."
            
            pytest.fail(error_msg)
    
    def test_userexecutioncontext_uses_ssot(self, project_root: Path):
        """Test that all UserExecutionContext creation uses SSOT methods."""
        python_files = self.get_python_files(project_root)
        violations = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for UserExecutionContext creation patterns
                if 'UserExecutionContext(' in content:
                    lines = content.split('\n')
                    for line_num, line in enumerate(lines, 1):
                        if 'UserExecutionContext(' in line:
                            # Check the following lines for UUID violations in the constructor
                            context_lines = []
                            current_line = line_num - 1
                            paren_count = line.count('(') - line.count(')')
                            
                            # Collect the full constructor call
                            while current_line < len(lines) and paren_count > 0:
                                context_lines.append(lines[current_line])
                                current_line += 1
                                if current_line < len(lines):
                                    paren_count += lines[current_line].count('(') - lines[current_line].count(')')
                            
                            full_context = '\n'.join(context_lines)
                            
                            # Check for UUID violations in the context creation
                            if re.search(r'(str\(uuid\.uuid4\(\)\)|uuid\.uuid4\(\)\.hex)', full_context):
                                relative_path = file_path.relative_to(project_root)
                                violations.append(f"{relative_path}:{line_num} - UserExecutionContext with inline UUID")
                                
            except (UnicodeDecodeError, IOError):
                continue
        
        if violations:
            error_msg = "Found UserExecutionContext creation with SSOT violations:\n\n"
            for violation in violations:
                error_msg += f"  🚨 {violation}\n"
            error_msg += "\n✅ SOLUTION: Use create_user_execution_context_factory() from shared.id_generation\n"
            pytest.fail(error_msg)
    
    def test_unified_id_generator_functionality(self):
        """Test that UnifiedIdGenerator provides expected functionality."""
        # Test basic ID generation
        basic_id = UnifiedIdGenerator.generate_base_id("test")
        assert basic_id.startswith("test_")
        assert len(basic_id.split('_')) >= 3  # prefix_timestamp_counter[_random]
        
        # Test WebSocket ID generation
        user_id = "test_user"
        ws_conn_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        assert "ws_conn" in ws_conn_id
        assert user_id[:8] in ws_conn_id
        
        ws_client_id = UnifiedIdGenerator.generate_websocket_client_id(user_id)
        assert "ws_client" in ws_client_id
        assert user_id[:8] in ws_client_id
        
        # Test user context ID generation
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids(user_id, "test_op")
        assert thread_id.startswith("thread_test_op_")
        assert run_id.startswith("run_test_op_")
        assert request_id.startswith("req_test_op_")
        
        # Test UUID replacement function
        replacement = generate_uuid_replacement()
        assert len(replacement) == 8  # Should be 8 characters
        assert replacement.isalnum()  # Should be alphanumeric
    
    def test_id_uniqueness_and_collision_protection(self):
        """Test that generated IDs are unique and collision-resistant."""
        # Generate multiple IDs and ensure they're unique
        ids = []
        for i in range(100):
            id1 = UnifiedIdGenerator.generate_base_id("test")
            id2 = UnifiedIdGenerator.generate_websocket_connection_id(f"user_{i}")
            id3 = generate_uuid_replacement()
            ids.extend([id1, id2, id3])
        
        # Check for uniqueness
        unique_ids = set(ids)
        assert len(unique_ids) == len(ids), f"Found {len(ids) - len(unique_ids)} duplicate IDs!"
        
        # Test user context ID relationships
        thread_id, run_id, request_id = UnifiedIdGenerator.generate_user_context_ids("user123", "operation")
        context_ids = [thread_id, run_id, request_id]
        
        # All should be unique
        assert len(set(context_ids)) == 3
        
        # All should contain operation context
        assert all("operation" in id_val for id_val in context_ids)
    
    def test_id_parsing_and_validation(self):
        """Test ID parsing and validation functionality."""
        # Generate a test ID
        test_id = UnifiedIdGenerator.generate_base_id("test_prefix")
        
        # Parse the ID
        parsed = UnifiedIdGenerator.parse_id(test_id)
        assert parsed is not None
        assert parsed.prefix == "test_prefix"
        assert parsed.full_id == test_id
        
        # Validate the ID
        assert UnifiedIdGenerator.is_valid_id(test_id)
        assert UnifiedIdGenerator.is_valid_id(test_id, "test_prefix")
        
        # Test invalid IDs
        assert not UnifiedIdGenerator.is_valid_id("invalid_id")
        assert not UnifiedIdGenerator.is_valid_id(test_id, "wrong_prefix")
    
    def test_critical_production_files_compliance(self, project_root: Path):
        """Test that critical production files are SSOT compliant."""
        critical_files = [
            "netra_backend/app/dependencies.py",
            "netra_backend/app/websocket_core/user_context_extractor.py",
            "test_framework/websocket_helpers.py",
            "test_framework/utils/websocket.py"
        ]
        
        violations_found = False
        
        for file_path in critical_files:
            full_path = project_root / file_path
            if full_path.exists():
                violations = self.find_uuid_violations(full_path)
                if violations:
                    violations_found = True
                    pytest.fail(f"CRITICAL: Found SSOT violations in {file_path}:\n" + 
                               "\n".join([f"  Line {line_num}: {line}" for line_num, line in violations]))
        
        if not violations_found:
            # Success - log that critical files are compliant
            print("✅ All critical production files are SSOT compliant")


class TestIDGenerationRegression:
    """Test suite to prevent regression in ID generation patterns."""
    
    def test_no_new_uuid_imports(self, project_root: Path):
        """Test that no new direct UUID imports are added to critical files."""
        critical_files = [
            "netra_backend/app/dependencies.py",
            "netra_backend/app/websocket_core/user_context_extractor.py",
        ]
        
        for file_path in critical_files:
            full_path = project_root / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for problematic import patterns
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith('import uuid') or line.strip().startswith('from uuid import'):
                        # Allow if there's a SSOT compliance comment
                        if 'SSOT' not in line and 'compliance' not in line.lower():
                            pytest.fail(f"{file_path}:{line_num} - New UUID import detected. Use shared.id_generation instead.")
    
    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])