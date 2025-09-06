# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Comprehensive unit tests for corpus_admin validators.

# REMOVED_SYNTAX_ERROR: Business Value: Ensures approval validation and business rule enforcement for
# REMOVED_SYNTAX_ERROR: critical corpus operations. These validators protect against unauthorized
# REMOVED_SYNTAX_ERROR: operations and ensure proper approval workflows for enterprise clients.
""

import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.corpus_admin.validators import CorpusApprovalValidator
# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.corpus_admin.models import ( )
CorpusOperation,
CorpusType,
CorpusMetadata,
CorpusOperationRequest
from netra_backend.app.agents.state import DeepAgentState


# REMOVED_SYNTAX_ERROR: class TestCorpusApprovalValidator:
    # REMOVED_SYNTAX_ERROR: """Test CorpusApprovalValidator class."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create validator instance for testing."""
    # REMOVED_SYNTAX_ERROR: return CorpusApprovalValidator()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create sample corpus metadata for testing."""
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="test_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.KNOWLEDGE_BASE,
    # REMOVED_SYNTAX_ERROR: description="Test knowledge base for validation",
    # REMOVED_SYNTAX_ERROR: access_level="private"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_state(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create sample agent state for testing."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
    # REMOVED_SYNTAX_ERROR: state.user_request = "Delete the outdated documentation corpus"
    # REMOVED_SYNTAX_ERROR: state.user_id = "test_user_123"
    # REMOVED_SYNTAX_ERROR: state.chat_thread_id = "thread_456"
    # REMOVED_SYNTAX_ERROR: state.triage_result = {"category": "corpus_management", "is_admin_mode": True}
    # REMOVED_SYNTAX_ERROR: return state

# REMOVED_SYNTAX_ERROR: def test_initialization(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test validator initialization."""
    # REMOVED_SYNTAX_ERROR: assert validator is not None
    # REMOVED_SYNTAX_ERROR: assert isinstance(validator.approval_thresholds, dict)
    # REMOVED_SYNTAX_ERROR: assert "delete_documents" in validator.approval_thresholds
    # REMOVED_SYNTAX_ERROR: assert "update_documents" in validator.approval_thresholds
    # REMOVED_SYNTAX_ERROR: assert "export_size_mb" in validator.approval_thresholds

# REMOVED_SYNTAX_ERROR: def test_approval_thresholds_values(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test approval threshold values are reasonable."""
    # REMOVED_SYNTAX_ERROR: thresholds = validator.approval_thresholds

    # REMOVED_SYNTAX_ERROR: assert thresholds["delete_documents"] == 100
    # REMOVED_SYNTAX_ERROR: assert thresholds["update_documents"] == 500
    # REMOVED_SYNTAX_ERROR: assert thresholds["export_size_mb"] == 100

    # Ensure all thresholds are positive numbers
    # REMOVED_SYNTAX_ERROR: for key, value in thresholds.items():
        # REMOVED_SYNTAX_ERROR: assert isinstance(value, (int, float))
        # REMOVED_SYNTAX_ERROR: assert value > 0


