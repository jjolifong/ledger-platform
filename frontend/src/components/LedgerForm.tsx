import { useMemo, useState, type FormEvent } from 'react'
import type { LedgerRow, LedgerWritableFields } from '../types'
import './LedgerForm.css'

type FormState = {
  name: string
  gender: string
  address: string
  phone: string
  car_number: string
  car_model: string
  category: string
  registered_at: string
  period_start: string
  period_end: string
  note: string
}

function emptyForm(): FormState {
  return {
    name: '',
    gender: '',
    address: '',
    phone: '',
    car_number: '',
    car_model: '',
    category: '',
    registered_at: '',
    period_start: '',
    period_end: '',
    note: '',
  }
}

function fromRow(row: LedgerRow): FormState {
  return {
    name: row.name ?? '',
    gender: row.gender ?? '',
    address: row.address ?? '',
    phone: row.phone ?? '',
    car_number: row.car_number ?? '',
    car_model: row.car_model ?? '',
    category: row.category ?? '',
    registered_at: row.registered_at ?? '',
    period_start: row.period_start ?? '',
    period_end: row.period_end ?? '',
    note: row.note ?? '',
  }
}

function toNullable(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

function toPayload(form: FormState): LedgerWritableFields {
  return {
    name: toNullable(form.name),
    gender: toNullable(form.gender),
    address: toNullable(form.address),
    phone: toNullable(form.phone),
    car_number: form.car_number.trim(),
    car_model: toNullable(form.car_model),
    category: toNullable(form.category),
    registered_at: toNullable(form.registered_at),
    period_start: toNullable(form.period_start),
    period_end: toNullable(form.period_end),
    note: toNullable(form.note),
  }
}

interface LedgerFormProps {
  mode: 'create' | 'edit'
  initial?: LedgerRow | null
  submitting?: boolean
  onCancel: () => void
  onSubmit: (payload: LedgerWritableFields | Partial<LedgerWritableFields>) => Promise<void> | void
}

export default function LedgerForm({
  mode,
  initial = null,
  submitting = false,
  onCancel,
  onSubmit,
}: LedgerFormProps) {
  const initialForm = useMemo(
    () => (mode === 'edit' && initial ? fromRow(initial) : emptyForm()),
    [mode, initial],
  )
  const [form, setForm] = useState<FormState>(initialForm)
  const [error, setError] = useState<string | null>(null)

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (!form.car_number.trim()) {
      setError('차량번호는 필수입니다')
      return
    }

    if (
      form.period_start &&
      form.period_end &&
      form.period_end < form.period_start
    ) {
      setError('종료일은 시작일보다 빠를 수 없습니다')
      return
    }

    const next = toPayload(form)

    if (mode === 'create') {
      await onSubmit(next)
      return
    }

    const prev = toPayload(initialForm)
    const patch: Partial<LedgerWritableFields> = {}
    ;(Object.keys(next) as (keyof LedgerWritableFields)[]).forEach((key) => {
      if (next[key] !== prev[key]) {
        Object.assign(patch, { [key]: next[key] })
      }
    })
    await onSubmit(patch)
  }

  return (
    <div className="ledger-modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="ledger-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ledger-form-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ledger-modal-header">
          <h2 id="ledger-form-title">{mode === 'create' ? '신규 등록' : '대장 수정'}</h2>
          <button type="button" className="ghost-btn" onClick={onCancel} disabled={submitting}>
            닫기
          </button>
        </div>

        <form className="ledger-form" onSubmit={(e) => void handleSubmit(e)}>
          <label>
            이름
            <input
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              disabled={submitting}
            />
          </label>

          <label>
            성별
            <select
              value={form.gender}
              onChange={(e) => updateField('gender', e.target.value)}
              disabled={submitting}
            >
              <option value="">선택</option>
              <option value="남">남</option>
              <option value="여">여</option>
              <option value="기타">기타</option>
            </select>
          </label>

          <label className="full">
            주소
            <input
              value={form.address}
              onChange={(e) => updateField('address', e.target.value)}
              disabled={submitting}
            />
          </label>

          <label>
            연락처
            <input
              value={form.phone}
              onChange={(e) => updateField('phone', e.target.value)}
              disabled={submitting}
            />
          </label>

          <label>
            차량번호 <span className="required">*</span>
            <input
              value={form.car_number}
              onChange={(e) => updateField('car_number', e.target.value)}
              disabled={submitting}
              required
            />
          </label>

          <label>
            차종
            <input
              value={form.car_model}
              onChange={(e) => updateField('car_model', e.target.value)}
              disabled={submitting}
            />
          </label>

          <label>
            구분
            <select
              value={form.category}
              onChange={(e) => updateField('category', e.target.value)}
              disabled={submitting}
            >
              <option value="">선택</option>
              <option value="거주자">거주자</option>
              <option value="회사원">회사원</option>
              <option value="기타">기타</option>
            </select>
          </label>

          <label>
            등록일
            <input
              type="date"
              value={form.registered_at}
              onChange={(e) => updateField('registered_at', e.target.value)}
              disabled={submitting}
            />
          </label>

          <label>
            등록기간 시작일
            <input
              type="date"
              value={form.period_start}
              onChange={(e) => updateField('period_start', e.target.value)}
              disabled={submitting}
            />
          </label>

          <label>
            등록기간 종료일
            <input
              type="date"
              value={form.period_end}
              onChange={(e) => updateField('period_end', e.target.value)}
              disabled={submitting}
            />
          </label>

          <label className="full">
            비고
            <textarea
              rows={3}
              value={form.note}
              onChange={(e) => updateField('note', e.target.value)}
              disabled={submitting}
            />
          </label>

          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}

          <div className="form-actions">
            <button type="button" className="ghost-btn" onClick={onCancel} disabled={submitting}>
              취소
            </button>
            <button type="submit" className="primary-btn" disabled={submitting}>
              {submitting ? '저장 중…' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
