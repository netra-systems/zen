"""
Unit tests for parsers
Coverage Target: 90%
Business Value: Revenue-critical component
"""

import pytest
from netra_backend.app.agents.corpus_admin.parsers import CorpusRequestParser

class TestCorpusRequestParser:
    """Test suite for CorpusRequestParser"""

    @pytest.fixture
    def instance(self):
        """Create test instance"""
        return CorpusRequestParser()

    def test_initialization(self, instance):
        """Test proper initialization"""
        assert instance is not None
        assert hasattr(instance, 'parse_request')
        assert hasattr(instance, 'extract_corpus_name')
        assert hasattr(instance, 'extract_parameters')
        assert hasattr(instance, 'validate_request')

    def test_parse_request_create(self, instance):
        """Test parsing create request"""
        result = instance.parse_request("create a new corpus")
        assert result['operation'] == 'create'
        assert result['type'] == 'corpus'

    def test_parse_request_update(self, instance):
        """Test parsing update request"""
        result = instance.parse_request("update the corpus")
        assert result['operation'] == 'update'
        assert result['type'] == 'corpus'

    def test_parse_request_delete(self, instance):
        """Test parsing delete request"""
        result = instance.parse_request("delete corpus")
        assert result['operation'] == 'delete'
        assert result['type'] == 'corpus'

    def test_parse_request_search(self, instance):
        """Test parsing search request"""
        result = instance.parse_request("search in corpus")
        assert result['operation'] == 'search'
        assert result['type'] == 'corpus'

    def test_parse_request_unknown(self, instance):
        """Test parsing unknown request"""
        result = instance.parse_request("something random")
        assert result['operation'] == 'unknown'
        assert result['type'] == 'corpus'

    def test_extract_corpus_name_valid(self, instance):
        """Test extracting corpus name when valid"""
        result = instance.extract_corpus_name("create corpus testcorpus")
        assert result == 'testcorpus'

    def test_extract_corpus_name_none(self, instance):
        """Test extracting corpus name when not present"""
        result = instance.extract_corpus_name("create something")
        assert result is None

    def test_extract_parameters(self, instance):
        """Test parameter extraction"""
        request = "create corpus testcorpus"
        result = instance.extract_parameters(request)
        assert result['corpus_name'] == 'testcorpus'
        assert result['user_request'] == request

    def test_validate_request_valid(self, instance):
        """Test request validation with valid request"""
        request = {'operation': 'create', 'type': 'corpus'}
        assert instance.validate_request(request) is True

    def test_validate_request_invalid(self, instance):
        """Test request validation with invalid request"""
        request = {'operation': 'create'}  # Missing 'type'
        assert instance.validate_request(request) is False