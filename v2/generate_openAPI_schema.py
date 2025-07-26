import json
import os

# Set an environment variable to indicate that the application is being run
# for schema generation. This must be done *before* importing any application
# modules (like `app.main`) to ensure they are configured correctly.
os.environ["GENERATE_SCHEMA_MODE"] = "1"

# Now that the environment is set up for schema generation, we can import
# the FastAPI app instance. The app's configuration will use dummy values
# instead of trying to connect to a real database.
from app.main import app
from fastapi.openapi.utils import get_openapi


def generate_openapi_schema():
    """
    Generates the OpenAPI schema from the FastAPI application and saves it
    to a JSON file. This function is intended to be run as a standalone script.
    """
    print("Generating OpenAPI schema...")

    # Use FastAPI's utility to create the schema dictionary.
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    # Determine the output path for the schema file. It should be placed
    # in the parent directory of the 'app' folder (i.e., in 'v2/').
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "..", "openapi.json")

    # Write the generated schema to the file.
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
        f.write("\n") # Add a newline at the end of the file

    print(f"Successfully generated OpenAPI schema at: {output_path}")


if __name__ == "__main__":
    generate_openapi_schema()
