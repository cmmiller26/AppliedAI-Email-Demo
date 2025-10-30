#!/usr/bin/env python3
"""
Send test emails from markdown file using Microsoft Graph API.

This script parses tests/data/test_emails.md and sends emails via Graph API
for testing email classification functionality.
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import httpx


def parse_test_emails(markdown_path: str) -> List[Dict]:
    """
    Parse test_emails.md and extract email data.

    Args:
        markdown_path: Path to the markdown file containing test emails

    Returns:
        List of dicts with keys:
        - category: str
        - email_number: int
        - title: str
        - from_name: str
        - from_email: str
        - subject: str
        - body: str
    """
    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(f"Test emails file not found: {markdown_path}")

    content = path.read_text(encoding='utf-8')

    emails = []
    current_category = None

    # Split by category sections first
    category_sections = re.split(r'\n## Category: (\w+)', content)

    # Skip first section (header before any categories)
    for i in range(1, len(category_sections), 2):
        category = category_sections[i]
        category_content = category_sections[i + 1] if i + 1 < len(category_sections) else ""

        # Split this category's content by individual emails
        email_sections = re.split(r'\n### Email \d+:\s*([^\n]+)', category_content)

        # Process email sections (skip first element which is text before first email)
        for j in range(1, len(email_sections), 2):
            title = email_sections[j].strip()
            email_content = email_sections[j + 1] if j + 1 < len(email_sections) else ""

            # Extract From field
            from_match = re.search(r'\*\*From:\*\*\s*([^<\n]+?)(?:\s*<([^>]+)>)?(?:\n|$)', email_content)
            if not from_match:
                print(f"Warning: Could not parse From field in {title}, skipping...")
                continue

            from_name = from_match.group(1).strip()
            from_email = from_match.group(2).strip() if from_match.group(2) else ""

            # Extract Subject
            subject_match = re.search(r'\*\*Subject:\*\*\s*([^\n]+)', email_content)
            if not subject_match:
                print(f"Warning: Could not parse Subject in {title}, skipping...")
                continue

            subject = subject_match.group(1).strip()

            # Extract Body (everything after **Body:** until --- or end)
            body_match = re.search(r'\*\*Body:\*\*\s*\n(.*?)(?:\n---|\Z)', email_content, re.DOTALL)
            if not body_match:
                print(f"Warning: Could not parse Body in {title}, skipping...")
                continue

            body = body_match.group(1).strip()

            # Extract email number from the section split
            email_num_match = re.search(r'Email (\d+):', title)
            email_number = int(email_num_match.group(1)) if email_num_match else 0

            emails.append({
                'category': category,
                'email_number': email_number,
                'title': title,
                'from_name': from_name,
                'from_email': from_email,
                'subject': subject,
                'body': body
            })

    return emails


async def send_email(
    access_token: str,
    recipient: str,
    email_data: dict,
    include_metadata: bool = True,
    save_to_drafts: bool = False
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Send email using Microsoft Graph API.

    Args:
        access_token: OAuth token
        recipient: Email address to send to
        email_data: Dict with category, subject, body, from_name, from_email
        include_metadata: Whether to add [TEST] markers (does NOT include category)
        save_to_drafts: If True, save to Drafts instead of sending (avoids spam filters)

    Returns:
        Tuple of (success: bool, error_message: Optional[str], message_id: Optional[str])
    """
    # Prepare email body
    body = email_data['body']

    # Optionally add minimal metadata (no category - that would give away the answer!)
    if include_metadata:
        metadata = "[TEST EMAIL]\n\n"
        body = metadata + body

    # For sent emails (not drafts), add mock sender to body since we can't change From field
    # For drafts, we'll set the From field in the payload instead
    if not save_to_drafts and email_data['from_email']:
        sender_note = f"[This test email simulates a message from: {email_data['from_name']} <{email_data['from_email']}>]\n\n"
        body = sender_note + body

    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json"
    }

    # Prepare sender info
    # Note: For sent emails, Graph API always uses the authenticated user as sender
    # For drafts, we can set the "from" field to show the mock sender
    from_field = None
    if email_data['from_email']:
        from_field = {
            "emailAddress": {
                "name": email_data['from_name'],
                "address": email_data['from_email']
            }
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if save_to_drafts:
                # Create message in Drafts folder
                url = "https://graph.microsoft.com/v1.0/me/messages"
                payload = {
                    "subject": email_data['subject'],
                    "body": {
                        "contentType": "Text",
                        "content": body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": recipient
                            }
                        }
                    ]
                }
                # For drafts, we can set the "from" field (not possible for sent emails)
                if from_field:
                    payload["from"] = from_field

                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 201:
                    # Extract message ID from response
                    response_data = response.json()
                    message_id = response_data.get('id')
                    return True, None, message_id
                else:
                    error_msg = f"{response.status_code}"
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg += f" - {error_data['error'].get('message', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text[:100]}"
                    return False, error_msg, None
            else:
                # Send email
                # WARNING: When actually sending, Graph API ALWAYS uses authenticated user as sender
                # The mock sender will only be visible in the email body as a note
                url = "https://graph.microsoft.com/v1.0/me/sendMail"
                payload = {
                    "message": {
                        "subject": email_data['subject'],
                        "body": {
                            "contentType": "Text",
                            "content": body
                        },
                        "toRecipients": [
                            {
                                "emailAddress": {
                                    "address": recipient
                                }
                            }
                        ]
                    },
                    "saveToSentItems": False
                }
                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 202:
                    return True, None, None
                else:
                    error_msg = f"{response.status_code}"
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg += f" - {error_data['error'].get('message', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text[:100]}"
                    return False, error_msg, None
    except Exception as e:
        return False, str(e), None


