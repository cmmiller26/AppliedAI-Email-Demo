# AppliedAI Email Classifier (POC)

Automated email classification system using Microsoft Graph API and Azure AI Foundry with Azure OpenAI, built with FastAPI.

## Overview

This proof-of-concept demonstrates:
- **OAuth Authentication** with Microsoft Entra ID
- **Email Fetching** via Microsoft Graph API
- **AI Classification** using Azure AI Foundry with Azure OpenAI (GPT-4o-mini)
- **Automated Batch Processing** with idempotency and Outlook category assignment
- **Background Scheduler** for automatic email processing
- **Web Dashboard** for monitoring and control
- **FastAPI Web Application** hosted on Azure App Service (planned)

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd appliedai-email-classifier-poc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Azure App Registration Setup

Create an Azure App Registration for OAuth authentication:

1. **Navigate to Azure Portal**
   - Go to Azure Active Directory → App registrations
   - Click "New registration"

2. **Register Application**
   - Name: `app-appliedai-classifier-poc`
   - Supported account types: **Accounts in this organizational directory only (Single tenant)**
   - Redirect URI: (Leave blank for now, add later)
   - Click "Register"

3. **Note Application Details**
   - Copy the **Application (client) ID** → This is your `CLIENT_ID`
   - Copy the **Directory (tenant) ID** → This is your `TENANT_ID`

4. **Create Client Secret**
   - Navigate to "Certificates & secrets"
   - Click "New client secret"
   - Description: `poc-local-dev`
   - Expires: **24 months**
   - Click "Add"
   - ⚠️ **IMPORTANT**: Copy the secret **Value** immediately (not the Secret ID!)
   - Save this as `CLIENT_SECRET` in your `.env` file
   - **You cannot view this value again!**

5. **Add Redirect URI**
   - Navigate to "Authentication"
   - Click "Add a platform" → "Web"
   - Redirect URI: `http://localhost:8000/auth/callback`
   - Click "Configure"

6. **Configure API Permissions**
   - Navigate to "API permissions"
   - Click "Add a permission" → "Microsoft Graph" → "Delegated permissions"
   - Add these permissions:
     - ✅ `Mail.Read` - Read user mail
     - ✅ `Mail.ReadWrite` - Read and write user mail (for category assignment)
     - ✅ `offline_access` - Maintain access to data
   - Click "Add permissions"
   - **Optional**: Click "Grant admin consent" (requires admin rights)

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your credentials from App Registration:
# - CLIENT_ID (Application client ID from step 3)
# - TENANT_ID (Directory tenant ID from step 3)
# - CLIENT_SECRET (Secret Value from step 4)
# - AZURE_OPENAI_KEY (Azure OpenAI API key via AI Foundry)
# - AZURE_OPENAI_ENDPOINT (Azure OpenAI endpoint URL)
# - AZURE_OPENAI_DEPLOYMENT (Deployment name: gpt-4o-mini)
# - AZURE_OPENAI_API_VERSION (API version: 2024-12-01-preview)
```

### 4. Run the Application

```bash
# Start the FastAPI server
python -m uvicorn src.main:app --reload

# Open in browser
open http://localhost:8000
```

### 5. Test the System

```bash
# Authenticate
open http://localhost:8000/auth/login

# Check health
curl http://localhost:8000/health

# Fetch emails
curl http://localhost:8000/graph/fetch?top=10

# Process new emails with automatic classification and category assignment
curl -X POST http://localhost:8000/inbox/process-new
```

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ HTTP
       ▼
┌─────────────────────────┐
│   FastAPI Application   │
│                         │
│  ┌────────┐  ┌────────┐ │
│  │  Auth  │  │ Graph  │ │
│  │  Flow  │  │  API   │ │
│  └────────┘  └────────┘ │
│                         │
│  ┌────────────────────┐ │
│  │ Azure OpenAI       │ │
│  │   Classifier       │ │
│  └────────────────────┘ │
│                         │
│  ┌────────────────────┐ │
│  │ Batch Processor &  │ │
│  │ Category Assigner  │ │
│  └────────────────────┘ │
└────────┬────────────┬───┘
         │            │
         ▼            ▼
┌──────────────┐  ┌──────────────────────┐
│ Microsoft    │  │ Azure AI Foundry     │
│ Graph API    │  │ (Azure OpenAI)       │
└──────────────┘  └──────────────────────┘
```

