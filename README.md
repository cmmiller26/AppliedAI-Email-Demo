# Email Classification POC

Automated email classification system using Microsoft Graph API and Azure OpenAI Service, built with FastAPI.

## Overview

This proof-of-concept demonstrates:
- **OAuth Authentication** with Microsoft Entra ID
- **Email Fetching** via Microsoft Graph API
- **AI Classification** using Azure OpenAI Service with GPT-4o-mini
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
# - AZURE_OPENAI_API_VERSION (API version: 2024-02-15-preview)
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

### Classification
- `POST /classify` - Classify individual email
- `POST /inbox/process-new` - Process new emails

### Debug
- `GET /health` - Health check
- `GET /debug/token` - View token info
- `GET /debug/processed` - View processed emails

## Email Categories

The system classifies emails into 6 categories:

| Category | Description | Examples |
|----------|-------------|----------|
| **URGENT** | Time-sensitive, requires immediate action | Assignment deadlines, registration deadlines |
| **ACADEMIC** | Class-related content | Lecture notes, grades, office hours |
| **ADMINISTRATIVE** | University services | Financial aid, housing, policy updates |
| **SOCIAL** | Events and social activities | Club meetings, campus events |
| **PROMOTIONAL** | Marketing and promotions | Sales, subscriptions, newsletters |
| **OTHER** | Everything else | Package delivery, password resets |

## Testing

See **[docs/TESTING.md](docs/TESTING.md)** for complete testing guide.

### Quick Test

```bash
# Get token
TOKEN=$(curl -s http://localhost:8000/debug/token | jq -r .access_token)

# Create test emails in Inbox (with mock senders!)
python tests/send_test_emails.py --token "$TOKEN"

# Fetch and verify
curl "http://localhost:8000/graph/fetch?folder=inbox&top=20"
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
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version | `2024-02-15-preview` |
| `REDIRECT_URI` | OAuth redirect URI | `http://localhost:8000/auth/callback` |

## Project Structure

```
appliedai-demo/
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py             # Main FastAPI application
│   ├── graph.py            # Microsoft Graph API integration
│   └── classifier.py       # Azure OpenAI classification logic (future)
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

✅ Completed:
- OAuth authentication flow
- Microsoft Graph API integration
- Email fetching from inbox/drafts/sentitems
- Azure OpenAI Service classification endpoint
- Test email generation script
- Folder-based email reading (drafts for testing)

🚧 In Progress:
- Automated batch processing
- Web dashboard UI

📋 Planned:
- Token refresh logic
- Multi-user support
- Persistent storage
- Azure deployment

## Known Limitations (POC)

- **In-memory storage**: Data lost on server restart
- **Single-user**: One token per server instance
- **No token refresh**: Must re-authenticate when token expires (~1 hour)
- **No persistence**: Processed emails not saved to database

These will be addressed in Phase 2 after POC validation.

## Security Notes

- Never commit `.env` file or secrets to git
- Use OAuth flows only (no password storage)
- HTTPS required in production
- Tokens stored server-side (not in cookies)
- CSRF protection via state parameter

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
