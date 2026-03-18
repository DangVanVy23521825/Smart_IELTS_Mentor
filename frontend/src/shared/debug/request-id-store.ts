let lastRequestId: string | null = null
const listeners = new Set<(value: string | null) => void>()

export function setLastRequestId(value: string | null): void {
  lastRequestId = value
  listeners.forEach((listener) => listener(value))
}

export function getLastRequestId(): string | null {
  return lastRequestId
}

export function subscribeRequestId(listener: (value: string | null) => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}
