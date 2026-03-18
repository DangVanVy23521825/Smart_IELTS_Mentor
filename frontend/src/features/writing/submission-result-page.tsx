import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { getSubmission } from '../../shared/api/writing-api'
import { describeHttpError, normalizeApiError } from '../../shared/api/errors'
import { ErrorCallout } from '../../shared/ui/error-callout'
import { FeedbackForm } from '../feedback/feedback-form'

export function SubmissionResultPage() {
  const { submissionId } = useParams<{ submissionId: string }>()

  const query = useQuery({
    queryKey: ['submission-result', submissionId],
    queryFn: () => getSubmission(submissionId ?? ''),
    enabled: Boolean(submissionId),
    refetchInterval: (state) => (state.state.data?.assessment ? false : 4000),
  })

  const data = query.data
  const assessment = data?.assessment
  const errorMessage = query.error ? describeHttpError(normalizeApiError(query.error)) : null

  return (
    <section className="stack-lg">
      <div className="card">
        <h1>Submission Result</h1>
        <ErrorCallout message={errorMessage} />
        {query.isLoading ? <p>Đang tải kết quả...</p> : null}
        {data ? (
          <div className="stack-xs">
            <p>
              <strong>Submission ID:</strong> {data.submission_id}
            </p>
            <p>
              <strong>Created at:</strong> {new Date(data.created_at).toLocaleString()}
            </p>
          </div>
        ) : null}
        {!assessment ? (
          <p>
            Kết quả chưa sẵn sàng. <Link to="/writing/new">Nộp bài khác</Link> hoặc chờ thêm một chút.
          </p>
        ) : null}
      </div>

      {assessment ? (
        <div className="card stack">
          <h2>Overall Band: {assessment.overall_band}</h2>
          <section className="stack">
            <h3>Criteria</h3>
            {assessment.criteria.map((criterion) => (
              <article key={criterion.criterion} className="criterion-item">
                <h4>
                  {criterion.criterion} - {criterion.band}
                </h4>
                <p>{criterion.justification}</p>
                {criterion.citations.length > 0 ? (
                  <details>
                    <summary>Citations ({criterion.citations.length})</summary>
                    <ul>
                      {criterion.citations.map((citation, idx) => (
                        <li key={`${criterion.criterion}-${idx}`}>{citation.snippet}</li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </article>
            ))}
          </section>

          <section className="stack">
            <h3>Error Analysis</h3>
            {assessment.errors.length === 0 ? (
              <p>Không có lỗi nổi bật.</p>
            ) : (
              <ul>
                {assessment.errors.map((error, idx) => (
                  <li key={`${error.type}-${idx}`}>
                    <strong>{error.type}</strong> ({error.severity}): {error.message}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="stack">
            <h3>Study Plan</h3>
            {assessment.study_plan.length === 0 ? (
              <p>Chưa có study plan.</p>
            ) : (
              <ol>
                {assessment.study_plan.map((item, idx) => (
                  <li key={`${item.focus_area}-${idx}`}>
                    <strong>{item.focus_area}</strong>
                    {item.activities.length > 0 ? (
                      <ul>
                        {item.activities.map((activity, aIdx) => (
                          <li key={`${item.focus_area}-${aIdx}`}>{activity}</li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      ) : null}

      {submissionId && assessment ? <FeedbackForm submissionId={submissionId} /> : null}
    </section>
  )
}
