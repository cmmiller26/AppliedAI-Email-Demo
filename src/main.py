"""
Email Sorting POC - FastAPI Application
Main application entry point

Uses Azure AI Foundry with Azure OpenAI for email classification.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
import os
import secrets
import time
from typing import Optional, List, Dict
from dotenv import load_dotenv
from msal import ConfidentialClientApplication
from src.graph import get_messages, assign_category_to_message
from src.classifier import classify_email, PRESET_CATEGORIES
from src import scheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Email Sorting POC",
    description="Automated email classification using Microsoft Graph and Azure AI Foundry with Azure OpenAI",
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
SCOPES = ["Mail.Read", "Mail.ReadWrite", "Mail.Send"]
# For OAuth authorization, use full URIs without offline_access
# (offline_access is added automatically by MSAL when using ConfidentialClientApplication)
AUTH_SCOPES = ["https://graph.microsoft.com/Mail.Read", "https://graph.microsoft.com/Mail.ReadWrite", "https://graph.microsoft.com/Mail.Send"]

# In-memory storage (POC only - will be replaced with database in production)
user_tokens = {}  # {user_id: {access_token, refresh_token, expires_at}}
processed_emails = {}  # {internet_message_id: {category, timestamp, confidence}}
last_check_time = None  # Timestamp of last email fetch
auth_state_store = {}  # {state: timestamp} - CSRF protection for OAuth flow


# Pydantic models for request/response validation
class ClassifyRequest(BaseModel):
    """Request body for /classify endpoint"""
    subject: str = Field(..., description="Email subject line", min_length=1)
    body: str = Field(..., description="Email body content", min_length=1)
    from_address: str = Field(..., alias="from", description="Sender email address", min_length=1)
    categories: Optional[List[str]] = Field(
        None,
        description="Optional list of categories to use (defaults to preset categories)"
    )

    class Config:
        populate_by_name = True  # Allow both 'from' and 'from_address'
        json_schema_extra = {
            "example": {
                "subject": "CS 4980 Assignment Due Friday",
                "body": "Your programming assignment is due this Friday at 11:59 PM...",
                "from": "john-smith@uiowa.edu",
                "categories": ["URGENT", "ACADEMIC", "ADMINISTRATIVE", "SOCIAL", "PROMOTIONAL", "OTHER"]
            }
        }


class ClassifyResponse(BaseModel):
    """Response body for /classify endpoint"""
    category: str = Field(..., description="Classified category")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Brief explanation of classification")

    class Config:
        json_schema_extra = {
            "example": {
                "category": "ACADEMIC",
                "confidence": 0.92,
                "reasoning": "Email from professor about assignment deadline"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response format"""
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    path: str = Field(..., description="Request path that caused the error")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Missing required field: subject",
                "timestamp": "2025-10-31T12:00:00Z",
                "path": "/classify"
            }
        }


class ProcessedEmailInfo(BaseModel):
    """Single processed email information"""
    id: str = Field(..., description="Graph API message ID")
    subject: str = Field(..., description="Email subject")
    category: str = Field(..., description="Classified category")
    confidence: float = Field(..., description="Classification confidence")
    receivedDateTime: str = Field(..., description="When email was received")


class ProcessNewResponse(BaseModel):
    """Response body for /inbox/process-new endpoint"""
    processed: int = Field(..., description="Number of emails processed")
    lastCheck: Optional[str] = Field(None, description="Previous check timestamp")
    newCheck: str = Field(..., description="Current check timestamp")
    categories: Dict[str, int] = Field(..., description="Count of emails per category")
    emails: List[ProcessedEmailInfo] = Field(..., description="List of processed emails")

    class Config:
        json_schema_extra = {
            "example": {
                "processed": 5,
                "lastCheck": "2025-10-31T09:00:00Z",
                "newCheck": "2025-10-31T12:00:00Z",
                "categories": {
                    "URGENT": 1,
                    "ACADEMIC": 3,
                    "SOCIAL": 1
                },
                "emails": [
                    {
                        "id": "AAMkAGI...",
                        "subject": "CS 4980 Assignment",
                        "category": "ACADEMIC",
                        "confidence": 0.92,
                        "receivedDateTime": "2025-10-31T10:30:00Z"
                    }
                ]
            }
        }