## API Endpoints

### Dashboard & Authentication
- `GET /` - **Interactive web dashboard** with stats, category distribution, and email lists
- `GET /auth/login` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/logout` - Logout and clear token

### Email Operations
- `GET /graph/fetch` - Fetch emails from mailbox
  - Query params: `top`, `skip`, `folder` (inbox/drafts/sentitems)
- `POST /inbox/process-new` - Automatically process new emails with classification and Outlook category assignment

### Classification
- `POST /classify` - Classify individual email

### Scheduler Control
- `POST /scheduler/start` - Start background processing
- `POST /scheduler/stop` - Stop background processing
- `GET /scheduler/status` - Get scheduler status and stats

### Debug
- `GET /health` - Health check
- `GET /debug/token` - View token info
- `GET /debug/processed` - View all processed emails with classifications

## Email Categories

The system classifies emails into 6 categories and automatically assigns Outlook category labels:

| Category | Description | Color | Examples |
|----------|-------------|-------|----------|
| **URGENT** 🔴 | Time-sensitive, requires immediate action | Red | Assignment deadlines, registration deadlines |
| **ACADEMIC** 📚 | Class-related content | Blue | Lecture notes, grades, office hours |
| **ADMINISTRATIVE** 🏛️ | University services | Orange | Financial aid, housing, policy updates |
| **SOCIAL** 🎉 | Events and social activities | Green | Club meetings, campus events |
| **PROMOTIONAL** 📢 | Marketing and promotions | Purple | Sales, subscriptions, newsletters |
| **OTHER** 📦 | Everything else | Gray | Package delivery, password resets |

## Web Dashboard

### Features

Access the dashboard at `http://localhost:8000/` after authentication.

**Stats Overview:**
- Total processed emails count
- Last check time (relative: "Just now", "5m ago", "2h ago")
- Scheduler status (Running/Stopped with animated indicator)
- Average confidence percentage

**Category Distribution:**
- 6 category cards with emoji icons and counts
- Color-coded by category (red, blue, orange, green, purple, gray)
- Shows description for each category

**Email Lists:**
- Tables grouped by category showing recent emails
- Displays: subject (truncated), from address, timestamp
- Color-coded confidence badges:
  - 🟢 Green (80%+): High confidence
  - 🟡 Yellow (60-79%): Medium confidence
  - 🔴 Red (<60%): Low confidence
- Limited to 10 most recent emails per category

**Action Controls:**
- **Process New Emails** button - Triggers batch processing with loading state
- **View Debug Data** link - Opens detailed JSON view
- **Auto-refresh** checkbox - Reloads page every 30 seconds
- **Logout** button - Clears token and returns to login screen

**Technologies:**
- Jinja2 templates for server-side rendering
- Tailwind CSS for responsive styling
- Vanilla JavaScript for interactivity
- University of Iowa branding

## Automated Processing Features

### Batch Processing (/inbox/process-new)
- Fetches new emails since last check (or all on first run)
- Classifies each email using Azure OpenAI
- Assigns Outlook category labels automatically
- Ensures idempotency using `internetMessageId`
- Returns summary with category distribution

### Background Scheduler
- Automatically processes new emails at configurable intervals (default: 60s)
- Runs in background thread using APScheduler
- Auto-starts on application startup
- Control via REST API or environment variables
- Graceful error handling (token expiry, API failures)

### Outlook Category Assignment
Emails are automatically tagged with colored category labels in Outlook:
- **Non-destructive**: Emails stay in inbox
- **Visual**: Color-coded labels for quick recognition
- **Cross-platform**: Works in Outlook desktop, web, and mobile
- **Multi-category support**: One email can have multiple categories

### Idempotency
- Each email is processed exactly once
- Uses `internetMessageId` as unique identifier
- Safe to run `/inbox/process-new` multiple times
- Tracks `last_check_time` to only process new emails

## Testing

See **[docs/TESTING.md](docs/TESTING.md)** for complete testing guide.

### Quick Test