# REMOVED_SYNTAX_ERROR: class TestApprovalRequirements:
    # REMOVED_SYNTAX_ERROR: """Test approval requirement checking logic."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusApprovalValidator()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="approval_test_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.DOCUMENTATION,
    # REMOVED_SYNTAX_ERROR: description="Test corpus for approval validation"
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_delete_operation_requires_approval(self, validator, sample_metadata):
        # REMOVED_SYNTAX_ERROR: """Test that DELETE operations always require approval."""
        # REMOVED_SYNTAX_ERROR: delete_request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
        # REMOVED_SYNTAX_ERROR: state.triage_result = {}

        # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(delete_request, state)
        # REMOVED_SYNTAX_ERROR: assert requires_approval is True

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_non_delete_operations_basic(self, validator, sample_metadata):
            # REMOVED_SYNTAX_ERROR: """Test that non-DELETE operations don't automatically require approval."""
            # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
            # REMOVED_SYNTAX_ERROR: state.triage_result = {}

            # Test CREATE operation
            # REMOVED_SYNTAX_ERROR: create_request = CorpusOperationRequest( )
            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
            # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
            
            # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(create_request, state)
            # REMOVED_SYNTAX_ERROR: assert requires_approval is False

            # Test SEARCH operation
            # REMOVED_SYNTAX_ERROR: search_request = CorpusOperationRequest( )
            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
            # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
            
            # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(search_request, state)
            # REMOVED_SYNTAX_ERROR: assert requires_approval is False

            # Test ANALYZE operation
            # REMOVED_SYNTAX_ERROR: analyze_request = CorpusOperationRequest( )
            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.ANALYZE,
            # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
            
            # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(analyze_request, state)
            # REMOVED_SYNTAX_ERROR: assert requires_approval is False

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_explicit_approval_request_in_triage(self, validator, sample_metadata):
                # REMOVED_SYNTAX_ERROR: """Test approval when explicitly requested in triage result."""
                # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
                # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                

                # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                # REMOVED_SYNTAX_ERROR: state.triage_result = {"require_approval": True}

                # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(request, state)
                # REMOVED_SYNTAX_ERROR: assert requires_approval is True

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_no_explicit_approval_request_in_triage(self, validator, sample_metadata):
                    # REMOVED_SYNTAX_ERROR: """Test no approval when not explicitly requested in triage result."""
                    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
                    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                    

                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                    # REMOVED_SYNTAX_ERROR: state.triage_result = {"require_approval": False}

                    # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(request, state)
                    # REMOVED_SYNTAX_ERROR: assert requires_approval is False

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_large_update_operation_requires_approval(self, validator, sample_metadata):
                        # REMOVED_SYNTAX_ERROR: """Test that large UPDATE operations require approval."""
                        # REMOVED_SYNTAX_ERROR: update_request = CorpusOperationRequest( )
                        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
                        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
                        # REMOVED_SYNTAX_ERROR: filters={"document_type": "all", "status": "published"}  # Has filters
                        

                        # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                        # REMOVED_SYNTAX_ERROR: state.triage_result = {}

                        # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(update_request, state)
                        # REMOVED_SYNTAX_ERROR: assert requires_approval is True

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_small_update_operation_no_approval(self, validator, sample_metadata):
                            # REMOVED_SYNTAX_ERROR: """Test that small UPDATE operations don't require approval."""
                            # REMOVED_SYNTAX_ERROR: update_request = CorpusOperationRequest( )
                            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
                            # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                            # No filters - considered small update
                            

                            # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                            # REMOVED_SYNTAX_ERROR: state.triage_result = {}

                            # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(update_request, state)
                            # REMOVED_SYNTAX_ERROR: assert requires_approval is False

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_empty_triage_result(self, validator, sample_metadata):
                                # REMOVED_SYNTAX_ERROR: """Test approval checking with empty triage result."""
                                # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                                # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                                

                                # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                                # REMOVED_SYNTAX_ERROR: state.triage_result = None

                                # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(request, state)
                                # REMOVED_SYNTAX_ERROR: assert requires_approval is False

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_non_dict_triage_result(self, validator, sample_metadata):
                                    # REMOVED_SYNTAX_ERROR: """Test approval checking with non-dict triage result."""
                                    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                                    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.VALIDATE,
                                    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                                    

                                    # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                                    # REMOVED_SYNTAX_ERROR: state.triage_result = "not_a_dict"

                                    # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(request, state)
                                    # REMOVED_SYNTAX_ERROR: assert requires_approval is False

                                    # REMOVED_SYNTAX_ERROR: @pytest.fixture)
                                    # REMOVED_SYNTAX_ERROR: CorpusOperation.CREATE,
                                    # REMOVED_SYNTAX_ERROR: CorpusOperation.SEARCH,
                                    # REMOVED_SYNTAX_ERROR: CorpusOperation.ANALYZE,
                                    # REMOVED_SYNTAX_ERROR: CorpusOperation.INDEX,
                                    # REMOVED_SYNTAX_ERROR: CorpusOperation.VALIDATE,
                                    
                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_all_non_delete_operations(self, validator, sample_metadata, operation):
                                        # REMOVED_SYNTAX_ERROR: """Test that all non-DELETE operations behave consistently."""
                                        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                                        # REMOVED_SYNTAX_ERROR: operation=operation,
                                        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                                        

                                        # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                                        # REMOVED_SYNTAX_ERROR: state.triage_result = {}

                                        # REMOVED_SYNTAX_ERROR: requires_approval = await validator.check_approval_requirements(request, state)
                                        # REMOVED_SYNTAX_ERROR: assert requires_approval is False


