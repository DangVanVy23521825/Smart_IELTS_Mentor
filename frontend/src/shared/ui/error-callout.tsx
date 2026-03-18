type ErrorCalloutProps = {
  message: string | null
}

export function ErrorCallout({ message }: ErrorCalloutProps) {
  if (!message) return null
  return <div className="error-callout">{message}</div>
}
