export type UserRole = 'read' | 'write' | 'admin'

export interface User {
  username: string
  role: UserRole
}

export interface LoginResponse {
  username: string
  role: UserRole
}

export interface ApiErrorBody {
  detail?: string | { msg: string }[]
}

export interface LedgerRow {
  id: string
  name: string | null
  gender: string | null
  address: string | null
  phone: string | null
  car_number: string
  car_model: string | null
  category: string | null
  registered_at: string | null
  period_start: string | null
  period_end: string | null
  note: string | null
  is_deleted: number
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type LedgerWritableFields = {
  name: string | null
  gender: string | null
  address: string | null
  phone: string | null
  car_number: string
  car_model: string | null
  category: string | null
  registered_at: string | null
  period_start: string | null
  period_end: string | null
  note: string | null
}

export interface LedgerListResponse {
  items: LedgerRow[]
  total: number
}

export interface AccountUser {
  username: string
  role: UserRole
  is_active: number
  failed_login_count: number
  last_login_at: string | null
  created_at: string
  temporary_password?: string
}

export interface AccountListResponse {
  items: AccountUser[]
  total: number
}

export interface AuditLogEntry {
  id: number
  table_name: string
  record_id: string | null
  action: string
  result: 'SUCCESS' | 'FAIL' | string
  old_value: string | null
  new_value: string | null
  username: string | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLogEntry[]
  total: number
}

