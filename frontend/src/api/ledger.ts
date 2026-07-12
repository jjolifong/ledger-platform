import { apiFetch, ApiError, parseErrorMessage, readJson } from './client'
import type {
  ApiErrorBody,
  LedgerListResponse,
  LedgerRow,
  LedgerWritableFields,
} from '../types'

export type LedgerSortField =
  | 'name'
  | 'gender'
  | 'category'
  | 'car_number'
  | 'car_model'
  | 'phone'
  | 'registered_at'
  | 'period_start'
  | 'period_end'
  | 'note'
  | 'created_at'

export async function list(
  search?: string,
  sort?: LedgerSortField,
  order: 'asc' | 'desc' = 'asc',
): Promise<LedgerListResponse> {
  const params = new URLSearchParams()
  if (search?.trim()) {
    params.set('search', search.trim())
  }
  if (sort) {
    params.set('sort', sort)
  }
  params.set('order', order)

  const response = await apiFetch(`/api/ledger?${params.toString()}`)
  const body = await readJson<LedgerListResponse & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  return {
    items: body?.items ?? [],
    total: body?.total ?? 0,
  }
}

export async function create(data: LedgerWritableFields): Promise<LedgerRow> {
  const response = await apiFetch('/api/ledger', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  const body = await readJson<LedgerRow & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  if (!body?.id) {
    throw new ApiError(response.status, '생성 응답이 올바르지 않습니다')
  }
  return body
}

export async function update(
  id: string,
  data: Partial<LedgerWritableFields>,
): Promise<LedgerRow> {
  const response = await apiFetch(`/api/ledger/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
  const body = await readJson<LedgerRow & ApiErrorBody>(response)
  if (!response.ok) {
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
  if (!body?.id) {
    throw new ApiError(response.status, '수정 응답이 올바르지 않습니다')
  }
  return body
}

export async function remove(id: string): Promise<void> {
  const response = await apiFetch(`/api/ledger/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const body = await readJson<ApiErrorBody>(response)
    throw new ApiError(response.status, parseErrorMessage(response.status, body))
  }
}