# Storage layer helper functions
def is_processed(message_id: str) -> bool:
    """
    Check if an email has already been processed.

    Args:
        message_id: internetMessageId from Graph API

    Returns:
        True if email has been processed, False otherwise
    """
    return message_id in processed_emails


def mark_processed(
    message_id: str,
    category: str,
    confidence: float,
    subject: str,
    from_email: str
) -> None:
    """
    Mark an email as processed and store its classification result.

    Args:
        message_id: internetMessageId from Graph API (unique identifier)
        category: Classified category
        confidence: Classification confidence score (0.0 to 1.0)
        subject: Email subject line
        from_email: Sender email address
    """
    processed_emails[message_id] = {
        "category": category,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "subject": subject,
        "from": from_email
    }
    logger.debug(f"Marked email as processed: {message_id[:20]}... -> {category}")


def get_processed_emails() -> dict:
    """
    Get all processed emails with their classification results.

    Returns:
        Dictionary of processed emails keyed by internetMessageId
    """
    return processed_emails.copy()


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


def get_valid_token() -> Optional[str]:
    """
    Get valid access token for demo_user

    Checks if the demo_user exists in user_tokens and verifies that
    the token has not expired.

    Returns:
        Access token string if valid, None if user not authenticated
        or token expired
    """
    # Check if demo_user has stored tokens
    if "demo_user" not in user_tokens:
        logger.warning("No token found for demo_user")
        return None

    token_info = user_tokens["demo_user"]

    # Check if token is expired
    expires_at = token_info.get("expires_at", 0)
    current_time = time.time()

    if current_time > expires_at:
        logger.warning(f"Token expired for demo_user (expired at {datetime.fromtimestamp(expires_at).isoformat()})")
        return None

    # Token is valid
    return token_info.get("access_token")


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

        # Calculate category distribution
        category_stats = {}
        for email_data in processed_emails.values():
            cat = email_data["category"]
            category_stats[cat] = category_stats.get(cat, 0) + 1

        return JSONResponse(
            status_code=200,
            content={
                "message": "Authentication successful!",
                "authenticated": True,
                "token_expires_at": datetime.fromtimestamp(expires_at).isoformat() + "Z",
                "token_expired": is_expired,
                "has_refresh_token": token_info.get("refresh_token") is not None,
                "processing_stats": {
                    "total_processed": len(processed_emails),
                    "last_check_time": last_check_time.isoformat() + "Z" if last_check_time else None,
                    "category_distribution": category_stats
                },
                "next_steps": [
                    "Use GET /graph/fetch to fetch emails from inbox",
                    "Use POST /classify to classify an email with Azure OpenAI",
                    "Use POST /inbox/process-new to process new emails automatically",
                    "Use GET /debug/processed to view all processed emails"
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


@app.get("/debug/token")
async def debug_token():
    """
    Debug endpoint to check token info (for development only)
    """
    if "demo_user" not in user_tokens:
        return {"error": "No token found"}

    token_info = user_tokens["demo_user"]

    # Decode the access token to see claims (base64 decode middle part)
    import base64
    import json

    try:
        access_token = token_info.get("access_token", "")
        # JWT tokens have 3 parts: header.payload.signature
        parts = access_token.split(".")
        if len(parts) >= 2:
            # Decode payload (add padding if needed)
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)  # Add padding
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)

            return {
                "access_token": access_token,  # Include actual token for test script
                "expires_at": datetime.fromtimestamp(token_info.get("expires_at", 0)).isoformat(),
                "token_expired": time.time() > token_info.get("expires_at", 0),
                "scopes": claims.get("scp", "No scopes found"),  # Space-separated list
                "audience": claims.get("aud"),
                "issuer": claims.get("iss")
            }
    except Exception as e:
        return {"error": f"Could not decode token: {str(e)}"}


@app.get("/debug/test-graph")
async def test_graph():
    """
    Test Microsoft Graph API with /me endpoint to verify token works
    """
    import httpx

    if "demo_user" not in user_tokens:
        return {"error": "No token found"}

    access_token = get_valid_token()
    if not access_token:
        return {"error": "Token expired"}

    # Try calling /me endpoint which requires minimal permissions
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    results = {}

    try:
        async with httpx.AsyncClient() as client:
            # Test 1: /me endpoint
            response_me = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            results["me"] = {
                "status": response_me.status_code,
                "success": response_me.status_code == 200
            }

            # Test 2: /me/mailFolders endpoint
            response_folders = await client.get(
                "https://graph.microsoft.com/v1.0/me/mailFolders",
                headers=headers
            )
            results["mailFolders"] = {
                "status": response_folders.status_code,
                "success": response_folders.status_code == 200,
                "response": response_folders.json() if response_folders.status_code == 200 else response_folders.text
            }

            # Test 3: /me/messages endpoint with minimal params
            response_messages = await client.get(
                "https://graph.microsoft.com/v1.0/me/messages?$top=1",
                headers=headers
            )
            results["messages_simple"] = {
                "status": response_messages.status_code,
                "success": response_messages.status_code == 200,
                "response": response_messages.json() if response_messages.status_code == 200 else response_messages.text
            }

            # Test 4: Try Outlook REST API (for personal accounts)
            # Personal Microsoft accounts often need outlook.office.com instead of graph.microsoft.com
            outlook_headers = headers.copy()
            response_outlook = await client.get(
                "https://outlook.office.com/api/v2.0/me/messages?$top=1",
                headers=outlook_headers
            )
            results["outlook_api"] = {
                "status": response_outlook.status_code,
                "success": response_outlook.status_code == 200,
                "response": response_outlook.json() if response_outlook.status_code == 200 else response_outlook.text
            }

            return results

    except Exception as e:
        return {"error": str(e), "results": results}


@app.get("/debug/processed")
async def debug_processed():
    """
    Debug endpoint to view all processed emails (for development only)

    Returns:
        JSON with count of processed emails, last check time, and full list
    """
    return {
        "count": len(processed_emails),
        "last_check_time": last_check_time.isoformat() + "Z" if last_check_time else None,
        "emails": [
            {
                "internet_message_id": msg_id,
                "subject": data["subject"],
                "from": data["from"],
                "category": data["category"],
                "confidence": data["confidence"],
                "processed_at": data["timestamp"]
            }
            for msg_id, data in processed_emails.items()
        ]
    }


@app.get("/graph/fetch")
async def graph_fetch(
    top: int = Query(10, ge=1, le=50, description="Number of emails to fetch (1-50)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    folder: str = Query("inbox", description="Folder to read from: inbox, drafts, or sentitems")
):
    """
    Fetch emails from Microsoft Graph API

    Retrieves email messages from the specified folder using
    Microsoft Graph API. Requires valid authentication token from prior
    OAuth login flow.

    Args:
        top: Number of emails to fetch (1-50, default=10)
        skip: Pagination offset (default=0)
        folder: Folder to read from - "inbox" (default), "drafts", or "sentitems"

    Returns:
        JSON response with messages array, count, and pagination info

    Error Responses:
        401 Unauthorized: No valid token (user must authenticate)
        403 Forbidden: Personal account detected (organizational account required)
        500 Internal Server Error: Graph API or network failure
    """
    try:
        logger.info(f"Fetching emails from Graph API (folder={folder}, top={top}, skip={skip})")

        # Validate and get access token
        access_token = get_valid_token()

        if not access_token:
            logger.warning("Graph fetch attempted without valid authentication")
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please visit /auth/login to authenticate with Microsoft."
            )

        # Check if this is a personal account (which has limited Graph API access)
        token_info = user_tokens.get("demo_user", {})
        if token_info:
            import base64
            import json
            try:
                parts = access_token.split(".")
                if len(parts) >= 2:
                    payload = parts[1]
                    payload += "=" * (4 - len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload)
                    claims = json.loads(decoded)

                    # Check for personal account indicators
                    idp = claims.get("idp", "")
                    tenant_id = claims.get("tid", "")

                    # Consumer tenant ID for personal Microsoft accounts
                    CONSUMER_TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"

                    if idp == "live.com" or tenant_id == CONSUMER_TENANT:
                        logger.warning("Personal Microsoft account detected - Graph API mail access not supported")
                        raise HTTPException(
                            status_code=403,
                            detail="Personal Microsoft accounts (outlook.com, hotmail.com) are not supported. "
                                   "Please use an organizational account (e.g., @uiowa.edu) or sign up for a "
                                   "free Microsoft 365 Developer account at https://developer.microsoft.com/microsoft-365/dev-program"
                        )
            except Exception as e:
                logger.debug(f"Could not check account type: {e}")

        # Call Graph API helper function
        try:
            result = await get_messages(
                access_token=access_token,
                top=top,
                skip=skip,
                folder=folder
            )

            logger.info(f"Successfully fetched {result['count']} messages from Graph API")

            # Return response matching API specification
            return JSONResponse(
                status_code=200,
                content=result
            )

        except Exception as graph_error:
            # Check if it's a 401 authentication error from Graph API
            if hasattr(graph_error, 'response') and hasattr(graph_error.response, 'status_code'):
                if graph_error.response.status_code == 401:
                    logger.error("Graph API rejected token - token may be expired or invalid")
                    raise HTTPException(
                        status_code=401,
                        detail="Access token expired or invalid. Please visit /auth/login to re-authenticate."
                    )

            # Other Graph API or network errors
            logger.error(f"Error fetching messages from Graph API: {str(graph_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch emails from Microsoft Graph: {str(graph_error)}"
            )

    except HTTPException:
        # Re-raise HTTP exceptions (already logged and formatted)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in /graph/fetch: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest):
    """
    Classify an email using Azure OpenAI via Azure AI Foundry

    Analyzes email content (subject, body, sender) and categorizes it into one of
    the preset categories: URGENT, ACADEMIC, ADMINISTRATIVE, SOCIAL, PROMOTIONAL, or OTHER.

    Args:
        request: ClassifyRequest with subject, body, from_address, and optional categories

    Returns:
        ClassifyResponse with category, confidence score (0.0-1.0), and reasoning

    Error Responses:
        400 Bad Request: Missing or invalid required fields (subject, body, from)
        500 Internal Server Error: Azure OpenAI API failure or classification error
    """
    try:
        logger.info(f"Classification requested for email: '{request.subject[:50]}...'")

        # Validate categories if provided
        if request.categories:
            invalid_categories = [cat for cat in request.categories if cat not in PRESET_CATEGORIES]
            if invalid_categories:
                logger.warning(f"Invalid categories provided: {invalid_categories}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "ValidationError",
                        "message": f"Invalid categories: {invalid_categories}. Valid categories are: {PRESET_CATEGORIES}",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "path": "/classify"
                    }
                )

        # Call classifier function
        result = classify_email(
            subject=request.subject,
            body=request.body,
            from_address=request.from_address
        )

        # Check if classification failed (confidence 0.0 usually indicates error)
        if result.get("confidence", 0.0) == 0.0 and "failed" in result.get("reasoning", "").lower():
            logger.error(f"Classification failed: {result.get('reasoning')}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "ClassificationError",
                    "message": f"Classification failed: {result.get('reasoning', 'Unknown error')}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "path": "/classify"
                }
            )

        logger.info(f"Email classified as '{result['category']}' with confidence {result['confidence']:.2f}")

        # Return successful classification
        return ClassifyResponse(
            category=result["category"],
            confidence=result["confidence"],
            reasoning=result["reasoning"]
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already logged and formatted)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in /classify: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": f"Classification failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "path": "/classify"
            }
        )


