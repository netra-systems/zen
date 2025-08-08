
import json
from pydantic import BaseModel
from app import schemas


def main():
    models = [
        schemas.User,
        schemas.WebSocketMessage,
    ]
    for model in models:
        with open(f"shared/{model.__name__}.json", "w") as f:
            f.write(model.model_json_schema())


if __name__ == "__main__":
    main()
