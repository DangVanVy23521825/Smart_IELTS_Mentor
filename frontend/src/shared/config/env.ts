const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const apiPrefix = import.meta.env.VITE_API_PREFIX ?? '/api/v1'

export const env = {
  apiBaseUrl: baseUrl,
  apiPrefix,
}
