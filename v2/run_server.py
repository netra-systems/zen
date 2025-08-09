import uvicorn
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Netra AI server')
    parser.add_argument('--no-reload', action='store_true', 
                        help='Run server without auto-reload (useful for testing)')
    args = parser.parse_args()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not args.no_reload,
        lifespan="on"
    )