import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <section className="card">
      <h1>Smart IELTS Mentor</h1>
      <p className="muted">Frontend MVP cho luồng chấm Writing Task 2.</p>
      <Link to="/writing/new">Bắt đầu nộp bài</Link>
    </section>
  )
}
