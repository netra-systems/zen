import sys
import os

# Change CWD to v2 directory
v2_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(v2_path)
# Add v2 path to the beginning of sys.path
if v2_path not in sys.path:
    sys.path.insert(0, v2_path)

print(f"sys.executable: {sys.executable}")
print(f"sys.path: {sys.path}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")

# Add the site-packages directory to the Python path
site_packages = r"C:\Users\antho\miniconda3\Lib\site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

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