import sys
import os

# Add the site-packages directory to the Python path
site_packages = r"C:\Users\antho\miniconda3\Lib\site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic_to_typescript import generate_typescript_defs
from app import schemas

def main():
    """Generate TypeScript definitions from Pydantic schemas."""
    ts_defs = generate_typescript_defs(
        ["app.schemas"],
        [schemas.WebSocketMessage, schemas.SubAgentState, schemas.ToolResult, schemas.ToolInput, schemas.Todo, schemas.DeepAgentState, schemas.User, schemas.Token, schemas.AnalysisRequest, schemas.WebSocketError, schemas.StreamEvent, schemas.RunComplete, schemas.SubAgentUpdate, schemas.AgentStarted, schemas.AgentCompleted, schemas.AgentErrorMessage, schemas.ReferenceItem, schemas.ReferenceGetResponse, schemas.ReferenceCreateRequest, schemas.ReferenceUpdateRequest, schemas.Corpus, schemas.CorpusCreate, schemas.CorpusUpdate, schemas.ContentCorpusGenParams, schemas.LogGenParams, schemas.SyntheticDataGenParams, schemas.DataIngestionParams, schemas.ContentCorpus, schemas.AnalysisResult, schemas.LogEntry, schemas.ConfigForm, schemas.AgentState, schemas.ToolStatus, schemas.ToolInvocation, schemas.SubAgentLifecycle, schemas.GoogleUser, schemas.UserBase, schemas.UserCreate, schemas.UserUpdate, schemas.UserInDBBase, schemas.UserInDB, schemas.TokenPayload, schemas.LogTableSettings, schemas.TimePeriodSettings, schemas.DefaultLogTableSettings, schemas.Settings, schemas.DataSource, schemas.TimeRange, schemas.Workload, schemas.RequestModel, schemas.StartAgentPayload, schemas.StartAgentMessage, schemas.SupplyOptionBase, schemas.SupplyOptionCreate, schemas.SupplyOptionUpdate, schemas.SupplyOptionInDBBase, schemas.SupplyOption, schemas.ContentGenParams, schemas.LinguisticFeatures, schemas.SLOProfile, schemas.RiskProfile, schemas.WorkloadProfile, schemas.CostModel, schemas.TechnicalSpecs, schemas.PerformanceDistribution, schemas.LatencyDistributions, schemas.SafetyAndQualityProfile, schemas.TokenizerProfile, schemas.SupplyRecord, schemas.ParetoSolution, schemas.Policy, schemas.CanaryHealthCheckResult, schemas.Log, schemas.CorpusBase, schemas.CorpusInDBBase, schemas.SecretReference, schemas.GoogleCloudConfig, schemas.OAuthConfig, schemas.DevUser, schemas.DevLoginRequest, schemas.AuthEndpoints, schemas.AuthConfigResponse, schemas.ClickHouseNativeConfig, schemas.ClickHouseHTTPSConfig, schemas.ClickHouseHTTPSDevConfig, schemas.ClickHouseLoggingConfig, schemas.LangfuseConfig, schemas.LLMConfig, schemas.AppConfig, schemas.DevelopmentConfig, schemas.ProductionConfig, schemas.TestingConfig, schemas.ToolConfig, schemas.ClickHouseCredentials, schemas.ModelIdentifier, schemas.EventMetadata, schemas.TraceContext, schemas.Request, schemas.Response, schemas.Performance, schemas.FinOps, schemas.EnrichedMetrics, schemas.UnifiedLogEntry, schemas.DiscoveredPattern, schemas.PredictedOutcome, schemas.BaselineMetrics, schemas.LearnedPolicy, schemas.CostComparison, schemas.AnalysisResult, schemas.LogEntry, schemas.AdditionalTable, schemas.ConfigForm, schemas.AgentState, schemas.ToolStatus, schemas.ToolInput, schemas.ToolResult, schemas.ToolInvocation, schemas.DeepAgentState, schemas.Todo, schemas.SubAgentState, schemas.SubAgentLifecycle, schemas.Message, schemas.MessageType, schemas.UserMessage, schemas.AgentMessage, schemas.ToolStarted, schemas.ToolCompleted, schemas.StopAgent, schemas.StreamEvent, schemas.RunComplete, schemas.SubAgentUpdate, schemas.AgentStarted, schemas.AgentCompleted, schemas.AgentErrorMessage, schemas.WebSocketError, schemas.AnalysisRequest, schemas.WebSocketMessage]
    )
    with open("frontend/app/types/index.ts", "w") as f:
        f.write(ts_defs)


if __name__ == "__main__":
    main()