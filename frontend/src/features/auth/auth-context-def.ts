import { createContext } from 'react'
import type { LoginRequest, RegisterRequest } from '../../shared/types/api'

export type AuthContextValue = {
  isAuthenticated: boolean
  login: (payload: LoginRequest) => Promise<void>
  register: (payload: RegisterRequest) => Promise<void>
  logout: () => Promise<void>
  forceLogout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
