import { useEffect, useState } from 'react'
import { getLastRequestId, subscribeRequestId } from './request-id-store'

export function RequestIdPanel() {
  const [requestId, setRequestId] = useState<string | null>(getLastRequestId())

  useEffect(() => subscribeRequestId(setRequestId), [])

  if (!requestId) return null

  return (
    <div className="request-id-panel">
      request_id: <code>{requestId}</code>
    </div>
  )
}
