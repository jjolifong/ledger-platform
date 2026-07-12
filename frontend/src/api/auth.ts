import { apiFetch, ApiError, parseErrorMessage, readJson } from './client'
import type { ApiErrorBody, LoginResponse, User } from '../types'

export async function login(username: string, password: string): Promise<User> {
  const response = await apiFetch('/api/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  const body = await readJson<LoginResponse & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  if (!body?.username || !body?.role) {
    throw new ApiError(response.status, '로그인 응답이 올바르지 않습니다')
  }
  return { username: body.username, role: body.role }
}

export async function logout(): Promise<void> {
  const response = await apiFetch('/api/logout', { method: 'POST' })
  if (!response.ok && response.status !== 401) {
    const body = await readJson<ApiErrorBody>(response)
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
}

export async function me(): Promise<User | null> {
  const response = await apiFetch('/api/me')
  if (response.status === 401) {
    return null
  }
  const body = await readJson<User & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  if (!body?.username || !body?.role) {
    return null
  }
  return { username: body.username, role: body.role }
}