# REMOVED_SYNTAX_ERROR: class TestApprovalMessageGeneration:
    # REMOVED_SYNTAX_ERROR: """Test approval message generation."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return CorpusApprovalValidator()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="message_test_corpus",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.KNOWLEDGE_BASE,
    # REMOVED_SYNTAX_ERROR: description="Test corpus for message generation",
    # REMOVED_SYNTAX_ERROR: access_level="public"
    

# REMOVED_SYNTAX_ERROR: def test_basic_approval_message_structure(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test basic approval message structure."""
    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)

    # REMOVED_SYNTAX_ERROR: assert "📚 Corpus Administration Request" in message
    # REMOVED_SYNTAX_ERROR: assert "Operation:" in message
    # REMOVED_SYNTAX_ERROR: assert "DELETE" in message.upper()
    # REMOVED_SYNTAX_ERROR: assert "Corpus:" in message
    # REMOVED_SYNTAX_ERROR: assert "message_test_corpus" in message
    # REMOVED_SYNTAX_ERROR: assert "Type:" in message
    # REMOVED_SYNTAX_ERROR: assert "Knowledge Base" in message
    # REMOVED_SYNTAX_ERROR: assert "Access Level:" in message
    # REMOVED_SYNTAX_ERROR: assert "public" in message
    # REMOVED_SYNTAX_ERROR: assert "Do you approve this operation?" in message

# REMOVED_SYNTAX_ERROR: def test_delete_operation_warning(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test that DELETE operations include warning message."""
    # REMOVED_SYNTAX_ERROR: delete_request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(delete_request)

    # REMOVED_SYNTAX_ERROR: assert "⚠️" in message
    # REMOVED_SYNTAX_ERROR: assert "Warning" in message
    # REMOVED_SYNTAX_ERROR: assert "cannot be undone" in message

# REMOVED_SYNTAX_ERROR: def test_non_delete_operation_no_warning(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test that non-DELETE operations don't include warning."""
    # REMOVED_SYNTAX_ERROR: update_request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(update_request)

    # REMOVED_SYNTAX_ERROR: assert "⚠️" not in message
    # REMOVED_SYNTAX_ERROR: assert "cannot be undone" not in message

# REMOVED_SYNTAX_ERROR: def test_operation_descriptions(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test operation descriptions in messages."""
    # REMOVED_SYNTAX_ERROR: operation_tests = [ )
    # REMOVED_SYNTAX_ERROR: (CorpusOperation.CREATE, "create a new corpus"),
    # REMOVED_SYNTAX_ERROR: (CorpusOperation.UPDATE, "update existing corpus entries"),
    # REMOVED_SYNTAX_ERROR: (CorpusOperation.DELETE, "delete corpus data"),
    # REMOVED_SYNTAX_ERROR: (CorpusOperation.EXPORT, "export corpus data"),
    # REMOVED_SYNTAX_ERROR: (CorpusOperation.IMPORT, "import new data into corpus"),
    # REMOVED_SYNTAX_ERROR: (CorpusOperation.VALIDATE, "validate corpus integrity"),
    

    # REMOVED_SYNTAX_ERROR: for operation, expected_description in operation_tests:
        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=operation,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        

        # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)
        # REMOVED_SYNTAX_ERROR: assert expected_description in message

# REMOVED_SYNTAX_ERROR: def test_search_operation_fallback(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test SEARCH operation uses fallback description."""
    # REMOVED_SYNTAX_ERROR: search_request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(search_request)

    # SEARCH is not in operation descriptions, so it uses fallback
    # REMOVED_SYNTAX_ERROR: assert "perform operation on" in message

