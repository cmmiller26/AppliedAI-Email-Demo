# System Architecture - Email Sorting POC

## High-Level Overview

```
┌─────────────┐
│   Browser   │
│   (User)    │
└──────┬──────┘
       │
       │ HTTP Requests
       ▼
┌─────────────────────────────────────┐
│      FastAPI Application            │
│                                     │
│  ┌────────────┐  ┌──────────────┐   │
│  │   Auth     │  │  Dashboard   │   │
│  │  Endpoints │  │   (HTML)     │   │
│  └────────────┘  └──────────────┘   │
│                                     │
│  ┌────────────┐  ┌──────────────┐   │
│  │   Graph    │  │ Classifier   │   │
│  │    API     │  │  (Azure AI)  │   │
│  └────────────┘  └──────────────┘   │
│                                     │
│  ┌────────────────────────────────┐ │
│  │   In-Memory Storage            │ │
│  │  • user_tokens                 │ │
│  │  • processed_emails            │ │
│  │  • last_check_time             │ │
│  └────────────────────────────────┘ │
└──────┬─────────────────────┬────────┘
       │                     │
       │                     │
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│  Microsoft   │      │ Azure OpenAI │
│  Graph API   │      │   Service    │
│ (Entra ID)   │      │  (GPT-4o)    │
└──────────────┘      └──────────────┘
```

---

## Component Details

### 1. FastAPI Application (`app.py`)

**Responsibilities:**
- HTTP request handling
- Route management
- Session/token management (in-memory for POC)
- Error handling and logging

**Key Modules:**
- `app.py` - Main application entry point
- `graph.py` - Microsoft Graph API integration
- `classifier.py` - Azure OpenAI classification logic
- `templates/` - HTML templates for dashboard

**Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - HTTP client for API calls
- `python-dotenv` - Environment configuration

---

### 2. Authentication Flow (OAuth 2.0)

```
User                Browser             FastAPI             Microsoft Entra ID
 │                    │                   │                       │
 │  Click "Login"     │                   │                       │
 ├───────────────────►│                   │                       │
 │                    │  GET /auth/login  │                       │
 │                    ├──────────────────►│                       │
 │                    │                   │  Generate auth URL    │
 │                    │                   │  with state param     │
 │                    │                   │                       │
 │                    │ 302 Redirect      │                       │
 │                    │◄──────────────────┤                       │
 │                    │                   │                       │
 │                    │  Redirect to Microsoft                    │
 │                    ├──────────────────────────────────────────►│
 │                    │                   │                       │
 │  Sign in with      │                   │                       │
 │  credentials       │                   │                       │
 ├───────────────────►│                   │                       │
 │                    │                   │                       │
 │                    │  Authorization granted                    │
 │                    │◄──────────────────────────────────────────┤
 │                    │                   │                       │
 │                    │  GET /auth/callback?code=xxx&state=yyy    │
 │                    ├──────────────────►│                       │
 │                    │                   │  Validate state       │
 │                    │                   │  Exchange code for    │
 │                    │                   │  access token         │
 │                    │                   ├──────────────────────►│
 │                    │                   │                       │
 │                    │                   │  Return tokens        │
 │                    │                   │◄──────────────────────┤
 │                    │                   │  Store in memory      │
 │                    │                   │                       │
 │                    │  302 to dashboard │                       │
 │                    │◄──────────────────┤                       │
 │  View dashboard    │                   │                       │
 │◄───────────────────┤                   │                       │
```

**Implementation Details:**
```python
# MSAL Configuration
from msal import ConfidentialClientApplication

auth_app = ConfidentialClientApplication(
    client_id=os.getenv("CLIENT_ID"),
    client_credential=os.getenv("CLIENT_SECRET"),
    authority=f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}"
)

# Scopes requested
SCOPES = ["Mail.Read", "Mail.ReadWrite", "offline_access"]

# Token storage (POC - in-memory)
user_tokens = {}  # {user_id: {access_token, refresh_token, expires_at}}
```

---

### 3. Email Fetching Flow

```
FastAPI              Graph API             Response
   │                    │                     │
   │  GET /graph/fetch  │                     │
   │  ?top=10           │                     │
   │                    │                     │
   │  Retrieve token    │                     │
   │  from memory       │                     │
   │                    │                     │
   │  GET /me/messages  │                     │
   │  Authorization:    │                     │
   │  Bearer {token}    │                     │
   ├───────────────────►│                     │
   │                    │                     │
   │                    │  Query mailbox      │
   │                    │                     │
   │                    │  Return messages    │
   │◄───────────────────┤                     │
   │                    │                     │
   │  Format response   │                     │
   │                    │                     │
   │  Return JSON       │                     │
   ├─────────────────────────────────────────►│
```

**Graph API Endpoint:**
```
GET https://graph.microsoft.com/v1.0/me/messages
    ?$top=10
    &$select=id,subject,from,receivedDateTime,bodyPreview,hasAttachments
    &$orderby=receivedDateTime DESC
```

