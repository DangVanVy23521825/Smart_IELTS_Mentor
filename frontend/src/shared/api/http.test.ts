import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, configureAuthHandlers } from './http'
import { clearTokens, setTokens } from '../auth/token-store'
import { ApiError } from './errors'

function mockJsonResponse(status: number, body: unknown, headers?: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...(headers ?? {}),
    },
  })
}

describe('apiRequest auth refresh flow', () => {
  beforeEach(() => {
    clearTokens()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    clearTokens()
  })

  it('retries once after 401 when refresh succeeds', async () => {
    setTokens('old-access', 'refresh-token')

    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(mockJsonResponse(401, { detail: 'expired' }))
      .mockResolvedValueOnce(mockJsonResponse(200, { ok: true }, { 'x-request-id': 'req-1' }))

    configureAuthHandlers({
      onRefresh: async () => {
        setTokens('new-access', 'new-refresh')
        return { access_token: 'new-access', refresh_token: 'new-refresh', token_type: 'bearer' }
      },
      onUnauthorized: vi.fn(),
    })

    const response = await apiRequest<{ ok: boolean }>('/health')

    expect(response.ok).toBe(true)
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it('throws ApiError when response is non-2xx', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      mockJsonResponse(422, {
        detail: [{ loc: ['body', 'text'], msg: 'Field required', type: 'value_error' }],
      }),
    )

    configureAuthHandlers({
      onRefresh: async () => null,
      onUnauthorized: vi.fn(),
    })

    await expect(apiRequest('/submissions/writing', { method: 'POST', body: {} })).rejects.toBeInstanceOf(ApiError)
  })
})
