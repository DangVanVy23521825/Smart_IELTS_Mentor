import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom'
import { AppLayout } from './layout'
import { HomePage } from './home-page'
import { NotFoundPage } from './not-found-page'
import { LoginPage } from '../features/auth/login-page'
import { RegisterPage } from '../features/auth/register-page'
import { JobStatusPage } from '../features/jobs/job-status-page'
import { SubmissionResultPage } from '../features/writing/submission-result-page'
import { WritingPage } from '../features/writing/writing-page'
import { ProtectedRoute, PublicRoute } from '../shared/ui/route-guard'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: (
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'writing/new',
        element: (
          <ProtectedRoute>
            <WritingPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'jobs/:jobId',
        element: (
          <ProtectedRoute>
            <JobStatusPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'submissions/:submissionId',
        element: (
          <ProtectedRoute>
            <SubmissionResultPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'login',
        element: (
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        ),
      },
      {
        path: 'register',
        element: (
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        ),
      },
      {
        path: 'home',
        element: <Navigate to="/" replace />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