**Response Format:**
```json
{
  "messages": [
    {
      "id": "AAMkAGI2...",
      "subject": "CS 4980 Assignment",
      "from": {
        "emailAddress": {
          "name": "Professor Smith",
          "address": "john-smith@uiowa.edu"
        }
      },
      "receivedDateTime": "2025-10-28T10:30:00Z",
      "bodyPreview": "Your assignment is due...",
      "hasAttachments": false
    }
  ]
}
```

---

### 4. Email Classification Flow

```
FastAPI         Classifier Module      OpenAI API       Response
   │                   │                    │              │
   │ POST /classify    │                    │              │
   │ {email data}      │                    │              │
   ├──────────────────►│                    │              │
   │                   │                    │              │
   │                   │ Sanitize input     │              │
   │                   │ (strip HTML,       │              │
   │                   │  truncate body)    │              │
   │                   │                    │              │
   │                   │ Build prompt       │              │
   │                   │                    │              │
   │                   │ POST /chat/        │              │
   │                   │ completions        │              │
   │                   ├───────────────────►│              │
   │                   │                    │              │
   │                   │                    │ Process      │
   │                   │                    │              │
   │                   │ JSON response      │              │
   │                   │◄───────────────────┤              │
   │                   │                    │              │
   │                   │ Parse category,    │              │
   │                   │ confidence         │              │
   │                   │                    │              │
   │ Return result     │                    │              │
   │◄──────────────────┤                    │              │
   │                   │                    │              │
   │ {category, conf}  │                    │              │
   ├──────────────────────────────────────────────────────►│
```

**Azure OpenAI Request:**
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

response = client.chat.completions.create(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),  # e.g., "gpt-4o-mini"
    temperature=0.3,
    max_tokens=200,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
)
```

---

### 5. Automated Processing Flow

```
User              FastAPI           Graph API      Classifier      Storage
 │                  │                   │              │              │
 │ GET /inbox/      │                   │              │              │
 │ process-new      │                   │              │              │
 ├─────────────────►│                   │              │              │
 │                  │                   │              │              │
 │                  │ Check             │              │              │
 │                  │ last_check_time   │              │              │
 │                  │                   │              │              │
 │                  │ Fetch new emails  │              │              │
 │                  ├──────────────────►│              │              │
 │                  │                   │              │              │
 │                  │ Filter processed  │              │              │
 │                  │ emails            │              │              │
 │                  │                   │              │              │
 │                  │ For each new email:              │              │
 │                  │                   │              │              │
 │                  │ Classify email    │              │              │
 │                  ├─────────────────────────────────►│              │
 │                  │                   │              │              │
 │                  │                   │ Return category             │
 │                  │◄─────────────────────────────────┤              │
 │                  │                   │              │              │
 │                  │ Store result      │              │              │
 │                  ├────────────────────────────────────────────────►│
 │                  │                   │              │              │
 │                  │ Update            │              │              │
 │                  │ last_check_time   │              │              │
 │                  │                   │              │              │
 │ Return summary   │                   │              │              │
 │◄─────────────────┤                   │              │              │
```

**Deduplication Logic:**
```python
processed_emails = {}  # {internet_message_id: {...}}

def is_processed(message_id: str) -> bool:
    return message_id in processed_emails

def mark_processed(message_id: str, category: str, confidence: float):
    processed_emails[message_id] = {
        "category": category,
        "confidence": confidence,
        "timestamp": datetime.utcnow()
    }
```

---

## Data Models

### Token Storage
```python
{
    "user_id": "demo_user",  # POC uses single user
    "access_token": "eyJ0eXAiOiJKV1...",
    "refresh_token": "0.AXsAjd...",
    "expires_at": 1698509234  # Unix timestamp
}
```

### Processed Email Record
```python
{
    "internet_message_id": "<CAB...@mail.gmail.com>",
    "category": "ACADEMIC",
    "confidence": 0.92,
    "timestamp": "2025-10-28T12:00:00Z",
    "subject": "CS 4980 Assignment",
    "from": "john-smith@uiowa.edu"
}
```

### Classification Result
```python
{
    "category": "ACADEMIC",
    "confidence": 0.92,
    "reasoning": "Email from professor about class assignment"
}
```

---

## State Management (POC)

### Global State Variables
```python
# In-memory storage (resets on server restart)
user_tokens = {}              # OAuth tokens
processed_emails = {}         # Classification results
last_check_time = None        # Timestamp of last email fetch
```

### Limitations (POC)
- **No persistence:** Data lost on restart
- **Single-user only:** One token per server instance
- **No token refresh:** Must re-authenticate after expiry

### Future: Production State
- **Database:** PostgreSQL or Azure SQL
- **Cache:** Redis for session tokens
- **Blob Storage:** Azure Blob for processed email metadata

---

## Security Considerations

### POC Security (Minimal)
- ✅ OAuth state parameter prevents CSRF
- ✅ Tokens stored server-side (not in cookies)
- ✅ HTTPS enforced in production
- ❌ No token encryption at rest
- ❌ No rate limiting
- ❌ No input validation on email content

### Production Security (Future)
- Encrypt tokens at rest (Azure Key Vault)
- Implement rate limiting
- Add CORS policies
- Sanitize all user inputs
- Add audit logging
- Comply with IT-15 policy (multi-factor auth, access controls)

---

## Scalability Considerations

### Current Limitations
- In-memory storage → Single server only
- Synchronous processing → Blocks on slow API calls
- No caching → Repeated classification of same emails

### Future Improvements
- **Horizontal scaling:** Session state in Redis/database
- **Async processing:** Background workers for classification
- **Caching:** Cache classification results by email hash
- **Webhooks:** Microsoft Graph webhooks instead of polling

---

## Error Handling Strategy

### Error Types
1. **Authentication Errors** (401, 403)
   - Redirect to `/auth/login`
   - Clear invalid tokens

2. **Graph API Errors** (429, 500)
   - Retry with exponential backoff
   - Return friendly error message

3. **Azure OpenAI Service Errors** (429, 500)
   - Fallback to rule-based classification
   - Return low confidence result

4. **Invalid Input** (400)
   - Validate request payload
   - Return clear error message

### Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Log all API calls
logger.info(f"Fetching emails: top={top}")
logger.error(f"Graph API error: {error}")
```

