import uvicorn
import argparse
import socket
import json
import os
from pathlib import Path

def get_free_port():
    """Get a free port by binding to port 0."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def write_service_discovery(port: int, host: str = "localhost"):
    """Write service discovery info for frontend."""
    discovery_dir = Path(".netra")
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
    parser = argparse.ArgumentParser(description='Run the Netra AI server')
    parser.add_argument('--no-reload', action='store_true', 
                        help='Run server without auto-reload (useful for testing)')
    parser.add_argument('--port', type=int, default=None,
                        help='Port to run the server on (default: 8000 or auto-detect)')
    parser.add_argument('--dynamic-port', action='store_true',
                        help='Automatically find and use a free port')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind the server to (default: 0.0.0.0)')
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
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=port,
        reload=not args.no_reload,
        lifespan="on"
    )