async def process_new_emails_internal(access_token: str) -> dict:
    """
    Internal function for processing new emails.

    This function contains the core email processing logic and can be called
    by both the REST endpoint and the background scheduler.

    Args:
        access_token: Valid OAuth access token

    Returns:
        Dict with processing results matching ProcessNewResponse structure

    Raises:
        Exception: If processing fails (caller should handle)
    """
    global last_check_time

    logger.info("Starting batch processing of new emails")

    # Store old last_check_time for response
    previous_check = last_check_time.isoformat() + "Z" if last_check_time else None

    # Fetch emails from Graph API
    # On first run, fetch all emails (no filter)
    # On subsequent runs, only fetch emails newer than last_check_time
    logger.info(f"Fetching emails (last check: {previous_check or 'never'})")

    try:
        # Fetch emails - get more than default to process in batches
        result = await get_messages(
            access_token=access_token,
            top=50,  # Fetch up to 50 emails per batch
            skip=0,
            folder="inbox"
        )

        messages = result.get("messages", [])
        logger.info(f"Fetched {len(messages)} emails from Graph API")

    except Exception as graph_error:
        logger.error(f"Error fetching messages from Graph API: {str(graph_error)}")
        raise Exception(f"Failed to fetch emails: {str(graph_error)}")

    # Filter messages to only those received after last_check_time
    if last_check_time:
        # Filter by receivedDateTime
        new_messages = []
        for msg in messages:
            received_dt_str = msg.get("receivedDateTime")
            if received_dt_str:
                # Parse ISO 8601 datetime
                from dateutil import parser
                received_dt = parser.parse(received_dt_str)
                # Remove timezone info for comparison
                received_dt_naive = received_dt.replace(tzinfo=None)

                if received_dt_naive > last_check_time:
                    new_messages.append(msg)

        messages = new_messages
        logger.info(f"Filtered to {len(messages)} emails received after last check")

    # Filter out already processed emails (idempotency)
    unprocessed_messages = []
    for msg in messages:
        message_id = msg.get("internetMessageId")
        if not message_id:
            logger.warning(f"Email missing internetMessageId: {msg.get('id')} - skipping")
            continue

        if is_processed(message_id):
            logger.debug(f"Email already processed: {message_id[:20]}... - skipping")
            continue

        unprocessed_messages.append(msg)

    logger.info(f"Found {len(unprocessed_messages)} unprocessed emails to classify")

    # Process each unprocessed email
    processed_count = 0
    category_counts = {}
    processed_emails_info = []

    for msg in unprocessed_messages:
        try:
            # Extract email fields
            message_id = msg.get("internetMessageId")
            subject = msg.get("subject", "(No Subject)")
            body_preview = msg.get("bodyPreview", "")
            received_dt = msg.get("receivedDateTime")
            graph_id = msg.get("id")

            # Extract sender email address
            from_obj = msg.get("from", {})
            from_email_obj = from_obj.get("emailAddress", {})
            from_email = from_email_obj.get("address", "unknown@example.com")

            logger.info(f"Classifying email: '{subject[:50]}...' from {from_email}")

            # Classify email
            classification = classify_email(
                subject=subject,
                body=body_preview,
                from_address=from_email
            )

            category = classification["category"]
            confidence = classification["confidence"]

            # Assign Outlook category to the email
            try:
                await assign_category_to_message(
                    access_token=access_token,
                    message_id=graph_id,
                    category=category
                )
                logger.info(f"Assigned Outlook category '{category}' to email")
            except Exception as category_error:
                # Log error but don't fail the whole batch
                logger.error(f"Failed to assign category to email: {str(category_error)}")
                # Continue processing - classification still succeeded

            # Mark as processed
            mark_processed(
                message_id=message_id,
                category=category,
                confidence=confidence,
                subject=subject,
                from_email=from_email
            )

            # Update category counts
            category_counts[category] = category_counts.get(category, 0) + 1

            # Add to response list
            processed_emails_info.append({
                "id": graph_id,
                "subject": subject,
                "category": category,
                "confidence": confidence,
                "receivedDateTime": received_dt
            })

            processed_count += 1
            logger.info(f"Email classified as {category} (confidence: {confidence:.2f})")

        except Exception as classify_error:
            # Log error but continue processing other emails
            logger.error(f"Error classifying email {msg.get('id')}: {str(classify_error)}")
            # Don't raise - continue to next email
            continue

    # Update last_check_time to now
    current_time = datetime.utcnow()
    last_check_time = current_time
    new_check = current_time.isoformat() + "Z"

    logger.info(f"Batch processing complete: {processed_count} emails processed")
    logger.info(f"Category distribution: {category_counts}")

    # Return summary
    return {
        "processed": processed_count,
        "lastCheck": previous_check,
        "newCheck": new_check,
        "categories": category_counts,
        "emails": processed_emails_info
    }


