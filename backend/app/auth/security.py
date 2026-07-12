"""인증·세션 유틸 및 get_current_user 의존성."""

from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Cookie, HTTPException

from app.db.database import get_connection

SESSION_COOKIE = "session_token"
SESSION_HOURS = 8
LOGIN_FAIL_MESSAGE = "아이디 또는 비밀번호가 올바르지 않습니다"
LOCKED_MESSAGE = "계정이 잠겼습니다. 관리자에게 문의하세요"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_str() -> str:
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))


def create_session(conn: sqlite3.Connection, username: str) -> str:
    token = secrets.token_urlsafe(32)
    now = utc_now()
    created_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    expires_at = (now + timedelta(hours=SESSION_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """
        INSERT INTO sessions (token, username, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (token, username, expires_at, created_at),
    )
    return token


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def get_session(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT token, username, expires_at, created_at FROM sessions WHERE token = ?",
        (token,),
    ).fetchone()


def write_audit_log(
    conn: sqlite3.Connection,
    *,
    action: str,
    result: str,
    username: str | None,
    ip_address: str | None,
    table_name: str = "users",
    record_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (
            table_name, record_id, action, result,
            old_value, new_value, username, ip_address, created_at
        ) VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?)
        """,
        (table_name, record_id, action, result, username, ip_address, utc_now_str()),
    )


def get_user_by_username(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, username, password_hash, role, is_active,
               failed_login_count, last_login_at, created_at
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()


def get_current_user(session_token: str | None = Cookie(default=None)) -> dict[str, Any]:
    """쿠키 세션으로 현재 사용자를 확인. 이후 보호 API에서 재사용."""
    if not session_token:
        raise HTTPException(status_code=401, detail=LOGIN_FAIL_MESSAGE)

    conn = get_connection()
    try:
        session = get_session(conn, session_token)
        if session is None:
            raise HTTPException(status_code=401, detail=LOGIN_FAIL_MESSAGE)

        if session["expires_at"] < utc_now_str():
            delete_session(conn, session_token)
            conn.commit()
            raise HTTPException(status_code=401, detail=LOGIN_FAIL_MESSAGE)

        user = get_user_by_username(conn, session["username"])
        if user is None or user["is_active"] != 1:
            raise HTTPException(status_code=401, detail=LOGIN_FAIL_MESSAGE)

        return {"username": user["username"], "role": user["role"]}
    finally:
        conn.close()