```bash
# Authenticate
open http://localhost:8000/auth/login

# Get processing stats
curl http://localhost:8000/

# Process all new emails
curl -X POST http://localhost:8000/inbox/process-new | python -m json.tool

# View processed emails
curl http://localhost:8000/debug/processed | python -m json.tool

# Run again (should process 0 emails - idempotency test)
curl -X POST http://localhost:8000/inbox/process-new | python -m json.tool

# Check Outlook to see category labels!
open https://outlook.com
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/API_SPEC.md](docs/API_SPEC.md) | Endpoint definitions and request/response formats |
| [docs/CLASSIFICATION_SPEC.md](docs/CLASSIFICATION_SPEC.md) | AI categories, prompts, and classification logic |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, flow diagrams, data models |
| [docs/AZURE_AI_FOUNDRY.md](docs/AZURE_AI_FOUNDRY.md) | Azure AI Foundry setup and features guide |
| [docs/SECURITY.md](docs/SECURITY.md) | Security best practices and compliance guide |
| [docs/TESTING.md](docs/TESTING.md) | Testing guide and workflow |
| [docs/POC_ROADMAP.md](docs/POC_ROADMAP.md) | Development plan and progress |
| [CLAUDE.md](CLAUDE.md) | AI assistant instructions |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Web Framework** | FastAPI |
| **ASGI Server** | Uvicorn + Gunicorn |
| **Authentication** | MSAL (Microsoft Authentication Library) |
| **HTTP Client** | httpx |
| **AI Platform** | Azure AI Foundry |
| **AI Model** | Azure OpenAI Service (GPT-4o-mini) via AI Foundry |
| **Date Parsing** | python-dateutil |
| **Deployment** | Azure App Service (planned) |

## Environment Variables

| Variable | Description | Example | Where to Find |
|----------|-------------|---------|---------------|
| `CLIENT_ID` | Azure App Registration client ID | `edd9d097-4e9f-...` | App Registration → Overview |
| `TENANT_ID` | Azure tenant (directory) ID | `d2ecbd81-bc7c-...` | App Registration → Overview |
| `CLIENT_SECRET` | Client secret value | `secret123...` | Certificates & secrets (Description: `poc-local-dev`) |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | `abc123...` | AI Foundry Project → Settings |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://aih-appliedai-classifier-poc.cognitiveservices.azure.com/` | AI Foundry Project → Settings |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | `gpt-4o-mini` | AI Foundry Project → Deployments |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-12-01-preview` | Use recommended version |
| `REDIRECT_URI` | OAuth redirect URI | `http://localhost:8000/auth/callback` | Must match App Registration |

## Project Structure

```
appliedai-email-classifier-poc/
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py             # Main FastAPI application
│   ├── graph.py            # Microsoft Graph API integration
│   ├── classifier.py       # Azure OpenAI classification logic
│   └── scheduler.py        # Background email processing scheduler
├── templates/              # Web dashboard templates
│   └── dashboard.html      # Main dashboard UI
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── docs/                   # Documentation
│   ├── API_SPEC.md
│   ├── CLASSIFICATION_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── TESTING.md
│   └── POC_ROADMAP.md
└── tests/                  # Test utilities
    ├── __init__.py
    ├── send_test_emails.py
    └── data/
        └── test_emails.md
```

## Development Status

**POC COMPLETE: 2025-11-04** ✅

### ✅ Completed (Phases 1-6):
- OAuth authentication flow with Microsoft Entra ID
- Microsoft Graph API integration
- Email fetching from inbox/drafts/sentitems
- Azure OpenAI Service classification via AI Foundry
- **Automated batch processing with idempotency**
- **Automatic Outlook category assignment**
- **Background scheduler with APScheduler**
- **Professional web dashboard with stats and controls**
- **In-memory storage (processed_emails, last_check_time)**
- Debug endpoints for development
- Test email generation script
- Comprehensive documentation

### 📋 Future Enhancements (Phases 7-8):
- **Performance Optimization**
  - Parallel processing with asyncio (5-10 workers)
  - Azure OpenAI Batch API for overnight processing
  - Persistent storage (Azure SQL or Table Storage)
- **Production Readiness**
  - Token refresh logic
  - Multi-user support with session management
  - Database migration from in-memory storage
  - Azure App Service deployment
  - Enhanced monitoring and logging
  - Compliance with IT-15 policy

## Known Limitations (POC)

- **Sequential processing**: Emails classified one at a time (~1.5-2.5s each)
- **In-memory storage**: Data lost on server restart
- **Single-user**: One token per server instance
- **No token refresh**: Must re-authenticate when token expires (~1 hour)
- **No persistence**: Processed emails not saved to database
- **Batch size limit**: Processes up to 50 emails per run

