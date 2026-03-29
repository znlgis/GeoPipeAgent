export interface SSEOptions {
  onMessage?: (event: string, data: any) => void
  onError?: (error: any) => void
  onDone?: () => void
}

export function createSSEConnection(
  url: string,
  body: any,
  options: SSEOptions,
): AbortController {
  const controller = new AbortController()

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ message: response.statusText }))
        options.onError?.(errorData)
        return
      }
      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''

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
                options.onDone?.()
              } else {
                options.onMessage?.(currentEvent, data)
              }
            } catch {
              options.onMessage?.(currentEvent, dataStr)
            }
          }
        }
      }
      options.onDone?.()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        options.onError?.(err)
      }
    })

  return controller
}
