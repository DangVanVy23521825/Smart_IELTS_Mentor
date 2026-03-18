import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from './use-auth'
import { describeHttpError, normalizeApiError } from '../../shared/api/errors'
import { ErrorCallout } from '../../shared/ui/error-callout'

const registerSchema = z
  .object({
    email: z.email('Email không hợp lệ'),
    password: z.string().min(8, 'Mật khẩu tối thiểu 8 ký tự').max(128),
    confirmPassword: z.string().min(8, 'Mật khẩu tối thiểu 8 ký tự'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Mật khẩu xác nhận không khớp',
    path: ['confirmPassword'],
  })

type RegisterForm = z.infer<typeof registerSchema>

export function RegisterPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const form = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: '', password: '', confirmPassword: '' },
  })

  const mutation = useMutation({
    mutationFn: (data: RegisterForm) =>
      auth.register({
        email: data.email,
        password: data.password,
      }),
    onSuccess: () => navigate('/login', { replace: true }),
  })

  const errorMessage = mutation.error ? describeHttpError(normalizeApiError(mutation.error)) : null

  return (
    <section className="card auth-card">
      <h1>Tạo tài khoản</h1>
      <p className="muted">Đăng ký để bắt đầu nộp bài Writing.</p>
      <ErrorCallout message={errorMessage} />
      <form className="stack" onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
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
        <label className="stack-xs">
          <span>Nhập lại mật khẩu</span>
          <input type="password" {...form.register('confirmPassword')} />
          <small>{form.formState.errors.confirmPassword?.message}</small>
        </label>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Đang tạo tài khoản...' : 'Đăng ký'}
        </button>
      </form>
      <p className="muted">
        Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
      </p>
    </section>
  )
}
