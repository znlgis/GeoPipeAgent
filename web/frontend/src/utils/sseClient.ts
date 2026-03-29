export interface SSEOptions {
  onMessage?: (event: string, data: any) => void
  onError?: (error: any) => void
  onDone?: () => void
  /** Called when a reconnection attempt starts (attempt number, delay ms). */
  onReconnect?: (attempt: number, delay: number) => void
  /** Maximum number of reconnection attempts (default: 3). */
  maxRetries?: number
}

/**
 * Parse SSE stream from a ReadableStream reader.
 * Returns true if the stream ended normally, false if aborted.
 */
async function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  options: SSEOptions,
): Promise<boolean> {
  const decoder = new TextDecoder()
  let buffer = ''
  let receivedDone = false

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let currentEvent = 'message'
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        const dataStr = line.slice(6)
        try {
          const data = JSON.parse(dataStr)
          if (currentEvent === 'done') {
            options.onMessage?.(currentEvent, data)
            receivedDone = true
          } else {
            options.onMessage?.(currentEvent, data)
          }
        } catch {
          options.onMessage?.(currentEvent, dataStr)
        }
      }
    }
  }

  return receivedDone
}

export function createSSEConnection(
  url: string,
  body: any,
  options: SSEOptions,
): AbortController {
  const controller = new AbortController()
  const maxRetries = options.maxRetries ?? 3
  let attempt = 0

  async function connect() {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }))
        options.onError?.(errorData)
        return
      }

      const reader = response.body?.getReader()
      if (!reader) return

      // Reset attempt counter on successful connection
      attempt = 0
      const receivedDone = await parseSSEStream(reader, options)

      if (receivedDone) {
        options.onDone?.()
      } else if (!controller.signal.aborted) {
        // Stream ended without a 'done' event — attempt reconnection
        await maybeReconnect()
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        return
      }

      // Network error — attempt reconnection with exponential backoff
      if (attempt < maxRetries && !controller.signal.aborted) {
        await maybeReconnect()
      } else {
        options.onError?.(err)
      }
    }
  }

  async function maybeReconnect() {
    if (controller.signal.aborted || attempt >= maxRetries) {
      options.onDone?.()
      return
    }

    attempt++
    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 16000)
    options.onReconnect?.(attempt, delay)

    await new Promise<void>((resolve) => {
      const timer = setTimeout(resolve, delay)
      // If aborted during wait, resolve immediately
      controller.signal.addEventListener('abort', () => {
        clearTimeout(timer)
        resolve()
      }, { once: true })
    })

    if (!controller.signal.aborted) {
      await connect()
    }
  }

  connect()
  return controller
}
