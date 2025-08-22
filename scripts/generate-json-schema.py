import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from netra_backend.app import schemas


def main():
    models = {
        "User": schemas.User.model_json_schema(),
        "WebSocketMessage": schemas.WebSocketMessage.model_json_schema(),
        "AnalysisRequest": schemas.AnalysisRequest.model_json_schema(),
        "WebSocketError": schemas.WebSocketError.model_json_schema(),
        "RequestModel": schemas.RequestModel.model_json_schema(),
        "StartAgentMessage": schemas.StartAgentMessage.model_json_schema(),
        "StartAgentPayload": schemas.StartAgentPayload.model_json_schema(),
        "Workload": schemas.Workload.model_json_schema(),
        "DataSource": schemas.DataSource.model_json_schema(),
        "TimeRange": schemas.TimeRange.model_json_schema(),
        "Settings": schemas.Settings.model_json_schema(),
    }
    with open(f"shared/schemas.json", "w") as f:
        f.write(json.dumps(models, indent=2))


if __name__ == "__main__":
    main()