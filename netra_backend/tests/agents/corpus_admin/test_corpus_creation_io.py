"""
Unit tests for corpus_creation_io
Coverage Target: 90%
Business Value: Revenue-critical component
"""""

import pytest
from netra_backend.app.agents.corpus_admin import corpus_creation_io
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

class TestCorpusCreationIo:
    """Test suite for corpus_creation_io functions"""

    def test_parse_json_valid(self):
        """Test parse_json with valid JSON"""
        result = corpus_creation_io.parse_json('{"key": "value"}')
        assert result == {"key": "value"}

        def test_parse_json_invalid(self):
            """Test parse_json with invalid JSON"""
            result = corpus_creation_io.parse_json('invalid json')
            assert result is None

            def test_validate_array_valid(self):
                """Test validate_array with valid array"""
                result = corpus_creation_io.validate_array([1, 2, 3])
                assert result is True

                def test_validate_array_invalid(self):
                    """Test validate_array with non-array"""
                    result = corpus_creation_io.validate_array({"key": "value"})
                    assert result is False
