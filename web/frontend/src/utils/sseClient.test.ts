import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createSSEConnection } from './sseClient'

describe('createSSEConnection', () => {
  let mockFetch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockFetch = vi.fn()
    vi.stubGlobal('fetch', mockFetch)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function createMockReadableStream(chunks: string[]): ReadableStream<Uint8Array> {
    const encoder = new TextEncoder()
    let index = 0
    return new ReadableStream({
      pull(controller) {
        if (index < chunks.length) {
          controller.enqueue(encoder.encode(chunks[index++]))
        } else {
          controller.close()
        }
      },
    })
  }

  it('returns an AbortController', () => {
    mockFetch.mockResolvedValue(
      new Response(createMockReadableStream([]), { status: 200 }),
    )
    const controller = createSSEConnection('/api/test', {}, {})
    expect(controller).toBeInstanceOf(AbortController)
  })

  it('parses SSE events and calls onMessage', async () => {
    const sseData =
      'event: chunk\ndata: {"content":"hello"}\n\nevent: done\ndata: {"result":"ok"}\n\n'
    mockFetch.mockResolvedValue(
      new Response(createMockReadableStream([sseData]), { status: 200 }),
    )

    const messages: Array<{ event: string; data: any }> = []
    const onDone = vi.fn()

    createSSEConnection('/api/test', { msg: 'hi' }, {
      onMessage: (event, data) => messages.push({ event, data }),
      onDone,
    })

    // Wait for stream to complete
    await new Promise((r) => setTimeout(r, 100))

    expect(messages).toHaveLength(2)
    expect(messages[0].event).toBe('chunk')
    expect(messages[0].data.content).toBe('hello')
    expect(messages[1].event).toBe('done')
    expect(onDone).toHaveBeenCalled()
  })

  it('calls onError for non-OK responses', async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const onError = vi.fn()
    createSSEConnection('/api/test', {}, { onError })

    await new Promise((r) => setTimeout(r, 100))
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ detail: 'not found' }),
    )
  })

  it('does not call onError when aborted', async () => {
    mockFetch.mockRejectedValue(new DOMException('Aborted', 'AbortError'))

    const onError = vi.fn()
    const controller = createSSEConnection('/api/test', {}, { onError })
    controller.abort()

    await new Promise((r) => setTimeout(r, 100))
    expect(onError).not.toHaveBeenCalled()
  })

  it('sends POST request with correct body', async () => {
    mockFetch.mockResolvedValue(
      new Response(createMockReadableStream([]), { status: 200 }),
    )

    createSSEConnection('/api/test', { key: 'value' }, {})

    await new Promise((r) => setTimeout(r, 50))

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'value' }),
      }),
    )
  })
})