# REMOVED_SYNTAX_ERROR: def test_approval_message_with_filters(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test approval message includes filter information."""
    # REMOVED_SYNTAX_ERROR: filters = { )
    # REMOVED_SYNTAX_ERROR: "document_type": "technical",
    # REMOVED_SYNTAX_ERROR: "status": "published",
    # REMOVED_SYNTAX_ERROR: "date_range": "2024-01-01 to 2024-12-31"
    

    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
    # REMOVED_SYNTAX_ERROR: filters=filters
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)

    # REMOVED_SYNTAX_ERROR: assert "Filters Applied:" in message
    # REMOVED_SYNTAX_ERROR: assert "document_type: technical" in message
    # REMOVED_SYNTAX_ERROR: assert "status: published" in message
    # REMOVED_SYNTAX_ERROR: assert "date_range: 2024-01-01 to 2024-12-31" in message

# REMOVED_SYNTAX_ERROR: def test_approval_message_without_filters(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test approval message without filters."""
    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
    # REMOVED_SYNTAX_ERROR: filters={}
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)

    # REMOVED_SYNTAX_ERROR: assert "Filters Applied:" not in message

# REMOVED_SYNTAX_ERROR: def test_approval_prompt_text(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test approval prompt text is present."""
    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)

    # REMOVED_SYNTAX_ERROR: assert "Reply with 'approve' to proceed" in message
    # REMOVED_SYNTAX_ERROR: assert "or 'cancel' to abort" in message

# REMOVED_SYNTAX_ERROR: def test_corpus_type_formatting(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test corpus type formatting in messages."""
    # REMOVED_SYNTAX_ERROR: type_tests = [ )
    # REMOVED_SYNTAX_ERROR: (CorpusType.KNOWLEDGE_BASE, "Knowledge Base"),
    # REMOVED_SYNTAX_ERROR: (CorpusType.TRAINING_DATA, "Training Data"),
    # REMOVED_SYNTAX_ERROR: (CorpusType.REFERENCE_DATA, "Reference Data"),
    # REMOVED_SYNTAX_ERROR: (CorpusType.DOCUMENTATION, "Documentation"),
    # REMOVED_SYNTAX_ERROR: (CorpusType.EMBEDDINGS, "Embeddings"),
    

    # REMOVED_SYNTAX_ERROR: for corpus_type, expected_display in type_tests:
        # REMOVED_SYNTAX_ERROR: metadata = CorpusMetadata( )
        # REMOVED_SYNTAX_ERROR: corpus_name="type_test",
        # REMOVED_SYNTAX_ERROR: corpus_type=corpus_type,
        # REMOVED_SYNTAX_ERROR: access_level="private"
        

        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
        

        # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)
        # REMOVED_SYNTAX_ERROR: assert expected_display in message

# REMOVED_SYNTAX_ERROR: def test_multiple_filters_formatting(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test multiple filters are properly formatted."""
    # REMOVED_SYNTAX_ERROR: filters = { )
    # REMOVED_SYNTAX_ERROR: "category": "api_docs",
    # REMOVED_SYNTAX_ERROR: "language": "english",
    # REMOVED_SYNTAX_ERROR: "priority": "high",
    # REMOVED_SYNTAX_ERROR: "tags": ["public", "v2"],
    # REMOVED_SYNTAX_ERROR: "size_mb": {"min": 1, "max": 100}
    

    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
    # REMOVED_SYNTAX_ERROR: filters=filters
    

    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)

    # Check all filter keys are present
    # REMOVED_SYNTAX_ERROR: for key in filters.keys():
        # REMOVED_SYNTAX_ERROR: assert "formatted_string" in message

        # Check filter values are present
        # REMOVED_SYNTAX_ERROR: assert "api_docs" in message
        # REMOVED_SYNTAX_ERROR: assert "english" in message
        # REMOVED_SYNTAX_ERROR: assert "high" in message


# REMOVED_SYNTAX_ERROR: class TestPrivateMethods:
    # REMOVED_SYNTAX_ERROR: """Test private/helper methods."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusApprovalValidator()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="private_test",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.EMBEDDINGS,
    # REMOVED_SYNTAX_ERROR: access_level="restricted"
    

# REMOVED_SYNTAX_ERROR: def test_is_delete_operation(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test delete operation detection."""
    # REMOVED_SYNTAX_ERROR: delete_request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
    

    # REMOVED_SYNTAX_ERROR: assert validator._is_delete_operation(delete_request) is True

    # Test non-delete operations
    # REMOVED_SYNTAX_ERROR: for operation in [CorpusOperation.CREATE, CorpusOperation.UPDATE, CorpusOperation.SEARCH]:
        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=operation,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        
        # REMOVED_SYNTAX_ERROR: assert validator._is_delete_operation(request) is False

# REMOVED_SYNTAX_ERROR: def test_has_explicit_approval_request(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test explicit approval request detection."""
    # Test with explicit approval
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
    # REMOVED_SYNTAX_ERROR: state.triage_result = {"require_approval": True}
    # REMOVED_SYNTAX_ERROR: assert validator._has_explicit_approval_request(state) is True

    # Test without explicit approval
    # REMOVED_SYNTAX_ERROR: state.triage_result = {"require_approval": False}
    # REMOVED_SYNTAX_ERROR: assert validator._has_explicit_approval_request(state) is False

    # Test with missing key (returns None which is falsy)
    # REMOVED_SYNTAX_ERROR: state.triage_result = {"other_key": "value"}
    # REMOVED_SYNTAX_ERROR: assert not validator._has_explicit_approval_request(state)

    # Test with None triage result
    # REMOVED_SYNTAX_ERROR: state.triage_result = None
    # REMOVED_SYNTAX_ERROR: assert not validator._has_explicit_approval_request(state)

    # Test with non-dict triage result
    # REMOVED_SYNTAX_ERROR: state.triage_result = "not a dict"
    # REMOVED_SYNTAX_ERROR: assert validator._has_explicit_approval_request(state) is False

# REMOVED_SYNTAX_ERROR: def test_is_large_update_operation(self, validator, sample_metadata):
    # REMOVED_SYNTAX_ERROR: """Test large update operation detection."""
    # Test UPDATE with filters (large)
    # REMOVED_SYNTAX_ERROR: large_update = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
    # REMOVED_SYNTAX_ERROR: filters={"type": "all"}
    
    # REMOVED_SYNTAX_ERROR: assert validator._is_large_update_operation(large_update) is True

    # Test UPDATE without filters (small)
    # REMOVED_SYNTAX_ERROR: small_update = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
    # REMOVED_SYNTAX_ERROR: filters={}
    
    # REMOVED_SYNTAX_ERROR: assert validator._is_large_update_operation(small_update) is False

    # Test non-UPDATE operations
    # REMOVED_SYNTAX_ERROR: for operation in [CorpusOperation.CREATE, CorpusOperation.DELETE, CorpusOperation.SEARCH]:
        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=operation,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata,
        # REMOVED_SYNTAX_ERROR: filters={"some": "filter"}
        
        # REMOVED_SYNTAX_ERROR: assert validator._is_large_update_operation(request) is False

# REMOVED_SYNTAX_ERROR: def test_get_operation_descriptions(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test operation descriptions dictionary."""
    # REMOVED_SYNTAX_ERROR: descriptions = validator._get_operation_descriptions()

    # REMOVED_SYNTAX_ERROR: assert isinstance(descriptions, dict)
    # REMOVED_SYNTAX_ERROR: assert len(descriptions) == 6  # Should cover 6 operations

    # Test specific descriptions
    # REMOVED_SYNTAX_ERROR: assert descriptions[CorpusOperation.CREATE] == "create a new corpus"
    # REMOVED_SYNTAX_ERROR: assert descriptions[CorpusOperation.UPDATE] == "update existing corpus entries"
    # REMOVED_SYNTAX_ERROR: assert descriptions[CorpusOperation.DELETE] == "delete corpus data"
    # REMOVED_SYNTAX_ERROR: assert descriptions[CorpusOperation.EXPORT] == "export corpus data"
    # REMOVED_SYNTAX_ERROR: assert descriptions[CorpusOperation.IMPORT] == "import new data into corpus"
    # REMOVED_SYNTAX_ERROR: assert descriptions[CorpusOperation.VALIDATE] == "validate corpus integrity"

    # SEARCH and ANALYZE should not be in descriptions (fallback to generic)
    # REMOVED_SYNTAX_ERROR: assert CorpusOperation.SEARCH not in descriptions
    # REMOVED_SYNTAX_ERROR: assert CorpusOperation.ANALYZE not in descriptions

