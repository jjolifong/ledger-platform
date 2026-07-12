"""대장(ledger) CRUD 엔드포인트."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth.security import get_current_user, utc_now_str
from app.db.database import get_connection

router = APIRouter(prefix="/api")

ALLOWED_SORT = frozenset(
    {
        "name",
        "gender",
        "address",
        "phone",
        "car_number",
        "car_model",
        "category",
        "registered_at",
        "period_start",
        "period_end",
        "note",
        "created_at",
        "updated_at",
        "updated_by",
    }
)

LEDGER_COLUMNS = (
    "id",
    "name",
    "gender",
    "address",
    "phone",
    "car_number",
    "car_model",
    "category",
    "registered_at",
    "period_start",
    "period_end",
    "note",
    "is_deleted",
    "updated_by",
    "created_at",
    "updated_at",
)

UPDATABLE_FIELDS = (
    "name",
    "gender",
    "address",
    "phone",
    "car_number",
    "car_model",
    "category",
    "registered_at",
    "period_start",
    "period_end",
    "note",
)


class LedgerCreate(BaseModel):
    name: str | None = None
    gender: str | None = None
    address: str | None = None
    phone: str | None = None
    car_number: str = Field(..., min_length=1)
    car_model: str | None = None
    category: str | None = None
    registered_at: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    note: str | None = None


class LedgerUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    address: str | None = None
    phone: str | None = None
    car_number: str | None = None
    car_model: str | None = None
    category: str | None = None
    registered_at: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    note: str | None = None


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def _write_audit(
    conn: sqlite3.Connection,
    *,
    action: str,
    result: str,
    username: str | None,
    ip_address: str | None,
    record_id: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (
            table_name, record_id, action, result,
            old_value, new_value, username, ip_address, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "ledger",
            record_id,
            action,
            result,
            old_value,
            new_value,
            username,
            ip_address,
            utc_now_str(),
        ),
    )


def _require_write(
    conn: sqlite3.Connection,
    user: dict[str, Any],
    request: Request,
    action: str,
    attempt_payload: dict[str, Any],
    record_id: str | None = None,
) -> None:
    if user["role"] in ("write", "admin"):
        return

    _write_audit(
        conn,
        action=action,
        result="FAIL",
        username=user["username"],
        ip_address=_client_ip(request),
        record_id=record_id,
        old_value=None,
        new_value=json.dumps(attempt_payload, ensure_ascii=False),
    )
    conn.commit()
    raise HTTPException(status_code=403, detail="권한이 없습니다")


def _get_active_row(conn: sqlite3.Connection, ledger_id: str) -> sqlite3.Row | None:
    return conn.execute(
        f"SELECT {', '.join(LEDGER_COLUMNS)} FROM ledger WHERE id = ? AND is_deleted = 0",
        (ledger_id,),
    ).fetchone()


@router.get("/ledger")
def list_ledger(
    search: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    order: str = Query(default="asc"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _ = current_user  # read 이상: 로그인만 되면 허용

    sort_col = sort if sort in ALLOWED_SORT else "created_at"
    order_dir = "DESC" if order.lower() == "desc" else "ASC"

    where = "is_deleted = 0"
    params: list[Any] = []
    if search:
        where += " AND (name LIKE ? OR car_number LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    conn = get_connection()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM ledger WHERE {where}",
            params,
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT {', '.join(LEDGER_COLUMNS)}
            FROM ledger
            WHERE {where}
            ORDER BY {sort_col} {order_dir}
            """,
            params,
        ).fetchall()
        return {
            "items": [_row_to_dict(row) for row in rows],
            "total": total,
        }
    finally:
        conn.close()


@router.get("/ledger/{ledger_id}")
def get_ledger(
    ledger_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    _ = current_user
    conn = get_connection()
    try:
        row = _get_active_row(conn, ledger_id)
        if row is None:
            raise HTTPException(status_code=404, detail="대장을 찾을 수 없습니다")
        return _row_to_dict(row)  # type: ignore[return-value]
    finally:
        conn.close()


@router.post("/ledger", status_code=200)
def create_ledger(
    body: LedgerCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    payload = body.model_dump()
    conn = get_connection()
    try:
        _require_write(conn, current_user, request, "create", payload)

        now = utc_now_str()
        ledger_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO ledger (
                id, name, gender, address, phone, car_number, car_model,
                category, registered_at, period_start, period_end, note,
                is_deleted, updated_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                ledger_id,
                body.name,
                body.gender,
                body.address,
                body.phone,
                body.car_number,
                body.car_model,
                body.category,
                body.registered_at,
                body.period_start,
                body.period_end,
                body.note,
                current_user["username"],
                now,
                now,
            ),
        )
        created = _row_to_dict(_get_active_row(conn, ledger_id))
        _write_audit(
            conn,
            action="create",
            result="SUCCESS",
            username=current_user["username"],
            ip_address=_client_ip(request),
            record_id=ledger_id,
            new_value=json.dumps(created, ensure_ascii=False),
        )
        conn.commit()
        return created  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.patch("/ledger/{ledger_id}")
def update_ledger(
    ledger_id: str,
    body: LedgerUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    # id / created_at / is_deleted 는 모델에 없으므로 무시됨
    changes = body.model_dump(exclude_unset=True)
    conn = get_connection()
    try:
        _require_write(
            conn,
            current_user,
            request,
            "update",
            {"id": ledger_id, **changes},
            record_id=ledger_id,
        )

        old_row = _get_active_row(conn, ledger_id)
        if old_row is None:
            raise HTTPException(status_code=404, detail="대장을 찾을 수 없습니다")

        old_dict = _row_to_dict(old_row)
        now = utc_now_str()
        set_parts = ["updated_by = ?", "updated_at = ?"]
        params: list[Any] = [current_user["username"], now]
        for field in UPDATABLE_FIELDS:
            if field in changes:
                set_parts.append(f"{field} = ?")
                params.append(changes[field])
        params.append(ledger_id)

        conn.execute(
            f"UPDATE ledger SET {', '.join(set_parts)} WHERE id = ? AND is_deleted = 0",
            params,
        )
        new_row = _get_active_row(conn, ledger_id)
        new_dict = _row_to_dict(new_row)
        _write_audit(
            conn,
            action="update",
            result="SUCCESS",
            username=current_user["username"],
            ip_address=_client_ip(request),
            record_id=ledger_id,
            old_value=json.dumps(old_dict, ensure_ascii=False),
            new_value=json.dumps(new_dict, ensure_ascii=False),
        )
        conn.commit()
        return new_dict  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.delete("/ledger/{ledger_id}")
def delete_ledger(
    ledger_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    conn = get_connection()
    try:
        _require_write(
            conn,
            current_user,
            request,
            "delete",
            {"id": ledger_id},
            record_id=ledger_id,
        )

        old_row = _get_active_row(conn, ledger_id)
        if old_row is None:
            raise HTTPException(status_code=404, detail="대장을 찾을 수 없습니다")

        old_dict = _row_to_dict(old_row)
        now = utc_now_str()
        conn.execute(
            """
            UPDATE ledger
            SET is_deleted = 1, updated_by = ?, updated_at = ?
            WHERE id = ? AND is_deleted = 0
            """,
            (current_user["username"], now, ledger_id),
        )
        _write_audit(
            conn,
            action="delete",
            result="SUCCESS",
            username=current_user["username"],
            ip_address=_client_ip(request),
            record_id=ledger_id,
            old_value=json.dumps(old_dict, ensure_ascii=False),
        )
        conn.commit()
        return {"ok": True, "id": ledger_id}
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
