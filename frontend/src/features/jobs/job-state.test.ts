import { describe, expect, it } from 'vitest'
import { computePollingIntervalMs, isJobTerminal } from './job-state'

describe('job-state helpers', () => {
  it('returns terminal status correctly', () => {
    expect(isJobTerminal('succeeded')).toBe(true)
    expect(isJobTerminal('failed')).toBe(true)
    expect(isJobTerminal('queued')).toBe(false)
    expect(isJobTerminal('running')).toBe(false)
  })

  it('calculates polling interval with backoff', () => {
    expect(computePollingIntervalMs(0, false)).toBe(2000)
    expect(computePollingIntervalMs(6, false)).toBe(3000)
    expect(computePollingIntervalMs(11, false)).toBe(5000)
    expect(computePollingIntervalMs(20, false)).toBe(8000)
    expect(computePollingIntervalMs(20, true)).toBe(false)
  })
})
