# API Specification - Email Sorting POC

## Base URL
- Local: `http://localhost:8000`
- Production: `https://appliedai-api.azurewebsites.net` (future)

## Endpoints

### Health Check

**GET** `/health`

Returns service status.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2025-10-28T12:00:00Z"
}
```

---

### Authentication Flow

**GET** `/auth/login`

Initiates OAuth 2.0 Authorization Code flow with Microsoft Entra ID.

**Query Parameters:**
- None (state is generated server-side)

**Response:**
- `302 Redirect` to Microsoft sign-in page

**Scopes Requested:**
- `Mail.Read` - Read user's email
- `Mail.ReadWrite` - Move emails between folders (future)
- `offline_access` - Refresh token for persistent access

---

**GET** `/auth/callback`

OAuth callback endpoint. Microsoft redirects here after user authorization.

**Query Parameters:**
- `code` (string, required) - Authorization code from Microsoft
- `state` (string, required) - CSRF protection token
- `error` (string, optional) - Error code if authorization failed
- `error_description` (string, optional) - Human-readable error

**Success Response:**
- `302 Redirect` to `/` (dashboard)
- Token stored in server memory

**Error Response:**
- `400 Bad Request` with error details

---

### Email Fetching

**GET** `/graph/fetch`

Fetches emails from Microsoft Graph API using stored access token.

**Query Parameters:**
- `top` (integer, optional, default=10) - Number of emails to fetch (max 50)
- `skip` (integer, optional, default=0) - Pagination offset

**Response:**
```json
{
  "messages": [
    {
      "id": "AAMkAGI...",
      "subject": "CS 4980 Assignment Due",
      "from": {
        "emailAddress": {
          "name": "Professor Smith",
          "address": "john-smith@uiowa.edu"
        }
      },
      "receivedDateTime": "2025-10-28T10:30:00Z",
      "bodyPreview": "Your assignment is due this Friday...",
      "hasAttachments": false
    }
  ],
  "count": 10,
  "hasMore": true
}
```

**Error Responses:**
- `401 Unauthorized` - No valid token stored (redirect to `/auth/login`)
- `500 Internal Server Error` - Graph API failure

---

### Email Classification

**POST** `/classify`

Classifies a single email using Azure OpenAI Service.

**Request Body:**
```json
{
  "subject": "CS 4980 Assignment Due Friday",
  "body": "Your programming assignment is due this Friday at 11:59 PM...",
  "from": "john-smith@uiowa.edu",
  "categories": ["URGENT", "ACADEMIC", "ADMINISTRATIVE", "SOCIAL", "PROMOTIONAL", "OTHER"]
}
```

**Notes:**
- `categories` is optional - defaults to preset categories
- `body` can be full body or preview (first 500 chars recommended)

**Response:**
```json
{
  "category": "ACADEMIC",
  "confidence": 0.92,
  "reasoning": "Email from professor about assignment deadline"
}
```

**Error Responses:**
- `400 Bad Request` - Missing required fields
- `500 Internal Server Error` - Azure OpenAI Service failure

---

### Process New Emails

**GET** `/inbox/process-new`

Fetches unprocessed emails (received since last check), classifies them, and stores results.

**Query Parameters:**
- None (uses stored timestamp of last processing)

**Response:**
```json
{
  "processed": 5,
  "lastCheck": "2025-10-28T09:00:00Z",
  "newCheck": "2025-10-28T12:00:00Z",
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
      "receivedDateTime": "2025-10-28T10:30:00Z"
    }
  ]
}
```

**Error Responses:**
- `401 Unauthorized` - No valid token
- `500 Internal Server Error` - Processing failure

---

### Backfill Existing Inbox (Optional for POC)

**POST** `/inbox/backfill`

Triggers batch classification of all existing emails in inbox. Long-running operation.

**Request Body:**
```json
{
  "maxEmails": 100
}
```

**Response:**
```json
{
  "jobId": "uuid-here",
  "status": "started",
  "estimatedTime": "2-5 minutes",
  "message": "Processing 100 emails"
}
```

**Check Status:**
**GET** `/inbox/backfill/{jobId}`

```json
{
  "jobId": "uuid-here",
  "status": "processing",
  "progress": {
    "processed": 45,
    "total": 100,
    "errors": 0
  }
}
```

---

### Dashboard

**GET** `/`

Simple HTML dashboard showing classification results.

**Response:**
- HTML page with:
  - Login button (if not authenticated)
  - Email list grouped by category
  - "Process New Emails" button
  - "Backfill Inbox" button (optional)

---

## Authentication & Authorization

### Token Storage (POC)
- In-memory dictionary: `{user_id: {access_token, refresh_token, expires_at}}`
- Tokens cleared on server restart
- Production will use Azure Key Vault or encrypted database

### Token Refresh
- Not implemented in POC
- On 401 from Graph API, redirect to `/auth/login`

### Security Notes
- State parameter validates OAuth callback
- No session management in POC (single-user demo)
- HTTPS required in production

---

## Rate Limiting (Future)

Not implemented in POC. Future considerations:
- Azure OpenAI: Varies by deployment tier and quota
- Graph API: Varies by license
- Implement retry with exponential backoff

---

## Error Handling

All endpoints return errors in consistent format:

```json
{
  "error": "InvalidToken",
  "message": "Access token expired",
  "timestamp": "2025-10-28T12:00:00Z",
  "path": "/graph/fetch"
}
```

HTTP Status Codes:
- `200 OK` - Success
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server/API failure