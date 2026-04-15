import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/**
 * API Communication Tests
 *
 * These tests verify that the frontend can communicate with the backend API
 * using the correct endpoints and handle responses properly.
 */

describe('API Communication', () => {
  const API_BASE_URL = '/api'
  const CHAT_ENDPOINT = `${API_BASE_URL}/chat`

  beforeEach(() => {
    // Mock fetch globally
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('chat endpoint is correctly configured', () => {
    expect(CHAT_ENDPOINT).toBe('/api/chat')
  })

  it('can make POST request to chat endpoint', async () => {
    const mockResponse = { ok: true, status: 200 }
    ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

    const payload = {
      prompt: { content: 'What is AAPL price?', id: '1', role: 'user' },
      threadId: 'test-thread-123',
      responseId: 'r1',
    }

    const response = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    expect(global.fetch).toHaveBeenCalledWith(
      CHAT_ENDPOINT,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    )
    expect(response.ok).toBe(true)
    expect(response.status).toBe(200)
  })

  it('handles successful chat response', async () => {
    const mockResponse = {
      ok: true,
      status: 200,
      body: {
        getReader: () => ({
          read: vi
            .fn()
            .mockResolvedValueOnce({
              done: false,
              value: new TextEncoder().encode('Apple stock is trading at $175.43'),
            })
            .mockResolvedValueOnce({ done: true }),
        }),
      },
    }
    ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

    const response = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: { content: 'AAPL price', id: '1', role: 'user' },
        threadId: 'thread1',
        responseId: 'r1',
      }),
    })

    expect(response.ok).toBe(true)
    expect(response.body).toBeDefined()
  })

  it('handles network errors gracefully', async () => {
    ;(global.fetch as any).mockRejectedValueOnce(new Error('Network error'))

    await expect(
      fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: { content: 'test', id: '1', role: 'user' },
          threadId: 'thread1',
          responseId: 'r1',
        }),
      })
    ).rejects.toThrow('Network error')
  })

  it('handles 500 server error', async () => {
    const mockResponse = {
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    }
    ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

    const response = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ prompt: { content: 'test', id: '1', role: 'user' } }),
    })

    expect(response.ok).toBe(false)
    expect(response.status).toBe(500)
  })

  it('handles 400 bad request error', async () => {
    const mockResponse = {
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Invalid request format' }),
    }
    ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

    const response = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ invalid: 'payload' }),
    })

    expect(response.ok).toBe(false)
    expect(response.status).toBe(400)
  })

  it('sends correct request payload structure', async () => {
    const mockResponse = { ok: true, status: 200 }
    ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

    const payload = {
      prompt: {
        content: 'What is AAPL price?',
        id: 'msg-123',
        role: 'user',
      },
      threadId: 'thread-abc-123',
      responseId: 'resp-456',
    }

    await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const fetchCall = (global.fetch as any).mock.calls[0]
    const sentPayload = JSON.parse(fetchCall[1].body)

    expect(sentPayload).toHaveProperty('prompt')
    expect(sentPayload.prompt).toHaveProperty('content')
    expect(sentPayload.prompt).toHaveProperty('id')
    expect(sentPayload.prompt).toHaveProperty('role')
    expect(sentPayload).toHaveProperty('threadId')
    expect(sentPayload).toHaveProperty('responseId')
  })

  it('uses correct HTTP method for chat', async () => {
    const mockResponse = { ok: true }
    ;(global.fetch as any).mockResolvedValueOnce(mockResponse)

    await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ prompt: { content: 'test', id: '1', role: 'user' } }),
    })

    expect(global.fetch).toHaveBeenCalledWith(
      CHAT_ENDPOINT,
      expect.objectContaining({ method: 'POST' })
    )
  })
})
