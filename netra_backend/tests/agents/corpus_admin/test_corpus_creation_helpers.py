"""
Unit tests for corpus_creation_helpers
Coverage Target: 90%
Business Value: Revenue-critical component
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from netra_backend.app.agents.corpus_admin.corpus_creation_helpers import get_handlers

class TestCorpusCreationHelpers:
    """Test suite for corpus creation helpers"""
    
    def test_get_handlers_with_available_handlers(self):
        """Test get_handlers when handlers are available"""
        with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.HANDLERS_AVAILABLE', True):
            with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.create_validation_handler') as mock_val:
                with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.create_indexing_handler') as mock_idx:
                    with patch('netra_backend.app.agents.corpus_admin.corpus_creation_helpers.create_upload_handler') as mock_upl:
                        mock_val.return_value = Mock()
                        mock_idx.return_value = Mock()
                        mock_upl.return_value = Mock()
                        
                        v, i, u = get_handlers()
                        
                        assert v is not None
                        assert i is not None
                        assert u is not None
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
