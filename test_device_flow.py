import os
import msal
import httpx
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")

# IMPORTANT:
# For personal Outlook.com accounts + delegated access, use "consumers" or "common".
# "consumers" limits to Microsoft personal accounts; "common" allows org + personal.
AUTHORITY = "https://login.microsoftonline.com/consumers"

SCOPES = ["Mail.Read"]  # Add "offline_access" if you plan to cache refresh tokens with other flows
GRAPH = "https://graph.microsoft.com/v1.0"

def get_token_via_device_code():
    app = msal.PublicClientApplication(client_id=CLIENT_ID, authority=AUTHORITY)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to create device flow: {flow}")
    print("To sign in, visit:", flow["verification_uri"])
    print("Enter code:", flow["user_code"])
    result = app.acquire_token_by_device_flow(flow)  # Blocks until complete or timeout
    # print the id_token claims if present
    claims = result.get("id_token_claims")
    if claims:
        print("Signed in as:", claims.get("preferred_username"), "| tenant:", claims.get("tid"))
    if "access_token" not in result:
        raise RuntimeError(f"Token acquisition failed: {result}")
    return result["access_token"]

async def main():
    token = get_token_via_device_code()
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch 5 most recent messages
        r = await client.get(f"{GRAPH}/me/messages?$top=5&$select=subject,from,receivedDateTime,bodyPreview,internetMessageId",
                             headers=headers)
        r.raise_for_status()
        data = r.json()
        print("=== TOP 5 MESSAGES ===")
        for m in data.get("value", []):
            print(f"- {m.get('receivedDateTime')} | {m.get('from', {}).get('emailAddress', {}).get('address')} | {m.get('subject')}")
            print(f"  preview: {m.get('bodyPreview')[:120]!r}")
            print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())