import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def should_skip_file(file_path):
    """Check if file should be skipped"""
    skip_dirs = {
        # Version control and IDE
        '.git', '.vscode', '.idea', '.claude',
        # Python cache and build
        '__pycache__', '.pytest_cache', '.coverage', '.tox', '.mypy_cache', 
        '.ruff_cache', 'htmlcov', '.egg-info', 'dist', 'build', 'wheelhouse',
        '.hypothesis', '.benchmarks', '.nox', '.pants.d',
        # Virtual environments
        'venv', 'venv_test', 'env', '.env', 'virtualenv', '.venv', '.virtualenv', 
        'ENV', 'env.bak', 'venv.bak', 'Include', 'Lib', 'Scripts', 'bin', 'lib', 
        'lib64', 'share', 'pyvenv.cfg', 'site-packages', 'conda-meta', 'pkgs', 
        '.conda', 'envs',
        # Node/JavaScript
        'node_modules', 'bower_components', '.next', '.nuxt', 'out', 
        '.nyc_output', '.sass-cache', '.parcel-cache', '.turbo',
        # Database and migrations
        'migrations', 'alembic',
        # Static/media/public
        'static', 'media', 'public',
        # Cache and temp
        'tmp', 'temp', 'cache', 'logs', '.dev_cache', '.dev_launcher_cache',
        'optimized_test_cache',
        # Test outputs
        'test_reports', 'test-results', 'junit', 'allure-results', 'cypress',
        # Documentation and marketing
        'docs', 'marketing_materials', 'technical_content', 
        'business-context', 'architecture_docs',
        'deployment_docs', 'reports', 'plans',
        'agent_communications', 'team_updates',
        # Infrastructure
        'terraform', 'terraform-dev-postgres', 'terraform-gcp', 
        'terraform-github-gemini', 'infrastructure', 'lark',
        # Vendor
        'vendor', 'ccusage', 'act-cli',
        # GitHub
        '.github', '.githooks',
        # Specific project folders
        'Deepthinkxmls', 'APEX', 'shared'
    }
    
    skip_files = {
        'dump_project_files.py', 'project_dump.txt', '.DS_Store', 
        'Thumbs.db', 'desktop.ini', '.gitignore', '.gitattributes',
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'poetry.lock', 'Pipfile.lock', 'composer.lock',
        'act.exe', 'nul', '.coverage', '.coveragerc',
        'terraform.tfstate', 'terraform.tfstate.backup', 'tfplan'
    }
    
    file_path_str = str(file_path)
    path_parts = set(file_path.parts)
    
    # Check directory patterns
    if skip_dirs & path_parts:
        return True
    
    # Check file names
    if file_path.name in skip_files:
        return True
    
    # Skip compiled/cached files by extension
    skip_extensions = {
        # Compiled
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.o', '.a',
        '.class', '.jar', '.war', '.ear', '.whl',
        # Binary/media
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.rar', '.7z', '.bz2', '.xz',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac', '.mkv', '.webm',
        '.db', '.sqlite', '.sqlite3', '.pickle', '.pkl', '.h5', '.hdf5',
        '.bin', '.dat', '.data', '.model', '.weights', '.onnx', '.pb',
        # Logs and temp
        '.log', '.tmp', '.temp', '.bak', '.backup', '.swp', '.swo',
        '.orig', '.rej', '.cache', '.lock',
        # Map files
        '.map', '.min.js', '.min.css',
        # HTML (for test reports)
        '.html'
    }
    
    if file_path.suffix.lower() in skip_extensions:
        return True
    
    # Skip files starting with dot (hidden files)
    if file_path.name.startswith('.') and file_path.name != '.env.example':
        return True
    
    # Skip very large files (>5MB)
    try:
        if file_path.stat().st_size > 5 * 1024 * 1024:
            return True
    except:
        pass
    
    return False

