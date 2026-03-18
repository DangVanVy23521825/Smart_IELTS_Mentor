import { apiRequest } from './http'
import type {
  LoginRequest,
  LogoutRequest,
  RefreshTokenRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from '../types/api'

export function register(payload: RegisterRequest): Promise<UserResponse> {
  return apiRequest<UserResponse>('/auth/register', {
    method: 'POST',
    body: payload,
    skipAuth: true,
    skipAutoRefresh: true,
  })
}

export function login(payload: LoginRequest): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: payload,
    skipAuth: true,
    skipAutoRefresh: true,
  })
}

export function refreshTokens(payload: RefreshTokenRequest): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/refresh', {
    method: 'POST',
    body: payload,
    skipAuth: true,
    skipAutoRefresh: true,
  })
}

export function logout(payload: LogoutRequest): Promise<{ status: string }> {
  return apiRequest<{ status: string }>('/auth/logout', {
    method: 'POST',
    body: payload,
    skipAutoRefresh: true,
  })
}
