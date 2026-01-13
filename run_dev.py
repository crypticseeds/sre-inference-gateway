#!/usr/bin/env python3
"""Development server runner."""

import subprocess
import sys
from pathlib import Path


def main():
    """Run the development server."""
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    
    # Run with uv
    cmd = [
        "uv", "run", "uvicorn", 
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--log-level", "info"
    ]
    
    print("Starting SRE Inference Gateway development server...")
    print(f"Command: {' '.join(cmd)}")
    print("Server will be available at: http://localhost:8000")
    print("API docs available at: http://localhost:8000/docs")
    print("Metrics available at: http://localhost:9090/metrics")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run(cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()