import type { JobStatus } from '../../shared/types/api'

export function isJobTerminal(status: JobStatus): boolean {
  return status === 'succeeded' || status === 'failed'
}

export function computePollingIntervalMs(pollCount: number, hidden: boolean): number | false {
  if (hidden) return false
  if (pollCount < 5) return 2000
  if (pollCount < 10) return 3000
  if (pollCount < 15) return 5000
  return 8000
}