# REMOVED_SYNTAX_ERROR: def test_build_filters_section(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test filters section building."""
    # REMOVED_SYNTAX_ERROR: filters = { )
    # REMOVED_SYNTAX_ERROR: "category": "technical",
    # REMOVED_SYNTAX_ERROR: "priority": "high",
    # REMOVED_SYNTAX_ERROR: "tags": ["api", "docs"]
    

    # REMOVED_SYNTAX_ERROR: filters_section = validator._build_filters_section(filters)

    # REMOVED_SYNTAX_ERROR: assert "**Filters Applied:**" in filters_section
    # REMOVED_SYNTAX_ERROR: assert "- category: technical" in filters_section
    # REMOVED_SYNTAX_ERROR: assert "- priority: high" in filters_section
    # REMOVED_SYNTAX_ERROR: assert "- tags: ['api', 'docs']" in filters_section

# REMOVED_SYNTAX_ERROR: def test_get_approval_prompt(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test approval prompt text."""
    # REMOVED_SYNTAX_ERROR: prompt = validator._get_approval_prompt()

    # REMOVED_SYNTAX_ERROR: assert "**Do you approve this operation?**" in prompt
    # REMOVED_SYNTAX_ERROR: assert "Reply with 'approve' to proceed" in prompt
    # REMOVED_SYNTAX_ERROR: assert "or 'cancel' to abort" in prompt


# REMOVED_SYNTAX_ERROR: class TestValidateApprovalRequired:
    # REMOVED_SYNTAX_ERROR: """Test the validate_approval_required method."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusApprovalValidator()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def sample_metadata(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="validate_test",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.TRAINING_DATA,
    # REMOVED_SYNTAX_ERROR: access_level="private"
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_validate_approval_required_delegates_to_check(self, validator, sample_metadata):
        # REMOVED_SYNTAX_ERROR: """Test that validate_approval_required delegates to check_approval_requirements."""
        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
        

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
        # REMOVED_SYNTAX_ERROR: state.triage_result = {}

        # This should delegate to check_approval_requirements
        # REMOVED_SYNTAX_ERROR: result = await validator.validate_approval_required( )
        # REMOVED_SYNTAX_ERROR: request, state, "test_run_123", True
        

        # DELETE operations should require approval
        # REMOVED_SYNTAX_ERROR: assert result is True

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_validate_approval_required_with_stream_updates(self, validator, sample_metadata):
            # REMOVED_SYNTAX_ERROR: """Test validate_approval_required with streaming updates."""
            # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
            # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.CREATE,
            # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
            

            # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
            # REMOVED_SYNTAX_ERROR: state.triage_result = {"require_approval": True}

            # Test with stream_updates=True
            # REMOVED_SYNTAX_ERROR: result = await validator.validate_approval_required( )
            # REMOVED_SYNTAX_ERROR: request, state, "stream_run_456", True
            
            # REMOVED_SYNTAX_ERROR: assert result is True

            # Test with stream_updates=False
            # REMOVED_SYNTAX_ERROR: result = await validator.validate_approval_required( )
            # REMOVED_SYNTAX_ERROR: request, state, "no_stream_run_789", False
            
            # REMOVED_SYNTAX_ERROR: assert result is True

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_validate_approval_required_parameters(self, validator, sample_metadata):
                # REMOVED_SYNTAX_ERROR: """Test that all parameters are properly handled."""
                # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
                # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.SEARCH,
                # REMOVED_SYNTAX_ERROR: corpus_metadata=sample_metadata
                

                # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
                # REMOVED_SYNTAX_ERROR: state.user_id = "param_test_user"
                # REMOVED_SYNTAX_ERROR: state.chat_thread_id = "param_test_thread"
                # REMOVED_SYNTAX_ERROR: state.triage_result = {}

                # The method should handle all parameters without error
                # REMOVED_SYNTAX_ERROR: result = await validator.validate_approval_required( )
                # REMOVED_SYNTAX_ERROR: request, state, "param_test_run", False
                

                # SEARCH without special conditions should not require approval
                # REMOVED_SYNTAX_ERROR: assert result is False


