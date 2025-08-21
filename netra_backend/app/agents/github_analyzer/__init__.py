"""GitHub Code Analysis Service Package.

Analyzes GitHub repositories to map AI/LLM operations and configurations.
"""

# FIXME: GitHubAnalyzerService not available
# from netra_backend.app.agents.corpus_admin.agent import GitHubAnalyzerService
from netra_backend.app.agents.github_analyzer.scanner_core import RepositoryScanner
from netra_backend.app.agents.github_analyzer.pattern_detector import AIPatternDetector
from netra_backend.app.agents.github_analyzer.config_parser import ConfigurationExtractor
from netra_backend.app.agents.github_analyzer.llm_mapper import LLMCallMapper
from netra_backend.app.agents.github_analyzer.tool_analyzer import ToolUsageAnalyzer
from netra_backend.app.agents.github_analyzer.output_formatter import AIOperationsMapFormatter
from netra_backend.app.agents.github_analyzer.github_client import GitHubAPIClient

__all__ = [
    "GitHubAnalyzerService",
    "RepositoryScanner",
    "AIPatternDetector",
    "ConfigurationExtractor",
    "LLMCallMapper",
    "ToolUsageAnalyzer",
    "AIOperationsMapFormatter",
    "GitHubAPIClient"
]