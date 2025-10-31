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

### 1. FastAPI Application (`src/main.py`)

**Responsibilities:**
- HTTP request handling
- Route management
- Session/token management (in-memory for POC)
- Error handling and logging

**Key Modules:**
- `src/main.py` - Main application entry point
- `src/graph.py` - Microsoft Graph API integration
- `src/classifier.py` - Azure OpenAI classification logic (future)
- `templates/` - HTML templates for dashboard (future)

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

### Processed Email Record (In-Memory Storage)
```python
processed_emails = {
    "<CAB...@mail.gmail.com>": {  # Key: internetMessageId
        "category": "ACADEMIC",
        "confidence": 0.92,
        "timestamp": "2025-10-31T12:00:00Z",
        "subject": "CS 4980 Assignment",
        "from": "john-smith@uiowa.edu"
    }
}

last_check_time = datetime(2025, 10, 31, 12, 0, 0)  # Global variable
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

## Outlook Category Assignment

### Category Assignment Flow

```
FastAPI         Graph API             Outlook
   │                │                    │
   │ Classify email │                    │
   │ category="URGENT"                   │
   │                │                    │
   │ GET /messages/{id}                  │
   │ $select=categories                  │
   ├───────────────►│                    │
   │                │                    │
   │ Return current │                    │
   │ categories: [] │                    │
   │◄───────────────┤                    │
   │                │                    │
   │ PATCH /messages/{id}                │
   │ {categories:["URGENT"]}             │
   ├───────────────►│                    │
   │                │  Update email      │
   │                ├───────────────────►│
   │                │                    │
   │ 200 OK         │                    │
   │◄───────────────┤                    │
```

### Implementation Details

**Function:** `assign_category_to_message(access_token, message_id, category)`

Located in: `src/graph.py`

**Process:**
1. GET current categories from email (preserves existing)
2. Add new category if not already present
3. PATCH email with updated categories array
4. Outlook automatically creates category if doesn't exist

**Requirements:**
- OAuth scope: `Mail.ReadWrite` (required for PATCH operations)
- message_id: Graph API message ID (not internetMessageId)
- Category names are case-sensitive

**Error Handling:**
- If category assignment fails, email is still marked as processed
- Logs error but continues processing other emails
- Returns success=True/False

---

## State Management (POC)

### Global State Variables
```python
# In-memory storage (resets on server restart)
user_tokens = {}              # OAuth tokens
processed_emails = {}         # Classification results
last_check_time = None        # Timestamp of last email fetch
```

### Limitations (POC) - Phase 5 Complete (2025-10-31)
- **No persistence:** Data lost on restart (in-memory only)
- **Single-user only:** One token per server instance
- **No token refresh:** Must re-authenticate after expiry (~1 hour)
- **Sequential processing:** Emails processed one at a time (~1.5-2.5s per email)
- **Batch size limit:** Processes up to 50 emails per run
- **No retry logic:** Failed classifications are skipped

### Future: Production State (Phases 7-8)
- **Database:** PostgreSQL, Azure SQL, or Azure Table Storage
- **Cache:** Redis for session tokens and fast lookups
- **Blob Storage:** Azure Blob for processed email metadata
- **Parallel Processing:** asyncio with 5-10 concurrent workers
- **Token Refresh:** Automatic refresh token flow
- **Multi-user:** Session management with per-user storage

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

### Current Limitations (Phase 5)
- In-memory storage → Single server only
- Sequential processing → One email at a time (~1.5-2.5s each)
- No caching → Repeated API calls for category assignment
- Synchronous batch processing → Blocks until all emails processed

### Future Improvements (Phases 7-8)

#### 1. Parallel Processing with asyncio
**Implementation:**
```python
async def process_emails_parallel(emails, access_token, max_workers=5):
    semaphore = asyncio.Semaphore(max_workers)

    async def process_with_limit(email):
        async with semaphore:
            return await classify_and_assign(email, access_token)

    results = await asyncio.gather(
        *[process_with_limit(email) for email in emails],
        return_exceptions=True
    )
    return results
```

**Benefits:**
- 5-10x speedup (10 emails in ~5s instead of ~20s)
- Better resource utilization
- Rate limit control with semaphore

**Challenges:**
- Azure OpenAI rate limits (need quota management)
- Graph API throttling (429 responses)
- Error handling for partial failures

#### 2. Azure OpenAI Batch API
**Use Case:** Overnight processing of 1000+ emails

**Benefits:**
- ~50% cost discount
- No rate limit concerns
- Process large backlogs efficiently

**Implementation:**
```python
# Submit batch job
batch_job = await submit_batch_classification(emails)

