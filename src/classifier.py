"""
Email Classification Module using Azure AI Foundry with Azure OpenAI

This module provides functionality to classify emails into preset categories
using GPT models hosted on Azure AI Foundry with Azure OpenAI Service.

The module uses the OpenAI Python SDK which works seamlessly with AI Foundry -
no code changes needed! AI Foundry provides enhanced monitoring, evaluation tools,
and access to advanced features like Prompt Flow.
"""

import os
import re
from typing import Dict
from openai import AzureOpenAI


# Preset categories for POC v0.1
PRESET_CATEGORIES = [
    "URGENT",         # Time-sensitive emails requiring immediate attention
    "ACADEMIC",       # Class-related emails, assignments, grades, lectures
    "ADMINISTRATIVE", # University business, registration, forms, official notices
    "SOCIAL",         # Events, club meetings, social gatherings
    "PROMOTIONAL",    # Marketing emails, newsletters, advertisements
    "OTHER"           # Catch-all for emails that don't fit above categories
]


# System prompt from CLASSIFICATION_SPEC.md
SYSTEM_PROMPT = """You are an email classification assistant for university students at the University of Iowa.
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
}"""


def sanitize_input(text: str) -> str:
    """
    Sanitizes email text by removing HTML tags and limiting length.

    Args:
        text: Raw email text (may contain HTML)

    Returns:
        Cleaned text, truncated to 500 characters
    """
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove excessive whitespace and newlines
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    # Truncate to 500 characters
    if len(text) > 500:
        text = text[:500]

    return text


def classify_email(subject: str, body: str, from_address: str) -> Dict[str, any]:
    """
    Classifies an email using Azure OpenAI Service via Azure AI Foundry.

    Args:
        subject: Email subject line
        body: Email body content
        from_address: Sender email address

    Returns:
        Dictionary with classification results:
        {
            "category": str,      # One of PRESET_CATEGORIES
            "confidence": float,  # 0.0 to 1.0
            "reasoning": str      # Brief explanation
        }

    On error, returns:
        {
            "category": "OTHER",
            "confidence": 0.0,
            "reasoning": "Classification failed - [error details]"
        }
    """
    try:
        # Initialize Azure OpenAI client (works with AI Foundry - no code changes needed!)
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  # Points to AI Foundry's OpenAI resource
        )

        # Sanitize inputs
        subject_clean = sanitize_input(subject)
        body_preview = sanitize_input(body)

        # Construct user prompt
        user_prompt = f"""Classify this email:

From: {from_address}
Subject: {subject_clean}
Body Preview: {body_preview}"""

        # Call Azure OpenAI (via AI Foundry)
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"}
        )

        # Parse response
        import json
        result = json.loads(response.choices[0].message.content)

        # Validate category
        if result.get("category") not in PRESET_CATEGORIES:
            result["category"] = "OTHER"
            result["confidence"] = 0.0
            result["reasoning"] = f"Invalid category returned: {result.get('category')}"

        # Ensure confidence is a float between 0 and 1
        confidence = float(result.get("confidence", 0.0))
        result["confidence"] = max(0.0, min(1.0, confidence))

        return result

    except Exception as e:
        # Fallback error response
        return {
            "category": "OTHER",
            "confidence": 0.0,
            "reasoning": f"Classification failed - {type(e).__name__}: {str(e)}"
        }


# Fallback keywords for future rule-based classification (if AI unavailable)
FALLBACK_KEYWORDS = {
    "URGENT": ["urgent", "asap", "due today", "deadline", "immediately", "due tonight"],
    "ACADEMIC": ["assignment", "exam", "grade", "lecture", "professor", "syllabus", "homework"],
    "ADMINISTRATIVE": ["registration", "enroll", "tuition", "form", "bursar", "registrar"],
    "SOCIAL": ["meeting", "event", "rsvp", "join us", "party", "gathering"],
    "PROMOTIONAL": ["unsubscribe", "discount", "offer", "newsletter", "limited time"]
}


def classify_email_fallback(subject: str, body: str, from_address: str) -> Dict[str, any]:
    """
    Simple keyword-based fallback classification (no AI required).

    This is a backup method if Azure OpenAI Service is unavailable.

    Args:
        subject: Email subject line
        body: Email body content
        from_address: Sender email address

    Returns:
        Dictionary with classification results
    """
    text = f"{subject} {body}".lower()

    # Check each category for keyword matches
    for category, keywords in FALLBACK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return {
                    "category": category,
                    "confidence": 0.6,  # Lower confidence for rule-based
                    "reasoning": f"Keyword match: '{keyword}'"
                }

    # No matches found
    return {
        "category": "OTHER",
        "confidence": 0.3,
        "reasoning": "No keyword matches found"
    }
