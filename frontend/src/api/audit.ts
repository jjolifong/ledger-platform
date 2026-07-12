import { apiFetch, ApiError, parseErrorMessage, readJson } from './client'
import type { ApiErrorBody, AuditLogListResponse } from '../types'

export type AuditFilters = {
  table_name?: string
  username?: string
  result?: string
  limit?: number
}

export async function listAuditLogs(filters: AuditFilters = {}): Promise<AuditLogListResponse> {
  const params = new URLSearchParams()
  if (filters.table_name) {
    params.set('table_name', filters.table_name)
  }
  if (filters.username?.trim()) {
    params.set('username', filters.username.trim())
  }
  if (filters.result) {
    params.set('result', filters.result)
  }
  if (filters.limit) {
    params.set('limit', String(filters.limit))
  }

  const query = params.toString()
  const response = await apiFetch(`/api/audit-log${query ? `?${query}` : ''}`)
  const body = await readJson<AuditLogListResponse & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  return {
    items: body?.items ?? [],
    total: body?.total ?? 0,
  }
}
