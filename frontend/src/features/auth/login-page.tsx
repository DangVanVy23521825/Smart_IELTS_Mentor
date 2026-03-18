import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from './use-auth'
import { describeHttpError, normalizeApiError } from '../../shared/api/errors'
import { ErrorCallout } from '../../shared/ui/error-callout'

const loginSchema = z.object({
  email: z.email('Email không hợp lệ'),
  password: z.string().min(8, 'Mật khẩu tối thiểu 8 ký tự'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/writing/new'

  const form = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  const mutation = useMutation({
    mutationFn: (data: LoginForm) => auth.login(data),
    onSuccess: () => navigate(redirectTo, { replace: true }),
  })

  const errorMessage = mutation.error ? describeHttpError(normalizeApiError(mutation.error)) : null

  return (
    <section className="card auth-card">
      <h1>Đăng nhập</h1>
      <p className="muted">Truy cập hệ thống chấm IELTS Writing Task 2.</p>
      <ErrorCallout message={errorMessage} />
      <form
        className="stack"
        onSubmit={form.handleSubmit((data) => {
          mutation.mutate(data)
        })}
      >
        <label className="stack-xs">
          <span>Email</span>
          <input type="email" {...form.register('email')} />
          <small>{form.formState.errors.email?.message}</small>
        </label>
        <label className="stack-xs">
          <span>Mật khẩu</span>
          <input type="password" {...form.register('password')} />
          <small>{form.formState.errors.password?.message}</small>
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </button>
      </form>
      <p className="muted">
        Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
      </p>
    </section>
  )
}