These will be addressed in future phases (see Future Enhancements below).

## Future Enhancements

### Performance Optimization
- **Parallel Processing**: Use asyncio with ThreadPoolExecutor (5-10 concurrent workers)
  - Target: 10 emails in ~5 seconds (currently ~20 seconds)
  - Implementation: `asyncio.gather()` with semaphore for rate limiting
- **Azure OpenAI Batch API**: For overnight batch processing of 1000+ emails
  - Lower cost (~50% discount)
  - Process large backlogs efficiently

### Persistent Storage
- **Azure SQL Database**: Structured storage with SQL queries
  - Table: `processed_emails` with indexed `internet_message_id`
  - Benefits: ACID guarantees, complex queries, reporting
- **Azure Table Storage**: NoSQL key-value store
  - PartitionKey: category, RowKey: message_id
  - Benefits: Lower cost, high throughput, simple schema
- **Redis Cache**: Fast in-memory cache with persistence
  - Benefits: Sub-millisecond lookups, pub/sub for real-time updates

### Enhanced Features
- Token refresh logic for uninterrupted operation
- Multi-user support with per-user category preferences
- Custom category definitions (user-defined categories)
- Confidence thresholds (only assign category if confidence > 0.7)
- Multi-category support (one email, multiple categories)
- Performance monitoring and analytics dashboard

## Security Notes

- Never commit `.env` file or secrets to git
- Use OAuth flows only (no password storage)
- HTTPS required in production
- Tokens stored server-side (not in cookies)
- CSRF protection via state parameter
- Mail.ReadWrite scope required for category assignment

## Troubleshooting

### Authentication Issues

**Problem:** Can't authenticate / "Invalid client secret"
**Solution:**
1. Verify `CLIENT_ID`, `TENANT_ID`, `CLIENT_SECRET` in `.env`
2. Check client secret hasn't expired (24-month expiration)
3. Ensure client secret **Value** was copied (not Secret ID)
4. Recreate client secret if needed (Description: `poc-local-dev`)

**Problem:** "Redirect URI mismatch"
**Solution:**
1. Check `REDIRECT_URI` in `.env` matches Azure App Registration
2. Azure Portal → App Registration → Authentication → Web → Redirect URIs
3. Must be exactly: `http://localhost:8000/auth/callback`

**Problem:** "Insufficient permissions" error
**Solution:**
1. Azure Portal → App Registration → API permissions
2. Ensure these are added:
   - Mail.Read
   - Mail.ReadWrite
   - offline_access
3. Grant admin consent if available

**Problem:** Token expired
**Solution:**
- POC: Re-authenticate at `http://localhost:8000/auth/login`
- Access tokens expire after ~1 hour
- Phase 8 will implement automatic refresh

### Client Secret Management

**Problem:** "I lost my client secret value"
**Solution:**
- You cannot retrieve the original value
- Create a new client secret:
  1. Azure Portal → App Registration → Certificates & secrets
  2. New client secret
  3. Description: `poc-local-dev-2` (or similar)
  4. Copy value immediately
  5. Update `.env` file
  6. Delete old secret

**Problem:** "Client secret expired"
**Solution:**
- Set expiration to 24 months when creating
- Set calendar reminder to rotate before expiration
- For rotation: Create new secret → Update `.env` → Delete old secret

### Email Fetching Issues

**Problem:** 401 Unauthorized
**Solution:** Re-authenticate to get fresh token

**Problem:** Empty results
**Solution:** Check folder parameter and verify emails exist

### Processing Issues

**Problem:** /inbox/process-new returns 0 emails
**Solution:** This is normal if you've already processed all emails (idempotency working!)

**Problem:** Categories not showing in Outlook
**Solution:**
1. Verify Mail.ReadWrite scope in token: `curl http://localhost:8000/debug/token`
2. Check server logs for "Successfully assigned category" messages
3. Refresh Outlook web/desktop

### Test Email Issues

**Problem:** Spam filter blocking
**Solution:** Use `--save-to-drafts` instead of sending

See [docs/TESTING.md](docs/TESTING.md) for more troubleshooting.

## Contributing

This is a proof-of-concept for internal use. For questions or issues, contact the development team.

## License

Internal use only - University of Iowa

## Contact

For questions about this POC, see documentation or contact the project team.
