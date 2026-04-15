"""
Token counting utilities for managing conversation context.
"""

import tiktoken
from typing import List
from langchain.messages import SystemMessage
from app.core.constants import MAX_HISTORY_MESSAGES

# Initialize tokenizer for GPT-5
try:
    encoding = tiktoken.encoding_for_model("gpt-4")  # GPT-5 likely uses same encoding
except KeyError:
    encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """
    Count tokens in a text string.

    Args:
        text: The text to count tokens for

    Returns:
        Number of tokens in the text
    """
    return len(encoding.encode(text))


def count_message_tokens(messages: List) -> int:
    """
    Count total tokens in a list of messages.

    Args:
        messages: List of message objects with content attribute

    Returns:
        Total number of tokens across all messages
    """
    total = 0
    for msg in messages:
        if hasattr(msg, "content"):
            total += count_tokens(str(msg.content))
    return total


def trim_conversation_history(messages: List, max_messages: int = MAX_HISTORY_MESSAGES) -> List:
    """
    Trim conversation history to keep only recent messages.
    Always keeps the system message and the most recent user/assistant pairs.

    Args:
        messages: List of message objects
        max_messages: Maximum number of messages to keep (excluding system message)

    Returns:
        Trimmed list of messages
    """
    if len(messages) <= max_messages + 1:  # +1 for system message
        return messages

    # Keep system message and last N messages
    system_msg = messages[0] if messages and isinstance(messages[0], SystemMessage) else None
    recent_messages = messages[-(max_messages):]

    if system_msg:
        return [system_msg] + recent_messages
    return recent_messages
