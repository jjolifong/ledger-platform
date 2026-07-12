import { useCallback, useEffect, useState } from 'react'
import * as ledgerApi from '../api/ledger'
import type { LedgerSortField } from '../api/ledger'
import { ApiError } from '../api/client'
import LedgerForm from '../components/LedgerForm'
import { useAuth } from '../contexts/AuthContext'
import { navigate } from '../navigation'
import type { LedgerRow, LedgerWritableFields } from '../types'
import './LedgerPage.css'

type SortState = {
  field: LedgerSortField
  order: 'asc' | 'desc'
}

const SORTABLE_COLUMNS: { key: LedgerSortField; label: string }[] = [
  { key: 'name', label: '이름' },
  { key: 'gender', label: '성별' },
  { key: 'category', label: '구분' },
  { key: 'car_number', label: '차량번호' },
  { key: 'car_model', label: '차종' },
  { key: 'phone', label: '연락처' },
  { key: 'registered_at', label: '등록일' },
  { key: 'period_start', label: '등록기간' },
  { key: 'note', label: '비고' },
]

function formatPeriod(start: string | null, end: string | null): string {
  if (!start && !end) {
    return '-'
  }
  return `${start ?? '-'} ~ ${end ?? '-'}`
}

export default function LedgerPage() {
  const { user, logout } = useAuth()
  const canWrite = user?.role === 'write' || user?.role === 'admin'

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortState>({ field: 'created_at', order: 'desc' })
  const [items, setItems] = useState<LedgerRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [formMode, setFormMode] = useState<'create' | 'edit' | null>(null)
  const [editing, setEditing] = useState<LedgerRow | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  const loadList = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await ledgerApi.list(search, sort.field, sort.order)
      setItems(result.items)
      setTotal(result.total)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('목록을 불러오지 못했습니다')
      }
    } finally {
      setLoading(false)
    }
  }, [search, sort.field, sort.order])

  useEffect(() => {
    void loadList()
  }, [loadList])

  function toggleSort(field: LedgerSortField) {
    setSort((prev) => {
      if (prev.field === field) {
        return { field, order: prev.order === 'asc' ? 'desc' : 'asc' }
      }
      return { field, order: 'asc' }
    })
  }

  function openCreate() {
    setEditing(null)
    setFormMode('create')
  }

  function openEdit(row: LedgerRow) {
    setEditing(row)
    setFormMode('edit')
  }

  function closeForm() {
    if (submitting) {
      return
    }
    setFormMode(null)
    setEditing(null)
  }

  async function handleFormSubmit(
    payload: LedgerWritableFields | Partial<LedgerWritableFields>,
  ) {
    setSubmitting(true)
    setError(null)
    try {
      if (formMode === 'create') {
        await ledgerApi.create(payload as LedgerWritableFields)
      } else if (formMode === 'edit' && editing) {
        if (Object.keys(payload).length > 0) {
          await ledgerApi.update(editing.id, payload)
        }
      }
      setFormMode(null)
      setEditing(null)
      await loadList()
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('저장에 실패했습니다')
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(row: LedgerRow) {
    const ok = window.confirm(
      '이 항목을 삭제합니다. 관리자가 이력에서 확인할 수 있습니다.',
    )
    if (!ok) {
      return
    }
    setError(null)
    try {
      await ledgerApi.remove(row.id)
      await loadList()
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('삭제에 실패했습니다')
      }
    }
  }

  if (!user) {
    return null
  }

  return (
    <div className="ledger-page">
      <header className="ledger-topbar">
        <div className="topbar-left">
          <div className="brand">대장관리 플랫폼</div>
          <nav className="top-nav">
            <button type="button" className="nav-link active">
              대장
            </button>
            {user.role === 'admin' ? (
              <button type="button" className="nav-link" onClick={() => navigate('/admin')}>
                관리
              </button>
            ) : null}
          </nav>
        </div>
        <div className="topbar-right">
          <span className="user-chip">
            {user.username} ({user.role})
          </span>
          <button type="button" className="ghost-btn" onClick={() => void logout()}>
            로그아웃
          </button>
        </div>
      </header>

      <main className="ledger-main">
        <div className="ledger-toolbar">
          <div className="search-group">
            <label htmlFor="ledger-search">검색</label>
            <input
              id="ledger-search"
              placeholder="이름 또는 차량번호"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
          </div>
          <div className="toolbar-meta">
            <span>총 {total}건</span>
            {canWrite ? (
              <button type="button" className="primary-btn" onClick={openCreate}>
                + 신규 등록
              </button>
            ) : null}
          </div>
        </div>

        {error ? (
          <p className="page-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>연번</th>
                {SORTABLE_COLUMNS.map((col) => (
                  <th key={col.key}>
                    <button
                      type="button"
                      className="sort-btn"
                      onClick={() => toggleSort(col.key)}
                    >
                      {col.label}
                      {sort.field === col.key ? (sort.order === 'asc' ? ' ↑' : ' ↓') : ''}
                    </button>
                  </th>
                ))}
                {canWrite ? <th>관리</th> : null}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={canWrite ? 11 : 10} className="empty-cell">
                    불러오는 중…
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={canWrite ? 11 : 10} className="empty-cell">
                    표시할 데이터가 없습니다
                  </td>
                </tr>
              ) : (
                items.map((row, index) => (
                  <tr key={row.id}>
                    <td>{index + 1}</td>
                    <td>{row.name ?? '-'}</td>
                    <td>{row.gender ?? '-'}</td>
                    <td>{row.category ?? '-'}</td>
                    <td>{row.car_number}</td>
                    <td>{row.car_model ?? '-'}</td>
                    <td>{row.phone ?? '-'}</td>
                    <td>{row.registered_at ?? '-'}</td>
                    <td>{formatPeriod(row.period_start, row.period_end)}</td>
                    <td>{row.note ?? '-'}</td>
                    {canWrite ? (
                      <td className="actions-cell">
                        <button type="button" className="link-btn" onClick={() => openEdit(row)}>
                          수정
                        </button>
                        <button
                          type="button"
                          className="link-btn danger"
                          onClick={() => void handleDelete(row)}
                        >
                          삭제
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>

      {formMode ? (
        <LedgerForm
          key={`${formMode}-${editing?.id ?? 'new'}`}
          mode={formMode}
          initial={editing}
          submitting={submitting}
          onCancel={closeForm}
          onSubmit={handleFormSubmit}
        />
      ) : null}
    </div>
  )
}
