import { useEffect, useMemo, useState, type ReactNode } from 'react'
import * as authApi from '../../shared/api/auth-api'
import { configureAuthHandlers } from '../../shared/api/http'
import { clearTokens, getRefreshToken, hasSessionTokens, setTokens } from '../../shared/auth/token-store'
import type { TokenResponse } from '../../shared/types/api'
import { AuthContext, type AuthContextValue } from './auth-context-def'

async function refreshWithStoredToken(): Promise<TokenResponse | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null

  try {
    const tokens = await authApi.refreshTokens({ refresh_token: refreshToken })
    setTokens(tokens.access_token, tokens.refresh_token)
    return tokens
  } catch {
    clearTokens()
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(hasSessionTokens())

  const value = useMemo<AuthContextValue>(() => {
    const forceLogout = () => {
      clearTokens()
      setIsAuthenticated(false)
    }

    return {
      isAuthenticated,
      async register(payload) {
        await authApi.register(payload)
      },
      async login(payload) {
        const tokens = await authApi.login(payload)
        setTokens(tokens.access_token, tokens.refresh_token)
        setIsAuthenticated(true)
      },
      async logout() {
        const refreshToken = getRefreshToken()
        try {
          if (refreshToken) {
            await authApi.logout({ refresh_token: refreshToken })
          }
        } finally {
          forceLogout()
        }
      },
      forceLogout,
    }
  }, [isAuthenticated])

  useEffect(() => {
    configureAuthHandlers({
      onRefresh: refreshWithStoredToken,
      onUnauthorized: () => {
        clearTokens()
        setIsAuthenticated(false)
      },
    })
  }, [])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
