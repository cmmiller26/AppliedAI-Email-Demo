"""
Email Sorting POC - FastAPI Application
Main application entry point
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from datetime import datetime
import logging
import os
import secrets
import time
from dotenv import load_dotenv
from msal import ConfidentialClientApplication

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

# MSAL Configuration
# Build authority URL for Microsoft Entra ID OAuth
msal_app = ConfidentialClientApplication(
    client_id=os.getenv("CLIENT_ID"),
    client_credential=os.getenv("CLIENT_SECRET"),
    authority=f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}"
)

# OAuth scopes requested from Microsoft Graph API
# For Graph API calls, use short-form scopes
SCOPES = ["Mail.Read", "Mail.ReadWrite"]
# For OAuth authorization, use full URIs without offline_access
# (offline_access is added automatically by MSAL when using ConfidentialClientApplication)
AUTH_SCOPES = ["https://graph.microsoft.com/Mail.Read", "https://graph.microsoft.com/Mail.ReadWrite"]

# In-memory storage (POC only - will be replaced with database in production)
user_tokens = {}  # {user_id: {access_token, refresh_token, expires_at}}
processed_emails = {}  # {internet_message_id: {category, timestamp, confidence}}
last_check_time = None  # Timestamp of last email fetch
auth_state_store = {}  # {state: timestamp} - CSRF protection for OAuth flow


def cleanup_old_states(max_age_seconds: int = 3600):
    """
    Remove old state tokens from auth_state_store to prevent memory bloat.
    States older than max_age_seconds (default 1 hour) are deleted.

    Args:
        max_age_seconds: Maximum age of state tokens in seconds
    """
    current_time = time.time()
    expired_states = [
        state for state, timestamp in auth_state_store.items()
        if current_time - timestamp > max_age_seconds
    ]
    for state in expired_states:
        del auth_state_store[state]

    if expired_states:
        logger.info(f"Cleaned up {len(expired_states)} expired state tokens")


@app.get("/")
async def root():
    """
    Root endpoint - simple dashboard showing authentication status.

    Returns:
        JSON response with authentication status and next steps
    """
    is_authenticated = "demo_user" in user_tokens

    if is_authenticated:
        token_info = user_tokens["demo_user"]
        expires_at = token_info.get("expires_at", 0)
        is_expired = time.time() > expires_at

        return JSONResponse(
            status_code=200,
            content={
                "message": "Authentication successful!",
                "authenticated": True,
                "token_expires_at": datetime.fromtimestamp(expires_at).isoformat() + "Z",
                "token_expired": is_expired,
                "has_refresh_token": token_info.get("refresh_token") is not None,
                "next_steps": [
                    "Use /graph/fetch to fetch emails",
                    "Use /classify to classify an email",
                    "Use /inbox/process-new to process new emails"
                ]
            }
        )
    else:
        return JSONResponse(
            status_code=200,
            content={
                "message": "Welcome to Email Sorting POC",
                "authenticated": False,
                "next_steps": [
                    "Visit /auth/login to authenticate with Microsoft"
                ]
            }
        )


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


@app.get("/auth/login")
async def auth_login():
    """
    Initiates OAuth 2.0 Authorization Code flow with Microsoft Entra ID.

    Generates a random state token for CSRF protection, stores it in memory,
    and redirects the user to Microsoft's sign-in page.

    Returns:
        302 Redirect to Microsoft sign-in page
    """
    try:
        # Clean up old state tokens before creating a new one
        cleanup_old_states()

        # Generate random state token for CSRF protection (32 bytes = 256 bits)
        state = secrets.token_urlsafe(32)

        # Store state with current timestamp for validation in callback
        auth_state_store[state] = time.time()

        logger.info(f"Initiating OAuth login flow (state: {state[:8]}...)")

        # Build authorization URL using MSAL
        auth_url = msal_app.get_authorization_request_url(
            scopes=AUTH_SCOPES,
            state=state,
            redirect_uri=os.getenv("REDIRECT_URI")
        )

        logger.info(f"Redirecting to Microsoft sign-in page")

        # Redirect user to Microsoft sign-in page
        return RedirectResponse(url=auth_url, status_code=302)

    except Exception as e:
        logger.error(f"Error initiating OAuth login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate login: {str(e)}"
        )


@app.get("/auth/callback")
async def auth_callback(
    code: str = Query(None, description="Authorization code from Microsoft"),
    state: str = Query(None, description="CSRF protection token"),
    error: str = Query(None, description="Error code if authorization failed"),
    error_description: str = Query(None, description="Human-readable error description")
):
    """
    OAuth callback endpoint - handles redirect from Microsoft after user authentication.

    Validates the state token (CSRF check), exchanges the authorization code for
    access and refresh tokens, and stores them in memory.

    Args:
        code: Authorization code from Microsoft (required for success)
        state: CSRF protection token (required)
        error: Error code if authorization failed (optional)
        error_description: Human-readable error description (optional)

    Returns:
        302 Redirect to dashboard (/) on success
        400 Bad Request on validation failure
        500 Internal Server Error on token exchange failure
    """
    try:
        # Handle Microsoft error responses first
        if error:
            logger.error(f"OAuth error from Microsoft: {error} - {error_description}")
            raise HTTPException(
                status_code=400,
                detail=f"Authentication failed: {error_description or error}"
            )

        # Validate required parameters
        if not state:
            logger.warning("Callback received without state parameter")
            raise HTTPException(
                status_code=400,
                detail="Missing state parameter"
            )

        if not code:
            logger.warning("Callback received without authorization code")
            raise HTTPException(
                status_code=400,
                detail="Missing authorization code"
            )

        # Validate state token (CSRF protection)
        if state not in auth_state_store:
            logger.warning(f"Invalid or expired state token received: {state[:8]}...")
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired state token. Please try logging in again."
            )

        # Remove used state token (one-time use)
        del auth_state_store[state]
        logger.info(f"State validated successfully: {state[:8]}...")

        # Exchange authorization code for access token
        logger.info("Exchanging authorization code for access token")
        token_response = msal_app.acquire_token_by_authorization_code(
            code=code,
            scopes=AUTH_SCOPES,
            redirect_uri=os.getenv("REDIRECT_URI")
        )

        # Check if token exchange was successful
        if "error" in token_response:
            error_msg = token_response.get("error_description", token_response.get("error"))
            logger.error(f"Token exchange failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Token exchange failed: {error_msg}"
            )

        # Extract tokens from response
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")  # May be None if offline_access not granted
        expires_in = token_response.get("expires_in", 3600)  # Default 1 hour if not provided

        if not access_token:
            logger.error("No access token in response")
            raise HTTPException(
                status_code=500,
                detail="No access token received from Microsoft"
            )

        # Calculate token expiration timestamp
        expires_at = int(time.time() + expires_in)

        # Store tokens in memory (POC single-user mode)
        user_tokens["demo_user"] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at
        }

        # Log success with user info if available
        user_info = token_response.get("id_token_claims", {})
        username = user_info.get("preferred_username", "demo_user")
        logger.info(f"Authentication successful for user: {username}")
        logger.info(f"Token expires at: {datetime.fromtimestamp(expires_at).isoformat()}")
        logger.info(f"Refresh token available: {refresh_token is not None}")

        # Redirect to dashboard
        return RedirectResponse(url="/", status_code=302)

    except HTTPException:
        # Re-raise HTTP exceptions (already logged)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
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