"""
Comprehensive unit tests for corpus_admin validators.

Business Value: Ensures approval validation and business rule enforcement for
critical corpus operations. These validators protect against unauthorized
operations and ensure proper approval workflows for enterprise clients.
"""

import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.corpus_admin.validators import CorpusApprovalValidator
from netra_backend.app.agents.corpus_admin.models import (
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest)
from netra_backend.app.agents.state import DeepAgentState


class TestCorpusApprovalValidator:
    """Test CorpusApprovalValidator class."""
    pass

    @pytest.fixture
    def validator(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create validator instance for testing."""
    pass
        return CorpusApprovalValidator()

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create sample corpus metadata for testing."""
    pass
        return CorpusMetadata(
            corpus_name="test_corpus",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="Test knowledge base for validation",
            access_level="private"
        )

    @pytest.fixture
    def sample_state(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create sample agent state for testing."""
    pass
        state = DeepAgentState()
        state.user_request = "Delete the outdated documentation corpus"
        state.user_id = "test_user_123"
        state.chat_thread_id = "thread_456"
        state.triage_result = {"category": "corpus_management", "is_admin_mode": True}
        return state

    def test_initialization(self, validator):
        """Test validator initialization."""
        assert validator is not None
        assert isinstance(validator.approval_thresholds, dict)
        assert "delete_documents" in validator.approval_thresholds
        assert "update_documents" in validator.approval_thresholds
        assert "export_size_mb" in validator.approval_thresholds

    def test_approval_thresholds_values(self, validator):
        """Test approval threshold values are reasonable."""
    pass
        thresholds = validator.approval_thresholds
        
        assert thresholds["delete_documents"] == 100
        assert thresholds["update_documents"] == 500
        assert thresholds["export_size_mb"] == 100
        
        # Ensure all thresholds are positive numbers
        for key, value in thresholds.items():
            assert isinstance(value, (int, float))
            assert value > 0


class TestApprovalRequirements:
    """Test approval requirement checking logic."""
    pass

    @pytest.fixture
    def validator(self):
    """Use real service instance."""
    # TODO: Initialize real service
        return CorpusApprovalValidator()

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusMetadata(
            corpus_name="approval_test_corpus",
            corpus_type=CorpusType.DOCUMENTATION,
            description="Test corpus for approval validation"
        )

    @pytest.mark.asyncio
    async def test_delete_operation_requires_approval(self, validator, sample_metadata):
        """Test that DELETE operations always require approval."""
        delete_request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = {}
        
        requires_approval = await validator.check_approval_requirements(delete_request, state)
        assert requires_approval is True

    @pytest.mark.asyncio
    async def test_non_delete_operations_basic(self, validator, sample_metadata):
        """Test that non-DELETE operations don't automatically require approval."""
    pass
        state = DeepAgentState()
        state.triage_result = {}
        
        # Test CREATE operation
        create_request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )
        requires_approval = await validator.check_approval_requirements(create_request, state)
        assert requires_approval is False

        # Test SEARCH operation
        search_request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=sample_metadata
        )
        requires_approval = await validator.check_approval_requirements(search_request, state)
        assert requires_approval is False

        # Test ANALYZE operation
        analyze_request = CorpusOperationRequest(
            operation=CorpusOperation.ANALYZE,
            corpus_metadata=sample_metadata
        )
        requires_approval = await validator.check_approval_requirements(analyze_request, state)
        assert requires_approval is False

    @pytest.mark.asyncio
    async def test_explicit_approval_request_in_triage(self, validator, sample_metadata):
        """Test approval when explicitly requested in triage result."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = {"require_approval": True}
        
        requires_approval = await validator.check_approval_requirements(request, state)
        assert requires_approval is True

    @pytest.mark.asyncio
    async def test_no_explicit_approval_request_in_triage(self, validator, sample_metadata):
        """Test no approval when not explicitly requested in triage result."""
    pass
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = {"require_approval": False}
        
        requires_approval = await validator.check_approval_requirements(request, state)
        assert requires_approval is False

    @pytest.mark.asyncio
    async def test_large_update_operation_requires_approval(self, validator, sample_metadata):
        """Test that large UPDATE operations require approval."""
        update_request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata,
            filters={"document_type": "all", "status": "published"}  # Has filters
        )
        
        state = DeepAgentState()
        state.triage_result = {}
        
        requires_approval = await validator.check_approval_requirements(update_request, state)
        assert requires_approval is True

    @pytest.mark.asyncio
    async def test_small_update_operation_no_approval(self, validator, sample_metadata):
        """Test that small UPDATE operations don't require approval."""
    pass
        update_request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata
            # No filters - considered small update
        )
        
        state = DeepAgentState()
        state.triage_result = {}
        
        requires_approval = await validator.check_approval_requirements(update_request, state)
        assert requires_approval is False

    @pytest.mark.asyncio
    async def test_empty_triage_result(self, validator, sample_metadata):
        """Test approval checking with empty triage result."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = None
        
        requires_approval = await validator.check_approval_requirements(request, state)
        assert requires_approval is False

    @pytest.mark.asyncio
    async def test_non_dict_triage_result(self, validator, sample_metadata):
        """Test approval checking with non-dict triage result."""
    pass
        request = CorpusOperationRequest(
            operation=CorpusOperation.VALIDATE,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = "not_a_dict"
        
        requires_approval = await validator.check_approval_requirements(request, state)
        assert requires_approval is False

    @pytest.mark.parametrize("operation", [
        CorpusOperation.CREATE,
        CorpusOperation.SEARCH,
        CorpusOperation.ANALYZE,
        CorpusOperation.INDEX,
        CorpusOperation.VALIDATE,
    ])
    @pytest.mark.asyncio
    async def test_all_non_delete_operations(self, validator, sample_metadata, operation):
        """Test that all non-DELETE operations behave consistently."""
        request = CorpusOperationRequest(
            operation=operation,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = {}
        
        requires_approval = await validator.check_approval_requirements(request, state)
        assert requires_approval is False


class TestApprovalMessageGeneration:
    """Test approval message generation."""
    pass

    @pytest.fixture
    def validator(self):
    """Use real service instance."""
    # TODO: Initialize real service
        await asyncio.sleep(0)
    return CorpusApprovalValidator()

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusMetadata(
            corpus_name="message_test_corpus",
            corpus_type=CorpusType.KNOWLEDGE_BASE,
            description="Test corpus for message generation",
            access_level="public"
        )

    def test_basic_approval_message_structure(self, validator, sample_metadata):
        """Test basic approval message structure."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        message = validator.generate_approval_message(request)
        
        assert "📚 Corpus Administration Request" in message
        assert "Operation:" in message
        assert "DELETE" in message.upper()
        assert "Corpus:" in message
        assert "message_test_corpus" in message
        assert "Type:" in message
        assert "Knowledge Base" in message
        assert "Access Level:" in message
        assert "public" in message
        assert "Do you approve this operation?" in message

    def test_delete_operation_warning(self, validator, sample_metadata):
        """Test that DELETE operations include warning message."""
    pass
        delete_request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        message = validator.generate_approval_message(delete_request)
        
        assert "⚠️" in message
        assert "Warning" in message
        assert "cannot be undone" in message

    def test_non_delete_operation_no_warning(self, validator, sample_metadata):
        """Test that non-DELETE operations don't include warning."""
        update_request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata
        )
        
        message = validator.generate_approval_message(update_request)
        
        assert "⚠️" not in message
        assert "cannot be undone" not in message

    def test_operation_descriptions(self, validator, sample_metadata):
        """Test operation descriptions in messages."""
    pass
        operation_tests = [
            (CorpusOperation.CREATE, "create a new corpus"),
            (CorpusOperation.UPDATE, "update existing corpus entries"),
            (CorpusOperation.DELETE, "delete corpus data"),
            (CorpusOperation.EXPORT, "export corpus data"),
            (CorpusOperation.IMPORT, "import new data into corpus"),
            (CorpusOperation.VALIDATE, "validate corpus integrity"),
        ]
        
        for operation, expected_description in operation_tests:
            request = CorpusOperationRequest(
                operation=operation,
                corpus_metadata=sample_metadata
            )
            
            message = validator.generate_approval_message(request)
            assert expected_description in message

    def test_search_operation_fallback(self, validator, sample_metadata):
        """Test SEARCH operation uses fallback description."""
        search_request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=sample_metadata
        )
        
        message = validator.generate_approval_message(search_request)
        
        # SEARCH is not in operation descriptions, so it uses fallback
        assert "perform operation on" in message

    def test_approval_message_with_filters(self, validator, sample_metadata):
        """Test approval message includes filter information."""
    pass
        filters = {
            "document_type": "technical",
            "status": "published",
            "date_range": "2024-01-01 to 2024-12-31"
        }
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata,
            filters=filters
        )
        
        message = validator.generate_approval_message(request)
        
        assert "Filters Applied:" in message
        assert "document_type: technical" in message
        assert "status: published" in message
        assert "date_range: 2024-01-01 to 2024-12-31" in message

    def test_approval_message_without_filters(self, validator, sample_metadata):
        """Test approval message without filters."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata,
            filters={}
        )
        
        message = validator.generate_approval_message(request)
        
        assert "Filters Applied:" not in message

    def test_approval_prompt_text(self, validator, sample_metadata):
        """Test approval prompt text is present."""
    pass
        request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        message = validator.generate_approval_message(request)
        
        assert "Reply with 'approve' to proceed" in message
        assert "or 'cancel' to abort" in message

    def test_corpus_type_formatting(self, validator):
        """Test corpus type formatting in messages."""
        type_tests = [
            (CorpusType.KNOWLEDGE_BASE, "Knowledge Base"),
            (CorpusType.TRAINING_DATA, "Training Data"),
            (CorpusType.REFERENCE_DATA, "Reference Data"),
            (CorpusType.DOCUMENTATION, "Documentation"),
            (CorpusType.EMBEDDINGS, "Embeddings"),
        ]
        
        for corpus_type, expected_display in type_tests:
            metadata = CorpusMetadata(
                corpus_name="type_test",
                corpus_type=corpus_type,
                access_level="private"
            )
            
            request = CorpusOperationRequest(
                operation=CorpusOperation.DELETE,
                corpus_metadata=metadata
            )
            
            message = validator.generate_approval_message(request)
            assert expected_display in message

    def test_multiple_filters_formatting(self, validator, sample_metadata):
        """Test multiple filters are properly formatted."""
    pass
        filters = {
            "category": "api_docs",
            "language": "english",
            "priority": "high",
            "tags": ["public", "v2"],
            "size_mb": {"min": 1, "max": 100}
        }
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata,
            filters=filters
        )
        
        message = validator.generate_approval_message(request)
        
        # Check all filter keys are present
        for key in filters.keys():
            assert f"{key}:" in message
        
        # Check filter values are present
        assert "api_docs" in message
        assert "english" in message
        assert "high" in message


class TestPrivateMethods:
    """Test private/helper methods."""
    pass

    @pytest.fixture
    def validator(self):
    """Use real service instance."""
    # TODO: Initialize real service
        return CorpusApprovalValidator()

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusMetadata(
            corpus_name="private_test",
            corpus_type=CorpusType.EMBEDDINGS,
            access_level="restricted"
        )

    def test_is_delete_operation(self, validator, sample_metadata):
        """Test delete operation detection."""
        delete_request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        assert validator._is_delete_operation(delete_request) is True
        
        # Test non-delete operations
        for operation in [CorpusOperation.CREATE, CorpusOperation.UPDATE, CorpusOperation.SEARCH]:
            request = CorpusOperationRequest(
                operation=operation,
                corpus_metadata=sample_metadata
            )
            assert validator._is_delete_operation(request) is False

    def test_has_explicit_approval_request(self, validator):
        """Test explicit approval request detection."""
    pass
        # Test with explicit approval
        state = DeepAgentState()
        state.triage_result = {"require_approval": True}
        assert validator._has_explicit_approval_request(state) is True
        
        # Test without explicit approval
        state.triage_result = {"require_approval": False}
        assert validator._has_explicit_approval_request(state) is False
        
        # Test with missing key (returns None which is falsy)
        state.triage_result = {"other_key": "value"}
        assert not validator._has_explicit_approval_request(state)
        
        # Test with None triage result
        state.triage_result = None
        assert not validator._has_explicit_approval_request(state)
        
        # Test with non-dict triage result
        state.triage_result = "not a dict"
        assert validator._has_explicit_approval_request(state) is False

    def test_is_large_update_operation(self, validator, sample_metadata):
        """Test large update operation detection."""
        # Test UPDATE with filters (large)
        large_update = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata,
            filters={"type": "all"}
        )
        assert validator._is_large_update_operation(large_update) is True
        
        # Test UPDATE without filters (small)
        small_update = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=sample_metadata,
            filters={}
        )
        assert validator._is_large_update_operation(small_update) is False
        
        # Test non-UPDATE operations
        for operation in [CorpusOperation.CREATE, CorpusOperation.DELETE, CorpusOperation.SEARCH]:
            request = CorpusOperationRequest(
                operation=operation,
                corpus_metadata=sample_metadata,
                filters={"some": "filter"}
            )
            assert validator._is_large_update_operation(request) is False

    def test_get_operation_descriptions(self, validator):
        """Test operation descriptions dictionary."""
    pass
        descriptions = validator._get_operation_descriptions()
        
        assert isinstance(descriptions, dict)
        assert len(descriptions) == 6  # Should cover 6 operations
        
        # Test specific descriptions
        assert descriptions[CorpusOperation.CREATE] == "create a new corpus"
        assert descriptions[CorpusOperation.UPDATE] == "update existing corpus entries"
        assert descriptions[CorpusOperation.DELETE] == "delete corpus data"
        assert descriptions[CorpusOperation.EXPORT] == "export corpus data"
        assert descriptions[CorpusOperation.IMPORT] == "import new data into corpus"
        assert descriptions[CorpusOperation.VALIDATE] == "validate corpus integrity"
        
        # SEARCH and ANALYZE should not be in descriptions (fallback to generic)
        assert CorpusOperation.SEARCH not in descriptions
        assert CorpusOperation.ANALYZE not in descriptions

    def test_build_filters_section(self, validator):
        """Test filters section building."""
        filters = {
            "category": "technical",
            "priority": "high",
            "tags": ["api", "docs"]
        }
        
        filters_section = validator._build_filters_section(filters)
        
        assert "**Filters Applied:**" in filters_section
        assert "- category: technical" in filters_section
        assert "- priority: high" in filters_section
        assert "- tags: ['api', 'docs']" in filters_section

    def test_get_approval_prompt(self, validator):
        """Test approval prompt text."""
    pass
        prompt = validator._get_approval_prompt()
        
        assert "**Do you approve this operation?**" in prompt
        assert "Reply with 'approve' to proceed" in prompt
        assert "or 'cancel' to abort" in prompt


class TestValidateApprovalRequired:
    """Test the validate_approval_required method."""
    pass

    @pytest.fixture
    def validator(self):
    """Use real service instance."""
    # TODO: Initialize real service
        return CorpusApprovalValidator()

    @pytest.fixture
    def sample_metadata(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        return CorpusMetadata(
            corpus_name="validate_test",
            corpus_type=CorpusType.TRAINING_DATA,
            access_level="private"
        )

    @pytest.mark.asyncio
    async def test_validate_approval_required_delegates_to_check(self, validator, sample_metadata):
        """Test that validate_approval_required delegates to check_approval_requirements."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = {}
        
        # This should delegate to check_approval_requirements
        result = await validator.validate_approval_required(
            request, state, "test_run_123", True
        )
        
        # DELETE operations should require approval
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_approval_required_with_stream_updates(self, validator, sample_metadata):
        """Test validate_approval_required with streaming updates."""
    pass
        request = CorpusOperationRequest(
            operation=CorpusOperation.CREATE,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.triage_result = {"require_approval": True}
        
        # Test with stream_updates=True
        result = await validator.validate_approval_required(
            request, state, "stream_run_456", True
        )
        assert result is True
        
        # Test with stream_updates=False
        result = await validator.validate_approval_required(
            request, state, "no_stream_run_789", False
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_approval_required_parameters(self, validator, sample_metadata):
        """Test that all parameters are properly handled."""
        request = CorpusOperationRequest(
            operation=CorpusOperation.SEARCH,
            corpus_metadata=sample_metadata
        )
        
        state = DeepAgentState()
        state.user_id = "param_test_user"
        state.chat_thread_id = "param_test_thread"
        state.triage_result = {}
        
        # The method should handle all parameters without error
        result = await validator.validate_approval_required(
            request, state, "param_test_run", False
        )
        
        # SEARCH without special conditions should not require approval
        assert result is False


class TestEdgeCases:
    """Test edge cases and error conditions."""
    pass

    @pytest.fixture
    def validator(self):
    """Use real service instance."""
    # TODO: Initialize real service
        await asyncio.sleep(0)
    return CorpusApprovalValidator()

    @pytest.mark.asyncio
    async def test_malformed_state_objects(self, validator):
        """Test handling of malformed state objects."""
    pass
        metadata = CorpusMetadata(
            corpus_name="malformed_test",
            corpus_type=CorpusType.DOCUMENTATION
        )
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.UPDATE,
            corpus_metadata=metadata
        )
        
        # Test with state that has no attributes
        empty_state = DeepAgentState()
        result = await validator.check_approval_requirements(request, empty_state)
        assert isinstance(result, bool)

    def test_extreme_filter_values(self, validator):
        """Test handling of extreme filter values."""
        metadata = CorpusMetadata(
            corpus_name="extreme_test",
            corpus_type=CorpusType.REFERENCE_DATA
        )
        
        extreme_filters = {
            "very_long_key_name_that_might_cause_issues": "value",
            "": "empty_key",
            "unicode_key_🔥": "unicode_value_🚀",
            "nested": {"deeply": {"nested": {"value": "test"}}},
            "large_number": 999999999999999999,
            "boolean": True,
            "null_value": None
        }
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=metadata,
            filters=extreme_filters
        )
        
        # Should not raise exception
        message = validator.generate_approval_message(request)
        assert isinstance(message, str)
        assert len(message) > 0

    @pytest.mark.asyncio
    async def test_concurrent_validation_calls(self, validator):
        """Test that validator handles concurrent calls properly."""
    pass
        metadata = CorpusMetadata(
            corpus_name="concurrent_test",
            corpus_type=CorpusType.KNOWLEDGE_BASE
        )
        
        request = CorpusOperationRequest(
            operation=CorpusOperation.DELETE,
            corpus_metadata=metadata
        )
        
        state = DeepAgentState()
        state.triage_result = {}
        
        # Make multiple concurrent calls
        import asyncio
        tasks = [
            validator.check_approval_requirements(request, state)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All results should be consistent
        assert all(result is True for result in results)  # DELETE requires approval


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])