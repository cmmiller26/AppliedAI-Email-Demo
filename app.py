"""
Email Sorting POC - FastAPI Application
Main application entry point
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Email Sorting POC",
    description="Automated email classification using Microsoft Graph and OpenAI",
    version="0.1.0"
)

# In-memory storage (POC only - will be replaced with database in production)
user_tokens = {}  # {user_id: {access_token, refresh_token, expires_at}}
processed_emails = {}  # {internet_message_id: {category, timestamp, confidence}}
last_check_time = None  # Timestamp of last email fetch


@app.get("/health")
async def health_check():
    """
    Health check endpoint - verifies service is running
    
    Returns:
        JSON response with status, version, and timestamp
    """
    logger.info("Health check requested")
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "environment": {
                "client_id_configured": bool(os.getenv("CLIENT_ID")),
                "tenant_id_configured": bool(os.getenv("TENANT_ID")),
                "openai_key_configured": bool(os.getenv("OPENAI_API_KEY")),
                "redirect_uri": os.getenv("REDIRECT_URI", "not set")
            }
        }
    )


@app.on_event("startup")
async def startup_event():
    """
    Run on application startup
    """
    logger.info("=" * 50)
    logger.info("Email Sorting POC Starting Up")
    logger.info("=" * 50)
    logger.info(f"Redirect URI: {os.getenv('REDIRECT_URI', 'NOT SET')}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info("Server ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown
    """
    logger.info("Email Sorting POC shutting down...")
    logger.info(f"Total tokens stored: {len(user_tokens)}")
    logger.info(f"Total emails processed: {len(processed_emails)}")


# For running directly with Python (development only)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )