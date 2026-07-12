#!/bin/sh
set -e

cd /app/backend

# 1. DB 스키마 생성 (파일이 이미 있으면 건너뜀)
if [ ! -f ledger.db ]; then
  echo "[entrypoint] init_db: ledger.db 없음 → 스키마 생성"
  python -m app.db.init_db
else
  echo "[entrypoint] init_db: ledger.db 이미 존재 → 건너뜀"
fi

# 2. 더미 시드 (이미 시드되어 있으면 건너뜀, 시드 시 seed.py 멱등성 로직 사용)
USER_COUNT=$(python -c "import sqlite3; conn=sqlite3.connect('ledger.db'); print(conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]); conn.close()")
if [ "$USER_COUNT" = "0" ]; then
  echo "[entrypoint] seed: 사용자 없음 → 더미 데이터 시드"
  python -m app.db.seed
else
  echo "[entrypoint] seed: 이미 시드됨 (users=${USER_COUNT}) → 건너뜀"
fi

# 3. uvicorn (PORT 환경변수 우선, 기본 8000)
PORT="${PORT:-8000}"
echo "[entrypoint] uvicorn: host=0.0.0.0 port=${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
