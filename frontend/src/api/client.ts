import type { ApiErrorBody } from '../types'

type UnauthorizedHandler = () => void

let unauthorizedHandler: UnauthorizedHandler | null = null

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function parseErrorMessage(status: number, body: ApiErrorBody | null): string {
  const detail = body?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  if (status === 423) {
    return '계정이 잠겼습니다. 관리자에게 문의하세요'
  }
  if (status === 401) {
    return '아이디 또는 비밀번호가 올바르지 않습니다'
  }
  return '요청을 처리할 수 없습니다'
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(input, {
    ...init,
    headers,
    credentials: 'include',
  })

  if (response.status === 401) {
    unauthorizedHandler?.()
  }

  return response
}

export async function readJson<T>(response: Response): Promise<T | null> {
  const text = await response.text()
  if (!text) {
    return null
  }
  try {
    return JSON.parse(text) as T
  } catch {
    return null
  }
}
