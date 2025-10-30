# AI Assistant Guide

## Project Intent

Build a secure, policy-compliant email automation service:

- Authenticate via Microsoft Entra ID (OAuth), never HawkID passwords
- Read mail via Microsoft Graph
- Classify messages with Azure OpenAI
- Host on Azure App Service (Python 3.12, Linux), later enabling webhook or polling behavior

## Non-Negotiables

- Never commit secrets (`CLIENT_SECRET`, `AZURE_OPENAI_KEY`)
- Use OAuth flows only (Device Code for local testing, Auth Code for web deployment)
- Ensure endpoints are idempotent; do not reprocess the same `internetMessageId`

## Documentation Structure

**All detailed specifications live in `docs/` folder. Reference these when implementing:**

| Document | Purpose | When to Reference |
|----------|---------|-------------------|
| `docs/API_SPEC.md` | Endpoint definitions, request/response formats | Implementing any endpoint |
| `docs/CLASSIFICATION_SPEC.md` | AI categories, prompts, Azure OpenAI configuration | Building classifier logic |
| `docs/ARCHITECTURE.md` | System design, flow diagrams, data models | Understanding component interactions |
| `docs/TESTING.md` | Testing workflow, test email script usage | Testing classification system |
| `docs/POC_ROADMAP.md` | Development plan and task breakdown | Planning daily work |
| `Enterprise_Authentication...pdf` | University IT security policies | Production compliance (not POC) |

## Tech Stack

- **Framework**: FastAPI + Uvicorn + Gunicorn
- **Auth**: MSAL for Python (`PublicClientApplication` for local, `ConfidentialClientApplication` for web)
- **HTTP Client**: httpx for Graph API calls
- **AI**: Azure OpenAI Service (gpt-4o-mini)
- **Scheduling** (Optional): APScheduler for polling

## Environment Variables

| Name | Purpose |
|------|---------|
| `CLIENT_ID` | Azure Entra app client ID |
| `TENANT_ID` | Azure tenant ID |
| `CLIENT_SECRET` | Azure app secret (only for web Auth Code flow) |
| `AZURE_OPENAI_KEY` | Azure OpenAI Service API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL (e.g., https://appliedai-openai.openai.azure.com/) |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment name (gpt-4o-mini) |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version (2024-02-15-preview) |
| `REDIRECT_URI` | OAuth redirect URI — local: `http://localhost:8000/auth/callback`, prod: `https://appliedai-api.azurewebsites.net/auth/callback` |

## Testing Account

- Demo email: `appliedai.demo@outlook.com`
- Used for OAuth testing (no access to real @uiowa.edu accounts yet)

## AI Assistant Workflow

When helping with this project:

1. **Always check relevant docs first** before implementing
2. **Write all code files as artifacts** for easy copying
3. **Reference doc sections** when explaining design decisions
4. **Follow the POC_ROADMAP** for implementation order