def read_file_content(file_path):
    """Try to read file content with various encodings"""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            return f"[Error reading file: {e}]"
    
    return "[Unable to read file - unsupported encoding or binary file]"

def dump_project_files(root_dir, output_file):
    """Dump all project files into a single output file"""
    root_path = Path(root_dir)
    
    # Statistics tracking
    file_types = defaultdict(int)
    included_files = []
    skipped_types = defaultdict(int)
    total_size = 0
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"Project Files Dump\n")
        out.write(f"Generated: {datetime.now().isoformat()}\n")
        out.write(f"Root Directory: {root_path.absolute()}\n")
        out.write("=" * 80 + "\n\n")
        
        file_count = 0
        skipped_count = 0
        error_count = 0
        
        # First pass: collect statistics
        all_files = []
        for file_path in root_path.rglob('*'):
            if file_path.is_file():
                all_files.append(file_path)
        
        print(f"Found {len(all_files)} total files in project")
        
        # Process files
        for file_path in sorted(all_files):
            ext = file_path.suffix.lower() or '.no_extension'
            
            if should_skip_file(file_path):
                skipped_count += 1
                skipped_types[ext] += 1
                continue
            
            file_types[ext] += 1
            relative_path = file_path.relative_to(root_path)
            included_files.append((relative_path, file_path))
            
            try:
                total_size += file_path.stat().st_size
            except:
                pass
        
        # Write index at the beginning
        out.write("FILE TYPE INDEX\n")
        out.write("-" * 80 + "\n")
        out.write("Included file types:\n")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            out.write(f"  {ext:20s} : {count:5d} files\n")
        
        out.write("\nSkipped file types:\n")
        for ext, count in sorted(skipped_types.items(), key=lambda x: x[1], reverse=True)[:20]:
            out.write(f"  {ext:20s} : {count:5d} files\n")
        
        out.write(f"\nTotal included files: {len(included_files)}\n")
        out.write(f"Total skipped files: {skipped_count}\n")
        out.write(f"Total size of included files: {total_size / (1024*1024):.2f} MB\n")
        out.write("=" * 80 + "\n\n")
        
        # Write file contents
        out.write("FILE CONTENTS\n")
        out.write("=" * 80 + "\n")
        
        for relative_path, file_path in included_files:
            out.write(f"\n{'=' * 80}\n")
            out.write(f"FILE: {relative_path}\n")
            out.write(f"{'=' * 80}\n")
            
            try:
                content = read_file_content(file_path)
                out.write(content)
                if not content.endswith('\n'):
                    out.write('\n')
                file_count += 1
            except Exception as e:
                out.write(f"[Error processing file: {e}]\n")
                error_count += 1
        
        out.write(f"\n{'=' * 80}\n")
        out.write(f"Summary:\n")
        out.write(f"  Files included: {file_count}\n")
        out.write(f"  Files skipped: {skipped_count}\n")
        out.write(f"  Errors: {error_count}\n")
        out.write(f"{'=' * 80}\n")
    
    return file_count, skipped_count, error_count, file_types

if __name__ == "__main__":
    project_root = Path(__file__).parent
    output_file = project_root / "project_dump.txt"
    
    print(f"Starting project dump...")
    print(f"Root directory: {project_root}")
    print(f"Output file: {output_file}")
    
    try:
        file_count, skipped_count, error_count, file_types = dump_project_files(project_root, output_file)
        
        print(f"\nDump completed successfully!")
        print(f"  Files included: {file_count}")
        print(f"  Files skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
        print(f"\nTop included file types:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {ext:15s} : {count:5d} files")
        print(f"\nOutput saved to: {output_file}")
        
        # Show file size
        size = output_file.stat().st_size
        if size > 1024 * 1024:
            print(f"Output file size: {size / (1024 * 1024):.2f} MB")
        else:
            print(f"Output file size: {size / 1024:.2f} KB")
            
    except Exception as e:
        print(f"Error during dump: {e}")
        sys.exit(1)