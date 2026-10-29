export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  const data = await response.json()
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map(item => `${item.loc.slice(1).join('.')}: ${item.msg}`).join('; ')
      : data.detail
    const error = new Error(detail || 'The request could not be completed.')
    error.fieldErrors = Array.isArray(data.detail)
      ? Object.fromEntries(data.detail.filter(item => item.loc?.[0] === 'body' && typeof item.loc[1] === 'string')
        .map(item => [item.loc[1], item.msg.replace(/^Value error, /, '')]))
      : {}
    throw error
  }
  return data
}
