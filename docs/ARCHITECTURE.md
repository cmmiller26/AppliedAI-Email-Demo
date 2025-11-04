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
┌──────────────┐      ┌──────────────────────┐
│  Microsoft   │      │ Azure AI Foundry     │
│  Graph API   │      │ (Azure OpenAI)       │
│ (Entra ID)   │      │  (GPT-4o-mini)       │
└──────────────┘      └──────────────────────┘
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
- `src/classifier.py` - Azure OpenAI classification logic
- `src/scheduler.py` - Background email processing scheduler
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

**Azure OpenAI Request (via AI Foundry):**
```python
from openai import AzureOpenAI

# Initialize client - works with AI Foundry (no code changes needed!)
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

### 6. Background Scheduler (`src/scheduler.py`)

The scheduler provides automatic email processing at configurable intervals using APScheduler.

**Architecture:**
```
┌───────────────────────────────────────────────────────┐
│              FastAPI Application                      │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │         APScheduler (Background Thread)         │  │
│  │                                                 │  │
│  │  ┌───────────────────────────────────────────┐  │  │
│  │  │    IntervalTrigger (every 60s)            │  │  │
│  │  │                                           │  │  │
│  │  │   Calls process_new_emails_internal()     │  │  │
│  │  │                  ↓                        │  │  │
│  │  │   ┌─────────────────────────────────┐     │  │  │
│  │  │   │  1. Get valid access token      │     │  │  │
│  │  │   │  2. Fetch new emails            │     │  │  │
│  │  │   │  3. Filter unprocessed emails   │     │  │  │
│  │  │   │  4. Classify with Azure OpenAI  │     │  │  │
│  │  │   │  5. Assign Outlook categories   │     │  │  │
│  │  │   │  6. Mark as processed           │     │  │  │
│  │  │   └─────────────────────────────────┘     │  │  │
│  │  └───────────────────────────────────────────┘  │  │
│  │                                                 │  │
│  │  Control via REST API:                          │  │
│  │  • POST /scheduler/start?interval=60            │  │
│  │  • POST /scheduler/stop                         │  │
│  │  • GET  /scheduler/status                       │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

**Key Features:**
- **Auto-start**: Scheduler starts automatically on app startup (configurable via `SCHEDULER_AUTO_START`)
- **Configurable interval**: 10-3600 seconds (default: 60s via `POLLING_INTERVAL`)
- **Error handling**: Gracefully handles token expiration, API errors without crashing
- **Idempotency**: Respects `internetMessageId` tracking - never processes same email twice
- **Status tracking**: Tracks last run time, next run time, and results
- **Dynamic control**: Start/stop/reconfigure without restarting app

**Scheduler Configuration:**
```python
# Environment variables
POLLING_INTERVAL=60           # Interval in seconds (default: 60)
SCHEDULER_AUTO_START=true     # Auto-start on app startup (default: true)
```

**Error Handling Strategy:**
```python
async def _job_wrapper():
    try:
        # Process emails
        result = await processing_function()
        logger.info(f"[Scheduler] Processed {result['processed']} emails")
    except Exception as e:
        logger.error(f"[Scheduler] Error: {e}")
        # Don't crash - continue scheduling
        if "Token expired" in str(e):
            logger.warning("[Scheduler] Skipping due to expired token")
```

**Integration with Main App:**
```python
# Startup
@app.on_event("startup")
async def startup_event():
    scheduler.initialize_scheduler(scheduler_processing_wrapper)
    if os.getenv("SCHEDULER_AUTO_START", "true") == "true":
        scheduler.start_scheduler(interval_seconds=60)

# Shutdown
@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown_scheduler()
```

---

## Azure AI Foundry Integration

### Overview

This project uses **Azure AI Foundry** (formerly Azure AI Studio) as the centralized platform for AI operations. Azure AI Foundry provides a unified hub for managing Azure OpenAI deployments along with additional features like monitoring, evaluation, and Prompt Flow.

### Why Azure AI Foundry?

Microsoft recommends Azure AI Foundry for building production AI applications because it provides:

1. **Unified Management**: Hub → Project → Resources hierarchy for better organization
2. **Built-in Monitoring**: Track token usage, performance, latency, and costs
3. **Evaluation Tools**: Test model accuracy with datasets
4. **Prompt Flow**: Visual designer for complex AI workflows (future use)
5. **Model Catalog**: Easy access to multiple AI models
6. **Content Safety**: Built-in filtering and moderation tools
7. **Better Cost Visibility**: Track spending across projects

### Current Configuration

```
┌─────────────────────────────────────────┐
│      Azure AI Foundry Hub               │
│  (aih-appliedai-classifier-poc)         │
│           Region: North Central US      │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │   Azure AI Foundry Project        │  │
│  │  (aip-appliedai-classifier-poc)   │  │
│  │                                   │  │
│  │  Connected Resources:             │  │
│  │  • Azure OpenAI Service           │  │
│  │  • Monitoring & Evaluation        │  │
│  │  • Prompt Flow (optional)         │  │
│  └───────────────────────────────────┘  │
└──────────┬──────────────────────────────┘
           │
           ▼
    ┌─────────────────┐
    │   FastAPI App   │
    │   (Your Code)   │
    └─────────────────┘
```

