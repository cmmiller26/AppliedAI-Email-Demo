# AI Assistant Guide

## Project Intent

Build a secure, policy-compliant email automation service:

- Authenticate via Microsoft Entra ID (OAuth), never HawkID passwords
- Read mail via Microsoft Graph
- Classify messages with OpenAI
- Host on Azure App Service (Python 3.12, Linux), later enabling webhook or polling behavior

## Non-Negotiables

- Never commit secrets (`CLIENT_SECRET`, `OPENAI_API_KEY`)
- Use OAuth flows only (Device Code for local testing, Auth Code for web deployment)
- Ensure endpoints are idempotent; do not reprocess the same `internetMessageId`

## Current Status

- ✅ `test_device_flow.py` works with the Outlook demo tenant using delegated Mail.Read permissions
- ⚙️ FastAPI scaffold exists in `app.py`

## Tasks for AI / Developer Assistance

### 1. Implement Auth Code Flow

- `GET /auth/login`: Redirect to Microsoft sign-in
- `GET /auth/callback`: Exchange code for tokens (store in memory for now)

### 2. Graph Integration

- `GET /graph/fetch?top=10`: Server-side call to `/me/messages`

### 3. Classification Endpoint

- `POST /classify`: Accepts `{subject, preview, body}` → Returns `{label}`

### 4. Storage Layer

- Add lightweight persistence (in-memory dict → later Azure Table/Blob)

### 5. Testing

- Write unit tests for the classifier normalization logic (pure functions)

## Tech Stack

- **Frameworks**: FastAPI + Uvicorn + Gunicorn
- **Auth**: MSAL for Python (`PublicClientApplication` for local, `ConfidentialClientApplication` for web)
- **Networking**: httpx for Graph API calls
- **AI Integration**: OpenAI for classification
- **Scheduling (Optional)**: APScheduler for polling and refresh cycles

## Environment Variables

| Name | Purpose |
|------|---------|
| `CLIENT_ID` | Azure Entra app client ID |
| `TENANT_ID` | Azure tenant ID |
| `CLIENT_SECRET` | Azure app secret (only for web Auth Code flow) |
| `OPENAI_API_KEY` | OpenAI API key |
| `REDIRECT_URI` | OAuth redirect URI — local: `http://localhost:8000/auth/callback`, prod: `https://appliedai-api.azurewebsites.net/auth/callback` |

## Definition of Done (MVP)

- `/health` → Returns 200
- `/auth/login` → Microsoft sign-in → `/auth/callback` stores access token
- `/graph/fetch` → Returns latest messages as JSON
- `/classify` → Returns a category string
- Deployed to Azure App Service with secrets configured in App Settings