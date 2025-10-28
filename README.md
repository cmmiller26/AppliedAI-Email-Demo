# AppliedAI Email Demo

A Python demo that:
- Authenticates with Microsoft Graph (personal Outlook demo tenant)
- Fetches messages from `/me/messages`
- (Optionally) classifies them with OpenAI
- Will later run as a FastAPI web app on Azure App Service

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate
pip install -r requirements.txt
cp .env.example .env          # fill in values
python test_device_flow.py