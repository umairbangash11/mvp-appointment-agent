export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const getHeaders = (): HeadersInit => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

const redirectToLogin = () => {
  if (typeof window === 'undefined') return
  localStorage.removeItem('token')
  localStorage.removeItem('refresh_token')
  window.location.href = '/login'
}

/**
 * Fetch with auth headers.
 * On 401: tries to refresh the access token once using refresh_token.
 * If refresh also fails → clears tokens and redirects to /login.
 */
export const authFetch = async (
  path: string,
  options: RequestInit = {},
  _isRetry = false,
): Promise<Response> => {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...getHeaders(),
      ...(options.headers as Record<string, string> ?? {}),
    },
  })

  if (res.status === 401 && !_isRetry) {
    const refreshToken = typeof window !== 'undefined'
      ? localStorage.getItem('refresh_token')
      : null

    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })

        if (refreshRes.ok) {
          const data = await refreshRes.json()
          localStorage.setItem('token', data.access_token)
          if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
          // Retry original request once with new token
          return authFetch(path, options, true)
        }
      } catch { /* fall through to redirect */ }
    }

    redirectToLogin()
  }

  return res
}
