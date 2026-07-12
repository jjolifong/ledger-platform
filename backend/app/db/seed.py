"""더미 시드 데이터를 삽입한다. 재실행 시 기존 데이터를 모두 지우고 새로 넣는다."""

import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import bcrypt

DB_PATH = Path(__file__).resolve().parent.parent.parent / "ledger.db"

# 초기 비밀번호 (콘솔에만 출력, DB에는 bcrypt 해시만 저장)
INITIAL_PASSWORD = "ChangeMe123!"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _note_for_period_end(period_end: str) -> str:
    """실행일 기준으로 period_end가 이전이면 만료, 이후(당일 포함)면 유효기간 중."""
    if period_end < date.today().isoformat():
        return "만료"
    return "유효기간 중"


def seed() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB 파일이 없습니다: {DB_PATH}\n먼저 init_db.py를 실행하세요."
        )

    created_at = _now()

    # 계정마다 hashpw를 개별 호출해 salt가 다른 해시를 저장
    users = [
        (str(uuid.uuid4()), "admin", _hash_password(INITIAL_PASSWORD), "admin", 1, 0, None, created_at),
        (str(uuid.uuid4()), "writer", _hash_password(INITIAL_PASSWORD), "write", 1, 0, None, created_at),
        (str(uuid.uuid4()), "reader1", _hash_password(INITIAL_PASSWORD), "read", 1, 0, None, created_at),
        (str(uuid.uuid4()), "reader2", _hash_password(INITIAL_PASSWORD), "read", 1, 0, None, created_at),
    ]

    # period: 일부는 유효기간 중, 일부는 만료 (note는 실행일 기준 자동 판정)
    # name, gender, address, phone, car_number, car_model, category,
    # registered_at, period_start, period_end, is_deleted, updated_by
    ledger_rows = [
        (
            "테스트이용자1",
            "남",
            "서울시 테스트구 더미로 1",
            "010-0000-0001",
            "12가0001",
            "테스트모델A",
            "거주자",
            "2025-01-10",
            "2025-01-01",
            "2026-12-31",
            0,
            "admin",
        ),
        (
            "테스트이용자2",
            "여",
            "서울시 테스트구 더미로 2",
            "010-0000-0002",
            "12가0002",
            "테스트모델B",
            "회사원",
            "2025-02-15",
            "2025-02-01",
            "2026-06-30",
            0,
            "writer",
        ),
        (
            "테스트이용자3",
            "기타",
            "서울시 테스트구 더미로 3",
            "010-0000-0003",
            "12가0003",
            "테스트모델C",
            "기타",
            "2024-03-01",
            "2024-01-01",
            "2024-12-31",
            0,
            "admin",
        ),
        (
            "테스트이용자4",
            "남",
            "서울시 테스트구 더미로 4",
            "010-0000-0004",
            "12가0004",
            "테스트모델D",
            "거주자",
            "2024-06-20",
            "2024-06-01",
            "2025-05-31",
            0,
            "writer",
        ),
        (
            "테스트이용자5",
            "여",
            "서울시 테스트구 더미로 5",
            "010-0000-0005",
            "12가0005",
            "테스트모델E",
            "회사원",
            "2025-07-01",
            "2025-07-01",
            "2027-06-30",
            0,
            "admin",
        ),
        (
            "테스트이용자6",
            "남",
            "서울시 테스트구 더미로 6",
            "010-0000-0006",
            "12가0006",
            "테스트모델F",
            "기타",
            "2023-11-11",
            "2023-11-01",
            "2024-10-31",
            0,
            "writer",
        ),
        (
            "테스트이용자7",
            "여",
            "서울시 테스트구 더미로 7",
            "010-0000-0007",
            "12가0007",
            "테스트모델G",
            "거주자",
            "2025-09-01",
            "2025-09-01",
            "2026-08-31",
            0,
            "admin",
        ),
        (
            "테스트이용자8",
            "기타",
            "서울시 테스트구 더미로 8",
            "010-0000-0008",
            "12가0008",
            "테스트모델H",
            "회사원",
            "2025-04-12",
            "2025-04-01",
            "2025-12-31",
            0,
            "writer",
        ),
    ]

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 멱등성: 기존 데이터 전부 삭제 후 재삽입
        cur.execute("DELETE FROM audit_log")
        cur.execute("DELETE FROM ledger")
        cur.execute("DELETE FROM users")

        cur.executemany(
            """
            INSERT INTO users (
                id, username, password_hash, role, is_active,
                failed_login_count, last_login_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            users,
        )

        ledger_params = []
        for row in ledger_rows:
            (
                name,
                gender,
                address,
                phone,
                car_number,
                car_model,
                category,
                registered_at,
                period_start,
                period_end,
                is_deleted,
                updated_by,
            ) = row
            note = _note_for_period_end(period_end)
            ledger_params.append(
                (
                    str(uuid.uuid4()),
                    name,
                    gender,
                    address,
                    phone,
                    car_number,
                    car_model,
                    category,
                    registered_at,
                    period_start,
                    period_end,
                    note,
                    is_deleted,
                    updated_by,
                    created_at,
                    created_at,
                )
            )

        cur.executemany(
            """
            INSERT INTO ledger (
                id, name, gender, address, phone, car_number, car_model,
                category, registered_at, period_start, period_end, note,
                is_deleted, updated_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ledger_params,
        )

        conn.commit()

        user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        ledger_count = cur.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
        audit_count = cur.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]

        print(f"시드 완료: {DB_PATH}")
        print(f"  users: {user_count}")
        print(f"  ledger: {ledger_count}")
        print(f"  audit_log: {audit_count}")
        print()
        print("초기 비밀번호 (모든 사용자 공통):")
        print(f"  {INITIAL_PASSWORD}")
        print("사용자 목록: admin, writer, reader1, reader2")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
