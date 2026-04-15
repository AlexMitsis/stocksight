"""
Application constants and configuration values.
"""

# Token counting configuration
TOKEN_LIMIT: int = 250000  # Set below the 272k limit to leave room for response
WARNING_THRESHOLD: int = 200000  # Warn when approaching limit
MAX_HISTORY_MESSAGES: int = 20  # Keep last N user/assistant message pairs
