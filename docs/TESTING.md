# Email Classification Testing Guide

Complete guide for testing the email classification system using Azure OpenAI Service with test emails in your Inbox.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Testing Strategy](#testing-strategy)
- [Using the Test Email Script](#using-the-test-email-script)
- [Testing Workflow](#testing-workflow)
- [Command Reference](#command-reference)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Authenticate and Get Token

```bash
# Start the FastAPI app
python -m uvicorn app:app --reload

# Open login page in browser
open http://localhost:8000/auth/login

# Get your access token
curl http://localhost:8000/debug/token
```

### 2. Create Test Emails in Inbox

```bash
# Get token
TOKEN=$(curl -s http://localhost:8000/debug/token | jq -r .access_token)

# Create all 18 test emails in your Inbox (one simple command!)
python tests/send_test_emails.py --token "$TOKEN"
```

**What this does:**
- ✅ Creates emails in Drafts with mock senders
- ✅ Automatically moves them to Inbox
- ✅ No category hints (clean for AI testing)
- ✅ Fast (no delays by default)

### 3. Test AI Classification

```bash
# Fetch emails from Inbox
curl "http://localhost:8000/graph/fetch?folder=inbox&top=20"

# Classify a single email
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "CS 4980 Assignment Due Tonight",
    "body": "Your homework is due at 11:59 PM",
    "from": "professor@uiowa.edu"
  }'

# Batch process all new emails with automatic category assignment
curl -X POST "http://localhost:8000/inbox/process-new"
```

---

## Testing Strategy

### How Test Emails Work

The test script uses a clever workaround to get realistic emails in your Inbox:

1. **Creates in Drafts** - Emails are created as drafts, which allows setting custom "From" addresses
2. **Moves to Inbox** - Automatically moves each email from Drafts to Inbox
3. **Result** - Emails appear in Inbox with proper mock senders!

### Why This Approach?

| Feature | Our Approach | Sending Directly |
|---------|--------------|------------------|
| Mock sender in "From" field | ✅ Yes | ❌ No (always shows auth user) |
| Bypasses spam filters | ✅ Yes | ❌ Gets blocked |
| No category hints | ✅ Yes | ✅ Yes |
| In Inbox for testing | ✅ Yes | ✅ Yes (if not blocked) |
| Fast setup | ✅ Instant | ❌ Slow (needs 15s delays) |

**Result:** Test emails in Inbox with realistic mock senders, ready for AI classification!

### Test Email Categories

The `tests/data/test_emails.md` file contains 18 test emails across 6 categories:

| Category | Count | Example Subjects |
|----------|-------|------------------|
| URGENT | 3 | "Assignment Due Tonight", "Registration Closes Tomorrow" |
| ACADEMIC | 3 | "Week 8 Lecture Notes", "Your Midterm Grade is Available" |
| ADMINISTRATIVE | 3 | "Complete Your FAFSA", "Housing Application Now Open" |
| SOCIAL | 3 | "Applied AI Club Meeting", "Homecoming Game Watch Party" |
| PROMOTIONAL | 3 | "20% Off Textbooks", "Amazon Prime Student FREE" |
| OTHER | 3 | "Package Delivery", "Password Reset Confirmation" |

---

## Using the Test Email Script

### Script Location

```
tests/send_test_emails.py
```

### Available Options

```bash
python tests/send_test_emails.py --help
```

**Options:**
- `--token TOKEN` - Access token (required)
- `--categories LIST` - Filter by categories (e.g., "URGENT,ACADEMIC")
- `--limit N` - Limit number of emails to create
- `--delay SECONDS` - Delay between operations (default: 0, no delay)
- `--dry-run` - Preview without creating

### Common Usage Patterns

**Create all test emails (default - recommended):**
```bash
python tests/send_test_emails.py --token "$TOKEN"
```

**Preview emails before creating:**
```bash
python tests/send_test_emails.py --token "$TOKEN" --dry-run
```

**Test with one email:**
```bash
python tests/send_test_emails.py --token "$TOKEN" --limit 1
```

**Create specific category:**
```bash
# Just URGENT category (3 emails)
python tests/send_test_emails.py --token "$TOKEN" --categories "URGENT"

# Multiple categories
python tests/send_test_emails.py --token "$TOKEN" --categories "URGENT,ACADEMIC"
```

**Add delay if needed:**
```bash
# 2 second delay between operations
python tests/send_test_emails.py --token "$TOKEN" --delay 2
```

### What the Script Does (Automatically)

Every time you run the script, it automatically:

1. ✅ **Creates in Drafts** - Allows setting mock "From" addresses
2. ✅ **Sets mock sender** - e.g., "Professor John Smith <john-smith@uiowa.edu>"
3. ✅ **No metadata** - Clean emails with no category hints
4. ✅ **Moves to Inbox** - Automatically moves each email from Drafts to Inbox

**Result:**
```
From: Professor John Smith <john-smith@uiowa.edu>
To: testuser@appliedaiuiowa.onmicrosoft.com
Subject: CS 4980 Assignment Due Tonight at 11:59 PM

This is a reminder that your machine learning assignment is due tonight at 11:59 PM.

Please submit via Canvas. Late submissions will receive a 10% penalty per day.
```

No `[TEST EMAIL]` marker, no category labels - just a clean email ready for AI classification!

---

## Testing Workflow

### Complete Test Cycle

#### Step 1: Create Test Emails in Inbox

```bash
# Authenticate
open http://localhost:8000/auth/login

# Get token
TOKEN=$(curl -s http://localhost:8000/debug/token | jq -r .access_token)

# Create all 18 test emails in Inbox
python tests/send_test_emails.py --token "$TOKEN"
```

**Output:**
```
Parsing test emails from: tests/data/test_emails.md
Found 18 emails across 6 categories

Creating test emails with mock senders in Inbox

[1/18] ✓ URGENT: CS 4980 Assignment Due Tonight at 11:59 PM
[2/18] ✓ URGENT: ACTION REQUIRED: Spring 2026 Registration Closes Tomorrow
...
[18/18] ✓ OTHER: Hope you're doing well!

======================================================================
Moving 18 emails from Drafts to Inbox...
======================================================================

[1/18] ✓ Moved to Inbox: CS 4980 Assignment Due Tonight at 11:59 PM
...
[18/18] ✓ Moved to Inbox: Hope you're doing well!

======================================================================
Summary:
✓ Successfully created: 18/18

✓ Moved to Inbox: 18/18
======================================================================
```

#### Step 2: Verify Emails in Inbox

```bash
# Fetch emails from Inbox
curl "http://localhost:8000/graph/fetch?folder=inbox&top=20"
```

**Response:**
```json
{
  "messages": [
    {
      "id": "AAMk...",
      "subject": "CS 4980 Assignment Due Tonight at 11:59 PM",
      "from": {
        "emailAddress": {
          "name": "Professor John Smith",
          "address": "john-smith@uiowa.edu"
        }
      },
      "bodyPreview": "This is a reminder that your machine learning...",
      "internetMessageId": "<msg123@inbox>"
    }
  ],
  "count": 18,
  "hasMore": false
}
```

Notice the `from` field shows the **mock sender**, not the authenticated user!

#### Step 3: Test Batch Processing (Automated Classification)

```bash
# Process all new emails (first run)
curl -X POST "http://localhost:8000/inbox/process-new" | python -m json.tool
```

**Expected Output:**
```json
{
  "processed": 18,
  "lastCheck": null,
  "newCheck": "2025-10-31T12:00:00Z",
  "categories": {
    "URGENT": 3,
    "ACADEMIC": 3,
    "ADMINISTRATIVE": 3,
    "SOCIAL": 3,
    "PROMOTIONAL": 3,
    "OTHER": 3
  },
  "emails": [
    {
      "id": "AAMkAGI...",
      "subject": "CS 4980 Assignment Due Tonight at 11:59 PM",
      "category": "URGENT",
      "confidence": 0.95,
      "receivedDateTime": "2025-10-31T10:30:00Z"
    }
    // ... 17 more emails
  ]
}
```

#### Step 4: Verify Idempotency (Should Process 0 Emails)

```bash
# Run again immediately
curl -X POST "http://localhost:8000/inbox/process-new" | python -m json.tool
```

**Expected Output:**
```json
{
  "processed": 0,
  "lastCheck": "2025-10-31T12:00:00Z",
  "newCheck": "2025-10-31T12:01:00Z",
  "categories": {},
  "emails": []
}
```

✅ **This confirms idempotency - no duplicate processing!**

#### Step 5: Check Processed Emails

```bash
# View all processed emails
curl "http://localhost:8000/debug/processed" | python -m json.tool
```

**Expected Output:**
```json
{
  "count": 18,
  "last_check_time": "2025-10-31T12:01:00Z",
  "emails": [
    {
      "internet_message_id": "<CAB123@mail.gmail.com>",
      "subject": "CS 4980 Assignment Due Tonight at 11:59 PM",
      "from": "john-smith@uiowa.edu",
      "category": "URGENT",
      "confidence": 0.95,
      "processed_at": "2025-10-31T12:00:15Z"
    }
    // ... 17 more emails
  ]
}
```

#### Step 6: Verify Outlook Categories

```bash
# Open Outlook to see colored category labels
open https://outlook.com  # or https://outlook.office.com
```

Emails should now have colored category labels in Outlook!

#### Step 7: Test with New Email

Send yourself a new test email, then:

```bash
# Wait ~30 seconds for delivery

# Process new emails (should process 1)
curl -X POST "http://localhost:8000/inbox/process-new" | python -m json.tool
```

**Expected Output:**
```json
{
  "processed": 1,
  "lastCheck": "2025-10-31T12:01:00Z",
  "newCheck": "2025-10-31T12:05:00Z",
  "categories": {
    "SOCIAL": 1
  },
  "emails": [
    {
      "id": "AAMkAGI...",
      "subject": "Applied AI Meeting Tomorrow",
      "category": "SOCIAL",
      "confidence": 0.91,
      "receivedDateTime": "2025-10-31T12:04:00Z"
    }
  ]
}
```

#### Step 8: Single Email Classification (Optional)

```bash
# Classify individual email without batch processing
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "CS 4980 Assignment Due Tonight at 11:59 PM",
    "body": "This is a reminder that your machine learning assignment is due tonight...",
    "from": "john-smith@uiowa.edu"
  }'
```

### Iterative Testing

Test specific categories during development:

```bash
# Test URGENT classification
python tests/send_test_emails.py --token "$TOKEN" --categories "URGENT"
curl "http://localhost:8000/graph/fetch?folder=inbox&top=3"

# Test PROMOTIONAL classification
python tests/send_test_emails.py --token "$TOKEN" --categories "PROMOTIONAL"
curl "http://localhost:8000/graph/fetch?folder=inbox&top=3"
```

---

## Command Reference

### Quick Reference Commands

```bash
# Authentication
open http://localhost:8000/auth/login
TOKEN=$(curl -s http://localhost:8000/debug/token | jq -r .access_token)

# Create all test emails in Inbox
python tests/send_test_emails.py --token "$TOKEN"

# Create single email
python tests/send_test_emails.py --token "$TOKEN" --limit 1

# Create specific category
python tests/send_test_emails.py --token "$TOKEN" --categories "URGENT"

# Fetch and verify from Inbox
curl "http://localhost:8000/graph/fetch?folder=inbox&top=20"

# Batch process new emails (automatic classification + category assignment)
curl -X POST "http://localhost:8000/inbox/process-new"

# View processed emails
curl "http://localhost:8000/debug/processed"

# Check Outlook for categories
open https://outlook.com
```

### Graph API Folder Options

The Graph API endpoint supports reading from different folders:

```bash
# Inbox (default - where test emails are created)
curl "http://localhost:8000/graph/fetch?folder=inbox"

# Drafts folder
curl "http://localhost:8000/graph/fetch?folder=drafts"

# Sent Items folder
curl "http://localhost:8000/graph/fetch?folder=sentitems"
```

---

## Troubleshooting

### No token found

**Error:** `{"error":"No token found"}`

**Solution:** Authenticate first:
```bash
open http://localhost:8000/auth/login
```

### Token expired

**Error:** `401 - Token is expired`

**Solution:** Re-authenticate to get a fresh token:
```bash
open http://localhost:8000/auth/login
```

### Missing Mail.Send permission

**Error:** `403 - Access is denied`

**Solution:** The token needs the `Mail.Send` scope. Re-authenticate:
```bash
open http://localhost:8000/auth/login
# Verify scopes include Mail.Send:
curl -s http://localhost:8000/debug/token | grep scopes
```

### Emails don't appear in Inbox

**Problem:** Ran the script but don't see emails in Inbox

**Solution:**
1. Check the script output - did it successfully create and move emails?
2. Verify with Graph API: `curl "http://localhost:8000/graph/fetch?folder=inbox&top=20"`
3. Check if emails are stuck in Drafts: `curl "http://localhost:8000/graph/fetch?folder=drafts&top=20"`
4. Try with `--limit 1` to test with one email first

### Emails show wrong sender

**Problem:** Emails show "Test User" instead of mock sender

**Solution:** This shouldn't happen with the current script (it always creates with mock senders). If you see this:
1. Check you're using the latest version of the script
2. Verify the script output shows "Moving X emails from Drafts to Inbox"
3. The mock sender is only preserved when emails are created in Drafts first, then moved

### File not found error

**Error:** `Test emails file not found: tests/data/test_emails.md`

**Solution:** Run the script from the project root:
```bash
# From project root (correct)
python tests/send_test_emails.py --token "$TOKEN"

# Not from tests directory
cd /path/to/appliedai-demo
python tests/send_test_emails.py --token "$TOKEN"
```

---

## Best Practices

### ✅ DO:
- Use the simple default command: `python tests/send_test_emails.py --token "$TOKEN"`
- Test with `--limit 1` first before creating all 18 emails
- Use `--categories` to test specific email types
- Re-authenticate when token expires
- Run script from project root directory
- Clean up test emails from Inbox when done testing

### ❌ DON'T:
- Forget to re-authenticate if token expires
- Run script from `tests/` directory
- Add delays unless necessary (slows down testing)

---

## Advanced Usage

### Custom Test Emails

Edit `tests/data/test_emails.md` to add your own test cases:

```markdown
## Category: URGENT 🔴

### Email 4: Custom Test
**From:** Test User <test@example.com>
**Subject:** My Custom Test Email
**Body:**
This is a custom test email for specific edge cases.

---
```

### Programmatic Usage

Import and use the functions directly:

```python
from tests.send_test_emails import parse_test_emails, send_email
import asyncio

# Parse emails
emails = parse_test_emails("tests/data/test_emails.md")

# Filter
urgent_emails = [e for e in emails if e['category'] == 'URGENT']

# Send
async def main():
    for email in urgent_emails:
        success, error = await send_email(
            access_token="YOUR_TOKEN",
            recipient="test@example.com",
            email_data=email,
            save_to_drafts=True,
            include_metadata=False
        )
        print(f"Sent: {success}")

asyncio.run(main())
```

---

## Future Enhancements

- [ ] Cleanup script to delete all test drafts
- [ ] Verification script to compare expected vs actual classifications
- [ ] Performance metrics (timing, success rate)
- [ ] HTML email body support
- [ ] Attachment support
- [ ] Batch sending via single API call
- [ ] Auto-refresh token when expired
