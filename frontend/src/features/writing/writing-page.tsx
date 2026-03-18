import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm, useWatch } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { submitWriting } from '../../shared/api/writing-api'
import { describeHttpError, normalizeApiError } from '../../shared/api/errors'
import { ErrorCallout } from '../../shared/ui/error-callout'

const MAX_WORDS = 650

const writingSchema = z.object({
  prompt: z.string().optional(),
  text: z.string().min(1, 'Vui lòng nhập bài viết'),
})

type WritingForm = z.infer<typeof writingSchema>

function countWords(text: string): number {
  if (!text.trim()) return 0
  return text.trim().split(/\s+/).length
}

export function WritingPage() {
  const navigate = useNavigate()
  const form = useForm<WritingForm>({
    resolver: zodResolver(writingSchema),
    defaultValues: { prompt: '', text: '' },
  })
  const text = useWatch({ control: form.control, name: 'text' }) ?? ''
  const words = countWords(text)

  const mutation = useMutation({
    mutationFn: (data: WritingForm) =>
      submitWriting({
        prompt: data.prompt?.trim() || null,
        text: data.text,
      }),
    onSuccess: (response) => {
      navigate(`/jobs/${response.job_id}`, {
        state: { submissionId: response.submission_id },
      })
    },
  })

  const errorMessage = mutation.error ? describeHttpError(normalizeApiError(mutation.error)) : null

  return (
    <section className="card">
      <h1>Submit IELTS Writing Task 2</h1>
      <p className="muted">Nộp bài viết và hệ thống sẽ chấm điểm bằng pipeline RAG 2-phase.</p>
      <ErrorCallout message={errorMessage} />
      <form className="stack" onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
        <label className="stack-xs">
          <span>Đề bài (optional)</span>
          <textarea rows={3} {...form.register('prompt')} placeholder="Discuss both views and give your opinion..." />
        </label>
        <label className="stack-xs">
          <span>Bài viết</span>
          <textarea rows={12} {...form.register('text')} placeholder="Some people believe that..." />
          <div className="inline-between">
            <small>{form.formState.errors.text?.message}</small>
            <small className={words > MAX_WORDS ? 'danger-text' : 'muted'}>{words}/{MAX_WORDS} words</small>
          </div>
        </label>
        <button type="submit" disabled={mutation.isPending || words > MAX_WORDS || words === 0}>
          {mutation.isPending ? 'Đang gửi...' : 'Nộp bài'}
        </button>
      </form>
    </section>
  )
}