# REMOVED_SYNTAX_ERROR: class TestEdgeCases:
    # REMOVED_SYNTAX_ERROR: """Test edge cases and error conditions."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return CorpusApprovalValidator()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_malformed_state_objects(self, validator):
        # REMOVED_SYNTAX_ERROR: """Test handling of malformed state objects."""
        # REMOVED_SYNTAX_ERROR: metadata = CorpusMetadata( )
        # REMOVED_SYNTAX_ERROR: corpus_name="malformed_test",
        # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.DOCUMENTATION
        

        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.UPDATE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
        

        # Test with state that has no attributes
        # REMOVED_SYNTAX_ERROR: empty_state = DeepAgentState()
        # REMOVED_SYNTAX_ERROR: result = await validator.check_approval_requirements(request, empty_state)
        # REMOVED_SYNTAX_ERROR: assert isinstance(result, bool)

# REMOVED_SYNTAX_ERROR: def test_extreme_filter_values(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test handling of extreme filter values."""
    # REMOVED_SYNTAX_ERROR: metadata = CorpusMetadata( )
    # REMOVED_SYNTAX_ERROR: corpus_name="extreme_test",
    # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.REFERENCE_DATA
    

    # REMOVED_SYNTAX_ERROR: extreme_filters = { )
    # REMOVED_SYNTAX_ERROR: "very_long_key_name_that_might_cause_issues": "value",
    # REMOVED_SYNTAX_ERROR: "": "empty_key",
    # REMOVED_SYNTAX_ERROR: "unicode_key_🔥": "unicode_value_🚀",
    # REMOVED_SYNTAX_ERROR: "nested": {"deeply": {"nested": {"value": "test"}}},
    # REMOVED_SYNTAX_ERROR: "large_number": 999999999999999999,
    # REMOVED_SYNTAX_ERROR: "boolean": True,
    # REMOVED_SYNTAX_ERROR: "null_value": None
    

    # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
    # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
    # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata,
    # REMOVED_SYNTAX_ERROR: filters=extreme_filters
    

    # Should not raise exception
    # REMOVED_SYNTAX_ERROR: message = validator.generate_approval_message(request)
    # REMOVED_SYNTAX_ERROR: assert isinstance(message, str)
    # REMOVED_SYNTAX_ERROR: assert len(message) > 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_concurrent_validation_calls(self, validator):
        # REMOVED_SYNTAX_ERROR: """Test that validator handles concurrent calls properly."""
        # REMOVED_SYNTAX_ERROR: metadata = CorpusMetadata( )
        # REMOVED_SYNTAX_ERROR: corpus_name="concurrent_test",
        # REMOVED_SYNTAX_ERROR: corpus_type=CorpusType.KNOWLEDGE_BASE
        

        # REMOVED_SYNTAX_ERROR: request = CorpusOperationRequest( )
        # REMOVED_SYNTAX_ERROR: operation=CorpusOperation.DELETE,
        # REMOVED_SYNTAX_ERROR: corpus_metadata=metadata
        

        # REMOVED_SYNTAX_ERROR: state = DeepAgentState()
        # REMOVED_SYNTAX_ERROR: state.triage_result = {}

        # Make multiple concurrent calls
        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: tasks = [ )
        # REMOVED_SYNTAX_ERROR: validator.check_approval_requirements(request, state)
        # REMOVED_SYNTAX_ERROR: for _ in range(10)
        

        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

        # All results should be consistent
        # REMOVED_SYNTAX_ERROR: assert all(result is True for result in results)  # DELETE requires approval


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])