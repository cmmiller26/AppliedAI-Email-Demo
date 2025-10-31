# Email Classification Specification

## Overview

This document defines how emails are classified using Azure OpenAI Service with GPT models. The system uses preset categories for the POC with an extensible design for future user-defined categories.

---

## Preset Categories (POC v0.1)

### 1. URGENT 🔴
**Description:** Time-sensitive emails requiring immediate attention.

**Characteristics:**
- Contains deadline language ("due today", "by 5pm", "urgent")
- Action verbs ("respond immediately", "confirm by")
- High-priority senders (professors with assignments, registration deadlines)

**Examples:**
- "Assignment due tonight at 11:59 PM"
- "Final exam location change - please confirm"
- "Action required: Financial aid deadline tomorrow"

---

### 2. ACADEMIC 📚
**Description:** Class-related emails including assignments, grades, lectures, and course materials.

**Characteristics:**
- From professors, TAs, or course management systems
- Contains course codes (CS 4980, MATH 2850)
- Keywords: assignment, exam, lecture, grade, syllabus, office hours

**Examples:**
- "CS 4980: Week 5 lecture notes posted"
- "Your midterm grade is available"
- "TA office hours rescheduled"

---

### 3. ADMINISTRATIVE 🏛️
**Description:** University business, registration, forms, official notices.

**Characteristics:**
- From university departments (Registrar, Bursar, Housing)
- Keywords: registration, enrollment, tuition, forms, policy, requirement
- Official tone and formatting

**Examples:**
- "Fall 2026 registration opens November 1"
- "Complete your housing application"
- "University policy update notification"

---

### 4. SOCIAL 🎉
**Description:** Events, club meetings, social gatherings, and community announcements.

**Characteristics:**
- From student organizations, campus events
- Keywords: meeting, event, party, join us, RSVP, free food
- Casual, invitational tone

**Examples:**
- "Applied AI club meeting this Thursday"
- "Homecoming game watch party - free pizza!"
- "Join us for the career fair"

---

### 5. PROMOTIONAL 📢
**Description:** Marketing emails, newsletters, announcements, and advertisements.

**Characteristics:**
- Bulk/mass email formatting
- Marketing language ("limited time", "don't miss out", "subscribe")
- From external organizations or campus marketing departments
- Contains unsubscribe links

**Examples:**
- "Student discount: 20% off textbooks"
- "Weekly campus newsletter"
- "Amazon Prime Student - Free 6 months"

---

### 6. OTHER 📦
**Description:** Catch-all for emails that don't fit above categories.

**Characteristics:**
- Ambiguous content
- Low confidence in other categories
- Personal emails
- Automated notifications

**Examples:**
- "Package delivery notification"
- "Password reset confirmation"
- Personal correspondence

---

## Azure OpenAI Configuration

### Model Selection
```python
# Using Azure OpenAI Service deployment
DEPLOYMENT_NAME = "gpt-4o-mini"  # Cost-effective, fast, good accuracy
# Alternative: Deploy "gpt-4o" for higher accuracy (more expensive)
```

### Parameters
```python
{
    "model": "gpt-4o-mini",  # Deployment name in Azure OpenAI
    "temperature": 0.3,      # Low temperature for consistent results
    "max_tokens": 200,       # Enough for JSON response
    "response_format": {"type": "json_object"}  # Force JSON output
}
```

**Why these settings:**
- **Temperature 0.3:** Reduces randomness, ensures consistent categorization
- **max_tokens 200:** Sufficient for category + confidence + reasoning
- **JSON mode:** Guarantees parseable response

---

## Prompt Template

