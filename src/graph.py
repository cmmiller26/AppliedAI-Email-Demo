"""
Microsoft Graph API Integration Module

Provides helper functions for interacting with Microsoft Graph API
to fetch and manage email data.
"""

import httpx
import logging
from typing import Dict, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Microsoft Graph API base URL
GRAPH_API_BASE_URL = "https://graph.microsoft.com/v1.0"


async def get_messages(
    access_token: str,
    top: int = 10,
    skip: int = 0,
    folder: str = "inbox"
) -> Dict:
    """
    Fetch emails from Microsoft Graph API

    Makes an authenticated request to the Microsoft Graph API to retrieve
    email messages from the specified folder. Returns a paginated list of messages
    with key metadata fields.

    Args:
        access_token: OAuth access token with Mail.Read scope
        top: Number of emails to fetch (max 50, default 10)
        skip: Pagination offset (default 0)
        folder: Folder to read from - "inbox" (default), "drafts", or "sentitems"

    Returns:
        Dict with following keys:
            - messages (List[Dict]): Array of email message objects
            - count (int): Number of messages returned
            - hasMore (bool): True if more messages available (pagination)

    Raises:
        httpx.HTTPStatusError: If Graph API returns error status
        httpx.RequestError: If network request fails

    Example response:
        {
            "messages": [
                {
                    "id": "AAMkAGI...",
                    "subject": "Meeting Tomorrow",
                    "from": {"emailAddress": {"name": "John", "address": "john@example.com"}},
                    "receivedDateTime": "2025-10-28T10:30:00Z",
                    "bodyPreview": "Let's meet at...",
                    "hasAttachments": false,
                    "internetMessageId": "<msg123@mail.example.com>"
                }
            ],
            "count": 10,
            "hasMore": true
        }
    """
    logger.info(f"Fetching messages from Graph API (folder={folder}, top={top}, skip={skip})")

    # Build request URL with query parameters
    # Use mailFolders for specific folders, or /me/messages for all messages
    folder_map = {
        "inbox": "inbox",
        "drafts": "drafts",
        "sentitems": "sentitems"
    }

    folder_id = folder_map.get(folder.lower(), "inbox")
    url = f"{GRAPH_API_BASE_URL}/me/mailFolders/{folder_id}/messages"

    # Query parameters for Graph API
    # $select: Choose specific fields to reduce response size and improve performance
    # $orderby: Sort by most recent first
    # $top/$skip: Pagination parameters
    params = {
        "$select": "id,subject,from,receivedDateTime,bodyPreview,hasAttachments,internetMessageId",
        "$orderby": "receivedDateTime DESC",
        "$top": str(top),
        "$skip": str(skip)
    }

    # Request headers with authentication
    # Strip any whitespace from token to prevent formatting issues
    token = access_token.strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Log first/last few chars of token for debugging (never log full token)
    logger.debug(f"Using token: {token[:10]}...{token[-10:]}")

    try:
        # Make async HTTP request to Graph API
        async with httpx.AsyncClient() as client:
            # Log the request details for debugging (before making request)
            logger.info(f"Graph API request: GET {url}?$top={top}&$skip={skip}")
            logger.debug(f"Request headers: {dict(headers)}")  # Log full headers for debugging

            response = await client.get(url, params=params, headers=headers)

            # Log the response status
            logger.debug(f"Response status: {response.status_code}")

            # Check for authentication errors
            if response.status_code == 401:
                # Log the full error response from Graph API
                try:
                    error_body = response.json()
                    logger.error(f"Graph API returned 401 Unauthorized: {error_body}")
                except:
                    logger.error(f"Graph API returned 401 Unauthorized (raw response): {response.text}")

                raise httpx.HTTPStatusError(
                    message="Unauthorized: Access token is invalid or expired. Please re-authenticate.",
                    request=response.request,
                    response=response
                )

            # Raise exception for any other HTTP errors
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Extract messages array from OData response
            messages = data.get("value", [])

            # Check if there are more pages available
            # Graph API includes @odata.nextLink when pagination is available
            has_more = "@odata.nextLink" in data

            logger.info(f"Successfully fetched {len(messages)} messages from Graph API")
            if has_more:
                logger.info("More messages available (pagination)")

            # Return formatted response matching API specification
            return {
                "messages": messages,
                "count": len(messages),
                "hasMore": has_more
            }

    except httpx.HTTPStatusError as e:
        # HTTP error from Graph API (already logged above for 401)
        if e.response.status_code != 401:  # Don't log 401 twice
            logger.error(f"Graph API returned error {e.response.status_code}: {e.response.text}")
        raise

    except httpx.RequestError as e:
        # Network or connection error
        logger.error(f"Network error while calling Graph API: {str(e)}")
        raise

    except Exception as e:
        # Unexpected error (JSON parsing, etc.)
        logger.error(f"Unexpected error in get_messages: {str(e)}")
        raise


async def assign_category_to_message(
    access_token: str,
    message_id: str,
    category: str
) -> bool:
    """
    Assign an Outlook category to an email message

    Uses Microsoft Graph API to add a category label to an email.
    The category will be created automatically if it doesn't exist.

    Args:
        access_token: OAuth access token with Mail.ReadWrite scope
        message_id: Graph API message ID (not internetMessageId)
        category: Category name to assign (e.g., "URGENT", "ACADEMIC")

    Returns:
        True if category was assigned successfully, False otherwise

    Raises:
        httpx.HTTPStatusError: If Graph API returns error status
        httpx.RequestError: If network request fails

    Example:
        success = await assign_category_to_message(
            access_token="eyJ0...",
            message_id="AAMkAGI...",
            category="URGENT"
        )
    """
    logger.info(f"Assigning category '{category}' to message {message_id[:20]}...")

    # Build request URL
    url = f"{GRAPH_API_BASE_URL}/me/messages/{message_id}"

    # Request headers with authentication
    token = access_token.strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Request body - PATCH to update the categories property
    # Categories is an array of category names
    # We need to GET first to preserve existing categories, then add ours
    try:
        async with httpx.AsyncClient() as client:
            # First, get current categories
            response_get = await client.get(
                url,
                headers=headers,
                params={"$select": "categories"}
            )

            if response_get.status_code == 401:
                logger.error(f"Graph API returned 401 when fetching message categories")
                raise httpx.HTTPStatusError(
                    message="Unauthorized: Access token is invalid or expired",
                    request=response_get.request,
                    response=response_get
                )

            response_get.raise_for_status()
            current_data = response_get.json()
            current_categories = current_data.get("categories", [])

            # Add our category if not already present
            if category not in current_categories:
                current_categories.append(category)

            # PATCH to update categories
            payload = {
                "categories": current_categories
            }

            logger.debug(f"Updating message categories to: {current_categories}")

            response_patch = await client.patch(
                url,
                headers=headers,
                json=payload
            )

            if response_patch.status_code == 401:
                logger.error(f"Graph API returned 401 when updating message categories")
                raise httpx.HTTPStatusError(
                    message="Unauthorized: Access token is invalid or expired",
                    request=response_patch.request,
                    response=response_patch
                )

            response_patch.raise_for_status()

            logger.info(f"Successfully assigned category '{category}' to message")
            return True

    except httpx.HTTPStatusError as e:
        # HTTP error from Graph API
        logger.error(f"Graph API returned error {e.response.status_code}: {e.response.text}")
        raise

    except httpx.RequestError as e:
        # Network or connection error
        logger.error(f"Network error while calling Graph API: {str(e)}")
        raise

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in assign_category_to_message: {str(e)}")
        raise
