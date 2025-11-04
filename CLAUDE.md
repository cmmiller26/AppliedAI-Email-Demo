# AI Assistant Guide

## Project Intent

Build a secure, policy-compliant email automation service:

- Authenticate via Microsoft Entra ID (OAuth), never HawkID passwords
- Read mail via Microsoft Graph
- Classify messages with Azure AI Foundry (Azure OpenAI)
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
- **AI Platform**: Azure AI Foundry (formerly Azure AI Studio)
- **AI Model**: Azure OpenAI Service (gpt-4o-mini) via AI Foundry
- **Scheduling** (Optional): APScheduler for polling

## Environment Variables

| Name | Purpose | Source |
|------|---------|--------|
| `CLIENT_ID` | Azure App Registration client ID | App Registration → Overview |
| `TENANT_ID` | Azure tenant ID | App Registration → Overview |
| `CLIENT_SECRET` | Client secret (Description: `poc-local-dev`) | Certificates & secrets |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | AI Foundry → Settings |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | AI Foundry → Settings |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (gpt-4o-mini) | AI Foundry → Deployments |
| `AZURE_OPENAI_API_VERSION` | API version (2024-12-01-preview) | Recommended version |
| `REDIRECT_URI` | OAuth callback URL | `http://localhost:8000/auth/callback` (local) |

## Azure Resources

This project uses the following Azure resources with standardized naming:

| Resource Type | Name | Purpose |
|---------------|------|---------|
| **App Registration** | `app-appliedai-classifier-poc` | OAuth 2.0 authentication |
| **Resource Group** | `rg-appliedai-classifier-poc` | Resource container |
| **AI Foundry Hub** | `aih-appliedai-classifier-poc` | AI platform hub (North Central US) |
| **AI Foundry Project** | `aip-appliedai-classifier-poc` | AI project workspace |
| **App Service** (future) | `app-appliedai-classifier-poc` | Web hosting |

## Azure AI Foundry Setup

This project uses **Azure AI Foundry** (formerly Azure AI Studio) as the centralized platform for AI operations. The existing `openai` Python SDK works seamlessly with AI Foundry - no code changes needed! AI Foundry provides enhanced monitoring, evaluation tools, and access to Prompt Flow for future enhancements.

## Testing Account

- Demo email: `appliedai.demo@outlook.com`
- Used for OAuth testing (no access to real @uiowa.edu accounts yet)

## AI Assistant Workflow

When helping with this project:

1. **Always check relevant docs first** before implementing
2. **Write all code files as artifacts** for easy copying
3. **Reference doc sections** when explaining design decisions
4. **Follow the POC_ROADMAP** for implementation order