# Email Classification POC

Automated email classification system using Microsoft Graph API and Azure OpenAI Service, built with FastAPI.

## Overview

This proof-of-concept demonstrates:
- **OAuth Authentication** with Microsoft Entra ID
- **Email Fetching** via Microsoft Graph API
- **AI Classification** using Azure OpenAI Service with GPT-4o-mini
- **Automated Batch Processing** with idempotency and Outlook category assignment
- **FastAPI Web Application** hosted on Azure App Service (planned)

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd appliedai-demo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your credentials:
# - CLIENT_ID (Azure Entra app ID)
# - CLIENT_SECRET (Azure app secret)
# - TENANT_ID (Azure tenant ID)
# - AZURE_OPENAI_KEY (Azure OpenAI Service API key)
# - AZURE_OPENAI_ENDPOINT (Azure OpenAI endpoint URL)
# - AZURE_OPENAI_DEPLOYMENT (Deployment name: gpt-4o-mini)
# - AZURE_OPENAI_API_VERSION (API version: 2024-10-21)
```

### 3. Run the Application

```bash
# Start the FastAPI server
python -m uvicorn src.main:app --reload

# Open in browser
open http://localhost:8000
```

### 4. Test the System

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
│  ┌────────┐  ┌────────┐│
│  │  Auth  │  │ Graph  ││
│  │  Flow  │  │  API   ││
│  └────────┘  └────────┘│
│                         │
│  ┌────────────────────┐│
│  │ Azure OpenAI       ││
│  │   Classifier       ││
│  └────────────────────┘│
│                         │
│  ┌────────────────────┐│
│  │ Batch Processor &  ││
│  │ Category Assigner  ││
│  └────────────────────┘│
└────────┬────────────┬───┘
         │            │
         ▼            ▼
┌──────────────┐  ┌──────────────┐
│ Microsoft    │  │ Azure OpenAI │
│ Graph API    │  │   Service    │
└──────────────┘  └──────────────┘
```

## API Endpoints

### Authentication
- `GET /auth/login` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler

### Email Operations
- `GET /graph/fetch` - Fetch emails from mailbox
  - Query params: `top`, `skip`, `folder` (inbox/drafts/sentitems)
- `POST /inbox/process-new` - **NEW!** Automatically process new emails with classification and Outlook category assignment

### Classification
- `POST /classify` - Classify individual email

### Debug
- `GET /health` - Health check
- `GET /` - Dashboard with processing statistics
- `GET /debug/token` - View token info
- `GET /debug/processed` - **NEW!** View all processed emails with classifications

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

## Automated Processing Features

### Batch Processing (/inbox/process-new)
- Fetches new emails since last check (or all on first run)
- Classifies each email using Azure OpenAI
- Assigns Outlook category labels automatically
- Ensures idempotency using `internetMessageId`
- Returns summary with category distribution

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
| **AI/ML** | Azure OpenAI Service (GPT-4o-mini) |
| **Date Parsing** | python-dateutil |
| **Deployment** | Azure App Service (planned) |

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CLIENT_ID` | Azure Entra app client ID | `edd9d097-4e9f-...` |
| `TENANT_ID` | Azure tenant ID | `d2ecbd81-bc7c-...` |
| `CLIENT_SECRET` | Azure app secret | `secret123...` |
| `AZURE_OPENAI_KEY` | Azure OpenAI Service API key | `abc123...` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://appliedai-openai.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment name | `gpt-4o-mini` |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version | `2024-10-21` |
| `REDIRECT_URI` | OAuth redirect URI | `http://localhost:8000/auth/callback` |

## Project Structure

```
appliedai-demo/
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py             # Main FastAPI application
│   ├── graph.py            # Microsoft Graph API integration
│   └── classifier.py       # Azure OpenAI classification logic
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

**Phase 5 Completed: 2025-10-31** ✅

### ✅ Completed:
- OAuth authentication flow with Microsoft Entra ID
- Microsoft Graph API integration
- Email fetching from inbox/drafts/sentitems
- Azure OpenAI Service classification endpoint
- **Automated batch processing (/inbox/process-new)**
- **Idempotency using internetMessageId**
- **Automatic Outlook category assignment**
- **In-memory storage (processed_emails, last_check_time)**
- **Debug endpoint for viewing processed emails**
- Test email generation script
- Folder-based email reading (drafts for testing)

### 🚧 In Progress:
- Web dashboard UI

### 📋 Planned (Future Phases):
- **Performance Optimization (Phase 7)**
  - Parallel processing with asyncio (5-10 workers)
  - Azure OpenAI Batch API for overnight processing
  - Persistent storage (Azure SQL or Table Storage)
- **Production Readiness (Phase 8)**
  - Token refresh logic
  - Multi-user support with session management
  - Database migration from in-memory storage
  - Azure deployment and monitoring
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

**Problem:** Can't authenticate
**Solution:** Check `CLIENT_ID`, `TENANT_ID`, `CLIENT_SECRET` in `.env`

**Problem:** Token expired
**Solution:** Re-authenticate at `http://localhost:8000/auth/login`

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
