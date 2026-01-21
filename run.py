"""
Development server entry point.

Run this script to start the Uvicorn development server:
    python run.py

For production, use:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
