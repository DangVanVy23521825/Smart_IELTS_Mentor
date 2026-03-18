import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="card">
      <h1>404</h1>
      <p>Không tìm thấy trang bạn yêu cầu.</p>
      <Link to="/writing/new">Quay về trang viết bài</Link>
    </section>
  )
}
