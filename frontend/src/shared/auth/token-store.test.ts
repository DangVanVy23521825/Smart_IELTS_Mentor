import { afterEach, describe, expect, it } from 'vitest'
import { clearTokens, getAccessToken, getRefreshToken, hasSessionTokens, setTokens } from './token-store'

describe('token-store', () => {
  afterEach(() => {
    clearTokens()
  })

  it('persists access/refresh tokens in localStorage', () => {
    setTokens('access-a', 'refresh-b')

    expect(getAccessToken()).toBe('access-a')
    expect(getRefreshToken()).toBe('refresh-b')
    expect(hasSessionTokens()).toBe(true)
  })

  it('clears all tokens', () => {
    setTokens('access-a', 'refresh-b')
    clearTokens()

    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(hasSessionTokens()).toBe(false)
  })
})
