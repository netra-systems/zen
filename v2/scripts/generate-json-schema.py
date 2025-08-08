
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app import schemas


def main():
    models = [
        schemas.User,
        schemas.WebSocketMessage,
    ]
    for model in models:
        with open(f"shared/{model.__name__}.json", "w") as f:
            f.write(json.dumps(model.model_json_schema(), indent=2))


if __name__ == "__main__":
    main()
