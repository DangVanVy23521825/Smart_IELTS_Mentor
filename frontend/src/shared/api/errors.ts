export type ApiValidationIssue = {
  loc: Array<string | number>
  msg: string
  type: string
}

export class ApiError extends Error {
  status: number
  detail: string
  validationIssues: ApiValidationIssue[]
  requestId: string | null

  constructor(params: {
    status: number
    detail: string
    validationIssues?: ApiValidationIssue[]
    requestId?: string | null
  }) {
    super(params.detail)
    this.name = 'ApiError'
    this.status = params.status
    this.detail = params.detail
    this.validationIssues = params.validationIssues ?? []
    this.requestId = params.requestId ?? null
  }
}

export function normalizeApiError(error: unknown, fallback = 'Unexpected error'): ApiError {
  if (error instanceof ApiError) {
    return error
  }
  if (error instanceof Error) {
    return new ApiError({
      status: 0,
      detail: error.message || fallback,
    })
  }
  return new ApiError({ status: 0, detail: fallback })
}

export function describeHttpError(error: ApiError): string {
  switch (error.status) {
    case 401:
      return 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn.'
    case 404:
      return 'Không tìm thấy dữ liệu yêu cầu.'
    case 409:
      return 'Dữ liệu bị xung đột (ví dụ email đã tồn tại).'
    case 422:
      return error.validationIssues[0]?.msg ?? error.detail ?? 'Dữ liệu gửi lên chưa hợp lệ.'
    case 429:
      return 'Bạn đang thao tác quá nhanh. Vui lòng thử lại sau.'
    case 503:
      return 'Hệ thống tạm thời quá tải hoặc đang bảo trì.'
    default:
      return error.detail || 'Đã có lỗi xảy ra.'
  }
}
