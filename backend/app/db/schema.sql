CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('read', 'write', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    last_login_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger (
    id TEXT PRIMARY KEY,
    name TEXT,
    gender TEXT,
    address TEXT,
    phone TEXT,
    car_number TEXT NOT NULL,
    car_model TEXT,
    category TEXT,
    registered_at TEXT,
    period_start TEXT,
    period_end TEXT,
    note TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    updated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id TEXT,
    action TEXT NOT NULL,
    result TEXT NOT NULL CHECK(result IN ('SUCCESS', 'FAIL')),
    old_value TEXT,
    new_value TEXT,
    username TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_car_number ON ledger(car_number);
CREATE INDEX IF NOT EXISTS idx_ledger_name ON ledger(name);
CREATE INDEX IF NOT EXISTS idx_ledger_is_deleted ON ledger(is_deleted);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);
