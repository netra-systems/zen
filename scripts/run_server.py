import sys
import os
from pathlib import Path

# Add project root to Python path to ensure app module can be imported
current_file = Path(__file__).resolve()
if current_file.parent.name == 'scripts':
    # We're in the scripts directory, add parent (project root) to path
    project_root = current_file.parent.parent
else:
    # We're in the project root already
    project_root = current_file.parent

# Add to Python path if not already there
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Verify app module can be found
app_dir = project_root / "app"
if not app_dir.exists():
    print(f"ERROR: app directory not found at {app_dir}")
    print(f"Current directory: {Path.cwd()}")
    print(f"Project root: {project_root}")
    sys.exit(1)

# Now import the rest
import uvicorn
import argparse
import socket
import json

def get_free_port():
    """Get a free port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def write_service_discovery(port: int, host: str = "localhost"):
    """Write service discovery info for frontend."""
    # Always write to project root's .netra directory
    discovery_dir = project_root / ".netra"
    discovery_dir.mkdir(exist_ok=True)
    
    discovery_file = discovery_dir / "backend.json"
    discovery_info = {
        "host": host,
        "port": port,
        "api_url": f"http://{host}:{port}",
        "ws_url": f"ws://{host}:{port}/ws",
        "pid": os.getpid()
    }
    
    with open(discovery_file, 'w') as f:
        json.dump(discovery_info, f, indent=2)
    
    print(f"Service discovery info written to {discovery_file}")
    return discovery_file

if __name__ == "__main__":
    # Mark that we're running from dev launcher if backend port is set
    if os.environ.get('BACKEND_PORT'):
        os.environ['DEV_LAUNCHER_ACTIVE'] = 'true'
    
    parser = argparse.ArgumentParser(description='Run the Netra AI server')
    parser.add_argument('--no-reload', action='store_true', 
                        help='Run server without auto-reload (useful for testing)')
    parser.add_argument('--port', type=int, default=None,
                        help='Port to run the server on (default: 8000 or auto-detect)')
    parser.add_argument('--dynamic-port', action='store_true',
                        help='Automatically find and use a free port')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind the server to (default: 0.0.0.0)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show verbose debug output')
    args = parser.parse_args()
    
    # Determine port
    if args.dynamic_port:
        port = get_free_port()
        print(f"Dynamically allocated port: {port}")
    elif args.port:
        port = args.port
    else:
        # Check environment variable first, then default to 8000
        port = int(os.environ.get('BACKEND_PORT', 8000))
    
    # Write service discovery info for frontend
    discovery_host = "localhost" if args.host == "0.0.0.0" else args.host
    write_service_discovery(port, discovery_host)
    
    # Set environment variable for the app to know its port
    os.environ['SERVER_PORT'] = str(port)
    
    print(f"Starting Netra AI server on {args.host}:{port}")
    print(f"API URL: http://{discovery_host}:{port}")
    print(f"WebSocket URL: ws://{discovery_host}:{port}/ws")
    
    if args.verbose:
        print(f"\nDebug Info:")
        print(f"  Project root: {project_root}")
        print(f"  Python path: {sys.path[:3]}")
        print(f"  App directory exists: {(project_root / 'app').exists()}")
        print(f"  Current directory: {Path.cwd()}")
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=port,
        reload=not args.no_reload
    )