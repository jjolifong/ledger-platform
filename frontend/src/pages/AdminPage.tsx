import { useCallback, useEffect, useState, type FormEvent } from 'react'
import * as auditApi from '../api/audit'
import { ApiError } from '../api/client'
import * as usersApi from '../api/users'
import { useAuth } from '../contexts/AuthContext'
import { navigate } from '../navigation'
import type { AccountUser, AuditLogEntry, UserRole } from '../types'
import './AdminPage.css'

type TabKey = 'accounts' | 'audit'

function formatJson(raw: string | null): string {
  if (!raw) {
    return '-'
  }
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

export default function AdminPage() {
  const { user, logout } = useAuth()
  const [tab, setTab] = useState<TabKey>('accounts')
  const [error, setError] = useState<string | null>(null)

  const [accounts, setAccounts] = useState<AccountUser[]>([])
  const [accountsLoading, setAccountsLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState<UserRole>('read')
  const [creating, setCreating] = useState(false)
  const [tempPassword, setTempPassword] = useState<string | null>(null)

  const [auditItems, setAuditItems] = useState<AuditLogEntry[]>([])
  const [auditLoading, setAuditLoading] = useState(false)
  const [tableFilter, setTableFilter] = useState('')
  const [usernameFilter, setUsernameFilter] = useState('')
  const [resultFilter, setResultFilter] = useState('')
  const [selectedAudit, setSelectedAudit] = useState<AuditLogEntry | null>(null)

  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/')
    }
  }, [user])

  const loadAccounts = useCallback(async () => {
    setAccountsLoading(true)
    setError(null)
    try {
      const result = await usersApi.listUsers()
      setAccounts(result.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '계정 목록을 불러오지 못했습니다')
    } finally {
      setAccountsLoading(false)
    }
  }, [])

  const loadAudit = useCallback(async () => {
    setAuditLoading(true)
    setError(null)
    try {
      const result = await auditApi.listAuditLogs({
        table_name: tableFilter || undefined,
        username: usernameFilter || undefined,
        result: resultFilter || undefined,
        limit: 100,
      })
      setAuditItems(result.items)
      setSelectedAudit((prev) => {
        if (!prev) {
          return null
        }
        return result.items.find((item) => item.id === prev.id) ?? null
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '이력을 불러오지 못했습니다')
    } finally {
      setAuditLoading(false)
    }
  }, [tableFilter, usernameFilter, resultFilter])

  useEffect(() => {
    if (user?.role === 'admin' && tab === 'accounts') {
      void loadAccounts()
    }
  }, [user, tab, loadAccounts])

  useEffect(() => {
    if (user?.role === 'admin' && tab === 'audit') {
      void loadAudit()
    }
  }, [user, tab, loadAudit])

  if (!user) {
    return null
  }

  if (user.role !== 'admin') {
    return (
      <div className="app-loading" role="status">
        대장 화면으로 이동 중…
      </div>
    )
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCreating(true)
    setError(null)
    try {
      await usersApi.createUser(newUsername.trim(), newPassword, newRole)
      setCreateOpen(false)
      setNewUsername('')
      setNewPassword('')
      setNewRole('read')
      await loadAccounts()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '계정 생성에 실패했습니다')
    } finally {
      setCreating(false)
    }
  }

  async function handleRoleChange(username: string, role: UserRole) {
    setError(null)
    try {
      await usersApi.updateUser(username, { role })
      await loadAccounts()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '역할 변경에 실패했습니다')
      await loadAccounts()
    }
  }

  async function handleToggleActive(account: AccountUser) {
    setError(null)
    try {
      await usersApi.updateUser(account.username, {
        is_active: account.is_active === 1 ? 0 : 1,
      })
      await loadAccounts()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '활성 상태 변경에 실패했습니다')
    }
  }

  async function handleResetPassword(username: string) {
    setError(null)
    try {
      const updated = await usersApi.updateUser(username, { reset_password: true })
      if (updated.temporary_password) {
        setTempPassword(updated.temporary_password)
      }
      await loadAccounts()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '비밀번호 초기화에 실패했습니다')
    }
  }

  return (
    <div className="admin-page">
      <header className="admin-topbar">
        <div className="topbar-left">
          <div className="brand">대장관리 플랫폼</div>
          <nav className="top-nav">
            <button type="button" className="nav-link" onClick={() => navigate('/')}>
              대장
            </button>
            <button type="button" className="nav-link active">
              관리
            </button>
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

      <main className="admin-main">
        <div className="tabs">
          <button
            type="button"
            className={tab === 'accounts' ? 'tab active' : 'tab'}
            onClick={() => setTab('accounts')}
          >
            계정 관리
          </button>
          <button
            type="button"
            className={tab === 'audit' ? 'tab active' : 'tab'}
            onClick={() => setTab('audit')}
          >
            변경 이력
          </button>
        </div>

        {error ? (
          <p className="page-error" role="alert">
            {error}
          </p>
        ) : null}

        {tab === 'accounts' ? (
          <section>
            <div className="section-toolbar">
              <h1>계정 관리</h1>
              <button type="button" className="primary-btn" onClick={() => setCreateOpen(true)}>
                + 계정 생성
              </button>
            </div>

            <div className="table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>아이디</th>
                    <th>역할</th>
                    <th>활성</th>
                    <th>로그인 실패</th>
                    <th>최종 로그인</th>
                    <th>생성일</th>
                    <th>관리</th>
                  </tr>
                </thead>
                <tbody>
                  {accountsLoading ? (
                    <tr>
                      <td colSpan={7} className="empty-cell">
                        불러오는 중…
                      </td>
                    </tr>
                  ) : accounts.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="empty-cell">
                        계정이 없습니다
                      </td>
                    </tr>
                  ) : (
                    accounts.map((account) => {
                      const isSelf = account.username === user.username
                      return (
                        <tr key={account.username}>
                          <td>{account.username}</td>
                          <td>
                            <select
                              value={account.role}
                              disabled={isSelf}
                              title={isSelf ? '본인 계정은 변경 불가' : undefined}
                              onChange={(e) =>
                                void handleRoleChange(account.username, e.target.value as UserRole)
                              }
                            >
                              <option value="read">read</option>
                              <option value="write">write</option>
                              <option value="admin">admin</option>
                            </select>
                          </td>
                          <td>{account.is_active === 1 ? '활성' : '비활성'}</td>
                          <td>{account.failed_login_count}</td>
                          <td>{account.last_login_at ?? '-'}</td>
                          <td>{account.created_at}</td>
                          <td className="actions-cell">
                            <button
                              type="button"
                              className="link-btn"
                              onClick={() => void handleResetPassword(account.username)}
                            >
                              비밀번호 초기화
                            </button>
                            <button
                              type="button"
                              className="link-btn"
                              disabled={isSelf}
                              title={isSelf ? '본인 계정은 변경 불가' : undefined}
                              onClick={() => void handleToggleActive(account)}
                            >
                              {account.is_active === 1 ? '비활성화' : '활성화'}
                            </button>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>
        ) : (
          <section>
            <div className="section-toolbar">
              <h1>변경 이력</h1>
            </div>

            <div className="audit-filters">
              <label>
                테이블
                <select value={tableFilter} onChange={(e) => setTableFilter(e.target.value)}>
                  <option value="">전체</option>
                  <option value="ledger">ledger</option>
                  <option value="users">users</option>
                </select>
              </label>
              <label>
                사용자명
                <input
                  value={usernameFilter}
                  onChange={(e) => setUsernameFilter(e.target.value)}
                  placeholder="username"
                />
              </label>
              <label>
                결과
                <select value={resultFilter} onChange={(e) => setResultFilter(e.target.value)}>
                  <option value="">전체</option>
                  <option value="SUCCESS">SUCCESS</option>
                  <option value="FAIL">FAIL</option>
                </select>
              </label>
              <button type="button" className="ghost-btn" onClick={() => void loadAudit()}>
                조회
              </button>
            </div>

            <div className="table-wrap">
              <table className="admin-table audit-table">
                <thead>
                  <tr>
                    <th>시각</th>
                    <th>사용자</th>
                    <th>테이블</th>
                    <th>동작</th>
                    <th>결과</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLoading ? (
                    <tr>
                      <td colSpan={6} className="empty-cell">
                        불러오는 중…
                      </td>
                    </tr>
                  ) : auditItems.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="empty-cell">
                        이력이 없습니다
                      </td>
                    </tr>
                  ) : (
                    auditItems.map((item) => (
                      <tr
                        key={item.id}
                        className={[
                          item.result === 'FAIL' ? 'fail-row' : '',
                          selectedAudit?.id === item.id ? 'selected-row' : '',
                        ]
                          .filter(Boolean)
                          .join(' ')}
                        onClick={() => setSelectedAudit(item)}
                      >
                        <td>{item.created_at}</td>
                        <td>{item.username ?? '-'}</td>
                        <td>{item.table_name}</td>
                        <td>{item.action}</td>
                        <td>{item.result}</td>
                        <td>{item.ip_address ?? '-'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {selectedAudit ? (
              <div className="audit-detail">
                <h2>
                  상세 #{selectedAudit.id} · {selectedAudit.action} / {selectedAudit.result}
                </h2>
                <div className="json-grid">
                  <div>
                    <h3>old_value</h3>
                    <pre>{formatJson(selectedAudit.old_value)}</pre>
                  </div>
                  <div>
                    <h3>new_value</h3>
                    <pre>{formatJson(selectedAudit.new_value)}</pre>
                  </div>
                </div>
              </div>
            ) : null}
          </section>
        )}
      </main>

      {createOpen ? (
        <div className="modal-backdrop" role="presentation" onClick={() => !creating && setCreateOpen(false)}>
          <div className="modal-card" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <h2>계정 생성</h2>
            <form onSubmit={(e) => void handleCreate(e)}>
              <label>
                아이디
                <input
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  required
                  disabled={creating}
                />
              </label>
              <label>
                초기 비밀번호
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  disabled={creating}
                />
              </label>
              <label>
                역할
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as UserRole)}
                  disabled={creating}
                >
                  <option value="read">read</option>
                  <option value="write">write</option>
                  <option value="admin">admin</option>
                </select>
              </label>
              <div className="form-actions">
                <button
                  type="button"
                  className="ghost-btn"
                  disabled={creating}
                  onClick={() => setCreateOpen(false)}
                >
                  취소
                </button>
                <button type="submit" className="primary-btn" disabled={creating}>
                  {creating ? '생성 중…' : '생성'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {tempPassword ? (
        <div className="modal-backdrop" role="presentation">
          <div className="modal-card" role="dialog" aria-modal="true">
            <h2>임시 비밀번호</h2>
            <p className="temp-password">{tempPassword}</p>
            <p className="temp-warning">이 창을 닫으면 다시 볼 수 없습니다</p>
            <div className="form-actions">
              <button type="button" className="primary-btn" onClick={() => setTempPassword(null)}>
                닫기
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