**Resources:**
- **Hub**: `aih-appliedai-classifier-poc` (North Central US)
- **Project**: `aip-appliedai-classifier-poc`
- **Model Deployment**: `gpt-4o-mini`

### Code Compatibility

✅ **No code changes needed!** The existing `openai` Python SDK works seamlessly with AI Foundry.

The Azure OpenAI endpoint provided by AI Foundry uses the same API format:

```python
# This code works with both direct Azure OpenAI and AI Foundry
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  # Points to AI Foundry's OpenAI resource
)
```

### Benefits Over Direct Azure OpenAI

| Feature | Direct Azure OpenAI | Azure AI Foundry |
|---------|-------------------|------------------|
| Model Deployment | ✅ | ✅ |
| Token Usage Tracking | Basic | Advanced with dashboards |
| Evaluation Datasets | ❌ | ✅ Built-in |
| Prompt Flow | ❌ | ✅ Visual designer |
| Content Safety | Manual setup | ✅ Built-in |
| Multi-model Management | Separate resources | ✅ Unified catalog |
| Cost Tracking | Azure billing only | ✅ Project-level insights |
| A/B Testing | Manual | ✅ Built-in tools |

### Future Enhancements (Phase 7-8)

#### 1. Prompt Flow Integration
Use visual designer to build and test classification pipelines without code.

#### 2. Evaluation Datasets
Create test sets to measure classification accuracy over time:
- Upload labeled test emails
- Run batch evaluations
- Track accuracy metrics
- Compare prompt variations

#### 3. A/B Testing
Compare different prompts or models to optimize performance:
- Test multiple system prompts
- Compare GPT-4o vs GPT-4o-mini
- Measure accuracy and cost trade-offs

#### 4. Content Safety
Apply filters to detect inappropriate content in emails:
- Profanity detection
- Harassment identification
- PII detection and redaction

#### 5. Advanced Monitoring
Set up alerts for:
- High latency (>3s per classification)
- Error rate spikes
- Unusual token usage patterns
- Budget thresholds

---

## Authentication Architecture

### Azure App Registration

**Resource Name**: `app-appliedai-classifier-poc`

The application uses Azure App Registration (Microsoft Entra ID) for OAuth 2.0 authentication.

#### Configuration Details

| Setting | Value |
|---------|-------|
| Name | `app-appliedai-classifier-poc` |
| Account Types | Single tenant (University of Iowa only) |
| Redirect URI | `http://localhost:8000/auth/callback` (POC) |
| Client Secret | Description: `poc-local-dev`, Expires: 24 months |

#### API Permissions (Microsoft Graph)

| Permission | Type | Purpose |
|------------|------|---------|
| `Mail.Read` | Delegated | Read user's email messages |
| `Mail.ReadWrite` | Delegated | Assign Outlook categories to emails |
| `offline_access` | Delegated | Refresh tokens for persistent access |

#### OAuth 2.0 Flow

```
User → Login → Microsoft Entra ID → Authorization
                                    ↓
                              Code Exchange
                                    ↓
                            Access Token + Refresh Token
                                    ↓
                        Stored in server memory (POC)
```

### Client Secret Management

#### POC Strategy (Current)
```
Storage:      .env file (local, gitignored)
Description:  poc-local-dev
Expiration:   24 months
Rotation:     Manual (calendar reminder)
Access:       Single developer
```

#### Production Strategy (Phase 8)
```
Storage:      Azure Key Vault
Description:  prod-{environment}
Expiration:   6 months (enforced)
Rotation:     Automated with Azure Functions
Access:       App Service managed identity
```

### Security Considerations

1. **POC Environment:**
   - ✅ OAuth state parameter prevents CSRF
   - ✅ Tokens stored server-side (not in cookies)
   - ✅ Single tenant (University directory only)
   - ⚠️ No token encryption at rest (acceptable for POC)
   - ⚠️ No automatic token refresh (must re-authenticate)

2. **Production Requirements (Phase 8):**
   - Use Azure Key Vault for secrets
   - Implement automatic token refresh
   - Enable audit logging
   - Configure network restrictions
   - Comply with IT-15 policy
   - Add multi-factor authentication

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
| **AI Platform** | Azure AI Foundry | Centralized AI management, monitoring, evaluation |
| **AI Model** | Azure OpenAI Service (GPT-4o-mini) | Email classification via AI Foundry |
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

**Azure AI Foundry Classification:**
Few-shot learning with GPT-4o-mini to categorize emails based on content, hosted on Azure AI Foundry with Azure OpenAI Service

**Idempotency:**
Ensuring same email is not processed multiple times using `internetMessageId`

**In-Memory Storage:**
Python dicts stored in RAM, cleared on restart (POC only)