### System Prompt
```
You are an email classification assistant for university students at the University of Iowa. 
Your job is to categorize emails to help students organize their inbox efficiently.

Classify each email into exactly ONE of these categories:
- URGENT: Time-sensitive, requires immediate action, has deadlines
- ACADEMIC: Classes, assignments, grades, lectures, professors, course materials
- ADMINISTRATIVE: Registration, forms, tuition, university business, official notices
- SOCIAL: Events, club meetings, social gatherings, RSVPs, campus activities
- PROMOTIONAL: Marketing, newsletters, advertisements, bulk emails
- OTHER: Everything else

Consider:
1. Sender domain (e.g., @uiowa.edu suggests ACADEMIC or ADMINISTRATIVE)
2. Keywords indicating urgency, deadlines, or time-sensitivity
3. Tone (official vs casual vs marketing)
4. Context clues in subject and body

Respond ONLY with valid JSON in this exact format:
{
  "category": "CATEGORY_NAME",
  "confidence": 0.85,
  "reasoning": "Brief explanation of why this category was chosen"
}
```

### User Prompt (Per Email)
```
Classify this email:

From: {from_address}
Subject: {subject}
Body Preview: {body_preview}

Received: {received_datetime}
```

**Input Processing:**
- `body_preview`: First 500 characters of email body
- Strip HTML tags: `<p>`, `<div>`, etc.
- Remove excessive whitespace and newlines
- Normalize encoding

---

## Implementation Details

### Function Signature
```python
def classify_email(
    subject: str,
    body: str,
    from_address: str,
    categories: list[str] = None,  # Future: user-defined categories
    model: str = "gpt-4o-mini"     # Azure OpenAI deployment name
) -> dict:
    """
    Classifies an email using Azure OpenAI Service.

    Returns:
        {
            "category": str,
            "confidence": float,  # 0.0 to 1.0
            "reasoning": str
        }
    """
```

### Error Handling
```python
# If Azure OpenAI Service fails
{
    "category": "OTHER",
    "confidence": 0.0,
    "reasoning": "Classification failed - API error"
}

# If confidence < 0.5
{
    "category": "OTHER",
    "confidence": 0.35,
    "reasoning": "Low confidence - ambiguous email content"
}
```

### Fallback Rules (No AI Available)
Simple keyword matching as backup:
```python
FALLBACK_KEYWORDS = {
    "URGENT": ["urgent", "asap", "due today", "deadline", "immediately"],
    "ACADEMIC": ["assignment", "exam", "grade", "lecture", "professor"],
    "ADMINISTRATIVE": ["registration", "enroll", "tuition", "form"],
    "SOCIAL": ["meeting", "event", "rsvp", "join us"],
    "PROMOTIONAL": ["unsubscribe", "discount", "offer", "newsletter"]
}
```

---

## Cost Estimation (POC)

### Azure OpenAI Pricing (gpt-4o-mini)
- Hosted on Azure OpenAI Service
- Input: $0.15 / 1M tokens
- Output: $0.60 / 1M tokens
- May be covered by university Azure credits

### Per Email Cost
- Average email: ~300 tokens input, ~50 tokens output
- Cost per email: **~$0.00006** (less than 1 cent per 100 emails)

### POC Budget
- 1,000 emails classified: **~$0.06**
- 10,000 emails: **~$0.60**

**Very cost-effective for testing!**

---

## Extensibility for Future Phases

### User-Defined Categories (Phase 2)
```python
def classify_email(
    subject: str,
    body: str,
    from_address: str,
    categories: list[str] = DEFAULT_CATEGORIES,  # User can override
    examples: dict[str, list[str]] = None  # Few-shot examples per category
):
    # Dynamically build prompt with user categories + examples
    pass
```

### AI-Suggested Categories (Phase 3)
```python
def analyze_inbox_patterns(emails: list[dict]) -> list[str]:
    """
    Analyze user's inbox and suggest natural categories.
    Uses clustering on email metadata (senders, keywords, frequency).
    """
    pass
```

---

## Testing Strategy

### Test Cases
1. **Clear categorization** - Obvious category assignments
2. **Edge cases** - Ambiguous emails, multiple potential categories
3. **Spam/promotional** - Ensure marketing emails don't leak into other categories
4. **Urgency detection** - Deadline keywords correctly trigger URGENT
5. **Sender domain** - @uiowa.edu emails correctly categorized

