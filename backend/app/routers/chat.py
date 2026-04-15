"""
Chat API router with streaming endpoint.
"""

import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from loguru import logger
from langchain.messages import HumanMessage, SystemMessage

from app.models.chat import RequestObject
from app.models.database import User
from app.agents.stock_analyst import agent, get_system_message
from app.utils.token_counter import count_tokens
from app.services.context_storage_service import get_context_storage_service
from app.services.context_retrieval_service import get_context_retrieval_service
from app.core.security import get_current_active_user

router = APIRouter()


@router.post("/api/chat/debug")
async def chat_debug(data: dict):
    """Debug endpoint to see raw request data"""
    logger.info(f"Raw request data: {data}")
    return {"received": data}


@router.post("/api/chat")
async def chat(
    request: RequestObject,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
):
    """
    Stream chat responses from the stock analyst agent with RAG (Retrieval-Augmented Generation).

    Requires authentication via JWT token.

    Flow:
    1. Retrieve relevant past context from pgvector based on user query
    2. Include retrieved context in system message
    3. Stream agent response
    4. Store conversation turn in PostgreSQL (async background task)

    Args:
        request: Chat request object containing prompt, thread ID, and response ID
        background_tasks: FastAPI background tasks for storing conversation
        current_user: Current authenticated user from JWT token

    Returns:
        Streaming response with agent output
    """
    config = {"configurable": {"thread_id": request.threadId}}
    user_message = request.prompt.content
    thread_id = request.threadId
    user_id = current_user.id  # Extract user ID from authenticated user

    logger.info(
        f"Received chat request - Thread ID: {thread_id}, User ID: {user_id}, Message: {user_message[:100]}..."
    )

    # STEP 1: Retrieve relevant context from pgvector (RAG)
    context_retrieval = get_context_retrieval_service()
    relevant_contexts = await context_retrieval.retrieve_relevant_context(
        query=user_message,
        thread_id=thread_id,
        user_id=user_id,
        top_k=5,
    )

    # STEP 2: Format context for prompt and count tokens
    context_text = context_retrieval.format_context_for_prompt(relevant_contexts)
    context_tokens = count_tokens(context_text) if context_text else 0

    # Log context retrieval metrics
    if relevant_contexts:
        avg_relevance = sum(c["relevance_score"] for c in relevant_contexts) / len(relevant_contexts)
        logger.info(
            f"RAG: Retrieved {len(relevant_contexts)} context chunks "
            f"({context_tokens} tokens, avg relevance: {avg_relevance:.3f})"
        )
    else:
        logger.info(f"RAG: No relevant context found for thread {thread_id}")

    # Track the full response for storage
    full_response = [""]  # Use list to allow mutation in nested function
    total_input_tokens = [0]  # Use list to allow mutation in nested function

    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Count tokens in the current message
            current_message_tokens = count_tokens(user_message)
            total_input_tokens[0] = current_message_tokens + context_tokens
            logger.info(
                f"Token count - Message: {current_message_tokens}, "
                f"Context: {context_tokens}, Total: {total_input_tokens[0]}"
            )

            # STEP 3: Build messages for the agent
            # Pass system prompt + context + user message directly in stream call (reference pattern)
            # Include user's preferred currency in system message
            user_currency = current_user.preferred_currency or "USD"
            base_system_message = get_system_message(user_currency=user_currency)

            if context_text:
                # Enhance system message with context
                enhanced_system_content = f"""{base_system_message.content}

RELEVANT PAST CONVERSATION CONTEXT:
{context_text}

Use the above context to provide context-aware responses."""
                system_msg = SystemMessage(content=enhanced_system_content)
            else:
                system_msg = base_system_message

            # STEP 4: Stream the response - exactly like reference project
            token_count = 0
            for token, _ in agent.stream(
                {"messages": [system_msg, HumanMessage(user_message)]},
                stream_mode="messages",
                config=config
            ):
                token_count += 1
                content = token.content if hasattr(token, 'content') else ""
                logger.debug(f"Token {token_count}: type={type(token).__name__}, has_content={bool(content)}, content_preview={content[:50] if content else 'EMPTY'}")

                # Yield content if it exists
                if content:
                    full_response[0] += content
                    yield content

            logger.info(f"Streaming complete. Total response: {len(full_response[0])} chars, {token_count} tokens processed")

        except Exception as e:
            import traceback
            error_message = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"Error in chat endpoint: {error_message}\n{error_traceback}")

            if "tokens exceed" in error_message.lower() or "token limit" in error_message.lower():
                error_msg = "\n\nError: Conversation has exceeded the token limit. Please clear the conversation and start fresh."
            else:
                error_msg = f"\n\nError: {error_message}"

            full_response[0] += error_msg
            yield error_msg

        finally:
            # STEP 5: Store conversation turn in PostgreSQL (async background task)
            # Use FastAPI's BackgroundTasks to store after streaming completes
            background_tasks.add_task(
                store_conversation_context,
                thread_id=thread_id,
                user_id=user_id,
                user_message=user_message,
                assistant_response=full_response[0],
                tokens=total_input_tokens[0] + count_tokens(full_response[0]),
            )

    # Create streaming response with plain text (GenUI SDK expects plain text streaming)
    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )


async def store_conversation_context(
    thread_id: str,
    user_id: int,
    user_message: str,
    assistant_response: str,
    tokens: int,
):
    """
    Background task to store conversation turn with embeddings.

    This runs asynchronously after the response is sent to the user,
    so storage delays don't affect response time.

    Args:
        thread_id: Conversation thread identifier
        user_id: User identifier
        user_message: User's message
        assistant_response: Assistant's response
        tokens: Total token count for this turn
    """
    try:
        context_storage = get_context_storage_service()
        success = await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=user_id,
            user_message=user_message,
            assistant_response=assistant_response,
            tokens=tokens,
        )

        if success:
            logger.info(f"Successfully stored conversation context for thread {thread_id}")
        else:
            logger.warning(
                f"Failed to store conversation context for thread {thread_id} (embeddings may not be configured)"
            )

    except Exception as e:
        # Log but don't raise - storage failures shouldn't affect chat
        logger.error(f"Error in background context storage: {e}")
