"""엑셀 대장을 SQLite ledger 테이블로 이관한다 (append only).

사용법: python migrate_excel.py <엑셀파일경로>
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent.parent / "ledger.db"

COLUMN_MAP = {
    "이름": "name",
    "성별": "gender",
    "주소": "address",
    "연락처": "phone",
    "차량번호": "car_number",
    "차종": "car_model",
    "구분": "category",
    "등록일": "registered_at",
    "비고": "note",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cell_str(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return None
    return text


def _parse_period(raw) -> tuple[str | None, str | None, bool]:
    """등록기간 파싱. 성공 시 (start, end, True), 실패/빈값 시 (None, None, False)."""
    text = _cell_str(raw)
    if text is None:
        return None, None, False
    if "~" not in text:
        return None, None, False
    left, right = text.split("~", 1)
    start = left.strip() or None
    end = right.strip() or None
    if start is None or end is None:
        return None, None, False
    return start, end, True


def migrate(excel_path: Path) -> None:
    if not excel_path.exists():
        raise FileNotFoundError(f"엑셀 파일이 없습니다: {excel_path}")
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB 파일이 없습니다: {DB_PATH}\n먼저 init_db.py를 실행하세요."
        )

    df = pd.read_excel(excel_path, engine="openpyxl")
    source_rows = len(df)

    # 엑셀 행 번호: 헤더가 1행이므로 데이터는 2행부터
    prepared: list[dict] = []
    skipped_empty_car: list[int] = []
    period_warnings: list[int] = []

    for offset, (_, row) in enumerate(df.iterrows()):
        excel_row_num = offset + 2
        car_number = _cell_str(row.get("차량번호"))
        if car_number is None:
            skipped_empty_car.append(excel_row_num)
            print(f"[건너뜀] 엑셀 {excel_row_num}행: 차량번호 없음")
            continue

        period_start, period_end, ok = _parse_period(row.get("등록기간"))
        if not ok:
            period_warnings.append(excel_row_num)
            print(
                f"[경고] 엑셀 {excel_row_num}행: 등록기간 파싱 불가 "
                f"(period_start/period_end=NULL로 이관)"
            )

        record = {
            "car_number": car_number,
            "period_start": period_start,
            "period_end": period_end,
        }
        for ko, en in COLUMN_MAP.items():
            record[en] = _cell_str(row.get(ko)) if en != "car_number" else car_number
        # car_number는 위에서 확정
        record["car_number"] = car_number
        prepared.append(record)

    print()
    print("=== 이관 전 확인 ===")
    print(f"  엑셀 파일: {excel_path}")
    print(f"  엑셀 원본 행수: {source_rows}")
    print(f"  이관 대상(차량번호 있음): {len(prepared)}")
    print(f"  건너뛸 행(차량번호 없음): {len(skipped_empty_car)}")
    print(f"  등록기간 경고 예정: {len(period_warnings)}")
    answer = input("진행할까요? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("이관을 취소했습니다.")
        return

    now = _now()
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    try:
        cur = conn.cursor()
        for record in prepared:
            ledger_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO ledger (
                    id, name, gender, address, phone, car_number, car_model,
                    category, registered_at, period_start, period_end, note,
                    is_deleted, updated_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'migration', ?, ?)
                """,
                (
                    ledger_id,
                    record.get("name"),
                    record.get("gender"),
                    record.get("address"),
                    record.get("phone"),
                    record["car_number"],
                    record.get("car_model"),
                    record.get("category"),
                    record.get("registered_at"),
                    record.get("period_start"),
                    record.get("period_end"),
                    record.get("note"),
                    now,
                    now,
                ),
            )
            inserted += 1
        conn.commit()
        total_after = cur.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    finally:
        conn.close()

    print()
    print("=== 이관 리포트 ===")
    print(f"  엑셀 원본 행수: {source_rows}")
    print(f"  이관 성공 건수: {inserted}")
    print(f"  건너뛴 건수:")
    print(f"    - 차량번호 누락: {len(skipped_empty_car)}건 {skipped_empty_car}")
    print(f"  등록기간 파싱 경고: {len(period_warnings)}건 {period_warnings}")
    print(f"  이관 후 DB ledger 총 건수: {total_after}")


def main() -> None:
    if len(sys.argv) != 2:
        print("사용법: python migrate_excel.py <엑셀파일경로>")
        sys.exit(1)
    migrate(Path(sys.argv[1]).expanduser().resolve())


if __name__ == "__main__":
    main()
