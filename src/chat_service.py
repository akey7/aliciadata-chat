"""Claude API interaction with streaming support."""

import os
from typing import Generator, Optional
from anthropic import Anthropic


# Initialize Anthropic client
client: Optional[Anthropic] = None


def initialize_client() -> None:
    """Initialize the Anthropic client with API key from environment."""
    global client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    client = Anthropic(api_key=api_key)


def validate_api_key() -> bool:
    """
    Test API connectivity on startup.

    Returns:
        bool: True if API key is valid and connection successful, False otherwise.
    """
    try:
        if client is None:
            initialize_client()

        # Test with a minimal API call
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        return True
    except Exception as e:
        print(f"API validation error: {e}")
        return False


def format_message_history(db_messages: list) -> list:
    """
    Convert database format to Anthropic API message format.

    Args:
        db_messages: List of messages from database with fields:
                    (id, timestamp, session_uuid, message_type, contents, created_at)

    Returns:
        List of messages in Anthropic API format with role and content.
    """
    messages = []

    for msg in db_messages:
        # db_messages format: (id, timestamp, session_uuid, message_type, contents, created_at)
        message_type = msg[3]  # message_type column
        contents = msg[4]      # contents column

        # Skip system messages as they are passed separately
        if message_type == "system":
            continue

        # Convert message_type to role (user or assistant)
        if message_type in ("user", "assistant"):
            messages.append({
                "role": message_type,
                "content": contents
            })

    return messages


def stream_message(messages: list, system_prompt: str) -> Generator[str, None, str]:
    """
    Send messages to Claude API with streaming enabled.

    Args:
        messages: List of messages in Anthropic API format
        system_prompt: System prompt with resume and job description context

    Yields:
        str: Text chunks as they arrive from the API

    Returns:
        str: Complete message after streaming completes
    """
    if client is None:
        initialize_client()

    try:
        full_response = ""

        # Create streaming response
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield text

        return full_response

    except Exception as e:
        error_msg = f"Error during streaming: {str(e)}"
        print(error_msg)
        yield error_msg
        return error_msg
