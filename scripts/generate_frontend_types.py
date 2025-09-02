import os
import sys
from shared.isolated_environment import get_env

# Change CWD to project root directory
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_path)
# Add project path to the beginning of sys.path
if project_path not in sys.path:
    sys.path.insert(0, project_path)

print(f"sys.executable: {sys.executable}")
print(f"sys.path: {sys.path}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")

# Add the site-packages directory to the Python path
site_packages = r"C:\Users\antho\miniconda3\Lib\site-packages"
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

try:
    from pydantic2ts import generate_typescript_defs
except Exception as e:
    print(e)
    sys.exit(1)

def main():
    """Generate TypeScript definitions from Pydantic schemas."""
    generate_typescript_defs(
        "app.schemas",
        "frontend/types/backend_schema_auto_generated.ts"
    )


if __name__ == "__main__":
    main()
