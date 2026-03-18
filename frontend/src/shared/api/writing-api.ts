import { apiRequest } from './http'
import type { JobEnqueuedResponse, JobStatusResponse, SubmissionResultResponse, SubmitWritingRequest } from '../types/api'

export function submitWriting(payload: SubmitWritingRequest): Promise<JobEnqueuedResponse> {
  return apiRequest<JobEnqueuedResponse>('/submissions/writing', {
    method: 'POST',
    body: payload,
  })
}

export function getJob(jobId: string): Promise<JobStatusResponse> {
  return apiRequest<JobStatusResponse>(`/jobs/${jobId}`)
}

export function getSubmission(submissionId: string): Promise<SubmissionResultResponse> {
  return apiRequest<SubmissionResultResponse>(`/submissions/${submissionId}`)
}
