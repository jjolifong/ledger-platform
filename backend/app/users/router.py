"""계정 관리 및 변경 이력 조회 (admin 전용)."""

from __future__ import annotations

import json
import secrets
import sqlite3
import uuid
from typing import Any, Literal

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth.security import get_current_user, utc_now_str
from app.db.database import get_connection

router = APIRouter(prefix="/api")

USER_PUBLIC_FIELDS = (
    "username",
    "role",
    "is_active",
    "failed_login_count",
    "last_login_at",
    "created_at",
)

RoleType = Literal["read", "write", "admin"]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    role: RoleType


class UserUpdate(BaseModel):
    role: RoleType | None = None
    is_active: int | None = Field(default=None, ge=0, le=1)
    reset_password: bool | None = None


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in USER_PUBLIC_FIELDS}


def _audit_snapshot(row: sqlite3.Row | dict[str, Any], *, password_reset: bool = False) -> dict[str, Any]:
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in USER_PUBLIC_FIELDS}
    else:
        data = {key: row[key] for key in USER_PUBLIC_FIELDS if key in row}
    if password_reset:
        data["password_reset"] = True
    return data


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
            "users",
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


def _require_admin(
    conn: sqlite3.Connection,
    user: dict[str, Any],
    request: Request,
    action: str,
    attempt_payload: dict[str, Any],
    record_id: str | None = None,
) -> None:
    if user["role"] == "admin":
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


def _get_user_row(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return conn.execute(
        f"""
        SELECT id, password_hash, {', '.join(USER_PUBLIC_FIELDS)}
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()


@router.get("/users")
def list_users(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    conn = get_connection()
    try:
        _require_admin(conn, current_user, request, "list_users", {})
        rows = conn.execute(
            f"""
            SELECT {', '.join(USER_PUBLIC_FIELDS)}
            FROM users
            ORDER BY created_at ASC, username ASC
            """
        ).fetchall()
        return {"items": [_public_user(row) for row in rows], "total": len(rows)}
    finally:
        conn.close()


@router.post("/users", status_code=200)
def create_user(
    body: UserCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    payload = {"username": body.username, "role": body.role}
    conn = get_connection()
    try:
        _require_admin(conn, current_user, request, "account_change", payload)

        existing = _get_user_row(conn, body.username)
        if existing is not None:
            raise HTTPException(status_code=409, detail="이미 존재하는 사용자명입니다")

        user_id = str(uuid.uuid4())
        now = utc_now_str()
        password_hash = _hash_password(body.password)
        conn.execute(
            """
            INSERT INTO users (
                id, username, password_hash, role, is_active,
                failed_login_count, last_login_at, created_at
            ) VALUES (?, ?, ?, ?, 1, 0, NULL, ?)
            """,
            (user_id, body.username, password_hash, body.role, now),
        )
        _write_audit(
            conn,
            action="account_change",
            result="SUCCESS",
            username=current_user["username"],
            ip_address=_client_ip(request),
            record_id=user_id,
            new_value=json.dumps(
                {"username": body.username, "role": body.role},
                ensure_ascii=False,
            ),
        )
        conn.commit()
        created = _get_user_row(conn, body.username)
        return _public_user(created)  # type: ignore[arg-type]
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.patch("/users/{username}")
def update_user(
    username: str,
    body: UserUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    changes = body.model_dump(exclude_unset=True)
    # 감사/권한 실패 기록용 — 비밀번호 값은 절대 넣지 않음
    attempt = {"username": username, **{k: v for k, v in changes.items() if k != "reset_password"}}
    if changes.get("reset_password") is True:
        attempt["reset_password"] = True

    conn = get_connection()
    try:
        _require_admin(
            conn,
            current_user,
            request,
            "account_change",
            attempt,
            record_id=username,
        )

        target = _get_user_row(conn, username)
        if target is None:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

        is_self = current_user["username"] == username
        if is_self:
            if "role" in changes and changes["role"] != target["role"]:
                raise HTTPException(
                    status_code=400,
                    detail="자신의 역할은 변경할 수 없습니다",
                )
            if changes.get("is_active") == 0:
                raise HTTPException(
                    status_code=400,
                    detail="자신을 비활성화할 수 없습니다",
                )

        old_snap = _audit_snapshot(target)
        set_parts: list[str] = []
        params: list[Any] = []
        temporary_password: str | None = None
        password_reset = False

        if "role" in changes:
            set_parts.append("role = ?")
            params.append(changes["role"])

        if "is_active" in changes:
            set_parts.append("is_active = ?")
            params.append(changes["is_active"])

        if changes.get("reset_password") is True:
            temporary_password = secrets.token_urlsafe(12)
            set_parts.append("password_hash = ?")
            params.append(_hash_password(temporary_password))
            set_parts.append("failed_login_count = 0")
            password_reset = True

        if not set_parts:
            return _public_user(target)

        params.append(username)
        conn.execute(
            f"UPDATE users SET {', '.join(set_parts)} WHERE username = ?",
            params,
        )

        if changes.get("is_active") == 0:
            conn.execute("DELETE FROM sessions WHERE username = ?", (username,))

        updated = _get_user_row(conn, username)
        new_snap = _audit_snapshot(updated, password_reset=password_reset)  # type: ignore[arg-type]
        _write_audit(
            conn,
            action="account_change",
            result="SUCCESS",
            username=current_user["username"],
            ip_address=_client_ip(request),
            record_id=updated["id"],  # type: ignore[index]
            old_value=json.dumps(old_snap, ensure_ascii=False),
            new_value=json.dumps(new_snap, ensure_ascii=False),
        )
        conn.commit()

        result = _public_user(updated)  # type: ignore[arg-type]
        if temporary_password is not None:
            result["temporary_password"] = temporary_password
        return result
    except HTTPException:
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@router.get("/audit-log")
def list_audit_log(
    request: Request,
    table_name: str | None = Query(default=None),
    username: str | None = Query(default=None),
    result: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
) -> dict:
    filters: dict[str, Any] = {}
    if table_name is not None:
        filters["table_name"] = table_name
    if username is not None:
        filters["username"] = username
    if result is not None:
        filters["result"] = result
    filters["limit"] = limit

    conn = get_connection()
    try:
        _require_admin(conn, current_user, request, "list_audit", filters)

        where_parts: list[str] = []
        params: list[Any] = []
        if table_name is not None:
            where_parts.append("table_name = ?")
            params.append(table_name)
        if username is not None:
            where_parts.append("username = ?")
            params.append(username)
        if result is not None:
            where_parts.append("result = ?")
            params.append(result)

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        params.append(limit)
        rows = conn.execute(
            f"""
            SELECT id, table_name, record_id, action, result,
                   old_value, new_value, username, ip_address, created_at
            FROM audit_log
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        items = [{key: row[key] for key in row.keys()} for row in rows]
        return {"items": items, "total": len(items)}
    finally:
        conn.close()