async def move_message_to_inbox(
    access_token: str,
    message_id: str
) -> tuple[bool, Optional[str]]:
    """
    Move a message from Drafts to Inbox using Microsoft Graph API.

    Args:
        access_token: OAuth token
        message_id: ID of the message to move

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/move"

    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json"
    }

    # Payload with destination folder ID (inbox)
    payload = {
        "destinationId": "inbox"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 201:
                return True, None
            else:
                error_msg = f"{response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f" - {error_data['error'].get('message', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text[:100]}"
                return False, error_msg
    except Exception as e:
        return False, str(e)


def print_dry_run(emails: List[Dict], recipient: str):
    """Print emails that would be sent in dry-run mode."""
    print("\n" + "=" * 70)
    print("DRY RUN MODE - No emails will be sent")
    print("=" * 70)
    print(f"\nWould send {len(emails)} emails to: {recipient}\n")

    for i, email in enumerate(emails, 1):
        print(f"{i}. [{email['category']}] {email['subject']}")
        if email['from_email']:
            print(f"   From: {email['from_name']} <{email['from_email']}>")
        else:
            print(f"   From: {email['from_name']}")
        print(f"   Body: ({len(email['body'])} characters)")
        print()


async def main():
    """Main function to parse arguments and send test emails."""
    parser = argparse.ArgumentParser(
        description="Create test emails in Inbox with mock senders for AI classification testing"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Access token from /debug/token endpoint"
    )
    parser.add_argument(
        "--categories",
        help="Filter by categories (comma-separated, e.g., 'URGENT,ACADEMIC')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of emails to create (e.g., --limit 1)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Seconds to wait between operations (default: 0, no delay)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview emails without creating them"
    )

    args = parser.parse_args()

    # Validate token
    if not args.token or not args.token.strip():
        print("Error: Access token is required and cannot be empty")
        print("\nTo get a token:")
        print("  1. Authenticate: open http://localhost:8000/auth/login")
        print("  2. Get token: curl http://localhost:8000/debug/token")
        print("  3. Or use: TOKEN=$(curl -s http://localhost:8000/debug/token | jq -r .access_token)")
        sys.exit(1)

    # Determine path to test_emails.md (relative to project root)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    test_emails_path = project_root / "tests" / "data" / "test_emails.md"

    print(f"Parsing test emails from: {test_emails_path}")

    try:
        emails = parse_test_emails(str(test_emails_path))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not emails:
        print("Error: No emails found in markdown file")
        sys.exit(1)

    # Filter by categories if specified
    if args.categories:
        requested_categories = [cat.strip().upper() for cat in args.categories.split(',')]
        original_count = len(emails)
        emails = [e for e in emails if e['category'] in requested_categories]
        print(f"Filtered to {len(emails)} emails from categories: {', '.join(requested_categories)}")
        if len(emails) == 0:
            print(f"Warning: No emails matched the specified categories")
            sys.exit(1)
    else:
        # Count categories
        categories = set(e['category'] for e in emails)
        print(f"Found {len(emails)} emails across {len(categories)} categories")

    # Apply limit if specified
    if args.limit and args.limit > 0:
        emails = emails[:args.limit]
        print(f"Limited to first {len(emails)} email(s)")

    # Dry run mode
    if args.dry_run:
        print_dry_run(emails, "testuser@appliedaiuiowa.onmicrosoft.com")
        return

    # Default behavior: save to drafts, no metadata, move to inbox
    recipient = "testuser@appliedaiuiowa.onmicrosoft.com"

    print(f"\nCreating test emails with mock senders in Inbox\n")

    success_count = 0
    failed_count = 0
    failed_emails = []
    message_ids = []  # Track message IDs for moving to inbox

    for i, email in enumerate(emails, 1):
        print(f"[{i}/{len(emails)}] ", end="", flush=True)

        success, error, message_id = await send_email(
            access_token=args.token,
            recipient=recipient,
            email_data=email,
            include_metadata=False,  # Always no metadata
            save_to_drafts=True  # Always save to drafts first
        )

        if success:
            print(f"✓ {email['category']}: {email['subject']}")
            success_count += 1
            if message_id:
                message_ids.append((message_id, email['subject']))
        else:
            print(f"✗ {email['category']}: {email['subject']}")
            print(f"    Error: {error}")
            failed_count += 1
            failed_emails.append((email['subject'], error))

        # Delay between emails (except after last one)
        if args.delay > 0 and i < len(emails):
            await asyncio.sleep(args.delay)

    # Move drafts to inbox (always done)
    if message_ids:
        print(f"\n{'=' * 70}")
        print(f"Moving {len(message_ids)} emails from Drafts to Inbox...")
        print(f"{'=' * 70}\n")

        moved_count = 0
        move_failed_count = 0

        for i, (message_id, subject) in enumerate(message_ids, 1):
            print(f"[{i}/{len(message_ids)}] ", end="", flush=True)

            move_success, move_error = await move_message_to_inbox(
                access_token=args.token,
                message_id=message_id
            )

            if move_success:
                print(f"✓ Moved to Inbox: {subject}")
                moved_count += 1
            else:
                print(f"✗ Failed to move: {subject}")
                print(f"    Error: {move_error}")
                move_failed_count += 1

            # Small delay between moves
            if args.delay > 0 and i < len(message_ids):
                await asyncio.sleep(args.delay)

    # Print summary
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"✓ Successfully created: {success_count}/{len(emails)}")
    if failed_count > 0:
        print(f"✗ Failed to create: {failed_count}/{len(emails)}")

    if message_ids:
        print(f"\n✓ Moved to Inbox: {moved_count}/{len(message_ids)}")
        if move_failed_count > 0:
            print(f"✗ Failed to move: {move_failed_count}/{len(message_ids)}")

    if failed_count > 0:
        print("\nFailed emails:")
        for subject, error in failed_emails:
            print(f"  - {subject}")
            print(f"    {error}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
