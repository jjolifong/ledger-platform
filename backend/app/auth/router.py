"""로그인 / 로그아웃 / 내 정보 엔드포인트."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth.security import (
    LOCKED_MESSAGE,
    LOGIN_FAIL_MESSAGE,
    SESSION_COOKIE,
    create_session,
    delete_session,
    get_current_user,
    get_user_by_username,
    utc_now_str,
    verify_password,
    write_audit_log,
)
from app.db.database import get_connection

router = APIRouter(prefix="/api")


class LoginRequest(BaseModel):
    username: str
    password: str


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response) -> dict:
    conn = get_connection()
    try:
        user = get_user_by_username(conn, body.username)

        if user is None or user["is_active"] != 1:
            raise HTTPException(status_code=401, detail=LOGIN_FAIL_MESSAGE)

        if user["failed_login_count"] >= 5:
            raise HTTPException(status_code=423, detail=LOCKED_MESSAGE)

        if not verify_password(body.password, user["password_hash"]):
            conn.execute(
                """
                UPDATE users
                SET failed_login_count = failed_login_count + 1
                WHERE username = ?
                """,
                (user["username"],),
            )
            write_audit_log(
                conn,
                action="login",
                result="FAIL",
                username=user["username"],
                ip_address=_client_ip(request),
                record_id=user["id"],
            )
            conn.commit()
            raise HTTPException(status_code=401, detail=LOGIN_FAIL_MESSAGE)

        now = utc_now_str()
        conn.execute(
            """
            UPDATE users
            SET failed_login_count = 0, last_login_at = ?
            WHERE username = ?
            """,
            (now, user["username"]),
        )
        token = create_session(conn, user["username"])
        write_audit_log(
            conn,
            action="login",
            result="SUCCESS",
            username=user["username"],
            ip_address=_client_ip(request),
            record_id=user["id"],
        )
        conn.commit()

        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return {"username": user["username"], "role": user["role"]}
    finally:
        conn.close()


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None),
) -> dict:
    if session_token:
        conn = get_connection()
        try:
            delete_session(conn, session_token)
            conn.commit()
        finally:
            conn.close()

    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)) -> dict:
    return current_user
