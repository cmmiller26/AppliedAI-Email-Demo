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

Classifies a single email using Azure OpenAI via Azure AI Foundry.

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
- `500 Internal Server Error` - Azure OpenAI API failure

---

### Process New Emails

**POST** `/inbox/process-new`

Fetches unprocessed emails (received since last check), classifies them using Azure OpenAI via Azure AI Foundry, assigns Outlook categories, and stores results.

**Features:**
- Ensures idempotency using `internetMessageId` (same email never processed twice)
- Automatically assigns Outlook category labels to emails
- Tracks `last_check_time` to only process new emails on subsequent runs
- Processes up to 50 emails per batch

**Query Parameters:**
- None (uses stored timestamp of last processing)

**Response:**
```json
{
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
```

**Idempotency Behavior:**
- First run: Processes all emails in inbox (up to 50)
- Subsequent runs: Only processes emails received after `lastCheck`
- Already-processed emails are skipped (even if received after `lastCheck`)
- Safe to call multiple times

**Outlook Category Assignment:**
- Each classified email automatically gets an Outlook category label
- Categories appear as colored tags in Outlook desktop, web, and mobile
- If category assignment fails, email is still marked as processed

**Error Responses:**
- `401 Unauthorized` - No valid token
- `500 Internal Server Error` - Processing failure

---

### Scheduler Control

**POST** `/scheduler/start?interval={seconds}`

Starts the background email processing scheduler.

**Query Parameters:**
- `interval` (integer, optional) - Polling interval in seconds (10-3600)
  - If not provided, uses `POLLING_INTERVAL` from environment (default: 60)
  - Minimum: 10 seconds
  - Maximum: 3600 seconds (1 hour)

**Response:**
```json
{
  "message": "Scheduler started successfully",
  "interval_seconds": 60,
  "next_run": "2025-11-04T12:01:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Invalid interval (< 10 or > 3600)
- `500 Internal Server Error` - Scheduler initialization failed

**Notes:**
- Scheduler automatically calls `/inbox/process-new` logic at specified interval
- Can be called while scheduler is already running to change interval
- Respects idempotency - won't reprocess same emails

---

**POST** `/scheduler/stop`

Stops the background email processing scheduler.

**Query Parameters:**
- None

**Response:**
```json
{
  "message": "Scheduler stopped successfully",
  "status": "stopped"
}
```

**Notes:**
- Scheduler can be restarted later with `/scheduler/start`
- No emails will be processed automatically while stopped
- Manual `/inbox/process-new` endpoint still works

---

**GET** `/scheduler/status`

Gets current scheduler status and statistics.

**Query Parameters:**
- None

**Response:**
```json
{
  "running": true,
  "interval_seconds": 60,
  "next_run": "2025-11-04T12:01:00Z",
  "last_run": "2025-11-04T12:00:00Z",
  "last_run_result": {
    "processed": 5,
    "categories": {
      "URGENT": 1,
      "ACADEMIC": 3,
      "SOCIAL": 1
    }
  }
}
```

**Fields:**
- `running` (boolean) - Whether scheduler is currently active
- `interval_seconds` (integer|null) - Current polling interval
- `next_run` (string|null) - ISO 8601 timestamp of next scheduled run
- `last_run` (string|null) - ISO 8601 timestamp of last run
- `last_run_result` (object|null) - Results from last processing run

**Notes:**
- Returns status even if scheduler is stopped
- `last_run_result` includes error details if last run failed

---

### View Processed Emails (Debug)

**GET** `/debug/processed`

Returns all processed emails with their classifications (debug endpoint).

**Query Parameters:**
- None

**Response:**
```json
{
  "count": 10,
  "last_check_time": "2025-10-31T12:00:00Z",
  "emails": [
    {
      "internet_message_id": "<CAB123@mail.gmail.com>",
      "subject": "CS 4980 Assignment Due Tonight",
      "from": "professor@uiowa.edu",
      "category": "URGENT",
      "confidence": 0.95,
      "processed_at": "2025-10-31T11:30:15Z"
    }
  ]
}
```

**Notes:**
- For development/debugging only
- Shows all emails processed since server start
- In-memory storage (cleared on server restart)

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

Interactive web dashboard displaying email classification statistics and results.

**Response:**
- HTML page with:
  - **Not Authenticated View:**
    - Login screen with "Sign In with Microsoft" button
    - University of Iowa branding
  - **Authenticated View:**
    - **Stats Cards:**
      - Total processed emails
      - Last check time (relative: "Just now", "5m ago", etc.)
      - Scheduler status (Running/Stopped with indicator)
      - Average confidence percentage
    - **Category Distribution:**
      - 6 category cards with emoji, description, and count
      - Color-coded by category (red, blue, orange, green, purple, gray)
    - **Action Bar:**
      - "Process New Emails" button (with loading state)
      - "View Debug Data" link (opens /debug/processed)
      - Auto-refresh checkbox (30-second reload)
    - **Email Lists:**
      - Tables grouped by category
      - Shows subject, from, timestamp, confidence badge
      - Color-coded confidence: green (80%+), yellow (60-79%), red (<60%)
      - Limited to 10 most recent emails per category
    - **Empty State:**
      - Friendly message if no emails processed yet
    - **Logout Button:**
      - Clears token and returns to login screen

**Features:**
- Responsive design using Tailwind CSS
- Real-time stats updated on page load
- JavaScript-driven process button with feedback
- Optional auto-refresh for monitoring

**Technologies:**
- Jinja2 templates for server-side rendering
- Tailwind CSS (CDN) for styling
- Vanilla JavaScript for interactivity

---

**GET** `/auth/logout`

Logout endpoint that clears user token and redirects to dashboard.

**Response:**
- `302 Redirect` to `/` (dashboard)
- Token removed from server memory

**Notes:**
- After logout, dashboard shows login screen
- Safe to call even if not authenticated

---

## Authentication & Authorization

### Azure App Registration

The API uses OAuth 2.0 with Azure App Registration for authentication.

**App Registration Details:**
- Name: `app-appliedai-classifier-poc`
- Tenant: Single tenant (University of Iowa)
- Client Secret: `poc-local-dev` (24-month expiration)

### Token Management

#### Token Storage (POC)
Tokens are stored in server memory:
```python
user_tokens = {
    "demo_user": {
        "access_token": "eyJ0eXAi...",
        "refresh_token": "0.AXsA...",
        "expires_at": 1698509234
    }
}
```

#### Token Expiration
- Access tokens expire after **~1 hour**
- Refresh tokens valid for **90 days**
- POC: Manual re-authentication when expired
- Production: Automatic refresh using refresh token

### API Scopes

| Scope | Purpose | Required |
|-------|---------|----------|
| `Mail.Read` | Read user's emails | Yes |
| `Mail.ReadWrite` | Assign Outlook categories | Yes |
| `offline_access` | Refresh token support | Yes |

### Token Refresh
- Not implemented in POC
- On 401 from Graph API, redirect to `/auth/login`
- Phase 8 will implement automatic refresh using refresh_token

### Security Notes
- State parameter validates OAuth callback (CSRF protection)
- No session management in POC (single-user demo)
- HTTPS required in production
- Client secret stored in `.env` (gitignored)
- Production: Use Azure Key Vault for secrets

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