### Sample Test Emails
```python
TEST_EMAILS = [
    {
        "subject": "CS 4980 Assignment due tonight",
        "from": "john-smith@uiowa.edu",
        "expected": "URGENT"
    },
    {
        "subject": "Applied AI meeting this Thursday",
        "from": "applied-ai@uiowa.edu",
        "expected": "SOCIAL"
    },
    {
        "subject": "20% off all textbooks this week!",
        "from": "bookstore@marketing.com",
        "expected": "PROMOTIONAL"
    }
]
```

---

## Performance Metrics

### Target Accuracy (POC)
- **>85%** correct categorization on test set
- **<5%** "OTHER" category usage (indicates good category coverage)
- **>0.7** average confidence score

### Monitoring
- Log all classifications with confidence scores
- Track category distribution over time
- Flag low-confidence classifications for manual review

---

## Outlook Category Assignment

### Overview

After classification, emails are automatically tagged with Outlook category labels using Microsoft Graph API. Categories appear as colored tags in Outlook desktop, web, and mobile.

### Implementation

**Function:** `assign_category_to_message(access_token, message_id, category)`
**Location:** `src/graph.py`

**Process:**
1. GET current categories from email (`/me/messages/{id}?$select=categories`)
2. Add new category to existing list (preserves user-defined categories)
3. PATCH email with updated categories array
4. Outlook automatically creates category if it doesn't exist

**Example:**
```python
from src.graph import assign_category_to_message

# Assign URGENT category to an email
success = await assign_category_to_message(
    access_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
    message_id="AAMkAGI2...",  # Graph API message ID
    category="URGENT"
)
```

### Requirements

- **OAuth Scope:** `Mail.ReadWrite` (required for PATCH operations)
- **message_id:** Graph API message ID (from `messages.id`, not `internetMessageId`)
- **Category names:** Case-sensitive, must match classification categories

### API Calls

**GET categories:**
```http
GET https://graph.microsoft.com/v1.0/me/messages/{id}
    ?$select=categories
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "categories": ["Blue Category", "Important"]
}
```

**PATCH categories:**
```http
PATCH https://graph.microsoft.com/v1.0/me/messages/{id}
Content-Type: application/json
Authorization: Bearer {access_token}

{
  "categories": ["Blue Category", "Important", "URGENT"]
}
```

**Response:** `204 No Content` (success)

### Category Colors in Outlook

Users can customize category colors in Outlook:

**Suggested Colors:**
- **URGENT** → Red 🔴
- **ACADEMIC** → Blue 🔵
- **ADMINISTRATIVE** → Orange 🟠
- **SOCIAL** → Green 🟢
- **PROMOTIONAL** → Purple 🟣
- **OTHER** → Gray ⚪

**How to customize (Outlook Web):**
1. Settings (gear icon) → View all Outlook settings
2. General → Categories
3. Select category → Choose color

**How to customize (Outlook Desktop):**
1. Home tab → Categorize → All Categories
2. Select category → Color dropdown
3. Rename if desired (e.g., "🔴 URGENT")

### Error Handling

- **If category assignment fails:** Email is still marked as processed (classification succeeds)
- **Error logged:** Server logs the failure but continues processing other emails
- **Graceful degradation:** Users can still see classifications in `/debug/processed`

**Common Errors:**
- `401 Unauthorized`: Token expired or missing Mail.ReadWrite scope
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Invalid message_id

### Performance

- **Latency:** ~200-500ms per email (1 GET + 1 PATCH request)
- **Total per email:** ~1.5-2.5s (classification + category assignment)
- **Batch of 10 emails:** ~20s (sequential processing)

**Future Optimization:**
- Batch PATCH requests (if Graph API supports)
- Queue category assignments for async processing
- Cache category state to avoid redundant GETs

---

## Future Improvements

1. **Multi-label classification** - Some emails fit multiple categories
2. **Priority scoring** - Within each category, rank by importance
3. **Batch category assignment** - Update multiple emails in one API call
4. **Confidence thresholds** - Only assign category if confidence > 0.7
5. **Learning from user feedback** - Improve classifications based on user corrections
6. **Custom category definitions** - Allow users to define their own categories
7. **Category icons** - Add emoji icons to category names automatically