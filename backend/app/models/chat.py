"""
Pydantic models for chat API requests and responses.
"""

from pydantic import BaseModel


class PromptObject(BaseModel):
    """Represents a chat prompt message."""

    content: str
    id: str
    role: str


class RequestObject(BaseModel):
    """Represents a chat request from the client."""

    prompt: PromptObject
    threadId: str
    responseId: str
