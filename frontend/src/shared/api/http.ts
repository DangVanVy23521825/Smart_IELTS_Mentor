import { env } from '../config/env'
import { setLastRequestId } from '../debug/request-id-store'
import { getAccessToken } from '../auth/token-store'
import { ApiError, type ApiValidationIssue } from './errors'
import type { TokenResponse } from '../types/api'

type RefreshHandler = () => Promise<TokenResponse | null>
type UnauthorizedHandler = () => void

let refreshHandler: RefreshHandler | null = null
let unauthorizedHandler: UnauthorizedHandler | null = null
let refreshInFlight: Promise<TokenResponse | null> | null = null

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  skipAuth?: boolean
  skipAutoRefresh?: boolean
  retrying?: boolean
}

export function configureAuthHandlers(handlers: {
  onRefresh: RefreshHandler
  onUnauthorized: UnauthorizedHandler
}): void {
  refreshHandler = handlers.onRefresh
  unauthorizedHandler = handlers.onUnauthorized
}

function tryParseJson(text: string): unknown {
  if (!text) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return null
  }
}

function asValidationIssues(input: unknown): ApiValidationIssue[] {
  if (!Array.isArray(input)) return []
  return input.filter((item): item is ApiValidationIssue => {
    if (!item || typeof item !== 'object') return false
    const maybe = item as Partial<ApiValidationIssue>
    return Array.isArray(maybe.loc) && typeof maybe.msg === 'string' && typeof maybe.type === 'string'
  })
}

async function refreshOnce(): Promise<TokenResponse | null> {
  if (!refreshHandler) return null
  if (!refreshInFlight) {
    refreshInFlight = refreshHandler().finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${env.apiBaseUrl}${env.apiPrefix}${path}`
  const headers = new Headers(options.headers ?? {})
  headers.set('Content-Type', 'application/json')

  if (!options.skipAuth) {
    const token = getAccessToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })

  const requestId = response.headers.get('x-request-id')
  setLastRequestId(requestId)

  if (response.status === 401 && !options.skipAuth && !options.skipAutoRefresh && !options.retrying) {
    const refreshed = await refreshOnce()
    if (refreshed?.access_token) {
      return apiRequest<T>(path, { ...options, retrying: true })
    }
    unauthorizedHandler?.()
  }

  const text = await response.text()
  const parsed = tryParseJson(text)

  if (!response.ok) {
    let detail = response.statusText || 'Request failed'
    let validationIssues: ApiValidationIssue[] = []

    if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
      const parsedDetail = (parsed as { detail?: unknown }).detail
      if (typeof parsedDetail === 'string') {
        detail = parsedDetail
      } else {
        validationIssues = asValidationIssues(parsedDetail)
        if (validationIssues[0]?.msg) {
          detail = validationIssues[0].msg
        }
      }
    }

    throw new ApiError({
      status: response.status,
      detail,
      validationIssues,
      requestId,
    })
  }

  if (!text) {
    return {} as T
  }
  return parsed as T
}