---

## Deployment Architecture (Future)

```
┌─────────────────────────────────────────┐
│         Azure App Service               │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │    FastAPI App (Linux/Python)     │  │
│  │    - Gunicorn + Uvicorn           │  │
│  │    - Environment variables        │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │    App Settings (Secrets)         │  │
│  │    - CLIENT_ID                    │  │
│  │    - CLIENT_SECRET                │  │
│  │    - AZURE_OPENAI_KEY             │  │
│  │    - AZURE_OPENAI_ENDPOINT        │  │
│  │    - AZURE_OPENAI_DEPLOYMENT      │  │
│  │    - AZURE_OPENAI_API_VERSION     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
           │
           │ HTTPS
           ▼
┌───────────────────────┐
│   Azure SQL Database  │  (Future)
│   or Azure Table      │
└───────────────────────┘
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Framework** | FastAPI | HTTP endpoints, routing |
| **ASGI Server** | Uvicorn + Gunicorn | Production server |
| **Authentication** | MSAL Python | OAuth 2.0 flows |
| **HTTP Client** | httpx | Graph API calls |
| **AI/ML** | Azure OpenAI Service | Email classification with GPT-4o-mini |
| **Templates** | Jinja2 | HTML rendering |
| **Configuration** | python-dotenv | Environment variables |
| **Hosting** | Azure App Service | Cloud deployment (future) |

---

## Testing Strategy

### Unit Tests
- `classifier.py` → Test prompt generation, response parsing
- `graph.py` → Mock Graph API responses
- Input sanitization functions

### Integration Tests
- OAuth flow (end-to-end)
- Graph API → Classify → Store pipeline
- Error handling (token expiry, API failures)

### Manual Testing
- Browser-based auth flow
- Dashboard functionality
- Edge cases (empty inbox, network failures)

---

## Performance Targets (POC)

| Metric | Target | Notes |
|--------|--------|-------|
| Auth flow latency | <3s | Microsoft sign-in |
| Email fetch | <1s | 10 emails |
| Single classification | <2s | Azure OpenAI Service call |
| Batch processing (100 emails) | <3min | Sequential, no parallelization |
| Dashboard load | <1s | With cached results |

---

## Future Architecture Enhancements

### Phase 2: Multi-User Support
- Session management (Flask-Login or FastAPI-Users)
- User database (PostgreSQL)
- Per-user category customization

### Phase 3: Real-Time Processing
- Microsoft Graph webhooks
- Background job queue (Celery + Redis)
- Push notifications to users

### Phase 4: Advanced Features
- Machine learning model training on user feedback
- Multi-label classification
- Smart folder auto-creation in Outlook
- Browser extension for inline classification

---

## Documentation Map

```
docs/
├── API_SPEC.md           ← Endpoint definitions
├── CLASSIFICATION_SPEC.md ← AI logic and categories
├── ARCHITECTURE.md       ← This file
├── POC_ROADMAP.md        ← Development plan
└── TESTING.md            ← Test cases (future)
```

---

## Quick Reference: Key Concepts

**OAuth 2.0 Authorization Code Flow:**
User → Login URL → Microsoft Sign-In → Callback with code → Exchange for token

**Microsoft Graph API:**
RESTful API for accessing Microsoft 365 data (emails, calendar, etc.)

**Azure OpenAI Classification:**
Few-shot learning with GPT-4o-mini to categorize emails based on content, hosted on Azure OpenAI Service

**Idempotency:**
Ensuring same email is not processed multiple times using `internetMessageId`

**In-Memory Storage:**
Python dicts stored in RAM, cleared on restart (POC only)