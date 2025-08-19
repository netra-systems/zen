import os
import sys
from pathlib import Path
from datetime import datetime

def should_skip_file(file_path):
    """Check if file should be skipped"""
    skip_patterns = [
        '.git', '__pycache__', '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe',
        'node_modules', 'venv', 'env', '.env', 'dist', 'build', '.egg-info',
        '.pytest_cache', '.coverage', '.tox', '.mypy_cache', '.ruff_cache',
        'htmlcov', '.idea', '.vscode', '.DS_Store', 'Thumbs.db',
        'dump_project_files.py', 'project_dump.txt'
    ]
    
    file_path_str = str(file_path)
    for pattern in skip_patterns:
        if pattern in file_path_str:
            return True
    
    # Skip binary files
    binary_extensions = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.rar', '.7z', '.jar', '.war',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
        '.db', '.sqlite', '.pickle', '.pkl', '.h5', '.hdf5'
    }
    
    if file_path.suffix.lower() in binary_extensions:
        return True
    
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
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"Project Files Dump\n")
        out.write(f"Generated: {datetime.now().isoformat()}\n")
        out.write(f"Root Directory: {root_path.absolute()}\n")
        out.write("=" * 80 + "\n\n")
        
        file_count = 0
        skipped_count = 0
        error_count = 0
        
        for file_path in sorted(root_path.rglob('*')):
            if file_path.is_file():
                if should_skip_file(file_path):
                    skipped_count += 1
                    continue
                
                relative_path = file_path.relative_to(root_path)
                
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
    
    return file_count, skipped_count, error_count

if __name__ == "__main__":
    project_root = Path(__file__).parent
    output_file = project_root / "project_dump.txt"
    
    print(f"Starting project dump...")
    print(f"Root directory: {project_root}")
    print(f"Output file: {output_file}")
    
    try:
        file_count, skipped_count, error_count = dump_project_files(project_root, output_file)
        
        print(f"\nDump completed successfully!")
        print(f"  Files included: {file_count}")
        print(f"  Files skipped: {skipped_count}")
        print(f"  Errors: {error_count}")
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