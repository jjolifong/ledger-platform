import { apiFetch, ApiError, parseErrorMessage, readJson } from './client'
import type {
  AccountListResponse,
  AccountUser,
  ApiErrorBody,
  UserRole,
} from '../types'

export async function listUsers(): Promise<AccountListResponse> {
  const response = await apiFetch('/api/users')
  const body = await readJson<AccountListResponse & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  return {
    items: body?.items ?? [],
    total: body?.total ?? 0,
  }
}

export async function createUser(
  username: string,
  password: string,
  role: UserRole,
): Promise<AccountUser> {
  const response = await apiFetch('/api/users', {
    method: 'POST',
    body: JSON.stringify({ username, password, role }),
  })
  const body = await readJson<AccountUser & ApiErrorBody>(response)
  if (!response.ok) {
    if (response.status === 409) {
      throw new ApiError(409, '이미 존재하는 아이디')
    }
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  if (!body?.username) {
    throw new ApiError(response.status, '계정 생성 응답이 올바르지 않습니다')
  }
  return body
}

export async function updateUser(
  username: string,
  data: {
    role?: UserRole
    is_active?: 0 | 1
    reset_password?: boolean
  },
): Promise<AccountUser> {
  const response = await apiFetch(`/api/users/${encodeURIComponent(username)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
  const body = await readJson<AccountUser & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  if (!body?.username) {
    throw new ApiError(response.status, '계정 수정 응답이 올바르지 않습니다')
  }
  return body
}
