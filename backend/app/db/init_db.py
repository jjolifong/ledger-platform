"""schema.sql을 읽어 backend/ledger.db를 생성한다."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "ledger.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema)
        conn.commit()
        print(f"DB 생성 완료: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
