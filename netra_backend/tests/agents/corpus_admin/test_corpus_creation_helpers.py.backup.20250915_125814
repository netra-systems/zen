"""
Unit tests for corpus_creation_helpers
Coverage Target: 90%
Business Value: Revenue-critical component
"""

import pytest
from unittest.mock import patch
from netra_backend.app.agents.corpus_admin.corpus_creation_helpers import get_handlers


class TestCorpusCreationHelpers:
    """Test suite for corpus creation helpers"""

    def test_get_handlers_with_available_handlers(self):
        """Test get_handlers when handlers are available"""
        with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.HANDLERS_AVAILABLE', True):
            with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.create_validation_handler') as mock_val:
                with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.create_indexing_handler') as mock_idx:
                    with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.create_upload_handler') as mock_upl:
                        # Create mock handler instances
                        mock_validation_handler = {"type": "validation", "status": "active"}
                        mock_indexing_handler = {"type": "indexing", "status": "active"}
                        mock_upload_handler = {"type": "upload", "status": "active"}
                        
                        mock_val.return_value = mock_validation_handler
                        mock_idx.return_value = mock_indexing_handler
                        mock_upl.return_value = mock_upload_handler

                        v, i, u = get_handlers()

                        assert v is not None
                        assert i is not None
                        assert u is not None
                        assert v == mock_validation_handler
                        assert i == mock_indexing_handler
                        assert u == mock_upload_handler
                        mock_val.assert_called_once()
                        mock_idx.assert_called_once()
                        mock_upl.assert_called_once()

    def test_get_handlers_without_available_handlers(self):
        """Test get_handlers when handlers are not available"""
        with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.HANDLERS_AVAILABLE', False):
            v, i, u = get_handlers()

            assert v is None
            assert i is None
            assert u is None

    def test_get_handlers_default_behavior(self):
        """Test get_handlers with default configuration (handlers not available)"""
        # Test the actual default behavior without mocking HANDLERS_AVAILABLE
        v, i, u = get_handlers()
        
        assert v is None
        assert i is None
        assert u is None
