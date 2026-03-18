import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { submitFeedback } from '../../shared/api/feedback-api'
import { describeHttpError, normalizeApiError } from '../../shared/api/errors'
import { ErrorCallout } from '../../shared/ui/error-callout'

const feedbackSchema = z.object({
  rating: z
    .string()
    .optional()
    .refine((value) => !value || (Number(value) >= 1 && Number(value) <= 5), 'Rating phải từ 1 đến 5'),
  message: z.string().optional(),
})

type FeedbackForm = z.infer<typeof feedbackSchema>

export function FeedbackForm({ submissionId }: { submissionId: string }) {
  const form = useForm<FeedbackForm>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: { rating: undefined, message: '' },
  })

  const mutation = useMutation({
    mutationFn: (data: FeedbackForm) =>
      submitFeedback({
        submission_id: submissionId,
        rating: data.rating ? Number(data.rating) : null,
        message: data.message?.trim() || null,
      }),
  })

  const errorMessage = mutation.error ? describeHttpError(normalizeApiError(mutation.error)) : null

  return (
    <section className="card">
      <h2>Gửi feedback</h2>
      <ErrorCallout message={errorMessage} />
      <form className="stack" onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
        <label className="stack-xs">
          <span>Rating</span>
          <select {...form.register('rating')}>
            <option value="">Chọn rating</option>
            <option value="1">1 - Rất tệ</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
            <option value="5">5 - Rất tốt</option>
          </select>
          <small>{form.formState.errors.rating?.message}</small>
        </label>
        <label className="stack-xs">
          <span>Nhận xét</span>
          <textarea rows={4} {...form.register('message')} placeholder="Điểm nào hữu ích, điểm nào cần cải thiện..." />
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Đang gửi...' : mutation.isSuccess ? 'Đã gửi' : 'Gửi feedback'}
        </button>
      </form>
    </section>
  )
}
