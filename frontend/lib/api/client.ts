import { API_BASE_URL } from '@/lib/constants'
import type { ApiErrorBody } from '@/types/organizer'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly detail?: unknown
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export class NetworkError extends Error {
  constructor() {
    super('Unable to reach the ORDO backend. Is it running on localhost:8000?')
    this.name = 'NetworkError'
  }
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })
  } catch {
    throw new NetworkError()
  }

  if (!response.ok) {
    const body: ApiErrorBody = await response.json().catch(() => ({
      code: 'UNKNOWN_ERROR',
      message: `HTTP ${response.status}`,
    }))
    throw new ApiError(response.status, body.code, body.message, body.detail)
  }

  return response.json() as Promise<T>
}
