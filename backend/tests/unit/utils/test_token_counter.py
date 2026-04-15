"""
Unit tests for token_counter utilities.

Tests TC1.2.3 and TC1.2.4 from Epic Story 1.2
"""

import pytest
from langchain.messages import SystemMessage, HumanMessage, AIMessage
from app.utils.token_counter import count_tokens, count_message_tokens, trim_conversation_history
from app.core.constants import MAX_HISTORY_MESSAGES


@pytest.mark.unit
class TestCountTokens:
    """Test suite for count_tokens function."""

    def test_count_tokens_accuracy(self):
        """
        TC1.2.3: Token counting accuracy

        Given: A simple text string
        When: count_tokens is called
        Then: Returns reasonable token count
        """
        # Given
        text = "What is the price of AAPL?"

        # When
        count = count_tokens(text)

        # Then
        assert isinstance(count, int)
        assert count > 0
        # Should be around 7-9 tokens for this text
        assert 5 < count < 12

    def test_count_tokens_empty_string(self):
        """
        Test token counting with empty string.
        """
        # When
        count = count_tokens("")

        # Then
        assert count == 0

    def test_count_tokens_long_text(self):
        """
        Test token counting with longer text.
        """
        # Given
        text = " ".join(["word"] * 100)  # 100 words

        # When
        count = count_tokens(text)

        # Then
        assert count > 50  # Should be at least 50 tokens
        assert count < 200  # Should be less than 200 tokens

    def test_count_tokens_unicode(self):
        """
        Test token counting with unicode characters.
        """
        # Given
        text = "Hello 世界 🌍"

        # When
        count = count_tokens(text)

        # Then
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_deterministic(self):
        """
        Test that token counting is deterministic.
        """
        # Given
        text = "Test message for token counting"

        # When
        count1 = count_tokens(text)
        count2 = count_tokens(text)

        # Then
        assert count1 == count2


@pytest.mark.unit
class TestCountMessageTokens:
    """Test suite for count_message_tokens function."""

    def test_count_message_tokens_multiple_messages(self, mock_langchain_messages):
        """
        Test counting tokens across multiple messages.
        """
        # Given
        messages = [
            mock_langchain_messages["system"],
            mock_langchain_messages["human"],
            mock_langchain_messages["ai"],
        ]

        # When
        total = count_message_tokens(messages)

        # Then
        assert isinstance(total, int)
        assert total > 0

    def test_count_message_tokens_empty_list(self):
        """
        Test counting tokens with empty message list.
        """
        # When
        total = count_message_tokens([])

        # Then
        assert total == 0

    def test_count_message_tokens_single_message(self):
        """
        Test counting tokens with single message.
        """
        # Given
        messages = [HumanMessage("Hello")]

        # When
        total = count_message_tokens(messages)

        # Then
        assert total > 0
        assert total < 10


@pytest.mark.unit
class TestTrimConversationHistory:
    """Test suite for trim_conversation_history function."""

    def test_trim_conversation_keeps_recent(self):
        """
        TC1.2.4: Conversation trimming keeps recent messages

        Given: Long conversation history
        When: trim_conversation_history is called with max_messages=2
        Then: Keeps system message and last 2 messages
        """
        # Given
        messages = [
            SystemMessage("system prompt"),
            HumanMessage("msg 1"),
            AIMessage("response 1"),
            HumanMessage("msg 2"),
            AIMessage("response 2"),
            HumanMessage("msg 3"),
        ]

        # When
        trimmed = trim_conversation_history(messages, max_messages=2)

        # Then
        assert len(trimmed) == 3  # system + 2 messages
        assert isinstance(trimmed[0], SystemMessage)
        assert trimmed[0].content == "system prompt"
        assert trimmed[-1].content == "msg 3"

    def test_trim_conversation_no_system_message(self):
        """
        Test trimming when there's no system message.
        """
        # Given
        messages = [
            HumanMessage("msg 1"),
            AIMessage("response 1"),
            HumanMessage("msg 2"),
            AIMessage("response 2"),
            HumanMessage("msg 3"),
        ]

        # When
        trimmed = trim_conversation_history(messages, max_messages=2)

        # Then
        assert len(trimmed) == 2  # Just last 2 messages
        assert trimmed[-1].content == "msg 3"

    def test_trim_conversation_already_short(self):
        """
        Test that short conversations aren't trimmed.
        """
        # Given
        messages = [
            SystemMessage("system"),
            HumanMessage("msg 1"),
        ]

        # When
        trimmed = trim_conversation_history(messages, max_messages=20)

        # Then
        assert len(trimmed) == 2  # All messages kept
        assert trimmed == messages

    def test_trim_conversation_preserves_system(self):
        """
        Test that system message is always preserved.
        """
        # Given
        messages = [
            SystemMessage("system prompt"),
        ] + [HumanMessage(f"msg {i}") for i in range(50)]

        # When
        trimmed = trim_conversation_history(messages, max_messages=5)

        # Then
        assert isinstance(trimmed[0], SystemMessage)
        assert trimmed[0].content == "system prompt"
        assert len(trimmed) == 6  # system + 5 messages

    def test_trim_conversation_uses_default_max(self):
        """
        Test that default max_messages is used.
        """
        # Given
        messages = [SystemMessage("system")] + [HumanMessage(f"msg {i}") for i in range(50)]

        # When
        trimmed = trim_conversation_history(messages)  # No max_messages specified

        # Then
        assert len(trimmed) == MAX_HISTORY_MESSAGES + 1  # system + MAX_HISTORY_MESSAGES

    def test_trim_conversation_empty_list(self):
        """
        Test trimming with empty message list.
        """
        # When
        trimmed = trim_conversation_history([])

        # Then
        assert trimmed == []
