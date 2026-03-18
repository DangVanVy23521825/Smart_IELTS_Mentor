import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getJob } from '../../shared/api/writing-api'
import { describeHttpError, normalizeApiError } from '../../shared/api/errors'
import { ErrorCallout } from '../../shared/ui/error-callout'
import { computePollingIntervalMs, isJobTerminal } from './job-state'

export function JobStatusPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()

  const query = useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => getJob(jobId ?? ''),
    enabled: Boolean(jobId),
    refetchInterval: (queryState) => {
      const status = queryState.state.data?.status
      if (!status || isJobTerminal(status)) return false
      const pollCount = queryState.state.dataUpdateCount
      const hidden = typeof document !== 'undefined' ? document.hidden : false
      return computePollingIntervalMs(pollCount, hidden)
    },
  })

  useEffect(() => {
    if (query.data?.status === 'succeeded') {
      navigate(`/submissions/${query.data.submission_id}`)
    }
  }, [query.data, navigate])

  const statusLabel = useMemo(() => {
    const status = query.data?.status
    switch (status) {
      case 'queued':
        return 'Đang chờ worker xử lý'
      case 'running':
        return 'Đang chấm bài'
      case 'succeeded':
        return 'Hoàn tất'
      case 'failed':
        return 'Xử lý thất bại'
      default:
        return 'Đang tải...'
    }
  }, [query.data?.status])

  const errorMessage = query.error ? describeHttpError(normalizeApiError(query.error)) : null

  return (
    <section className="card">
      <h1>Job Status</h1>
      <p className="muted">Theo dõi tiến trình chấm bài theo thời gian thực.</p>
      <ErrorCallout message={errorMessage} />

      <div className="status-box">
        <p>
          <strong>Job ID:</strong> {jobId}
        </p>
        <p>
          <strong>Trạng thái:</strong> {statusLabel}
        </p>
        <p>
          <strong>Progress:</strong> {query.data?.progress ?? 0}%
        </p>
        {query.data?.error_message ? (
          <p className="danger-text">
            <strong>Lỗi:</strong> {query.data.error_message}
          </p>
        ) : null}
      </div>

      <div className="inline-gap">
        <button type="button" onClick={() => query.refetch()} disabled={query.isFetching}>
          {query.isFetching ? 'Đang refresh...' : 'Refresh ngay'}
        </button>
        {query.data?.status === 'failed' ? <Link to="/writing/new">Nộp lại bài</Link> : null}
      </div>
    </section>
  )
}
