export type UserRole = 'user' | 'admin'

export interface RegisterRequest {
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
}

export interface UserResponse {
  id: string
  email: string
  role: UserRole
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface LogoutRequest {
  refresh_token: string
}

export interface SubmitWritingRequest {
  prompt?: string | null
  text: string
}

export interface JobEnqueuedResponse {
  submission_id: string
  job_id: string
}

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface JobStatusResponse {
  job_id: string
  submission_id: string
  status: JobStatus
  progress: number
  error_message?: string | null
}

export interface SubmissionResultResponse {
  submission_id: string
  type: string
  created_at: string
  assessment: WritingAssessmentV1 | null
}

export interface FeedbackCreateRequest {
  submission_id?: string | null
  rating?: number | null
  message?: string | null
  extra_data?: Record<string, unknown> | null
}

export interface FeedbackCreateResponse {
  id: string
  created_at: string
}

export interface Citation {
  source_type: string
  source_id?: string | null
  title?: string | null
  snippet: string
  criterion?: 'TR' | 'CC' | 'LR' | 'GRA' | null
  band?: number | null
}

export interface ErrorItem {
  type: string
  severity: 'low' | 'medium' | 'high'
  location?: string | null
  message: string
  suggestion: string
  fixed_example?: string | null
}

export interface StudyPlanItem {
  focus_area: string
  activities: string[]
}

export interface CriterionScore {
  criterion: 'TR' | 'CC' | 'LR' | 'GRA'
  band: number
  justification: string
  key_issues: string[]
  improvements: string[]
  citations: Citation[]
}

export interface WritingAssessmentV1 {
  schema_version: 'v1'
  submission_type: 'writing'
  task: 'task2'
  overall_band: number
  criteria: CriterionScore[]
  errors: ErrorItem[]
  study_plan: StudyPlanItem[]
  improved_version?: string | null
  citations: Citation[]
}
