"""Unit tests for Reliability Scorer.



Date Created: 2025-01-22

Last Updated: 2025-01-22



Business Value: Ensures source reliability scoring accuracy.

"""



import pytest

from datetime import datetime, timedelta

from shared.isolated_environment import IsolatedEnvironment



from netra_backend.app.tools.reliability_scorer import ReliabilityScorer





@pytest.fixture

def scorer():

    """Create reliability scorer instance."""

    return ReliabilityScorer()





def test_source_scoring_official(scorer):

    """Test scoring for official sources."""

    score = scorer.score_source("official_government_api")

    assert score == 1.0





def test_source_scoring_academic(scorer):

    """Test scoring for academic sources."""

    score = scorer.score_source("academic_research_paper")

    assert score == 0.9





def test_source_scoring_unknown(scorer):

    """Test scoring for unknown sources."""

    score = scorer.score_source("random_website")

    assert score == 0.2





def test_recency_scoring_current(scorer):

    """Test recency scoring for current content."""

    today = datetime.now().strftime("%Y-%m-%d")

    score = scorer.score_recency(today)

    assert score == 1.0





def test_recency_scoring_old(scorer):

    """Test recency scoring for old content."""

    old_date = "2020-01-01"

    score = scorer.score_recency(old_date)

    assert score == 0.2





def test_completeness_scoring_complete(scorer):

    """Test completeness scoring for complete data."""

    result = {

        "title": "Test Title",

        "content": "Test content",

        "url": "https://example.com",

        "date": "2025-01-22",

        "source": "official"

    }

    score = scorer.score_completeness(result)

    assert score == 1.0





def test_completeness_scoring_partial(scorer):

    """Test completeness scoring for partial data."""

    result = {

        "title": "Test Title",

        "content": "Test content"

    }

    score = scorer.score_completeness(result)

    assert score == 0.4  # 2 out of 5 fields





def test_conflict_resolution(scorer):

    """Test conflict resolution scoring."""

    results = [

        {"content": "Claim A is true"},

        {"content": "Claim A is true"},

        {"content": "Claim B is true"}

    ]

    consensus = scorer.score_conflict_resolution(results)

    

    assert len(consensus) > 0

    assert max(consensus.values()) >= 0.66  # 2/3 consensus

