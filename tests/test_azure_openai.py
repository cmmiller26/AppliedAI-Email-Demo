"""
Azure OpenAI Service Connection Test

This script verifies that Azure OpenAI credentials are correctly configured
and tests the classification functionality with a sample email.
"""

import os
from dotenv import load_dotenv
from src.classifier import classify_email


def test_azure_openai_connection():
    """
    Tests Azure OpenAI Service connection and classification functionality.
    """
    print("=" * 60)
    print("Azure OpenAI Service Connection Test")
    print("=" * 60)
    print()

    # Load environment variables from .env file
    load_dotenv()

    # Verify required environment variables
    required_vars = [
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION"
    ]

    print("Checking environment variables...")
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var:
                display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"  ✓ {var}: {display_value}")
        else:
            print(f"  ✗ {var}: NOT SET")
            missing_vars.append(var)

    if missing_vars:
        print()
        print(f"ERROR: Missing environment variables: {', '.join(missing_vars)}")
        print("Please ensure these are set in your .env file.")
        return False

    print()
    print("-" * 60)
    print("Testing classification with sample email...")
    print("-" * 60)

    # Test email (from specification)
    test_subject = "CS 4980 Assignment Due Tonight"
    test_body = "Your homework is due at 11:59 PM"
    test_from = "professor@uiowa.edu"

    print()
    print(f"From: {test_from}")
    print(f"Subject: {test_subject}")
    print(f"Body: {test_body}")
    print()
    print("Calling Azure OpenAI Service...")

    # Attempt classification
    try:
        result = classify_email(
            subject=test_subject,
            body=test_body,
            from_address=test_from
        )

        print()
        print("=" * 60)
        print("CLASSIFICATION RESULT")
        print("=" * 60)
        print(f"Category:   {result['category']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Reasoning:  {result['reasoning']}")
        print()

        # Validate result
        expected_categories = ["URGENT", "ACADEMIC"]
        if result['category'] in expected_categories:
            print(f"✓ SUCCESS: Classification matches expected category ({expected_categories})")
            print()
            print("Your Azure OpenAI Service credentials are working correctly!")
            return True
        elif result['confidence'] == 0.0:
            print(f"✗ FAILURE: Classification failed")
            print(f"  Reason: {result['reasoning']}")
            return False
        else:
            print(f"⚠ WARNING: Unexpected category '{result['category']}'")
            print(f"  Expected one of: {expected_categories}")
            print(f"  However, the API call succeeded - credentials are valid.")
            return True

    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(f"Failed to classify email: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        print()
        print("Possible issues:")
        print("  1. Invalid API key")
        print("  2. Incorrect endpoint URL")
        print("  3. Deployment name doesn't exist")
        print("  4. Network connectivity issues")
        print("  5. Azure OpenAI Service quota exceeded")
        return False


if __name__ == "__main__":
    success = test_azure_openai_connection()

    print()
    print("=" * 60)
    if success:
        print("TEST PASSED ✓")
    else:
        print("TEST FAILED ✗")
    print("=" * 60)
