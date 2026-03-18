const ACCESS_TOKEN_KEY = 'sim_access_token'
const REFRESH_TOKEN_KEY = 'sim_refresh_token'

function hasWindow(): boolean {
  return typeof window !== 'undefined'
}

export function getAccessToken(): string | null {
  if (!hasWindow()) return null
  return window.localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  if (!hasWindow()) return null
  return window.localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (!hasWindow()) return
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function clearTokens(): void {
  if (!hasWindow()) return
  window.localStorage.removeItem(ACCESS_TOKEN_KEY)
  window.localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function hasSessionTokens(): boolean {
  return Boolean(getAccessToken() && getRefreshToken())
}