# Poll for completion (or use webhooks)
while batch_job.status != "completed":
    await asyncio.sleep(60)
    batch_job = await get_batch_status(batch_job.id)

# Process results
results = await get_batch_results(batch_job.id)
```

#### 3. Persistent Storage Options

**Option A: Azure SQL Database**
```sql
CREATE TABLE processed_emails (
    internet_message_id VARCHAR(255) PRIMARY KEY,
    graph_message_id VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    confidence DECIMAL(3,2),
    subject NVARCHAR(MAX),
    from_email VARCHAR(255),
    processed_at DATETIME2 DEFAULT GETUTCDATE(),
    INDEX idx_processed_at (processed_at),
    INDEX idx_category (category)
);
```

**Benefits:**
- ACID guarantees
- Complex queries for analytics
- Familiar SQL interface
- ~$5-10/month for basic tier

**Option B: Azure Table Storage**
```python
# PartitionKey: category, RowKey: internet_message_id
table_client.upsert_entity({
    "PartitionKey": "URGENT",
    "RowKey": "<CAB123@mail.gmail.com>",
    "subject": "Assignment Due",
    "confidence": 0.95,
    "timestamp": datetime.utcnow()
})
```

**Benefits:**
- Lower cost (~$1/month)
- High throughput (thousands of ops/sec)
- Simple key-value model
- No schema management

**Option C: Redis Cache**
```python
redis_client.hset(
    "processed_emails",
    "<CAB123@mail.gmail.com>",
    json.dumps({
        "category": "URGENT",
        "confidence": 0.95,
        "timestamp": "2025-10-31T12:00:00Z"
    })
)
```

**Benefits:**
- Sub-millisecond lookups
- Pub/sub for real-time updates
- TTL for auto-expiration
- ~$10-20/month for basic tier

#### 4. Horizontal Scaling
- **Load balancer:** Azure Application Gateway
- **Session state:** Move to Redis/SQL
- **Stateless app servers:** Multiple FastAPI instances
- **Message queue:** Azure Service Bus for background jobs

#### 5. Caching Strategy
- **Classification results:** Cache by email content hash (dedupe)
- **Category assignments:** Cache recent assignments
- **Graph API responses:** Cache user profile/folders
- **TTL:** 1 hour for classifications, 24 hours for metadata

#### 6. Webhooks Instead of Polling
**Microsoft Graph Webhooks:**
```python
# Subscribe to inbox changes
subscription = await graph_client.subscriptions.post({
    "changeType": "created",
    "notificationUrl": "https://your-app.com/webhooks/email-received",
    "resource": "/me/mailFolders('inbox')/messages",
    "expirationDateTime": datetime.utcnow() + timedelta(days=3)
})
```

**Benefits:**
- Real-time processing (no polling delay)
- Lower API usage
- Better user experience

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

## Performance Targets

### Current Performance (Phase 5 - Sequential)

| Metric | Current | Notes |
|--------|---------|-------|
| Auth flow latency | ~2-3s | Microsoft sign-in |
| Email fetch | <1s | 50 emails from Graph API |
| Single classification | 1-2s | Azure OpenAI Service call |
| Category assignment | 200-500ms | 1 GET + 1 PATCH to Graph API |
| **Total per email** | **1.5-2.5s** | Classification + category assignment |
| Batch processing (10 emails) | ~20s | Sequential processing |
| Batch processing (50 emails) | ~2min | Sequential processing |
| Dashboard load | <500ms | In-memory data retrieval |

### Future Performance (Phase 7 - Parallel)

| Metric | Target | Improvement | Implementation |
|--------|--------|-------------|----------------|
| Batch processing (10 emails) | ~5s | 4x faster | asyncio with 5 workers |
| Batch processing (50 emails) | ~25s | 5x faster | asyncio with 10 workers |
| Batch processing (100 emails) | ~50s | 4x faster | asyncio with 10 workers + rate limiting |
| Overnight batch (1000+ emails) | N/A | Cost efficient | Azure OpenAI Batch API |
| Database lookup | <10ms | Fast idempotency check | Redis or indexed SQL |

### Bottlenecks and Optimization Opportunities

1. **Azure OpenAI API** (~1-2s per call)
   - Solution: Parallel processing with rate limit management
   - Alternative: Batch API for large jobs

2. **Graph API Category Assignment** (~200-500ms per email)
   - Solution: Batch PATCH requests (if Graph API supports)
   - Alternative: Queue assignments for async processing

3. **Sequential Processing** (no concurrency)
   - Solution: asyncio.gather() with semaphore
   - Expected: 5-10x speedup

4. **In-Memory Lookups** (fast, but not persistent)
   - Solution: Redis cache or indexed database
   - Expected: <10ms lookups even after restart

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