@app.post("/inbox/process-new", response_model=ProcessNewResponse)
async def process_new_emails():
    """
    Fetch and classify new emails since last check

    Retrieves emails received since the last processing run (or all emails on first run),
    filters out already-processed emails using internetMessageId for idempotency,
    classifies each new email with Azure OpenAI via Azure AI Foundry, and stores the results.

    Returns:
        ProcessNewResponse with processing summary and classified emails

    Error Responses:
        401 Unauthorized: No valid token (user must authenticate)
        500 Internal Server Error: Graph API or classification failures
    """
    try:
        logger.info("Processing new emails via REST endpoint")

        # Validate and get access token
        access_token = get_valid_token()

        if not access_token:
            logger.warning("Process-new attempted without valid authentication")
            raise HTTPException(
                status_code=401,
                detail="Not authenticated. Please visit /auth/login to authenticate with Microsoft."
            )

        # Call internal processing function
        result = await process_new_emails_internal(access_token)

        # Convert emails list to ProcessedEmailInfo models
        emails_with_models = [
            ProcessedEmailInfo(**email) for email in result["emails"]
        ]

        # Return as ProcessNewResponse model
        return ProcessNewResponse(
            processed=result["processed"],
            lastCheck=result["lastCheck"],
            newCheck=result["newCheck"],
            categories=result["categories"],
            emails=emails_with_models
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already logged)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in /inbox/process-new: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


