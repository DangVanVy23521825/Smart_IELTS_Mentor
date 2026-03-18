import { apiRequest } from './http'
import type { FeedbackCreateRequest, FeedbackCreateResponse } from '../types/api'

export function submitFeedback(payload: FeedbackCreateRequest): Promise<FeedbackCreateResponse> {
  return apiRequest<FeedbackCreateResponse>('/feedback', {
    method: 'POST',
    body: payload,
  })
}
