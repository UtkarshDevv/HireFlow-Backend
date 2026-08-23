"""Entry point — run with: python run.py"""
import os
import uvicorn
from app.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.app_port))
    host = os.environ.get("HOST", "0.0.0.0")
    is_dev = os.environ.get("ENVIRONMENT", "development").lower() == "development"
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=is_dev,
    )