async def scheduler_processing_wrapper() -> dict:
    """
    Wrapper function for scheduler to process emails.
    Handles token validation and returns results.
    """
    # Get valid token
    access_token = get_valid_token()

    if not access_token:
        raise Exception("Not authenticated. Token expired or missing.")

    # Process emails
    return await process_new_emails_internal(access_token)


@app.post("/scheduler/start")
async def start_scheduler_endpoint(
    interval: int = Query(None, ge=10, le=3600, description="Polling interval in seconds (10-3600)")
):
    """
    Start the background email processing scheduler.

    Args:
        interval: Optional polling interval in seconds (min 10, max 3600).
                 If not provided, uses POLLING_INTERVAL env var or default (60s).

    Returns:
        JSON with scheduler status and configuration

    Example:
        POST /scheduler/start?interval=30
    """
    try:
        # Use provided interval, or get default from environment/config
        if interval is None:
            interval = scheduler.get_default_interval()

        logger.info(f"Starting scheduler with interval={interval}s")

        result = scheduler.start_scheduler(interval_seconds=interval)

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Scheduler started successfully",
                "interval_seconds": interval,
                "next_run": result["next_run"]
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@app.post("/scheduler/stop")
async def stop_scheduler_endpoint():
    """
    Stop the background email processing scheduler.

    Returns:
        JSON with success message

    Example:
        POST /scheduler/stop
    """
    try:
        logger.info("Stopping scheduler")

        result = scheduler.stop_scheduler()

        return JSONResponse(
            status_code=200,
            content={
                "message": result["message"],
                "status": result["status"]
            }
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@app.get("/scheduler/status")
async def get_scheduler_status_endpoint():
    """
    Get current scheduler status and statistics.

    Returns:
        JSON with scheduler state, interval, next run time, last run info

    Example response:
        {
            "running": true,
            "interval_seconds": 60,
            "next_run": "2025-11-04T12:01:00Z",
            "last_run": "2025-11-04T12:00:00Z",
            "last_run_result": {
                "processed": 3,
                "categories": {"URGENT": 1, "ACADEMIC": 2}
            }
        }
    """
    try:
        status = scheduler.get_scheduler_status()

        return JSONResponse(
            status_code=200,
            content=status
        )

    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


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

    # Initialize scheduler
    try:
        scheduler.initialize_scheduler(scheduler_processing_wrapper)
        logger.info("Scheduler initialized successfully")

        # Check if auto-start is enabled (default: yes)
        auto_start = os.getenv("SCHEDULER_AUTO_START", "true").lower() == "true"

        if auto_start:
            interval = scheduler.get_default_interval()
            scheduler.start_scheduler(interval_seconds=interval)
            logger.info(f"Scheduler auto-started with interval={interval}s")
        else:
            logger.info("Scheduler auto-start disabled (use POST /scheduler/start to enable)")

    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {str(e)}")
        logger.warning("Application will continue without scheduler")

    logger.info("Server ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown
    """
    logger.info("Email Sorting POC shutting down...")

    # Shutdown scheduler gracefully
    try:
        scheduler.shutdown_scheduler()
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")

    logger.info(f"Total tokens stored: {len(user_tokens)}")
    logger.info(f"Total emails processed: {len(processed_emails)}")


# For running directly with Python (development only)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )